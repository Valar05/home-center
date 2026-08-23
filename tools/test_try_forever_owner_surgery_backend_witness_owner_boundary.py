#!/usr/bin/env python3
"""RED owner-boundary regression for backend witness-parity consumption.

SOURCE ONLY / INTENTIONALLY RED against the current branch. The existing
``admit_backend_result_with_inventory_custody`` wrapper validates canonical Surgery/group custody
but does not yet require ``artifactContentWitnesses`` parity before delegating to authority admission.

When that exact existing wrapper consumes the parity gate, this fixture may turn green. Do not
create a second backend authority owner to satisfy it.
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


def result_with_drifted_witness():
    first = surgery("patches/a.patch", 10, "a" * 64)
    second = surgery("patches/b.patch", 20, "b" * 64)
    return {
        "schema": "try-forever-owner-surgery-custody.v10",
        "backend": "HELD_DIRECTORY_DESCRIPTOR",
        "artifactDirectoryEntriesObserved": 2,
        "artifactCandidatesObserved": 2,
        "surgeries": [first, second],
        "artifactContentWitnesses": [
            # Deliberately conflicts with the exact Surgery content evidence.
            {"path": first["path"], "byteCount": 10, "sha256": "d" * 64},
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


def test_existing_backend_admission_must_reject_witness_content_drift():
    selection = select_owner_surgery_backend(SUPPORTED_POSIX)
    wounded = result_with_drifted_witness()
    try:
        admitted = admit_backend_result_with_inventory_custody(selection, deepcopy(wounded))
    except ValueError:
        return
    raise AssertionError(
        "RED: existing backend result-integrity/admission wrapper admitted drifted "
        f"artifactContentWitnesses: {admitted!r}"
    )
