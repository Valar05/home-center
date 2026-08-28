#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_content_custody as custody
from try_forever_generated_index_artifact_observation import GeneratedIndexArtifactObservation
from try_forever_skill_head_content_binding import git_blob_content_identity


class SkillContentCustodyTest(unittest.TestCase):
    def test_one_observation_supplies_title_sha_and_git_blob_identity(self):
        path = Path("skills/alpha/SKILL.md")
        payload = b"# One Artifact\nbody text\n"
        artifact = GeneratedIndexArtifactObservation(
            size_bytes=len(payload),
            sha256="a" * 64,
            utf8_text=payload.decode("utf-8"),
        )

        with mock.patch.object(
            custody,
            "observe_generated_index_artifact",
            return_value=artifact,
        ) as observe:
            result = custody.observe_skill_content(
                path,
                max_bytes=1024,
                max_title_scan_bytes=512,
                max_title_line_bytes=128,
                max_title_chars=64,
            )

        observe.assert_called_once_with(path, max_bytes=1024)
        self.assertEqual("One Artifact", result.title)
        self.assertEqual("a" * 64, result.sha256)
        self.assertEqual(len(payload), result.size_bytes)
        self.assertEqual(git_blob_content_identity(payload), result.git_blob_identity)

    def test_fallback_title_and_git_blob_identity_share_same_observed_text(self):
        path = Path("skills/fallback-name/SKILL.md")
        payload = b"body only\n"
        artifact = GeneratedIndexArtifactObservation(
            size_bytes=len(payload),
            sha256="b" * 64,
            utf8_text=payload.decode("utf-8"),
        )
        with mock.patch.object(
            custody,
            "observe_generated_index_artifact",
            return_value=artifact,
        ) as observe:
            result = custody.observe_skill_content(
                path,
                max_bytes=1024,
                max_title_scan_bytes=512,
                max_title_line_bytes=128,
                max_title_chars=64,
            )
        observe.assert_called_once_with(path, max_bytes=1024)
        self.assertEqual("fallback-name", result.title)
        self.assertEqual("b" * 64, result.sha256)
        self.assertEqual(git_blob_content_identity(payload), result.git_blob_identity)

    def test_title_line_budget_rejects_without_reopening_named_path(self):
        path = Path("skills/alpha/SKILL.md")
        payload = ("# " + ("x" * 80) + "\nbody\n").encode("utf-8")
        artifact = GeneratedIndexArtifactObservation(
            size_bytes=len(payload),
            sha256="c" * 64,
            utf8_text=payload.decode("utf-8"),
        )
        with mock.patch.object(
            custody,
            "observe_generated_index_artifact",
            return_value=artifact,
        ) as observe:
            with self.assertRaises(custody.SkillContentCustodyTitleResourceLimitError):
                custody.observe_skill_content(
                    path,
                    max_bytes=1024,
                    max_title_scan_bytes=64,
                    max_title_line_bytes=32,
                    max_title_chars=128,
                )
        observe.assert_called_once()

    def test_observation_byte_count_drift_fails_closed(self):
        path = Path("skills/alpha/SKILL.md")
        payload = b"# Alpha\n"
        artifact = GeneratedIndexArtifactObservation(
            size_bytes=len(payload) + 1,
            sha256="d" * 64,
            utf8_text=payload.decode("utf-8"),
        )
        with mock.patch.object(
            custody,
            "observe_generated_index_artifact",
            return_value=artifact,
        ) as observe:
            with self.assertRaises(custody.SkillContentCustodyTextError):
                custody.observe_skill_content(
                    path,
                    max_bytes=1024,
                    max_title_scan_bytes=512,
                    max_title_line_bytes=128,
                    max_title_chars=64,
                )
        observe.assert_called_once_with(path, max_bytes=1024)


if __name__ == "__main__":
    unittest.main()
