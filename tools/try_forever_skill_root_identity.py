#!/usr/bin/env python3
"""Portable no-follow directory-root identity policy for TRY FOREVER custody.

This remains one reusable source organ. The original skills-root wrappers are preserved for
``try_forever_skill_provenance_probe`` while other non-P0 evidence owners may compose the same
no-follow identity/revalidation primitive instead of growing parallel root-custody logic.

The policy intentionally does not claim an atomic cross-platform no-follow directory open.
Portable source can capture root identity before work and revalidate it afterwards. That detects
observable persistent replacement/type/redirector drift. Identity reuse and a complete
swap-and-restore race between observations remain explicit unclosed boundaries.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillRootIdentity:
    """One no-follow observation of a directory-root candidate.

    The historical type name is retained for source compatibility. The identity payload itself is
    generic and may be reused by other bounded TRY FOREVER directory owners.
    """

    device: int
    inode: int
    file_type: int
    file_attributes: int
    reparse_tag: int
    redirector_kind: str

    @property
    def is_directory(self) -> bool:
        return self.file_type == stat.S_IFDIR

    @property
    def has_stable_token(self) -> bool:
        # st_dev identifies a filesystem, not one directory object. Require a
        # non-zero inode/file-index component before (device, inode) may be used
        # as a persistent object identity. If unavailable, fail closed.
        return self.inode != 0


@dataclass(frozen=True)
class SkillRootRevalidationVerdict:
    status: str
    reason: str


def _known_reparse_tag(name: str) -> int:
    value = getattr(stat, name, 0)
    return value if isinstance(value, int) else 0


def redirector_kind_from_stat(observed: os.stat_result) -> str:
    """Classify link-like root topology from one no-follow stat observation."""

    if stat.S_ISLNK(observed.st_mode):
        return "symlink"

    tag = int(getattr(observed, "st_reparse_tag", 0) or 0)
    if tag == _known_reparse_tag("IO_REPARSE_TAG_SYMLINK") and tag != 0:
        return "symlink"
    if tag == _known_reparse_tag("IO_REPARSE_TAG_MOUNT_POINT") and tag != 0:
        return "junction"
    return ""


def capture_directory_root_identity(root: Path) -> SkillRootIdentity:
    """Capture one no-follow directory-root identity without resolving redirectors."""

    observed = os.stat(root, follow_symlinks=False)
    return SkillRootIdentity(
        device=int(observed.st_dev),
        inode=int(observed.st_ino),
        file_type=stat.S_IFMT(observed.st_mode),
        file_attributes=int(getattr(observed, "st_file_attributes", 0) or 0),
        reparse_tag=int(getattr(observed, "st_reparse_tag", 0) or 0),
        redirector_kind=redirector_kind_from_stat(observed),
    )


def revalidate_directory_root_identity(
    before: SkillRootIdentity,
    after: SkillRootIdentity,
    *,
    subject: str,
) -> SkillRootRevalidationVerdict:
    """Fail closed unless both observations bind the same ordinary directory.

    This is persistent-drift evidence, not an atomic handle-binding claim.
    """

    if before.redirector_kind:
        return SkillRootRevalidationVerdict(
            status="REDIRECTOR_BLOCKED",
            reason=f"{subject} is a {before.redirector_kind}; ordinary owned topology is required",
        )
    if after.redirector_kind:
        return SkillRootRevalidationVerdict(
            status="ROOT_CHANGED",
            reason=f"{subject} became a {after.redirector_kind} while bounded work was in progress",
        )
    if not before.is_directory or not after.is_directory:
        return SkillRootRevalidationVerdict(
            status="ROOT_CHANGED",
            reason=f"{subject} was not the same ordinary directory before and after bounded work",
        )
    if not before.has_stable_token or not after.has_stable_token:
        return SkillRootRevalidationVerdict(
            status="IDENTITY_UNAVAILABLE",
            reason=(
                f"{subject} inode/file-index identity is unavailable; portable revalidation "
                "cannot certify one directory object"
            ),
        )
    if (before.device, before.inode) != (after.device, after.inode):
        return SkillRootRevalidationVerdict(
            status="ROOT_CHANGED",
            reason=f"{subject} device/inode identity changed while bounded work was in progress",
        )
    return SkillRootRevalidationVerdict(
        status="STABLE",
        reason=f"the same no-follow {subject} device/inode identity bracketed bounded work",
    )


def capture_skill_root_identity(skills_root: Path) -> SkillRootIdentity:
    """Compatibility wrapper for the repository ``skills`` root."""

    return capture_directory_root_identity(skills_root)


def revalidate_skill_root_identity(
    before: SkillRootIdentity,
    after: SkillRootIdentity,
) -> SkillRootRevalidationVerdict:
    """Compatibility wrapper preserving skills-root behavior and evidence wording."""

    return revalidate_directory_root_identity(before, after, subject="skills root")


__all__ = [
    "SkillRootIdentity",
    "SkillRootRevalidationVerdict",
    "capture_directory_root_identity",
    "capture_skill_root_identity",
    "redirector_kind_from_stat",
    "revalidate_directory_root_identity",
    "revalidate_skill_root_identity",
]
