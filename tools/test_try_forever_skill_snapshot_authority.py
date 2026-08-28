#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_snapshot_authority import certify_repository_skills


class SkillSnapshotAuthorityTest(unittest.TestCase):
    def test_stable_clean_expected_head_keeps_bounded_records(self):
        source = ("alpha", "beta")
        verdict = certify_repository_skills(
            source,
            snapshot_status="STABLE_CLEAN",
            expected_head_error="",
        )

        self.assertTrue(verdict.authoritative)
        self.assertEqual("CERTIFIED_CURRENT", verdict.status)
        self.assertEqual(source, verdict.records)
        self.assertEqual(2, verdict.count)

    def test_unstable_snapshot_returns_zero_repository_skill_authority(self):
        verdict = certify_repository_skills(
            ("alpha", "beta"),
            snapshot_status="UNSTABLE",
            expected_head_error="",
        )

        self.assertFalse(verdict.authoritative)
        self.assertEqual("UNSTABLE_SNAPSHOT", verdict.status)
        self.assertEqual((), verdict.records)
        self.assertEqual(0, verdict.count)

    def test_expected_head_mismatch_returns_zero_authority_even_when_snapshot_is_clean(self):
        verdict = certify_repository_skills(
            ("alpha",),
            snapshot_status="STABLE_CLEAN",
            expected_head_error="expected head deadbeef, observed cafe",
        )

        self.assertFalse(verdict.authoritative)
        self.assertEqual("EXPECTED_HEAD_MISMATCH", verdict.status)
        self.assertEqual((), verdict.records)

    def test_expected_head_mismatch_wins_over_unstable_snapshot_for_exact_boundary(self):
        verdict = certify_repository_skills(
            ("alpha",),
            snapshot_status="UNSTABLE",
            expected_head_error="expected head deadbeef, observed cafe",
        )

        self.assertEqual("EXPECTED_HEAD_MISMATCH", verdict.status)
        self.assertEqual((), verdict.records)

    def test_certification_does_not_mutate_the_input_sequence(self):
        source = ["alpha", "beta"]
        verdict = certify_repository_skills(
            source,
            snapshot_status="STABLE_CLEAN",
            expected_head_error="",
        )

        self.assertEqual(["alpha", "beta"], source)
        self.assertEqual(("alpha", "beta"), verdict.records)


if __name__ == "__main__":
    unittest.main()
