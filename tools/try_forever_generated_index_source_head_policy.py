#!/usr/bin/env python3
"""Exact generated-index source-HEAD admission for TRY FOREVER provenance.

Generated-index metadata is a discovery aid, never repository authority.  Even so,
its declared source HEAD is evidence and must be classified by evidence shape before
freshness comparison.  A malformed, case-normalized, whitespace-normalized, or
control-bearing string is not an ordinary stale Git identity.

This helper owns no JSON parsing, repository I/O, skill discovery, renderer, phone
surface, P0 lane, deployment, or acceptance.  The sole provenance owner remains
``try_forever_skill_provenance_probe.py``.
"""

from __future__ import annotations

from typing import Any


class GeneratedIndexSourceHeadError(ValueError):
    """Generated-index sourceHead cannot be admitted as exact Git identity evidence."""


def _is_canonical_git_object_id(value: str) -> bool:
    return len(value) in (40, 64) and all(
        character in "0123456789abcdef" for character in value
    )


def admit_generated_index_source_head(value: Any) -> str:
    """Return exact sourceHead or fail closed on malformed declared identity.

    ``None`` and the exact empty string remain the owner's existing "not declared"
    state.  Any non-empty declaration must already be canonical lowercase SHA-1 or
    SHA-256 object-ID text.  No trim, case-fold, Unicode normalization, or other
    repair is permitted because the exact declared identity is the evidence.
    """

    if value is None:
        return ""
    if type(value) is not str:
        raise GeneratedIndexSourceHeadError(
            "generated index sourceHead must be exact string evidence"
        )
    if value == "":
        return ""
    if not _is_canonical_git_object_id(value):
        raise GeneratedIndexSourceHeadError(
            "generated index sourceHead must be canonical lowercase SHA-1 or SHA-256 object-ID text"
        )
    return value


__all__ = [
    "GeneratedIndexSourceHeadError",
    "admit_generated_index_source_head",
]
