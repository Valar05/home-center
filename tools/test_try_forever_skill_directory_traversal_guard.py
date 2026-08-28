#!/usr/bin/env python3

import unittest

from try_forever_skill_directory_traversal_guard import (
    SkillDirectoryIdentity,
    revalidate_skill_directory_for_traversal,
)


def directory(*, device=1, inode=10, redirector="", file_type=0o040000):
    return SkillDirectoryIdentity(
        device=device,
        inode=inode,
        file_type=file_type,
        redirector_kind=redirector,
    )


class SkillDirectoryTraversalGuardTest(unittest.TestCase):
    def test_same_ordinary_directory_is_stable(self):
        verdict = revalidate_skill_directory_for_traversal(directory(), directory())
        self.assertEqual("STABLE", verdict.status)

    def test_redirector_at_discovery_is_blocked(self):
        verdict = revalidate_skill_directory_for_traversal(
            directory(redirector="symlink"), directory()
        )
        self.assertEqual("REDIRECTOR_BLOCKED", verdict.status)

    def test_directory_replaced_by_redirector_before_scan_is_rejected(self):
        verdict = revalidate_skill_directory_for_traversal(
            directory(), directory(redirector="symlink")
        )
        self.assertEqual("DIRECTORY_CHANGED", verdict.status)

    def test_device_inode_replacement_is_rejected(self):
        verdict = revalidate_skill_directory_for_traversal(
            directory(device=2, inode=20), directory(device=2, inode=21)
        )
        self.assertEqual("DIRECTORY_CHANGED", verdict.status)

    def test_missing_stable_identity_fails_closed(self):
        verdict = revalidate_skill_directory_for_traversal(
            directory(inode=0), directory(inode=0)
        )
        self.assertEqual("IDENTITY_UNAVAILABLE", verdict.status)

    def test_non_directory_shape_is_rejected(self):
        verdict = revalidate_skill_directory_for_traversal(
            directory(), directory(file_type=0o100000)
        )
        self.assertEqual("DIRECTORY_CHANGED", verdict.status)

    def test_stable_observation_does_not_claim_atomicity(self):
        verdict = revalidate_skill_directory_for_traversal(directory(), directory())
        self.assertEqual("STABLE", verdict.status)
        self.assertNotIn("atomic", verdict.reason.lower())


if __name__ == "__main__":
    unittest.main()
