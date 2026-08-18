#!/usr/bin/env python3

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe


class SkillFileIdentityIntegrationTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.skills = self.repo / "skills"
        self.skills.mkdir()

    def tearDown(self):
        self.temp.cleanup()

    def write_skill(self, name: str, text: str = "# Stable Skill\n") -> Path:
        path = self.skills / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_stable_ordinary_candidate_reaches_record_authority(self):
        path = self.write_skill("alpha")

        records, errors = probe.discover_skills(self.repo)

        self.assertEqual([], errors)
        self.assertEqual(1, len(records))
        self.assertEqual(path.relative_to(self.repo).as_posix(), records[0].path)
        self.assertEqual("Stable Skill", records[0].title)
        self.assertEqual(probe.sha256_file(path), records[0].sha256)

    def test_named_skill_directory_fails_global_topology_gate_before_title_or_hash(self):
        candidate = self.skills / "alpha" / "SKILL.md"
        candidate.mkdir(parents=True)

        with mock.patch.object(probe, "markdown_title") as title, mock.patch.object(
            probe, "sha256_file"
        ) as digest:
            records, errors = probe.discover_skills(self.repo)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("SkillCandidateTopologyError", errors[0].error_type)
        self.assertEqual("identity", errors[0].stage)
        title.assert_not_called()
        digest.assert_not_called()

    def test_named_skill_symlink_fails_global_topology_gate_without_following_target(self):
        target = self.write_skill("target")
        alias = self.skills / "alias" / "SKILL.md"
        alias.parent.mkdir(parents=True)
        try:
            os.symlink(target, alias)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"file symlink unavailable on this runner: {type(error).__name__}")

        with mock.patch.object(probe, "markdown_title") as title, mock.patch.object(
            probe, "sha256_file"
        ) as digest:
            records, errors = probe.discover_skills(self.repo)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("SkillCandidateTopologyError", errors[0].error_type)
        self.assertEqual(alias.relative_to(self.repo).as_posix(), errors[0].path)
        title.assert_not_called()
        digest.assert_not_called()

    def test_replacement_after_hash_is_rejected_before_record_append(self):
        path = self.write_skill("alpha")
        real_hash = probe.sha256_file

        def hash_then_replace(candidate: Path, *, max_bytes=None):
            digest = real_hash(candidate, max_bytes=max_bytes)
            replacement = candidate.with_name("replacement.tmp")
            replacement.write_text("# Replacement Skill\n", encoding="utf-8")
            os.replace(replacement, candidate)
            return digest

        with mock.patch.object(probe, "sha256_file", side_effect=hash_then_replace):
            records, errors = probe.discover_skills(self.repo)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("SkillFileChanged", errors[0].error_type)
        self.assertEqual("identity", errors[0].stage)
        self.assertNotIn("atomic", errors[0].reason.lower())

    def test_identity_capture_failure_never_falls_through_to_title_or_hash(self):
        self.write_skill("alpha")

        with mock.patch.object(
            probe,
            "capture_skill_file_identity",
            side_effect=OSError("identity unavailable"),
        ), mock.patch.object(probe, "markdown_title") as title, mock.patch.object(
            probe, "sha256_file"
        ) as digest:
            records, errors = probe.discover_skills(self.repo)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("identity", errors[0].stage)
        self.assertEqual("OSError", errors[0].error_type)
        title.assert_not_called()
        digest.assert_not_called()


if __name__ == "__main__":
    unittest.main()
