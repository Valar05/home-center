#!/usr/bin/env python3
"""Exact state admission for TRY FOREVER owner-surgery evidence.

Promotion authority must never come from substring matching. The state token is evidence, so this
policy preserves exact spelling, rejects normalization-dependent text, and grants promotion
readiness only to an explicit allow-list of current promotion states.

This is supporting source only. It does not apply a surgery, mutate an owner, execute tests, touch
Phone Hands/P0, or claim runtime/deployment/delivery.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


PROMOTION_READY_STATES = frozenset({
    "PROPOSED_NOT_APPLIED",
    "CORRECTED_PROPOSED_NOT_APPLIED",
})

_STATE_RE = re.compile(r"^[A-Z0-9]+(?:_[A-Z0-9]+)*$")


class OwnerSurgeryStateError(ValueError):
    """The surgery state cannot be admitted as exact owner-custody evidence."""


@dataclass(frozen=True)
class OwnerSurgeryStateAdmission:
    state: str
    promotion_candidate: bool
    classification: str


def admit_owner_surgery_state(raw: object) -> OwnerSurgeryStateAdmission:
    """Admit one exact state token without normalization or substring authority.

    Unknown but syntactically canonical states remain useful archaeology, but they are never
    promotion candidates. Only exact entries in ``PROMOTION_READY_STATES`` may enter the promotion
    collision/current-base machinery.
    """

    if not isinstance(raw, str):
        raise OwnerSurgeryStateError("owner surgery state must be a string")
    if not raw:
        raise OwnerSurgeryStateError("owner surgery state must not be empty")
    if raw != raw.strip():
        raise OwnerSurgeryStateError("owner surgery state must not require whitespace normalization")
    if _STATE_RE.fullmatch(raw) is None:
        raise OwnerSurgeryStateError(
            "owner surgery state must be canonical uppercase ASCII letters/digits joined by underscores"
        )

    if raw in PROMOTION_READY_STATES:
        return OwnerSurgeryStateAdmission(
            state=raw,
            promotion_candidate=True,
            classification="PROMOTION_READY",
        )

    return OwnerSurgeryStateAdmission(
        state=raw,
        promotion_candidate=False,
        classification="NON_PROMOTION_OR_UNKNOWN",
    )


__all__ = [
    "OwnerSurgeryStateAdmission",
    "OwnerSurgeryStateError",
    "PROMOTION_READY_STATES",
    "admit_owner_surgery_state",
]
