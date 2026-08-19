#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from try_forever_provenance_report_path import project_report_path


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
        self.assertIn("...#", projection.display_path)

    def test_none_stays_explicitly_none(self) -> None:
        projection = project_report_path(Path("/srv/home-center"), None)
        self.assertEqual("NONE", projection.scope)
        self.assertEqual("", projection.display_path)

    def test_nonpositive_budget_is_programmer_error(self) -> None:
        with self.assertRaises(ValueError):
            project_report_path(Path("/srv/home-center"), Path("/srv/home-center/x"), max_chars=0)


if __name__ == "__main__":
    unittest.main()
