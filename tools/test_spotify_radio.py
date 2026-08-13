#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_PATH = ROOT / "spotify_radio.py"
SPEC = importlib.util.spec_from_file_location("spotify_radio", SOURCE_PATH)
radio = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(radio)

SPOTIFY_PLAYING = """
Sessions Stack - have 1 sessions:
  com.spotify.music/com.spotify.music.MainActivity (userId=0)
    active=true
    state=PlaybackState {state=3, position=1234, buffered position=0, speed=1.0}
    metadata:
      android.media.metadata.TITLE=Battles
      android.media.metadata.ARTIST=Alpine Universe
Media button session is com.spotify.music/com.spotify.music.MainActivity
"""

COMPETING = """
Sessions Stack - have 2 sessions:
  com.example.podcast/.Player (userId=0)
    active=true
    state=PlaybackState {state=3, position=42}
  com.spotify.music/com.spotify.music.MainActivity (userId=0)
    active=true
    state=PlaybackState {state=2, position=1234}
Media button session is com.example.podcast/.Player
"""


def main() -> int:
    source = SOURCE_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "am start -W -a android.intent.action.VIEW",
        "monkey -p",
        "cmd media_session dispatch",
        "def _launch(",
    ):
        assert forbidden not in source, f"foreground/global fallback remains: {forbidden}"
    for required in (
        "SpotifyMediaBridge",
        "CLASSPATH=",
        "app_process /system/bin",
        "spotify_session_missing_background_only",
        '"foregroundLaunchUsed": False',
    ):
        assert required in source, f"exact-package background bridge missing: {required}"

    parsed = radio.parse_media_session(SPOTIFY_PLAYING)
    assert parsed["currentPackage"] == radio.PACKAGE
    assert parsed["spotify"]["state"] == 3
    assert parsed["spotify"]["stateName"] == "playing"
    assert parsed["spotify"]["title"] == "Battles"
    assert parsed["spotify"]["artist"] == "Alpine Universe"
    assert parsed["competingPlayingPackages"] == []

    competing = radio.parse_media_session(COMPETING)
    assert competing["currentPackage"] == "com.example.podcast"
    assert competing["spotify"]["state"] == 2
    assert competing["competingPlayingPackages"] == ["com.example.podcast"]

    assert radio.parse_call_state("mMode=MODE_NORMAL", "")["active"] is False
    assert radio.parse_call_state("mMode=MODE_IN_CALL", "")["active"] is True

    assert radio.compile_prompt("radio play") == ("play", {})
    assert radio.compile_prompt("Spotify next") == ("next", {})
    assert radio.compile_prompt("keep it rolling") == ("play", {})
    assert radio.compile_prompt("playlist https://open.spotify.com/playlist/1234567890ABCDEFGHIJKL") == (
        "set-playlist",
        {"uri": "https://open.spotify.com/playlist/1234567890ABCDEFGHIJKL"},
    )
    try:
        radio.compile_prompt("find whatever and click around")
        raise AssertionError("unbounded prompt compiled")
    except ValueError:
        pass

    original_overlay_path = radio._overlay_apk_path
    original_run_rish = radio.run_rish
    captured_commands: list[str] = []
    try:
        radio._overlay_apk_path = lambda: "/data/app/example/base.apk"

        def fake_rish(command: str, timeout: int = 30) -> str:
            captured_commands.append(command)
            return json.dumps({
                "ok": True,
                "schema": "home-center.spotify-media-bridge.v1",
                "action": "play-uri",
                "targetPackage": radio.PACKAGE,
                "requestedUri": "spotify:playlist:1234567890ABCDEFGHIJKL",
                "foregroundLaunchUsed": False,
                "before": {"package": radio.PACKAGE, "state": 2},
                "after": {"package": radio.PACKAGE, "state": 3},
            }) + "\n__HC_RC=0\n"

        radio.run_rish = fake_rish
        bridged = radio._bridge("play-uri", "spotify:playlist:1234567890ABCDEFGHIJKL")
        assert bridged["ok"] is True
        assert bridged["result"]["targetPackage"] == radio.PACKAGE
        assert bridged["result"]["foregroundLaunchUsed"] is False
        assert len(captured_commands) == 1
        assert "CLASSPATH=/data/app/example/base.apk" in captured_commands[0]
        assert "app_process /system/bin" in captured_commands[0]
        assert radio.BRIDGE_CLASS in captured_commands[0]
        assert "am start" not in captured_commands[0]
        assert "monkey" not in captured_commands[0]
    finally:
        radio._overlay_apk_path = original_overlay_path
        radio.run_rish = original_run_rish

    with tempfile.TemporaryDirectory() as temporary:
        radio.STATE_DIR = Path(temporary)
        radio.STATE_FILE = radio.STATE_DIR / "state.json"
        radio.RECEIPTS = radio.STATE_DIR / "receipts.jsonl"
        radio.PID_FILE = radio.STATE_DIR / "keepalive.pid"
        radio.LOG_FILE = radio.STATE_DIR / "keepalive.log"
        state = radio.save_state({
            "continuous": True,
            "desiredPlaying": True,
            "lastRecoveryAttemptAtMs": 0,
        })
        healthy_snapshot = {
            "call": {"active": False},
            "media": {
                "currentPackage": radio.PACKAGE,
                "competingPlayingPackages": [],
                "spotify": {"exists": True, "state": 3},
            },
        }
        recover, reason = radio._should_recover(state, healthy_snapshot, radio._now_ms())
        assert recover is False and reason == "spotify_healthy"

        paused_snapshot = {
            "call": {"active": False},
            "media": {
                "currentPackage": radio.PACKAGE,
                "competingPlayingPackages": [],
                "spotify": {"exists": True, "state": 2},
            },
        }
        recover, reason = radio._should_recover(state, paused_snapshot, radio._now_ms())
        assert recover is True and reason == "spotify_not_playing"

        call_snapshot = {
            **paused_snapshot,
            "call": {"active": True},
        }
        recover, reason = radio._should_recover(state, call_snapshot, radio._now_ms())
        assert recover is False and reason == "call_active"

        competitor_snapshot = {
            "call": {"active": False},
            "media": {
                "currentPackage": "com.example.podcast",
                "competingPlayingPackages": ["com.example.podcast"],
                "spotify": {"exists": True, "state": 2},
            },
        }
        recover, reason = radio._should_recover(state, competitor_snapshot, radio._now_ms())
        assert recover is False and reason == "competing_media"

        missing_snapshot = {
            "packageInstalled": True,
            "foreground": "unchanged",
            "call": {"active": False},
            "media": {
                "currentPackage": "",
                "competingPlayingPackages": [],
                "spotify": {"exists": False, "state": 0},
            },
        }
        original_snapshot = radio.session_snapshot
        original_receipt = radio.receipt
        original_bridge = radio._bridge
        bridge_called = False
        try:
            radio.session_snapshot = lambda: missing_snapshot
            radio.receipt = lambda kind, ok, **fields: {"kind": kind, "ok": ok, **fields}

            def forbidden_bridge(*_args, **_kwargs):
                nonlocal bridge_called
                bridge_called = True
                raise AssertionError("bridge must not run without an existing Spotify session")

            radio._bridge = forbidden_bridge
            yielded = radio.keepalive_once()
            assert yielded["ok"] is True
            assert yielded["action"] == "yield"
            assert yielded["reason"] == "spotify_session_missing_background_only"
            assert yielded["foregroundLaunchUsed"] is False
            assert bridge_called is False
        finally:
            radio.session_snapshot = original_snapshot
            radio.receipt = original_receipt
            radio._bridge = original_bridge

    print(json.dumps({
        "ok": True,
        "tests": [
            "Spotify-specific session parsing",
            "metadata extraction",
            "competing-player rejection",
            "call-state yield",
            "bounded natural-language prompt compiler",
            "exact-package rish/app_process bridge",
            "foreground launcher absence",
            "missing-session fail-closed yield",
            "continuous keepalive recovery",
            "healthy-session no-op",
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
