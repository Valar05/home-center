#!/usr/bin/env python3
"""Repository-level regression source for the canonical v10 owner-surgery inventory.

The 08:02 checkpoint left current-inventory behavior under the stricter textual state grammar
unexecuted. This fixture makes that exact contract executable when an authorized non-phone test lane
is available. Source existence is not execution or TESTED evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from try_forever_owner_surgery_custody_probe import classify


REPO_ROOT = Path(__file__).resolve().parents[1]
PATCH_ROOT = REPO_ROOT / "patches"


def test_current_try_forever_surgery_inventory_is_fully_admissible_under_v10():
    report = classify(PATCH_ROOT, current_owner_blobs={})
    assert report["evidenceComplete"], json.dumps(
        report["discoveryErrors"],
        sort_keys=True,
        indent=2,
    )
    assert report["artifactCandidatesObserved"] > 0
    assert report["artifactDirectoryEntriesObserved"] >= report["artifactCandidatesObserved"]
    assert len(report["surgeries"]) == report["artifactCandidatesObserved"]


def test_historical_v8_v9_owner_custody_artifacts_do_not_reenter_promotion_authority():
    report = classify(PATCH_ROOT, current_owner_blobs={})
    by_name = {Path(item["path"]).name: item for item in report["surgeries"]}

    v8 = by_name["try-forever-owner-surgery-custody-v8-final-root.patch"]
    v9 = by_name["try-forever-owner-surgery-custody-v9-root-state.patch"]
    v10 = by_name["try-forever-owner-surgery-custody-v10-root-state-exact.patch"]

    assert v8["promotion_candidate"] is False
    assert v9["promotion_candidate"] is False
    assert v10["promotion_candidate"] is False
    assert v10["state"] == "APPLIED_SOURCE"


def test_current_inventory_with_no_owner_blob_never_claims_current_base_readiness():
    report = classify(PATCH_ROOT, current_owner_blobs={})
    assert report["collisionSets"] == []
    assert report["staleBaseGroups"] == []
    for group in report["unverifiedBaseGroups"]:
        assert group["status"] == "UNVERIFIED_BASE_GROUP"
        assert "current-base readiness is unproven" in group["boundary"]
