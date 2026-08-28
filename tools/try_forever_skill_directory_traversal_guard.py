#!/usr/bin/env python3
"""Fail-closed child-directory topology revalidation for skill traversal.

The existing provenance probe discovers child directories with no-follow DirEntry
metadata, but later traverses a queued Path. A directory can be replaced between
those two moments. This helper gives the existing owner a portable observation /
revalidation vocabulary without pretending Python provides one universal atomic
no-follow directory-open primitive on every supported platform.

It owns no traversal loop, provenance report, registry, renderer, scheduler,
phone surface, P0 recovery lane, deployment, or acceptance path.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path

from try_forever_skill_root_identity import redirector_kind_from_stat


@dataclass(frozen=True)
class SkillDirectoryIdentity:
    device: int
    inode: int
    file_type: int
    redirector_kind: str

    @property
    def is_directory(self) -> bool:
        return self.file_type == stat.S_IFDIR

    @property
    def has_stable_token(self) -> bool:
        return self.inode != 0


@dataclass(frozen=True)
class SkillDirectoryTraversalVerdict:
    status: str
    reason: str


def capture_skill_directory_identity(path: Path) -> SkillDirectoryIdentity:
    """Capture one child-directory observation without following redirectors."""

    observed = os.stat(path, follow_symlinks=False)
    return SkillDirectoryIdentity(
        device=int(observed.st_dev),
        inode=int(observed.st_ino),
        file_type=stat.S_IFMT(observed.st_mode),
        redirector_kind=redirector_kind_from_stat(observed),
    )


def revalidate_skill_directory_for_traversal(
    discovered: SkillDirectoryIdentity,
    before_scan: SkillDirectoryIdentity,
) -> SkillDirectoryTraversalVerdict:
    """Reject redirector/type/identity drift before a queued child is traversed.

    This catches persistent replacement between parent enumeration and child
    traversal. It intentionally does not claim to close a swap-and-restore race,
    identity reuse, or replacement after this observation but before ``scandir``.
    Those require a stronger platform-specific handle-binding strategy.
    """

    if discovered.redirector_kind:
        return SkillDirectoryTraversalVerdict(
            status="REDIRECTOR_BLOCKED",
            reason=(
                "child directory was discovered as a redirector; repository-owned "
                "traversal topology is required"
            ),
        )
    if before_scan.redirector_kind:
        return SkillDirectoryTraversalVerdict(
            status="DIRECTORY_CHANGED",
            reason=(
                "queued child directory became a redirector before traversal; "
                "do not follow it"
            ),
        )
    if not discovered.is_directory or not before_scan.is_directory:
        return SkillDirectoryTraversalVerdict(
            status="DIRECTORY_CHANGED",
            reason="queued child path is not the same ordinary directory shape",
        )
    if not discovered.has_stable_token or not before_scan.has_stable_token:
        return SkillDirectoryTraversalVerdict(
            status="IDENTITY_UNAVAILABLE",
            reason=(
                "child directory inode/file-index identity is unavailable; portable "
                "revalidation cannot certify one queued directory object"
            ),
        )
    if (discovered.device, discovered.inode) != (
        before_scan.device,
        before_scan.inode,
    ):
        return SkillDirectoryTraversalVerdict(
            status="DIRECTORY_CHANGED",
            reason=(
                "queued child directory device/inode identity changed between "
                "discovery and traversal"
            ),
        )
    return SkillDirectoryTraversalVerdict(
        status="STABLE",
        reason=(
            "the same ordinary child-directory device/inode identity was observed "
            "at discovery and immediately before traversal"
        ),
    )


__all__ = [
    "SkillDirectoryIdentity",
    "SkillDirectoryTraversalVerdict",
    "capture_skill_directory_identity",
    "revalidate_skill_directory_for_traversal",
]
