#!/usr/bin/env python3
"""RED owner-boundary fixture for provenance CLI evidence admission.

The existing owner still compares raw ``args.expected_head`` and silently applies
``max(0.0, args.max_index_age_hours)``. This fixture remains RED until the sole
provenance owner composes ``admit_cli_evidence`` before those values enter authority
or report logic. Source presence is not TESTED evidence.
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

        self.assertIn(
            "admit_cli_evidence",
            source,
            "RED: owner must compose the exact CLI evidence contract",
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


if __name__ == "__main__":
    unittest.main()
