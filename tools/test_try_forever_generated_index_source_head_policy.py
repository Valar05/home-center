#!/usr/bin/env python3
"""Hostile source regression for generated-index sourceHead admission."""

import unittest

from try_forever_generated_index_source_head_policy import (
    GeneratedIndexSourceHeadError,
    admit_generated_index_source_head,
)


class GeneratedIndexSourceHeadPolicyTest(unittest.TestCase):
    def test_missing_source_head_remains_missing(self):
        self.assertEqual(admit_generated_index_source_head(None), "")
        self.assertEqual(admit_generated_index_source_head(""), "")

    def test_canonical_sha1_and_sha256_are_admitted_exactly(self):
        sha1 = "a" * 40
        sha256 = "b" * 64
        self.assertEqual(admit_generated_index_source_head(sha1), sha1)
        self.assertEqual(admit_generated_index_source_head(sha256), sha256)

    def test_whitespace_is_not_normalized_into_authority(self):
        for value in (" " + "a" * 40, "a" * 40 + "\n", "\t" + "b" * 64):
            with self.subTest(value=repr(value)):
                with self.assertRaises(GeneratedIndexSourceHeadError):
                    admit_generated_index_source_head(value)

    def test_case_is_not_normalized_into_authority(self):
        with self.assertRaises(GeneratedIndexSourceHeadError):
            admit_generated_index_source_head("A" * 40)

    def test_control_or_non_hex_text_is_rejected(self):
        for value in ("a" * 39 + "\x00", "g" * 40, "a" * 39, "b" * 65):
            with self.subTest(value=repr(value)):
                with self.assertRaises(GeneratedIndexSourceHeadError):
                    admit_generated_index_source_head(value)

    def test_non_string_shapes_are_rejected(self):
        for value in (False, 0, 1.0, [], {}):
            with self.subTest(value=repr(value)):
                with self.assertRaises(GeneratedIndexSourceHeadError):
                    admit_generated_index_source_head(value)


if __name__ == "__main__":
    unittest.main()
