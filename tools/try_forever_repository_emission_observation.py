#!/usr/bin/env python3
"""Single-command repository observation for TRY FOREVER report emission.

This helper narrows the gap created by separately invoking ``git rev-parse`` and
``git status`` for a late report-emission check. One ``git status --porcelain=v2
--branch`` process supplies both the reported HEAD and worktree cleanliness.

It is still an observation, not atomic repository binding: the filesystem can
change while Git is scanning, and equal observations cannot prove away
swap-and-restore or identity reuse. This module owns no renderer, scheduler,
phone surface, P0 recovery lane, or provenance authority by itself.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RepositoryEmissionObservation:
    status: str
    reason: str
    head: str
    dirty: bool | None


def _is_git_object_id(value: str) -> bool:
    """Accept canonical SHA-1 or SHA-256 object ids, not arbitrary header text."""

    return len(value) in (40, 64) and all(
        character in "0123456789abcdef" for character in value
    )


def parse_porcelain_v2_branch_status(output: str) -> RepositoryEmissionObservation:
    """Parse one porcelain-v2 branch/status observation fail closed.

    ``branch.oid`` is authority-facing identity, so exactly one canonical header
    is required. Duplicate headers are ambiguous even when they repeat the same
    value; accepting first-wins or last-wins evidence would make parser behavior
    depend on hostile or malformed output ordering rather than one Git identity.
    """

    head = ""
    dirty = False
    oid_headers = 0

    for raw_line in output.splitlines():
        line = raw_line.rstrip("\r\n")
        if line.startswith("# branch.oid "):
            oid_headers += 1
            if oid_headers != 1:
                return RepositoryEmissionObservation(
                    status="UNAVAILABLE",
                    reason="single-command git status reported duplicate branch.oid headers",
                    head="",
                    dirty=None,
                )
            oid = line[len("# branch.oid ") :].strip()
            if not _is_git_object_id(oid):
                return RepositoryEmissionObservation(
                    status="UNAVAILABLE",
                    reason="single-command git status did not report a canonical branch.oid",
                    head="",
                    dirty=None,
                )
            head = oid
            continue
        if not line or line.startswith("# "):
            continue
        # Any porcelain-v2 record (ordinary, rename/copy, unmerged, untracked,
        # ignored when requested) means the checkout is not clean for authority.
        dirty = True

    if oid_headers != 1 or not head:
        return RepositoryEmissionObservation(
            status="UNAVAILABLE",
            reason="single-command git status did not report exactly one canonical branch.oid",
            head="",
            dirty=None,
        )

    return RepositoryEmissionObservation(
        status="OBSERVED",
        reason=(
            "HEAD and worktree cleanliness were derived from one unambiguous git "
            "status --porcelain=v2 --branch process"
        ),
        head=head,
        dirty=dirty,
    )


def observe_repository_emission(repo_root: Path) -> RepositoryEmissionObservation:
    """Capture HEAD plus cleanliness from one Git process.

    Failure is projected into bounded source-level state rather than raised into a
    caller that might accidentally reuse stale discovery-time observations.
    """

    try:
        completed = subprocess.run(
            [
                "git",
                "status",
                "--porcelain=v2",
                "--branch",
                "--untracked-files=normal",
            ],
            cwd=repo_root,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return RepositoryEmissionObservation(
            status="UNAVAILABLE",
            reason="single-command repository emission observation failed",
            head="",
            dirty=None,
        )

    return parse_porcelain_v2_branch_status(completed.stdout)
