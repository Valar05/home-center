#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("spotify_radio", ROOT / "spotify_radio.py")
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
    assert radio.compile_prompt("playlist https://open.spotify.com/playlist/abc") == (
        "set-playlist",
        {"uri": "https://open.spotify.com/playlist/abc"},
    )
    try:
        radio.compile_prompt("find whatever and click around")
        raise AssertionError("unbounded prompt compiled")
    except ValueError:
        pass

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

    print(json.dumps({
        "ok": True,
        "tests": [
            "Spotify-specific session parsing",
            "metadata extraction",
            "competing-player rejection",
            "call-state yield",
            "bounded natural-language prompt compiler",
            "continuous keepalive recovery",
            "healthy-session no-op",
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
