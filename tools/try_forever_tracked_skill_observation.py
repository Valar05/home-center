#!/usr/bin/env python3
"""Bounded Git-tracked observation for TRY FOREVER repository-skill candidates.

Filesystem discovery and clean-worktree evidence do not prove that a discovered
``skills/**/SKILL.md`` is tracked by Git. This helper observes only the candidate
identities already supplied by the sole provenance owner. It deliberately does
not walk the repository, discover new skills, certify authority, render UI, touch
phone/P0 surfaces, or create a second provenance owner.

The Git subprocess reuses the repository-emission environment scrubber, uses
literal pathspecs, has a finite deadline, and bounds both candidate count and
argument bytes. Its stdout is also bounded by those literal candidate inputs.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterable

from try_forever_repository_emission_observation import (
    GIT_STATUS_TIMEOUT_SECONDS,
    _repository_observation_env,
)

DEFAULT_MAX_TRACKED_PATHS = 2048
DEFAULT_MAX_ARGUMENT_BYTES = 1024 * 1024


@dataclass(frozen=True)
class TrackedSkillObservation:
    status: str
    reason: str
    tracked_paths: tuple[str, ...]


def _literal_skill_pathspec(path: str) -> str:
    if not path or "\x00" in path:
        raise ValueError("tracked-skill identity must be non-empty and contain no NUL")
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or any(part in ("", ".", "..") for part in parsed.parts):
        raise ValueError("tracked-skill identity must be a normalized repository-relative path")
    if len(parsed.parts) < 3 or parsed.parts[0] != "skills" or parsed.parts[-1] != "SKILL.md":
        raise ValueError("tracked-skill identity must name skills/**/SKILL.md")
    return f":(literal){path}"


def observe_tracked_skill_candidates(
    repo_root: Path,
    candidate_paths: Iterable[str],
    *,
    max_paths: int = DEFAULT_MAX_TRACKED_PATHS,
    max_argument_bytes: int = DEFAULT_MAX_ARGUMENT_BYTES,
) -> TrackedSkillObservation:
    """Return the exact Git-tracked subset of an already-discovered candidate set.

    ``OBSERVED`` means the Git query completed under the declared bounds. It does
    not mean every candidate is tracked; callers must compare ``tracked_paths``
    through the existing tracked-authority policy. ``UNAVAILABLE`` fails closed
    when path admission, resource bounds, Git execution, or output identity is
    not trustworthy.
    """

    if max_paths < 0 or max_argument_bytes < 0:
        raise ValueError("tracked-skill observation budgets must be non-negative")

    candidates = tuple(sorted(set(candidate_paths)))
    if len(candidates) > max_paths:
        return TrackedSkillObservation(
            status="UNAVAILABLE",
            reason=f"tracked-skill candidate count exceeds declared budget {max_paths}",
            tracked_paths=(),
        )
    if not candidates:
        return TrackedSkillObservation(
            status="OBSERVED",
            reason="empty candidate set requires no Git tracked-path query",
            tracked_paths=(),
        )

    try:
        pathspecs = tuple(_literal_skill_pathspec(path) for path in candidates)
        argument_bytes = sum(len(os.fsencode(pathspec)) for pathspec in pathspecs)
    except (ValueError, UnicodeEncodeError) as error:
        return TrackedSkillObservation(
            status="UNAVAILABLE",
            reason=f"tracked-skill candidate identity rejected before Git query: {type(error).__name__}",
            tracked_paths=(),
        )

    if argument_bytes > max_argument_bytes:
        return TrackedSkillObservation(
            status="UNAVAILABLE",
            reason=f"tracked-skill literal pathspec bytes exceed declared budget {max_argument_bytes}",
            tracked_paths=(),
        )

    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--full-name", "--", *pathspecs],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=False,
            timeout=GIT_STATUS_TIMEOUT_SECONDS,
            env=_repository_observation_env(),
        )
    except subprocess.TimeoutExpired:
        return TrackedSkillObservation(
            status="UNAVAILABLE",
            reason="tracked-skill Git query exceeded its execution deadline",
            tracked_paths=(),
        )
    except (OSError, subprocess.CalledProcessError):
        return TrackedSkillObservation(
            status="UNAVAILABLE",
            reason="tracked-skill Git query failed",
            tracked_paths=(),
        )

    raw_paths = tuple(part for part in completed.stdout.split(b"\x00") if part)
    observed = tuple(sorted({os.fsdecode(part) for part in raw_paths}))
    candidate_set = frozenset(candidates)
    unexpected = tuple(path for path in observed if path not in candidate_set)
    if unexpected:
        return TrackedSkillObservation(
            status="UNAVAILABLE",
            reason="tracked-skill Git query returned an identity outside the exact literal candidate set",
            tracked_paths=(),
        )

    return TrackedSkillObservation(
        status="OBSERVED",
        reason="exact Git-tracked subset observed through bounded literal candidate pathspecs",
        tracked_paths=observed,
    )
