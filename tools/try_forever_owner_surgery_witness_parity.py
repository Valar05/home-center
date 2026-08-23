#!/usr/bin/env python3
"""Supporting facade for canonical owner-surgery artifact-content witness parity.

The stronger parity invariant is now owned by the existing backend-result integrity gate so backend
authority admission cannot bypass it. This module remains as the narrow supporting/review surface
used by witness-focused regressions and doctrine; it delegates to that owner gate instead of
creating a second inventory parser or circular authority dependency.
"""

from __future__ import annotations

from collections.abc import Mapping

from try_forever_owner_surgery_backend_result_integrity import (
    BackendWitnessParityError,
    CANONICAL_CUSTODY_SCHEMA,
    audit_backend_result_witness_parity,
)


SCHEMA = "try-forever-owner-surgery-witness-parity.v2"
CanonicalWitnessParityError = BackendWitnessParityError


def audit_canonical_witness_parity(result: Mapping[str, object]) -> dict[str, object]:
    """Expose the existing owner's stronger parity audit as a supporting evidence receipt."""

    integrity = audit_backend_result_witness_parity(result)
    return {
        **integrity,
        "schema": SCHEMA,
        "backendWitnessIntegritySchema": integrity["schema"],
        "canonicalCustodySchema": CANONICAL_CUSTODY_SCHEMA,
        # Preserve the focused review-receipt vocabulary used by the existing witness regressions.
        "surgeryContentIdentities": integrity["surgeriesAdmitted"],
        "artifactContentWitnesses": integrity["artifactContentWitnessesAdmitted"],
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "boundary": (
            "Canonical inventory/group custody plus Surgery↔artifactContentWitness parity are now "
            "owned by the existing backend-result integrity/admission boundary. This facade grants "
            "no additional authority and provides supporting review evidence only."
        ),
    }
