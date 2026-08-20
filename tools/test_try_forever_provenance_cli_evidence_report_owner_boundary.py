#!/usr/bin/env python3
"""RED owner-report fixture for authority-facing CLI evidence auditability.

The generated-index currentness verdict depends on the admitted freshness window,
and repository certification may depend on an expected-head binding. A durable
report must therefore state the exact admitted policy inputs that governed it.
This remains regression source, not executed test evidence.
"""

import inspect
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe


class ProvenanceCliEvidenceReportOwnerBoundaryTest(unittest.TestCase):
    def test_report_must_expose_admitted_authority_input_contract(self):
        source = inspect.getsource(probe.main)

        self.assertIn(
            '"cliEvidence"',
            source,
            "RED: durable report must identify the admitted authority-input contract",
        )
        self.assertIn(
            '"expectedHead"',
            source,
            "RED: report must preserve the exact admitted expected-head binding",
        )
        self.assertIn(
            '"maxIndexAgeHours"',
            source,
            "RED: VERIFIED_CURRENT is not auditable without the freshness window used",
        )


if __name__ == "__main__":
    unittest.main()
