#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_provenance_probe import discover_skills


class SkillRootTopologyTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def symlink_or_skip(self, link: Path, target: Path) -> None:
        try:
            link.symlink_to(target, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"directory symlink unavailable: {type(error).__name__}")

    def test_symlinked_skills_root_is_rejected_before_traversal_or_per_file_work(self):
        outside = self.root / "outside-skills"
        skill = outside / "external" / "SKILL.md"
        skill.parent.mkdir(parents=True, exist_ok=True)
        skill.write_text("# external\n", encoding="utf-8")
        self.symlink_or_skip(self.root / "skills", outside)

        with (
            patch("try_forever_skill_provenance_probe.bounded_skill_candidates") as candidates,
            patch("try_forever_skill_provenance_probe.markdown_title") as title,
            patch("try_forever_skill_provenance_probe.sha256_file") as sha256,
        ):
            records, errors = discover_skills(self.root)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("skills", errors[0].path)
        self.assertEqual("repository", errors[0].stage)
        self.assertEqual("SymlinkedSkillsRoot", errors[0].error_type)
        self.assertIn("outside repository-owned topology is forbidden", errors[0].reason)
        candidates.assert_not_called()
        title.assert_not_called()
        sha256.assert_not_called()

    def test_broken_symlinked_skills_root_is_not_laundered_into_missing_directory(self):
        missing_target = self.root / "missing-target"
        self.symlink_or_skip(self.root / "skills", missing_target)

        records, errors = discover_skills(self.root)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("SymlinkedSkillsRoot", errors[0].error_type)
        self.assertNotEqual("MissingSkillsDirectory", errors[0].error_type)

    def test_real_skills_directory_can_continue_to_bounded_candidate_gate(self):
        skills_root = self.root / "skills"
        skills_root.mkdir(parents=True, exist_ok=True)

        with patch(
            "try_forever_skill_provenance_probe.bounded_skill_candidates",
            return_value=[],
        ) as candidates:
            records, errors = discover_skills(self.root)

        self.assertEqual([], records)
        self.assertEqual([], errors)
        candidates.assert_called_once_with(skills_root)


if __name__ == "__main__":
    unittest.main()
