#!/usr/bin/env python3
from __future__ import annotations

import unittest

from try_forever_provenance_report_path import project_repository_relative_report_path


class ProvenanceReportPathSeparatorEvidenceTest(unittest.TestCase):
    def test_line_and_paragraph_separators_are_revealed_not_emitted_raw(self) -> None:
        relative = "skills/line\u2028paragraph\u2029wall/SKILL.md"
        projection = project_repository_relative_report_path(relative)

        self.assertNotIn("\u2028", projection.display_path)
        self.assertNotIn("\u2029", projection.display_path)
        self.assertIn(r"\u{2028}", projection.display_path)
        self.assertIn(r"\u{2029}", projection.display_path)

    def test_literal_separator_marker_text_cannot_alias_actual_separator(self) -> None:
        actual = project_repository_relative_report_path(
            "skills/line\u2028wall/SKILL.md"
        )
        literal = project_repository_relative_report_path(
            r"skills/line\u{2028}wall/SKILL.md"
        )

        self.assertNotEqual(actual.display_path, literal.display_path)
        self.assertIn(r"\u{2028}", actual.display_path)
        self.assertIn(r"\\u{2028}", literal.display_path)

    def test_over_budget_separator_path_collapses_from_exact_identity(self) -> None:
        relative = "skills/" + ("\u2028" * 40) + "/SKILL.md"
        projection = project_repository_relative_report_path(relative, max_chars=64)

        self.assertLessEqual(len(projection.display_path), 64)
        self.assertRegex(projection.display_path, r"^<repo-path>\.\.\.#[0-9a-f]{16}$")
        self.assertNotIn("\u2028", projection.display_path)


if __name__ == "__main__":
    unittest.main()
