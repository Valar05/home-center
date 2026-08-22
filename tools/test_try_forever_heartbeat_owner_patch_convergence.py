#!/usr/bin/env python3
"""Source-only regression for converged heartbeat owner surgery.

This does not execute Android, exercise TalkBack, mutate the phone/P0 chain, or promote patch
existence into owner wiring. It prevents two independently applicable same-base surgeries from
quietly racing the sole OperatorOverlayService owner.
"""

from pathlib import Path


OWNER = Path(
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "OperatorOverlayService.java"
)
COMBINED = Path("patches/try-forever-heartbeat-selection-announcement-owner-combined.patch")
SELECTION = Path("patches/try-forever-heartbeat-native-selection-collection-owner.patch")
ANNOUNCEMENT = Path("patches/try-forever-heartbeat-material-transition-live-region-owner.patch")
BASE_BLOB = "c5de1411a6b68087ae17aff83c032af754587150"


def main() -> int:
    owner = OWNER.read_text(encoding="utf-8")
    combined = COMBINED.read_text(encoding="utf-8")
    selection = SELECTION.read_text(encoding="utf-8")
    announcement = ANNOUNCEMENT.read_text(encoding="utf-8")

    assert "STATUS: CANONICAL_PROPOSED_NOT_APPLIED" in combined
    assert f"BASE OWNER BLOB: {BASE_BLOB}" in combined

    # Selection collection lifecycle is present in the canonical surgery.
    assert "applyHeartbeatSelectionAccessibility(model)" in combined
    assert "HeartbeatSelectionAccessibilityPolicy.fromModel" in combined
    assert "AccessibilityNodeInfo.CollectionInfo.obtain(" in combined
    assert "AccessibilityNodeInfo.CollectionItemInfo.obtain(" in combined
    assert "applyHeartbeatSelectionAccessibility(currentHeartbeatModel())" in combined

    # Only the automatic heartbeat material-transition announcement is migration-ready.
    assert "Consequence.HEARTBEAT_MATERIAL_TRANSITION" in combined
    assert "heartbeatSummary.setAccessibilityLiveRegion" in combined
    assert "-            heartbeatSummary.announceForAccessibility" in combined
    assert "spotifyStatus.announceForAccessibility" not in combined
    assert "heartbeatDetail.announceForAccessibility" not in combined
    assert "adamInput.announceForAccessibility" not in combined

    # Standalone same-base surgeries are provenance only; applying them alone would stale custody.
    assert "SUPERSEDED_BY_COMBINED_PATCH__DO_NOT_APPLY_ALONE" in selection
    assert "SUPERSEDED_BY_COMBINED_PATCH__DO_NOT_APPLY_ALONE" in announcement
    assert BASE_BLOB in selection
    assert BASE_BLOB in announcement

    # Current owner is intentionally still unwired. Patch source is not implementation.
    assert "private void applyHeartbeatSelectionAccessibility(" not in owner
    assert "heartbeatSummary.announceForAccessibility(" in owner

    print("Heartbeat owner patch convergence source: canonical combined surgery, owner still unwired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
