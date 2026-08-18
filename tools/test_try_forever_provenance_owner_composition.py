#!/usr/bin/env python3

import json
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe
from try_forever_skill_root_identity import SkillRootIdentity


def root_identity(inode: int = 100) -> SkillRootIdentity:
    return SkillRootIdentity(
        device=1,
        inode=inode,
        file_type=stat.S_IFDIR,
        file_attributes=0,
        reparse_tag=0,
        redirector_kind="",
    )


class ProvenanceOwnerCompositionTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        (self.repo / "skills").mkdir()
        self.now = datetime(2026, 8, 18, 22, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def inspect(self, payload: dict):
        path = self.repo / "generated-index.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return probe.inspect_generated_index(
            path,
            current_head="abc123",
            current_tree_dirty=False,
            max_age_hours=24.0,
            now=self.now,
        )

    def test_casefold_collision_rejects_entire_set_before_title_or_hash_work(self):
        stable = root_identity()
        lower = self.repo / "skills" / "alpha" / "SKILL.md"
        upper = self.repo / "skills" / "ALPHA" / "SKILL.md"

        with mock.patch.object(
            probe, "bounded_skill_candidates", return_value=[lower, upper]
        ), mock.patch.object(
            probe, "capture_skill_root_identity", side_effect=[stable, stable]
        ), mock.patch.object(probe, "markdown_title") as title_mock, mock.patch.object(
            probe, "sha256_file"
        ) as hash_mock:
            records, errors = probe.discover_skills(self.repo)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("CaseInsensitiveIdentityCollision", errors[0].error_type)
        self.assertIn("first-wins", errors[0].reason)
        title_mock.assert_not_called()
        hash_mock.assert_not_called()

    def test_conflicting_source_head_aliases_are_unresolved_not_first_wins(self):
        verdict = self.inspect(
            {
                "sourceHead": "abc123",
                "source_head": "different",
                "generatedAt": self.now.isoformat(),
                "dirtySource": False,
            }
        )

        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("GeneratedIndexAliasConflictError", verdict.reason)
        self.assertEqual("", verdict.source_head)

    def test_bool_cannot_masquerade_as_timestamp_alias(self):
        verdict = self.inspect(
            {
                "sourceHead": "abc123",
                "generatedAt": True,
                "dirtySource": False,
            }
        )

        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("GeneratedIndexAliasTypeError", verdict.reason)

    def test_identical_typed_aliases_keep_verified_current_semantics(self):
        timestamp = self.now.isoformat()
        verdict = self.inspect(
            {
                "sourceHead": "abc123",
                "source_head": "abc123",
                "generatedAt": timestamp,
                "generated_at": timestamp,
                "dirtySource": False,
                "dirty_source": False,
            }
        )

        self.assertEqual("VERIFIED_CURRENT", verdict.status)
        self.assertEqual("abc123", verdict.source_head)
        self.assertFalse(verdict.dirty_source)


if __name__ == "__main__":
    unittest.main()
