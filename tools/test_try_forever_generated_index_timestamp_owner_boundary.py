#!/usr/bin/env python3
"""RED owner-boundary fixture for exact generated-index timestamp admission.

Regression source only. It remains intentionally RED until the sole provenance
owner delegates timestamp admission to the exact timestamp policy.
"""

import inspect
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe


class GeneratedIndexTimestampOwnerBoundaryTest(unittest.TestCase):
    def test_owner_must_delegate_to_exact_timestamp_policy(self):
        source = inspect.getsource(probe.parse_timestamp)
        self.assertIn(
            "parse_generated_index_timestamp",
            source,
            "RED: owner timestamp adapter must delegate to the exact policy",
        )
        self.assertNotIn(
            ".strip()",
            source,
            "RED: owner must not normalize edge evidence before timestamp admission",
        )

    def test_owner_rejects_normalization_dependent_timestamp_text(self):
        for value in (
            " 2026-08-19T22:02:12Z",
            "2026-08-19T22:02:12Z ",
            "\t2026-08-19T22:02:12Z",
            "2026-08-19T22:02:12Z\n",
            "\u202e2026-08-19T22:02:12Z",
        ):
            with self.subTest(value=repr(value)):
                self.assertIsNone(
                    probe.parse_timestamp(value),
                    "RED: normalization-dependent timestamp evidence must fail closed",
                )

    def test_owner_preserves_existing_accepted_timestamp_shapes(self):
        exact = probe.parse_timestamp("2026-08-19T22:02:12Z")
        numeric = probe.parse_timestamp(1787176932)
        self.assertIsNotNone(exact)
        self.assertIsNotNone(numeric)
        self.assertEqual(0, exact.utcoffset().total_seconds())
        self.assertEqual(0, numeric.utcoffset().total_seconds())


if __name__ == "__main__":
    unittest.main()
