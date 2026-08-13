#!/usr/bin/env python3
from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


class JudgmentJarUsageEnforcementTest(unittest.TestCase):
    def test_context_use_fails_closed_without_receipt(self):
        module = importlib.import_module("judgment_jars")
        jar = {"id": "mission-boundary", "title": "Mission Boundary", "sourcePath": ".continue/rules/00-judgement-jar-mission-boundary.md"}
        with patch.object(module, "record_receipt", return_value={"ok": False, "state": "FAILED"}):
            with self.assertRaises(module.ReceiptError):
                module.context_receipt({}, jar, {}, "packet", "test", "load", "return", "input")

    def test_vlad_fast_surface_preserves_normal_vlad(self):
        module = importlib.import_module("vlad")
        with patch.object(module.judgment_jars, "main", return_value=0) as jars:
            self.assertEqual(module.main(["jar", "mission-boundary"]), 0)
            jars.assert_called_once_with(["get", "mission-boundary"])
        with patch.object(module.jar_receipt, "main", return_value=0) as receipt:
            self.assertEqual(module.main(["jar", "receipt", "mission-boundary", "plan", "body"]), 0)
            receipt.assert_called_once_with(["record", "mission-boundary", "plan", "body"])
        with patch.object(module.adam, "run_mode", return_value=0) as review:
            self.assertEqual(module.main(["challenge", "this"]), 0)
            self.assertEqual(review.call_args.args[0], "vlad")

    def test_plan_requires_controlled_output_kind(self):
        module = importlib.import_module("adam_planned_venice_receipted")
        original_validate = module._ORIGINAL_VALIDATE
        original_read = module.read_config
        try:
            module._ORIGINAL_VALIDATE = lambda _action: (True, "")
            module.read_config = lambda _path: {"receipts": {"outputKinds": ["plan", "answer"]}}
            self.assertEqual(module.validate_plan_packet({"outputKind": "plan"}), (True, ""))
            ok, error = module.validate_plan_packet({})
            self.assertFalse(ok); self.assertIn("outputKind", error)
            ok, error = module.validate_plan_packet({"outputKind": "vibes"})
            self.assertFalse(ok); self.assertIn("outputKind", error)
        finally:
            module._ORIGINAL_VALIDATE = original_validate
            module.read_config = original_read

    def test_every_canonical_phase_names_output_kind(self):
        source = (TOOLS / "adam_planned_venice_receipted.py").read_text(encoding="utf-8")
        for token in [
            'output_kind="context_packet"',
            'output_kind="review_verdict"',
            'output_kind=_CURRENT_OUTPUT_KIND',
            'source="adam.preflight.selected-jar-context"',
            'source="adam.execution.active-jar-context"',
            'source="adam.preflight.venice-plan-review"',
            'source="adam.completion.venice-review"',
            'source="adam.task.output"',
        ]:
            self.assertIn(token, source)

    def test_canonical_installed_entrypoints_are_receipted(self):
        adam = (TOOLS / "adam.py").read_text(encoding="utf-8")
        selfheal = (TOOLS / "venice_review_selfheal.sh").read_text(encoding="utf-8")
        setup = (TOOLS / "setup_vlad_swarm_daemon.sh").read_text(encoding="utf-8")
        self.assertIn("adam_planned_venice_receipted.py", adam)
        self.assertIn("venice_review_receipted.py", selfheal)
        self.assertIn('VLAD_BIN="$BIN_DIR/vlad"', setup)
        self.assertIn("sameDaemonSync", setup)
        self.assertNotIn("judgment-jar-receipt-daemon", setup)

    def test_capability_states_remain_separate(self):
        receipt_source = (TOOLS / "judgment_jar_receipts.py").read_text(encoding="utf-8")
        self.assertIn('"state": "PENDING_HOME_CENTER"', receipt_source)
        self.assertIn('"state": "DELIVERED_HOME_CENTER"', receipt_source)
        self.assertIn("sorted((p[\"pending\"]).glob(\"*.json\"))", receipt_source)
        self.assertIn("jarSourceSha256", receipt_source)


if __name__ == "__main__":
    unittest.main()
