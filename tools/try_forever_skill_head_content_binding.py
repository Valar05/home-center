#!/usr/bin/env python3
"""Pure worktree-content ↔ HEAD-blob binding for TRY FOREVER repository skills.

Git clean-status evidence is useful but not sufficient authority for exact worktree
content because index flags can intentionally alter ordinary worktree checking.
This supporting policy computes the Git blob object IDs for one exact observed UTF-8
artifact and compares them with the blob identity obtained from the named HEAD tree.

It performs no repository I/O, discovery, rendering, phone/P0 work, deployment, or
acceptance. The sole provenance owner remains ``try_forever_skill_provenance_probe``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class GitBlobContentIdentity:
    size_bytes: int
    sha1_oid: str
    sha256_oid: str


@dataclass(frozen=True)
class SkillHeadContentBinding:
    status: str
    reason: str
    expected_head_oid: str
    observed_content_oid: str

    @property
    def authoritative(self) -> bool:
        return self.status == "MATCH"


def git_blob_content_identity(content: bytes) -> GitBlobContentIdentity:
    """Return Git blob IDs for exact bytes under both repository hash formats."""

    header = f"blob {len(content)}\0".encode("ascii")
    framed = header + content
    return GitBlobContentIdentity(
        size_bytes=len(content),
        sha1_oid=hashlib.sha1(framed).hexdigest(),  # Git SHA-1 object format compatibility.
        sha256_oid=hashlib.sha256(framed).hexdigest(),
    )


def git_blob_content_identity_from_utf8(utf8_text: str) -> GitBlobContentIdentity:
    """Return exact blob identities for already-admitted strict UTF-8 text."""

    return git_blob_content_identity(utf8_text.encode("utf-8", errors="strict"))


def assess_skill_head_content_binding(
    expected_head_oid: str,
    content_identity: GitBlobContentIdentity,
) -> SkillHeadContentBinding:
    """Fail closed unless exact observed content is the exact HEAD blob.

    A 40-hex expected OID selects the SHA-1 Git object identity; a 64-hex expected
    OID selects SHA-256. Any other shape is unavailable authority rather than an
    opportunity to normalize or guess.
    """

    if len(expected_head_oid) == 40:
        observed_oid = content_identity.sha1_oid
    elif len(expected_head_oid) == 64:
        observed_oid = content_identity.sha256_oid
    else:
        return SkillHeadContentBinding(
            status="UNAVAILABLE",
            reason="HEAD blob identity uses an unsupported or non-canonical object-ID length",
            expected_head_oid=expected_head_oid,
            observed_content_oid="",
        )

    if not expected_head_oid or any(
        character not in "0123456789abcdef" for character in expected_head_oid
    ):
        return SkillHeadContentBinding(
            status="UNAVAILABLE",
            reason="HEAD blob identity is not canonical lowercase hexadecimal evidence",
            expected_head_oid=expected_head_oid,
            observed_content_oid="",
        )

    if observed_oid != expected_head_oid:
        return SkillHeadContentBinding(
            status="MISMATCH",
            reason=(
                "exact observed SKILL.md content does not match the blob committed at HEAD; "
                "clean-status or tracked-path evidence cannot override this content mismatch"
            ),
            expected_head_oid=expected_head_oid,
            observed_content_oid=observed_oid,
        )

    return SkillHeadContentBinding(
        status="MATCH",
        reason="exact observed SKILL.md bytes match the ordinary blob committed at HEAD",
        expected_head_oid=expected_head_oid,
        observed_content_oid=observed_oid,
    )


__all__ = [
    "GitBlobContentIdentity",
    "SkillHeadContentBinding",
    "assess_skill_head_content_binding",
    "git_blob_content_identity",
    "git_blob_content_identity_from_utf8",
]
