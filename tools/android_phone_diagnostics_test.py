from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from android_phone_diagnostics import DiagnosticsEngine, canonical_bytes, digest


def action(kind: str, **changes):
    value = {
        "action": "phone_diagnostics",
        "schema": "phone.diagnostics.request.v1",
        "diagnosticKind": kind,
        "deviceId": "primary-phone",
        "packageId": "com.termux",
        "workerId": "phone-relay:primary-phone",
        "queueDocId": "queue-doc",
        "queueRevision": "revision-1",
        "commissionHash": "a" * 64,
        "laneId": "phone-diagnostics",
        "sessionId": "session-1",
        "streamId": "stream-1",
        "chunkIndex": 0,
        "maxEntries": 20,
        "maxBytes": 65536,
    }
    value.update(changes)
    return value


class DiagnosticsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.outside = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.engine = DiagnosticsEngine({"GODOT_PROJECTS": self.root})

    def tearDown(self):
        self.temp.cleanup()
        self.outside.cleanup()

    def test_rejects_arbitrary_command_args_and_unknown_fields(self):
        for key, value in (("command", "rm -rf x"), ("argv", ["git", "status"]), ("path", "/tmp")):
            with self.subTest(key=key), self.assertRaises(ValueError):
                self.engine.execute(action("capability_snapshot", **{key: value}))
        with self.assertRaises(ValueError):
            self.engine.execute(action("capability_snapshot", maxEntries="200"))
        with self.assertRaises(PermissionError):
            self.engine.execute(action("capability_snapshot", rootId="GODOT_PROJECTS"))

    def test_rejects_wrong_device_package_worker_root_and_commission(self):
        bad = [
            action("capability_snapshot", deviceId="other-phone"),
            action("capability_snapshot", packageId="other.package"),
            action("capability_snapshot", workerId="worker:other"),
            action("tree_inventory", rootId="HOME"),
            action("capability_snapshot", commissionHash="forged"),
        ]
        for value in bad:
            with self.subTest(value=value), self.assertRaises((ValueError, PermissionError)):
                self.engine.execute(value)

    def test_tree_skips_hidden_secret_binary_and_symlink_escape(self):
        (self.root / "project.godot").write_text("[application]\n")
        (self.root / ".hidden").mkdir()
        (self.root / ".hidden" / "memory.md").write_text("hidden")
        (self.root / ".env").write_text("TOKEN=do-not-read")
        (self.root / "access_token_notes.md").write_text("do-not-read")
        (Path(self.outside.name) / "outside.md").write_text("outside")
        os.symlink(Path(self.outside.name), self.root / "escape")
        receipt = self.engine.execute(action("tree_inventory", rootId="GODOT_PROJECTS"))
        result = receipt["result"]
        names = [item["relativePath"] for item in result["entries"]]
        self.assertEqual(names, ["project.godot"])
        self.assertGreaterEqual(result["skipped"]["hidden"], 2)
        self.assertGreaterEqual(result["skipped"]["secret"], 1)
        self.assertEqual(result["skipped"]["symlink"], 1)
        self.assertFalse(receipt["networkUsed"])
        self.assertFalse(receipt["writeUsed"])
        self.assertFalse(receipt["subprocessUsed"])

    def test_manifest_hashes_only_allowlisted_small_text(self):
        (self.root / "project.godot").write_text("[application]\n")
        (self.root / "large.md").write_bytes(b"x" * (1024 * 1024 + 1))
        (self.root / "image.png").write_bytes(b"png")
        receipt = self.engine.execute(action(
            "file_manifest", rootId="GODOT_PROJECTS", extensions=[".godot", ".md"]))
        by_name = {item["relativePath"]: item for item in receipt["result"]["entries"]}
        self.assertEqual(by_name["project.godot"]["hashState"], "HASHED")
        self.assertEqual(by_name["large.md"]["hashState"], "TOO_LARGE")
        self.assertNotIn("image.png", by_name)
        with self.assertRaises(PermissionError):
            self.engine.execute(action(
                "file_manifest", rootId="GODOT_PROJECTS", extensions=[".apk"]))

    def test_budgets_chunk_and_resume_without_duplicate(self):
        for name in ("a.md", "b.md", "c.md"):
            (self.root / name).write_text(name)
        first = self.engine.execute(action(
            "tree_inventory", rootId="GODOT_PROJECTS", maxEntries=1))["result"]
        self.assertEqual(first["status"], "MORE")
        self.assertEqual(first["entryCount"], 1)
        second = self.engine.execute(action(
            "tree_inventory", rootId="GODOT_PROJECTS", maxEntries=5,
            streamId="stream-1", chunkIndex=1,
            watermark=first["watermarkAfter"], previousChunkHash=first["chunkHash"]))["result"]
        self.assertEqual(second["status"], "COMPLETE")
        self.assertNotIn(first["entries"][0]["relativePath"],
                         [item["relativePath"] for item in second["entries"]])
        self.assertEqual(second["previousChunkHash"], first["chunkHash"])

    def test_interruption_resume_hash_and_zero_file_truth_are_sensitive(self):
        empty = self.engine.execute(action(
            "tree_inventory", rootId="GODOT_PROJECTS"))["result"]
        self.assertEqual(empty["observedEntryCount"], 0)
        forged = json.loads(canonical_bytes(empty))
        forged["observedEntryCount"] = 4
        self.assertNotEqual(empty["chunkHash"], digest({
            key: value for key, value in forged.items()
            if key not in {"chunkHash", "status", "byteCount"}
        }))
        with self.assertRaises(PermissionError):
            self.engine.execute(action(
                "tree_inventory", rootId="GODOT_PROJECTS", watermark="../escape"))

    def test_timeout_cannot_claim_complete_and_root_symlink_is_rejected(self):
        (self.root / "one.md").write_text("one")
        with mock.patch("android_phone_diagnostics.time.monotonic", side_effect=[0.0, 9.0]):
            result = self.engine.execute(action("tree_inventory", rootId="GODOT_PROJECTS"))["result"]
        self.assertFalse(result["scanComplete"])
        self.assertEqual(result["status"], "MORE")
        linked = Path(self.outside.name) / "linked"
        os.symlink(self.root, linked)
        with self.assertRaises(PermissionError):
            DiagnosticsEngine({"GODOT_PROJECTS": linked}).execute(
                action("tree_inventory", rootId="GODOT_PROJECTS"))

    def test_repo_status_never_reads_remotes_or_claims_clean(self):
        git = self.root / "demo" / ".git"
        (git / "refs" / "heads").mkdir(parents=True)
        (git / "HEAD").write_text("ref: refs/heads/main\n")
        (git / "refs" / "heads" / "main").write_text("b" * 40 + "\n")
        (git / "config").write_text("[remote \"origin\"]\nurl=https://token@example.invalid/repo\n")
        result = self.engine.execute(action(
            "repo_status", rootId="GODOT_PROJECTS"))["result"]
        self.assertEqual(result["entries"][0]["head"], "b" * 40)
        self.assertEqual(result["entries"][0]["dirtyState"], "UNKNOWN_NO_GIT_EXEC")
        self.assertEqual(result["entries"][0]["remoteDisclosure"], "REDACTED_NOT_READ")
        self.assertNotIn("example.invalid", json.dumps(result))

    def test_toolchain_probe_does_not_execute_tools(self):
        fake = self.root / "git"
        fake.write_bytes(b"tool")
        with mock.patch("android_phone_diagnostics.shutil.which", return_value=str(fake)), \
             mock.patch("android_phone_diagnostics.ALLOWED_TOOL_PREFIXES", (str(self.root) + "/",)):
            receipt = self.engine.execute(action("toolchain_probe"))
        self.assertTrue(receipt["result"]["tools"])
        self.assertTrue(all(item.get("version") == "UNKNOWN_NO_EXEC" for item in receipt["result"]["tools"]))
        self.assertFalse(receipt["subprocessUsed"])

    def test_receipt_is_identity_sensitive_and_postback_pending(self):
        first = self.engine.execute(action("capability_snapshot"))
        second = self.engine.execute(action("capability_snapshot", sessionId="session-2"))
        self.assertNotEqual(first["receiptHash"], second["receiptHash"])
        self.assertEqual(first["artifactPostback"]["state"], "PENDING_HOME_CENTER_POSTBACK")
        self.assertFalse(first["artifactPostback"]["durable"])


if __name__ == "__main__":
    unittest.main()
