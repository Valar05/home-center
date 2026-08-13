#!/data/data/com.termux/files/usr/bin/python
"""Deterministic Spotify radio control for the Home Center Android body.

This controller uses the installed Spotify Android app and its Android media
session. It never handles Spotify credentials, never calls the Spotify Web API,
and never treats a generic media-key exit code as playback proof.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from android_phone_hands_bridge import run_rish

PACKAGE = "com.spotify.music"
DEFAULT_PLAYLIST_NAME = "Fortress Radio — Rolling Forge"
DEFAULT_SEED_QUERY = "Battles Alpine Universe"
STATE_ROOT = Path(os.environ.get("HC_SPOTIFY_RADIO_STATE", "~/.local/state/home-center/spotify-radio")).expanduser()
CONFIG_PATH = STATE_ROOT / "config.json"
RECEIPTS_PATH = STATE_ROOT / "receipts.jsonl"
LAST_PATH = STATE_ROOT / "last.json"
MONITOR_PID_PATH = STATE_ROOT / "monitor.pid"
MONITOR_INTERVAL_SECONDS = max(5, int(os.environ.get("HC_SPOTIFY_RADIO_MONITOR_SECONDS", "20")))
RECOVERY_GRACE_SECONDS = max(10, int(os.environ.get("HC_SPOTIFY_RADIO_RECOVERY_GRACE_SECONDS", "45")))
SESSION_STATES = {0: "NONE", 1: "STOPPED", 2: "PAUSED", 3: "PLAYING", 4: "FAST_FORWARDING", 5: "REWINDING", 6: "BUFFERING", 7: "ERROR", 8: "CONNECTING", 9: "SKIPPING_TO_PREVIOUS", 10: "SKIPPING_TO_NEXT", 11: "SKIPPING_TO_QUEUE_ITEM"}
PLAYING_STATES = {"PLAYING", "BUFFERING", "CONNECTING", "SKIPPING_TO_PREVIOUS", "SKIPPING_TO_NEXT", "SKIPPING_TO_QUEUE_ITEM"}
INACTIVE_STATES = {"NONE", "STOPPED", "ERROR"}


@dataclass(frozen=True)
class PromptAction:
    action: str
    value: str = ""


def now_ms() -> int:
    return int(time.time() * 1000)


def default_config() -> dict[str, Any]:
    return {
        "schema": "home-center.spotify-radio.config.v1",
        "playlistName": DEFAULT_PLAYLIST_NAME,
        "playlistUri": "",
        "seedQuery": DEFAULT_SEED_QUERY,
        "enabled": False,
        "suspended": True,
        "lastVerifiedPlayingAtMs": 0,
        "lastActionAtMs": 0,
        "lastAction": "",
        "lastQuery": "",
    }


def ensure_state() -> None:
    STATE_ROOT.mkdir(parents=True, exist_ok=True)


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    ensure_state()
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def load_config() -> dict[str, Any]:
    base = default_config()
    if CONFIG_PATH.is_file():
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                base.update(loaded)
        except Exception:
            pass
    return base


def save_config(config: dict[str, Any]) -> None:
    clean = default_config()
    clean.update(config)
    clean["schema"] = "home-center.spotify-radio.config.v1"
    atomic_json(CONFIG_PATH, clean)


def write_receipt(kind: str, ok: bool, **fields: Any) -> dict[str, Any]:
    ensure_state()
    receipt = {
        "schema": "home-center.spotify-radio.receipt.v1",
        "kind": kind,
        "ok": bool(ok),
        "provider": "spotify-android",
        "package": PACKAGE,
        "observedAtMs": now_ms(),
        **fields,
    }
    with RECEIPTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")
    atomic_json(LAST_PATH, receipt)
    return receipt


def android(command: str, timeout: float = 25) -> str:
    return str(run_rish(command, timeout=timeout)).strip()


def package_probe() -> dict[str, Any]:
    packages = android("cmd package list packages 2>/dev/null | grep -Fx 'package:com.spotify.music' || true")
    resolved = android("cmd package resolve-activity --brief -a android.intent.action.MAIN -c android.intent.category.LAUNCHER com.spotify.music 2>/dev/null | tail -1 || true")
    version_raw = android("dumpsys package com.spotify.music 2>/dev/null | grep -E 'versionName=|versionCode=' | head -4 || true")
    installed = "package:com.spotify.music" in packages and bool(resolved)
    return {"installed": installed, "resolvedActivity": resolved, "versionRaw": version_raw}


def launch_spotify() -> dict[str, Any]:
    probe = package_probe()
    if not probe["installed"]:
        raise RuntimeError("Spotify Android is not installed or its launcher activity cannot be resolved.")
    component = str(probe["resolvedActivity"]).splitlines()[-1].strip()
    launch = android(f"am start -W -n {shlex.quote(component)}", timeout=35)
    return {**probe, "launch": launch, "component": component}


def spotify_session_block(raw: str) -> str:
    lines = str(raw or "").splitlines()
    start = -1
    indent = 0
    for index, line in enumerate(lines):
        if "spotify-media-session" in line and PACKAGE in line:
            start = index
            indent = len(line) - len(line.lstrip())
            break
    if start < 0:
        return ""
    selected: list[str] = []
    for index in range(start, len(lines)):
        line = lines[index]
        if index > start and line.strip() and (len(line) - len(line.lstrip())) <= indent and "spotify-media-session" not in line:
            break
        selected.append(line)
    return "\n".join(selected)


def metadata_value(block: str, key: str) -> str:
    patterns = [
        rf"android\.media\.metadata\.{re.escape(key)}=([^,\n}}]+)",
        rf"\b{re.escape(key.lower())}=([^,\n}}]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, block, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().strip("'\"")[:500]
    return ""


def parse_session(raw: str) -> dict[str, Any]:
    block = spotify_session_block(raw)
    if not block:
        return {"found": False, "package": PACKAGE, "state": "NONE", "stateCode": 0, "raw": ""}
    state_name = "NONE"
    state_code = 0
    match = re.search(r"state=PlaybackState\s*\{state=([A-Z_]+)\((\d+)\)", block)
    if match:
        state_name = match.group(1).upper()
        state_code = int(match.group(2))
    else:
        match = re.search(r"state=PlaybackState\s*\{state=(\d+)", block)
        if match:
            state_code = int(match.group(1))
            state_name = SESSION_STATES.get(state_code, f"UNKNOWN_{state_code}")
    position = 0
    position_match = re.search(r"\bposition=(-?\d+)", block)
    if position_match:
        position = int(position_match.group(1))
    title = metadata_value(block, "TITLE")
    artist = metadata_value(block, "ARTIST") or metadata_value(block, "ALBUM_ARTIST")
    album = metadata_value(block, "ALBUM")
    description = ""
    desc_match = re.search(r"\bdescription=([^\n]+)", block, flags=re.IGNORECASE)
    if desc_match:
        description = desc_match.group(1).strip()[:1000]
    return {
        "found": True,
        "package": PACKAGE,
        "state": state_name,
        "stateCode": state_code,
        "positionMs": position,
        "title": title,
        "artist": artist,
        "album": album,
        "description": description,
        "raw": block[-16000:],
    }


def read_session() -> dict[str, Any]:
    raw = android("dumpsys media_session 2>/dev/null", timeout=30)
    return parse_session(raw)


def wait_for_session(predicate, timeout_seconds: float = 8.0, interval: float = 0.5) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last = read_session()
    while time.monotonic() < deadline:
        if predicate(last):
            return last
        time.sleep(interval)
        last = read_session()
    return last


def ensure_session() -> dict[str, Any]:
    session = read_session()
    if session.get("found"):
        return session
    launch_spotify()
    return wait_for_session(lambda value: bool(value.get("found")), timeout_seconds=6.0)


def update_action_config(action: str, *, enabled: bool | None = None, suspended: bool | None = None, query: str = "", session: dict[str, Any] | None = None) -> dict[str, Any]:
    config = load_config()
    config["lastAction"] = action
    config["lastActionAtMs"] = now_ms()
    if enabled is not None:
        config["enabled"] = enabled
    if suspended is not None:
        config["suspended"] = suspended
    if query:
        config["lastQuery"] = query
    if session and session.get("state") in PLAYING_STATES:
        config["lastVerifiedPlayingAtMs"] = now_ms()
    save_config(config)
    return config


def result_response(prefix: str, session: dict[str, Any]) -> str:
    parts = [prefix]
    if session.get("title"):
        parts.append(str(session["title"]))
    if session.get("artist"):
        parts.append(f"by {session['artist']}")
    parts.append(f"[{session.get('state', 'UNKNOWN')}]")
    return " ".join(parts)


def send_media_key(key: str, expected_states: set[str] | None = None, timeout_seconds: float = 6.0) -> dict[str, Any]:
    before = ensure_session()
    if not before.get("found"):
        raise RuntimeError("Spotify did not expose an Android media session.")
    android(f"input keyevent {shlex.quote(key)}")
    if expected_states:
        after = wait_for_session(lambda value: value.get("state") in expected_states, timeout_seconds=timeout_seconds)
    else:
        time.sleep(0.8)
        after = read_session()
    return {"before": before, "after": after, "key": key}


def play_query(query: str, *, action_name: str = "play_query") -> dict[str, Any]:
    clean = " ".join(str(query or "").split())[:500]
    if not clean:
        raise ValueError("A non-empty Spotify search query is required.")
    probe = package_probe()
    if not probe["installed"]:
        raise RuntimeError("Spotify Android is not installed.")
    intent = android(
        "am start -W -a android.media.action.MEDIA_PLAY_FROM_SEARCH "
        f"--es query {shlex.quote(clean)} -p {shlex.quote(PACKAGE)}",
        timeout=40,
    )
    session = wait_for_session(lambda value: value.get("state") in PLAYING_STATES, timeout_seconds=10.0)
    verified = session.get("found") is True and session.get("state") in PLAYING_STATES
    config = update_action_config(action_name, enabled=True, suspended=False, query=clean, session=session)
    receipt = write_receipt(action_name, verified, query=clean, intent=intent[-4000:], session=session, config=config, playbackVerified=verified)
    return {"ok": verified, "action": action_name, "response": result_response("Spotify playing", session) if verified else f"Spotify search dispatched but playback is {session.get('state', 'unverified')}.", "receipt": receipt}


def play_uri(uri: str, *, action_name: str = "play_playlist") -> dict[str, Any]:
    clean = str(uri or "").strip()[:1200]
    if not re.fullmatch(r"spotify:(?:playlist|album|track|artist):[A-Za-z0-9]+", clean) and not re.fullmatch(r"https://open\.spotify\.com/(?:playlist|album|track|artist)/[A-Za-z0-9]+(?:\?.*)?", clean):
        raise ValueError("playlistUri must be a Spotify playlist/album/track/artist URI or open.spotify.com URL.")
    launch = android(f"am start -W -a android.intent.action.VIEW -d {shlex.quote(clean)} -p {shlex.quote(PACKAGE)}", timeout=40)
    time.sleep(2.0)
    keyed = send_media_key("KEYCODE_MEDIA_PLAY", expected_states=PLAYING_STATES, timeout_seconds=8.0)
    session = keyed["after"]
    verified = session.get("state") in PLAYING_STATES
    config = update_action_config(action_name, enabled=True, suspended=False, session=session)
    receipt = write_receipt(action_name, verified, uri=clean, launch=launch[-4000:], session=session, config=config, playbackVerified=verified)
    return {"ok": verified, "action": action_name, "response": result_response("Spotify playlist playing", session) if verified else f"Spotify playlist opened but playback is {session.get('state', 'unverified')}.", "receipt": receipt}


def start_radio() -> dict[str, Any]:
    config = load_config()
    uri = str(config.get("playlistUri") or "").strip()
    if uri:
        return play_uri(uri, action_name="start_radio")
    return play_query(str(config.get("seedQuery") or DEFAULT_SEED_QUERY), action_name="start_radio")


def resume_radio() -> dict[str, Any]:
    session = ensure_session()
    if session.get("state") in PLAYING_STATES:
        config = update_action_config("resume", enabled=True, suspended=False, session=session)
        receipt = write_receipt("resume", True, noOp=True, session=session, config=config, playbackVerified=True)
        return {"ok": True, "action": "resume", "response": result_response("Spotify already playing", session), "receipt": receipt}
    keyed = send_media_key("KEYCODE_MEDIA_PLAY", expected_states=PLAYING_STATES, timeout_seconds=8.0)
    after = keyed["after"]
    verified = after.get("state") in PLAYING_STATES
    config = update_action_config("resume", enabled=True, suspended=False, session=after)
    receipt = write_receipt("resume", verified, before=keyed["before"], session=after, config=config, playbackVerified=verified)
    return {"ok": verified, "action": "resume", "response": result_response("Spotify resumed", after) if verified else f"Spotify resume is {after.get('state', 'unverified')}.", "receipt": receipt}


def pause_radio() -> dict[str, Any]:
    session = ensure_session()
    if session.get("state") == "PAUSED":
        config = update_action_config("pause", suspended=True, session=session)
        receipt = write_receipt("pause", True, noOp=True, session=session, config=config, explicitHumanPause=True)
        return {"ok": True, "action": "pause", "response": result_response("Spotify paused", session), "receipt": receipt}
    keyed = send_media_key("KEYCODE_MEDIA_PAUSE", expected_states={"PAUSED", "STOPPED"}, timeout_seconds=6.0)
    after = keyed["after"]
    verified = after.get("state") in {"PAUSED", "STOPPED"}
    config = update_action_config("pause", suspended=True, session=after)
    receipt = write_receipt("pause", verified, before=keyed["before"], session=after, config=config, explicitHumanPause=True)
    return {"ok": verified, "action": "pause", "response": result_response("Spotify paused", after), "receipt": receipt}


def stop_radio() -> dict[str, Any]:
    try:
        keyed = send_media_key("KEYCODE_MEDIA_PAUSE", expected_states={"PAUSED", "STOPPED"}, timeout_seconds=5.0)
        session = keyed["after"]
    except Exception:
        session = read_session()
    config = update_action_config("stop", enabled=False, suspended=True, session=session)
    receipt = write_receipt("stop", True, session=session, config=config, explicitStop=True, monitorRecoveryForbidden=True)
    return {"ok": True, "action": "stop", "response": result_response("Fortress Radio stopped", session), "receipt": receipt}


def track_identity(session: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(session.get("title") or ""),
        str(session.get("artist") or ""),
        str(session.get("album") or ""),
    )


def track_change_verified(before: dict[str, Any], after: dict[str, Any]) -> bool:
    if after.get("found") is not True:
        return False
    before_identity = track_identity(before)
    after_identity = track_identity(after)
    if any(before_identity) and any(after_identity) and before_identity != after_identity:
        return True
    before_position = int(before.get("positionMs") or 0)
    after_position = int(after.get("positionMs") or 0)
    return before_position >= 5000 and 0 <= after_position < before_position - 3000


def skip_track(direction: str) -> dict[str, Any]:
    key = "KEYCODE_MEDIA_NEXT" if direction == "next" else "KEYCODE_MEDIA_PREVIOUS"
    before = ensure_session()
    send_media_key(key, timeout_seconds=2.0)
    after = wait_for_session(lambda value: track_change_verified(before, value), timeout_seconds=8.0)
    verified = track_change_verified(before, after)
    config = update_action_config(direction, enabled=True, suspended=False, session=after)
    receipt = write_receipt(
        direction,
        verified,
        before=before,
        session=after,
        config=config,
        spotifySessionOwned=after.get("found") is True,
        trackChangeVerified=verified,
    )
    response = result_response(f"Spotify {direction}", after) if verified else f"Spotify {direction} was dispatched, but a track change was not verified."
    return {"ok": verified, "action": direction, "response": response, "receipt": receipt}


def toggle_radio() -> dict[str, Any]:
    session = read_session()
    return pause_radio() if session.get("state") in PLAYING_STATES else resume_radio()


def status_result() -> dict[str, Any]:
    config = load_config()
    probe = package_probe()
    session = read_session()
    ok = bool(probe.get("installed"))
    receipt = write_receipt("status", ok, packageProbe=probe, session=session, config=config)
    response = result_response("Spotify", session)
    response += f" radio={'on' if config.get('enabled') else 'off'} suspended={'yes' if config.get('suspended') else 'no'}"
    return {"ok": ok, "action": "status", "response": response, "receipt": receipt}


def doctor_result() -> dict[str, Any]:
    probe = package_probe()
    session = read_session()
    ready = bool(probe.get("installed"))
    receipt = write_receipt("doctor", ready, packageProbe=probe, session=session, credentialHandling="none", webApiUsed=False)
    return {"ok": ready, "action": "doctor", "response": "Spotify Android radio body is ready." if ready else "Spotify Android radio body is not ready.", "receipt": receipt}


def configure_result(playlist_name: str | None, playlist_uri: str | None, seed_query: str | None) -> dict[str, Any]:
    config = load_config()
    if playlist_name is not None:
        config["playlistName"] = " ".join(playlist_name.split())[:240] or DEFAULT_PLAYLIST_NAME
    if playlist_uri is not None:
        clean = playlist_uri.strip()
        if clean and not re.fullmatch(r"spotify:playlist:[A-Za-z0-9]+", clean) and not re.fullmatch(r"https://open\.spotify\.com/playlist/[A-Za-z0-9]+(?:\?.*)?", clean):
            raise ValueError("playlistUri must identify a Spotify playlist.")
        config["playlistUri"] = clean
    if seed_query is not None:
        config["seedQuery"] = " ".join(seed_query.split())[:500] or DEFAULT_SEED_QUERY
    save_config(config)
    receipt = write_receipt("configure", True, config=config)
    return {"ok": True, "action": "configure", "response": f"Fortress Radio configured: {config['playlistName']}.", "receipt": receipt}


def monitor_decision(config: dict[str, Any], session: dict[str, Any], current_ms: int | None = None) -> str:
    current = now_ms() if current_ms is None else int(current_ms)
    if not config.get("enabled"):
        return "disabled"
    if config.get("suspended"):
        return "suspended"
    state = str(session.get("state") or "NONE")
    if state == "PAUSED":
        return "respect_pause"
    if state in PLAYING_STATES:
        return "healthy"
    last_verified = int(config.get("lastVerifiedPlayingAtMs") or 0)
    if state in INACTIVE_STATES and last_verified > 0 and current - last_verified >= RECOVERY_GRACE_SECONDS * 1000:
        return "recover"
    return "observe"


def monitor_once() -> dict[str, Any]:
    config = load_config()
    session = read_session()
    decision = monitor_decision(config, session)
    if decision == "recover":
        result = start_radio()
        receipt = write_receipt("monitor_recover", result.get("ok") is True, priorSession=session, recovery=result.get("receipt"), decision=decision)
        return {"ok": result.get("ok") is True, "action": "monitor", "response": "Fortress Radio recovered Spotify playback." if result.get("ok") else "Fortress Radio recovery failed.", "receipt": receipt}
    receipt = write_receipt("monitor_observe", True, session=session, config=config, decision=decision, autoResumeAttempted=False)
    return {"ok": True, "action": "monitor", "response": f"Fortress Radio monitor: {decision}.", "receipt": receipt}


def monitor_loop() -> int:
    ensure_state()
    MONITOR_PID_PATH.write_text(str(os.getpid()) + "\n", encoding="utf-8")
    write_receipt("monitor_start", True, pid=os.getpid(), intervalSeconds=MONITOR_INTERVAL_SECONDS)
    try:
        while True:
            try:
                monitor_once()
            except Exception as exc:
                write_receipt("monitor_error", False, error=f"{type(exc).__name__}: {exc}")
            time.sleep(MONITOR_INTERVAL_SECONDS)
    finally:
        try:
            if MONITOR_PID_PATH.read_text(encoding="utf-8").strip() == str(os.getpid()):
                MONITOR_PID_PATH.unlink()
        except Exception:
            pass


def normalize_prompt(text: str) -> str:
    return " ".join(str(text or "").strip().split())


def parse_prompt(text: str) -> PromptAction:
    original = normalize_prompt(text)
    lower = original.lower()
    if not lower:
        return PromptAction("status")
    if lower in {"status", "radio status", "spotify status", "what is playing", "what's playing", "whats playing", "now playing"} or "what is playing" in lower or "what's playing" in lower:
        return PromptAction("status")
    if lower in {"toggle", "play pause", "play/pause"}:
        return PromptAction("toggle")
    if re.search(r"\b(next|skip|skip this|next track|skip track)\b", lower):
        return PromptAction("next")
    if re.search(r"\b(previous|previous track|go back|last track)\b", lower):
        return PromptAction("previous")
    if re.search(r"\b(stop radio|radio off|stop spotify|turn (?:the )?radio off|disable radio)\b", lower) or lower == "stop":
        return PromptAction("stop")
    if re.search(r"\b(pause|hold the music|pause spotify|pause radio)\b", lower):
        return PromptAction("pause")
    if re.search(r"\b(resume|continue playing|unpause|resume spotify|resume radio)\b", lower):
        return PromptAction("resume")
    if re.search(r"\b(start radio|radio on|keep (?:it )?rolling|start fortress radio|play the playlist|play fortress radio)\b", lower):
        return PromptAction("start")
    query = original
    query = re.sub(r"(?i)^\s*(?:adam[, :]*)?(?:spotify|radio)[, :]*(?:please\s+)?play\s+", "", query)
    query = re.sub(r"(?i)^\s*(?:adam[, :]*)?play\s+", "", query)
    query = re.sub(r"(?i)\s+(?:on\s+)?spotify\s*$", "", query)
    query = normalize_prompt(query)
    if query and query.lower() != lower or re.match(r"(?i)^\s*(?:adam[, :]*)?(?:spotify|radio)?[, :]*(?:please\s+)?play\b", original):
        return PromptAction("play", query)
    return PromptAction("unsupported", original)


def execute_prompt(text: str) -> dict[str, Any]:
    parsed = parse_prompt(text)
    if parsed.action == "status":
        return status_result()
    if parsed.action == "toggle":
        return toggle_radio()
    if parsed.action == "next":
        return skip_track("next")
    if parsed.action == "previous":
        return skip_track("previous")
    if parsed.action == "stop":
        return stop_radio()
    if parsed.action == "pause":
        return pause_radio()
    if parsed.action == "resume":
        return resume_radio()
    if parsed.action == "start":
        return start_radio()
    if parsed.action == "play":
        return play_query(parsed.value)
    receipt = write_receipt("prompt_rejected", False, prompt=parsed.value, failureKind="unsupported_radio_prompt")
    return {"ok": False, "action": "unsupported", "failureKind": "unsupported_radio_prompt", "response": "Try: play Battles by Alpine Universe on Spotify; pause; next; previous; keep it rolling; radio status; stop radio.", "receipt": receipt}


def emit(result: dict[str, Any]) -> int:
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") is True else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fortress-radio", description="Promptable Spotify radio controller for Home Center")
    sub = parser.add_subparsers(dest="command", required=True)
    prompt = sub.add_parser("prompt")
    prompt.add_argument("text", nargs="?", default="")
    prompt.add_argument("--mode", default="radio")
    play = sub.add_parser("play")
    play.add_argument("query", nargs="+")
    for name in ("start", "resume", "pause", "toggle", "next", "previous", "stop", "status", "doctor", "monitor-once", "monitor"):
        sub.add_parser(name)
    configure = sub.add_parser("configure")
    configure.add_argument("--playlist-name")
    configure.add_argument("--playlist-uri")
    configure.add_argument("--seed-query")
    args = parser.parse_args(argv)
    try:
        if args.command == "prompt":
            return emit(execute_prompt(args.text))
        if args.command == "play":
            return emit(play_query(" ".join(args.query)))
        if args.command == "start":
            return emit(start_radio())
        if args.command == "resume":
            return emit(resume_radio())
        if args.command == "pause":
            return emit(pause_radio())
        if args.command == "toggle":
            return emit(toggle_radio())
        if args.command == "next":
            return emit(skip_track("next"))
        if args.command == "previous":
            return emit(skip_track("previous"))
        if args.command == "stop":
            return emit(stop_radio())
        if args.command == "status":
            return emit(status_result())
        if args.command == "doctor":
            return emit(doctor_result())
        if args.command == "configure":
            return emit(configure_result(args.playlist_name, args.playlist_uri, args.seed_query))
        if args.command == "monitor-once":
            return emit(monitor_once())
        if args.command == "monitor":
            return monitor_loop()
    except Exception as exc:
        receipt = write_receipt("command_failed", False, command=args.command, error=f"{type(exc).__name__}: {exc}")
        return emit({"ok": False, "action": args.command, "failureKind": "spotify_radio_command_failed", "response": str(exc), "receipt": receipt})
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
