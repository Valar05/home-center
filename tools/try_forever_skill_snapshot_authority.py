#!/usr/bin/env python3
"""Pure certification gate for TRY FOREVER repository-skill authority.

Discovery and authority are deliberately different states. A bounded discovery
may produce useful diagnostic records while the checkout is moving or while an
expected-head binding fails. Those records must not be emitted as certified
``repository_skill`` authority merely because a caller forgot ``--strict``.

This helper owns no repository I/O, probe process, renderer, scheduler, phone
surface, P0 recovery lane, deployment, or acceptance path. The existing
``try_forever_skill_provenance_probe`` remains the sole provenance owner.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

T = TypeVar("T")


@dataclass(frozen=True)
class SkillAuthorityCertification(Generic[T]):
    status: str
    reason: str
    records: tuple[T, ...]

    @property
    def authoritative(self) -> bool:
        return self.status == "CERTIFIED_CURRENT"

    @property
    def count(self) -> int:
        return len(self.records)


def certify_repository_skills(
    records: Sequence[T],
    *,
    snapshot_status: str,
    expected_head_error: str,
) -> SkillAuthorityCertification[T]:
    """Return records only when the report is bound to one stable clean checkout.

    ``expected_head_error`` is a separate custody gate: even a stable checkout
    must not be presented as authority for a different requested head. Failure
    is global and fail-closed; first-wins/partial authority is not produced.
    Diagnostic discovery may be retained separately by the owner if desired.
    """

    if expected_head_error.strip():
        return SkillAuthorityCertification(
            status="EXPECTED_HEAD_MISMATCH",
            reason=(
                "expected-head binding failed; discovered records are diagnostic "
                "only and cannot earn repository-skill authority"
            ),
            records=(),
        )
    if snapshot_status != "STABLE_CLEAN":
        return SkillAuthorityCertification(
            status="UNSTABLE_SNAPSHOT",
            reason=(
                "repository snapshot is not STABLE_CLEAN; discovered records are "
                "diagnostic only and cannot earn repository-skill authority"
            ),
            records=(),
        )
    return SkillAuthorityCertification(
        status="CERTIFIED_CURRENT",
        reason="one stable clean checkout and expected-head binding certify this set",
        records=tuple(records),
    )


__all__ = ["SkillAuthorityCertification", "certify_repository_skills"]
