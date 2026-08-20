#!/usr/bin/env python3
"""Hostile source fixtures for provenance CLI evidence admission.

These fixtures are regression source until an authorized runner executes them.
"""

import math
import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_provenance_cli_evidence_policy import (
    ProvenanceCliEvidenceError,
    admit_cli_evidence,
    admit_expected_head,
    admit_max_index_age_hours,
)


SHA1 = "0123456789abcdef0123456789abcdef01234567"
SHA256 = SHA1 + "0123456789abcdef01234567"


class ProvenanceCliEvidencePolicyTest(unittest.TestCase):
    def test_empty_expected_head_means_no_binding(self):
        self.assertEqual(admit_expected_head(""), "")
        self.assertEqual(admit_expected_head(None), "")

    def test_canonical_sha1_and_sha256_are_preserved_exactly(self):
        self.assertEqual(admit_expected_head(SHA1), SHA1)
        self.assertEqual(admit_expected_head(SHA256), SHA256)

    def test_expected_head_rejects_normalization_and_control_text(self):
        rejected = (
            f" {SHA1}",
            f"{SHA1} ",
            SHA1.upper(),
            f"{SHA1}\nFORGED",
            "not-a-git-object-id",
            123,
        )
        for value in rejected:
            with self.subTest(value=repr(value)):
                with self.assertRaises(ProvenanceCliEvidenceError):
                    admit_expected_head(value)

    def test_finite_non_negative_age_is_preserved(self):
        self.assertEqual(admit_max_index_age_hours(0), 0.0)
        self.assertEqual(admit_max_index_age_hours(0.25), 0.25)
        self.assertEqual(admit_max_index_age_hours(14 * 24), 336.0)

    def test_age_rejects_silent_clamp_and_nonfinite_freshness_disable(self):
        rejected = (-1, -0.01, math.inf, -math.inf, math.nan, True, "336")
        for value in rejected:
            with self.subTest(value=repr(value)):
                with self.assertRaises(ProvenanceCliEvidenceError):
                    admit_max_index_age_hours(value)

    def test_combined_contract_never_normalizes_one_bad_field(self):
        with self.assertRaises(ProvenanceCliEvidenceError):
            admit_cli_evidence(expected_head=f" {SHA1}", max_index_age_hours=336)
        with self.assertRaises(ProvenanceCliEvidenceError):
            admit_cli_evidence(expected_head=SHA1, max_index_age_hours=math.inf)


if __name__ == "__main__":
    unittest.main()
