#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

TARGET = Path("tools/spotify_radio.py")


class PatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


OLD_CONSTANT = 'PACKAGE = "com.spotify.music"\n'
NEW_CONSTANT = '''PACKAGE = "com.spotify.music"
OVERLAY_PACKAGE = "com.homecenter.operatoroverlay"
BRIDGE_CLASS = "com.homecenter.operatoroverlay.SpotifyMediaBridge"
'''

OLD_DISPATCH_AND_LAUNCH = '''def _dispatch_key(key: str, *, allow_inactive: bool = False) -> dict[str, Any]:
    if key not in MEDIA_KEYS:
        raise ValueError(f"unsupported media key: {key}")
    before = session_snapshot()
    allowed, reason = _spotify_is_dispatch_target(before, allow_inactive=allow_inactive)
    if not allowed:
        raise RadioError(reason)
    command = f"cmd media_session dispatch {shlex.quote(MEDIA_KEYS[key])}"
    output = run_rish(command)
    time.sleep(0.8 if key in {"play", "pause", "toggle", "stop"} else 1.2)
    after = session_snapshot()
    controlled = bool(
        (after["media"]["spotify"].get("exists"))
        and not after["media"].get("competingPlayingPackages")
        and (not after["media"].get("currentPackage") or after["media"].get("currentPackage") == PACKAGE)
    )
    row = receipt(
        f"media.{key}",
        controlled,
        command=command,
        output=output[-1000:],
        targetReason=reason,
        before=before,
        after=after,
        spotifyControlled=controlled,
    )
    if not controlled:
        raise RadioError("Spotify media-session verification failed after dispatch")
    return row


def _launch(uri: str = "") -> dict[str, Any]:
    target = _validate_spotify_uri(uri) if uri else ""
    if target:
        command = (
            "am start -W -a android.intent.action.VIEW "
            f"-d {shlex.quote(target)} -p {shlex.quote(PACKAGE)}"
        )
    else:
        command = (
            f"monkey -p {shlex.quote(PACKAGE)} "
            "-c android.intent.category.LAUNCHER 1"
        )
    output = run_rish(command, timeout=45)
    deadline = time.monotonic() + 15
    snapshot: dict[str, Any] = {}
    while time.monotonic() < deadline:
        snapshot = session_snapshot()
        if snapshot["media"]["spotify"].get("exists"):
            break
        time.sleep(0.8)
    ok = bool(snapshot and snapshot["media"]["spotify"].get("exists"))
    row = receipt(
        "spotify.launch",
        ok,
        playlistUri=target,
        command=command,
        output=output[-1500:],
        snapshot=snapshot,
        intentAcknowledged=True,
        sessionObserved=ok,
    )
    if not ok:
        raise RadioError("Spotify intent launched but no Spotify media session appeared")
    return row
'''

NEW_DISPATCH_AND_LAUNCH = '''def _overlay_apk_path() -> str:
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
    wrapped = (
        "{ " + bridge_command
        + "; rc=$?; printf '\\n__HC_RC=%s\\n' \"$rc\"; }"
    )
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
'''

OLD_PLAY = '''def play(uri: str = "", *, keep: bool = True) -> dict[str, Any]:
    state = load_state()
    target = uri or str(state.get("playlistUri") or "")
    _update_desired("play", desired=True, continuous=keep or bool(state.get("continuous")))
    snapshot = session_snapshot()
    allowed, _ = _spotify_is_dispatch_target(snapshot, allow_inactive=True)
    if not allowed:
        _launch(target)
    result = _dispatch_key("play", allow_inactive=True)
    after_state = int(result["after"]["media"]["spotify"].get("state") or 0)
    if after_state not in {3, 6, 8}:
        raise RadioError(f"Spotify did not enter playing/buffering/connecting state: {after_state}")
    if keep:
        ensure_daemon()
    return result
'''

NEW_PLAY = '''def play(uri: str = "", *, keep: bool = True) -> dict[str, Any]:
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
'''

OLD_DOCTOR = '''def doctor() -> dict[str, Any]:
    try:
        rish = find_rish()
        identity = run_rish("id")
        snapshot = session_snapshot()
        ok = bool(snapshot.get("packageInstalled"))
        return {
            "schema": "home-center.spotify-radio-doctor.v1",
            "ok": ok,
            "rish": rish,
            "identity": identity,
            "packageInstalled": snapshot.get("packageInstalled"),
            "spotifySessionObserved": snapshot["media"]["spotify"].get("exists"),
            "commandSurface": "cmd media_session dispatch",
            "systemTtsUsed": False,
            "cloudUsed": False,
            "snapshot": snapshot,
            "response": "Spotify Radio doctor ready." if ok else "Spotify is not installed.",
        }
    except Exception as exc:
        return {
            "schema": "home-center.spotify-radio-doctor.v1",
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}",
            "response": f"Spotify Radio doctor failed: {exc}",
        }
'''

NEW_DOCTOR = '''def doctor() -> dict[str, Any]:
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
'''

OLD_KEEPALIVE = '''def keepalive_once() -> dict[str, Any]:
    state = load_state()
    snapshot = session_snapshot()
    recover, reason = _should_recover(state, snapshot, _now_ms())
    if not recover:
        return receipt("keepalive.observe", True, action="yield", reason=reason, snapshot=snapshot)
    state["lastRecoveryAttemptAtMs"] = _now_ms()
    save_state(state)
    playlist_uri = str(state.get("playlistUri") or "")
    try:
        if not snapshot["media"]["spotify"].get("exists"):
            _launch(playlist_uri)
        result = _dispatch_key("play", allow_inactive=True)
        after_state = int(result["after"]["media"]["spotify"].get("state") or 0)
        ok = after_state in {3, 6, 8}
        return receipt(
            "keepalive.recover",
            ok,
            reason=reason,
            playlistUri=playlist_uri,
            playbackState=after_state,
            sourceReceipt=result,
        )
    except Exception as exc:
        return receipt(
            "keepalive.recover",
            False,
            reason=reason,
            error=f"{type(exc).__name__}: {exc}",
            playlistUri=playlist_uri,
        )
'''

NEW_KEEPALIVE = '''def keepalive_once() -> dict[str, Any]:
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
'''


def patch(text: str) -> str:
    text = replace_once(text, OLD_CONSTANT, NEW_CONSTANT, "bridge constants")
    text = replace_once(
        text,
        OLD_DISPATCH_AND_LAUNCH,
        NEW_DISPATCH_AND_LAUNCH,
        "exact-package bridge and foreground launcher removal",
    )
    text = replace_once(text, OLD_PLAY, NEW_PLAY, "background-only play")
    text = replace_once(text, OLD_DOCTOR, NEW_DOCTOR, "bridge doctor")
    text = replace_once(text, OLD_KEEPALIVE, NEW_KEEPALIVE, "background-only keepalive")
    forbidden = (
        "am start -W -a android.intent.action.VIEW",
        "monkey -p",
        "cmd media_session dispatch",
        "def _launch(",
    )
    found = [token for token in forbidden if token in text]
    if found:
        raise PatchError("forbidden foreground/global controls remain: " + ", ".join(found))
    required = (
        "SpotifyMediaBridge",
        "CLASSPATH=",
        "app_process /system/bin",
        "spotify_session_missing_background_only",
        '"foregroundLaunchUsed": False',
    )
    missing = [token for token in required if token not in text]
    if missing:
        raise PatchError("required no-foreground controls missing: " + ", ".join(missing))
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    target = root / TARGET
    if not target.is_file():
        raise PatchError(f"missing target: {target}")
    before = target.read_text(encoding="utf-8")
    after = patch(before)
    changed = before != after
    if changed:
        target.write_text(after, encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "target": str(target),
        "changed": changed,
        "foregroundLaunchForbidden": True,
        "exactPackageBridge": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
