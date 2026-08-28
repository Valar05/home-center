#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_title_fallback_policy import (
    SkillFallbackTitleResourceLimitError,
    SkillFallbackTitleSemanticError,
    admit_fallback_title,
    admit_markdown_h1_title,
    admit_skill_title,
)


class SkillTitleSourcePolicyTest(unittest.TestCase):
    def test_exact_bound_is_preserved_without_rewrite_for_h1_or_fallback(self):
        title = "A" * 256
        self.assertEqual(title, admit_skill_title(title, max_chars=256))
        self.assertEqual(title, admit_fallback_title(title, max_chars=256))

    def test_max_plus_one_is_rejected_not_truncated_into_authority(self):
        with self.assertRaises(SkillFallbackTitleResourceLimitError):
            admit_skill_title("A" * 257, max_chars=256)

    def test_c0_and_c1_controls_are_rejected_on_shared_title_surface(self):
        for value in ("safe\nunsafe", "safe\x00unsafe", "safe\x85unsafe"):
            with self.subTest(value=repr(value)):
                with self.assertRaises(SkillFallbackTitleSemanticError):
                    admit_skill_title(value, max_chars=256)

    def test_explicit_bidi_direction_controls_are_rejected(self):
        for marker in ("\u061c", "\u200e", "\u200f", "\u202e", "\u2066", "\u2069"):
            with self.subTest(marker=hex(ord(marker))):
                with self.assertRaises(SkillFallbackTitleSemanticError):
                    admit_skill_title(f"alpha{marker}beta", max_chars=256)

    def test_ordinary_unicode_joiners_and_combining_text_are_preserved(self):
        values = (
            "emoji-👩‍🚀",
            "combining-e\u0301",
            "zero-width-space-a\u200bb",
            "word-joiner-a\u2060b",
            "zwnj-a\u200cb",
        )
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(value, admit_skill_title(value, max_chars=256))

    def test_empty_or_non_string_title_is_rejected(self):
        with self.assertRaises(SkillFallbackTitleSemanticError):
            admit_skill_title("", max_chars=256)
        with self.assertRaises(SkillFallbackTitleSemanticError):
            admit_skill_title(None, max_chars=256)  # type: ignore[arg-type]

    def test_markdown_h1_removes_only_structural_line_ending_and_ascii_margin(self):
        self.assertEqual(
            "Safe title",
            admit_markdown_h1_title("  # Safe title  \r\n", max_chars=256),
        )

    def test_markdown_h1_edge_control_cannot_disappear_via_broad_strip(self):
        for marker in ("\x09", "\x0b", "\x0c", "\x1c", "\x1f", "\x85"):
            with self.subTest(marker=hex(ord(marker))):
                with self.assertRaises(SkillFallbackTitleSemanticError):
                    admit_markdown_h1_title(f"# safe{marker}\n", max_chars=256)

    def test_markdown_h1_bidi_control_is_rejected_before_authority(self):
        with self.assertRaises(SkillFallbackTitleSemanticError):
            admit_markdown_h1_title("# alpha\u202ebeta\n", max_chars=256)

    def test_non_h1_line_returns_none(self):
        self.assertIsNone(admit_markdown_h1_title("ordinary text\n", max_chars=256))


if __name__ == "__main__":
    unittest.main()
