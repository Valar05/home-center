#!/usr/bin/env python3
"""Self-integrity gate for operator-facing descriptor-shadow receipts.

This supporting organ does not create a second descriptor authority or receipt projector. It
recomputes the comparison claims already carried by descriptor-shadow v3, validates the exact
completed-comparison context, validates wound/unavailable status against the canonical/capability
context and evidence phase that can actually produce that status, checks the already-wired temporal
receipt context, and then delegates operator display to ``project_shadow_receipt``.

The purpose is narrow: a display receipt must not say MATCH merely because three booleans say so when
the artifact evidence, work metrics, or temporal receipt contradict those booleans. Likewise, a
wound label must not be accepted when its canonical/capability context or artifact/counter phase
describes work that could not have completed before that wound. Raw evidence is left untouched.
Promotion authority, TESTED, runtime, deployment, phone delivery, and acceptance are never granted
here.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from pathlib import Path

from try_forever_operator_receipt_snapshot_custody import (
    OperatorReceiptSnapshotCustodyError,
    snapshot_json_mapping,
)
from try_forever_owner_surgery_backend_policy import PORTABLE_UNAVAILABLE
from try_forever_owner_surgery_descriptor_shadow_audit import (
    CANONICAL_SCHEMA,
    SCHEMA as SHADOW_SCHEMA,
    SUPPORTED,
)
from try_forever_owner_surgery_shadow_receipt_projection import project_shadow_receipt
from try_forever_shadow_raw_capability_membrane import (
    require_raw_shadow_capability_membrane,
)
from try_forever_shadow_temporal_status_contract import admit_temporal_status


SCHEMA = "try-forever-owner-surgery-shadow-receipt-self-integrity.v2"
PORTABLE_AUTHORITY_BACKEND = "PORTABLE_PATHNAME_REVALIDATION"
TEMPORAL_BINDING_SCHEMA = "try-forever-owner-surgery-shadow-temporal-binding.v1"
TEMPORAL_RECEIPT_INTEGRITY_SCHEMA = (
    "try-forever-owner-surgery-shadow-temporal-receipt-integrity.v1"
)
COMPLETED_STATUSES = {"SHADOW_MATCH", "SHADOW_DIVERGED"}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class ShadowReceiptSelfIntegrityError(ValueError):
    """Raw shadow evidence contradicts the operator receipt claim it would produce."""


def _nonnegative_int(value: object, *, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ShadowReceiptSelfIntegrityError(
            f"{field} must be one non-negative integer"
        )
    return value


def _canonical_sha256(value: object, *, field: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise ShadowReceiptSelfIntegrityError(
            f"{field} must be 64 lowercase hexadecimal"
        )
    return value


def _artifact_map(items: object, *, field: str) -> dict[str, tuple[int, str]]:
    if not isinstance(items, list):
        raise ShadowReceiptSelfIntegrityError(f"{field} must be one list")

    observed: dict[str, tuple[int, str]] = {}
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ShadowReceiptSelfIntegrityError(
                f"{field}[{index}] must be one mapping"
            )
        path = item.get("path")
        if not isinstance(path, str) or not path:
            raise ShadowReceiptSelfIntegrityError(
                f"{field}[{index}].path must be one non-empty string"
            )
        if path in observed:
            raise ShadowReceiptSelfIntegrityError(
                f"{field} path identity must be unique: {path}"
            )
        byte_count = _nonnegative_int(
            item.get("byteCount"),
            field=f"{field}[{index}].byteCount",
        )
        sha256 = item.get("sha256")
        if not isinstance(sha256, str) or SHA256_RE.fullmatch(sha256) is None:
            raise ShadowReceiptSelfIntegrityError(
                f"{field}[{index}].sha256 must be 64 lowercase hexadecimal"
            )
        observed[path] = (byte_count, sha256)
    return observed


def _require_portable_authority_backend(result: Mapping[str, object]) -> None:
    if result.get("canonicalAuthorityBackend") != PORTABLE_AUTHORITY_BACKEND:
        raise ShadowReceiptSelfIntegrityError(
            "descriptor shadow receipt requires canonical portable authority backend context"
        )


def _require_completed_context(result: Mapping[str, object]) -> None:
    _require_portable_authority_backend(result)
    if result.get("canonicalAuthoritySchema") != CANONICAL_SCHEMA:
        raise ShadowReceiptSelfIntegrityError(
            "completed comparison requires exact canonical custody v10 context"
        )
    if result.get("canonicalEvidenceComplete") is not True:
        raise ShadowReceiptSelfIntegrityError(
            "completed comparison requires canonical evidenceComplete=true"
        )
    if result.get("descriptorCapabilityStatus") != SUPPORTED:
        raise ShadowReceiptSelfIntegrityError(
            "completed comparison requires exact supported descriptor capability context"
        )


def _require_wound_context(result: Mapping[str, object], status: str) -> None:
    """Require wound labels to agree with the context that can actually produce them.

    Comparison booleans already fail closed in the display projector. This gate protects an earlier
    semantic boundary: a wound/unavailable status must not be paired with a healthy or unrelated
    canonical/capability context and then accepted merely because no comparison completed.
    """

    _require_portable_authority_backend(result)
    canonical_schema = result.get("canonicalAuthoritySchema")
    canonical_complete = result.get("canonicalEvidenceComplete")
    capability = result.get("descriptorCapabilityStatus")

    if status == "CANONICAL_SCHEMA_WOUND":
        if not isinstance(canonical_schema, str) or not canonical_schema:
            raise ShadowReceiptSelfIntegrityError(
                "CANONICAL_SCHEMA_WOUND requires one explicit non-empty canonical schema identity"
            )
        if canonical_schema == CANONICAL_SCHEMA:
            raise ShadowReceiptSelfIntegrityError(
                "CANONICAL_SCHEMA_WOUND requires a non-v10 canonical schema"
            )
        if canonical_complete is not None or capability is not None:
            raise ShadowReceiptSelfIntegrityError(
                "CANONICAL_SCHEMA_WOUND must stop before canonical completeness/capability admission"
            )
        return

    if canonical_schema != CANONICAL_SCHEMA:
        raise ShadowReceiptSelfIntegrityError(
            f"{status} requires exact canonical custody v10 context"
        )

    if status == "CANONICAL_WOUND":
        if canonical_complete is not False:
            raise ShadowReceiptSelfIntegrityError(
                "CANONICAL_WOUND requires canonical evidenceComplete=false"
            )
        if capability is not None:
            raise ShadowReceiptSelfIntegrityError(
                "CANONICAL_WOUND must stop before descriptor capability admission"
            )
        return

    if canonical_complete is not True:
        raise ShadowReceiptSelfIntegrityError(
            f"{status} requires canonical evidenceComplete=true"
        )

    if status == "DESCRIPTOR_UNAVAILABLE":
        if capability != PORTABLE_UNAVAILABLE:
            raise ShadowReceiptSelfIntegrityError(
                "DESCRIPTOR_UNAVAILABLE requires exact portable-unavailable descriptor capability"
            )
        return

    if status == "CAPABILITY_WOUND":
        if (
            not isinstance(capability, str)
            or not capability
            or capability in {SUPPORTED, PORTABLE_UNAVAILABLE}
        ):
            raise ShadowReceiptSelfIntegrityError(
                "CAPABILITY_WOUND requires one non-admitted descriptor capability state"
            )
        return

    if status in {"PORTABLE_SHADOW_WOUND", "DESCRIPTOR_WOUND"}:
        if capability != SUPPORTED:
            raise ShadowReceiptSelfIntegrityError(
                f"{status} requires exact supported descriptor capability context"
            )
        return

    raise ShadowReceiptSelfIntegrityError(
        f"wound status is not one admitted self-integrity state: {status!r}"
    )


def _validate_wound_evidence_phase(result: Mapping[str, object], status: str) -> None:
    """Require pre-comparison evidence to match the pipeline phase where the wound occurred.

    ``None`` comparison booleans prove only that a comparison did not complete; they do not prove
    that artifact/counter evidence came from a stage that was actually reached. Early wounds must
    not carry later artifact observations. ``DESCRIPTOR_WOUND`` is intentionally different: portable
    staging completed before descriptor custody failed, so already-observed portable artifacts are
    preserved as diagnostic contact while descriptor evidence/counters remain unavailable.
    """

    portable = result.get("portableShadowArtifacts")
    descriptor = result.get("descriptorArtifacts")
    if not isinstance(portable, list) or not isinstance(descriptor, list):
        raise ShadowReceiptSelfIntegrityError(
            "wound artifact evidence must remain list-shaped"
        )

    descriptor_entries = result.get("descriptorArtifactDirectoryEntriesObserved")
    descriptor_candidates = result.get("descriptorArtifactCandidatesObserved")
    if descriptor_entries is not None or descriptor_candidates is not None:
        raise ShadowReceiptSelfIntegrityError(
            f"{status} must not carry completed descriptor work counters"
        )

    no_artifact_phase = {
        "CANONICAL_SCHEMA_WOUND",
        "CANONICAL_WOUND",
        "DESCRIPTOR_UNAVAILABLE",
        "CAPABILITY_WOUND",
        "PORTABLE_SHADOW_WOUND",
    }
    if status in no_artifact_phase:
        if portable:
            raise ShadowReceiptSelfIntegrityError(
                f"{status} must not carry portable artifact evidence from a later phase"
            )
        if descriptor:
            raise ShadowReceiptSelfIntegrityError(
                f"{status} must not carry descriptor artifact evidence from a later phase"
            )
        return

    if status == "DESCRIPTOR_WOUND":
        if descriptor:
            raise ShadowReceiptSelfIntegrityError(
                "DESCRIPTOR_WOUND must not carry descriptor artifact evidence from an incomplete descriptor stage"
            )
        portable_map = _artifact_map(portable, field="portableShadowArtifacts")
        canonical_candidates = _nonnegative_int(
            result.get("canonicalArtifactCandidatesObserved"),
            field="canonicalArtifactCandidatesObserved",
        )
        if len(portable_map) != canonical_candidates:
            raise ShadowReceiptSelfIntegrityError(
                "DESCRIPTOR_WOUND portable artifact evidence cardinality must equal canonical candidate count"
            )
        return

    raise ShadowReceiptSelfIntegrityError(
        f"wound evidence phase is not defined for status: {status!r}"
    )


def _recompute_completed_comparisons(
    result: Mapping[str, object],
) -> tuple[bool, bool, bool]:
    portable = _artifact_map(
        result.get("portableShadowArtifacts"),
        field="portableShadowArtifacts",
    )
    descriptor = _artifact_map(
        result.get("descriptorArtifacts"),
        field="descriptorArtifacts",
    )

    artifact_set_match = set(portable) == set(descriptor)
    content_identity_match = portable == descriptor

    canonical_entries = _nonnegative_int(
        result.get("canonicalArtifactDirectoryEntriesObserved"),
        field="canonicalArtifactDirectoryEntriesObserved",
    )
    canonical_candidates = _nonnegative_int(
        result.get("canonicalArtifactCandidatesObserved"),
        field="canonicalArtifactCandidatesObserved",
    )
    descriptor_entries = _nonnegative_int(
        result.get("descriptorArtifactDirectoryEntriesObserved"),
        field="descriptorArtifactDirectoryEntriesObserved",
    )
    descriptor_candidates = _nonnegative_int(
        result.get("descriptorArtifactCandidatesObserved"),
        field="descriptorArtifactCandidatesObserved",
    )

    if canonical_candidates > canonical_entries:
        raise ShadowReceiptSelfIntegrityError(
            "canonical artifact candidate count cannot exceed directory-entry count"
        )
    if descriptor_candidates > descriptor_entries:
        raise ShadowReceiptSelfIntegrityError(
            "descriptor artifact candidate count cannot exceed directory-entry count"
        )
    if len(portable) != canonical_candidates:
        raise ShadowReceiptSelfIntegrityError(
            "portable artifact evidence cardinality must equal canonical candidate count"
        )
    if len(descriptor) != descriptor_candidates:
        raise ShadowReceiptSelfIntegrityError(
            "descriptor artifact evidence cardinality must equal descriptor candidate count"
        )

    metrics_match = (
        canonical_entries == descriptor_entries
        and canonical_candidates == descriptor_candidates
    )

    claimed = (
        result.get("artifactSetMatch"),
        result.get("metricsMatch"),
        result.get("contentIdentityMatch"),
    )
    recomputed = (artifact_set_match, metrics_match, content_identity_match)
    if claimed != recomputed:
        raise ShadowReceiptSelfIntegrityError(
            f"shadow comparison booleans contradict artifact/metric evidence: "
            f"claimed={claimed!r} recomputed={recomputed!r}"
        )
    return recomputed


def _temporal_receipt_projection(
    result: Mapping[str, object],
) -> dict[str, object]:
    temporal = result.get("temporalContentBinding")
    if not isinstance(temporal, Mapping):
        raise ShadowReceiptSelfIntegrityError(
            "completed comparison requires temporalContentBinding receipt context"
        )
    if temporal.get("schema") != TEMPORAL_BINDING_SCHEMA:
        raise ShadowReceiptSelfIntegrityError(
            "temporalContentBinding must use the exact temporal binding schema"
        )
    if temporal.get("receiptIntegritySchema") != TEMPORAL_RECEIPT_INTEGRITY_SCHEMA:
        raise ShadowReceiptSelfIntegrityError(
            "temporalContentBinding must carry the exact receipt-integrity schema"
        )
    if temporal.get("shadowReceiptContextAdmitted") is not True:
        raise ShadowReceiptSelfIntegrityError(
            "temporalContentBinding must carry shadowReceiptContextAdmitted=true"
        )
    canonical_sha = _canonical_sha256(
        result.get("canonicalResultSha256"),
        field="canonicalResultSha256",
    )
    if temporal.get("canonicalResultSha256") != canonical_sha:
        raise ShadowReceiptSelfIntegrityError(
            "temporalContentBinding canonicalResultSha256 must match the shadow result"
        )
    if temporal.get("shadowCanonicalResultSha256") != canonical_sha:
        raise ShadowReceiptSelfIntegrityError(
            "temporalContentBinding shadowCanonicalResultSha256 must match the shadow result"
        )

    denied_boolean_fields = (
        "authorityAdmitted",
        "ownerMutation",
        "regressionExecuted",
        "tested",
        "runtimeUi",
        "runtimeTalkBack",
        "phoneDelivered",
    )
    for field in denied_boolean_fields:
        if temporal.get(field) is not False:
            raise ShadowReceiptSelfIntegrityError(
                f"temporalContentBinding must carry {field}=false"
            )

    status = admit_temporal_status(temporal.get("status"))
    proven = temporal.get("temporalBindingProven")
    if not isinstance(proven, bool):
        raise ShadowReceiptSelfIntegrityError(
            "temporalContentBinding temporalBindingProven must be one boolean"
        )
    if proven != (status == "TEMPORAL_CONTENT_BOUND"):
        raise ShadowReceiptSelfIntegrityError(
            "temporal binding proof boolean must agree with TEMPORAL_CONTENT_BOUND status"
        )
    if result.get("temporalBindingProven") is not proven:
        raise ShadowReceiptSelfIntegrityError(
            "top-level temporalBindingProven must equal nested temporal proof"
        )

    return {
        "temporalStatus": status,
        "temporalBindingProven": proven,
        "temporalReceiptContextAdmitted": True,
    }


def project_shadow_receipt_with_self_integrity(
    repo_root: Path,
    result: dict[str, object],
) -> dict[str, object]:
    """Self-audit one detached exact-JSON observation, then delegate to the existing projector."""

    try:
        result = snapshot_json_mapping(
            result,
            field="descriptor shadow self-integrity input",
        )
    except OperatorReceiptSnapshotCustodyError as exc:
        raise ShadowReceiptSelfIntegrityError(
            f"descriptor shadow self-integrity snapshot rejected: {exc}"
        ) from exc

    if result.get("schema") != SHADOW_SCHEMA:
        raise ShadowReceiptSelfIntegrityError(
            "self-integrity requires exact descriptor-shadow v3 source"
        )

    # Raw capability contradictions must fail closed before the bounded projector can replace them
    # with conservative false output fields. Projection is not capability repair.
    require_raw_shadow_capability_membrane(result)

    status = result.get("status")
    if not isinstance(status, str) or not status:
        raise ShadowReceiptSelfIntegrityError("shadow status must be one non-empty string")
    completed = status in COMPLETED_STATUSES
    temporal_projection: dict[str, object] = {
        "temporalStatus": None,
        "temporalBindingProven": False,
        "temporalReceiptContextAdmitted": False,
    }
    comparison_recomputed = False

    if completed:
        _require_completed_context(result)
        _recompute_completed_comparisons(result)
        temporal_projection = _temporal_receipt_projection(result)
        comparison_recomputed = True
    else:
        _require_wound_context(result, status)
        _validate_wound_evidence_phase(result, status)
        if "temporalContentBinding" in result or "temporalBindingProven" in result:
            raise ShadowReceiptSelfIntegrityError(
                "non-comparison wound/unavailable receipt must not carry temporal binding evidence"
            )

    receipt = project_shadow_receipt(repo_root, result)
    return {
        **receipt,
        "receiptSelfIntegritySchema": SCHEMA,
        "comparisonEvidenceRecomputed": comparison_recomputed,
        "woundContextValidated": not completed,
        **temporal_projection,
    }
