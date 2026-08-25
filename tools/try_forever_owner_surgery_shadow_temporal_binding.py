#!/usr/bin/env python3
"""Fail-closed temporal content binding for the owner-surgery descriptor shadow.

Canonical owner-surgery custody v10 now emits same-observation artifact content witnesses from the
bounded reads that produced admitted Surgery records. Descriptor-shadow v3 still observes portable
and held-directory bytes later. Matching later reads therefore become temporal evidence only when
those exact later identities agree with the canonical same-observation witnesses for the exact
canonical Surgery path set.

Caller-owned canonical/shadow evidence crosses the repository's existing one-observation bounded
exact-JSON snapshot organ before this policy reads schema, identity, witnesses, status, comparisons,
or artifact evidence. The public contract therefore advertises exact built-in ``dict`` inputs rather
than arbitrary ``Mapping`` capability. This closes split-view/callback evidence without creating a
second snapshot or temporal owner.

This policy grants no promotion authority and mutates no owner. A zero-artifact inventory is not
reported as a vacuous proven content binding: there is no artifact content to bind.
"""

from __future__ import annotations

import re

from try_forever_operator_receipt_snapshot_custody import (
    OperatorReceiptSnapshotCustodyError,
    snapshot_json_mapping,
)
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
    if type(items) is not list:
        raise TemporalBindingEvidenceError(f"{field} must be one list")

    result: dict[str, tuple[int, str]] = {}
    for index, item in enumerate(items):
        if type(item) is not dict:
            raise TemporalBindingEvidenceError(f"{field}[{index}] must be one exact dict")
        path = item.get("path")
        if type(path) is not str or not path:
            raise TemporalBindingEvidenceError(f"{field}[{index}].path must be one non-empty string")
        if path in result:
            raise TemporalBindingEvidenceError(f"{field} path identity must be unique: {path}")
        byte_count = item.get("byteCount")
        if type(byte_count) is not int or byte_count < 0:
            raise TemporalBindingEvidenceError(
                f"{field}[{index}].byteCount must be one non-negative integer"
            )
        sha256 = item.get("sha256")
        if type(sha256) is not str or SHA256_RE.fullmatch(sha256) is None:
            raise TemporalBindingEvidenceError(
                f"{field}[{index}].sha256 must be 64 lowercase hexadecimal"
            )
        result[path] = (byte_count, sha256)
    return result


def _canonical_surgery_paths(canonical_result: dict[str, object]) -> set[str]:
    surgeries = canonical_result.get("surgeries")
    if type(surgeries) is not list:
        raise TemporalBindingEvidenceError("canonical surgeries must be one list")
    paths: set[str] = set()
    for index, item in enumerate(surgeries):
        if type(item) is not dict:
            raise TemporalBindingEvidenceError(
                f"canonical surgeries[{index}] must be one exact dict"
            )
        path = item.get("path")
        if type(path) is not str or not path:
            raise TemporalBindingEvidenceError(
                f"canonical surgeries[{index}].path must be one non-empty string"
            )
        if path in paths:
            raise TemporalBindingEvidenceError(f"canonical surgery path identity must be unique: {path}")
        paths.add(path)
    return paths


def _unbound(
    *,
    status: str,
    expected_result_sha256: str,
    carried_result_sha256: object,
    boundary: str,
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "status": status,
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
        "boundary": boundary,
    }


def evaluate_temporal_content_binding(
    canonical_result: dict[str, object],
    shadow_result: dict[str, object],
) -> dict[str, object]:
    """Bind canonical-result identity to later artifact observations, or fail closed.

    Both caller-owned inputs are snapshotted before any semantic read. ``TEMPORAL_CONTENT_BOUND`` is
    possible only when canonical v10 carries exact same-observation artifact witnesses for at least
    one admitted Surgery and an admitted SHADOW_MATCH carries exact true comparison booleans for the
    same artifact set.
    """

    try:
        canonical_result = snapshot_json_mapping(
            canonical_result,
            field="canonical temporal-binding evidence",
        )
        shadow_result = snapshot_json_mapping(
            shadow_result,
            field="descriptor temporal-binding evidence",
        )
    except OperatorReceiptSnapshotCustodyError as exc:
        raise TemporalBindingEvidenceError(
            "temporal binding requires bounded exact built-in-dict evidence"
        ) from exc

    if canonical_result.get("schema") != CANONICAL_SCHEMA:
        raise TemporalBindingEvidenceError("temporal binding requires exact canonical custody v10")
    if shadow_result.get("schema") != SHADOW_SCHEMA:
        raise TemporalBindingEvidenceError("temporal binding requires exact descriptor-shadow v3")

    expected_result_sha256 = _canonical_result_sha256(canonical_result)
    carried_result_sha256 = shadow_result.get("canonicalResultSha256")
    if carried_result_sha256 != expected_result_sha256:
        return _unbound(
            status="CANONICAL_RESULT_ID_MISMATCH",
            expected_result_sha256=expected_result_sha256,
            carried_result_sha256=carried_result_sha256,
            boundary="Shadow evidence is not bound to the exact canonical result payload supplied for review.",
        )

    canonical_evidence_complete = canonical_result.get("evidenceComplete")
    if type(canonical_evidence_complete) is not bool:
        raise TemporalBindingEvidenceError("canonical evidenceComplete must be one boolean")
    if not canonical_evidence_complete:
        return _unbound(
            status="CANONICAL_WOUND",
            expected_result_sha256=expected_result_sha256,
            carried_result_sha256=carried_result_sha256,
            boundary="Canonical custody is incomplete; temporal content binding cannot be admitted.",
        )

    if shadow_result.get("descriptorAuthorityAdmitted") is not False:
        raise TemporalBindingEvidenceError(
            "temporal policy accepts only non-authoritative descriptor shadow evidence"
        )
    if shadow_result.get("ownerMutation") is not False:
        raise TemporalBindingEvidenceError(
            "temporal policy accepts only shadow evidence with ownerMutation=false"
        )

    shadow_status = shadow_result.get("status")
    comparisons = (
        shadow_result.get("artifactSetMatch"),
        shadow_result.get("metricsMatch"),
        shadow_result.get("contentIdentityMatch"),
    )
    if shadow_status != "SHADOW_MATCH" or comparisons != (True, True, True):
        return _unbound(
            status="SHADOW_COMPARISON_NOT_ADMITTED",
            expected_result_sha256=expected_result_sha256,
            carried_result_sha256=carried_result_sha256,
            boundary=(
                "Temporal binding requires an exact SHADOW_MATCH with path-set, work-metric, and content-identity comparisons all true."
            ),
        )

    raw_witnesses = canonical_result.get(WITNESS_FIELD)
    if raw_witnesses is None:
        return _unbound(
            status="CANONICAL_CONTENT_WITNESS_MISSING",
            expected_result_sha256=expected_result_sha256,
            carried_result_sha256=carried_result_sha256,
            boundary=(
                "Canonical v10 does not carry same-observation artifactContentWitnesses; later portable/descriptor "
                "content agreement cannot prove which bytes produced the canonical result."
            ),
        )

    canonical_witnesses = _artifact_identity_map(raw_witnesses, field=WITNESS_FIELD)
    canonical_paths = _canonical_surgery_paths(canonical_result)
    if set(canonical_witnesses) != canonical_paths:
        raise TemporalBindingEvidenceError(
            "canonical artifactContentWitnesses path set must equal canonical surgeries path set"
        )
    if not canonical_paths:
        return _unbound(
            status="NO_CANONICAL_ARTIFACT_CONTENT",
            expected_result_sha256=expected_result_sha256,
            carried_result_sha256=carried_result_sha256,
            boundary=(
                "Canonical custody contains no admitted Surgery artifact content; an empty witness/staging set "
                "must not be reported as a proven temporal content binding."
            ),
        )

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
