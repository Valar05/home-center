#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

TARGET = Path("tools/test_spotify_radio_overlay_contract.py")


class PatchError(RuntimeError):
    pass


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


def patch(text: str) -> str:
    text = replace_once(
        text,
        'STATE = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java"\n',
        'STATE = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java"\n'
        'BRIDGE = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/SpotifyMediaBridge.java"\n',
        "bridge path",
    )
    text = replace_once(
        text,
        '    state = STATE.read_text(encoding="utf-8")\n',
        '    state = STATE.read_text(encoding="utf-8")\n'
        '    bridge = BRIDGE.read_text(encoding="utf-8")\n',
        "bridge read",
    )
    old = '''    require(controller, "cmd media_session dispatch", "Android media-session transport")
    require(controller, "competingPlayingPackages", "competing player guard")
    require(controller, "call_active", "call yield")
    require(controller, "spotifyControlled", "post-dispatch Spotify verification")
    require(controller, "compile_prompt", "bounded natural-language compiler")
    require(controller, "playlistUri", "durable playlist identity")
    forbid(controller, "input keyevent", "blind global keyevent transport")
    forbid(controller, "termux-tts", "speech substitution")
    forbid(controller, "termux-media-player", "generic media player substitution")
'''
    new = '''    require(controller, 'BRIDGE_CLASS = "com.homecenter.operatoroverlay.SpotifyMediaBridge"', "installed bridge identity")
    require(controller, "CLASSPATH=", "installed APK classpath")
    require(controller, "app_process /system/bin", "Shizuku shell bridge process")
    require(controller, "competingPlayingPackages", "competing player guard")
    require(controller, "call_active", "call yield")
    require(controller, "spotifyControlled", "post-dispatch Spotify verification")
    require(controller, "compile_prompt", "bounded natural-language compiler")
    require(controller, "playlistUri", "durable playlist identity")
    require(controller, "spotify_session_missing_background_only", "missing-session fail closed")
    require(controller, '"foregroundLaunchUsed": False', "no-foreground receipt")
    forbid(controller, "input keyevent", "blind global keyevent transport")
    forbid(controller, "cmd media_session dispatch", "global media-session dispatch")
    forbid(controller, "android.intent.action.VIEW", "foreground Spotify intent")
    forbid(controller, "monkey -p", "foreground launcher")
    forbid(controller, "def _launch(", "foreground launch helper")
    forbid(controller, "termux-tts", "speech substitution")
    forbid(controller, "termux-media-player", "generic media player substitution")

    require(bridge, 'SPOTIFY_PACKAGE = "com.spotify.music"', "exact bridge package")
    require(bridge, "getActiveSessions(null)", "media-session authority")
    require(bridge, "controls.playFromUri", "playlist background start")
    require(bridge, "SPOTIFY_SESSION_ABSENT", "absent-session boundary")
    require(bridge, "COMPETING_MEDIA_SESSION", "competing-player boundary")
    require(bridge, '\\"foregroundLaunchUsed\\":false', "bridge no-foreground receipt")
    require(bridge, "ActivityThread", "app_process system context")
    forbid(bridge, "startActivity", "activity launch")
    forbid(bridge, "android.content.Intent", "intent launch")
    forbid(bridge, "dispatchMediaKeyEvent", "global media-key dispatch")
'''
    text = replace_once(text, old, new, "controller and bridge contract")
    text = replace_once(
        text,
        '            "Shizuku/rish media-session muscle",\n',
        '            "Shizuku/rish app_process muscle",\n'
        '            "exact Spotify MediaController",\n'
        '            "playlist playFromUri without Activity launch",\n',
        "assertion list",
    )
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    target = Path(args.root).resolve() / TARGET
    if not target.is_file():
        raise PatchError(f"missing target: {target}")
    before = target.read_text(encoding="utf-8")
    after = patch(before)
    changed = before != after
    if changed:
        target.write_text(after, encoding="utf-8")
    print(json.dumps({"ok": True, "target": str(target), "changed": changed}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
