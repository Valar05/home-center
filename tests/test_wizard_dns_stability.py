#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "agent-tools" / "wizard_dns.py"
spec = importlib.util.spec_from_file_location("wizard_dns", MODULE_PATH)
assert spec and spec.loader
wizard_dns = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wizard_dns)


class WizardDnsStabilityTests(unittest.TestCase):
    def test_stable_mode_refuses_zero_information_probe(self):
        case = wizard_dns.Case(
            name="zero-info",
            hypotheses=[
                wizard_dns.Hypothesis("a", {}),
                wizard_dns.Hypothesis("b", {}),
            ],
            probes=[
                wizard_dns.Probe("cheap", "literal", {"value": True}, cost=1),
                wizard_dns.Probe("expensive", "literal", {"value": False}, cost=5),
            ],
        )
        self.assertEqual(wizard_dns.choose_probe(case).name, "cheap")
        self.assertIsNone(wizard_dns.choose_probe(case, require_separation=True))

    def test_stable_mode_runs_separating_probe_then_stops(self):
        case = wizard_dns.Case(
            name="separating",
            hypotheses=[
                wizard_dns.Hypothesis("authoritative-wrong", {"auth": "wrong"}),
                wizard_dns.Hypothesis("cache", {"auth": "right"}),
            ],
            probes=[
                wizard_dns.Probe("auth", "literal", {"value": "right"}, cost=1),
                wizard_dns.Probe("leftover", "literal", {"value": "noise"}, cost=1),
            ],
        )
        probe, receipt = wizard_dns.step(case, require_separation=True)
        self.assertIsNotNone(probe)
        self.assertEqual(probe.name, "auth")
        self.assertTrue(receipt.ok)
        self.assertEqual([h.name for h in wizard_dns.survivors(case)], ["cache"])
        probe2, receipt2 = wizard_dns.step(case, require_separation=True)
        self.assertIsNone(probe2)
        self.assertIsNone(receipt2)
        self.assertNotIn("leftover", case.observations)


if __name__ == "__main__":
    unittest.main()
