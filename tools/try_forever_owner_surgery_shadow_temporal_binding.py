#!/usr/bin/env python3
"""Fail-closed temporal content binding for the owner-surgery descriptor shadow.

Current descriptor-shadow v3 fingerprints the canonical v10 result, then observes portable and
held-directory artifact bytes *after* canonical ``classify()`` has returned. Matching later reads
therefore prove staging agreement, not that those are the same bytes that produced the canonical
result. This supporting source names that missing evidence instead of letting SHADOW_MATCH imply a
stronger temporal claim.

A future canonical-owner integration may emit ``artifactContentWitnesses`` from the exact bounded
artifact observations that produced its Surgery records. Only then may this policy bind the
canonical result to later portable/descriptor observations. This module grants no promotion
authority and mutates no owner.
"""

from __future__ import annotations

import re
from collections.abc import Mapping

from try_forever_owner_surgery_descriptor_shadow_audit import (
    CANONICAL_SCHEMA,
    SCHEMA as SHADOW_SCHEMA,
    _canonical_result_sha256,
)


SCHEMA = "try-forever-owner-surgery-shadow-temporal-binding.v1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WITNESS_FIELD = "artifactContentWitnesses"


class TemporalBindingEvidenceError(ValueError):
    """Temporal binding evidence is malformed rather than merely unavailable."""


def _artifact_identity_map(items: object, *, field: str) -> dict[str, tuple[int, str]]:
    if not isinstance(items, list):
        raise TemporalBindingEvidenceError(f"{field} must be one list")

    result: dict[str, tuple[int, str]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise TemporalBindingEvidenceError(f"{field}[{index}] must be one mapping")
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise TemporalBindingEvidenceError(f"{field}[{index}].path must be one non-empty string")
        if path in result:
            raise TemporalBindingEvidenceError(f"{field} path identity must be unique: {path}")
        byte_count = item.get("byteCount")
        if isinstance(byte_count, bool) or not isinstance(byte_count, int) or byte_count < 0:
            raise TemporalBindingEvidenceError(
                f"{field}[{index}].byteCount must be one non-negative integer"
            )
        sha256 = item.get("sha256")
        if not isinstance(sha256, str) or SHA256_RE.fullmatch(sha256) is None:
            raise TemporalBindingEvidenceError(
                f"{field}[{index}].sha256 must be 64 lowercase hexadecimal"
            )
        result[path] = (byte_count, sha256)
    return result


def evaluate_temporal_content_binding(
    canonical_result: Mapping[str, object],
    shadow_result: Mapping[str, object],
) -> dict[str, object]:
    """Bind canonical-result identity to later artifact observations, or fail closed.

    ``TEMPORAL_CONTENT_BOUND`` is possible only when canonical v10 itself carries exact
    same-observation artifact witnesses and both later staging mechanisms match those witnesses.
    Current canonical v10 does not yet emit that field, so today's honest result is
    ``CANONICAL_CONTENT_WITNESS_MISSING``.
    """

    if not isinstance(canonical_result, Mapping):
        raise TemporalBindingEvidenceError("canonical_result must be one mapping")
    if not isinstance(shadow_result, Mapping):
        raise TemporalBindingEvidenceError("shadow_result must be one mapping")
    if canonical_result.get("schema") != CANONICAL_SCHEMA:
        raise TemporalBindingEvidenceError("temporal binding requires exact canonical custody v10")
    if shadow_result.get("schema") != SHADOW_SCHEMA:
        raise TemporalBindingEvidenceError("temporal binding requires exact descriptor-shadow v3")

    expected_result_sha256 = _canonical_result_sha256(canonical_result)
    carried_result_sha256 = shadow_result.get("canonicalResultSha256")
    if carried_result_sha256 != expected_result_sha256:
        return {
            "schema": SCHEMA,
            "status": "CANONICAL_RESULT_ID_MISMATCH",
            "canonicalResultSha256": expected_result_sha256,
            "shadowCanonicalResultSha256": carried_result_sha256,
            "temporalBindingProven": False,
            "authorityAdmitted": False,
            "ownerMutation": False,
            "regressionExecuted": False,
            "tested": False,
            "runtimeUi": False,
            "runtimeTalkBack": False,
            "phoneDelivered": False,
            "boundary": "Shadow evidence is not bound to the exact canonical result payload supplied for review.",
        }

    raw_witnesses = canonical_result.get(WITNESS_FIELD)
    if raw_witnesses is None:
        return {
            "schema": SCHEMA,
            "status": "CANONICAL_CONTENT_WITNESS_MISSING",
            "canonicalResultSha256": expected_result_sha256,
            "shadowCanonicalResultSha256": carried_result_sha256,
            "temporalBindingProven": False,
            "authorityAdmitted": False,
            "ownerMutation": False,
            "regressionExecuted": False,
            "tested": False,
            "runtimeUi": False,
            "runtimeTalkBack": False,
            "phoneDelivered": False,
            "boundary": (
                "Canonical v10 does not carry same-observation artifactContentWitnesses; later portable/descriptor "
                "content agreement cannot prove which bytes produced the canonical result."
            ),
        }

    canonical_witnesses = _artifact_identity_map(raw_witnesses, field=WITNESS_FIELD)
    portable = _artifact_identity_map(
        shadow_result.get("portableShadowArtifacts"),
        field="portableShadowArtifacts",
    )
    descriptor = _artifact_identity_map(
        shadow_result.get("descriptorArtifacts"),
        field="descriptorArtifacts",
    )

    bound = canonical_witnesses == portable == descriptor
    return {
        "schema": SCHEMA,
        "status": "TEMPORAL_CONTENT_BOUND" if bound else "TEMPORAL_CONTENT_DIVERGED",
        "canonicalResultSha256": expected_result_sha256,
        "shadowCanonicalResultSha256": carried_result_sha256,
        "canonicalWitnessCount": len(canonical_witnesses),
        "portableWitnessCount": len(portable),
        "descriptorWitnessCount": len(descriptor),
        "temporalBindingProven": bound,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "boundary": (
            "Canonical same-observation content witnesses and both later staging mechanisms agree exactly; this "
            "binds the evidence timeline but still grants no promotion authority or filesystem atomicity."
            if bound
            else "Canonical same-observation content witnesses and later staging evidence differ; stop before owner composition."
        ),
    }
