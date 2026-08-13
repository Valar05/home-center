#!/usr/bin/env python3
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "spotify_radio.py"
SPEC = importlib.util.spec_from_file_location("spotify_radio", MODULE_PATH)
radio = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(radio)


class FakeClient:
    def __init__(self, search, top):
        self.search = search
        self.top = top

    def search_tracks(self, query):
        return list(self.search.get(query, []))

    def top_tracks(self):
        return list(self.top)


def track(uri, name, artist, artist_id, duration=240000):
    return {
        "uri": uri,
        "id": uri.rsplit(":", 1)[-1],
        "name": name,
        "durationMs": duration,
        "artistIds": [artist_id],
        "artistNames": [artist],
    }


class PromptContract(unittest.TestCase):
    def test_direct_controls_are_typed(self):
        self.assertEqual("pause", radio.compile_prompt("pause")["action"])
        self.assertEqual("next", radio.compile_prompt("skip")["action"])
        self.assertEqual("status", radio.compile_prompt("what is playing")["action"])

    def test_creation_compiles_bounded_policy(self):
        plan = radio.compile_prompt(
            "Make me a 90 minute driving playlist, tense and propulsive, sparse vocals. Keep it rolling."
        )
        self.assertEqual("playlist", plan["kind"])
        self.assertEqual("create", plan["mode"])
        self.assertTrue(plan["rolling"])
        self.assertEqual(90, plan["policy"]["targetMinutes"])
        self.assertIn("driving", plan["policy"]["queries"])
        self.assertRegex(plan["policy"]["policyHash"], r"^[0-9a-f]{64}$")

    def test_revision_preserves_current_by_default(self):
        prior = {"queries": ["cinematic"], "targetMinutes": 60, "artistRepeatWindow": 8}
        plan = radio.compile_prompt("More synth, less choir", prior)
        self.assertEqual("revise", plan["mode"])
        self.assertTrue(plan["policy"]["preserveCurrentTrack"])
        self.assertIn("choir", " ".join(plan["policy"]["avoid"]))

    def test_stop_after_current_is_state_not_generic_stop(self):
        plan = radio.compile_prompt("Stop after this track")
        self.assertEqual("stop_after_current", plan["kind"])


class SelectionContract(unittest.TestCase):
    def test_selection_is_deterministic_and_respects_exclusions(self):
        a = track("spotify:track:A123456789", "Dark Drive", "Alpha", "alpha")
        b = track("spotify:track:B123456789", "Choir Storm", "Beta", "beta")
        c = track("spotify:track:C123456789", "Synth Road", "Gamma", "gamma")
        client = FakeClient({"synth driving": [a, b, c]}, [a, b, c])
        policy = {
            "queries": ["synth driving"],
            "avoid": ["choir"],
            "targetMinutes": 30,
            "artistRepeatWindow": 8,
            "policyHash": "1" * 64,
        }
        state = {"recentTrackUris": [a["uri"]], "recentArtistIds": []}
        first = radio.choose_tracks(client, policy, state, [], 10)
        second = radio.choose_tracks(client, policy, state, [], 10)
        self.assertEqual(first, second)
        self.assertEqual([c["uri"]], [item["uri"] for item in first])

    def test_target_count_is_bounded(self):
        tracks = [track("spotify:track:A123456789", "A", "A", "a", 300000)]
        self.assertEqual(18, radio.target_track_count({"targetMinutes": 90}, tracks))
        self.assertEqual(8, radio.target_track_count({"targetMinutes": 15}, tracks))


class ReceiptContract(unittest.TestCase):
    def test_secrets_are_redacted_without_hiding_safe_metadata(self):
        value = radio.redacted({
            "accessToken": "abc",
            "refresh_token": "def",
            "authorization": "Bearer hidden",
            "authorizationUrl": "https://accounts.spotify.com/authorize?safe=1",
            "tokensExposed": False,
            "safe": "yes",
        })
        self.assertEqual("[REDACTED]", value["accessToken"])
        self.assertEqual("[REDACTED]", value["refresh_token"])
        self.assertEqual("[REDACTED]", value["authorization"])
        self.assertIn("accounts.spotify.com", value["authorizationUrl"])
        self.assertFalse(value["tokensExposed"])
        self.assertEqual("yes", value["safe"])

    def test_auth_url_is_returned_but_not_persisted(self):
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            overrides = {
                "CONFIG": root / "config.json",
                "STATE_DIR": root,
                "STATE": root / "state.json",
                "OAUTH_PENDING": root / "oauth-pending.json",
                "RECEIPTS": root / "receipts.jsonl",
                "LATEST": root / "latest.json",
            }
            output = io.StringIO()
            with mock.patch.multiple(radio, **overrides), contextlib.redirect_stdout(output):
                packet = radio.auth_url("A" * 32, "https://example.com/callback")
            durable = overrides["RECEIPTS"].read_text(encoding="utf-8") + overrides["LATEST"].read_text(encoding="utf-8")
            rendered = output.getvalue()
            self.assertNotIn("accounts.spotify.com", durable)
            self.assertNotIn("verifier", durable.lower())
            self.assertNotIn("verifier", rendered.lower())
            self.assertIn("accounts.spotify.com", packet["authorizationUrl"])
            self.assertFalse(packet["persisted"])
            self.assertEqual("home-center.spotify-radio-auth-url.v1", packet["schema"])

    def test_provider_row_parser_keeps_base64(self):
        row = radio.parse_provider_row(
            "Row: 0 control_enabled=0, spotify_request_id=123, spotify_receipt_b64=eyJvayI6dHJ1ZX0=, spotify_summary=Spotify • on"
        )
        self.assertEqual("123", row["spotify_request_id"])
        self.assertEqual("eyJvayI6dHJ1ZX0=", row["spotify_receipt_b64"])


class IdleEnsureContract(unittest.TestCase):
    def test_idle_ensure_calls_no_client_method(self):
        class ExplodingClient:
            def __getattr__(self, name):
                raise AssertionError(f"client method accessed: {name}")

        state = {"playlistId": "playlist-123", "rolling": False, "stopAfterCurrent": False}
        self.assertEqual(
            {"state": "rolling_disabled", "playlistId": "playlist-123"},
            radio.ensure_once(ExplodingClient(), state),
        )

    def test_idle_daemon_does_not_construct_spotify_client(self):
        idle = {"playlistId": "playlist-123", "rolling": False, "stopAfterCurrent": False}
        with mock.patch.object(radio, "load_state", return_value=idle), \
             mock.patch.object(radio, "SpotifyClient", side_effect=AssertionError("constructed")), \
             mock.patch.object(radio, "emit", side_effect=KeyboardInterrupt):
            self.assertEqual(0, radio.daemon(10))

    def test_idle_cli_ensure_does_not_construct_spotify_client(self):
        idle = {"playlistId": "playlist-123", "rolling": False, "stopAfterCurrent": False}
        with mock.patch.object(radio, "load_state", return_value=idle), \
             mock.patch.object(radio, "SpotifyClient", side_effect=AssertionError("constructed")), \
             mock.patch.object(radio, "emit") as emit, \
             mock.patch.object(sys, "argv", ["spotify-radio", "ensure"]):
            self.assertEqual(0, radio.main())
            self.assertEqual("rolling_disabled", emit.call_args.kwargs["result"]["state"])


class SourceBoundaryContract(unittest.TestCase):
    def setUp(self):
        self.python = MODULE_PATH.read_text(encoding="utf-8")
        self.android_root = ROOT / "android" / "operator-overlay" / "app" / "src" / "main"
        self.service = (self.android_root / "java" / "com" / "homecenter" / "operatoroverlay" / "SpotifyMediaUserService.java").read_text(encoding="utf-8")
        self.client = (self.android_root / "java" / "com" / "homecenter" / "operatoroverlay" / "SpotifyShizukuClient.java").read_text(encoding="utf-8")
        self.provider = (self.android_root / "java" / "com" / "homecenter" / "operatoroverlay" / "OperatorStateProvider.java").read_text(encoding="utf-8")
        self.overlay = (self.android_root / "java" / "com" / "homecenter" / "operatoroverlay" / "OperatorOverlayService.java").read_text(encoding="utf-8")

    def test_forbidden_foreground_and_generic_routes_absent(self):
        corpus = "\n".join([self.python, self.service, self.client, self.provider, self.overlay])
        forbidden = [
            "cmd media_session dispatch",
            "dispatchMediaKeyEvent",
            "Intent.ACTION_VIEW",
            "phone.open_uri",
            "monkey -p",
            "input keyevent",
            "startActivity(",
            "startActivityForResult(",
        ]
        for needle in forbidden:
            self.assertNotIn(needle, corpus, needle)

    def test_exact_spotify_session_is_required(self):
        self.assertIn('TARGET_PACKAGE = "com.spotify.music"', self.service)
        self.assertIn("manager.getActiveSessions(null)", self.service)
        self.assertIn("TARGET_PACKAGE.equals(controller.getPackageName())", self.service)
        self.assertIn('"SPOTIFY_SESSION_AUTHORITY_UNAVAILABLE"', self.service)
        self.assertIn('"SPOTIFY_SESSION_ABSENT"', self.service)

    def test_shizuku_user_service_is_real(self):
        self.assertIn("Shizuku.UserServiceArgs", self.client)
        self.assertIn("Shizuku.bindUserService", self.client)
        self.assertIn("SpotifyMediaUserService.class.getName()", self.client)
        self.assertNotIn("Shizuku.requestPermission", self.client)

    def test_provider_ingress_is_typed_and_background_only(self):
        self.assertIn('METHOD_SPOTIFY_CONTROL = "spotify_control"', self.provider)
        self.assertIn("enforceCallingOrSelfPermission", self.provider)
        self.assertIn("android.Manifest.permission.DUMP", self.provider)
        self.assertIn("startForegroundService(", self.provider)
        self.assertIn("OperatorOverlayService.class", self.provider)
        self.assertIn("ACTION_SPOTIFY_COMMAND", self.provider)
        self.assertNotIn("startActivity", self.provider)

    def test_overlay_has_widget_and_radio_prompt_mode(self):
        self.assertIn("spotifyStatus", self.overlay)
        self.assertIn("adamModeButton(", self.overlay)
        self.assertIn('"RADIO"', self.overlay)
        self.assertIn('"radio"', self.overlay)
        self.assertIn("ACTION_SPOTIFY_COMMAND", self.overlay)
        self.assertIn("SpotifyShizukuClient", self.overlay)

    def test_current_spotify_playlist_endpoints_only(self):
        self.assertIn('"/me/playlists"', self.python)
        self.assertIn('f"/playlists/{playlist_id}/items"', self.python)
        self.assertNotIn('f"/playlists/{playlist_id}/tracks"', self.python)
        self.assertIn('"code_challenge_method": "S256"', self.python)

    def test_android_content_extras_use_aosp_binding_order(self):
        self.assertIn('" --extra argument_b64:s:"', self.python)
        self.assertIn('" --extra request_id:l:"', self.python)
        self.assertNotIn('" --extra string:argument_b64:"', self.python)
        self.assertNotIn('" --extra long:request_id:"', self.python)


if __name__ == "__main__":
    unittest.main(verbosity=2)
