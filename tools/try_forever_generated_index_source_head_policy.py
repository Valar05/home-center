#!/usr/bin/env python3
"""Exact generated-index source-HEAD admission for TRY FOREVER provenance.

Generated-index metadata is a discovery aid, never repository authority. Even so,
its declared source HEAD is evidence and must be classified by evidence shape before
freshness comparison. A malformed, case-normalized, whitespace-normalized, or
control-bearing string is not an ordinary stale Git identity.

This helper owns no JSON parsing, repository I/O, skill discovery, renderer, phone
surface, P0 lane, deployment, or acceptance. The sole provenance owner remains
``try_forever_skill_provenance_probe.py``. Canonical Git object-ID shape is reused
from the repository's existing authority-facing Git observation organ rather than
growing a second definition.
"""

from __future__ import annotations

from typing import Any

from try_forever_repository_emission_observation import _is_git_object_id


class GeneratedIndexSourceHeadError(ValueError):
    """Generated-index sourceHead cannot be admitted as exact Git identity evidence."""


def admit_generated_index_source_head(value: Any) -> str:
    """Return exact sourceHead or fail closed on malformed declared identity.

    ``None`` and the exact empty string remain the owner's existing "not declared"
    state. Any non-empty declaration must already be canonical lowercase SHA-1 or
    SHA-256 object-ID text under the same shape contract used by repository custody.
    No trim, case-fold, Unicode normalization, or other repair is permitted because
    the exact declared identity is the evidence.
    """

    if value is None:
        return ""
    if type(value) is not str:
        raise GeneratedIndexSourceHeadError(
            "generated index sourceHead must be exact string evidence"
        )
    if value == "":
        return ""
    if not _is_git_object_id(value):
        raise GeneratedIndexSourceHeadError(
            "generated index sourceHead must be canonical lowercase SHA-1 or SHA-256 object-ID text"
        )
    return value


__all__ = [
    "GeneratedIndexSourceHeadError",
    "admit_generated_index_source_head",
]
