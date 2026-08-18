#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_provenance_probe import (
    MAX_SKILL_TITLE_CHARS,
    MAX_SKILL_TITLE_LINE_BYTES,
    MAX_SKILL_TITLE_SCAN_BYTES,
    SkillTitleResourceLimitError,
    discover_skills,
    markdown_title,
)


class SkillTitleResourceBudgetTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def skill_path(self, name: str) -> Path:
        path = self.root / "skills" / name / "SKILL.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def test_exact_title_character_budget_is_admitted(self):
        path = self.skill_path("exact-title")
        title = "T" * MAX_SKILL_TITLE_CHARS
        path.write_text(f"# {title}\n", encoding="utf-8")

        self.assertEqual(title, markdown_title(path))
        records, errors = discover_skills(self.root)
        self.assertEqual([], errors)
        self.assertEqual(title, records[0].title)

    def test_title_character_budget_plus_one_is_rejected_not_truncated(self):
        path = self.skill_path("oversized-title")
        title = "T" * (MAX_SKILL_TITLE_CHARS + 1)
        path.write_text(f"# {title}\n", encoding="utf-8")

        with self.assertRaises(SkillTitleResourceLimitError):
            markdown_title(path)

        records, errors = discover_skills(self.root)
        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("SkillTitleResourceLimitError", errors[0].error_type)
        self.assertEqual("skill title extraction exceeded the declared resource budget", errors[0].reason)
        self.assertEqual(64, len(errors[0].sha256))

    def test_oversized_first_line_is_rejected_before_later_plausible_h1(self):
        path = self.skill_path("oversized-line")
        path.write_bytes((b"x" * (MAX_SKILL_TITLE_LINE_BYTES + 1)) + b"\n# Counterfeit Later Title\n")

        records, errors = discover_skills(self.root)
        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("SkillTitleResourceLimitError", errors[0].error_type)

    def test_scan_budget_exhaustion_rejects_late_title_instead_of_truncating_into_authority(self):
        path = self.skill_path("late-title")
        line = b"x" * (MAX_SKILL_TITLE_LINE_BYTES - 1) + b"\n"
        repeats = MAX_SKILL_TITLE_SCAN_BYTES // len(line)
        path.write_bytes((line * repeats) + b"# Too Late\n")

        records, errors = discover_skills(self.root)
        self.assertEqual([], records)
        self.assertEqual(1, len(errors))
        self.assertEqual("SkillTitleResourceLimitError", errors[0].error_type)

    def test_malformed_utf8_within_budget_keeps_utf8_error_classification(self):
        bad = self.skill_path("broken-utf8")
        bad.write_bytes(b"# broken \xff\n")
        healthy = self.skill_path("healthy")
        healthy.write_text("# Healthy\n", encoding="utf-8")

        records, errors = discover_skills(self.root)
        self.assertEqual(["skills/healthy/SKILL.md"], [record.path for record in records])
        self.assertEqual(1, len(errors))
        self.assertEqual("UnicodeDecodeError", errors[0].error_type)
        self.assertEqual("skill file is not valid UTF-8 text", errors[0].reason)

    def test_titleless_file_within_scan_budget_keeps_folder_fallback(self):
        path = self.skill_path("fallback-name")
        path.write_text("No H1 here.\nStill bounded.\n", encoding="utf-8")
        self.assertEqual("fallback-name", markdown_title(path))


if __name__ == "__main__":
    unittest.main()
