#!/usr/bin/env python3

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe


class GeneratedIndexIngressBudgetTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 8, 18, 20, 7, 11, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def inspect(self, path: Path):
        return probe.inspect_generated_index(
            path,
            current_head="abc123",
            current_tree_dirty=False,
            max_age_hours=24.0,
            now=self.now,
        )

    def test_malformed_utf8_becomes_bounded_unresolved_verdict_instead_of_exception(self):
        path = self.root / "index.json"
        path.write_bytes(b"\xff\xfe{not-utf8}")

        verdict = self.inspect(path)

        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("UnicodeDecodeError", verdict.reason)

    def test_oversized_index_is_rejected_before_json_authority(self):
        path = self.root / "index.json"
        budget = getattr(probe, "MAX_GENERATED_INDEX_BYTES", 1024 * 1024)
        path.write_bytes(b" " * budget + b"{}")

        verdict = self.inspect(path)

        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("byte budget", verdict.reason)

    def test_small_valid_index_keeps_existing_verified_current_semantics(self):
        path = self.root / "index.json"
        path.write_text(
            json.dumps(
                {
                    "sourceHead": "abc123",
                    "generatedAt": self.now.isoformat(),
                    "dirtySource": False,
                }
            ),
            encoding="utf-8",
        )

        verdict = self.inspect(path)

        self.assertEqual("VERIFIED_CURRENT", verdict.status)
        self.assertEqual("abc123", verdict.source_head)
        self.assertFalse(verdict.dirty_source)


if __name__ == "__main__":
    unittest.main()
