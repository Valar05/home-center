#!/usr/bin/env python3
"""RED owner-boundary fixture for single-artifact SKILL.md custody.

This source is intentionally expected to fail against the current owner until the
sole provenance probe composes ``observe_skill_content``. It is regression source,
not passing-test evidence.
"""

import inspect
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe


class SkillContentCustodyOwnerBoundaryTest(unittest.TestCase):
    def test_owner_must_not_open_title_and_hash_as_separate_authority_reads(self):
        source = inspect.getsource(probe.discover_skills)

        self.assertIn(
            "observe_skill_content",
            source,
            "RED: owner must compose one bounded content observation",
        )
        self.assertNotIn(
            "title = markdown_title(path)",
            source,
            "RED: separate title Path.open remains in authority flow",
        )
        self.assertNotIn(
            "sha256 = sha256_file(path)",
            source,
            "RED: separate hash Path.open remains in authority flow",
        )


if __name__ == "__main__":
    unittest.main()
