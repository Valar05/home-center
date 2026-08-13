#!/usr/bin/env python3
from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


class AdamJarReceiptContractTest(unittest.TestCase):
    def test_plan_packet_requires_controlled_output_kind(self):
        module = importlib.import_module("adam_planned_venice_receipted")
        original_validate = module._ORIGINAL_VALIDATE
        original_kinds = module.usage.output_kinds
        original_read = module.read_config
        try:
            module._ORIGINAL_VALIDATE = lambda _action: (True, "")
            module.usage.output_kinds = lambda _config: frozenset({"plan", "answer"})
            module.read_config = lambda _path: {}
            self.assertEqual(module.validate_plan_packet({"outputKind": "plan"}), (True, ""))
            ok, error = module.validate_plan_packet({})
            self.assertFalse(ok)
            self.assertIn("outputKind", error)
            ok, error = module.validate_plan_packet({"outputKind": "vibes"})
            self.assertFalse(ok)
            self.assertIn("outputKind", error)
        finally:
            module._ORIGINAL_VALIDATE = original_validate
            module.usage.output_kinds = original_kinds
            module.read_config = original_read

    def test_canonical_entrypoints_are_receipt_enforced(self):
        adam = (TOOLS / "adam.py").read_text(encoding="utf-8")
        installer = (TOOLS / "install_adam_cli.sh").read_text(encoding="utf-8")
        selfheal = (TOOLS / "venice_review_selfheal.sh").read_text(encoding="utf-8")
        vlad = (TOOLS / "vlad.py").read_text(encoding="utf-8")
        self.assertIn("adam_planned_venice_receipted.py", adam)
        self.assertIn("adam_planned_venice_receipted.py", installer)
        self.assertIn("venice_review_receipted.py", selfheal)
        self.assertIn("judgment_jars.main", vlad)
        self.assertIn('run_mode("vlad"', vlad)

    def test_every_canonical_phase_names_its_output_kind(self):
        source = (TOOLS / "adam_planned_venice_receipted.py").read_text(encoding="utf-8")
        self.assertIn('output_kind="context_packet"', source)
        self.assertIn('output_kind="review_verdict"', source)
        self.assertIn("output_kind=_CURRENT_OUTPUT_KIND", source)
        self.assertIn('source="adam.preflight.selected-jar-context"', source)
        self.assertIn('source="adam.execution.active-jar-context"', source)
        self.assertIn('source="adam.preflight.venice-plan-review"', source)
        self.assertIn('source="adam.completion.venice-review"', source)
        self.assertIn('source="adam.task.output"', source)

    def test_no_second_registry_or_watcher_is_introduced(self):
        receipt_source = (TOOLS / "judgment_jar_receipts.py").read_text(encoding="utf-8")
        daemon_source = (TOOLS / "vlad_swarm_daemon.py").read_text(encoding="utf-8")
        setup_source = (TOOLS / "setup_vlad_swarm_daemon.sh").read_text(encoding="utf-8")
        self.assertIn("from judgment_jar_registry import resolve_jar", receipt_source)
        self.assertIn("sync_judgment_jars(repo_root)", daemon_source)
        self.assertNotIn("judgment-jar-receipt-daemon", setup_source)
        self.assertIn("sameDaemonSync", setup_source)

    def test_usage_receipt_contract_keeps_capability_states_separate(self):
        source = (TOOLS / "judgment_jar_receipts.py").read_text(encoding="utf-8")
        self.assertIn('"captureState": "CAPTURED"', source)
        self.assertIn('"homeCenterDeliveryState": "PENDING"', source)
        self.assertIn('"homeCenterDeliveryState": "DELIVERED"', source)
        self.assertIn("for path in sorted(state[\"outbox\"].glob(\"*.json\"))", source)
        self.assertIn("jar_source_changed_before_delivery", source)


if __name__ == "__main__":
    unittest.main()
