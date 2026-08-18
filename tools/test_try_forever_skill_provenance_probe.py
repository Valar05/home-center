#!/usr/bin/env python3

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_provenance_probe import (
    discover_skills,
    inspect_generated_index,
    resolve_repo_path,
)


class SkillProvenanceProbeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 8, 18, 7, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def write_index(self, **values):
        path = self.root / "generated" / "skill-index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(values), encoding="utf-8")
        return path

    def test_direct_current_tree_skill_discovery_is_authority(self):
        skill = self.root / "skills" / "heartbeat-alpha" / "SKILL.md"
        skill.parent.mkdir(parents=True)
        skill.write_text("# Heartbeat Alpha\n\nConcrete skill.\n", encoding="utf-8")
        records, errors = discover_skills(self.root)
        self.assertEqual([], errors)
        self.assertEqual(1, len(records))
        self.assertEqual("skills/heartbeat-alpha/SKILL.md", records[0].path)
        self.assertEqual("Heartbeat Alpha", records[0].title)
        self.assertEqual(64, len(records[0].sha256))

    def test_repo_relative_generated_index_resolves_under_repo_root(self):
        expected = self.root / "generated" / "skill-index.json"
        self.assertEqual(
            expected.resolve(),
            resolve_repo_path(self.root, "generated/skill-index.json"),
        )

    def test_matching_clean_fresh_index_is_verified_current(self):
        path = self.write_index(
            sourceHead="abc123",
            generatedAt=(self.now - timedelta(hours=2)).isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head="abc123",
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("VERIFIED_CURRENT", verdict.status)

    def test_foreign_head_is_stale(self):
        path = self.write_index(
            sourceHead="old-head",
            generatedAt=self.now.isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head="current-head",
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("STALE", verdict.status)
        self.assertIn("source head", verdict.reason)

    def test_declared_dirty_index_is_stale(self):
        path = self.write_index(
            sourceHead="abc123",
            generatedAt=self.now.isoformat(),
            dirtySource=True,
        )
        verdict = inspect_generated_index(
            path,
            current_head="abc123",
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("STALE", verdict.status)
        self.assertIn("dirty source tree", verdict.reason)

    def test_dirty_current_checkout_is_unresolved_not_verified(self):
        path = self.write_index(
            sourceHead="abc123",
            generatedAt=self.now.isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head="abc123",
            current_tree_dirty=True,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("current checkout is dirty", verdict.reason)

    def test_unknown_current_checkout_cleanliness_is_unresolved(self):
        path = self.write_index(
            sourceHead="abc123",
            generatedAt=self.now.isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head="abc123",
            current_tree_dirty=None,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("cleanliness is unavailable", verdict.reason)

    def test_old_index_is_stale(self):
        path = self.write_index(
            sourceHead="abc123",
            generatedAt=(self.now - timedelta(hours=337)).isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head="abc123",
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("STALE", verdict.status)
        self.assertIn("exceeds", verdict.reason)

    def test_implausibly_future_index_is_unresolved(self):
        path = self.write_index(
            sourceHead="abc123",
            generatedAt=(self.now + timedelta(minutes=6)).isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head="abc123",
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("future", verdict.reason)

    def test_missing_clean_tree_declaration_is_unresolved(self):
        path = self.write_index(
            sourceHead="abc123",
            generatedAt=self.now.isoformat(),
        )
        verdict = inspect_generated_index(
            path,
            current_head="abc123",
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("clean source tree", verdict.reason)


if __name__ == "__main__":
    unittest.main()
