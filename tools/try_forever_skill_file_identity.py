#!/usr/bin/env python3
"""Portable candidate-file identity policy for TRY FOREVER skill discovery.

This helper composes into the existing ``try_forever_skill_provenance_probe``.
It is not a second probe and owns no renderer, scheduler, phone surface, P0 lane,
or deployment path.

The policy is deliberately fail-closed but deliberately *not* called atomic.
Portable no-follow stat observations can detect persistent redirectors, object
replacement, and common in-place mutation between observations. They cannot
prove that a swap-and-restore race, inode/file-index reuse, or a same-token
content rewrite did not happen entirely between observations. An eventual
platform-specific handle-bound implementation may strengthen that boundary;
this helper must not pretend to have already done so.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from try_forever_skill_root_identity import redirector_kind_from_stat


@dataclass(frozen=True)
class SkillFileIdentity:
    """One no-follow observation of a named ``SKILL.md`` candidate."""

    device: int
    inode: int
    file_type: int
    size: int
    mtime_ns: int
    redirector_kind: str

    @property
    def is_regular_file(self) -> bool:
        return self.file_type == stat.S_IFREG

    @property
    def has_stable_token(self) -> bool:
        # st_dev identifies a filesystem, not one file object. Require a
        # non-zero inode/file-index component before (device, inode) may be used
        # as a persistent object identity.
        return self.inode != 0


@dataclass(frozen=True)
class SkillFileRevalidationVerdict:
    status: str
    reason: str


def capture_skill_file_identity(path: Path) -> SkillFileIdentity:
    """Capture one no-follow candidate observation without resolving links."""

    observed = os.stat(path, follow_symlinks=False)
    return SkillFileIdentity(
        device=int(observed.st_dev),
        inode=int(observed.st_ino),
        file_type=stat.S_IFMT(observed.st_mode),
        size=int(observed.st_size),
        mtime_ns=int(getattr(observed, "st_mtime_ns", int(observed.st_mtime * 1_000_000_000))),
        redirector_kind=redirector_kind_from_stat(observed),
    )


def revalidate_skill_file_identity(
    before: SkillFileIdentity,
    after: SkillFileIdentity,
) -> SkillFileRevalidationVerdict:
    """Fail closed unless two observations describe one stable ordinary file."""

    if before.redirector_kind:
        return SkillFileRevalidationVerdict(
            status="REDIRECTOR_BLOCKED",
            reason=(
                f"SKILL.md candidate is a {before.redirector_kind}; "
                "ordinary repository-owned file topology is required"
            ),
        )
    if after.redirector_kind:
        return SkillFileRevalidationVerdict(
            status="FILE_CHANGED",
            reason=(
                f"SKILL.md candidate became a {after.redirector_kind} while "
                "repository-skill authority was being evaluated"
            ),
        )
    if not before.is_regular_file or not after.is_regular_file:
        return SkillFileRevalidationVerdict(
            status="FILE_CHANGED",
            reason="SKILL.md candidate was not the same ordinary file across observations",
        )
    if not before.has_stable_token or not after.has_stable_token:
        return SkillFileRevalidationVerdict(
            status="IDENTITY_UNAVAILABLE",
            reason=(
                "SKILL.md inode/file-index identity is unavailable; portable "
                "revalidation cannot certify one file object"
            ),
        )
    if (before.device, before.inode) != (after.device, after.inode):
        return SkillFileRevalidationVerdict(
            status="FILE_CHANGED",
            reason="SKILL.md device/inode identity changed between observations",
        )
    if before.size != after.size or before.mtime_ns != after.mtime_ns:
        return SkillFileRevalidationVerdict(
            status="FILE_CHANGED",
            reason="SKILL.md size/mtime observation changed between identity checks",
        )
    return SkillFileRevalidationVerdict(
        status="STABLE",
        reason=(
            "the same no-follow SKILL.md device/inode and size/mtime observation "
            "bracketed the checked work"
        ),
    )


__all__ = [
    "SkillFileIdentity",
    "SkillFileRevalidationVerdict",
    "capture_skill_file_identity",
    "revalidate_skill_file_identity",
]
