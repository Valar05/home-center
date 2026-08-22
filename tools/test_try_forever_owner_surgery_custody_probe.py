#!/usr/bin/env python3
"""Regression source for TRY FOREVER owner-surgery custody classification."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from try_forever_owner_surgery_custody_probe import classify


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"
STALE = "1111111111111111111111111111111111111111"


def patch(state: str, name: str, base: str = BASE) -> str:
    return (
        f"# STATUS: {state}\n"
        f"# BASE OWNER BLOB: {base}\n"
        f"# OWNER: {OWNER}\n"
        f"# fixture: {name}\n"
        "diff --git a/owner b/owner\n"
    )


def delta(
    state: str,
    name: str,
    base: str = BASE,
    *,
    base_key: str = "baseBlob",
    state_key: str = "state",
) -> str:
    return json.dumps({
        "schema": "try-forever-owner-delta.v1",
        "owner": OWNER,
        base_key: base,
        state_key: state,
        "fixture": name,
    }, indent=2) + "\n"


def main() -> int:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-a.patch").write_text(
            patch("CORRECTED_PROPOSED_NOT_APPLIED", "a"), encoding="utf-8")
        (root / "try-forever-b.patch").write_text(
            patch("CANONICAL_PROPOSED_NOT_APPLIED", "b"), encoding="utf-8")
        (root / "try-forever-c.delta.json").write_text(
            delta("CORRECTED_PROPOSED_NOT_APPLIED", "c", base_key="ownerBaseBlob", state_key="status"),
            encoding="utf-8")
        (root / "try-forever-stale-a.patch").write_text(
            patch("CORRECTED_PROPOSED_NOT_APPLIED", "stale-a", STALE), encoding="utf-8")
        (root / "try-forever-stale-b.patch").write_text(
            patch("CANONICAL_PROPOSED_NOT_APPLIED", "stale-b", STALE), encoding="utf-8")
        (root / "try-forever-stale-c.delta.json").write_text(
            delta("CANONICAL_PROPOSED_NOT_APPLIED", "stale-c", STALE, base_key="baseOwnerBlob"),
            encoding="utf-8")
        (root / "try-forever-old.patch").write_text(
            patch("SUPERSEDED_BY_COMBINED_PATCH__DO_NOT_APPLY_ALONE", "old"), encoding="utf-8")
        (root / "try-forever-rejected.patch").write_text(
            patch("REJECTED_SUPERSEDED__DO_NOT_APPLY", "rejected"), encoding="utf-8")
        (root / "try-forever-applied.patch").write_text(
            patch("APPLIED_SOURCE", "applied"), encoding="utf-8")
        (root / "try-forever-applied.delta.json").write_text(
            delta("APPLIED_SOURCE", "applied-delta"), encoding="utf-8")

        result = classify(root, {OWNER: BASE})
        assert result["schema"] == "try-forever-owner-surgery-custody.v3"
        assert result["artifactKindsScanned"] == ["patch", "delta_json"]
        assert result["discoveryErrors"] == []
        assert result["evidenceComplete"] is True

        collisions = result["collisionSets"]
        assert len(collisions) == 1, collisions
        collision = collisions[0]
        assert collision["owner"] == OWNER
        assert collision["baseBlob"] == BASE
        assert collision["currentOwnerBlob"] == BASE
        assert collision["status"] == "CURRENT_BASE_COLLISION_SET"
        candidates = collision["promotionCandidates"]
        assert [Path(item["path"]).name for item in candidates] == [
            "try-forever-a.patch",
            "try-forever-b.patch",
            "try-forever-c.delta.json",
        ]
        assert [item["artifact_kind"] for item in candidates] == [
            "patch", "patch", "delta_json"]
        assert all(item["promotion_candidate"] for item in candidates)

        stale = result["staleBaseGroups"]
        assert len(stale) == 1, stale
        assert stale[0]["status"] == "STALE_BASE_GROUP"
        assert stale[0]["baseBlob"] == STALE
        assert stale[0]["currentOwnerBlob"] == BASE
        assert [Path(item["path"]).name for item in stale[0]["promotionCandidates"]] == [
            "try-forever-stale-a.patch",
            "try-forever-stale-b.patch",
            "try-forever-stale-c.delta.json",
        ]

        excluded = {
            Path(item["path"]).name
            for group in collisions + stale
            for item in group["promotionCandidates"]
        }
        assert "try-forever-old.patch" not in excluded
        assert "try-forever-rejected.patch" not in excluded
        assert "try-forever-applied.patch" not in excluded
        assert "try-forever-applied.delta.json" not in excluded

        unverified = classify(root)
        assert unverified["collisionSets"] == []
        assert unverified["staleBaseGroups"] == []
        assert len(unverified["unverifiedBaseGroups"]) == 2
        assert all(
            group["status"] == "UNVERIFIED_BASE_GROUP"
            for group in unverified["unverifiedBaseGroups"]
        )

        moved_owner = classify(root, {OWNER: "2222222222222222222222222222222222222222"})
        assert moved_owner["collisionSets"] == []
        assert len(moved_owner["staleBaseGroups"]) == 2

        capability = result["capability"]
        assert capability["sourceInspection"] is True
        assert capability["patchArtifactInspection"] is True
        assert capability["deltaArtifactInspection"] is True
        assert capability["currentOwnerCustodyProvided"] is True
        assert capability["patchApplied"] is False
        assert capability["ownerWired"] is False
        assert capability["regressionExecuted"] is False
        assert capability["tested"] is False
        assert capability["phoneDelivered"] is False

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        malformed = {
            "schema": "try-forever-owner-delta.v1",
            "owner": OWNER,
            "baseBlob": BASE,
            "ownerBaseBlob": STALE,
            "state": "CORRECTED_PROPOSED_NOT_APPLIED",
        }
        (root / "try-forever-conflicting.delta.json").write_text(
            json.dumps(malformed), encoding="utf-8")
        result = classify(root, {OWNER: BASE})
        assert result["surgeries"] == []
        assert result["collisionSets"] == []
        assert result["evidenceComplete"] is False
        assert len(result["discoveryErrors"]) == 1
        assert "conflicting base owner blob aliases" in result["discoveryErrors"][0]["boundary"]

    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-duplicate.delta.json").write_text(
            '{"schema":"try-forever-owner-delta.v1","owner":"a","owner":"b",'
            f'"baseBlob":"{BASE}","state":"CORRECTED_PROPOSED_NOT_APPLIED"}}',
            encoding="utf-8")
        result = classify(root)
        assert result["evidenceComplete"] is False
        assert len(result["discoveryErrors"]) == 1
        assert "duplicate JSON member" in result["discoveryErrors"][0]["boundary"]

    print("TRY FOREVER owner surgery custody regression source: patch + delta custody classified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
