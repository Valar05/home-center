#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
sys.path.insert(0, str(TOOLS))


class AdamJarReceiptContractTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        os.environ["HC_STATE_DIR"] = self.temp.name
        os.environ["HC_ATOM_URL"] = "http://127.0.0.1:1"
        for name in ("judgement_jar_runtime", "adam_planned_venice_receipted"):
            sys.modules.pop(name, None)
        self.module = importlib.import_module("adam_planned_venice_receipted")

    def tearDown(self):
        self.temp.cleanup()
        os.environ.pop("HC_STATE_DIR", None)
        os.environ.pop("HC_ATOM_URL", None)
        for name in ("judgement_jar_runtime", "adam_planned_venice_receipted"):
            sys.modules.pop(name, None)

    def packet(self, output_kind: str | None = "plan") -> dict:
        value = {
            "tool": "submit_plan",
            "researchSummary": "real state inspected",
            "plan": ["bounded step"],
            "selectedJars": [
                ".continue/rules/00-judgement-jar-mission-boundary.md",
                ".continue/rules/10-judgement-jar-local-first.md",
            ],
            "jarRationale": "mission and compute boundaries",
            "antagonism": ["wrong owner"],
            "doneCondition": "receipt exists",
            "evidenceStandard": "readback",
        }
        if output_kind is not None:
            value["outputKind"] = output_kind
        return value

    def test_catalog_and_plan_packet_output_kind(self):
        jars = self.module.jar_catalog()
        self.assertEqual(len(jars), 8)
        self.assertEqual([jar["order"] for jar in jars], [0, 10, 20, 30, 40, 50, 70, 80])
        self.assertEqual(self.module.validate_plan_packet(self.packet()), (True, ""))
        ok, error = self.module.validate_plan_packet(self.packet(None))
        self.assertFalse(ok)
        self.assertIn("outputKind", error)
        ok, error = self.module.validate_plan_packet(self.packet("vibes"))
        self.assertFalse(ok)
        self.assertIn("outputKind", error)
        prompt = self.module.planning_system("test", ROOT)
        self.assertIn("JUDGMENT JAR RECEIPT CONTRACT", prompt)
        self.assertIn("outputKind", prompt)

    def test_plan_review_emits_one_review_verdict_receipt_per_selected_jar(self):
        self.module._ORIGINAL_PLAN_REVIEW = lambda *_args, **_kwargs: {
            "verdict": "PASS",
            "directive": "PLAN_ALLOWED",
            "planPermissionGranted": True,
            "reviewText": "VERDICT: PASS\nDIRECTIVE: PLAN_ALLOWED",
            "receipt": "receipt://plan-review",
        }
        review = self.module.review_plan_phone("task", ROOT, self.packet())
        self.assertEqual(len(review["jarUsageReceiptIds"]), 2)
        lines = self.module.jar_runtime.RECEIPTS_PATH.read_text(encoding="utf-8").splitlines()
        values = [json.loads(line) for line in lines]
        self.assertEqual({value["output"]["kind"] for value in values}, {"review_verdict"})
        self.assertEqual({value["metadata"]["plannedOutputKind"] for value in values}, {"plan"})

    def test_completion_review_receipts_all_binding_jars(self):
        self.module._ORIGINAL_COMPLETION_REVIEW = lambda *_args, **_kwargs: {
            "verdict": "PASS",
            "directive": "STOP_ALLOWED",
            "stopPermissionGranted": True,
            "reviewText": "VERDICT: PASS\nDIRECTIVE: STOP_ALLOWED",
            "receipt": "receipt://completion-review",
            "codeReviewFirst": True,
        }
        review = self.module.completion_review("task", ROOT, {"tool": "finish"}, "jars", [], None)
        self.assertEqual(len(review["jarUsageReceiptIds"]), 8)
        lines = self.module.jar_runtime.RECEIPTS_PATH.read_text(encoding="utf-8").splitlines()
        values = [json.loads(line) for line in lines]
        self.assertEqual(len(values), 8)
        self.assertEqual({value["output"]["kind"] for value in values}, {"review_verdict"})
        self.assertEqual({value["metadata"]["phase"] for value in values}, {"completion"})

    def test_router_and_selfheal_use_receipt_enforced_entrypoints(self):
        adam_source = (TOOLS / "adam.py").read_text(encoding="utf-8")
        selfheal_source = (TOOLS / "venice_review_selfheal.sh").read_text(encoding="utf-8")
        self.assertIn("adam_planned_venice_receipted.py", adam_source)
        self.assertIn("venice_review_receipted.py", selfheal_source)


if __name__ == "__main__":
    unittest.main()
