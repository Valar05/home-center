#!/usr/bin/env python3
"""Hostile regression source for descriptor-shadow operator receipt self-integrity.

SOURCE ONLY. This fixture has not been observed executing in an authorized regression lane.
"""

from pathlib import Path

from try_forever_owner_surgery_backend_policy import PORTABLE_UNAVAILABLE
from try_forever_owner_surgery_descriptor_shadow_audit import (
    CANONICAL_SCHEMA,
    SCHEMA as SHADOW_SCHEMA,
    SUPPORTED,
)
from try_forever_owner_surgery_shadow_receipt_self_integrity import (
    TEMPORAL_BINDING_SCHEMA,
    TEMPORAL_RECEIPT_INTEGRITY_SCHEMA,
    project_shadow_receipt_with_self_integrity,
)


ROOT = Path("/repo")
CANONICAL_SHA = "1" * 64
ARTIFACT_SHA = "a" * 64


def artifact(path: str = "patches/a.patch", *, byte_count: int = 10, sha256: str = ARTIFACT_SHA):
    return {"path": path, "byteCount": byte_count, "sha256": sha256}


def temporal(*, status: str = "TEMPORAL_CONTENT_BOUND", proven: bool = True):
    return {
        "schema": TEMPORAL_BINDING_SCHEMA,
        "status": status,
        "canonicalResultSha256": CANONICAL_SHA,
        "shadowCanonicalResultSha256": CANONICAL_SHA,
        "temporalBindingProven": proven,
        "authorityAdmitted": False,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeUi": False,
        "runtimeTalkBack": False,
        "phoneDelivered": False,
        "boundary": "bounded semantic result only",
        "receiptIntegritySchema": TEMPORAL_RECEIPT_INTEGRITY_SCHEMA,
        "shadowReceiptContextAdmitted": True,
    }


def raw_match(**overrides):
    result = {
        "schema": SHADOW_SCHEMA,
        "status": "SHADOW_MATCH",
        "canonicalAuthorityBackend": "PORTABLE_PATHNAME_REVALIDATION",
        "canonicalAuthoritySchema": CANONICAL_SCHEMA,
        "canonicalResultSha256": CANONICAL_SHA,
        "canonicalEvidenceComplete": True,
        "canonicalArtifactDirectoryEntriesObserved": 2,
        "canonicalArtifactCandidatesObserved": 1,
        "descriptorCapabilityStatus": SUPPORTED,
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "boundary": "exact comparison completed",
        "portableShadowArtifacts": [artifact()],
        "descriptorArtifacts": [artifact()],
        "descriptorArtifactDirectoryEntriesObserved": 2,
        "descriptorArtifactCandidatesObserved": 1,
        "artifactSetMatch": True,
        "metricsMatch": True,
        "contentIdentityMatch": True,
        "temporalContentBinding": temporal(),
        "temporalBindingProven": True,
    }
    result.update(overrides)
    return result


def raw_wound(status: str, **overrides):
    result = raw_match(
        status=status,
        descriptorArtifacts=[],
        descriptorArtifactDirectoryEntriesObserved=None,
        descriptorArtifactCandidatesObserved=None,
        artifactSetMatch=None,
        metricsMatch=None,
        contentIdentityMatch=None,
    )
    result.pop("temporalContentBinding")
    result.pop("temporalBindingProven")
    result.update(overrides)
    return result


def expect_rejected(result, needle: str) -> None:
    try:
        project_shadow_receipt_with_self_integrity(ROOT, result)
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"contradictory shadow receipt escaped self-integrity: {result!r}")


def main() -> int:
    receipt = project_shadow_receipt_with_self_integrity(ROOT, raw_match())
    assert receipt["status"] == "SHADOW_MATCH"
    assert receipt["comparisonEvidenceRecomputed"] is True
    assert receipt["woundContextValidated"] is False
    assert receipt["temporalStatus"] == "TEMPORAL_CONTENT_BOUND"
    assert receipt["temporalBindingProven"] is True
    assert receipt["temporalReceiptContextAdmitted"] is True
    assert receipt["authorityAdmitted"] is False
    assert receipt["tested"] is False

    # A claimed path-set match cannot override contradictory artifact paths.
    expect_rejected(
        raw_match(descriptorArtifacts=[artifact("patches/b.patch")]),
        "comparison booleans contradict",
    )

    # A claimed content match cannot override exact SHA drift.
    expect_rejected(
        raw_match(descriptorArtifacts=[artifact(sha256="b" * 64)]),
        "comparison booleans contradict",
    )

    # A claimed metrics match cannot override observed work-counter drift.
    expect_rejected(
        raw_match(descriptorArtifactDirectoryEntriesObserved=3),
        "comparison booleans contradict",
    )

    # Equal counters are not self-validating if either candidate count exceeds its directory work.
    expect_rejected(
        raw_match(
            canonicalArtifactDirectoryEntriesObserved=1,
            canonicalArtifactCandidatesObserved=2,
        ),
        "canonical artifact candidate count cannot exceed directory-entry count",
    )
    expect_rejected(
        raw_match(
            descriptorArtifactDirectoryEntriesObserved=1,
            descriptorArtifactCandidatesObserved=2,
        ),
        "descriptor artifact candidate count cannot exceed directory-entry count",
    )

    # Completed comparison artifact evidence must account for every observed candidate on its side.
    expect_rejected(
        raw_match(
            canonicalArtifactDirectoryEntriesObserved=2,
            canonicalArtifactCandidatesObserved=2,
        ),
        "portable artifact evidence cardinality must equal canonical candidate count",
    )
    expect_rejected(
        raw_match(
            descriptorArtifactDirectoryEntriesObserved=2,
            descriptorArtifactCandidatesObserved=2,
        ),
        "descriptor artifact evidence cardinality must equal descriptor candidate count",
    )

    # Completed comparisons require the exact canonical/backend/capability context.
    expect_rejected(
        raw_match(canonicalAuthorityBackend="HELD_DIRECTORY_DESCRIPTOR"),
        "canonical portable authority backend",
    )
    expect_rejected(
        raw_match(canonicalEvidenceComplete=False),
        "evidenceComplete=true",
    )
    expect_rejected(
        raw_match(descriptorCapabilityStatus="UNKNOWN"),
        "supported descriptor capability",
    )

    # Temporal receipt proof is independently bound to exact receipt-integrity context.
    bad_temporal = temporal()
    bad_temporal["receiptIntegritySchema"] = "wrong"
    expect_rejected(
        raw_match(temporalContentBinding=bad_temporal),
        "exact receipt-integrity schema",
    )

    wrong_carried_result = temporal()
    wrong_carried_result["shadowCanonicalResultSha256"] = "2" * 64
    expect_rejected(
        raw_match(temporalContentBinding=wrong_carried_result),
        "shadowCanonicalResultSha256 must match",
    )

    promoted_runtime = temporal()
    promoted_runtime["runtimeTalkBack"] = True
    expect_rejected(
        raw_match(temporalContentBinding=promoted_runtime),
        "runtimeTalkBack=false",
    )

    promoted_regression = temporal()
    promoted_regression["regressionExecuted"] = True
    expect_rejected(
        raw_match(temporalContentBinding=promoted_regression),
        "regressionExecuted=false",
    )

    mismatched_proof = temporal(status="TEMPORAL_CONTENT_DIVERGED", proven=True)
    expect_rejected(
        raw_match(temporalContentBinding=mismatched_proof),
        "proof boolean must agree",
    )

    # Completed divergence is still a completed comparison, but temporal proof stays false.
    diverged_temporal = temporal(status="SHADOW_COMPARISON_NOT_ADMITTED", proven=False)
    diverged = raw_match(
        status="SHADOW_DIVERGED",
        descriptorArtifacts=[artifact(sha256="b" * 64)],
        contentIdentityMatch=False,
        temporalContentBinding=diverged_temporal,
        temporalBindingProven=False,
    )
    diverged_receipt = project_shadow_receipt_with_self_integrity(ROOT, diverged)
    assert diverged_receipt["status"] == "SHADOW_DIVERGED"
    assert diverged_receipt["woundContextValidated"] is False
    assert diverged_receipt["temporalBindingProven"] is False
    assert diverged_receipt["temporalStatus"] == "SHADOW_COMPARISON_NOT_ADMITTED"

    # Wound/unavailable states may carry null comparison truth but no stale temporal proof.
    # DESCRIPTOR_WOUND legitimately retains already-observed portable evidence, so completed-only
    # cardinality checks must not erase that diagnostic contact.
    wounded = raw_wound(
        "DESCRIPTOR_WOUND",
        canonicalArtifactDirectoryEntriesObserved=2,
        canonicalArtifactCandidatesObserved=1,
        descriptorCapabilityStatus=SUPPORTED,
        portableShadowArtifacts=[artifact()],
    )
    wounded_receipt = project_shadow_receipt_with_self_integrity(ROOT, wounded)
    assert wounded_receipt["status"] == "DESCRIPTOR_WOUND"
    assert wounded_receipt["comparisonEvidenceRecomputed"] is False
    assert wounded_receipt["woundContextValidated"] is True
    assert wounded_receipt["temporalReceiptContextAdmitted"] is False

    # Null comparison fields are not enough: pre-comparison evidence must match the phase where the
    # wound occurred. Early wounds cannot smuggle later artifacts/counters into operator display.
    expect_rejected(
        raw_wound(
            "CANONICAL_WOUND",
            canonicalEvidenceComplete=False,
            descriptorCapabilityStatus=None,
            portableShadowArtifacts=[artifact()],
        ),
        "must not carry portable artifact evidence from a later phase",
    )
    expect_rejected(
        raw_wound(
            "DESCRIPTOR_UNAVAILABLE",
            descriptorCapabilityStatus=PORTABLE_UNAVAILABLE,
            portableShadowArtifacts=[],
            descriptorArtifacts=[artifact()],
        ),
        "must not carry descriptor artifact evidence from a later phase",
    )
    expect_rejected(
        raw_wound(
            "PORTABLE_SHADOW_WOUND",
            descriptorCapabilityStatus=SUPPORTED,
            portableShadowArtifacts=[artifact()],
        ),
        "must not carry portable artifact evidence from a later phase",
    )
    expect_rejected(
        raw_wound(
            "DESCRIPTOR_WOUND",
            descriptorCapabilityStatus=SUPPORTED,
            portableShadowArtifacts=[artifact()],
            descriptorArtifactDirectoryEntriesObserved=1,
        ),
        "must not carry completed descriptor work counters",
    )
    expect_rejected(
        raw_wound(
            "DESCRIPTOR_WOUND",
            descriptorCapabilityStatus=SUPPORTED,
            portableShadowArtifacts=[artifact()],
            descriptorArtifacts=[artifact()],
        ),
        "must not carry descriptor artifact evidence from an incomplete descriptor stage",
    )
    expect_rejected(
        raw_wound(
            "DESCRIPTOR_WOUND",
            canonicalArtifactCandidatesObserved=2,
            descriptorCapabilityStatus=SUPPORTED,
            portableShadowArtifacts=[artifact()],
        ),
        "portable artifact evidence cardinality must equal canonical candidate count",
    )

    stale_temporal_wound = dict(wounded)
    stale_temporal_wound["temporalContentBinding"] = diverged_temporal
    expect_rejected(stale_temporal_wound, "must not carry temporal binding evidence")

    # Wound labels themselves are authority claims about where the pipeline stopped. Their context
    # must agree; null comparison fields alone are not sufficient self-integrity.
    expect_rejected(
        raw_wound("DESCRIPTOR_UNAVAILABLE", descriptorCapabilityStatus=SUPPORTED),
        "portable-unavailable descriptor capability",
    )
    unavailable = raw_wound(
        "DESCRIPTOR_UNAVAILABLE",
        descriptorCapabilityStatus=PORTABLE_UNAVAILABLE,
        portableShadowArtifacts=[],
    )
    assert project_shadow_receipt_with_self_integrity(ROOT, unavailable)["woundContextValidated"] is True

    expect_rejected(
        raw_wound("CANONICAL_WOUND", canonicalEvidenceComplete=True, descriptorCapabilityStatus=None),
        "evidenceComplete=false",
    )
    canonical_wound = raw_wound(
        "CANONICAL_WOUND",
        canonicalEvidenceComplete=False,
        descriptorCapabilityStatus=None,
        portableShadowArtifacts=[],
    )
    assert project_shadow_receipt_with_self_integrity(ROOT, canonical_wound)["woundContextValidated"] is True

    expect_rejected(
        raw_wound("PORTABLE_SHADOW_WOUND", descriptorCapabilityStatus=PORTABLE_UNAVAILABLE),
        "supported descriptor capability",
    )
    portable_wound = raw_wound(
        "PORTABLE_SHADOW_WOUND",
        descriptorCapabilityStatus=SUPPORTED,
        portableShadowArtifacts=[],
    )
    assert project_shadow_receipt_with_self_integrity(ROOT, portable_wound)["woundContextValidated"] is True

    expect_rejected(
        raw_wound("CAPABILITY_WOUND", descriptorCapabilityStatus=SUPPORTED),
        "non-admitted descriptor capability state",
    )
    capability_wound = raw_wound(
        "CAPABILITY_WOUND",
        descriptorCapabilityStatus="UNKNOWN_PLATFORM_STATE",
        portableShadowArtifacts=[],
    )
    assert project_shadow_receipt_with_self_integrity(ROOT, capability_wound)["woundContextValidated"] is True

    schema_wound = raw_wound(
        "CANONICAL_SCHEMA_WOUND",
        canonicalAuthoritySchema="try-forever-owner-surgery-custody.v9",
        canonicalEvidenceComplete=None,
        descriptorCapabilityStatus=None,
        portableShadowArtifacts=[],
    )
    assert project_shadow_receipt_with_self_integrity(ROOT, schema_wound)["woundContextValidated"] is True
    expect_rejected(
        raw_wound(
            "CANONICAL_SCHEMA_WOUND",
            canonicalAuthoritySchema=CANONICAL_SCHEMA,
            canonicalEvidenceComplete=None,
            descriptorCapabilityStatus=None,
            portableShadowArtifacts=[],
        ),
        "requires a non-v10 canonical schema",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
