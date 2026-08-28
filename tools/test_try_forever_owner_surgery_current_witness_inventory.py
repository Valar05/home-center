#!/usr/bin/env python3
"""Repository-level v10 witness-parity regression source.

SOURCE ONLY. This fixture executes the current canonical owner-surgery classifier when an authorized
non-phone test lane is available, then requires every admitted Surgery to have one exact
same-observation artifactContentWitness. Source existence is not TESTED evidence.
"""

from pathlib import Path

from try_forever_owner_surgery_custody_probe import PATCH_ROOT, classify
from try_forever_owner_surgery_witness_parity import audit_canonical_witness_parity


def test_current_v10_inventory_has_exact_surgery_witness_parity():
    report = classify(PATCH_ROOT, current_owner_blobs={})
    receipt = audit_canonical_witness_parity(report)
    assert receipt["witnessParity"] is True
    assert receipt["surgeryContentIdentities"] == len(report["surgeries"])
    assert receipt["artifactContentWitnesses"] == len(report["surgeries"])


def test_current_v10_witness_paths_equal_current_surgery_paths():
    report = classify(PATCH_ROOT, current_owner_blobs={})
    surgery_paths = {Path(item["path"]).as_posix() for item in report["surgeries"]}
    witness_paths = {
        Path(item["path"]).as_posix() for item in report["artifactContentWitnesses"]
    }
    assert witness_paths == surgery_paths
