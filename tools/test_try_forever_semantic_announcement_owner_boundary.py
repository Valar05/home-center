#!/usr/bin/env python3
"""RED source boundary for consequence-specific accessibility announcement migration.

This fixture is intentionally source-only. It imports the existing lexical Java owner
surface instead of inventing another parser. It proves neither Android execution nor
TalkBack behavior.

The current policy accepts only heartbeat material-transition migration. Spotify
receipt, repeated heartbeat detail selection, and Adam send are repeatable action
consequences whose exact replacement semantics remain unresolved, so their legacy
calls must stay in the owner until a later reviewed contract replaces them.
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
            "handleSpotifyReceipt",
            "refreshHeartbeatLights",
            "showHeartbeatDetail",
            "submitAdamRequest",
            "clearHeartbeatPreContactWoundToWaiting",
        )
    }


class SemanticAnnouncementOwnerBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.source = OWNER.read_text(encoding="utf-8")
        self.methods = owner_methods(self.source)
        for name, body in self.methods.items():
            self.assertTrue(body, f"missing direct owner method: {name}")

    def test_heartbeat_material_transition_uses_existing_announce_gate_as_live_region_gate(self) -> None:
        body = self.methods["refreshHeartbeatLights"]
        self.assertIn(
            "AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_MATERIAL_TRANSITION",
            body,
        )
        self.assertIn("heartbeatSummary.setAccessibilityLiveRegion(", body)
        self.assertIn("boolean announce =", body)
        self.assertNotIn("heartbeatSummary.announceForAccessibility", body)

    def test_waiting_recovery_disables_stale_heartbeat_live_region_before_value_change(self) -> None:
        body = self.methods["clearHeartbeatPreContactWoundToWaiting"]
        live_region = body.index("heartbeatSummary.setAccessibilityLiveRegion(")
        waiting_text = body.index('heartbeatSummary.setText("HEARTBEAT • waiting")')
        self.assertLess(live_region, waiting_text)
        self.assertIn("View.ACCESSIBILITY_LIVE_REGION_NONE", body)

    def test_spotify_repeatable_receipt_keeps_legacy_call_until_fresh_event_semantics_exist(self) -> None:
        body = self.methods["handleSpotifyReceipt"]
        self.assertIn("spotifyStatus.announceForAccessibility(", body)
        self.assertNotIn(
            "AccessibilityAnnouncementSemanticPolicy.Consequence.SPOTIFY_COMMAND_RECEIPT",
            body,
        )

    def test_repeated_detail_selection_keeps_legacy_call_until_fresh_event_semantics_exist(self) -> None:
        body = self.methods["showHeartbeatDetail"]
        self.assertIn("heartbeatDetail.announceForAccessibility(", body)
        self.assertNotIn(
            "AccessibilityAnnouncementSemanticPolicy.Consequence.HEARTBEAT_EXPLICIT_DETAIL_SELECTION",
            body,
        )

    def test_adam_repeatable_send_keeps_legacy_call_until_fresh_event_semantics_exist(self) -> None:
        body = self.methods["submitAdamRequest"]
        self.assertIn("adamInput.announceForAccessibility(", body)
        self.assertNotIn(
            "AccessibilityAnnouncementSemanticPolicy.Consequence.ADAM_SEND_CONFIRMATION",
            body,
        )


if __name__ == "__main__":
    unittest.main()
