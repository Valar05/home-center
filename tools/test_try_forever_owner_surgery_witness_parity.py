#!/usr/bin/env python3
"""Hostile regression source for canonical Surgery ↔ artifactContentWitness parity.

SOURCE ONLY. This file has not been observed executing in an authorized test lane.
"""

from copy import deepcopy

from try_forever_owner_surgery_witness_parity import (
    CanonicalWitnessParityError,
    audit_canonical_witness_parity,
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


def canonical_result():
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


def expect_rejected(result, needle: str):
    try:
        audit_canonical_witness_parity(result)
    except CanonicalWitnessParityError as exc:
        assert needle in str(exc), (needle, str(exc))
    else:
        raise AssertionError(f"unsafe witness evidence passed parity gate: {result!r}")


def main() -> int:
    valid = canonical_result()
    receipt = audit_canonical_witness_parity(valid)
    assert receipt["witnessParity"] is True
    assert receipt["surgeryContentIdentities"] == 2
    assert receipt["artifactContentWitnesses"] == 2
    assert receipt["authorityAdmitted"] is False
    assert receipt["tested"] is False

    missing = deepcopy(valid)
    missing["artifactContentWitnesses"].pop()
    expect_rejected(missing, "path set must equal surgeries path set")

    phantom = deepcopy(valid)
    phantom["artifactContentWitnesses"].append(
        {"path": "patches/phantom.patch", "byteCount": 1, "sha256": "c" * 64}
    )
    expect_rejected(phantom, "path set must equal surgeries path set")

    duplicate = deepcopy(valid)
    duplicate["artifactContentWitnesses"].append(
        dict(duplicate["artifactContentWitnesses"][0])
    )
    expect_rejected(duplicate, "path identity must be unique")

    byte_drift = deepcopy(valid)
    byte_drift["artifactContentWitnesses"][0]["byteCount"] = 11
    expect_rejected(byte_drift, "content identity must equal Surgery content evidence")

    sha_drift = deepcopy(valid)
    sha_drift["artifactContentWitnesses"][1]["sha256"] = "d" * 64
    expect_rejected(sha_drift, "content identity must equal Surgery content evidence")

    malformed_sha = deepcopy(valid)
    malformed_sha["artifactContentWitnesses"][0]["sha256"] = "A" * 64
    expect_rejected(malformed_sha, "must be 64 lowercase hexadecimal")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
