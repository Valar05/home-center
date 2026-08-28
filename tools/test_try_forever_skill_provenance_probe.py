#!/usr/bin/env python3

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_provenance_probe import (
    MAX_DISCOVERY_ERROR_PATH_CHARS,
    assess_repository_snapshot,
    bounded_error_path,
    emitted_capability_boundary,
    inspect_generated_index,
    resolve_repo_path,
)

HEAD_A = "a" * 40
HEAD_B = "b" * 40


class SkillProvenanceProbeTest(unittest.TestCase):
    """Pure top-level probe contracts that do not duplicate custody-owner fixtures.

    Repository-skill discovery/content authority is covered by the dedicated
    tracked-candidate, single-artifact custody, file/root identity, HEAD binding,
    and owner-boundary suites. This file deliberately does not resurrect the
    retired markdown_title/sha256_file test path or assume a non-Git temp root can
    earn repository-skill authority.
    """

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 8, 20, 11, 0, tzinfo=timezone.utc)

    def tearDown(self):
        self.temp.cleanup()

    def write_index(self, **values) -> Path:
        path = self.root / "generated" / "skill-index.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(values), encoding="utf-8")
        return path

    def test_discovery_error_path_collapse_is_bounded_and_identity_derived(self):
        source = "skills/" + ("x" * 2000) + "/SKILL.md"
        projected = bounded_error_path(source)

        self.assertLessEqual(len(projected), MAX_DISCOVERY_ERROR_PATH_CHARS)
        self.assertRegex(projected, r"^<repo-path>\.\.\.#[0-9a-f]{16}$")
        self.assertNotIn("x" * 32, projected)

    def test_in_budget_discovery_error_path_remains_exact(self):
        source = "skills/alpha/SKILL.md"
        self.assertEqual(source, bounded_error_path(source))

    def test_stable_clean_snapshot_brackets_direct_discovery(self):
        verdict = assess_repository_snapshot(
            head_before=HEAD_A,
            head_after=HEAD_A,
            dirty_before=False,
            dirty_after=False,
        )
        self.assertEqual("STABLE_CLEAN", verdict.status)
        self.assertIn("same clean git HEAD", verdict.reason)

    def test_head_move_during_discovery_is_unstable(self):
        verdict = assess_repository_snapshot(
            head_before=HEAD_A,
            head_after=HEAD_B,
            dirty_before=False,
            dirty_after=False,
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertIn("HEAD changed", verdict.reason)

    def test_dirty_checkout_after_discovery_is_unstable(self):
        verdict = assess_repository_snapshot(
            head_before=HEAD_A,
            head_after=HEAD_A,
            dirty_before=False,
            dirty_after=True,
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertIn("dirty", verdict.reason)

    def test_unknown_post_discovery_cleanliness_is_unstable(self):
        verdict = assess_repository_snapshot(
            head_before=HEAD_A,
            head_after=HEAD_A,
            dirty_before=False,
            dirty_after=None,
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertIn("cleanliness was unavailable", verdict.reason)

    def test_emitted_report_declares_current_probe_process_executed(self):
        boundary = emitted_capability_boundary()
        self.assertTrue(boundary["sourceProbe"])
        self.assertTrue(boundary["probeExecutedByThisArtifact"])
        self.assertTrue(boundary["probeExecutedByThisProcess"])
        self.assertFalse(boundary["tested"])
        self.assertFalse(boundary["runtimeUi"])
        self.assertFalse(boundary["phoneDelivery"])

    def test_repo_relative_generated_index_uses_lexical_absolute_path(self):
        expected = Path(os.path.abspath(self.root / "generated" / "skill-index.json"))
        self.assertEqual(
            expected,
            resolve_repo_path(self.root, "generated/skill-index.json"),
        )

    def test_no_generated_index_is_unresolved_without_counterfeit_currentness(self):
        verdict = inspect_generated_index(
            None,
            current_head=HEAD_A,
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertEqual("", verdict.inspection_sha256)

    def test_matching_clean_fresh_index_is_verified_current(self):
        path = self.write_index(
            sourceHead=HEAD_A,
            generatedAt=(self.now - timedelta(hours=2)).isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head=HEAD_A,
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("VERIFIED_CURRENT", verdict.status)
        self.assertEqual(64, len(verdict.inspection_sha256))

    def test_foreign_canonical_head_is_stale(self):
        path = self.write_index(
            sourceHead=HEAD_B,
            generatedAt=self.now.isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head=HEAD_A,
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("STALE", verdict.status)
        self.assertIn("source head", verdict.reason)

    def test_malformed_declared_source_head_is_unresolved(self):
        path = self.write_index(
            sourceHead="abc123",
            generatedAt=self.now.isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head=HEAD_A,
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("source head contract rejected", verdict.reason)

    def test_declared_dirty_index_is_stale(self):
        path = self.write_index(
            sourceHead=HEAD_A,
            generatedAt=self.now.isoformat(),
            dirtySource=True,
        )
        verdict = inspect_generated_index(
            path,
            current_head=HEAD_A,
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("STALE", verdict.status)
        self.assertIn("dirty source tree", verdict.reason)

    def test_dirty_current_checkout_is_unresolved_not_verified(self):
        path = self.write_index(
            sourceHead=HEAD_A,
            generatedAt=self.now.isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head=HEAD_A,
            current_tree_dirty=True,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("current checkout is dirty", verdict.reason)

    def test_unknown_current_checkout_cleanliness_is_unresolved(self):
        path = self.write_index(
            sourceHead=HEAD_A,
            generatedAt=self.now.isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head=HEAD_A,
            current_tree_dirty=None,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("cleanliness is unavailable", verdict.reason)

    def test_old_index_is_stale(self):
        path = self.write_index(
            sourceHead=HEAD_A,
            generatedAt=(self.now - timedelta(hours=337)).isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head=HEAD_A,
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("STALE", verdict.status)
        self.assertIn("exceeds", verdict.reason)

    def test_implausibly_future_index_is_unresolved(self):
        path = self.write_index(
            sourceHead=HEAD_A,
            generatedAt=(self.now + timedelta(minutes=6)).isoformat(),
            dirtySource=False,
        )
        verdict = inspect_generated_index(
            path,
            current_head=HEAD_A,
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("future", verdict.reason)

    def test_missing_clean_tree_declaration_is_unresolved(self):
        path = self.write_index(
            sourceHead=HEAD_A,
            generatedAt=self.now.isoformat(),
        )
        verdict = inspect_generated_index(
            path,
            current_head=HEAD_A,
            current_tree_dirty=False,
            max_age_hours=336,
            now=self.now,
        )
        self.assertEqual("UNRESOLVED", verdict.status)
        self.assertIn("clean source tree", verdict.reason)


if __name__ == "__main__":
    unittest.main()
