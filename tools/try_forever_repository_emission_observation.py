#!/usr/bin/env python3
"""Single-command repository observation for TRY FOREVER report emission.

This helper narrows the gap created by separately invoking ``git rev-parse`` and
``git status`` for a late report-emission check. One ``git status --porcelain=v2
--branch`` process supplies both the reported HEAD and worktree cleanliness.

The observation explicitly overrides configured submodule-ignore policy with
``--ignore-submodules=none``. A repository must not earn a clean emission receipt
merely because local configuration or .gitmodules asked status to ignore dirty
submodule worktrees.

The process itself is bounded by an owner-defined execution deadline. Timeout is
projected into the same fail-closed ``UNAVAILABLE`` state as other observation
failures; no stale prior HEAD/cleanliness evidence is returned.

Porcelain output is captured as bytes rather than host-locale text. Authority only
needs the ASCII ``branch.oid`` header plus whether any non-header record exists;
path bytes are therefore never decoded merely to decide clean/dirty state. This
prevents a hostile or non-decodable filename from crashing the evidence path.

Inherited Git repository-redirection variables are removed before the subprocess
runs. ``cwd`` alone does not defeat ``GIT_DIR`` / ``GIT_WORK_TREE`` / alternate
index/common-dir overrides, and command-scope ``GIT_CONFIG_*`` injection can also
rewrite repository behavior. Authority must observe the repository named by the
caller rather than whichever repository/config the parent process injected.

Authority-facing Git subprocesses also force ``GIT_NO_REPLACE_OBJECTS=1``. Git
replacement refs are a useful porcelain/debugging feature, but provenance must
observe the named raw repository objects rather than a replacement object graph.
Benign process environment such as ``PATH`` is preserved.

It is still an observation, not atomic repository binding: the filesystem can
change while Git is scanning, and equal observations cannot prove away
swap-and-restore or identity reuse. This module owns no renderer, scheduler,
phone surface, P0 recovery lane, or provenance authority by itself.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

GIT_STATUS_TIMEOUT_SECONDS = 5.0
_BRANCH_OID_PREFIX = b"# branch.oid "
_COMMENT_PREFIX = b"# "
_GIT_REPOSITORY_REDIRECT_ENV = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_COMMON_DIR",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_NAMESPACE",
    "GIT_SHALLOW_FILE",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_PARAMETERS",
)
_GIT_CONFIG_INJECTION_PREFIXES = (
    "GIT_CONFIG_KEY_",
    "GIT_CONFIG_VALUE_",
)


@dataclass(frozen=True)
class RepositoryEmissionObservation:
    status: str
    reason: str
    head: str
    dirty: bool | None


def _is_git_object_id(value: str) -> bool:
    return len(value) in (40, 64) and all(
        character in "0123456789abcdef" for character in value
    )


def _porcelain_bytes(output: str | bytes) -> bytes:
    if isinstance(output, bytes):
        return output
    if isinstance(output, str):
        return output.encode("utf-8", errors="surrogatepass")
    raise TypeError("porcelain-v2 status output must be str or bytes")


def _repository_observation_env() -> dict[str, str]:
    """Preserve normal process environment while removing Git authority redirects."""

    env = os.environ.copy()
    for key in _GIT_REPOSITORY_REDIRECT_ENV:
        env.pop(key, None)
    for key in tuple(env):
        if key.startswith(_GIT_CONFIG_INJECTION_PREFIXES):
            env.pop(key, None)
    env["GIT_NO_REPLACE_OBJECTS"] = "1"
    return env


def parse_porcelain_v2_branch_status(
    output: str | bytes,
) -> RepositoryEmissionObservation:
    raw_output = _porcelain_bytes(output)
    head = ""
    dirty = False
    oid_headers = 0

    for raw_line in raw_output.splitlines():
        line = raw_line.rstrip(b"\r\n")
        if line.startswith(_BRANCH_OID_PREFIX):
            oid_headers += 1
            if oid_headers != 1:
                return RepositoryEmissionObservation(
                    status="UNAVAILABLE",
                    reason="single-command git status reported duplicate branch.oid headers",
                    head="",
                    dirty=None,
                )
            raw_oid = line[len(_BRANCH_OID_PREFIX) :].strip()
            try:
                oid = raw_oid.decode("ascii", errors="strict")
            except UnicodeDecodeError:
                return RepositoryEmissionObservation(
                    status="UNAVAILABLE",
                    reason="single-command git status did not report an ASCII canonical branch.oid",
                    head="",
                    dirty=None,
                )
            if not _is_git_object_id(oid):
                return RepositoryEmissionObservation(
                    status="UNAVAILABLE",
                    reason="single-command git status did not report a canonical branch.oid",
                    head="",
                    dirty=None,
                )
            head = oid
            continue
        if not line or line.startswith(_COMMENT_PREFIX):
            continue
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
            "status --porcelain=v2 --branch process with submodule ignores disabled, "
            "inherited repository/config redirection removed, and replacement objects disabled"
        ),
        head=head,
        dirty=dirty,
    )


def observe_repository_emission(repo_root: Path) -> RepositoryEmissionObservation:
    try:
        completed = subprocess.run(
            [
                "git",
                "status",
                "--porcelain=v2",
                "--branch",
                "--untracked-files=normal",
                "--ignore-submodules=none",
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
        return RepositoryEmissionObservation(
            status="UNAVAILABLE",
            reason="single-command repository emission observation exceeded its execution deadline",
            head="",
            dirty=None,
        )
    except (OSError, subprocess.CalledProcessError):
        return RepositoryEmissionObservation(
            status="UNAVAILABLE",
            reason="single-command repository emission observation failed",
            head="",
            dirty=None,
        )
    return parse_porcelain_v2_branch_status(completed.stdout)
