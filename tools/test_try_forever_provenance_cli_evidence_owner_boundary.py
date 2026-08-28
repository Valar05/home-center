#!/usr/bin/env python3
"""RED owner-boundary fixture for provenance CLI evidence admission.

The sole provenance owner must compose the exact CLI evidence policy once before
expected-head or freshness inputs can influence authority or durable evidence.
This fixture is intentionally source-only until the owner surgery lands and an
authorized test lane executes it.
"""

import inspect
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe


class ProvenanceCliEvidenceOwnerBoundaryTest(unittest.TestCase):
    def test_owner_must_admit_cli_evidence_before_authority_logic(self):
        source = inspect.getsource(probe.main)
        module_source = inspect.getsource(probe)

        self.assertIn(
            "try_forever_provenance_cli_evidence_policy",
            module_source,
            "RED: sole owner must import the existing exact CLI evidence policy",
        )
        self.assertIn(
            "cli_evidence = admit_cli_evidence",
            source,
            "RED: owner must admit the CLI authority contract exactly once before use",
        )
        self.assertIn(
            "max_age_hours=cli_evidence.max_index_age_hours",
            source,
            "RED: generated-index freshness must use the admitted finite non-negative value",
        )
        self.assertIn(
            "cli_evidence.expected_head",
            source,
            "RED: expected-head authority must use the admitted canonical object id",
        )
        self.assertNotIn(
            "max_age_hours=max(0.0, args.max_index_age_hours)",
            source,
            "RED: negative/non-finite freshness input must not be normalized in place",
        )
        self.assertNotIn(
            "observed_head != args.expected_head",
            source,
            "RED: raw expected-head text must not enter authority comparison/report evidence",
        )
        self.assertNotIn(
            "if args.expected_head and",
            source,
            "RED: raw caller expected-head text must not remain an authority gate",
        )


if __name__ == "__main__":
    unittest.main()
