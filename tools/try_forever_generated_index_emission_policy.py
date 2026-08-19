#!/usr/bin/env python3
"""Final-emission custody policy for TRY FOREVER generated-index evidence.

A generated index may be verified against the certified clean repository snapshot,
but that currentness claim cannot outlive a later failed report-emission custody
check. Diagnostic STALE/UNRESOLVED evidence may survive; VERIFIED_CURRENT authority
is conservatively withheld. This pure policy owns no repository I/O, renderer,
scheduler, phone surface, or P0 recovery lane.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeneratedIndexEmissionVerdict:
    status: str
    reason: str
    currentness_withheld: bool


def project_generated_index_at_emission(
    *,
    prior_status: str,
    prior_reason: str,
    emission_status: str,
) -> GeneratedIndexEmissionVerdict:
    """Project prior index evidence through the final repository-custody gate.

    The final custody observation is intentionally last. We do not re-read or
    re-verify the generated index after that observation, because doing so would
    create new authority work after the declared final gate. If that gate is not
    STABLE_CLEAN, a prior VERIFIED_CURRENT claim becomes UNRESOLVED. Negative or
    already-unresolved diagnostics remain diagnostic and are not promoted.
    """

    if emission_status == "STABLE_CLEAN":
        return GeneratedIndexEmissionVerdict(
            status=prior_status,
            reason=prior_reason,
            currentness_withheld=False,
        )

    if prior_status == "VERIFIED_CURRENT":
        return GeneratedIndexEmissionVerdict(
            status="UNRESOLVED",
            reason=(
                "late report-emission snapshot revalidation failed; earlier "
                "generated-index currentness is withheld"
            ),
            currentness_withheld=True,
        )

    return GeneratedIndexEmissionVerdict(
        status=prior_status,
        reason=prior_reason,
        currentness_withheld=False,
    )
