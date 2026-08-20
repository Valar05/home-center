#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from try_forever_skill_head_content_binding import (
    assess_skill_head_content_binding,
    git_blob_content_identity,
    git_blob_content_identity_from_utf8,
)


class SkillHeadContentBindingTest(unittest.TestCase):
    def test_git_blob_identity_matches_known_sha1_and_sha256_framing(self):
        identity = git_blob_content_identity(b"Hello world\n")
        self.assertEqual(12, identity.size_bytes)
        self.assertEqual("802992c4220de19a90767f3000a79a31b98d0df7", identity.sha1_oid)
        self.assertEqual(
            "80fe97e8e24bdbd0d3ff55f19ba208315633d1d4bcd4e935e89c704656a52f51",
            identity.sha256_oid,
        )

    def test_exact_sha1_and_sha256_head_blobs_match(self):
        identity = git_blob_content_identity_from_utf8("Hello world\n")
        for expected in (identity.sha1_oid, identity.sha256_oid):
            with self.subTest(expected=expected):
                verdict = assess_skill_head_content_binding(expected, identity)
                self.assertEqual("MATCH", verdict.status)
                self.assertTrue(verdict.authoritative)
                self.assertEqual(expected, verdict.observed_content_oid)

    def test_clean_status_cannot_override_exact_content_mismatch(self):
        identity = git_blob_content_identity_from_utf8("changed worktree skill\n")
        verdict = assess_skill_head_content_binding("0" * 40, identity)
        self.assertEqual("MISMATCH", verdict.status)
        self.assertFalse(verdict.authoritative)
        self.assertNotEqual(verdict.expected_head_oid, verdict.observed_content_oid)
        self.assertIn("clean-status", verdict.reason)

    def test_uppercase_or_unknown_oid_shape_fails_closed(self):
        identity = git_blob_content_identity_from_utf8("body\n")
        for expected in ("A" * 40, "a" * 39, "a" * 41, "g" * 40):
            with self.subTest(expected=expected):
                verdict = assess_skill_head_content_binding(expected, identity)
                self.assertEqual("UNAVAILABLE", verdict.status)
                self.assertFalse(verdict.authoritative)
                self.assertEqual("", verdict.observed_content_oid)

    def test_utf8_helper_hashes_exact_encoded_bytes(self):
        text = "# 🦢\ncombining e\u0301\n"
        self.assertEqual(
            git_blob_content_identity(text.encode("utf-8")),
            git_blob_content_identity_from_utf8(text),
        )


if __name__ == "__main__":
    unittest.main()
