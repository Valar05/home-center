#!/usr/bin/env python3

import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_provenance_probe import discover_skills
from try_forever_skill_root_identity import SkillRootIdentity


def ordinary_root(inode: int) -> SkillRootIdentity:
    return SkillRootIdentity(
        device=7,
        inode=inode,
        file_type=stat.S_IFDIR,
        file_attributes=0,
        reparse_tag=0,
        redirector_kind="",
    )


class SkillRootIdentityOwnerIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        skill = self.root / "skills" / "healthy" / "SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text("# Healthy\n", encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def test_persistent_root_change_rejects_all_authority_before_title_or_hash(self):
        with patch(
            "try_forever_skill_provenance_probe.capture_skill_root_identity",
            side_effect=[ordinary_root(10), ordinary_root(11)],
        ), patch(
            "try_forever_skill_provenance_probe.markdown_title"
        ) as title_mock, patch(
            "try_forever_skill_provenance_probe.sha256_file"
        ) as hash_mock:
            records, errors = discover_skills(self.root)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("repository", errors[0].stage)
        self.assertEqual("SkillsRootIdentityChanged", errors[0].error_type)
        title_mock.assert_not_called()
        hash_mock.assert_not_called()

    def test_unavailable_root_identity_rejects_all_authority_before_title_or_hash(self):
        with patch(
            "try_forever_skill_provenance_probe.capture_skill_root_identity",
            side_effect=[ordinary_root(10), ordinary_root(0)],
        ), patch(
            "try_forever_skill_provenance_probe.markdown_title"
        ) as title_mock, patch(
            "try_forever_skill_provenance_probe.sha256_file"
        ) as hash_mock:
            records, errors = discover_skills(self.root)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("SkillsRootIdentityUnavailable", errors[0].error_type)
        title_mock.assert_not_called()
        hash_mock.assert_not_called()

    def test_root_redirector_blocks_before_candidate_traversal(self):
        redirector = SkillRootIdentity(
            device=7,
            inode=10,
            file_type=stat.S_IFDIR,
            file_attributes=0,
            reparse_tag=0,
            redirector_kind="junction",
        )
        with patch(
            "try_forever_skill_provenance_probe.capture_skill_root_identity",
            return_value=redirector,
        ), patch(
            "try_forever_skill_provenance_probe.bounded_skill_candidates"
        ) as candidates_mock:
            records, errors = discover_skills(self.root)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("JunctionSkillsRoot", errors[0].error_type)
        candidates_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
