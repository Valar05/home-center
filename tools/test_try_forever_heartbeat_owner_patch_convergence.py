#!/usr/bin/env python3
"""Source-only regression for converged heartbeat owner surgery.

This does not execute Android, exercise TalkBack, mutate the phone/P0 chain, or promote source
wiring into runtime evidence. It pins the applied sole-owner composition to the corrected horizontal
collection policy and preserves the narrower repeatable announcement receipts that were not migrated.
"""

from pathlib import Path


OWNER = Path(
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "OperatorOverlayService.java"
)
POLICY = Path(
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/"
    "HeartbeatSelectionAccessibilityPolicy.java"
)
COMBINED = Path("patches/try-forever-heartbeat-selection-announcement-owner-combined.patch")
SELECTION = Path("patches/try-forever-heartbeat-native-selection-collection-owner.patch")
ANNOUNCEMENT = Path("patches/try-forever-heartbeat-material-transition-live-region-owner.patch")
BASE_BLOB = "c5de1411a6b68087ae17aff83c032af754587150"
APPLIED_COMMIT = "47e7ac3410b48596ad22d1c72a94580133e1596f"
APPLIED_BLOB = "2935243f136359e3489a89108406e888b0ec2911"


def main() -> int:
    owner = OWNER.read_text(encoding="utf-8")
    policy = POLICY.read_text(encoding="utf-8")
    combined = COMBINED.read_text(encoding="utf-8")
    selection = SELECTION.read_text(encoding="utf-8")
    announcement = ANNOUNCEMENT.read_text(encoding="utf-8")

    assert "STATUS: APPLIED_SOURCE" in combined
    assert f"BASE OWNER BLOB: {BASE_BLOB}" in combined
    assert f"APPLIED OWNER COMMIT: {APPLIED_COMMIT}" in combined
    assert f"APPLIED OWNER BLOB: {APPLIED_BLOB}" in combined

    # The policy owns horizontal collection geometry: one row, N columns. The sole owner consumes
    # those decisions instead of copying geometry constants.
    assert "this.rowIndex = 0;" in policy
    assert "this.columnIndex = itemIndex;" in policy
    assert "this.rowCount = items.isEmpty() ? 0 : 1;" in policy
    assert "this.columnCount = items.size();" in policy
    assert "private void applyHeartbeatSelectionAccessibility(" in owner
    assert "HeartbeatSelectionAccessibilityPolicy.fromModel" in owner
    assert "decision.rowCount" in owner
    assert "decision.columnCount" in owner
    assert "itemDecision.rowIndex" in owner
    assert "itemDecision.columnIndex" in owner
    assert "applyHeartbeatSelectionAccessibility(currentHeartbeatModel())" in owner

    # Only HEARTBEAT_MATERIAL_TRANSITION migrated to one-shot live-region semantics.
    assert "Consequence.HEARTBEAT_MATERIAL_TRANSITION" in owner
    assert "heartbeatSummary.setAccessibilityLiveRegion" in owner
    assert "heartbeatSummary.announceForAccessibility(" not in owner

    # Repeatable/direct receipts remain explicit and were not removed by the heartbeat migration.
    assert "spotifyStatus.announceForAccessibility" in owner
    assert "heartbeatDetail.announceForAccessibility" in owner
    assert "adamInput.announceForAccessibility" in owner

    # Standalone same-base surgeries remain historical/superseded provenance only.
    assert "SUPERSEDED_BY_COMBINED_PATCH__DO_NOT_APPLY_ALONE" in selection
    assert "SUPERSEDED_BY_COMBINED_PATCH__DO_NOT_APPLY_ALONE" in announcement
    assert BASE_BLOB in selection
    assert BASE_BLOB in announcement

    print(
        "Heartbeat owner convergence source: horizontal collection + material-transition live "
        "region SOURCE_WIRED; repeatable receipts preserved; runtime/TalkBack unproven"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
