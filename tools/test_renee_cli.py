#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "tools" / "renee.py"


def run_cli(*args, home):
    env = dict(os.environ)
    env["RENEE_QA_HOME"] = str(home)
    return subprocess.run([sys.executable, str(CLI), "--json", *args], cwd=ROOT, env=env, text=True, capture_output=True)


class ReneeCliContract(unittest.TestCase):
    def test_status_is_deterministic_and_names_keyword(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("status", home=td)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["keyword"], "Rene QA")

    def test_review_writes_receipt_and_does_not_grant_final_stop(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("review", "tool exists", "--acceptance", "repo file present", home=td)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["verdict"], "PASS")
            self.assertFalse(payload["can_grant_final_stop"])
            self.assertEqual(payload["next_gate"], "Venice")
            self.assertTrue(Path(payload["receipt_path"]).exists())

    def test_deployed_claim_requires_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("review", "service deployed", "--state", "deployed", home=td)
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["verdict"], "REVISE_REQUIRED")
            self.assertTrue(any("no supplied receipt" in x for x in payload["blockers"]))

    def test_synthetic_cannot_claim_actual_renee(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("review", "Renee approved", "--actual-renee", home=td)
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertTrue(any("actual-Renee attribution" in x for x in payload["blockers"]))

    def test_correction_rejects_synthetic_provenance_at_parser(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("correct", "rqa-x", "wrong", "--provenance", "SYNTHETIC_RENEE", "--source", "synthetic", home=td)
            self.assertNotEqual(result.returncode, 0)

    def test_precedent_prefers_direct_human_over_recall(self):
        with tempfile.TemporaryDirectory() as td:
            for provenance, text in [("DREW_RECALL", "reachable state"), ("RENEE_DIRECT", "reachable state")]:
                result = run_cli("correct", "rqa-x", text, "--provenance", provenance, "--source", provenance.lower(), home=td)
                self.assertEqual(result.returncode, 0, result.stderr)
            result = run_cli("precedent", "reachable state", home=td)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["matches"][0]["provenance"], "RENEE_DIRECT")


if __name__ == "__main__":
    unittest.main()
