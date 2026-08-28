#!/usr/bin/env python3
"""Bounded HEAD-tree blob observation for TRY FOREVER repository skills.

A clean-looking worktree plus a tracked path is not enough to prove that the exact
``SKILL.md`` bytes being read are the bytes committed at ``HEAD``. Git index bits
such as assume-unchanged and skip-worktree deliberately change ordinary worktree
checking behavior. This supporting organ observes the exact regular-file blob OID
for the already-discovered bounded candidate set directly from the named HEAD tree.

It does not discover candidates, read worktree content, certify repository-skill
authority, render UI, touch phone/P0 surfaces, or create a second provenance owner.
The existing ``try_forever_skill_provenance_probe.py`` remains the sole owner.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from try_forever_repository_emission_observation import (
    GIT_STATUS_TIMEOUT_SECONDS,
    _is_git_object_id,
    _repository_observation_env,
)
from try_forever_tracked_skill_observation import (
    DEFAULT_MAX_ARGUMENT_BYTES,
    DEFAULT_MAX_TRACKED_PATHS,
    _literal_skill_pathspec,
)

_REGULAR_FILE_MODES = frozenset((b"100644", b"100755"))


@dataclass(frozen=True)
class HeadSkillBlob:
    path: str
    oid: str


@dataclass(frozen=True)
class HeadSkillBlobObservation:
    status: str
    reason: str
    head: str
    blobs: tuple[HeadSkillBlob, ...]

    @property
    def blob_by_path(self) -> dict[str, str]:
        return {blob.path: blob.oid for blob in self.blobs}


def observe_head_skill_blobs(
    repo_root: Path,
    head: str,
    candidate_paths: Iterable[str],
    *,
    max_paths: int = DEFAULT_MAX_TRACKED_PATHS,
    max_argument_bytes: int = DEFAULT_MAX_ARGUMENT_BYTES,
) -> HeadSkillBlobObservation:
    """Observe one exact regular-file blob OID per bounded candidate at ``head``.

    ``OBSERVED`` means every supplied candidate names exactly one ordinary blob in
    the requested tree. Missing entries, redirector modes, broadened output,
    malformed object IDs, duplicate records, resource overflow, Git failure, and
    timeout all fail closed as ``UNAVAILABLE`` with zero partial blob authority.
    """

    if max_paths < 0 or max_argument_bytes < 0:
        raise ValueError("HEAD skill blob observation budgets must be non-negative")
    if not _is_git_object_id(head):
        return HeadSkillBlobObservation(
            status="UNAVAILABLE",
            reason="HEAD skill blob observation requires one canonical Git object ID",
            head="",
            blobs=(),
        )

    candidates = tuple(sorted(set(candidate_paths)))
    if len(candidates) > max_paths:
        return HeadSkillBlobObservation(
            status="UNAVAILABLE",
            reason=f"HEAD skill candidate count exceeds declared budget {max_paths}",
            head=head,
            blobs=(),
        )
    if not candidates:
        return HeadSkillBlobObservation(
            status="OBSERVED",
            reason="empty skill candidate set requires no HEAD tree query",
            head=head,
            blobs=(),
        )

    try:
        pathspecs = tuple(_literal_skill_pathspec(path) for path in candidates)
        argument_bytes = sum(len(os.fsencode(pathspec)) for pathspec in pathspecs)
    except (ValueError, UnicodeEncodeError) as error:
        return HeadSkillBlobObservation(
            status="UNAVAILABLE",
            reason=f"HEAD skill candidate identity rejected before Git query: {type(error).__name__}",
            head=head,
            blobs=(),
        )

    if argument_bytes > max_argument_bytes:
        return HeadSkillBlobObservation(
            status="UNAVAILABLE",
            reason=f"HEAD skill literal pathspec bytes exceed declared budget {max_argument_bytes}",
            head=head,
            blobs=(),
        )

    try:
        completed = subprocess.run(
            [
                "git",
                "ls-tree",
                "-r",
                "-z",
                "--full-tree",
                head,
                "--",
                *pathspecs,
            ],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=False,
            timeout=GIT_STATUS_TIMEOUT_SECONDS,
            env=_repository_observation_env(),
        )
    except subprocess.TimeoutExpired:
        return HeadSkillBlobObservation(
            status="UNAVAILABLE",
            reason="HEAD skill tree query exceeded its execution deadline",
            head=head,
            blobs=(),
        )
    except (OSError, subprocess.CalledProcessError):
        return HeadSkillBlobObservation(
            status="UNAVAILABLE",
            reason="HEAD skill tree query failed",
            head=head,
            blobs=(),
        )

    candidate_set = frozenset(candidates)
    observed: dict[str, str] = {}
    for raw_entry in (entry for entry in completed.stdout.split(b"\x00") if entry):
        metadata, separator, raw_path = raw_entry.partition(b"\t")
        fields = metadata.split()
        if not separator or len(fields) != 3:
            return HeadSkillBlobObservation(
                status="UNAVAILABLE",
                reason="HEAD skill tree query returned malformed entry framing",
                head=head,
                blobs=(),
            )
        raw_mode, raw_type, raw_oid = fields
        if raw_mode not in _REGULAR_FILE_MODES or raw_type != b"blob":
            return HeadSkillBlobObservation(
                status="UNAVAILABLE",
                reason="HEAD skill tree entry is not an ordinary regular-file blob",
                head=head,
                blobs=(),
            )
        try:
            oid = raw_oid.decode("ascii", errors="strict")
            path = os.fsdecode(raw_path)
        except (UnicodeDecodeError, UnicodeEncodeError):
            return HeadSkillBlobObservation(
                status="UNAVAILABLE",
                reason="HEAD skill tree query returned an undecodable authority identity",
                head=head,
                blobs=(),
            )
        if not _is_git_object_id(oid) or len(oid) != len(head):
            return HeadSkillBlobObservation(
                status="UNAVAILABLE",
                reason="HEAD skill tree query returned a non-canonical or wrong-format blob OID",
                head=head,
                blobs=(),
            )
        if path not in candidate_set:
            return HeadSkillBlobObservation(
                status="UNAVAILABLE",
                reason="HEAD skill tree query returned an identity outside the exact literal candidate set",
                head=head,
                blobs=(),
            )
        if path in observed:
            return HeadSkillBlobObservation(
                status="UNAVAILABLE",
                reason="HEAD skill tree query returned duplicate authority for one candidate",
                head=head,
                blobs=(),
            )
        observed[path] = oid

    if frozenset(observed) != candidate_set:
        return HeadSkillBlobObservation(
            status="UNAVAILABLE",
            reason="HEAD tree does not contain exactly one ordinary blob for every discovered skill candidate",
            head=head,
            blobs=(),
        )

    blobs = tuple(HeadSkillBlob(path=path, oid=observed[path]) for path in candidates)
    return HeadSkillBlobObservation(
        status="OBSERVED",
        reason="exact regular-file HEAD blob OIDs observed for the bounded literal skill candidate set",
        head=head,
        blobs=blobs,
    )


__all__ = [
    "HeadSkillBlob",
    "HeadSkillBlobObservation",
    "observe_head_skill_blobs",
]
