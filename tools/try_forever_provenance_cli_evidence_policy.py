#!/usr/bin/env python3
"""Exact authority-facing CLI evidence admission for TRY FOREVER provenance.

The provenance probe currently accepts ``--expected-head`` as arbitrary text and
``--max-index-age-hours`` as any argparse float. Those values participate in
repository/index authority decisions and durable report evidence, so they must not
depend on broad normalization, non-finite arithmetic, or control-bearing free text.

This module is pure supporting source. It owns no argparse parser, repository I/O,
renderer, phone surface, P0 recovery lane, deployment, or acceptance path.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


class ProvenanceCliEvidenceError(ValueError):
    """Authority-facing CLI evidence is not exact enough to enter provenance logic."""


def is_canonical_git_object_id(value: str) -> bool:
    """Return whether *value* is one lowercase SHA-1/SHA-256 object id spelling."""

    return len(value) in (40, 64) and all(
        character in "0123456789abcdef" for character in value
    )


def admit_expected_head(value: Any) -> str:
    """Admit empty/no binding or one exact canonical Git object id.

    No trimming, case-folding, Unicode normalization, or best-effort extraction is
    allowed. Rejected text must never become durable ``expectedHeadError`` content.
    """

    if value is None or value == "":
        return ""
    if not isinstance(value, str) or not is_canonical_git_object_id(value):
        raise ProvenanceCliEvidenceError(
            "expected head must be empty or one canonical lowercase SHA-1/SHA-256 object id"
        )
    return value


def admit_max_index_age_hours(value: Any) -> float:
    """Admit one finite non-negative generated-index freshness window.

    ``bool`` is rejected explicitly even though Python treats it as an ``int``.
    Negative values are not silently clamped to zero and infinity cannot disable
    freshness comparison by arithmetic accident.
    """

    if type(value) not in (int, float):
        raise ProvenanceCliEvidenceError(
            "maximum generated-index age must be a finite non-negative number"
        )
    admitted = float(value)
    if not math.isfinite(admitted) or admitted < 0.0:
        raise ProvenanceCliEvidenceError(
            "maximum generated-index age must be finite and non-negative"
        )
    return admitted


@dataclass(frozen=True)
class ProvenanceCliEvidence:
    expected_head: str
    max_index_age_hours: float


def admit_cli_evidence(
    *,
    expected_head: Any,
    max_index_age_hours: Any,
) -> ProvenanceCliEvidence:
    """Admit the authority-facing CLI values as one explicit contract."""

    return ProvenanceCliEvidence(
        expected_head=admit_expected_head(expected_head),
        max_index_age_hours=admit_max_index_age_hours(max_index_age_hours),
    )


__all__ = [
    "ProvenanceCliEvidence",
    "ProvenanceCliEvidenceError",
    "admit_cli_evidence",
    "admit_expected_head",
    "admit_max_index_age_hours",
    "is_canonical_git_object_id",
]
