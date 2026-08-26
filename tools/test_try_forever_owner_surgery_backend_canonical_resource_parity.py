#!/usr/bin/env python3
"""Regression source for canonical-v10 resource parity at backend-result admission.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
The backend result policy must not accept owner identities, owner maps, authority-group counts,
or authority-member counts that canonical v10 itself cannot produce.
"""

from try_forever_owner_surgery_backend_policy import (
    DESCRIPTOR_BACKEND,
    SUPPORTED_POSIX,
    admit_selected_backend_result,
    select_owner_surgery_backend,
)
from try_forever_owner_surgery_custody_probe import MAX_CUSTODY_ARTIFACTS
from try_forever_owner_surgery_metadata_exactness import MAX_OWNER_IDENTITY_CODEPOINTS


BLOB = "a" * 40
STATE = "CORRECTED_PROPOSED_NOT_APPLIED"


def candidate(owner: str, path: str) -> dict[str, object]:
    return {
        "path": path,
        "artifact_kind": "patch",
        "owner": owner,
        "base_blob": BLOB,
        "state": STATE,
        "promotion_candidate": True,
    }


def result(*, owners: dict[str, str] | None = None) -> dict[str, object]:
    return {
        "backend": DESCRIPTOR_BACKEND,
        "portableFallbackAttempted": False,
        "artifactDirectoryEntriesObserved": 0,
        "artifactCandidatesObserved": 0,
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {} if owners is None else owners,
        "capability": {"currentOwnerCustodyProvided": True},
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
    }


def expect_rejected(payload: dict[str, object], needle: str) -> None:
    selection = select_owner_surgery_backend(SUPPORTED_POSIX)
    try:
        admit_selected_backend_result(selection, payload)
    except ValueError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"backend result widened canonical v10 custody: {needle}")


def main() -> int:
    selection = select_owner_surgery_backend(SUPPORTED_POSIX)
    ordinary = admit_selected_backend_result(selection, result(owners={"owner": BLOB}))
    assert ordinary["ownerEvidenceAdmitted"] is True
    assert ordinary["tested"] is False if "tested" in ordinary else True

    whitespace_owner = result(owners={" owner ": BLOB})
    expect_rejected(whitespace_owner, "exact owner identity")

    overlong_owner = result(owners={"o" * (MAX_OWNER_IDENTITY_CODEPOINTS + 1): BLOB})
    expect_rejected(overlong_owner, "owner-identity source ceiling")

    too_many_owners = result(
        owners={f"owner-{index}": BLOB for index in range(MAX_CUSTODY_ARTIFACTS + 1)}
    )
    expect_rejected(too_many_owners, "currentOwnerBlobs exceeds canonical item ceiling")

    too_many_groups = result()
    too_many_groups["unverifiedBaseGroups"] = [
        {
            "owner": f"owner-{index}",
            "baseBlob": BLOB,
            "status": "UNVERIFIED_BASE_GROUP",
            "promotionCandidates": [
                candidate(f"owner-{index}", f"patches/try-forever-{index}.patch")
            ],
        }
        for index in range(MAX_CUSTODY_ARTIFACTS + 1)
    ]
    expect_rejected(too_many_groups, "authority groups exceed canonical candidate ceiling")

    too_many_members = result(owners={"owner": BLOB})
    too_many_members["collisionSets"] = [
        {
            "owner": "owner",
            "baseBlob": BLOB,
            "status": "CURRENT_BASE_COLLISION_SET",
            "currentOwnerBlob": BLOB,
            "promotionCandidates": [
                candidate("owner", f"patches/try-forever-{index}.patch")
                for index in range(MAX_CUSTODY_ARTIFACTS + 1)
            ],
        }
    ]
    expect_rejected(too_many_members, "authority members exceed canonical candidate ceiling")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
