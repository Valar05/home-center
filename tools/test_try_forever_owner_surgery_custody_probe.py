#!/usr/bin/env python3
"""Regression source for TRY FOREVER owner-surgery custody classification."""

from pathlib import Path
from tempfile import TemporaryDirectory

from try_forever_owner_surgery_custody_probe import classify


OWNER = "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
BASE = "c5de1411a6b68087ae17aff83c032af754587150"


def patch(state: str, name: str) -> str:
    return (
        f"# STATUS: {state}\n"
        f"# BASE OWNER BLOB: {BASE}\n"
        f"# OWNER: {OWNER}\n"
        f"# fixture: {name}\n"
        "diff --git a/owner b/owner\n"
    )


def main() -> int:
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "try-forever-a.patch").write_text(
            patch("CORRECTED_PROPOSED_NOT_APPLIED", "a"), encoding="utf-8")
        (root / "try-forever-b.patch").write_text(
            patch("CANONICAL_PROPOSED_NOT_APPLIED", "b"), encoding="utf-8")
        (root / "try-forever-old.patch").write_text(
            patch("SUPERSEDED_BY_COMBINED_PATCH__DO_NOT_APPLY_ALONE", "old"), encoding="utf-8")
        (root / "try-forever-rejected.patch").write_text(
            patch("REJECTED_SUPERSEDED__DO_NOT_APPLY", "rejected"), encoding="utf-8")

        result = classify(root)
        collisions = result["collisionSets"]
        assert len(collisions) == 1, collisions
        collision = collisions[0]
        assert collision["owner"] == OWNER
        assert collision["baseBlob"] == BASE
        assert collision["status"] == "COLLISION_SET"
        candidates = collision["promotionCandidates"]
        assert [Path(item["path"]).name for item in candidates] == [
            "try-forever-a.patch",
            "try-forever-b.patch",
        ]
        assert all(item["promotion_candidate"] for item in candidates)

        capability = result["capability"]
        assert capability["sourceInspection"] is True
        assert capability["patchApplied"] is False
        assert capability["ownerWired"] is False
        assert capability["regressionExecuted"] is False
        assert capability["tested"] is False
        assert capability["phoneDelivered"] is False

    print("TRY FOREVER owner surgery custody regression source: collision set classified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
