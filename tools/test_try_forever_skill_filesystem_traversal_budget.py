#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_provenance_probe import (
    SkillTraversalResourceLimitError,
    bounded_skill_candidates,
    discover_skills,
)


class SkillFilesystemTraversalBudgetTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.skills_root = self.root / "skills"
        self.skills_root.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        self.temp.cleanup()

    def write_skill(self, name: str) -> Path:
        path = self.skills_root / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# {name}\n", encoding="utf-8")
        return path

    def test_exact_entry_limit_admits_complete_traversal_and_sorted_candidates(self):
        self.write_skill("zeta")
        self.write_skill("alpha")

        candidates = bounded_skill_candidates(
            self.skills_root,
            max_candidates=2,
            max_entries=4,
        )

        self.assertEqual(
            ["skills/alpha/SKILL.md", "skills/zeta/SKILL.md"],
            [path.relative_to(self.root).as_posix() for path in candidates],
        )

    def test_max_plus_one_non_candidate_entry_fails_closed(self):
        for name in ("a.txt", "b.txt", "c.txt"):
            (self.skills_root / name).write_text("noise", encoding="utf-8")

        with self.assertRaises(SkillTraversalResourceLimitError):
            bounded_skill_candidates(
                self.skills_root,
                max_candidates=10,
                max_entries=2,
            )

    def test_discovery_traversal_overflow_returns_no_partial_authority_or_per_file_work(self):
        self.write_skill("alpha")
        (self.skills_root / "noise-a.txt").write_text("noise", encoding="utf-8")
        (self.skills_root / "noise-b.txt").write_text("noise", encoding="utf-8")

        with (
            patch("try_forever_skill_provenance_probe.MAX_SKILL_TRAVERSAL_ENTRIES", 2),
            patch("try_forever_skill_provenance_probe.markdown_title") as title,
            patch("try_forever_skill_provenance_probe.sha256_file") as sha256,
        ):
            records, errors = discover_skills(self.root)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("skills", errors[0].path)
        self.assertEqual("traversal", errors[0].stage)
        self.assertEqual("SkillTraversalResourceLimitError", errors[0].error_type)
        self.assertIn("partial repository-skill authority is forbidden", errors[0].reason)
        title.assert_not_called()
        sha256.assert_not_called()

    def test_traversal_io_failure_is_structured_and_returns_no_partial_authority(self):
        with patch(
            "try_forever_skill_provenance_probe.os.scandir",
            side_effect=PermissionError("hostile raw detail must not leak"),
        ):
            records, errors = discover_skills(self.root)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("traversal", errors[0].stage)
        self.assertEqual("PermissionError", errors[0].error_type)
        self.assertEqual(
            "skill filesystem traversal could not be completed; partial repository-skill authority is forbidden",
            errors[0].reason,
        )
        self.assertNotIn("hostile raw detail", errors[0].reason)

    def test_directory_symlink_is_not_recursed(self):
        outside = self.root / "outside"
        outside.mkdir(parents=True, exist_ok=True)
        (outside / "SKILL.md").write_text("# outside\n", encoding="utf-8")
        link = self.skills_root / "linked-dir"
        try:
            link.symlink_to(outside, target_is_directory=True)
        except (OSError, NotImplementedError) as error:
            self.skipTest(f"directory symlink unavailable: {type(error).__name__}")

        candidates = bounded_skill_candidates(
            self.skills_root,
            max_candidates=10,
            max_entries=1,
        )

        self.assertEqual([], candidates)

    def test_zero_entry_budget_rejects_first_filesystem_entry(self):
        (self.skills_root / "noise.txt").write_text("noise", encoding="utf-8")

        with self.assertRaises(SkillTraversalResourceLimitError):
            bounded_skill_candidates(
                self.skills_root,
                max_candidates=10,
                max_entries=0,
            )

    def test_negative_entry_budget_is_programmer_error(self):
        with self.assertRaisesRegex(ValueError, "traversal entry budget"):
            bounded_skill_candidates(
                self.skills_root,
                max_candidates=10,
                max_entries=-1,
            )


if __name__ == "__main__":
    unittest.main()
