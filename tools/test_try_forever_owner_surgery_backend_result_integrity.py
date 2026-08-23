#!/usr/bin/env python3
"""Regression source for backend-result schema + exact surgery-membership custody.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

from try_forever_owner_surgery_backend_policy import (
    DESCRIPTOR_BACKEND,
    SUPPORTED_POSIX,
    select_owner_surgery_backend,
)
from try_forever_owner_surgery_backend_result_integrity import (
    CANONICAL_CUSTODY_SCHEMA,
    admit_backend_result_with_inventory_custody,
    audit_backend_result_inventory,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"
SHA_A = "a" * 64
SHA_B = "b" * 64


def surgery(
    path: str,
    *,
    artifact_kind: str = "patch",
    state: str = "CORRECTED_PROPOSED_NOT_APPLIED",
    promotion_candidate: bool = True,
    byte_count: int = 10,
    sha256: str = SHA_A,
):
    return {
        "path": path,
        "artifact_kind": artifact_kind,
        "owner": OWNER,
        "base_blob": BASE,
        "state": state,
        "promotion_candidate": promotion_candidate,
        "artifact_byte_count": byte_count,
        "artifact_sha256": sha256,
    }


def collision_group(*members):
    return {
        "owner": OWNER,
        "baseBlob": BASE,
        "status": "CURRENT_BASE_COLLISION_SET",
        "currentOwnerBlob": BASE,
        "promotionCandidates": list(members),
    }


def complete_result():
    first = surgery("patches/try-forever-a.patch")
    second = surgery(
        "patches/try-forever-b.delta.json",
        artifact_kind="delta_json",
        byte_count=20,
        sha256=SHA_B,
    )
    diagnostic = surgery(
        "patches/try-forever-applied.patch",
        state="APPLIED_SOURCE",
        promotion_candidate=False,
        byte_count=30,
        sha256="c" * 64,
    )
    return {
        "schema": CANONICAL_CUSTODY_SCHEMA,
        "backend": DESCRIPTOR_BACKEND,
        "artifactDirectoryEntriesObserved": 9,
        "artifactCandidatesObserved": 3,
        "surgeries": [first, second, diagnostic],
        "artifactContentWitnesses": [
            {"path": item["path"], "byteCount": item["artifact_byte_count"], "sha256": item["artifact_sha256"]}
            for item in [first, second, diagnostic]
        ],
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {OWNER: BASE},
        "collisionSets": [collision_group(first, second)],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
        "portableFallbackAttempted": False,
    }


def expect_rejected(result, needle: str) -> None:
    try:
        audit_backend_result_inventory(result)
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"unsafe backend result passed inventory custody: {result!r}")


def main() -> int:
    descriptor = select_owner_surgery_backend(SUPPORTED_POSIX)
    canonical = complete_result()
    integrity = audit_backend_result_inventory(canonical)
    assert integrity["canonicalCustodySchema"] == CANONICAL_CUSTODY_SCHEMA
    assert integrity["surgeriesAdmitted"] == 3
    assert integrity["authorityGroupMembersAdmitted"] == 2
    assert integrity["phantomPromotionMembers"] == 0
    assert integrity["contentEvidenceDriftMembers"] == 0
    assert integrity["authorityAdmitted"] is False
    assert integrity["tested"] is False

    admitted = admit_backend_result_with_inventory_custody(descriptor, canonical)
    assert admitted["backend"] == DESCRIPTOR_BACKEND
    assert admitted["ownerEvidenceAdmitted"] is True
    assert admitted["surgeriesAdmitted"] == 3
    assert admitted["authorityGroupMembersAdmitted"] == 2
    assert admitted["contentEvidenceDriftMembers"] == 0

    wrong_schema = complete_result()
    wrong_schema["schema"] = "try-forever-owner-surgery-custody.v11"
    expect_rejected(wrong_schema, "exact canonical owner-surgery custody v10")

    missing_schema = complete_result()
    missing_schema.pop("schema")
    expect_rejected(missing_schema, "exact canonical owner-surgery custody v10")

    no_surgeries = complete_result()
    no_surgeries.pop("surgeries")
    expect_rejected(no_surgeries, "surgeries must be one list")

    duplicate = complete_result()
    duplicate["surgeries"] = [
        surgery("patches/try-forever-a.patch"),
        surgery("patches/try-forever-a.patch"),
    ]
    duplicate["collisionSets"] = []
    expect_rejected(duplicate, "path identity must be unique")

    kind_mismatch = complete_result()
    kind_mismatch["surgeries"][0] = surgery(
        "patches/try-forever-a.patch",
        artifact_kind="delta_json",
    )
    expect_rejected(kind_mismatch, "artifact_kind must agree with the exact artifact path suffix")

    state_lie = complete_result()
    state_lie["surgeries"][0] = surgery(
        "patches/try-forever-a.patch",
        state="APPLIED_SOURCE",
        promotion_candidate=True,
    )
    expect_rejected(state_lie, "must agree with exact admitted surgery state")

    missing_content = complete_result()
    missing_content["surgeries"][0] = {
        key: value
        for key, value in missing_content["surgeries"][0].items()
        if key not in {"artifact_byte_count", "artifact_sha256"}
    }
    expect_rejected(missing_content, "artifact_byte_count")

    malformed_sha = complete_result()
    malformed_sha["surgeries"][0]["artifact_sha256"] = "A" * 64
    expect_rejected(malformed_sha, "artifact_sha256 must be 64 lowercase hexadecimal")

    phantom = complete_result()
    phantom_member = surgery("patches/try-forever-phantom.patch")
    phantom["collisionSets"] = [
        collision_group(phantom["surgeries"][0], phantom_member)
    ]
    expect_rejected(phantom, "must exist exactly in surgeries inventory")

    changed_state = complete_result()
    changed_state_member = surgery(
        "patches/try-forever-a.patch",
        state="PROPOSED_NOT_APPLIED",
        promotion_candidate=True,
    )
    changed_state["collisionSets"] = [
        collision_group(changed_state_member, changed_state["surgeries"][1])
    ]
    expect_rejected(changed_state, "must exist exactly in surgeries inventory")

    # Same metadata with drifted content evidence is not the exact canonical Surgery member.
    changed_content = complete_result()
    changed_content_member = dict(changed_content["surgeries"][0])
    changed_content_member["artifact_sha256"] = "d" * 64
    changed_content["collisionSets"] = [
        collision_group(changed_content_member, changed_content["surgeries"][1])
    ]
    expect_rejected(changed_content, "must exist exactly in surgeries inventory")

    malformed_member = complete_result()
    malformed_member["collisionSets"] = [
        collision_group(
            malformed_member["surgeries"][0],
            {"path": "patches/try-forever-b.delta.json"},
        )
    ]
    expect_rejected(malformed_member, "artifact_kind is unsupported")

    diagnostic_only = complete_result()
    diagnostic_only["collisionSets"] = []
    diagnostic_only["surgeries"] = [
        surgery(
            "patches/try-forever-applied.patch",
            state="APPLIED_SOURCE",
            promotion_candidate=False,
            byte_count=30,
            sha256="c" * 64,
        )
    ]
    audit = audit_backend_result_inventory(diagnostic_only)
    assert audit["surgeriesAdmitted"] == 1
    assert audit["authorityGroupMembersAdmitted"] == 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
