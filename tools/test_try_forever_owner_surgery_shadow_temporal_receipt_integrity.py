#!/usr/bin/env python3
"""Regression source for descriptor-shadow temporal receipt integrity.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

from copy import deepcopy

from try_forever_owner_surgery_descriptor_shadow_audit import (
    _canonical_result_sha256,
)
from try_forever_owner_surgery_shadow_temporal_receipt_integrity import (
    ShadowTemporalReceiptIntegrityError,
    evaluate_temporal_content_binding_with_receipt_integrity,
)


PATH = "patches/try-forever-a.patch"
OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "1" * 40
SHA = "a" * 64


def canonical() -> dict[str, object]:
    return {
        "schema": "try-forever-owner-surgery-custody.v10",
        "evidenceComplete": True,
        "surgeries": [
            {
                "path": PATH,
                "artifact_kind": "patch",
                "owner": OWNER,
                "base_blob": BASE,
                "state": "CORRECTED_PROPOSED_NOT_APPLIED",
                "promotion_candidate": True,
                "artifact_byte_count": 10,
                "artifact_sha256": SHA,
            }
        ],
        "artifactContentWitnesses": [
            {"path": PATH, "byteCount": 10, "sha256": SHA}
        ],
        "discoveryErrors": [],
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
    }


def shadow(canonical_result: dict[str, object]) -> dict[str, object]:
    artifact = {"path": PATH, "byteCount": 10, "sha256": SHA}
    return {
        "schema": "try-forever-owner-surgery-descriptor-shadow.v3",
        "status": "SHADOW_MATCH",
        "canonicalAuthorityBackend": "PORTABLE_PATHNAME_REVALIDATION",
        "canonicalAuthoritySchema": "try-forever-owner-surgery-custody.v10",
        "canonicalResultSha256": _canonical_result_sha256(canonical_result),
        "canonicalEvidenceComplete": True,
        "descriptorCapabilityStatus": "SUPPORTED_POSIX_PRIMITIVES",
        "descriptorAuthorityAdmitted": False,
        "ownerMutation": False,
        "artifactSetMatch": True,
        "metricsMatch": True,
        "contentIdentityMatch": True,
        "portableShadowArtifacts": [artifact],
        "descriptorArtifacts": [artifact],
    }


def expect_rejected(canonical_result, shadow_result, needle: str) -> None:
    try:
        evaluate_temporal_content_binding_with_receipt_integrity(
            canonical_result,
            shadow_result,
        )
    except ShadowTemporalReceiptIntegrityError as exc:
        assert needle in str(exc), str(exc)
    else:
        raise AssertionError("counterfeit shadow receipt context was admitted")


def main() -> int:
    canonical_result = canonical()
    valid_shadow = shadow(canonical_result)
    bound = evaluate_temporal_content_binding_with_receipt_integrity(
        canonical_result,
        valid_shadow,
    )
    assert bound["status"] == "TEMPORAL_CONTENT_BOUND"
    assert bound["temporalBindingProven"] is True
    assert bound["authorityAdmitted"] is False
    assert bound["shadowReceiptContextAdmitted"] is True

    wrong_schema = deepcopy(valid_shadow)
    wrong_schema["canonicalAuthoritySchema"] = "try-forever-owner-surgery-custody.v9"
    expect_rejected(canonical_result, wrong_schema, "canonicalAuthoritySchema")

    wrong_complete = deepcopy(valid_shadow)
    wrong_complete["canonicalEvidenceComplete"] = False
    expect_rejected(canonical_result, wrong_complete, "canonicalEvidenceComplete")

    wrong_backend = deepcopy(valid_shadow)
    wrong_backend["canonicalAuthorityBackend"] = "DESCRIPTOR_DIRECTORY_HANDLE"
    expect_rejected(canonical_result, wrong_backend, "canonicalAuthorityBackend")

    wrong_capability = deepcopy(valid_shadow)
    wrong_capability["descriptorCapabilityStatus"] = "SUPPORTED"
    expect_rejected(canonical_result, wrong_capability, "supported descriptor capability")

    incomplete = canonical()
    incomplete["evidenceComplete"] = False
    incomplete_shadow = shadow(incomplete)
    incomplete_shadow["canonicalEvidenceComplete"] = False
    expect_rejected(incomplete, incomplete_shadow, "cannot accompany incomplete canonical custody")

    diverged = shadow(canonical_result)
    diverged["status"] = "SHADOW_DIVERGED"
    diverged["contentIdentityMatch"] = False
    result = evaluate_temporal_content_binding_with_receipt_integrity(
        canonical_result,
        diverged,
    )
    assert result["status"] == "SHADOW_COMPARISON_NOT_ADMITTED"
    assert result["temporalBindingProven"] is False
    assert result["shadowReceiptContextAdmitted"] is True

    counterfeit_divergence = deepcopy(diverged)
    counterfeit_divergence["descriptorCapabilityStatus"] = "supported_posix_primitives"
    expect_rejected(
        canonical_result,
        counterfeit_divergence,
        "supported descriptor capability",
    )

    incomplete_divergence_canonical = canonical()
    incomplete_divergence_canonical["evidenceComplete"] = False
    incomplete_divergence = shadow(incomplete_divergence_canonical)
    incomplete_divergence["status"] = "SHADOW_DIVERGED"
    incomplete_divergence["canonicalEvidenceComplete"] = False
    incomplete_divergence["contentIdentityMatch"] = False
    expect_rejected(
        incomplete_divergence_canonical,
        incomplete_divergence,
        "cannot accompany incomplete canonical custody",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
