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
    def test_owner_must_use_one_bounded_content_observation(self):
        source = inspect.getsource(probe.discover_skills)

        self.assertEqual(
            1,
            source.count("observe_skill_content("),
            "RED: one and only one content observation should own title+SHA",
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

    def test_owner_reuses_existing_resource_authorities(self):
        source = inspect.getsource(probe.discover_skills)
        for token in (
            "max_bytes=MAX_SKILL_HASH_BYTES",
            "max_title_scan_bytes=MAX_SKILL_TITLE_SCAN_BYTES",
            "max_title_line_bytes=MAX_SKILL_TITLE_LINE_BYTES",
            "max_title_chars=MAX_SKILL_TITLE_CHARS",
        ):
            self.assertIn(token, source, f"RED: owner content custody must reuse {token}")

    def test_single_content_observation_does_not_remove_identity_revalidation(self):
        source = inspect.getsource(probe.discover_skills)
        content_index = source.index("observe_skill_content(")
        post_identity_index = source.index("file_after = capture_skill_file_identity(path)")
        self.assertLess(
            content_index,
            post_identity_index,
            "RED: post-content identity revalidation must remain after custody read",
        )
        self.assertIn(
            "file_verdict = revalidate_skill_file_identity(file_before, file_after)",
            source,
            "RED: one content read complements, not replaces, persistent identity revalidation",
        )


if __name__ == "__main__":
    unittest.main()
