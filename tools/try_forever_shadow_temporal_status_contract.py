#!/usr/bin/env python3
"""Exact status admission for descriptor-shadow temporal binding receipts.

The temporal-binding owner emits a finite status vocabulary. Receipt self-integrity must not accept an
arbitrary non-empty string merely because ``temporalBindingProven`` is false. This supporting organ
admits only the currently owned temporal states and grants no authority, TESTED, runtime, deployment,
phone delivery, or acceptance.
"""

from __future__ import annotations


SCHEMA = "try-forever-shadow-temporal-status-contract.v1"
ADMITTED_TEMPORAL_STATUSES = frozenset(
    {
        "CANONICAL_RESULT_ID_MISMATCH",
        "CANONICAL_WOUND",
        "SHADOW_COMPARISON_NOT_ADMITTED",
        "CANONICAL_CONTENT_WITNESS_MISSING",
        "NO_CANONICAL_ARTIFACT_CONTENT",
        "TEMPORAL_CONTENT_BOUND",
        "TEMPORAL_CONTENT_DIVERGED",
    }
)


class TemporalStatusContractError(ValueError):
    """Temporal receipt status is not one exact state owned by the temporal policy."""


def admit_temporal_status(value: object) -> str:
    """Return one exact admitted temporal status; never normalize unknown evidence."""

    if not isinstance(value, str) or value not in ADMITTED_TEMPORAL_STATUSES:
        raise TemporalStatusContractError(
            f"temporal status must be one exact admitted state, got {value!r}"
        )
    return value
