#!/usr/bin/env python3
"""Cross-platform root-topology identity policy for TRY FOREVER skill discovery.

This is a helper for the existing ``try_forever_skill_provenance_probe`` only.
It is not a second probe and owns no renderer, scheduler, phone surface, P0 lane,
or deployment path.

The policy intentionally does not claim an atomic cross-platform no-follow open.
Python exposes ``os.scandir(fd)`` only on Unix, so portable source can instead
capture the no-follow root identity before work and revalidate it before any
per-file authority is granted. That detects persistent replacement/type drift,
while a swap-and-restore race entirely between observations remains an explicit
unclosed boundary.
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SkillRootIdentity:
    """One no-follow observation of the repository ``skills`` root."""

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
        # Python documents st_ino/st_dev as the portable identity fields and
        # returns a Windows file index in st_ino when available. If both are
        # unavailable/zero, identity revalidation must fail closed.
        return self.device != 0 or self.inode != 0


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


def capture_skill_root_identity(skills_root: Path) -> SkillRootIdentity:
    """Capture one no-follow identity observation without resolving redirectors."""

    observed = os.stat(skills_root, follow_symlinks=False)
    return SkillRootIdentity(
        device=int(observed.st_dev),
        inode=int(observed.st_ino),
        file_type=stat.S_IFMT(observed.st_mode),
        file_attributes=int(getattr(observed, "st_file_attributes", 0) or 0),
        reparse_tag=int(getattr(observed, "st_reparse_tag", 0) or 0),
        redirector_kind=redirector_kind_from_stat(observed),
    )


def revalidate_skill_root_identity(
    before: SkillRootIdentity,
    after: SkillRootIdentity,
) -> SkillRootRevalidationVerdict:
    """Fail closed unless both observations bind the same ordinary directory."""

    if before.redirector_kind:
        return SkillRootRevalidationVerdict(
            status="REDIRECTOR_BLOCKED",
            reason=f"skills root is a {before.redirector_kind}; repository-owned topology is required",
        )
    if after.redirector_kind:
        return SkillRootRevalidationVerdict(
            status="ROOT_CHANGED",
            reason=f"skills root became a {after.redirector_kind} while discovery was in progress",
        )
    if not before.is_directory or not after.is_directory:
        return SkillRootRevalidationVerdict(
            status="ROOT_CHANGED",
            reason="skills root was not the same ordinary directory before and after discovery",
        )
    if not before.has_stable_token or not after.has_stable_token:
        return SkillRootRevalidationVerdict(
            status="IDENTITY_UNAVAILABLE",
            reason="skills root device/inode identity is unavailable; portable revalidation cannot certify one directory object",
        )
    if (before.device, before.inode) != (after.device, after.inode):
        return SkillRootRevalidationVerdict(
            status="ROOT_CHANGED",
            reason="skills root device/inode identity changed while discovery was in progress",
        )
    return SkillRootRevalidationVerdict(
        status="STABLE",
        reason="the same no-follow skills-root device/inode identity bracketed candidate enumeration",
    )


__all__ = [
    "SkillRootIdentity",
    "SkillRootRevalidationVerdict",
    "capture_skill_root_identity",
    "redirector_kind_from_stat",
    "revalidate_skill_root_identity",
]
