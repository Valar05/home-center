#!/usr/bin/env python3
"""Regression source for backend-result one-observation exact-JSON custody.

SOURCE ONLY. No authorized execution receipt exists for this file.
"""

from try_forever_owner_surgery_backend_policy import SUPPORTED_POSIX, select_owner_surgery_backend
from try_forever_owner_surgery_backend_result_integrity import (
    CANONICAL_CUSTODY_SCHEMA,
    admit_backend_result_with_inventory_custody,
    audit_backend_result_inventory,
    audit_backend_result_witness_parity,
)


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"


class CallbackDict(dict):
    get_calls = 0
    items_calls = 0

    def get(self, *args, **kwargs):
        type(self).get_calls += 1
        raise AssertionError("caller-owned get() executed before backend-result snapshot admission")

    def items(self):
        type(self).items_calls += 1
        raise AssertionError("caller-owned items() executed before backend-result snapshot admission")


class CallbackString(str):
    eq_calls = 0

    def __eq__(self, other):
        type(self).eq_calls += 1
        raise AssertionError("caller-owned string equality executed inside backend-result custody")



def surgery():
    return {
        "path": "patches/try-forever-a.patch",
        "artifact_kind": "patch",
        "owner": OWNER,
        "base_blob": BASE,
        "state": "CORRECTED_PROPOSED_NOT_APPLIED",
        "promotion_candidate": True,
        "artifact_byte_count": 10,
        "artifact_sha256": "a" * 64,
    }



def result():
    item = surgery()
    return {
        "schema": CANONICAL_CUSTODY_SCHEMA,
        "artifactDirectoryEntriesObserved": 1,
        "artifactCandidatesObserved": 1,
        "surgeries": [item],
        "artifactContentWitnesses": [
            {"path": item["path"], "byteCount": item["artifact_byte_count"], "sha256": item["artifact_sha256"]}
        ],
        "discoveryErrors": [],
        "evidenceComplete": True,
        "currentOwnerBlobs": {OWNER: BASE},
        "collisionSets": [],
        "staleBaseGroups": [],
        "unverifiedBaseGroups": [],
        "portableFallbackAttempted": False,
    }



def expect_snapshot_rejected(value, function) -> None:
    try:
        function(value)
    except ValueError as exc:
        assert "bounded exact JSON object" in str(exc), str(exc)
    else:
        raise AssertionError("hostile backend result crossed exact-JSON snapshot custody")



def main() -> int:
    ordinary = result()
    inventory = audit_backend_result_inventory(ordinary)
    assert inventory["callerEvidenceSnapshotted"] is True
    witness = audit_backend_result_witness_parity(ordinary)
    assert witness["callerEvidenceSnapshotted"] is True

    selection = select_owner_surgery_backend(SUPPORTED_POSIX)
    composed = admit_backend_result_with_inventory_custody(selection, ordinary)
    assert composed["callerEvidenceSnapshotted"] is True

    CallbackDict.get_calls = 0
    CallbackDict.items_calls = 0
    hostile_root = CallbackDict(result())
    expect_snapshot_rejected(hostile_root, audit_backend_result_inventory)
    assert CallbackDict.get_calls == 0
    assert CallbackDict.items_calls == 0

    CallbackDict.get_calls = 0
    CallbackDict.items_calls = 0
    hostile_nested = result()
    hostile_nested["surgeries"][0] = CallbackDict(hostile_nested["surgeries"][0])
    expect_snapshot_rejected(hostile_nested, audit_backend_result_inventory)
    assert CallbackDict.get_calls == 0
    assert CallbackDict.items_calls == 0

    CallbackString.eq_calls = 0
    hostile_scalar = result()
    hostile_scalar["schema"] = CallbackString(CANONICAL_CUSTODY_SCHEMA)
    expect_snapshot_rejected(hostile_scalar, audit_backend_result_inventory)
    assert CallbackString.eq_calls == 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
