#!/usr/bin/env python3
"""Fail-closed receipt-context gate for descriptor-shadow temporal binding.

This supporting source does not create promotion authority and does not replace the existing temporal
binding policy. It verifies that a SHADOW_MATCH carries the exact canonical context that the real
shadow owner is expected to preserve before delegating to ``evaluate_temporal_content_binding``.

A matching canonical-result SHA is necessary but not sufficient. A counterfeit or partially copied
shadow receipt must not earn temporal proof merely by repeating the right result digest and three
``True`` comparison booleans while disagreeing about canonical schema, canonical completeness,
canonical authority backend, or descriptor capability state.
"""

from __future__ import annotations

from collections.abc import Mapping

from try_forever_owner_surgery_descriptor_shadow_audit import (
    CANONICAL_SCHEMA,
    SCHEMA as SHADOW_SCHEMA,
    SUPPORTED,
)
from try_forever_owner_surgery_shadow_temporal_binding import (
    evaluate_temporal_content_binding,
)


SCHEMA = "try-forever-owner-surgery-shadow-temporal-receipt-integrity.v1"
PORTABLE_AUTHORITY_BACKEND = "PORTABLE_PATHNAME_REVALIDATION"


class ShadowTemporalReceiptIntegrityError(ValueError):
    """Shadow receipt context disagrees with the canonical result it claims to accompany."""


def evaluate_temporal_content_binding_with_receipt_integrity(
    canonical_result: Mapping[str, object],
    shadow_result: Mapping[str, object],
) -> dict[str, object]:
    """Validate receipt context, then delegate to the existing temporal-binding policy.

    Only ``SHADOW_MATCH`` can earn temporal proof. For that state, the shadow receipt must carry the
    exact v10 canonical schema, the exact canonical evidenceComplete boolean, the canonical portable
    authority backend, and the exact supported descriptor capability state. Other states still
    delegate to the existing temporal policy without being normalized into a match.
    """

    if not isinstance(canonical_result, Mapping):
        raise ShadowTemporalReceiptIntegrityError("canonical_result must be one mapping")
    if not isinstance(shadow_result, Mapping):
        raise ShadowTemporalReceiptIntegrityError("shadow_result must be one mapping")
    if canonical_result.get("schema") != CANONICAL_SCHEMA:
        raise ShadowTemporalReceiptIntegrityError(
            "receipt integrity requires exact canonical owner-surgery custody v10"
        )
    if shadow_result.get("schema") != SHADOW_SCHEMA:
        raise ShadowTemporalReceiptIntegrityError(
            "receipt integrity requires exact descriptor-shadow v3"
        )

    canonical_complete = canonical_result.get("evidenceComplete")
    if not isinstance(canonical_complete, bool):
        raise ShadowTemporalReceiptIntegrityError(
            "canonical evidenceComplete must be one boolean"
        )

    carried_schema = shadow_result.get("canonicalAuthoritySchema")
    if carried_schema != CANONICAL_SCHEMA:
        raise ShadowTemporalReceiptIntegrityError(
            "shadow canonicalAuthoritySchema must equal the exact canonical v10 schema"
        )

    carried_complete = shadow_result.get("canonicalEvidenceComplete")
    if carried_complete is not canonical_complete:
        raise ShadowTemporalReceiptIntegrityError(
            "shadow canonicalEvidenceComplete must equal the exact canonical evidenceComplete boolean"
        )

    if shadow_result.get("canonicalAuthorityBackend") != PORTABLE_AUTHORITY_BACKEND:
        raise ShadowTemporalReceiptIntegrityError(
            "shadow canonicalAuthorityBackend must remain the canonical portable owner"
        )

    status = shadow_result.get("status")
    if status == "SHADOW_MATCH":
        if canonical_complete is not True:
            raise ShadowTemporalReceiptIntegrityError(
                "SHADOW_MATCH cannot accompany incomplete canonical custody"
            )
        if shadow_result.get("descriptorCapabilityStatus") != SUPPORTED:
            raise ShadowTemporalReceiptIntegrityError(
                "SHADOW_MATCH requires exact supported descriptor capability evidence"
            )

    temporal = evaluate_temporal_content_binding(canonical_result, shadow_result)
    return {
        **temporal,
        "receiptIntegritySchema": SCHEMA,
        "shadowReceiptContextAdmitted": True,
    }
