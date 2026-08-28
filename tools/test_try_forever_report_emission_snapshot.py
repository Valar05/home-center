#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from try_forever_report_emission_snapshot import revalidate_report_emission_snapshot


class ReportEmissionSnapshotTest(unittest.TestCase):
    def test_same_clean_head_remains_stable_only_with_prior_authority(self) -> None:
        verdict = revalidate_report_emission_snapshot(
            prior_authoritative=True,
            certified_head="abc123",
            final_head="abc123",
            final_dirty=False,
        )
        self.assertEqual("STABLE_CLEAN", verdict.status)
        self.assertTrue(verdict.prior_authoritative)

    def test_non_authoritative_prior_snapshot_cannot_be_upgraded_by_matching_final_head(self) -> None:
        verdict = revalidate_report_emission_snapshot(
            prior_authoritative=False,
            certified_head="abc123",
            final_head="abc123",
            final_dirty=False,
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertFalse(verdict.prior_authoritative)
        self.assertIn("cannot manufacture authority", verdict.reason)

    def test_truthy_non_boolean_prior_authority_fails_closed(self) -> None:
        verdict = revalidate_report_emission_snapshot(
            prior_authoritative="false",  # type: ignore[arg-type]
            certified_head="abc123",
            final_head="abc123",
            final_dirty=False,
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertFalse(verdict.prior_authoritative)
        self.assertIn("explicitly authoritative", verdict.reason)

    def test_head_change_fails_closed(self) -> None:
        verdict = revalidate_report_emission_snapshot(
            prior_authoritative=True,
            certified_head="abc123",
            final_head="def456",
            final_dirty=False,
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertIn("HEAD changed", verdict.reason)

    def test_dirty_after_certification_fails_closed(self) -> None:
        verdict = revalidate_report_emission_snapshot(
            prior_authoritative=True,
            certified_head="abc123",
            final_head="abc123",
            final_dirty=True,
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertIn("became dirty", verdict.reason)

    def test_unknown_cleanliness_fails_closed(self) -> None:
        verdict = revalidate_report_emission_snapshot(
            prior_authoritative=True,
            certified_head="abc123",
            final_head="abc123",
            final_dirty=None,
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertIn("unavailable", verdict.reason)

    def test_missing_final_head_fails_closed(self) -> None:
        verdict = revalidate_report_emission_snapshot(
            prior_authoritative=True,
            certified_head="abc123",
            final_head="",
            final_dirty=False,
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertIn("HEAD is unavailable", verdict.reason)

    def test_missing_certified_head_cannot_be_upgraded_by_final_observation(self) -> None:
        verdict = revalidate_report_emission_snapshot(
            prior_authoritative=True,
            certified_head="",
            final_head="abc123",
            final_dirty=False,
        )
        self.assertEqual("UNSTABLE", verdict.status)
        self.assertIn("no certified", verdict.reason)


if __name__ == "__main__":
    unittest.main()
