#!/usr/bin/env python3

import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_provenance_probe import (
    DiscoveryError,
    MAX_DISCOVERY_ERROR_PATH_CHARS,
    SkillHashResourceLimitError,
    SkillTitleResourceLimitError,
    assess_repository_snapshot,
    bounded_error_path,
    discover_skills,
    emitted_capability_boundary,
    inspect_generated_index,
    resolve_repo_path,
    sha256_file,
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

    def write_skill(self, name: str, text: str) -> Path:
        path = self.root / "skills" / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_direct_current_tree_skill_discovery_is_authority(self):
        skill = self.write_skill("heartbeat-alpha", "# Heartbeat Alpha\n\nConcrete skill.\n")
        records, errors = discover_skills(self.root)
        self.assertEqual([], errors)
        self.assertEqual(1, len(records))
        self.assertEqual("skills/heartbeat-alpha/SKILL.md", records[0].path)
        self.assertEqual("Heartbeat Alpha", records[0].title)
        self.assertEqual(64, len(records[0].sha256))
        self.assertTrue(skill.is_file())

    def test_malformed_utf8_skill_is_rejected_before_whole_file_hash(self):
        bad = self.root / "skills" / "broken-utf8" / "SKILL.md"
        bad.parent.mkdir(parents=True, exist_ok=True)
        bad.write_bytes(b"# broken \xff\n")
        self.write_skill("healthy", "# Healthy\n\nStill discoverable.\n")

        records, errors = discover_skills(self.root)

        self.assertEqual(["skills/healthy/SKILL.md"], [record.path for record in records])
        self.assertEqual(1, len(errors))
        error = errors[0]
        self.assertIsInstance(error, DiscoveryError)
        self.assertEqual("skills/broken-utf8/SKILL.md", error.path)
        self.assertEqual("title", error.stage)
        self.assertEqual("UnicodeDecodeError", error.error_type)
        self.assertEqual("skill file is not valid UTF-8 text", error.reason)
        self.assertEqual("", error.sha256)

    def test_unreadable_skill_hash_isolated_without_raw_exception_prose(self):
        self.write_skill("broken-io", "# Broken I/O\n")
        self.write_skill("healthy", "# Healthy\n")

        def fake_sha(path: Path, *, max_bytes=None) -> str:
            if path.parent.name == "broken-io":
                raise OSError("HOST SECRET: do not surface this raw exception")
            return "a" * 64

        with patch("try_forever_skill_provenance_probe.sha256_file", side_effect=fake_sha):
            records, errors = discover_skills(self.root)

        self.assertEqual(["skills/healthy/SKILL.md"], [record.path for record in records])
        self.assertEqual(1, len(errors))
        error = errors[0]
        self.assertEqual("hash", error.stage)
        self.assertEqual("OSError", error.error_type)
        self.assertEqual("skill file bytes could not be read", error.reason)
        self.assertNotIn("HOST SECRET", error.reason)
        self.assertEqual("", error.sha256)

    def test_exact_hash_budget_returns_full_file_sha(self):
        path = self.root / "exact.bin"
        payload = b"0123456789abcdef"
        path.write_bytes(payload)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            sha256_file(path, max_bytes=len(payload)),
        )

    def test_hash_budget_max_plus_one_rejects_without_prefix_authority(self):
        path = self.root / "oversized.bin"
        path.write_bytes(b"x" * 17)
        with self.assertRaises(SkillHashResourceLimitError):
            sha256_file(path, max_bytes=16)

    def test_title_rejection_happens_before_whole_file_hash(self):
        self.write_skill("bad-title", "# Bad title\n")
        with patch(
            "try_forever_skill_provenance_probe.markdown_title",
            side_effect=SkillTitleResourceLimitError("bounded title wound"),
        ), patch("try_forever_skill_provenance_probe.sha256_file") as hash_mock:
            records, errors = discover_skills(self.root)
        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("title", errors[0].stage)
        hash_mock.assert_not_called()

    def test_oversized_skill_body_isolated_and_healthy_peer_survives(self):
        self.write_skill("healthy", "# Healthy\nsmall\n")
        huge = self.root / "skills" / "huge-body" / "SKILL.md"
        huge.parent.mkdir(parents=True, exist_ok=True)
        huge.write_bytes(b"# Huge Body\n" + (b"x" * 128))

        with patch("try_forever_skill_provenance_probe.MAX_SKILL_HASH_BYTES", 64):
            records, errors = discover_skills(self.root)

        self.assertEqual(["skills/healthy/SKILL.md"], [record.path for record in records])
        self.assertEqual(1, len(errors))
        error = errors[0]
        self.assertEqual("skills/huge-body/SKILL.md", error.path)
        self.assertEqual("hash", error.stage)
        self.assertEqual("SkillHashResourceLimitError", error.error_type)
        self.assertEqual(
            "skill file exceeds the declared whole-file hash resource budget",
            error.reason,
        )
        self.assertEqual("", error.sha256)

    def test_discovery_error_path_projection_is_hard_bounded(self):
        projected = bounded_error_path("skills/" + ("x" * 2000) + "/SKILL.md")
        self.assertEqual(MAX_DISCOVERY_ERROR_PATH_CHARS, len(projected))
        self.assertRegex(projected, r"\.\.\.#[0-9a-f]{16}$")

    def test_stable_clean_snapshot_brackets_direct_discovery(self):
        verdict = assess_repository_snapshot(
            head_before="abc123", head_after="abc123", dirty_before=False, dirty_after=False
        )
        self.assertEqual("STABLE_CLEAN", verdict.status)
        self.assertIn("same clean git HEAD", verdict.reason)

    def test_head_move_during_discovery_is_unstable(self):
        verdict = assess_repository_snapshot(
            head_before="abc123", head_after="def456", dirty_before=False, dirty_after=False
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertIn("HEAD changed", verdict.reason)

    def test_dirty_checkout_after_discovery_is_unstable(self):
        verdict = assess_repository_snapshot(
            head_before="abc123", head_after="abc123", dirty_before=False, dirty_after=True
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertIn("dirty", verdict.reason)

    def test_unknown_post_discovery_cleanliness_is_unstable(self):
        verdict = assess_repository_snapshot(
            head_before="abc123", head_after="abc123", dirty_before=False, dirty_after=None
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

    def test_repo_relative_generated_index_resolves_under_repo_root(self):
        expected = self.root / "generated" / "skill-index.json"
        self.assertEqual(
            expected.resolve(), resolve_repo_path(self.root, "generated/skill-index.json")
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
            sourceHead="old-head", generatedAt=self.now.isoformat(), dirtySource=False
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
            sourceHead="abc123", generatedAt=self.now.isoformat(), dirtySource=True
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
            sourceHead="abc123", generatedAt=self.now.isoformat(), dirtySource=False
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
            sourceHead="abc123", generatedAt=self.now.isoformat(), dirtySource=False
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
        path = self.write_index(sourceHead="abc123", generatedAt=self.now.isoformat())
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
