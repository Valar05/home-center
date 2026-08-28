#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_file_identity import (
    capture_skill_file_identity,
    revalidate_skill_file_identity,
)


class SkillFileIdentityTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "SKILL.md"
        self.path.write_text("# stable\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_same_ordinary_file_observation_is_stable(self):
        before = capture_skill_file_identity(self.path)
        after = capture_skill_file_identity(self.path)

        verdict = revalidate_skill_file_identity(before, after)

        self.assertEqual("STABLE", verdict.status)
        self.assertIn("observ", verdict.reason.lower())
        self.assertNotIn("atomic", verdict.reason.lower())

    def test_named_skill_symlink_is_redirector_blocked_without_following_target(self):
        target = self.path
        alias = self.root / "alias" / "SKILL.md"
        alias.parent.mkdir()
        try:
            os.symlink(target, alias)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"file symlink unavailable on this runner: {type(error).__name__}")

        before = capture_skill_file_identity(alias)
        verdict = revalidate_skill_file_identity(before, before)

        self.assertEqual("REDIRECTOR_BLOCKED", verdict.status)
        self.assertIn("repository-owned file topology", verdict.reason)

    def test_replacement_with_new_file_object_is_detected(self):
        before = capture_skill_file_identity(self.path)
        replacement = self.root / "replacement.tmp"
        replacement.write_text("# replacement\n", encoding="utf-8")
        os.replace(replacement, self.path)
        after = capture_skill_file_identity(self.path)

        verdict = revalidate_skill_file_identity(before, after)

        self.assertEqual("FILE_CHANGED", verdict.status)
        self.assertIn("device/inode", verdict.reason)

    def test_in_place_size_or_mtime_drift_is_detected(self):
        before = capture_skill_file_identity(self.path)
        self.path.write_text("# stable but materially longer now\n", encoding="utf-8")
        after = capture_skill_file_identity(self.path)

        verdict = revalidate_skill_file_identity(before, after)

        self.assertEqual("FILE_CHANGED", verdict.status)
        self.assertIn("size/mtime", verdict.reason)

    def test_unavailable_file_index_fails_closed(self):
        observed = capture_skill_file_identity(self.path)
        unavailable = replace(observed, inode=0)

        verdict = revalidate_skill_file_identity(unavailable, unavailable)

        self.assertEqual("IDENTITY_UNAVAILABLE", verdict.status)
        self.assertIn("cannot certify", verdict.reason)

    def test_equal_observations_are_not_claimed_as_atomic_binding(self):
        observed = capture_skill_file_identity(self.path)

        verdict = revalidate_skill_file_identity(observed, observed)

        self.assertEqual("STABLE", verdict.status)
        self.assertIn("bracketed", verdict.reason)
        self.assertNotIn("atomic", verdict.reason.lower())


if __name__ == "__main__":
    unittest.main()
