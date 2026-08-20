#!/usr/bin/env python3
"""RED owner-boundary fixture for exact generated-index timestamp admission."""

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe


class GeneratedIndexTimestampOwnerBoundaryTest(unittest.TestCase):
    def test_owner_must_not_strip_edge_whitespace_into_timestamp_authority(self):
        self.assertIsNone(
            probe.parse_timestamp(" 2026-08-19T22:02:12Z"),
            "RED: current owner broad-strips timestamp evidence before parsing",
        )


if __name__ == "__main__":
    unittest.main()
