#!/usr/bin/env python3

import sys
import tempfile
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_content_custody import (
    SkillContentCustodyTextError,
    SkillContentCustodyTitleResourceLimitError,
    observe_skill_content,
)
from try_forever_skill_provenance_probe import (
    MAX_SKILL_HASH_BYTES,
    MAX_SKILL_TITLE_CHARS,
    MAX_SKILL_TITLE_LINE_BYTES,
    MAX_SKILL_TITLE_SCAN_BYTES,
)
from try_forever_skill_title_fallback_policy import (
    SkillFallbackTitleResourceLimitError,
    SkillFallbackTitleSemanticError,
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

    def observe(self, path: Path):
        return observe_skill_content(
            path,
            max_bytes=MAX_SKILL_HASH_BYTES,
            max_title_scan_bytes=MAX_SKILL_TITLE_SCAN_BYTES,
            max_title_line_bytes=MAX_SKILL_TITLE_LINE_BYTES,
            max_title_chars=MAX_SKILL_TITLE_CHARS,
        )

    def test_exact_title_character_budget_is_admitted_from_one_artifact(self):
        path = self.skill_path("exact-title")
        title = "T" * MAX_SKILL_TITLE_CHARS
        path.write_text(f"# {title}\n", encoding="utf-8")

        observation = self.observe(path)

        self.assertEqual(title, observation.title)
        self.assertEqual(path.stat().st_size, observation.size_bytes)
        self.assertEqual(64, len(observation.sha256))

    def test_title_character_budget_plus_one_rejects_without_truncation(self):
        path = self.skill_path("oversized-title")
        title = "T" * (MAX_SKILL_TITLE_CHARS + 1)
        path.write_text(f"# {title}\n", encoding="utf-8")

        with self.assertRaises(SkillFallbackTitleResourceLimitError):
            self.observe(path)

    def test_oversized_first_line_is_rejected_before_later_plausible_h1(self):
        path = self.skill_path("oversized-line")
        path.write_bytes(
            (b"x" * (MAX_SKILL_TITLE_LINE_BYTES + 1))
            + b"\n# Counterfeit Later Title\n"
        )

        with self.assertRaises(SkillContentCustodyTitleResourceLimitError):
            self.observe(path)

    def test_scan_budget_exhaustion_rejects_late_title(self):
        path = self.skill_path("late-title")
        line = b"x" * (MAX_SKILL_TITLE_LINE_BYTES - 1) + b"\n"
        repeats = MAX_SKILL_TITLE_SCAN_BYTES // len(line)
        path.write_bytes((line * repeats) + b"# Too Late\n")

        with self.assertRaises(SkillContentCustodyTitleResourceLimitError):
            self.observe(path)

    def test_malformed_utf8_fails_the_single_artifact_observation(self):
        path = self.skill_path("broken-utf8")
        path.write_bytes(b"# broken \xff\n")

        with self.assertRaises(SkillContentCustodyTextError):
            self.observe(path)

    def test_hidden_control_cannot_be_stripped_into_h1_authority(self):
        path = self.skill_path("hidden-control")
        path.write_text("\t# Hidden Control\n", encoding="utf-8")

        with self.assertRaises(SkillFallbackTitleSemanticError):
            self.observe(path)

    def test_titleless_file_within_scan_budget_keeps_folder_fallback(self):
        path = self.skill_path("fallback-name")
        path.write_text("No H1 here.\nStill bounded.\n", encoding="utf-8")

        observation = self.observe(path)

        self.assertEqual("fallback-name", observation.title)
        self.assertEqual(64, len(observation.sha256))


if __name__ == "__main__":
    unittest.main()
