#!/usr/bin/env python3
"""RED owner-report fixture for authority-facing CLI evidence auditability.

A durable provenance verdict must state the exact admitted expected-head binding
and generated-index freshness window that governed it. Adding this authority
input contract changes the report contract, so the sole owner must advance the
schema explicitly rather than slipping an undocumented field into v5.
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
            '"schema": "try-forever-skill-provenance.v6"',
            source,
            "RED: adding durable authority-input evidence requires an explicit schema revision",
        )
        self.assertNotIn(
            '"schema": "try-forever-skill-provenance.v5"',
            source,
            "RED: v5 must not silently acquire a new authority-evidence contract",
        )
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
        self.assertIn(
            "cli_evidence.expected_head",
            source,
            "RED: report evidence must derive from admitted expected-head state",
        )
        self.assertIn(
            "cli_evidence.max_index_age_hours",
            source,
            "RED: report evidence must derive from admitted freshness state",
        )


if __name__ == "__main__":
    unittest.main()
