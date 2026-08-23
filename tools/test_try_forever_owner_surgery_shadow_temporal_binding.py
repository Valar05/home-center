#!/usr/bin/env python3
"""Regression source for descriptor-shadow temporal canonical-content binding.

SOURCE ONLY. No authorized execution receipt exists for this file.
"""

from try_forever_owner_surgery_descriptor_shadow_audit import _canonical_result_sha256
from try_forever_owner_surgery_shadow_temporal_binding import (
    TemporalBindingEvidenceError,
    evaluate_temporal_content_binding,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
PATH = "patches/try-forever-a.patch"
SHA = "a" * 64


def canonical(*, witnesses=None, evidence_complete=True, include_surgery=True):
    surgeries = []
    if include_surgery:
        surgeries.append({
            "path": PATH,
            "artifact_kind": "patch",
            "owner": OWNER,
            "base_blob": "1" * 40,
            "state": "CORRECTED_PROPOSED_NOT_APPLIED",
            "promotion_candidate": True,
            "artifact_byte_count": 10,
            "artifact_sha256": SHA,
        })
    result = {
        "schema": "try-forever-owner-surgery-custody.v10",
        "artifactDirectoryEntriesObserved": 1 if include_surgery else 0,
        "artifactCandidatesObserved": 1 if include_surgery else 0,
        "surgeries": surgeries,
        "discoveryErrors": [] if evidence_complete else [{"path": PATH, "boundary": "wound"}],
        "evidenceComplete": evidence_complete,
        "currentOwnerBlobs": {OWNER: "1" * 40},
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
    }
    if witnesses is not None:
        result["artifactContentWitnesses"] = witnesses
    return result


def shadow(
    result,
    *,
    portable_sha=SHA,
    descriptor_sha=SHA,
    status="SHADOW_MATCH",
    comparisons=(True, True, True),
    include_artifact=True,
):
    portable = []
    descriptor = []
    if include_artifact:
        portable.append({"path": PATH, "byteCount": 10, "sha256": portable_sha})
        descriptor.append({"path": PATH, "byteCount": 10, "sha256": descriptor_sha})
    return {
        "schema": "try-forever-owner-surgery-descriptor-shadow.v3",
        "status": status,
        "canonicalResultSha256": _canonical_result_sha256(result),
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "artifactSetMatch": comparisons[0],
        "metricsMatch": comparisons[1],
        "contentIdentityMatch": comparisons[2],
        "portableShadowArtifacts": portable,
        "descriptorArtifacts": descriptor,
    }


def main() -> int:
    # Missing witness remains a distinct fail-closed state even though canonical v10 source now
    # emits witnesses on its normal owner path. This fixture protects malformed/legacy input review.
    legacy_missing = canonical()
    missing = evaluate_temporal_content_binding(legacy_missing, shadow(legacy_missing))
    assert missing["status"] == "CANONICAL_CONTENT_WITNESS_MISSING"
    assert missing["temporalBindingProven"] is False
    assert missing["authorityAdmitted"] is False
    assert missing["tested"] is False

    # An empty canonical inventory must not earn a vacuous temporal proof just because all three
    # identity maps are empty and therefore equal.
    empty = canonical(witnesses=[], include_surgery=False)
    empty_result = evaluate_temporal_content_binding(
        empty,
        shadow(empty, include_artifact=False),
    )
    assert empty_result["status"] == "NO_CANONICAL_ARTIFACT_CONTENT"
    assert empty_result["temporalBindingProven"] is False
    assert empty_result["authorityAdmitted"] is False

    # Receipt identity must bind to the exact canonical payload under review.
    mismatched_shadow = shadow(legacy_missing)
    mismatched_shadow["canonicalResultSha256"] = "b" * 64
    mismatch = evaluate_temporal_content_binding(legacy_missing, mismatched_shadow)
    assert mismatch["status"] == "CANONICAL_RESULT_ID_MISMATCH"
    assert mismatch["temporalBindingProven"] is False

    # Canonical incompleteness is a distinct wound before content-witness admission.
    wounded = canonical(evidence_complete=False)
    canonical_wound = evaluate_temporal_content_binding(wounded, shadow(wounded))
    assert canonical_wound["status"] == "CANONICAL_WOUND"
    assert canonical_wound["temporalBindingProven"] is False

    witness = [{"path": PATH, "byteCount": 10, "sha256": SHA}]
    future = canonical(witnesses=witness)

    # A temporal proof may only consume an admitted positive shadow comparison.
    not_matched = evaluate_temporal_content_binding(
        future,
        shadow(future, status="SHADOW_DIVERGED", comparisons=(True, True, False)),
    )
    assert not_matched["status"] == "SHADOW_COMPARISON_NOT_ADMITTED"
    assert not_matched["temporalBindingProven"] is False

    bound = evaluate_temporal_content_binding(future, shadow(future))
    assert bound["status"] == "TEMPORAL_CONTENT_BOUND"
    assert bound["temporalBindingProven"] is True
    assert bound["authorityAdmitted"] is False
    assert bound["canonicalWitnessCount"] == 1

    # Later descriptor or portable drift breaks the temporal chain independently even if a caller
    # tries to present comparison booleans as green.
    diverged = evaluate_temporal_content_binding(
        future,
        shadow(future, descriptor_sha="c" * 64),
    )
    assert diverged["status"] == "TEMPORAL_CONTENT_DIVERGED"
    assert diverged["temporalBindingProven"] is False

    # Canonical witness identity is a set keyed by exact path; duplicate paths are evidence wounds.
    duplicate = canonical(witnesses=witness + witness)
    try:
        evaluate_temporal_content_binding(duplicate, shadow(duplicate))
    except TemporalBindingEvidenceError as exc:
        assert "path identity must be unique" in str(exc)
    else:
        raise AssertionError("duplicate canonical witness path earned temporal binding")

    # Witnesses must cover exactly the canonical surgery set; a phantom witness cannot join the chain.
    phantom = canonical(witnesses=witness + [{"path": "patches/phantom.patch", "byteCount": 1, "sha256": "d" * 64}])
    try:
        evaluate_temporal_content_binding(phantom, shadow(phantom))
    except TemporalBindingEvidenceError as exc:
        assert "path set must equal canonical surgeries path set" in str(exc)
    else:
        raise AssertionError("phantom canonical witness earned temporal binding")

    # Boolean byte counts and non-canonical digests may not be normalized into evidence.
    malformed = canonical(witnesses=[{"path": PATH, "byteCount": True, "sha256": SHA}])
    try:
        evaluate_temporal_content_binding(malformed, shadow(malformed))
    except TemporalBindingEvidenceError as exc:
        assert "byteCount" in str(exc)
    else:
        raise AssertionError("malformed canonical witness earned temporal binding")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
