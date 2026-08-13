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
        self.operator_state = (self.android_root / "java" / "com" / "homecenter" / "operatoroverlay" / "OperatorState.java").read_text(encoding="utf-8")
        self.overlay = (self.android_root / "java" / "com" / "homecenter" / "operatoroverlay" / "OperatorOverlayService.java").read_text(encoding="utf-8")
        self.installer = (ROOT / "tools" / "setup_spotify_radio.sh").read_text(encoding="utf-8")

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
        self.assertIn('"SPOTIFY_SESSION_AMBIGUOUS"', self.service)
        self.assertIn("spotifySessionCount", self.service)
        self.assertIn("VERIFY_POLL_MS", self.service)
        self.assertIn("VERIFY_TIMEOUT_MS", self.service)
        self.assertIn("SystemClock.elapsedRealtime()", self.service)

    def test_shizuku_user_service_is_real(self):
        self.assertIn("Shizuku.UserServiceArgs", self.client)
        self.assertIn("Shizuku.bindUserService", self.client)
        self.assertIn("SpotifyMediaUserService.class.getName()", self.client)
        self.assertIn("MIN_SHIZUKU_VERSION = 13", self.client)
        self.assertIn("Shizuku.getVersion() < MIN_SHIZUKU_VERSION", self.client)
        self.assertIn("unbindUserService(userServiceArgs, serviceConnection, false)", self.client)
        self.assertNotIn("Shizuku.requestPermission(", self.client)

    def test_provider_ingress_is_typed_and_background_only(self):
        self.assertIn('METHOD_SPOTIFY_CONTROL = "spotify_control"', self.provider)
        self.assertIn("enforceCallingOrSelfPermission", self.provider)
        self.assertIn("android.Manifest.permission.DUMP", self.provider)
        self.assertIn("startForegroundService(", self.provider)
        self.assertIn("OperatorOverlayService.class", self.provider)
        self.assertIn("ACTION_SPOTIFY_COMMAND", self.provider)
        self.assertNotIn("startActivity", self.provider)

    def test_migration_restore_is_dump_protected_and_screenless(self):
        self.assertIn('METHOD_RESTORE_MIGRATION_STATE = "restore_migration_state"', self.provider)
        start = self.provider.index("private static Bundle restoreMigrationState")
        end = self.provider.index("private static void validateMigrationExtras", start)
        restore = self.provider[start:end]
        self.assertIn("context.enforceCallingPermission(", restore)
        self.assertIn("android.Manifest.permission.DUMP", restore)
        self.assertLess(
            restore.index("context.enforceCallingPermission("),
            restore.index("OperatorState.restoreMigrationState("),
        )
        self.assertIn('result.putBoolean("restored", true)', restore)
        self.assertIn('result.putBoolean("control_enabled", false)', restore)
        self.assertNotIn("startService", restore)
        self.assertNotIn("startForegroundService", restore)
        self.assertNotIn("startActivity", restore)

    def test_migration_restore_has_bounded_fields_and_fail_closed_guards(self):
        allowed = {
            "KEY_MUTED",
            "KEY_LAST_HEARTBEAT_MS",
            "KEY_LAST_UPDATE_MS",
            "KEY_LATEST_SOURCE",
            "KEY_PANEL_COLLAPSED",
            "KEY_OVERLAY_HIDDEN",
        }
        restorable_start = self.provider.index("MIGRATION_RESTORABLE_KEYS")
        restorable_end = self.provider.index("MIGRATION_GUARD_KEYS", restorable_start)
        restorable = self.provider[restorable_start:restorable_end]
        for key in allowed:
            self.assertIn(key, restorable)
        for key in (
            "KEY_LATEST_TEXT",
            "KEY_ADAM_REQUEST_PAYLOAD_B64",
            "KEY_SPOTIFY_RECEIPT_B64",
            "credentials",
        ):
            self.assertNotIn(key, restorable)

        validation_start = self.provider.index("private static void validateMigrationExtras")
        validation_end = self.provider.index("private static String decodeSpotifyArgument", validation_start)
        validation = self.provider[validation_start:validation_end]
        self.assertIn("unsupported migration field", validation)
        self.assertIn("!Boolean.FALSE.equals", validation)
        self.assertIn("rejectNonzeroLease", validation)
        self.assertIn("migration cannot enable control", validation)
        self.assertIn("migration cannot restore screen leases", validation)

        state_start = self.operator_state.index("static boolean restoreMigrationState")
        state_end = self.operator_state.index("private static String sanitizeMigrationSource", state_start)
        state_restore = self.operator_state[state_start:state_end]
        self.assertIn(".putBoolean(KEY_CONTROL_ENABLED, false)", state_restore)
        self.assertIn(".putLong(KEY_SCREEN_ACTIVE_UNTIL_MS, 0L)", state_restore)
        self.assertIn(".putLong(KEY_SCREEN_YIELD_UNTIL_MS, 0L)", state_restore)
        self.assertIn("return editor.commit()", state_restore)
        self.assertNotIn("KEY_LATEST_TEXT", state_restore)
        self.assertNotIn("KEY_ADAM_REQUEST", state_restore)
        self.assertNotIn("KEY_SPOTIFY", state_restore)

        sanitizer_start = self.operator_state.index("private static String sanitizeMigrationSource")
        sanitizer_end = self.operator_state.index("static void setMuted", sanitizer_start)
        sanitizer = self.operator_state[sanitizer_start:sanitizer_end]
        self.assertIn("replace('\\r', ' ')", sanitizer)
        self.assertIn("replace('\\n', ' ')", sanitizer)
        self.assertIn("replace(',', ' ')", sanitizer)
        self.assertIn("clean.length() > 80", sanitizer)

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

    def test_installer_does_not_impersonate_reviews(self):
        for marker in (
            "Venice plan receipt",
            "Rene QA receipt",
            "Venice completion receipt",
            "PLAN_ALLOWED",
            "STOP_ALLOWED",
        ):
            self.assertNotIn(marker, self.installer, marker)

    def test_installer_verifies_pid_and_lock_owner_identity(self):
        self.assertIn("pid_is_service()", self.installer)
        self.assertIn("pid_is_lock_owner()", self.installer)
        self.assertIn('/proc/${pid}/cmdline', self.installer)
        self.assertIn("stale_pid_rejected", self.installer)
        self.assertIn("cleanup_install_temps()", self.installer)
        self.assertIn("pidIdentityVerified", self.installer)

    def test_android_content_extras_use_aosp_binding_order(self):
        self.assertIn('" --extra argument_b64:s:"', self.python)
        self.assertIn('" --extra request_id:l:"', self.python)
        self.assertNotIn('" --extra string:argument_b64:"', self.python)
        self.assertNotIn('" --extra long:request_id:"', self.python)


class AccountIntegrityContract(unittest.TestCase):
    def test_oauth_callback_parses_url_and_query(self):
        self.assertEqual(("abc", "state-1"), radio.parse_oauth_callback("https://example.test/callback?code=abc&state=state-1"))
        self.assertEqual(("xyz", "state-2"), radio.parse_oauth_callback("code=xyz&state=state-2"))

    def test_oauth_callback_rejects_denied_and_malformed(self):
        with self.assertRaises(radio.RadioError) as denied:
            radio.parse_oauth_callback("https://example.test/callback?error=access_denied&state=x")
        self.assertEqual("SPOTIFY_AUTHORIZATION_DENIED", denied.exception.code)
        for value in ("", "state=x", "code=x", "code=x&code=y&state=z"):
            with self.assertRaises(radio.RadioError) as invalid:
                radio.parse_oauth_callback(value)
            self.assertEqual("SPOTIFY_AUTH_CALLBACK_INVALID", invalid.exception.code)

    def test_oauth_code_is_not_a_cli_argument(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn('complete.add_argument("--code"', source)
        self.assertNotIn('complete.add_argument("--state"', source)
        self.assertIn("callback = sys.stdin.readline", source)

    def test_request_ids_are_unique_positive_signed_int64(self):
        values = [radio.next_request_id() for _ in range(512)]
        self.assertEqual(len(values), len(set(values)))
        self.assertTrue(all(0 < value <= (1 << 63) - 1 for value in values))

    def test_operation_lock_recovers_stale_owner(self):
        with tempfile.TemporaryDirectory() as temporary:
            old_lock = radio.OPERATION_LOCK
            radio.OPERATION_LOCK = pathlib.Path(temporary) / "operation.lock"
            try:
                radio.OPERATION_LOCK.write_text(json.dumps({"pid": 99999999, "purpose": "stale", "createdAtMs": radio.now_ms() - 700000}), encoding="utf-8")
                with radio.operation_lock("fresh", timeout=0.2):
                    current = json.loads(radio.OPERATION_LOCK.read_text(encoding="utf-8"))
                    self.assertEqual("fresh", current["purpose"])
                self.assertFalse(radio.OPERATION_LOCK.exists())
            finally:
                radio.OPERATION_LOCK = old_lock

    def test_operation_lock_fails_bounded_when_live(self):
        with tempfile.TemporaryDirectory() as temporary:
            old_lock = radio.OPERATION_LOCK
            radio.OPERATION_LOCK = pathlib.Path(temporary) / "operation.lock"
            try:
                radio.OPERATION_LOCK.write_text(json.dumps({"pid": __import__("os").getpid(), "purpose": "busy", "createdAtMs": radio.now_ms()}), encoding="utf-8")
                with self.assertRaises(radio.RadioError) as busy:
                    with radio.operation_lock("contender", timeout=0.05):
                        pass
                self.assertEqual("SPOTIFY_OPERATION_BUSY", busy.exception.code)
            finally:
                radio.remove_operation_lock()
                radio.OPERATION_LOCK = old_lock

    def test_provider_rejection_fails_before_receipt_poll(self):
        with mock.patch.object(radio, "rish", return_value="Bundle[{accepted=false}]") as invoke:
            with self.assertRaises(radio.RadioError) as rejected:
                radio.transport("status")
        self.assertEqual("SPOTIFY_PROVIDER_REJECTED", rejected.exception.code)
        self.assertEqual(1, invoke.call_count)

    def test_rolling_enable_requires_verified_playlist_and_policy(self):
        idle = {**radio.default_state(), "playlistId": "", "policyHash": ""}
        with mock.patch.object(radio, "load_state", return_value=idle),              mock.patch.object(radio, "SpotifyClient", side_effect=AssertionError("client constructed")):
            with self.assertRaises(radio.RadioError) as blocked:
                radio.handle_prompt("keep it rolling")
        self.assertEqual("SPOTIFY_RADIO_POLICY_REQUIRED", blocked.exception.code)

    def test_rolling_disable_is_local_and_network_free(self):
        state = {**radio.default_state(), "rolling": True, "playlistId": "playlist", "policyHash": "f" * 64}
        with mock.patch.object(radio, "load_state", return_value=state),              mock.patch.object(radio, "save_state") as save,              mock.patch.object(radio, "emit", return_value={"ok": True}),              mock.patch.object(radio, "SpotifyClient", side_effect=AssertionError("client constructed")):
            radio.handle_prompt("stop rolling")
        self.assertFalse(state["rolling"])
        save.assert_called_once()

    def test_sparse_vocals_biases_instrumental(self):
        plan = radio.compile_prompt("Make a driving synth playlist with sparse vocals")
        self.assertIn("instrumental", plan["policy"]["queries"])
        self.assertIn("vocals", plan["policy"]["avoid"])
        self.assertNotIn("vocals", plan["policy"]["queries"])

    def test_playlist_readback_requires_exact_sequence_and_snapshot(self):
        client = radio.SpotifyClient.__new__(radio.SpotifyClient)
        client.playlist_details = lambda playlist_id: {"snapshot_id": "snap-1", "public": False}
        client.playlist_items = lambda playlist_id: [{"uri": "spotify:track:A"}, {"uri": "spotify:track:B"}]
        self.assertEqual({"snapshotId": "snap-1", "itemCount": 2, "private": True}, client.verify_playlist_items("p", ["spotify:track:A", "spotify:track:B"], "snap-1"))
        with self.assertRaises(radio.RadioError) as mismatch:
            client.verify_playlist_items("p", ["spotify:track:B", "spotify:track:A"], "snap-1")
        self.assertEqual("SPOTIFY_PLAYLIST_READBACK_MISMATCH", mismatch.exception.code)

    def test_playlist_readback_rejects_public_playlist(self):
        client = radio.SpotifyClient.__new__(radio.SpotifyClient)
        client.playlist_details = lambda playlist_id: {"snapshot_id": "snap-1", "public": True}
        client.playlist_items = lambda playlist_id: [{"uri": "spotify:track:A"}]
        with self.assertRaises(radio.RadioError) as mismatch:
            client.verify_playlist_items("p", ["spotify:track:A"], "snap-1")
        self.assertEqual("SPOTIFY_PLAYLIST_READBACK_MISMATCH", mismatch.exception.code)

    def test_daemon_has_unexpected_error_survival(self):
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertIn("SPOTIFY_RADIO_DAEMON_ERROR", source)
        self.assertIn('with operation_lock("daemon-ensure")', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
