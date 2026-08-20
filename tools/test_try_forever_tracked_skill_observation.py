#!/usr/bin/env python3
"""Regression source for bounded exact Git-tracked skill observation."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from try_forever_skill_tracked_authority import require_tracked_skill_candidates
from try_forever_tracked_skill_observation import observe_tracked_skill_candidates


class TrackedSkillObservationTest(unittest.TestCase):
    def test_empty_candidate_set_avoids_git_work(self):
        with patch("try_forever_tracked_skill_observation.subprocess.run") as run:
            observation = observe_tracked_skill_candidates(Path("/repo"), ())
        self.assertEqual(observation.status, "OBSERVED")
        self.assertEqual(observation.tracked_paths, ())
        run.assert_not_called()

    def test_literal_pathspecs_and_sanitized_environment_are_used(self):
        candidate = "skills/[wild]*?/SKILL.md"
        completed = SimpleNamespace(stdout=(candidate + "\x00").encode())
        with (
            patch(
                "try_forever_tracked_skill_observation._repository_observation_env",
                return_value={"PATH": "/bin"},
            ),
            patch(
                "try_forever_tracked_skill_observation.subprocess.run",
                return_value=completed,
            ) as run,
        ):
            observation = observe_tracked_skill_candidates(Path("/repo"), (candidate,))

        self.assertEqual(observation.status, "OBSERVED")
        self.assertEqual(observation.tracked_paths, (candidate,))
        args, kwargs = run.call_args
        self.assertEqual(
            args[0],
            [
                "git",
                "ls-files",
                "-z",
                "--full-name",
                "--",
                f":(literal){candidate}",
            ],
        )
        self.assertEqual(kwargs["env"], {"PATH": "/bin"})
        self.assertFalse(kwargs["text"])
        self.assertIs(kwargs["stderr"], subprocess.DEVNULL)

    def test_observed_subset_drives_existing_fail_closed_authority_policy(self):
        alpha = "skills/alpha/SKILL.md"
        ignored = "skills/ignored/SKILL.md"
        completed = SimpleNamespace(stdout=(alpha + "\x00").encode())
        with patch(
            "try_forever_tracked_skill_observation.subprocess.run",
            return_value=completed,
        ):
            observation = observe_tracked_skill_candidates(
                Path("/repo"),
                (alpha, ignored),
            )

        self.assertEqual(observation.status, "OBSERVED")
        verdict = require_tracked_skill_candidates(
            (alpha, ignored),
            observation.tracked_paths,
        )
        self.assertEqual(verdict.status, "UNTRACKED_CANDIDATE")
        self.assertEqual(verdict.untracked_paths, (ignored,))

    def test_casefold_or_broadened_output_fails_closed(self):
        candidate = "skills/Alpha/SKILL.md"
        completed = SimpleNamespace(stdout=b"skills/alpha/SKILL.md\x00")
        with patch(
            "try_forever_tracked_skill_observation.subprocess.run",
            return_value=completed,
        ):
            observation = observe_tracked_skill_candidates(Path("/repo"), (candidate,))
        self.assertEqual(observation.status, "UNAVAILABLE")
        self.assertEqual(observation.tracked_paths, ())

    def test_path_count_and_argument_budgets_fail_before_git(self):
        with patch("try_forever_tracked_skill_observation.subprocess.run") as run:
            count = observe_tracked_skill_candidates(
                Path("/repo"),
                ("skills/a/SKILL.md", "skills/b/SKILL.md"),
                max_paths=1,
            )
            size = observe_tracked_skill_candidates(
                Path("/repo"),
                ("skills/a/SKILL.md",),
                max_argument_bytes=1,
            )
        self.assertEqual(count.status, "UNAVAILABLE")
        self.assertEqual(size.status, "UNAVAILABLE")
        run.assert_not_called()

    def test_non_repository_skill_identity_fails_before_git(self):
        with patch("try_forever_tracked_skill_observation.subprocess.run") as run:
            observation = observe_tracked_skill_candidates(
                Path("/repo"),
                ("../outside/SKILL.md",),
            )
        self.assertEqual(observation.status, "UNAVAILABLE")
        self.assertEqual(observation.tracked_paths, ())
        run.assert_not_called()

    def test_git_failure_and_timeout_do_not_invent_tracked_paths(self):
        with patch(
            "try_forever_tracked_skill_observation.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["git"]),
        ):
            failed = observe_tracked_skill_candidates(
                Path("/repo"),
                ("skills/a/SKILL.md",),
            )
        with patch(
            "try_forever_tracked_skill_observation.subprocess.run",
            side_effect=subprocess.TimeoutExpired(["git"], 5),
        ):
            timed_out = observe_tracked_skill_candidates(
                Path("/repo"),
                ("skills/a/SKILL.md",),
            )
        self.assertEqual(failed.status, "UNAVAILABLE")
        self.assertEqual(failed.tracked_paths, ())
        self.assertEqual(timed_out.status, "UNAVAILABLE")
        self.assertEqual(timed_out.tracked_paths, ())


if __name__ == "__main__":
    unittest.main()
