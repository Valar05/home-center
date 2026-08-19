#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from try_forever_provenance_report_path import (
    project_report_path,
    project_repository_relative_report_path,
)


class ProvenanceReportPathTest(unittest.TestCase):
    def test_repository_root_is_dot(self) -> None:
        projection = project_report_path(Path("/srv/home-center"), Path("/srv/home-center"))
        self.assertEqual(".", projection.display_path)
        self.assertEqual("REPOSITORY", projection.scope)

    def test_repository_file_is_relative_posix_path(self) -> None:
        projection = project_report_path(
            Path("/srv/home-center"),
            Path("/srv/home-center/reports/skills/index.json"),
        )
        self.assertEqual("reports/skills/index.json", projection.display_path)
        self.assertEqual("REPOSITORY", projection.scope)
        self.assertNotIn("/srv/home-center", projection.display_path)

    def test_repository_relative_record_path_uses_same_projection_without_filesystem_lookup(self) -> None:
        projection = project_repository_relative_report_path("skills/swan/SKILL.md")
        self.assertEqual("skills/swan/SKILL.md", projection.display_path)
        self.assertEqual("REPOSITORY", projection.scope)

    def test_repository_relative_record_path_reveals_controls_and_escapes_literal_markers(self) -> None:
        projected_control = project_repository_relative_report_path(
            "skills/line\nbidi\u202ejoin\u200d/SKILL.md"
        )
        literal_marker = project_repository_relative_report_path(
            r"skills/line\u{000A}bidi\u{202E}join\u{200D}/SKILL.md"
        )
        self.assertNotIn("\n", projected_control.display_path)
        self.assertNotIn("\u202e", projected_control.display_path)
        self.assertNotIn("\u200d", projected_control.display_path)
        self.assertIn(r"\u{000A}", projected_control.display_path)
        self.assertIn(r"\u{202E}", projected_control.display_path)
        self.assertIn(r"\u{200D}", projected_control.display_path)
        self.assertNotEqual(projected_control.display_path, literal_marker.display_path)
        self.assertIn(r"\\u{000A}", literal_marker.display_path)

    def test_repository_relative_record_path_rejects_absolute_and_parent_traversal_channels(self) -> None:
        with self.assertRaises(ValueError):
            project_repository_relative_report_path("/home/alice/secret")
        with self.assertRaises(ValueError):
            project_repository_relative_report_path("skills/../secret")
        with self.assertRaises(ValueError):
            project_repository_relative_report_path("")

    def test_repository_relative_record_path_is_hard_bounded_without_splitting_marker(self) -> None:
        relative = "skills/" + ("\u202e" * 12) + ("swan-" * 20) + "/SKILL.md"
        projection = project_repository_relative_report_path(relative, max_chars=64)
        self.assertLessEqual(len(projection.display_path), 64)
        self.assertTrue(projection.display_path.startswith("<repo-path>...#"))
        prefix = projection.display_path.split("...#", 1)[0]
        self.assertNotRegex(prefix, r"\\u\{[0-9A-F]*$")

    def test_over_budget_path_collapses_without_partial_combining_grapheme(self) -> None:
        relative = "skills/" + ("A" * 48) + "e\u0301" + ("tail-" * 12) + "/SKILL.md"
        projection = project_repository_relative_report_path(relative, max_chars=64)
        self.assertLessEqual(len(projection.display_path), 64)
        self.assertRegex(projection.display_path, r"^<repo-path>\.\.\.#[0-9a-f]{16}$")
        self.assertNotIn("\u0301", projection.display_path)

    def test_over_budget_path_collapses_without_partial_emoji_zwj_grapheme(self) -> None:
        relative = "skills/" + ("A" * 48) + "👩‍🚀" + ("tail-" * 12) + "/SKILL.md"
        projection = project_repository_relative_report_path(relative, max_chars=64)
        self.assertLessEqual(len(projection.display_path), 64)
        self.assertRegex(projection.display_path, r"^<repo-path>\.\.\.#[0-9a-f]{16}$")
        self.assertNotIn("👩", projection.display_path)
        self.assertNotIn("🚀", projection.display_path)
        self.assertNotIn("\u200d", projection.display_path)

    def test_distinct_over_budget_repository_paths_keep_distinct_repo_local_digests(self) -> None:
        first = project_repository_relative_report_path(
            "skills/" + ("A" * 100) + "/SKILL.md",
            max_chars=64,
        )
        second = project_repository_relative_report_path(
            "skills/" + ("B" * 100) + "/SKILL.md",
            max_chars=64,
        )
        self.assertNotEqual(first.display_path, second.display_path)
        self.assertTrue(first.display_path.startswith("<repo-path>...#"))
        self.assertTrue(second.display_path.startswith("<repo-path>...#"))

    def test_repository_control_and_format_characters_are_revealed_not_spoken_raw(self) -> None:
        projection = project_report_path(
            Path("/srv/home-center"),
            Path("/srv/home-center") / "reports" / "line\nbidi\u202ejoin\u200d.json",
        )
        self.assertEqual("REPOSITORY", projection.scope)
        self.assertNotIn("\n", projection.display_path)
        self.assertNotIn("\u202e", projection.display_path)
        self.assertNotIn("\u200d", projection.display_path)
        self.assertIn(r"\u{000A}", projection.display_path)
        self.assertIn(r"\u{202E}", projection.display_path)
        self.assertIn(r"\u{200D}", projection.display_path)

    def test_literal_escape_spelling_cannot_collide_with_projected_control(self) -> None:
        projected_control = project_report_path(
            Path("/srv/home-center"),
            Path("/srv/home-center") / "reports" / "x\ny.json",
        )
        literal_marker = project_report_path(
            Path("/srv/home-center"),
            Path("/srv/home-center") / "reports" / r"x\u{000A}y.json",
        )
        self.assertNotEqual(projected_control.display_path, literal_marker.display_path)
        self.assertIn(r"x\u{000A}y.json", projected_control.display_path)
        self.assertIn(r"x\\u{000A}y.json", literal_marker.display_path)

    def test_repository_evidence_projection_never_splits_an_escape_unit_at_bound(self) -> None:
        relative = "reports/" + ("\u202e" * 12) + "index.json"
        projection = project_report_path(
            Path("/srv/home-center"),
            Path("/srv/home-center") / relative,
            max_chars=64,
        )
        self.assertLessEqual(len(projection.display_path), 64)
        prefix = projection.display_path.split("...#", 1)[0]
        self.assertNotRegex(prefix, r"\\u\{[0-9A-F]*$")

    def test_external_path_never_serializes_host_topology_or_hash_oracle(self) -> None:
        secret_path = Path("/home/alice/private/generated-index.json")
        projection = project_report_path(Path("/srv/home-center"), secret_path)
        self.assertEqual("EXTERNAL", projection.scope)
        self.assertEqual("<external-path>", projection.display_path)
        self.assertNotIn("alice", projection.display_path)
        self.assertNotIn("/home/", projection.display_path)

    def test_distinct_external_paths_share_the_same_non_authoritative_marker(self) -> None:
        first = project_report_path(
            Path("/srv/home-center"), Path("/var/tmp/index-a.json")
        )
        second = project_report_path(
            Path("/srv/home-center"), Path("/home/bob/index-b.json")
        )
        self.assertEqual(first, second)
        self.assertEqual("<external-path>", first.display_path)

    def test_long_repository_relative_path_is_hard_bounded(self) -> None:
        relative = "reports/" + ("swan-" * 100) + "index.json"
        projection = project_report_path(
            Path("/srv/home-center"), Path("/srv/home-center") / relative, max_chars=80
        )
        self.assertEqual("REPOSITORY", projection.scope)
        self.assertLessEqual(len(projection.display_path), 80)
        self.assertRegex(projection.display_path, r"^<repo-path>\.\.\.#[0-9a-f]{16}$")

    def test_none_stays_explicitly_none(self) -> None:
        projection = project_report_path(Path("/srv/home-center"), None)
        self.assertEqual("NONE", projection.scope)
        self.assertEqual("", projection.display_path)

    def test_tiny_budget_cannot_amputate_semantic_markers(self) -> None:
        with self.assertRaises(ValueError):
            project_report_path(
                Path("/srv/home-center"), Path("/home/alice/index.json"), max_chars=16
            )

    def test_minimum_budget_still_preserves_external_marker(self) -> None:
        projection = project_report_path(
            Path("/srv/home-center"), Path("/home/alice/index.json"), max_chars=32
        )
        self.assertEqual("<external-path>", projection.display_path)


if __name__ == "__main__":
    unittest.main()
