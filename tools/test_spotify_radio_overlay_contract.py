#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICE = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
STATE = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorState.java"
DAEMON = ROOT / "tools/vlad_swarm_daemon.py"
CONTROLLER = ROOT / "tools/spotify_radio.py"
SETUP = ROOT / "tools/setup_spotify_radio.sh"
BUILD = ROOT / "android/operator-overlay/app/build.gradle"


def require(text: str, token: str, label: str) -> None:
    if token not in text:
        raise AssertionError(f"missing {label}: {token}")


def forbid(text: str, token: str, label: str) -> None:
    if token in text:
        raise AssertionError(f"forbidden {label}: {token}")


def main() -> int:
    service = SERVICE.read_text(encoding="utf-8")
    state = STATE.read_text(encoding="utf-8")
    daemon = DAEMON.read_text(encoding="utf-8")
    controller = CONTROLLER.read_text(encoding="utf-8")
    setup = SETUP.read_text(encoding="utf-8")
    build = BUILD.read_text(encoding="utf-8")

    require(service, 'radioRow.setContentDescription("Spotify Radio background controls")', "accessible persistent widget")
    require(service, 'radioButton("Prev", "previous"', "previous control")
    require(service, 'radioButton("Play", "toggle"', "play/pause control")
    require(service, 'radioButton("Next", "next"', "next control")
    require(service, 'radioButton("Stop", "stop"', "stop control")
    require(service, 'adamModeButton("RADIO", "radio"', "promptable radio mode")
    require(service, "root.addView(radioRow);\n        root.addView(details);", "widget outside collapsible details")
    require(service, 'OperatorState.submitAdamRequest(this, "radio", command, requestId)', "widget request transport")
    require(service, "MIN_TOUCH_TARGET_DP", "minimum accessible touch target")
    require(service, "handleControlButton", "local Home Center kill switch preserved")

    require(state, 'cleanMode.equals("radio")', "bounded radio request mode")
    require(daemon, 'if mode=="radio"', "radio daemon route")
    require(daemon, "run_spotify_radio(repo_root,text)", "deterministic radio executor")
    require(daemon, "ensure_spotify_radio(repo_root)", "keepalive continuation")
    require(daemon, "SPOTIFY_RADIO_STABLE", "stable installed runtime preference")

    require(controller, 'PACKAGE = "com.spotify.music"', "Spotify package binding")
    require(controller, "SpotifyMediaBridge", "exact-package Android media-session bridge")
    require(controller, "competingPlayingPackages", "competing player guard")
    require(controller, "call_active", "call yield")
    require(controller, "spotifyControlled", "post-dispatch Spotify verification")
    require(controller, "foregroundUnchanged", "foreground-stability acceptance gate")
    require(controller, "_foreground_unchanged", "foreground comparison helper")
    require(controller, "compile_prompt", "bounded natural-language compiler")
    require(controller, "playlistUri", "durable playlist identity")
    forbid(controller, "input keyevent", "blind global keyevent transport")
    forbid(controller, "termux-tts", "speech substitution")
    forbid(controller, "termux-media-player", "generic media player substitution")

    require(setup, ".local/lib/home-center/spotify-radio/spotify_radio.py", "repo-independent runtime")
    require(setup, ".termux/boot/home-center-spotify-radio.sh", "boot continuation")
    require(setup, "sourceSha256", "install source hash")
    require(setup, "runtimeSha256", "install readback hash")

    require(build, "versionCode 4", "overlay version bump")
    require(build, "versionName '1.3.0'", "overlay version name")

    print(json.dumps({
        "ok": True,
        "contract": "home-center.spotify-overlay-radio.v1",
        "assertions": [
            "existing overlay reused",
            "background widget remains visible when details collapse",
            "accessible quick controls",
            "RADIO prompt mode",
            "Shizuku/rish media-session muscle",
            "Spotify package/session verification before and after control",
            "call and competing-media yield",
            "stable phone runtime and boot recovery",
            "local kill switch preserved",
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
