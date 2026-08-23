#!/usr/bin/env python3
"""Regression source for backend-result schema + surgery-membership custody.

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


def surgery(
    path: str,
    *,
    artifact_kind: str = "patch",
    state: str = "CORRECTED_PROPOSED_NOT_APPLIED",
    promotion_candidate: bool = True,
):
    return {
        "path": path,
        "artifact_kind": artifact_kind,
        "owner": OWNER,
        "base_blob": BASE,
        "state": state,
        "promotion_candidate": promotion_candidate,
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
    )
    diagnostic = surgery(
        "patches/try-forever-applied.patch",
        state="APPLIED_SOURCE",
        promotion_candidate=False,
    )
    return {
        "schema": CANONICAL_CUSTODY_SCHEMA,
        "backend": DESCRIPTOR_BACKEND,
        "artifactDirectoryEntriesObserved": 9,
        "artifactCandidatesObserved": 3,
        "surgeries": [first, second, diagnostic],
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
    assert integrity["authorityAdmitted"] is False
    assert integrity["tested"] is False

    admitted = admit_backend_result_with_inventory_custody(descriptor, canonical)
    assert admitted["backend"] == DESCRIPTOR_BACKEND
    assert admitted["ownerEvidenceAdmitted"] is True
    assert admitted["surgeriesAdmitted"] == 3
    assert admitted["authorityGroupMembersAdmitted"] == 2

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
    expect_rejected(duplicate, "artifact identity must be unique")

    state_lie = complete_result()
    state_lie["surgeries"][0] = surgery(
        "patches/try-forever-a.patch",
        state="APPLIED_SOURCE",
        promotion_candidate=True,
    )
    expect_rejected(state_lie, "must agree with exact admitted surgery state")

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
        )
    ]
    audit = audit_backend_result_inventory(diagnostic_only)
    assert audit["surgeriesAdmitted"] == 1
    assert audit["authorityGroupMembersAdmitted"] == 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
