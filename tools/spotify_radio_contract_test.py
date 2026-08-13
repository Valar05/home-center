#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "spotify_radio.py"


def load_module():
    bridge = types.ModuleType("android_phone_hands_bridge")
    bridge.run_rish = lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("device call forbidden in pure contract test"))
    sys.modules["android_phone_hands_bridge"] = bridge
    spec = importlib.util.spec_from_file_location("spotify_radio_contract_subject", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def main() -> int:
    radio = load_module()

    expected_prompts = {
        "status": ("status", ""),
        "what's playing": ("status", ""),
        "toggle": ("toggle", ""),
        "next": ("next", ""),
        "skip this": ("next", ""),
        "previous": ("previous", ""),
        "pause spotify": ("pause", ""),
        "resume radio": ("resume", ""),
        "keep it rolling": ("start", ""),
        "stop radio": ("stop", ""),
        "play Battles by Alpine Universe on Spotify": ("play", "Battles by Alpine Universe"),
        "Spotify play Alpine Universe Battles": ("play", "Alpine Universe Battles"),
    }
    for prompt, expected in expected_prompts.items():
        parsed = radio.parse_prompt(prompt)
        assert (parsed.action, parsed.value) == expected, (prompt, parsed, expected)
    assert radio.parse_prompt("make me a sandwich").action == "unsupported"

    dump = """
  Sessions Stack - have 2 sessions:
    spotify-media-session com.spotify.music/spotify-media-session/111
      package=com.spotify.music
      state=PlaybackState {state=PLAYING(3), position=178443, buffered position=0, speed=1.0}
      metadata: size=5, description=Battles, Alpine Universe
        android.media.metadata.TITLE=Battles
        android.media.metadata.ARTIST=Alpine Universe
        android.media.metadata.ALBUM=Akoustik Vol. 2
      audioAttrs=AudioAttributes: usage=USAGE_MEDIA
    other-player package/example
"""
    session = radio.parse_session(dump)
    assert session["found"] is True
    assert session["package"] == "com.spotify.music"
    assert session["state"] == "PLAYING"
    assert session["stateCode"] == 3
    assert session["positionMs"] == 178443
    assert session["title"] == "Battles"
    assert session["artist"] == "Alpine Universe"
    assert session["album"] == "Akoustik Vol. 2"
    assert radio.parse_session("no sessions")["found"] is False

    before_track = {"found": True, "title": "Battles", "artist": "Alpine Universe", "album": "Akoustik", "positionMs": 120000}
    changed_track = {"found": True, "title": "The Empire of Winds", "artist": "Alpine Universe", "album": "Akoustik", "positionMs": 1000}
    reset_track = {"found": True, "title": "Battles", "artist": "Alpine Universe", "album": "Akoustik", "positionMs": 500}
    unchanged_track = {"found": True, "title": "Battles", "artist": "Alpine Universe", "album": "Akoustik", "positionMs": 121000}
    assert radio.track_change_verified(before_track, changed_track) is True
    assert radio.track_change_verified(before_track, reset_track) is True
    assert radio.track_change_verified(before_track, unchanged_track) is False
    assert radio.track_change_verified(before_track, {"found": False}) is False

    now = 1_000_000
    base = radio.default_config()
    base.update({"enabled": True, "suspended": False, "lastVerifiedPlayingAtMs": now - (radio.RECOVERY_GRACE_SECONDS + 1) * 1000})
    assert radio.monitor_decision(base, {"state": "PLAYING"}, now) == "healthy"
    assert radio.monitor_decision(base, {"state": "PAUSED"}, now) == "respect_pause"
    assert radio.monitor_decision(base, {"state": "STOPPED"}, now) == "recover"
    paused = dict(base, suspended=True)
    assert radio.monitor_decision(paused, {"state": "STOPPED"}, now) == "suspended"
    disabled = dict(base, enabled=False)
    assert radio.monitor_decision(disabled, {"state": "STOPPED"}, now) == "disabled"
    never_played = dict(base, lastVerifiedPlayingAtMs=0)
    assert radio.monitor_decision(never_played, {"state": "STOPPED"}, now) == "observe"

    source = MODULE_PATH.read_text(encoding="utf-8")
    assert "api.spotify.com" not in source
    assert "SPOTIFY_CLIENT_SECRET" not in source
    assert "SPOTIFY_ACCESS_TOKEN" not in source
    assert "KEYCODE_MEDIA_PAUSE" in source
    assert "KEYCODE_MEDIA_PLAY" in source
    assert "MEDIA_PLAY_FROM_SEARCH" in source
    assert "spotifySessionOwned" in source
    assert "monitorRecoveryForbidden" in source
    assert "respect_pause" in source

    with tempfile.TemporaryDirectory() as temp:
        radio.STATE_ROOT = Path(temp)
        radio.CONFIG_PATH = radio.STATE_ROOT / "config.json"
        radio.RECEIPTS_PATH = radio.STATE_ROOT / "receipts.jsonl"
        radio.LAST_PATH = radio.STATE_ROOT / "last.json"
        config = radio.default_config()
        config.update({"enabled": False, "suspended": True, "playlistName": "Fortress Radio — Rolling Forge"})
        radio.save_config(config)
        readback = radio.load_config()
        assert readback["enabled"] is False
        assert readback["suspended"] is True
        receipt = radio.write_receipt("test", True, evidence="bounded")
        assert json.loads(radio.LAST_PATH.read_text(encoding="utf-8"))["kind"] == "test"
        assert receipt["provider"] == "spotify-android"

    print("spotify_radio_contract_test: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
