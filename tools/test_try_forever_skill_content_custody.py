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


class SkillContentCustodyTest(unittest.TestCase):
    def test_one_observation_supplies_both_title_and_sha(self):
        path = Path("skills/alpha/SKILL.md")
        artifact = GeneratedIndexArtifactObservation(
            size_bytes=27,
            sha256="a" * 64,
            utf8_text="# One Artifact\nbody text\n",
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
        self.assertEqual(27, result.size_bytes)

    def test_fallback_title_is_derived_from_same_observed_text(self):
        path = Path("skills/fallback-name/SKILL.md")
        artifact = GeneratedIndexArtifactObservation(
            size_bytes=12,
            sha256="b" * 64,
            utf8_text="body only\n",
        )
        with mock.patch.object(
            custody,
            "observe_generated_index_artifact",
            return_value=artifact,
        ):
            result = custody.observe_skill_content(
                path,
                max_bytes=1024,
                max_title_scan_bytes=512,
                max_title_line_bytes=128,
                max_title_chars=64,
            )
        self.assertEqual("fallback-name", result.title)
        self.assertEqual("b" * 64, result.sha256)

    def test_title_line_budget_rejects_without_reopening_named_path(self):
        path = Path("skills/alpha/SKILL.md")
        artifact = GeneratedIndexArtifactObservation(
            size_bytes=200,
            sha256="c" * 64,
            utf8_text="# " + ("x" * 80) + "\nbody\n",
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


if __name__ == "__main__":
    unittest.main()
