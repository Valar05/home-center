#!/usr/bin/env python3

import hashlib
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_provenance_probe as probe
from try_forever_provenance_report_path import project_repository_relative_report_path


class DiscoveryErrorPathProjectionTest(unittest.TestCase):
    def test_over_budget_error_path_uses_same_whole_identity_collapse_as_report_policy(self):
        # Put a combining sequence exactly across the legacy prefix-cut boundary.
        # The serialized error path must not expose a partial human-text prefix
        # merely because the diagnostic was bounded once before report projection.
        relative = ("A" * 491) + "e\u0301" + ("B" * 80)
        self.assertGreater(len(relative), probe.MAX_DISCOVERY_ERROR_PATH_CHARS)

        error = probe.DiscoveryError(
            path=probe.bounded_error_path(relative),
            stage="identity",
            error_type="SyntheticBoundary",
            reason="fixture",
        )
        serialized = probe.project_discovery_error_for_report(error)["path"]
        expected = project_repository_relative_report_path(
            relative,
            max_chars=probe.MAX_DISCOVERY_ERROR_PATH_CHARS,
        ).display_path

        self.assertEqual(expected, serialized)
        self.assertTrue(serialized.startswith("<repo-path>...#"))
        self.assertNotIn("e...#", serialized)

    def test_over_budget_zwj_identity_never_exposes_a_partial_prefix(self):
        relative = ("A" * 505) + "👩\u200d💻" + ("B" * 40)
        self.assertGreater(len(relative), probe.MAX_DISCOVERY_ERROR_PATH_CHARS)

        bounded = probe.bounded_error_path(relative)
        expected = f"<repo-path>...#{hashlib.sha256(relative.encode('utf-8')).hexdigest()[:16]}"

        self.assertEqual(expected, bounded)
        self.assertLessEqual(len(bounded), probe.MAX_DISCOVERY_ERROR_PATH_CHARS)
        self.assertNotIn("👩", bounded)
        self.assertNotIn("💻", bounded)
        self.assertNotIn("\u200d", bounded)

    def test_over_budget_digest_is_bound_to_exact_original_relative_identity(self):
        left = ("A" * 520) + "X"
        right = ("A" * 520) + "Y"

        left_serialized = probe.project_discovery_error_for_report(
            probe.DiscoveryError(
                path=probe.bounded_error_path(left),
                stage="identity",
                error_type="SyntheticBoundary",
                reason="fixture",
            )
        )["path"]
        right_serialized = probe.project_discovery_error_for_report(
            probe.DiscoveryError(
                path=probe.bounded_error_path(right),
                stage="identity",
                error_type="SyntheticBoundary",
                reason="fixture",
            )
        )["path"]

        self.assertNotEqual(left_serialized, right_serialized)
        self.assertEqual(
            f"<repo-path>...#{hashlib.sha256(left.encode('utf-8')).hexdigest()[:16]}",
            left_serialized,
        )
        self.assertEqual(
            f"<repo-path>...#{hashlib.sha256(right.encode('utf-8')).hexdigest()[:16]}",
            right_serialized,
        )

    def test_in_budget_control_text_is_still_revealed_only_at_serialization(self):
        relative = "skills/line\nfeed/SKILL.md"
        bounded = probe.bounded_error_path(relative)
        self.assertEqual(relative, bounded)

        serialized = probe.project_discovery_error_for_report(
            probe.DiscoveryError(
                path=bounded,
                stage="identity",
                error_type="SyntheticBoundary",
                reason="fixture",
            )
        )["path"]
        self.assertIn(r"\u{000A}", serialized)
        self.assertNotIn("\n", serialized)


if __name__ == "__main__":
    unittest.main()
