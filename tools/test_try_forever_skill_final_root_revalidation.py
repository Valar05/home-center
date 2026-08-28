#!/usr/bin/env python3

import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe
from try_forever_skill_root_identity import SkillRootIdentity


def root_identity(inode: int) -> SkillRootIdentity:
    return SkillRootIdentity(
        device=1,
        inode=inode,
        file_type=stat.S_IFDIR,
        file_attributes=0,
        reparse_tag=0,
        redirector_kind="",
    )


class FinalRootRevalidationIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.skills = self.repo / "skills"
        skill = self.skills / "alpha" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# Alpha Skill\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_final_root_revalidation_occurs_after_per_file_authority_work(self):
        stable = root_identity(100)
        with mock.patch.object(
            probe,
            "capture_skill_root_identity",
            side_effect=[stable, stable, stable],
        ) as capture:
            records, errors = probe.discover_skills(self.repo)

        self.assertEqual([], errors)
        self.assertEqual(1, len(records))
        self.assertEqual(3, capture.call_count)

    def test_late_persistent_root_replacement_rejects_all_gathered_records(self):
        stable = root_identity(100)
        changed = root_identity(101)
        with mock.patch.object(
            probe,
            "capture_skill_root_identity",
            side_effect=[stable, stable, changed],
        ) as capture:
            records, errors = probe.discover_skills(self.repo)

        self.assertEqual(3, capture.call_count)
        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("repository", errors[0].stage)
        self.assertEqual("SkillsRootIdentityChanged", errors[0].error_type)
        self.assertIn("final", errors[0].reason.lower())

    def test_final_root_identity_failure_rejects_partial_authority(self):
        stable = root_identity(100)
        with mock.patch.object(
            probe,
            "capture_skill_root_identity",
            side_effect=[stable, stable, OSError("late root identity unavailable")],
        ) as capture:
            records, errors = probe.discover_skills(self.repo)

        self.assertEqual(3, capture.call_count)
        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("repository", errors[0].stage)
        self.assertEqual("OSError", errors[0].error_type)
        self.assertIn("after per-file authority work", errors[0].reason)


if __name__ == "__main__":
    unittest.main()
