#!/usr/bin/env python3
"""Hostile SOURCE-ONLY regression for owner-surgery authority-group member integrity.

This does not execute custody, apply owner surgeries, touch Android/Phone/P0, or claim TESTED.
It pins the supporting backend-result gate added by TRY FOREVER: a group shell is not promotion
authority unless its members are distinct canonical Surgery-shaped evidence bound to that group.
"""

from try_forever_owner_surgery_backend_policy import (
    DESCRIPTOR_BACKEND,
    SUPPORTED_POSIX,
    admit_selected_backend_result,
    select_owner_surgery_backend,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"
OTHER = "tools/other-owner.py"


def member(path: str, **overrides):
    value = {
        "path": path,
        "artifact_kind": "patch",
        "owner": OWNER,
        "base_blob": BASE,
        "state": "CORRECTED_PROPOSED_NOT_APPLIED",
        "promotion_candidate": True,
    }
    value.update(overrides)
    return value


def collision(members):
    return {
        "owner": OWNER,
        "baseBlob": BASE,
        "status": "CURRENT_BASE_COLLISION_SET",
        "currentOwnerBlob": BASE,
        "promotionCandidates": members,
    }


def result(groups):
    return {
        "backend": DESCRIPTOR_BACKEND,
        "artifactDirectoryEntriesObserved": 8,
        "artifactCandidatesObserved": 3,
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {OWNER: BASE},
        "collisionSets": groups,
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
        "portableFallbackAttempted": False,
    }


def reject(groups, needle: str) -> None:
    selection = select_owner_surgery_backend(SUPPORTED_POSIX)
    try:
        admit_selected_backend_result(selection, result(groups))
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError("counterfeit authority-group evidence was admitted")


def main() -> int:
    selection = select_owner_surgery_backend(SUPPORTED_POSIX)
    good = admit_selected_backend_result(
        selection,
        result([collision([
            member("patches/try-forever-a.patch"),
            member("patches/try-forever-b.patch", artifact_kind="delta_json"),
        ])]),
    )
    assert good["authorityGroupCounts"]["collisionSets"] == 1
    assert good["ownerEvidenceAdmitted"] is True

    reject([collision([])], "at least 2")
    reject(
        [collision([member("patches/try-forever-a.patch"), member("patches/try-forever-a.patch")])],
        "artifact identity must be unique",
    )
    duplicate_group = collision([
        member("patches/try-forever-a.patch"),
        member("patches/try-forever-b.patch"),
    ])
    reject([duplicate_group, dict(duplicate_group)], "owner/base identity must be unique")
    reject(
        [collision([
            member("patches/try-forever-a.patch", owner=OTHER),
            member("patches/try-forever-b.patch"),
        ])],
        "owner must match group owner",
    )
    reject(
        [collision([
            member("patches/try-forever-a.patch", base_blob="1" * 40),
            member("patches/try-forever-b.patch"),
        ])],
        "base_blob must match group baseBlob",
    )
    reject(
        [collision([
            member("patches/try-forever-a.patch", artifact_kind="binary"),
            member("patches/try-forever-b.patch"),
        ])],
        "artifact_kind is unsupported",
    )
    reject(
        [collision([
            member("patches/try-forever-a.patch", state="APPLIED_SOURCE", promotion_candidate=False),
            member("patches/try-forever-b.patch"),
        ])],
        "state is not promotion-ready",
    )
    reject(
        [collision([
            member("patches/try-forever-a.patch", promotion_candidate=False),
            member("patches/try-forever-b.patch"),
        ])],
        "promotion_candidate=true",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
