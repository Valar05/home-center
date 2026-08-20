#!/usr/bin/env python3
"""RED owner boundary for exact generated-index sourceHead admission.

The supporting policy exists, but the sole provenance owner must consume it before a
malformed declared sourceHead can be distinguished from an ordinary stale canonical
Git identity. This fixture stays RED until that reviewed owner wiring lands.
"""

import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
OWNER = (TOOLS_DIR / "try_forever_skill_provenance_probe.py").read_text(encoding="utf-8")


class GeneratedIndexSourceHeadOwnerBoundaryTest(unittest.TestCase):
    def test_owner_imports_exact_source_head_policy(self):
        self.assertIn("try_forever_generated_index_source_head_policy", OWNER)
        self.assertIn("admit_generated_index_source_head", OWNER)

    def test_owner_rejects_source_head_contract_before_stale_comparison(self):
        admission_index = OWNER.index("admit_generated_index_source_head")
        comparison_index = OWNER.index("source_head != current_head")
        self.assertLess(admission_index, comparison_index)

    def test_owner_has_typed_source_head_rejection_surface(self):
        self.assertIn("GeneratedIndexSourceHeadError", OWNER)
        self.assertIn("generated index source head contract rejected", OWNER)


if __name__ == "__main__":
    unittest.main()
