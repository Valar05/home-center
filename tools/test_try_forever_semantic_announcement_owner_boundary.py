#!/usr/bin/env python3
"""RED source boundary for consequence-specific accessibility announcement migration.

This fixture is intentionally source-only. It imports the existing lexical Java owner
surface instead of inventing another parser. It proves neither Android execution nor
TalkBack behavior. Until the sole OperatorOverlayService owner carries every semantic
replacement and removes the four deprecated announcement calls, this fixture should
remain RED.
"""

from __future__ import annotations

import unittest
from pathlib import Path

from try_forever_operator_accessibility_owner_probe import (
    java_lexical_code_surface,
    java_named_class_surface,
    java_private_void_method_surface,
)

ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"


def owner_methods(source: str) -> dict[str, str]:
    lexical = java_lexical_code_surface(source)
    owner = java_named_class_surface(lexical, "OperatorOverlayService")
    return {
        name: java_private_void_method_surface(owner, name)
        for name in (
            "createOverlay",
            "handleSpotifyReceipt",
            "refreshUi",
            "refreshHeartbeatLights",
            "showHeartbeatDetail",
            "submitAdamRequest",
        )
    }


class SemanticAnnouncementOwnerBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = OWNER.read_text(encoding="utf-8")
        self.methods = owner_methods(self.source)
        for name, body in self.methods.items():
            self.assertTrue(body, f"missing direct owner method: {name}")

    def test_legacy_global_announcements_are_retired_from_owner_code(self) -> None:
        lexical = java_lexical_code_surface(self.source)
        owner = java_named_class_surface(lexical, "OperatorOverlayService")
        self.assertNotIn(".announceForAccessibility(", owner)

    def test_spotify_receipt_uses_explicit_only_live_region_value(self) -> None:
        body = self.methods["handleSpotifyReceipt"]
        self.assertIn(
            "AccessibilityAnnouncementSemanticPolicy.Consequence.SPOTIFY_COMMAND_RECEIPT",
            body,
        )
        self.assertIn("spotifyStatus.setAccessibilityLiveRegion(", body)
        self.assertIn("requestId > 0L", body)
        self.assertNotIn("announceForAccessibility", body)

        background = self.methods["refreshUi"]
        self.assertIn("spotifyStatus.setAccessibilityLiveRegion(", background)
        self.assertIn("View.ACCESSIBILITY_LIVE_REGION_NONE", background)

    def test_heartbeat_material_transition_uses_existing_announce_gate_as_live_region_gate(self) -> None:
        body = self.methods["refreshHeartbeatLights"]
        self.assertIn(
            "AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_MATERIAL_TRANSITION",
            body,
        )
        self.assertIn("heartbeatSummary.setAccessibilityLiveRegion(", body)
        self.assertIn("boolean announce =", body)
        self.assertNotIn("heartbeatSummary.announceForAccessibility", body)

    def test_explicit_detail_selection_uses_detail_value_and_background_disables_live_region(self) -> None:
        body = self.methods["showHeartbeatDetail"]
        self.assertIn(
            "AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_EXPLICIT_DETAIL_SELECTION",
            body,
        )
        self.assertIn("heartbeatDetail.setAccessibilityLiveRegion(", body)
        self.assertIn("explicitSelection", body)
        self.assertIn("OperatorState.muted(this)", body)
        self.assertNotIn("heartbeatDetail.announceForAccessibility", body)

    def test_adam_send_uses_dedicated_status_value_not_editable_announcement(self) -> None:
        create = self.methods["createOverlay"]
        submit = self.methods["submitAdamRequest"]
        self.assertIn("adamStatus = textView(", create)
        self.assertIn("adamStatus.setAccessibilityLiveRegion(", create)
        self.assertIn("adamStatus.setText(", submit)
        self.assertIn(
            "AccessibilityAnnouncementSemanticPolicy.Consequence.ADAM_SEND_CONFIRMATION",
            submit,
        )
        self.assertNotIn("adamInput.announceForAccessibility", submit)


if __name__ == "__main__":
    unittest.main()
