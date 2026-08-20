#!/usr/bin/env python3
"""Owner-boundary regression source for strict generated-index JSON admission.

The sole provenance owner is now SOURCE_WIRED to the existing strict JSON policy.
This fixture preserves the promotion contract but remains REGRESSION_SOURCE /
UNEXECUTED until an authorized test body executes it on the exact reviewed head.
"""

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


class GeneratedIndexJsonOwnerBoundaryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (TOOLS_DIR / "try_forever_skill_provenance_probe.py").read_text(
            encoding="utf-8"
        )

    def test_owner_imports_strict_json_policy(self):
        self.assertIn(
            "from try_forever_generated_index_json_policy import (",
            self.source,
        )
        self.assertIn("GeneratedIndexJsonError", self.source)
        self.assertIn("parse_generated_index_json", self.source)

    def test_owner_no_longer_uses_default_last_wins_json_loads(self):
        self.assertNotIn("data = json.loads(observation.utf8_text)", self.source)
        self.assertIn(
            "data = parse_generated_index_json(observation.utf8_text)",
            self.source,
        )

    def test_owner_maps_strict_json_failure_to_unresolved_not_process_crash(self):
        self.assertIn("GeneratedIndexJsonError", self.source)
        self.assertIn(
            'reason=f"generated index is unreadable strict UTF-8 JSON: {type(error).__name__}"',
            self.source,
        )


if __name__ == "__main__":
    unittest.main()
