#!/usr/bin/env python3

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe
from try_forever_skill_directory_traversal_guard import SkillDirectoryTraversalVerdict
from try_forever_skill_title_fallback_policy import SkillFallbackTitleSemanticError


class ProvenanceOwnerConvergence2000Test(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_skill(self, name: str, text: str) -> Path:
        path = self.root / "skills" / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def run_main_with_snapshot(
        self,
        *,
        heads: tuple[str, str],
        dirties: tuple[bool | None, bool | None],
        expected_head: str = "",
    ) -> tuple[int, dict]:
        record = probe.SkillRecord(
            path="skills/alpha/SKILL.md",
            sha256="a" * 64,
            title="Alpha",
        )
        index = probe.IndexVerdict(
            status="UNRESOLVED",
            reason="no generated index supplied",
            path="",
            source_head="",
            generated_at="",
            dirty_source=None,
            age_hours=None,
        )
        argv = ["try_forever_skill_provenance_probe.py", "--repo-root", str(self.root)]
        if expected_head:
            argv.extend(["--expected-head", expected_head])
        output = io.StringIO()
        with patch.object(probe, "git_head", side_effect=heads), patch.object(
            probe, "git_dirty", side_effect=dirties
        ), patch.object(
            probe, "discover_skills", return_value=([record], [])
        ), patch.object(
            probe, "inspect_generated_index", return_value=index
        ), patch.object(
            sys, "argv", argv
        ), contextlib.redirect_stdout(output):
            rc = probe.main()
        return rc, probe.json.loads(output.getvalue())

    def test_v3_stable_snapshot_emits_certified_authority_and_discovery_count(self):
        rc, result = self.run_main_with_snapshot(
            heads=("abc123", "abc123"),
            dirties=(False, False),
        )
        self.assertEqual(0, rc)
        self.assertEqual("try-forever-skill-provenance.v3", result["schema"])
        self.assertEqual(1, result["discoveredSkillCount"])
        self.assertEqual(1, result["skillCount"])
        self.assertTrue(result["skillAuthority"]["authoritative"])
        self.assertEqual("CERTIFIED_CURRENT", result["skillAuthority"]["status"])
        self.assertEqual("Alpha", result["skills"][0]["title"])

    def test_v3_unstable_snapshot_keeps_discovery_diagnostic_but_emits_zero_authority(self):
        rc, result = self.run_main_with_snapshot(
            heads=("abc123", "def456"),
            dirties=(False, False),
        )
        self.assertEqual(0, rc)
        self.assertEqual(1, result["discoveredSkillCount"])
        self.assertEqual(0, result["skillCount"])
        self.assertEqual([], result["skills"])
        self.assertFalse(result["skillAuthority"]["authoritative"])
        self.assertEqual("UNSTABLE_SNAPSHOT", result["skillAuthority"]["status"])

    def test_v3_expected_head_mismatch_zeroes_authority_even_on_clean_snapshot(self):
        rc, result = self.run_main_with_snapshot(
            heads=("abc123", "abc123"),
            dirties=(False, False),
            expected_head="deadbeef",
        )
        self.assertEqual(0, rc)
        self.assertEqual(1, result["discoveredSkillCount"])
        self.assertEqual(0, result["skillCount"])
        self.assertEqual([], result["skills"])
        self.assertEqual(
            "EXPECTED_HEAD_MISMATCH",
            result["skillAuthority"]["status"],
        )
        self.assertIn("expected head deadbeef", result["expectedHeadError"])

    def test_real_owner_markdown_title_rejects_edge_control_before_broad_strip(self):
        path = self.root / "skills" / "edge-control" / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# safe\u0085\n", encoding="utf-8")

        with self.assertRaises(SkillFallbackTitleSemanticError):
            probe.markdown_title(path)

    def test_real_owner_folder_fallback_uses_same_title_semantic_gate(self):
        path = self.root / "skills" / "bad\u202etitle" / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("ordinary text\n", encoding="utf-8")

        with self.assertRaises(SkillFallbackTitleSemanticError):
            probe.markdown_title(path)

    def test_queued_child_identity_change_fails_discovery_before_title_or_hash(self):
        self.write_skill("child", "# Child\n")
        stable = SkillDirectoryTraversalVerdict(
            status="STABLE",
            reason="root still stable",
        )
        changed = SkillDirectoryTraversalVerdict(
            status="DIRECTORY_CHANGED",
            reason="queued child changed before traversal",
        )

        with patch.object(
            probe,
            "revalidate_skill_directory_for_traversal",
            side_effect=(stable, changed),
        ), patch.object(probe, "markdown_title") as title_mock, patch.object(
            probe, "sha256_file"
        ) as hash_mock:
            records, errors = probe.discover_skills(self.root)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("traversal", errors[0].stage)
        self.assertEqual(
            "SkillDirectoryTraversalDirectoryChanged",
            errors[0].error_type,
        )
        title_mock.assert_not_called()
        hash_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
