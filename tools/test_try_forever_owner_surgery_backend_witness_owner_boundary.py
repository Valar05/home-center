#!/usr/bin/env python3
"""Source regression for backend witness-parity owner consumption.

SOURCE ONLY / UNEXECUTED. The existing ``admit_backend_result_with_inventory_custody`` wrapper now
requires exact ``artifactContentWitnesses`` parity before delegating to authority admission. This
fixture pins that source contract without calling it TESTED or creating a second backend owner.
"""

from copy import deepcopy

from try_forever_owner_surgery_backend_policy import (
    SUPPORTED_POSIX,
    select_owner_surgery_backend,
)
from try_forever_owner_surgery_backend_result_integrity import (
    admit_backend_result_with_inventory_custody,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"


def surgery(path: str, byte_count: int, sha: str):
    return {
        "path": path,
        "artifact_kind": "patch",
        "owner": OWNER,
        "base_blob": BASE,
        "state": "CORRECTED_PROPOSED_NOT_APPLIED",
        "promotion_candidate": True,
        "artifact_byte_count": byte_count,
        "artifact_sha256": sha,
    }


def complete_result():
    first = surgery("patches/a.patch", 10, "a" * 64)
    second = surgery("patches/b.patch", 20, "b" * 64)
    return {
        "schema": "try-forever-owner-surgery-custody.v10",
        "backend": "HELD_DIRECTORY_DESCRIPTOR",
        "artifactDirectoryEntriesObserved": 2,
        "artifactCandidatesObserved": 2,
        "surgeries": [first, second],
        "artifactContentWitnesses": [
            {"path": first["path"], "byteCount": 10, "sha256": "a" * 64},
            {"path": second["path"], "byteCount": 20, "sha256": "b" * 64},
        ],
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {OWNER: BASE},
        "collisionSets": [
            {
                "owner": OWNER,
                "baseBlob": BASE,
                "status": "CURRENT_BASE_COLLISION_SET",
                "currentOwnerBlob": BASE,
                "promotionCandidates": [first, second],
            }
        ],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
        "portableFallbackAttempted": False,
    }


def expect_owner_rejected(result) -> None:
    selection = select_owner_surgery_backend(SUPPORTED_POSIX)
    try:
        admitted = admit_backend_result_with_inventory_custody(selection, deepcopy(result))
    except ValueError:
        return
    raise AssertionError(
        "existing backend result-integrity/admission wrapper admitted contradictory "
        f"artifactContentWitnesses: {admitted!r}"
    )


def test_existing_backend_admission_requires_exact_witness_parity():
    selection = select_owner_surgery_backend(SUPPORTED_POSIX)
    canonical = complete_result()
    admitted = admit_backend_result_with_inventory_custody(selection, deepcopy(canonical))
    assert admitted["witnessParity"] is True
    assert admitted["witnessParityOwnerWired"] is True
    assert admitted["artifactContentWitnessesAdmitted"] == 2

    drifted_sha = complete_result()
    drifted_sha["artifactContentWitnesses"][0]["sha256"] = "d" * 64
    expect_owner_rejected(drifted_sha)

    drifted_count = complete_result()
    drifted_count["artifactContentWitnesses"][0]["byteCount"] = 11
    expect_owner_rejected(drifted_count)

    missing = complete_result()
    missing["artifactContentWitnesses"] = missing["artifactContentWitnesses"][1:]
    expect_owner_rejected(missing)

    phantom = complete_result()
    phantom["artifactContentWitnesses"].append(
        {"path": "patches/phantom.patch", "byteCount": 1, "sha256": "e" * 64}
    )
    expect_owner_rejected(phantom)
