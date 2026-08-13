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
            result = run_cli("review", "tool exists", "--acceptance", "repo file present", "--failure-path", "missing config", home=td)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["verdict"], "PASS")
            self.assertFalse(payload["can_grant_final_stop"])
            self.assertEqual(payload["next_gate"], "Venice")
            self.assertIn("missing config", payload["reachable_failure_paths"])
            self.assertTrue(Path(payload["receipt_path"]).exists())

    def test_tested_claim_requires_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("review", "tests passed", "--state", "tested", "--acceptance", "tests pass", home=td)
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertTrue(any("tested claim" in x for x in payload["blockers"]))

    def test_missing_acceptance_is_a_blocker(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("review", "tool exists", home=td)
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertTrue(any("acceptance criterion" in x for x in payload["blockers"]))

    def test_unresolved_material_issue_forces_revision(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("review", "tool exists", "--acceptance", "repo file present", "--unresolved", "cannot reproduce crash", home=td)
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertTrue(any("cannot reproduce crash" in x for x in payload["blockers"]))

    def test_synthetic_cannot_claim_actual_renee(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("review", "Renee approved", "--acceptance", "human approval attributable", "--actual-renee", home=td)
            self.assertEqual(result.returncode, 2)
            payload = json.loads(result.stdout)
            self.assertTrue(any("actual-Renee attribution" in x for x in payload["blockers"]))

    def test_record_rejects_derived_rule_without_sources(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("record", "reachable states count", "--provenance", "DERIVED_RULE", "--source", "generalization", home=td)
            self.assertNotEqual(result.returncode, 0)

    def test_record_direct_precedent_and_query_it(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("record", "reachable state is product state", "--provenance", "RENEE_DIRECT", "--source", "authorized-chat:123", "--tag", "failure-path", home=td)
            self.assertEqual(result.returncode, 0, result.stderr)
            record = json.loads(result.stdout)
            self.assertEqual(record["provenance"], "RENEE_DIRECT")
            result = run_cli("precedent", "reachable state", home=td)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["matches"][0]["fingerprint"], record["fingerprint"])

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

    def test_regress_surfaces_human_regression_target(self):
        with tempfile.TemporaryDirectory() as td:
            result = run_cli("correct", "rqa-x", "you missed offline mode", "--provenance", "RENEE_CORRECTION", "--source", "authorized-chat:456", "--regression-target", "always inspect offline mode", home=td)
            self.assertEqual(result.returncode, 0, result.stderr)
            result = run_cli("regress", home=td)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["human_regression_targets"][0]["regression_target"], "always inspect offline mode")


if __name__ == "__main__":
    unittest.main()
