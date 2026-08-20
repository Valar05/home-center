#!/usr/bin/env python3

import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

TOOLS_DIR = Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import try_forever_skill_head_blob_observation as head_blob


HEAD = "a" * 40
BLOB_A = "b" * 40
BLOB_B = "c" * 40


def completed(stdout: bytes):
    return SimpleNamespace(stdout=stdout, returncode=0)


class HeadSkillBlobObservationTest(unittest.TestCase):
    def test_exact_regular_blobs_are_observed_in_candidate_order(self):
        stdout = (
            f"100644 blob {BLOB_B}\tskills/zeta/SKILL.md\0".encode()
            + f"100755 blob {BLOB_A}\tskills/alpha/SKILL.md\0".encode()
        )
        with mock.patch.object(head_blob.subprocess, "run", return_value=completed(stdout)) as run:
            result = head_blob.observe_head_skill_blobs(
                Path("/repo"),
                HEAD,
                ("skills/zeta/SKILL.md", "skills/alpha/SKILL.md"),
            )

        self.assertEqual("OBSERVED", result.status)
        self.assertEqual(
            {
                "skills/alpha/SKILL.md": BLOB_A,
                "skills/zeta/SKILL.md": BLOB_B,
            },
            result.blob_by_path,
        )
        argv = run.call_args.args[0]
        self.assertEqual("git", argv[0])
        self.assertIn("ls-tree", argv)
        self.assertIn("--full-tree", argv)
        self.assertIn(f":(literal)skills/alpha/SKILL.md", argv)
        self.assertIn(f":(literal)skills/zeta/SKILL.md", argv)
        self.assertFalse(run.call_args.kwargs["text"])
        self.assertEqual("1", run.call_args.kwargs["env"]["GIT_NO_REPLACE_OBJECTS"])

    def test_head_symlink_mode_fails_closed_with_zero_partial_authority(self):
        stdout = (
            f"100644 blob {BLOB_A}\tskills/alpha/SKILL.md\0".encode()
            + f"120000 blob {BLOB_B}\tskills/zeta/SKILL.md\0".encode()
        )
        with mock.patch.object(head_blob.subprocess, "run", return_value=completed(stdout)):
            result = head_blob.observe_head_skill_blobs(
                Path("/repo"),
                HEAD,
                ("skills/alpha/SKILL.md", "skills/zeta/SKILL.md"),
            )
        self.assertEqual("UNAVAILABLE", result.status)
        self.assertEqual((), result.blobs)

    def test_missing_head_candidate_fails_closed(self):
        stdout = f"100644 blob {BLOB_A}\tskills/alpha/SKILL.md\0".encode()
        with mock.patch.object(head_blob.subprocess, "run", return_value=completed(stdout)):
            result = head_blob.observe_head_skill_blobs(
                Path("/repo"),
                HEAD,
                ("skills/alpha/SKILL.md", "skills/zeta/SKILL.md"),
            )
        self.assertEqual("UNAVAILABLE", result.status)
        self.assertEqual((), result.blobs)

    def test_unexpected_path_or_duplicate_record_fails_closed(self):
        unexpected = f"100644 blob {BLOB_A}\tskills/other/SKILL.md\0".encode()
        duplicate = (
            f"100644 blob {BLOB_A}\tskills/alpha/SKILL.md\0".encode()
            + f"100644 blob {BLOB_A}\tskills/alpha/SKILL.md\0".encode()
        )
        for stdout in (unexpected, duplicate):
            with self.subTest(stdout=stdout):
                with mock.patch.object(head_blob.subprocess, "run", return_value=completed(stdout)):
                    result = head_blob.observe_head_skill_blobs(
                        Path("/repo"), HEAD, ("skills/alpha/SKILL.md",)
                    )
                self.assertEqual("UNAVAILABLE", result.status)
                self.assertEqual((), result.blobs)

    def test_noncanonical_head_is_rejected_without_git_io(self):
        with mock.patch.object(head_blob.subprocess, "run") as run:
            result = head_blob.observe_head_skill_blobs(
                Path("/repo"), "A" * 40, ("skills/alpha/SKILL.md",)
            )
        self.assertEqual("UNAVAILABLE", result.status)
        run.assert_not_called()

    def test_timeout_is_bounded_unavailable(self):
        with mock.patch.object(
            head_blob.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(cmd="git", timeout=5),
        ):
            result = head_blob.observe_head_skill_blobs(
                Path("/repo"), HEAD, ("skills/alpha/SKILL.md",)
            )
        self.assertEqual("UNAVAILABLE", result.status)
        self.assertEqual((), result.blobs)


if __name__ == "__main__":
    unittest.main()
