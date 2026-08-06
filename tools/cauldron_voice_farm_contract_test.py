#!/usr/bin/env python3
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FARM = ROOT / "local" / "cauldron_voice_farm"
SPEC = importlib.util.spec_from_file_location("preflight", FARM / "cauldron_voice_preflight.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class ContractTest(unittest.TestCase):
    def test_required_files_and_no_deployment_claim(self):
        for name in ["README.md", "models.v1.json", "canaries.v1.json", "install.ps1", "control.ps1", "run_canaries.ps1"]:
            self.assertTrue((FARM / name).is_file(), name)
        readme = (FARM / "README.md").read_text(encoding="utf-8")
        self.assertIn("does **not** install a service", " ".join(readme.split()))
        self.assertIn("No public or LAN listener is created", readme)

    def test_model_manifest_keeps_turbo_bounded_and_f5_excluded(self):
        manifest = json.loads((FARM / "models.v1.json").read_text(encoding="utf-8"))
        candidates = {item["id"]: item for item in manifest["candidates"]}
        self.assertEqual(set(candidates), {"kokoro-onnx-v1", "chatterbox-nano", "chatterbox-turbo"})
        self.assertEqual(candidates["chatterbox-turbo"]["vramCeilingBytes"], 4 * 1024**3)
        self.assertEqual(manifest["excluded"][0]["id"], "f5-tts")

    def test_split_is_automatic_ordered_and_bounded(self):
        text = "First sentence stays first. Second sentence stays second. Third sentence stays third."
        plan = MODULE.split_text(text, 40)
        self.assertTrue(plan["automatic"])
        self.assertFalse(plan["separateSplitOperation"])
        segments = [item["text"] for item in plan["segments"]]
        self.assertEqual(" ".join(segments), text)
        self.assertTrue(all(0 < len(item) <= 40 for item in segments))

    def test_request_identity_detects_change(self):
        first, _ = MODULE.request_identity("kokoro", "hello", "af_heart", "", 320)
        repeat, _ = MODULE.request_identity("kokoro", "hello", "af_heart", "", 320)
        changed, _ = MODULE.request_identity("kokoro", "goodbye", "af_heart", "", 320)
        self.assertEqual(first, repeat)
        self.assertNotEqual(first, changed)

    def test_consent_requires_exact_hash_and_use(self):
        with tempfile.TemporaryDirectory() as temp:
            reference = Path(temp) / "voice.wav"
            reference.write_bytes(b"owned-reference")
            digest = hashlib.sha256(reference.read_bytes()).hexdigest()
            consent = Path(temp) / "voice.wav.consent.json"
            consent.write_text(json.dumps({
                "schemaVersion": MODULE.CONSENT_SCHEMA_VERSION,
                "speakerOwner": "Adult Speaker",
                "consentAuthority": "Adult Speaker",
                "permittedUses": ["local_tts_clone"],
                "referenceSha256": digest,
            }), encoding="utf-8")
            self.assertEqual(MODULE.validate_consent(reference, consent)["referenceSha256"], digest)
            consent.write_text(consent.read_text().replace(digest, "0" * 64), encoding="utf-8")
            with self.assertRaisesRegex(MODULE.PreflightError, "REFERENCE_HASH_MISMATCH"):
                MODULE.validate_consent(reference, consent)

    def test_empty_text_and_unknown_engine_fail(self):
        with self.assertRaisesRegex(MODULE.PreflightError, "EMPTY_TEXT"):
            MODULE.split_text("  ")
        with self.assertRaisesRegex(MODULE.PreflightError, "ENGINE_UNSUPPORTED"):
            MODULE.request_identity("adjacent-substitute", "text", "voice", "", 320)

    def test_uninstall_and_public_listener_boundaries_are_literal(self):
        control = (FARM / "control.ps1").read_text(encoding="utf-8")
        self.assertIn("UNINSTALL_REQUIRES_APPROVED", control)
        self.assertIn("REFUSED_ROOT_OUTSIDE_VOICE_FARM", control)
        self.assertIn("publicListenerCreated=$false", control)


if __name__ == "__main__":
    unittest.main()
