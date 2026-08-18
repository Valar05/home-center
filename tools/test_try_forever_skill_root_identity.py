#!/usr/bin/env python3

import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_root_identity import (
    SkillRootIdentity,
    capture_skill_root_identity,
    redirector_kind_from_stat,
    revalidate_skill_root_identity,
)


class SkillRootIdentityPolicyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.skills = self.root / "skills"
        self.skills.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def test_same_directory_identity_is_stable(self):
        before = capture_skill_root_identity(self.skills)
        after = capture_skill_root_identity(self.skills)

        verdict = revalidate_skill_root_identity(before, after)

        if not before.has_stable_token:
            self.assertEqual("IDENTITY_UNAVAILABLE", verdict.status)
        else:
            self.assertEqual("STABLE", verdict.status)

    def test_persistent_root_replacement_is_detected(self):
        before = capture_skill_root_identity(self.skills)
        replacement = self.root / "replacement"
        replacement.mkdir()
        displaced = self.root / "skills-old"
        self.skills.rename(displaced)
        replacement.rename(self.skills)
        after = capture_skill_root_identity(self.skills)

        verdict = revalidate_skill_root_identity(before, after)

        if before.has_stable_token and after.has_stable_token:
            self.assertEqual("ROOT_CHANGED", verdict.status)
        else:
            self.assertEqual("IDENTITY_UNAVAILABLE", verdict.status)

    def test_symlink_root_is_classified_from_no_follow_stat(self):
        outside = self.root / "outside"
        outside.mkdir()
        link = self.root / "skills-link"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"directory symlink unavailable: {type(error).__name__}")

        observed = capture_skill_root_identity(link)
        verdict = revalidate_skill_root_identity(observed, observed)

        self.assertEqual("symlink", observed.redirector_kind)
        self.assertEqual("REDIRECTOR_BLOCKED", verdict.status)

    def test_windows_mount_point_reparse_tag_is_classified_as_junction(self):
        tag = getattr(stat, "IO_REPARSE_TAG_MOUNT_POINT", 0)
        if not tag:
            self.skipTest("Python platform does not expose IO_REPARSE_TAG_MOUNT_POINT")

        observed = SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_reparse_tag=tag,
        )

        self.assertEqual("junction", redirector_kind_from_stat(observed))

    def test_zero_identity_token_fails_closed(self):
        identity = SkillRootIdentity(
            device=0,
            inode=0,
            file_type=stat.S_IFDIR,
            file_attributes=0,
            reparse_tag=0,
            redirector_kind="",
        )

        verdict = revalidate_skill_root_identity(identity, identity)

        self.assertEqual("IDENTITY_UNAVAILABLE", verdict.status)

    def test_changed_to_redirector_wins_over_identity_comparison(self):
        before = SkillRootIdentity(
            device=1,
            inode=2,
            file_type=stat.S_IFDIR,
            file_attributes=0,
            reparse_tag=0,
            redirector_kind="",
        )
        after = SkillRootIdentity(
            device=1,
            inode=2,
            file_type=stat.S_IFDIR,
            file_attributes=0,
            reparse_tag=0,
            redirector_kind="junction",
        )

        verdict = revalidate_skill_root_identity(before, after)

        self.assertEqual("ROOT_CHANGED", verdict.status)
        self.assertIn("junction", verdict.reason)


if __name__ == "__main__":
    unittest.main()
