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
    SkillCandidateResourceLimitError,
    bounded_skill_candidates,
    discover_skills,
)


class SkillCandidateEnumerationTest(unittest.TestCase):
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

    def test_exact_limit_is_admitted_and_sorted_deterministically(self):
        self.write_skill("zeta")
        self.write_skill("alpha")
        self.write_skill("middle")

        candidates = bounded_skill_candidates(self.skills_root, max_candidates=3)

        self.assertEqual(
            [
                "skills/alpha/SKILL.md",
                "skills/middle/SKILL.md",
                "skills/zeta/SKILL.md",
            ],
            [path.relative_to(self.root).as_posix() for path in candidates],
        )

    def test_max_plus_one_fails_closed_in_candidate_throat(self):
        self.write_skill("alpha")
        self.write_skill("beta")
        self.write_skill("gamma")

        with self.assertRaises(SkillCandidateResourceLimitError):
            bounded_skill_candidates(self.skills_root, max_candidates=2)

    def test_discovery_overflow_returns_no_partial_authority_or_per_file_work(self):
        self.write_skill("alpha")
        self.write_skill("beta")
        self.write_skill("gamma")

        with (
            patch("try_forever_skill_provenance_probe.MAX_SKILL_CANDIDATES", 2),
            patch("try_forever_skill_provenance_probe.markdown_title") as title,
            patch("try_forever_skill_provenance_probe.sha256_file") as sha256,
        ):
            records, errors = discover_skills(self.root)

        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("skills", errors[0].path)
        self.assertEqual("enumeration", errors[0].stage)
        self.assertEqual("SkillCandidateResourceLimitError", errors[0].error_type)
        self.assertIn("partial repository-skill authority is forbidden", errors[0].reason)
        title.assert_not_called()
        sha256.assert_not_called()

    def test_zero_budget_rejects_first_candidate_without_per_file_authority(self):
        self.write_skill("alpha")

        with self.assertRaises(SkillCandidateResourceLimitError):
            bounded_skill_candidates(self.skills_root, max_candidates=0)

    def test_negative_budget_is_programmer_error(self):
        with self.assertRaisesRegex(ValueError, "candidate budget"):
            bounded_skill_candidates(self.skills_root, max_candidates=-1)


if __name__ == "__main__":
    unittest.main()
