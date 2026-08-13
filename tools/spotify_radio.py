#!/data/data/com.termux/files/usr/bin/python
"""Spotify-first background radio control for the Home Center Android overlay.

The visible widget and Adam prompt lane submit bounded commands. This module is
the deterministic Shizuku/rish muscle. It never parses prose into arbitrary
shell and never reports playback unless Android's media-session state verifies
Spotify as the controlled session.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import urllib.parse
from pathlib import Path
from typing import Any

PACKAGE = "com.spotify.music"
OVERLAY_PACKAGE = "com.homecenter.operatoroverlay"
BRIDGE_CLASS = "com.homecenter.operatoroverlay.SpotifyMediaBridge"
STATE_DIR = Path(os.environ.get(
    "HC_SPOTIFY_RADIO_STATE",
    "~/.local/state/home-center/spotify-radio",
)).expanduser()
STATE_FILE = STATE_DIR / "state.json"
RECEIPTS = STATE_DIR / "receipts.jsonl"
PID_FILE = STATE_DIR / "keepalive.pid"
LOG_FILE = STATE_DIR / "keepalive.log"
DEFAULT_INTERVAL = max(3.0, min(float(os.environ.get("HC_SPOTIFY_RADIO_INTERVAL", "7")), 30.0))
COMMAND_TIMEOUT = max(5, min(int(os.environ.get("HC_SPOTIFY_RADIO_COMMAND_TIMEOUT", "30")), 90))
PLAYBACK_NAMES = {
    0: "none",
    1: "stopped",
    2: "paused",
    3: "playing",
    4: "fast_forwarding",
    5: "rewinding",
    6: "buffering",
    7: "error",
    8: "connecting",
    9: "skipping_previous",
    10: "skipping_next",
    11: "skipping_queue_item",
}
MEDIA_KEYS = {
    "play": "play",
    "pause": "pause",
    "toggle": "play-pause",
    "stop": "stop",
    "next": "next",
    "previous": "previous",
}
PROMPT_ALIASES = {
    "play": "play",
    "start": "play",
    "resume": "play",
    "go": "play",
    "keep rolling": "play",
    "keep it rolling": "play",
    "roll": "play",
    "pause": "pause",
    "hold": "pause",
    "toggle": "toggle",
    "play pause": "toggle",
    "next": "next",
    "skip": "next",
    "skip this": "next",
    "previous": "previous",
    "prev": "previous",
    "back": "previous",
    "go back": "previous",
    "stop": "stop",
    "stop radio": "stop",
    "status": "status",
    "what is playing": "status",
    "what's playing": "status",
    "now playing": "status",
    "doctor": "doctor",
    "keep on": "keep-on",
    "continuous on": "keep-on",
    "keep off": "keep-off",
    "continuous off": "keep-off",
}


class RadioError(RuntimeError):
    pass


def _now_ms() -> int:
    return int(time.time() * 1000)


def _mkdirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def _default_state() -> dict[str, Any]:
    return {
        "schema": "home-center.spotify-radio-state.v1",
        "playlistUri": "",
        "playlistName": "",
        "continuous": False,
        "desiredPlaying": False,
        "lastExplicitCommand": "",
        "lastCommandAtMs": 0,
        "lastRecoveryAttemptAtMs": 0,
        "updatedAtMs": 0,
    }


def load_state() -> dict[str, Any]:
    _mkdirs()
    state = _default_state()
    if STATE_FILE.exists():
        try:
            saved = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(saved, dict):
                state.update(saved)
        except (OSError, ValueError):
            pass
    return state


def save_state(state: dict[str, Any]) -> dict[str, Any]:
    _mkdirs()
    state = {**_default_state(), **state, "updatedAtMs": _now_ms()}
    temp = STATE_FILE.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(STATE_FILE)
    return state


def receipt(kind: str, ok: bool, **fields: Any) -> dict[str, Any]:
    _mkdirs()
    row = {
        "schema": "home-center.spotify-radio-receipt.v1",
        "kind": kind,
        "ok": bool(ok),
        "atMs": _now_ms(),
        "package": PACKAGE,
        **fields,
    }
    with RECEIPTS.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return row


def find_rish() -> str:
    candidates = [
        os.environ.get("HC_RISH", ""),
        os.environ.get("RISH", ""),
        str(Path.home() / "bin" / "rish"),
        str(Path.home() / "rish"),
        "/storage/emulated/0/Android/data/moe.shizuku.privileged.api/files/rish",
        "/storage/emulated/0/Documents/rish",
        "/storage/emulated/0/Download/rish",
    ]
    path_value = os.environ.get("PATH", "")
    for directory in path_value.split(os.pathsep):
        if directory:
            candidates.append(str(Path(directory) / "rish"))
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            return candidate
    raise RadioError("Shizuku rish is not available")


def run_rish(command: str, timeout: int = COMMAND_TIMEOUT) -> str:
    rish = find_rish()
    process = subprocess.run(
        [rish, "-c", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    if process.returncode:
        detail = (process.stderr or process.stdout or f"rish exit {process.returncode}").strip()
        raise RadioError(detail[-2000:])
    return process.stdout.strip()


def _clean_metadata(value: str) -> str:
    text = str(value or "").strip().strip(",}")
    if text.lower() in {"null", "none", "<null>"}:
        return ""
    return text[:500]


def _metadata_value(segment: str, keys: tuple[str, ...]) -> str:
    patterns = []
    for key in keys:
        escaped = re.escape(key)
        patterns.extend([
            rf"(?im)^\s*{escaped}\s*=\s*(.+?)\s*$",
            rf"(?i)\b{escaped}\s*=\s*([^,\n}}]+)",
            rf"(?i)\b{escaped}\s*:\s*([^,\n}}]+)",
        ])
    for pattern in patterns:
        match = re.search(pattern, segment)
        if match:
            return _clean_metadata(match.group(1))
    return ""


def _session_sections(raw: str) -> list[tuple[str, str]]:
    lines = raw.splitlines()
    starts: list[tuple[int, str]] = []
    header_patterns = [
        re.compile(r"^\s*([A-Za-z0-9_.]+)/(?:[A-Za-z0-9_.$]+).*?(?:\(|$)"),
        re.compile(r"^\s*package\s*=\s*([A-Za-z0-9_.]+)\s*$", re.I),
        re.compile(r"^\s*ownerPackageName\s*=\s*([A-Za-z0-9_.]+)", re.I),
    ]
    for index, line in enumerate(lines):
        package = ""
        for pattern in header_patterns:
            match = pattern.search(line)
            if match:
                package = match.group(1)
                break
        if package:
            starts.append((index, package))
    sections: list[tuple[str, str]] = []
    for offset, (start, package) in enumerate(starts):
        end = starts[offset + 1][0] if offset + 1 < len(starts) else min(len(lines), start + 140)
        sections.append((package, "\n".join(lines[start:end])))
    return sections


def parse_media_session(raw: str) -> dict[str, Any]:
    current_package = ""
    current_patterns = [
        r"(?im)^\s*Media button session is\s+([A-Za-z0-9_.]+)(?:/|\s|$)",
        r"(?im)^\s*mMediaButtonSession\s*=\s*(?:MediaSessionRecord\{[^ ]+\s+)?([A-Za-z0-9_.]+)(?:/|\s|$)",
        r"(?im)^\s*mediaButtonSession\s*=\s*(?:MediaSessionRecord\{[^ ]+\s+)?([A-Za-z0-9_.]+)(?:/|\s|$)",
    ]
    for pattern in current_patterns:
        match = re.search(pattern, raw)
        if match:
            current_package = match.group(1)
            break

    spotify_candidates: list[dict[str, Any]] = []
    playing_packages: list[str] = []
    sections = _session_sections(raw)
    for package, segment in sections:
        active_match = re.search(r"(?i)\bactive\s*=\s*(true|false)", segment)
        active = bool(active_match and active_match.group(1).lower() == "true")
        state_matches = [int(value) for value in re.findall(r"(?i)\bstate\s*=\s*(\d+)", segment)]
        state_value = next((value for value in state_matches if value in PLAYBACK_NAMES), 0)
        if active and state_value == 3 and package not in playing_packages:
            playing_packages.append(package)
        if package == PACKAGE:
            spotify_candidates.append({
                "exists": True,
                "active": active,
                "state": state_value,
                "stateName": PLAYBACK_NAMES.get(state_value, f"unknown_{state_value}"),
                "title": _metadata_value(segment, (
                    "android.media.metadata.TITLE", "title", "displayTitle",
                )),
                "artist": _metadata_value(segment, (
                    "android.media.metadata.ARTIST", "artist", "subtitle",
                )),
                "album": _metadata_value(segment, (
                    "android.media.metadata.ALBUM", "album",
                )),
                "segmentDigest": hashlib.sha256(segment.encode("utf-8", "replace")).hexdigest(),
                "rawPreview": segment[-3000:],
            })

    if not spotify_candidates and PACKAGE in raw:
        index = raw.find(PACKAGE)
        segment = raw[max(0, index - 500):index + 5000]
        state_matches = [int(value) for value in re.findall(r"(?i)\bstate\s*=\s*(\d+)", segment)]
        state_value = next((value for value in state_matches if value in PLAYBACK_NAMES), 0)
        active_match = re.search(r"(?i)\bactive\s*=\s*(true|false)", segment)
        spotify_candidates.append({
            "exists": True,
            "active": bool(active_match and active_match.group(1).lower() == "true"),
            "state": state_value,
            "stateName": PLAYBACK_NAMES.get(state_value, f"unknown_{state_value}"),
            "title": _metadata_value(segment, ("android.media.metadata.TITLE", "title")),
            "artist": _metadata_value(segment, ("android.media.metadata.ARTIST", "artist")),
            "album": _metadata_value(segment, ("android.media.metadata.ALBUM", "album")),
            "segmentDigest": hashlib.sha256(segment.encode("utf-8", "replace")).hexdigest(),
            "rawPreview": segment[-3000:],
        })

    spotify = max(
        spotify_candidates,
        key=lambda row: (
            row.get("active") is True,
            row.get("state") == 3,
            bool(row.get("title")),
        ),
        default={
            "exists": False,
            "active": False,
            "state": 0,
            "stateName": "none",
            "title": "",
            "artist": "",
            "album": "",
            "segmentDigest": "",
            "rawPreview": "",
        },
    )
    competing = [
        package for package in playing_packages
        if package != PACKAGE
    ]
    return {
        "currentPackage": current_package,
        "playingPackages": playing_packages,
        "competingPlayingPackages": competing,
        "spotify": spotify,
        "rawDigest": hashlib.sha256(raw.encode("utf-8", "replace")).hexdigest(),
    }


def parse_call_state(audio_raw: str, telecom_raw: str) -> dict[str, Any]:
    mode_match = re.search(r"(?im)\bmMode\s*=\s*(MODE_[A-Z_]+)", audio_raw)
    audio_mode = mode_match.group(1) if mode_match else ""
    call_markers = [
        r"(?i)\bmIsInCall\s*=\s*true",
        r"(?i)\bmCallState\s*=\s*(?:1|2|RINGING|OFFHOOK|ACTIVE)",
        r"(?i)\bstate\s*=\s*(ACTIVE|RINGING|DIALING|CONNECTING|HOLDING)",
        r"(?i)\bCallAudioModeStateMachine.*?(?:IN_CALL|IN_COMMUNICATION)",
    ]
    telecom_active = any(re.search(pattern, telecom_raw) for pattern in call_markers)
    mode_active = bool(audio_mode and audio_mode not in {"MODE_NORMAL", "MODE_CURRENT"})
    return {
        "active": bool(telecom_active or mode_active),
        "audioMode": audio_mode,
        "telecomDigest": hashlib.sha256(telecom_raw.encode("utf-8", "replace")).hexdigest(),
    }


def package_installed() -> bool:
    output = run_rish(f"pm list packages {shlex.quote(PACKAGE)}")
    return f"package:{PACKAGE}" in output


def session_snapshot() -> dict[str, Any]:
    media_raw = run_rish("dumpsys media_session 2>/dev/null || cmd media_session list-sessions 2>/dev/null || true")
    audio_raw = run_rish("dumpsys audio 2>/dev/null | grep -E 'mMode=|mode:' | head -40 || true")
    telecom_raw = run_rish("dumpsys telecom 2>/dev/null | grep -E 'mIsInCall|mCallState|state =|CallAudioModeStateMachine' | head -100 || true")
    foreground = run_rish("dumpsys window 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp' | head -2 || true")
    return {
        "packageInstalled": package_installed(),
        "media": parse_media_session(media_raw),
        "call": parse_call_state(audio_raw, telecom_raw),
        "foreground": foreground[-1200:],
    }


def _validate_spotify_uri(value: str, *, playlist_only: bool = False) -> str:
    uri = str(value or "").strip()
    if not uri:
        raise ValueError("Spotify URI is required")
    if len(uri) > 4096:
        raise ValueError("Spotify URI is too long")
    if uri.startswith("spotify:"):
        parts = uri.split(":")
        if len(parts) < 3 or parts[1] not in {"playlist", "album", "track", "artist", "show", "episode"}:
            raise ValueError("unsupported Spotify URI")
        if playlist_only and parts[1] != "playlist":
            raise ValueError("playlist URI required")
        return uri
    parsed = urllib.parse.urlparse(uri)
    if parsed.scheme != "https" or parsed.hostname not in {"open.spotify.com", "www.spotify.com"}:
        raise ValueError("Spotify URL must use https://open.spotify.com")
    pieces = [piece for piece in parsed.path.split("/") if piece]
    if not pieces or pieces[0] not in {"playlist", "album", "track", "artist", "show", "episode"}:
        raise ValueError("unsupported Spotify URL")
    if playlist_only and pieces[0] != "playlist":
        raise ValueError("playlist URL required")
    return uri


def set_playlist(uri: str, name: str = "") -> dict[str, Any]:
    clean = _validate_spotify_uri(uri, playlist_only=True)
    state = load_state()
    state.update({
        "playlistUri": clean,
        "playlistName": str(name or state.get("playlistName") or "").strip()[:300],
        "lastExplicitCommand": "set-playlist",
        "lastCommandAtMs": _now_ms(),
    })
    save_state(state)
    return receipt("playlist.set", True, playlistUri=clean, playlistName=state["playlistName"])


def _spotify_is_dispatch_target(snapshot: dict[str, Any], *, allow_inactive: bool = False) -> tuple[bool, str]:
    media = snapshot.get("media") or {}
    spotify = media.get("spotify") or {}
    current = str(media.get("currentPackage") or "")
    competing = list(media.get("competingPlayingPackages") or [])
    if competing:
        return False, "competing_media_session"
    if current and current != PACKAGE:
        return False, f"media_button_session_owned_by:{current}"
    if not spotify.get("exists"):
        return False, "spotify_session_missing"
    if not allow_inactive and not spotify.get("active"):
        return False, "spotify_session_inactive"
    return True, "spotify_verified"


def _overlay_apk_path() -> str:
    command = (
        f"dumpsys package {shlex.quote(OVERLAY_PACKAGE)} 2>/dev/null "
        "| sed -n 's/^[[:space:]]*codePath=//p' | head -1"
    )
    code_path = run_rish(command).strip().splitlines()
    if not code_path:
        raise RadioError("Home Center overlay APK codePath is unavailable")
    candidate = code_path[-1].strip()
    if not candidate:
        raise RadioError("Home Center overlay APK codePath is empty")
    apk = candidate if candidate.endswith(".apk") else candidate.rstrip("/") + "/base.apk"
    verified = run_rish(
        f"test -r {shlex.quote(apk)} && printf '%s' {shlex.quote(apk)}"
    ).strip()
    if verified != apk:
        raise RadioError("Home Center overlay APK is not readable through rish")
    return apk


def _bridge(action: str, uri: str = "") -> dict[str, Any]:
    allowed = {"status", "play", "pause", "toggle", "next", "previous", "stop", "play-uri"}
    clean_action = str(action or "").strip().lower()
    if clean_action not in allowed:
        raise ValueError(f"unsupported Spotify bridge action: {clean_action}")
    clean_uri = ""
    if clean_action == "play-uri":
        clean_uri = _validate_spotify_uri(uri, playlist_only=True)
    elif uri:
        raise ValueError("Spotify URI is valid only for play-uri")

    apk = _overlay_apk_path()
    argv = [clean_action] + ([clean_uri] if clean_uri else [])
    bridge_command = (
        f"CLASSPATH={shlex.quote(apk)} app_process /system/bin "
        f"{shlex.quote(BRIDGE_CLASS)} "
        + " ".join(shlex.quote(value) for value in argv)
    )
    wrapped = bridge_command + '; rc=$?; printf "\\n__HC_RC=%s\\n" "$rc"'
    output = run_rish(wrapped, timeout=45)
    bridge_rc = None
    payload = None
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith("__HC_RC="):
            try:
                bridge_rc = int(stripped.split("=", 1)[1])
            except ValueError:
                bridge_rc = -1
        elif stripped.startswith("{") and stripped.endswith("}"):
            try:
                candidate = json.loads(stripped)
            except ValueError:
                continue
            if isinstance(candidate, dict):
                payload = candidate
    if payload is None:
        raise RadioError("Spotify media bridge returned no JSON receipt")
    if bridge_rc not in {0, None} or payload.get("ok") is not True:
        code = str(payload.get("error") or "SPOTIFY_MEDIA_BRIDGE_FAILED")
        detail = str(payload.get("detail") or "")
        raise RadioError(code + (f": {detail}" if detail else ""))
    if payload.get("targetPackage") != PACKAGE:
        raise RadioError("Spotify media bridge target-package mismatch")
    if payload.get("foregroundLaunchUsed") is not False:
        raise RadioError("Spotify media bridge reported forbidden foreground launch")
    return {
        "ok": True,
        "action": clean_action,
        "uri": clean_uri,
        "apk": apk,
        "command": bridge_command,
        "bridgeExitCode": bridge_rc,
        "result": payload,
        "output": output[-3000:],
    }


def _dispatch_key(key: str, *, allow_inactive: bool = False) -> dict[str, Any]:
    if key not in MEDIA_KEYS:
        raise ValueError(f"unsupported media key: {key}")
    before = session_snapshot()
    allowed, reason = _spotify_is_dispatch_target(before, allow_inactive=allow_inactive)
    if not allowed:
        raise RadioError(reason)
    bridge = _bridge(key)
    time.sleep(0.8 if key in {"play", "pause", "toggle", "stop"} else 1.2)
    after = session_snapshot()
    controlled = bool(
        bridge.get("ok") is True
        and after["media"]["spotify"].get("exists")
        and not after["media"].get("competingPlayingPackages")
        and (not after["media"].get("currentPackage") or after["media"].get("currentPackage") == PACKAGE)
    )
    row = receipt(
        f"media.{key}",
        controlled,
        commandSurface="rish/app_process exact-package MediaController",
        bridge=bridge,
        targetReason=reason,
        before=before,
        after=after,
        spotifyControlled=controlled,
        foregroundLaunchUsed=False,
    )
    if not controlled:
        raise RadioError("Spotify media-session verification failed after dispatch")
    return row


def _update_desired(command: str, *, desired: bool, continuous: bool | None = None) -> dict[str, Any]:
    state = load_state()
    state["desiredPlaying"] = bool(desired)
    if continuous is not None:
        state["continuous"] = bool(continuous)
    state["lastExplicitCommand"] = command
    state["lastCommandAtMs"] = _now_ms()
    return save_state(state)


def play(uri: str = "", *, keep: bool = True) -> dict[str, Any]:
    state = load_state()
    target = uri or str(state.get("playlistUri") or "")
    if target:
        target = _validate_spotify_uri(target, playlist_only=True)
    _update_desired("play", desired=True, continuous=keep or bool(state.get("continuous")))
    before = session_snapshot()
    allowed, reason = _spotify_is_dispatch_target(before, allow_inactive=True)
    if not allowed:
        raise RadioError(reason + "; foreground launch is forbidden")
    bridge = _bridge("play-uri", target) if target else _bridge("play")
    time.sleep(0.9)
    after = session_snapshot()
    after_state = int(after["media"]["spotify"].get("state") or 0)
    ok = bool(
        bridge.get("ok") is True
        and after_state in {3, 6, 8}
        and not after["media"].get("competingPlayingPackages")
    )
    result = receipt(
        "media.play",
        ok,
        commandSurface="rish/app_process exact-package MediaController",
        bridge=bridge,
        targetReason=reason,
        playlistUri=target,
        before=before,
        after=after,
        spotifyControlled=ok,
        foregroundLaunchUsed=False,
    )
    if not ok:
        raise RadioError(f"Spotify did not enter playing/buffering/connecting state: {after_state}")
    if keep:
        ensure_daemon()
    return result


def pause() -> dict[str, Any]:
    _update_desired("pause", desired=False)
    return _dispatch_key("pause")


def stop() -> dict[str, Any]:
    _update_desired("stop", desired=False, continuous=False)
    try:
        return _dispatch_key("stop")
    except RadioError:
        return _dispatch_key("pause")


def toggle() -> dict[str, Any]:
    snapshot = session_snapshot()
    if int(snapshot["media"]["spotify"].get("state") or 0) == 3:
        return pause()
    return play(keep=True)


def next_track() -> dict[str, Any]:
    _update_desired("next", desired=True)
    row = _dispatch_key("next")
    ensure_daemon()
    return row


def previous_track() -> dict[str, Any]:
    _update_desired("previous", desired=True)
    row = _dispatch_key("previous")
    ensure_daemon()
    return row


def status() -> dict[str, Any]:
    state = load_state()
    snapshot = session_snapshot()
    pid = 0
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            pid = 0
    daemon_running = bool(pid and Path(f"/proc/{pid}").exists())
    spotify = snapshot["media"]["spotify"]
    return {
        "schema": "home-center.spotify-radio-status.v1",
        "ok": True,
        "package": PACKAGE,
        "state": state,
        "snapshot": snapshot,
        "daemon": {
            "pid": pid or None,
            "running": daemon_running,
            "intervalSeconds": DEFAULT_INTERVAL,
        },
        "response": (
            f"Spotify Radio: {spotify.get('stateName', 'none')}"
            + (f" — {spotify.get('title')}" if spotify.get("title") else "")
            + (f" by {spotify.get('artist')}" if spotify.get("artist") else "")
            + ("; keep rolling is on" if state.get("continuous") else "; keep rolling is off")
        ),
    }


def doctor() -> dict[str, Any]:
    try:
        rish = find_rish()
        identity = run_rish("id")
        apk = _overlay_apk_path()
        snapshot = session_snapshot()
        session_observed = bool(snapshot["media"]["spotify"].get("exists"))
        bridge_probe: dict[str, Any]
        if session_observed:
            try:
                bridge_probe = _bridge("status")
            except Exception as exc:
                bridge_probe = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
        else:
            bridge_probe = {
                "ok": False,
                "error": "SPOTIFY_SESSION_ABSENT",
                "foregroundLaunchUsed": False,
            }
        ok = bool(snapshot.get("packageInstalled") and apk)
        return {
            "schema": "home-center.spotify-radio-doctor.v1",
            "ok": ok,
            "rish": rish,
            "identity": identity,
            "overlayApk": apk,
            "packageInstalled": snapshot.get("packageInstalled"),
            "spotifySessionObserved": session_observed,
            "bridgeProbe": bridge_probe,
            "commandSurface": "rish/app_process exact-package MediaController",
            "foregroundLaunchUsed": False,
            "systemTtsUsed": False,
            "cloudUsed": False,
            "snapshot": snapshot,
            "response": (
                "Spotify Radio bridge ready."
                if ok and session_observed and bridge_probe.get("ok") is True
                else "Spotify Radio installed; waiting for an existing Spotify media session."
                if ok
                else "Spotify or Home Center overlay is not installed."
            ),
        }
    except Exception as exc:
        return {
            "schema": "home-center.spotify-radio-doctor.v1",
            "ok": False,
            "foregroundLaunchUsed": False,
            "error": f"{type(exc).__name__}: {exc}",
            "response": f"Spotify Radio doctor failed: {exc}",
        }


def _pid_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return False
    return Path(f"/proc/{pid}").exists()


def ensure_daemon() -> dict[str, Any]:
    _mkdirs()
    state = load_state()
    if not state.get("continuous"):
        return {"ok": True, "started": False, "reason": "continuous_disabled"}
    if _pid_running():
        return {"ok": True, "started": False, "reason": "already_running"}
    log = LOG_FILE.open("ab", buffering=0)
    process = subprocess.Popen(
        [sys.executable, str(Path(__file__).resolve()), "daemon"],
        stdout=log,
        stderr=log,
        start_new_session=True,
    )
    time.sleep(0.2)
    return {
        "ok": _pid_running() or process.poll() is None,
        "started": True,
        "pid": process.pid,
    }


def keep_on() -> dict[str, Any]:
    state = _update_desired("keep-on", desired=True, continuous=True)
    daemon = ensure_daemon()
    return receipt("keep.on", bool(daemon.get("ok")), state=state, daemon=daemon)


def keep_off() -> dict[str, Any]:
    state = _update_desired("keep-off", desired=False, continuous=False)
    return receipt("keep.off", True, state=state)


def _should_recover(state: dict[str, Any], snapshot: dict[str, Any], now_ms: int) -> tuple[bool, str]:
    if not state.get("continuous") or not state.get("desiredPlaying"):
        return False, "not_requested"
    if snapshot["call"].get("active"):
        return False, "call_active"
    media = snapshot["media"]
    if media.get("competingPlayingPackages"):
        return False, "competing_media"
    current = str(media.get("currentPackage") or "")
    if current and current != PACKAGE:
        return False, "other_media_button_session"
    spotify = media.get("spotify") or {}
    if int(spotify.get("state") or 0) in {3, 6, 8}:
        return False, "spotify_healthy"
    last_attempt = int(state.get("lastRecoveryAttemptAtMs") or 0)
    if now_ms - last_attempt < 45000:
        return False, "recovery_cooldown"
    return True, "spotify_not_playing"


def keepalive_once() -> dict[str, Any]:
    state = load_state()
    snapshot = session_snapshot()
    recover, reason = _should_recover(state, snapshot, _now_ms())
    if not recover:
        return receipt(
            "keepalive.observe",
            True,
            action="yield",
            reason=reason,
            snapshot=snapshot,
            foregroundLaunchUsed=False,
        )
    if not snapshot["media"]["spotify"].get("exists"):
        return receipt(
            "keepalive.observe",
            True,
            action="yield",
            reason="spotify_session_missing_background_only",
            snapshot=snapshot,
            foregroundLaunchUsed=False,
        )
    state["lastRecoveryAttemptAtMs"] = _now_ms()
    save_state(state)
    playlist_uri = str(state.get("playlistUri") or "")
    try:
        if playlist_uri:
            playlist_uri = _validate_spotify_uri(playlist_uri, playlist_only=True)
            bridge = _bridge("play-uri", playlist_uri)
        else:
            bridge = _bridge("play")
        time.sleep(0.9)
        after = session_snapshot()
        after_state = int(after["media"]["spotify"].get("state") or 0)
        ok = bool(
            bridge.get("ok") is True
            and after_state in {3, 6, 8}
            and not after["media"].get("competingPlayingPackages")
        )
        return receipt(
            "keepalive.recover",
            ok,
            reason=reason,
            playlistUri=playlist_uri,
            playbackState=after_state,
            bridge=bridge,
            before=snapshot,
            after=after,
            foregroundLaunchUsed=False,
        )
    except Exception as exc:
        return receipt(
            "keepalive.recover",
            False,
            reason=reason,
            error=f"{type(exc).__name__}: {exc}",
            playlistUri=playlist_uri,
            foregroundLaunchUsed=False,
        )


def daemon() -> int:
    _mkdirs()
    PID_FILE.write_text(str(os.getpid()) + "\n", encoding="utf-8")

    def stop_signal(_signum: int, _frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, stop_signal)
    signal.signal(signal.SIGINT, stop_signal)
    receipt("daemon.start", True, pid=os.getpid(), intervalSeconds=DEFAULT_INTERVAL)
    try:
        while True:
            state = load_state()
            if not state.get("continuous"):
                break
            keepalive_once()
            time.sleep(DEFAULT_INTERVAL)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            PID_FILE.unlink()
        except OSError:
            pass
        receipt("daemon.stop", True, pid=os.getpid())
    return 0


def compile_prompt(text: str) -> tuple[str, dict[str, Any]]:
    raw = " ".join(str(text or "").strip().lower().split())
    if not raw:
        raise ValueError("radio prompt is empty")
    if raw in PROMPT_ALIASES:
        return PROMPT_ALIASES[raw], {}
    for prefix in ("radio ", "spotify ", "spotify radio "):
        if raw.startswith(prefix):
            remainder = raw[len(prefix):].strip()
            if remainder in PROMPT_ALIASES:
                return PROMPT_ALIASES[remainder], {}
            raw = remainder
            break
    if raw.startswith("playlist "):
        value = str(text).strip().split(None, 1)[1]
        return "set-playlist", {"uri": value}
    if raw.startswith("play "):
        value = str(text).strip().split(None, 1)[1]
        if value.startswith("spotify:") or value.startswith("https://open.spotify.com/"):
            return "play", {"uri": value}
    raise ValueError(
        "Unsupported radio prompt. Use play, pause, next, previous, stop, status, "
        "keep on/off, playlist <Spotify URL>, or play <Spotify URL>."
    )


def execute_prompt(text: str) -> dict[str, Any]:
    command, args = compile_prompt(text)
    if command == "play":
        result = play(args.get("uri", ""), keep=True)
    elif command == "pause":
        result = pause()
    elif command == "toggle":
        result = toggle()
    elif command == "next":
        result = next_track()
    elif command == "previous":
        result = previous_track()
    elif command == "stop":
        result = stop()
    elif command == "status":
        result = status()
    elif command == "doctor":
        result = doctor()
    elif command == "keep-on":
        result = keep_on()
    elif command == "keep-off":
        result = keep_off()
    elif command == "set-playlist":
        result = set_playlist(args["uri"])
    else:
        raise ValueError(command)
    if "response" not in result:
        current = status()
        result = {
            **result,
            "response": current["response"],
        }
    return result


def emit(value: dict[str, Any]) -> int:
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0 if value.get("ok") is not False else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="spotify-radio")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("status")
    play_parser = sub.add_parser("play")
    play_parser.add_argument("uri", nargs="?", default="")
    for name in ("pause", "toggle", "next", "previous", "stop", "keep-on", "keep-off", "ensure", "once", "daemon"):
        sub.add_parser(name)
    set_parser = sub.add_parser("set-playlist")
    set_parser.add_argument("uri")
    set_parser.add_argument("--name", default="")
    prompt_parser = sub.add_parser("prompt")
    prompt_parser.add_argument("text", nargs="+")
    args = parser.parse_args(argv)

    try:
        if args.command == "doctor":
            return emit(doctor())
        if args.command == "status":
            return emit(status())
        if args.command == "play":
            return emit(play(args.uri, keep=True))
        if args.command == "pause":
            return emit(pause())
        if args.command == "toggle":
            return emit(toggle())
        if args.command == "next":
            return emit(next_track())
        if args.command == "previous":
            return emit(previous_track())
        if args.command == "stop":
            return emit(stop())
        if args.command == "keep-on":
            return emit(keep_on())
        if args.command == "keep-off":
            return emit(keep_off())
        if args.command == "ensure":
            return emit(ensure_daemon())
        if args.command == "once":
            return emit(keepalive_once())
        if args.command == "daemon":
            return daemon()
        if args.command == "set-playlist":
            return emit(set_playlist(args.uri, args.name))
        if args.command == "prompt":
            return emit(execute_prompt(" ".join(args.text)))
        raise ValueError(args.command)
    except Exception as exc:
        result = receipt(
            f"command.{args.command}",
            False,
            error=f"{type(exc).__name__}: {exc}",
        )
        result["response"] = f"Spotify Radio failed: {exc}"
        return emit(result)


if __name__ == "__main__":
    raise SystemExit(main())
