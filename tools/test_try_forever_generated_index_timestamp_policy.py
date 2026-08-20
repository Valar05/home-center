#!/usr/bin/env python3

import sys
import unittest
from datetime import timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_generated_index_timestamp_policy import (
    GeneratedIndexTimestampError,
    parse_generated_index_timestamp,
)


class GeneratedIndexTimestampPolicyTest(unittest.TestCase):
    def test_exact_z_timestamp_is_accepted(self):
        parsed = parse_generated_index_timestamp("2026-08-19T22:02:12Z")
        self.assertEqual(timezone.utc, parsed.tzinfo)
        self.assertEqual(2026, parsed.year)

    def test_naive_timestamp_keeps_existing_utc_compatibility(self):
        parsed = parse_generated_index_timestamp("2026-08-19T22:02:12")
        self.assertEqual(timezone.utc, parsed.tzinfo)

    def test_edge_whitespace_is_rejected_not_stripped(self):
        for value in (
            " 2026-08-19T22:02:12Z",
            "2026-08-19T22:02:12Z ",
            "\t2026-08-19T22:02:12Z",
        ):
            with self.subTest(value=repr(value)):
                with self.assertRaises(GeneratedIndexTimestampError):
                    parse_generated_index_timestamp(value)

    def test_bool_and_nonfinite_numbers_are_rejected(self):
        for value in (True, False, float("inf"), float("nan")):
            with self.subTest(value=repr(value)):
                with self.assertRaises(GeneratedIndexTimestampError):
                    parse_generated_index_timestamp(value)


if __name__ == "__main__":
    unittest.main()
