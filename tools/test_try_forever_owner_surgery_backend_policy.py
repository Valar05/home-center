#!/usr/bin/env python3
"""Regression source for TRY FOREVER owner-surgery backend selection.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

from try_forever_owner_surgery_backend_policy import (
    DESCRIPTOR_BACKEND,
    OWNER_AUTHORITY_FIELDS,
    PORTABLE_BACKEND,
    PORTABLE_UNAVAILABLE,
    REQUIRED_OWNER_EVIDENCE_FIELDS,
    SUPPORTED_POSIX,
    admit_selected_backend_result,
    classify_selected_backend_failure,
    select_owner_surgery_backend,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"
STALE_BASE = "1111111111111111111111111111111111111111"
OTHER_OWNER = "tools/other-owner.py"
OTHER_BASE = "2222222222222222222222222222222222222222"


def complete_result(**overrides):
    result = {
        "backend": DESCRIPTOR_BACKEND,
        "artifactDirectoryEntriesObserved": 7,
        "artifactCandidatesObserved": 3,
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {OWNER: BASE},
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
        "portableFallbackAttempted": False,
    }
    result.update(overrides)
    return result


def candidate(
    *,
    owner=OWNER,
    base_blob=BASE,
    state="CORRECTED_PROPOSED_NOT_APPLIED",
    artifact_kind="patch",
    path="patches/try-forever-a.patch",
    promotion_candidate=True,
):
    return {
        "path": path,
        "artifact_kind": artifact_kind,
        "owner": owner,
        "base_blob": base_blob,
        "state": state,
        "promotion_candidate": promotion_candidate,
    }


def collision_group(**overrides):
    group = {
        "owner": OWNER,
        "baseBlob": BASE,
        "status": "CURRENT_BASE_COLLISION_SET",
        "currentOwnerBlob": BASE,
        "promotionCandidates": [
            candidate(path="patches/try-forever-a.patch"),
            candidate(path="patches/try-forever-b.patch", artifact_kind="delta_json"),
        ],
    }
    group.update(overrides)
    return group


def stale_group(**overrides):
    group = {
        "owner": OWNER,
        "baseBlob": STALE_BASE,
        "status": "STALE_BASE_GROUP",
        "currentOwnerBlob": BASE,
        "promotionCandidates": [
            candidate(base_blob=STALE_BASE, path="patches/try-forever-stale.patch"),
        ],
    }
    group.update(overrides)
    return group


def unverified_group(**overrides):
    group = {
        "owner": OTHER_OWNER,
        "baseBlob": OTHER_BASE,
        "status": "UNVERIFIED_BASE_GROUP",
        "promotionCandidates": [
            candidate(
                owner=OTHER_OWNER,
                base_blob=OTHER_BASE,
                path="patches/try-forever-unverified.patch",
            ),
        ],
    }
    group.update(overrides)
    return group


def expect_rejected(descriptor, result, needle: str) -> None:
    try:
        admit_selected_backend_result(descriptor, result)
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"unsafe backend result earned evidence authority: {result!r}")


def main() -> int:
    descriptor = select_owner_surgery_backend(SUPPORTED_POSIX)
    assert descriptor.backend == DESCRIPTOR_BACKEND
    assert descriptor.descriptor_selected is True
    assert descriptor.portable_is_primary is False
    assert descriptor.fallback_after_backend_failure is False
    assert descriptor.required_owner_evidence_fields == REQUIRED_OWNER_EVIDENCE_FIELDS
    assert descriptor.required_owner_evidence_fields == (
        "artifactDirectoryEntriesObserved",
        "artifactCandidatesObserved",
        "discoveryErrors",
        "currentOwnerBlobs",
    )
    assert OWNER_AUTHORITY_FIELDS == (
        "collisionSets",
        "staleBaseGroups",
        "unverifiedBaseGroups",
    )

    admitted = admit_selected_backend_result(descriptor, complete_result())
    assert admitted == {
        "backend": DESCRIPTOR_BACKEND,
        "status": "EVIDENCE_ADMITTED",
        "artifactDirectoryEntriesObserved": 7,
        "artifactCandidatesObserved": 3,
        "discoveryErrorCount": 0,
        "evidenceComplete": True,
        "currentOwnerCustodyProvided": True,
        "authorityGroupCounts": {
            "collisionSets": 0,
            "staleBaseGroups": 0,
            "unverifiedBaseGroups": 0,
        },
        "portableFallbackAttempted": False,
        "exhaustiveEvidenceAdmitted": True,
        "ownerEvidenceAdmitted": True,
    }

    valid_collision = admit_selected_backend_result(
        descriptor,
        complete_result(collisionSets=[collision_group()]),
    )
    assert valid_collision["ownerEvidenceAdmitted"] is True
    assert valid_collision["authorityGroupCounts"]["collisionSets"] == 1

    valid_stale = admit_selected_backend_result(
        descriptor,
        complete_result(staleBaseGroups=[stale_group()]),
    )
    assert valid_stale["ownerEvidenceAdmitted"] is True
    assert valid_stale["authorityGroupCounts"]["staleBaseGroups"] == 1

    # Authenticated custody for OWNER must not upgrade OTHER_OWNER's unverified authority.
    unrelated_authenticated_owner = admit_selected_backend_result(
        descriptor,
        complete_result(unverifiedBaseGroups=[unverified_group()]),
    )
    assert unrelated_authenticated_owner["currentOwnerCustodyProvided"] is True
    assert unrelated_authenticated_owner["exhaustiveEvidenceAdmitted"] is True
    assert unrelated_authenticated_owner["ownerEvidenceAdmitted"] is False
    assert unrelated_authenticated_owner["authorityGroupCounts"]["unverifiedBaseGroups"] == 1

    incomplete = admit_selected_backend_result(
        descriptor,
        complete_result(
            discoveryErrors=[{"boundary": "artifact wounded"}],
            evidenceComplete=False,
        ),
    )
    assert incomplete["ownerEvidenceAdmitted"] is False
    assert incomplete["exhaustiveEvidenceAdmitted"] is False
    assert incomplete["evidenceComplete"] is False
    assert incomplete["discoveryErrorCount"] == 1

    # Diagnostic surgeries may remain present after a wounded exhaustive scan; they are not promotion authority.
    incomplete_with_diagnostics = complete_result(
        discoveryErrors=[{"boundary": "artifact wounded"}],
        evidenceComplete=False,
    )
    incomplete_with_diagnostics["surgeries"] = [{"path": "diagnostic-only.patch"}]
    assert admit_selected_backend_result(
        descriptor,
        incomplete_with_diagnostics,
    )["ownerEvidenceAdmitted"] is False

    no_owner = admit_selected_backend_result(
        descriptor,
        complete_result(currentOwnerBlobs={}),
    )
    assert no_owner["exhaustiveEvidenceAdmitted"] is True
    assert no_owner["currentOwnerCustodyProvided"] is False
    assert no_owner["ownerEvidenceAdmitted"] is False

    expect_rejected(
        descriptor,
        complete_result(
            collisionSets=[collision_group()],
            discoveryErrors=[{"boundary": "artifact wounded"}],
            evidenceComplete=False,
        ),
        "partial promotion authority",
    )
    expect_rejected(
        descriptor,
        complete_result(artifactCandidatesObserved=8),
        "cannot exceed",
    )
    expect_rejected(
        descriptor,
        complete_result(artifactCandidatesObserved=True),
        "non-negative integer",
    )
    expect_rejected(
        descriptor,
        complete_result(artifactDirectoryEntriesObserved=-1),
        "non-negative integer",
    )
    expect_rejected(
        descriptor,
        complete_result(evidenceComplete="yes"),
        "evidenceComplete",
    )
    expect_rejected(
        descriptor,
        complete_result(discoveryErrors=None),
        "discoveryErrors",
    )
    expect_rejected(
        descriptor,
        complete_result(
            discoveryErrors=[{"boundary": "artifact wounded"}],
            evidenceComplete=True,
        ),
        "agree with discoveryErrors",
    )
    expect_rejected(
        descriptor,
        complete_result(currentOwnerBlobs=None),
        "currentOwnerBlobs",
    )
    expect_rejected(
        descriptor,
        complete_result(currentOwnerBlobs={OWNER: BASE.upper()}),
        "40 lowercase hexadecimal",
    )
    expect_rejected(
        descriptor,
        complete_result(staleBaseGroups=None),
        "staleBaseGroups",
    )
    expect_rejected(
        descriptor,
        complete_result(backend=PORTABLE_BACKEND),
        "identity",
    )
    expect_rejected(
        descriptor,
        complete_result(portableFallbackAttempted=True),
        "fallback",
    )

    # Authority groups must agree with authenticated current-owner custody, not merely be list-shaped.
    expect_rejected(
        descriptor,
        complete_result(collisionSets=[collision_group(owner=OTHER_OWNER)]),
        "promotion candidate owner must match group owner",
    )
    expect_rejected(
        descriptor,
        complete_result(collisionSets=[collision_group(currentOwnerBlob=OTHER_BASE)]),
        "must match currentOwnerBlobs",
    )
    expect_rejected(
        descriptor,
        complete_result(
            collisionSets=[collision_group(
                baseBlob=STALE_BASE,
                promotionCandidates=[
                    candidate(base_blob=STALE_BASE, path="patches/try-forever-a.patch"),
                    candidate(base_blob=STALE_BASE, path="patches/try-forever-b.patch"),
                ],
            )],
        ),
        "must equal authenticated current owner blob",
    )
    expect_rejected(
        descriptor,
        complete_result(
            staleBaseGroups=[stale_group(
                baseBlob=BASE,
                promotionCandidates=[candidate(base_blob=BASE)],
            )],
        ),
        "must differ from authenticated current owner blob",
    )
    expect_rejected(
        descriptor,
        complete_result(
            currentOwnerBlobs={OWNER: BASE, OTHER_OWNER: OTHER_BASE},
            unverifiedBaseGroups=[unverified_group()],
        ),
        "must not have authenticated current-owner custody",
    )
    expect_rejected(
        descriptor,
        complete_result(unverifiedBaseGroups=[unverified_group(currentOwnerBlob=OTHER_BASE)]),
        "must not claim a currentOwnerBlob",
    )
    expect_rejected(
        descriptor,
        complete_result(collisionSets=["not-a-group"]),
        "entries must be mappings",
    )

    # Group shell != authority: every promotion member must be canonical and bound to the group.
    expect_rejected(
        descriptor,
        complete_result(collisionSets=[collision_group(promotionCandidates=[])]),
        "at least 2",
    )
    expect_rejected(
        descriptor,
        complete_result(staleBaseGroups=[stale_group(promotionCandidates=[])]),
        "at least 1",
    )
    expect_rejected(
        descriptor,
        complete_result(unverifiedBaseGroups=[unverified_group(promotionCandidates=[])]),
        "at least 1",
    )
    expect_rejected(
        descriptor,
        complete_result(collisionSets=[collision_group(promotionCandidates=["not-a-member", candidate()])]),
        "promotionCandidates entries must be mappings",
    )
    expect_rejected(
        descriptor,
        complete_result(collisionSets=[collision_group(promotionCandidates=[
            candidate(owner=OTHER_OWNER),
            candidate(path="patches/try-forever-b.patch"),
        ])]),
        "owner must match group owner",
    )
    expect_rejected(
        descriptor,
        complete_result(collisionSets=[collision_group(promotionCandidates=[
            candidate(base_blob=STALE_BASE),
            candidate(path="patches/try-forever-b.patch"),
        ])]),
        "base_blob must match group baseBlob",
    )
    expect_rejected(
        descriptor,
        complete_result(collisionSets=[collision_group(promotionCandidates=[
            candidate(artifact_kind="binary"),
            candidate(path="patches/try-forever-b.patch"),
        ])]),
        "artifact_kind is unsupported",
    )
    expect_rejected(
        descriptor,
        complete_result(collisionSets=[collision_group(promotionCandidates=[
            candidate(path=""),
            candidate(path="patches/try-forever-b.patch"),
        ])]),
        "path must be one non-empty string",
    )
    expect_rejected(
        descriptor,
        complete_result(collisionSets=[collision_group(promotionCandidates=[
            candidate(state="APPLIED_SOURCE", promotion_candidate=False),
            candidate(path="patches/try-forever-b.patch"),
        ])]),
        "state is not promotion-ready",
    )
    expect_rejected(
        descriptor,
        complete_result(collisionSets=[collision_group(promotionCandidates=[
            candidate(promotion_candidate=False),
            candidate(path="patches/try-forever-b.patch"),
        ])]),
        "promotion_candidate=true",
    )

    wound = classify_selected_backend_failure(
        descriptor,
        "candidate identity changed after held-root enumeration",
    )
    assert wound == {
        "backend": DESCRIPTOR_BACKEND,
        "status": "FAIL_CLOSED",
        "boundary": "candidate identity changed after held-root enumeration",
        "portableFallbackAttempted": False,
        "ownerEvidenceAdmitted": False,
    }

    portable = select_owner_surgery_backend(PORTABLE_UNAVAILABLE)
    assert portable.backend == PORTABLE_BACKEND
    assert portable.descriptor_selected is False
    assert portable.portable_is_primary is True
    assert portable.fallback_after_backend_failure is False
    assert portable.required_owner_evidence_fields == REQUIRED_OWNER_EVIDENCE_FIELDS

    portable_result = complete_result(backend=PORTABLE_BACKEND)
    admitted_portable = admit_selected_backend_result(portable, portable_result)
    assert admitted_portable["backend"] == PORTABLE_BACKEND
    assert admitted_portable["ownerEvidenceAdmitted"] is True

    for unsupported in ("", "SUPPORTED", "UNKNOWN", "supported_posix_primitives"):
        try:
            select_owner_surgery_backend(unsupported)
        except ValueError as exc:
            assert "unsupported directory-handle capability status" in str(exc)
        else:
            raise AssertionError(f"unknown capability status earned backend authority: {unsupported!r}")

    try:
        classify_selected_backend_failure(descriptor, "")
    except ValueError as exc:
        assert "failure boundary" in str(exc)
    else:
        raise AssertionError("empty descriptor failure boundary earned authority")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
