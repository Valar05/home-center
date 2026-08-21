#!/usr/bin/env python3
"""Source-only inventory guard for TRY FOREVER accessibility announcement migration.

This regression deliberately does not execute Android or TalkBack. It guards the current
existing-owner surface against two opposite failures:

* a fifth legacy announceForAccessibility consequence appearing unnoticed; and
* an over-broad migration patch removing explicit-event receipts whose replacement contract is
  still blocked.

The lexical Java helper is the existing source-evidence organ. No second Java parser is created.
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
POLICY = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/AccessibilityAnnouncementSemanticPolicy.java"
NARROW_PATCH = ROOT / "patches/try-forever-heartbeat-material-transition-live-region-owner.patch"
BROAD_PATCH = ROOT / "patches/try-forever-semantic-announcement-owner-v2.patch"

EXPECTED_LEGACY_METHODS = {
    "handleSpotifyReceipt": "spotifyStatus.announceForAccessibility(",
    "refreshHeartbeatLights": "heartbeatSummary.announceForAccessibility(",
    "showHeartbeatDetail": "heartbeatDetail.announceForAccessibility(",
    "submitAdamRequest": "adamInput.announceForAccessibility(",
}


class SemanticAnnouncementInventoryTest(unittest.TestCase):
    def setUp(self) -> None:
        source = OWNER.read_text(encoding="utf-8")
        lexical = java_lexical_code_surface(source)
        self.owner = java_named_class_surface(lexical, "OperatorOverlayService")
        self.assertTrue(self.owner, "missing direct OperatorOverlayService source surface")

    def test_legacy_announcement_inventory_is_exactly_the_four_known_consequences(self) -> None:
        self.assertEqual(4, self.owner.count(".announceForAccessibility("))
        for method_name, marker in EXPECTED_LEGACY_METHODS.items():
            method = java_private_void_method_surface(self.owner, method_name)
            self.assertTrue(method, f"missing direct owner method: {method_name}")
            self.assertIn(marker, method)
            self.assertEqual(1, method.count(".announceForAccessibility("))

    def test_narrow_patch_removes_only_the_migration_ready_heartbeat_legacy_call(self) -> None:
        patch = NARROW_PATCH.read_text(encoding="utf-8")
        removed_lines = [
            line for line in patch.splitlines()
            if line.startswith("-") and "announceForAccessibility(" in line
        ]
        self.assertEqual(1, len(removed_lines))
        self.assertIn("heartbeatSummary.announceForAccessibility(", removed_lines[0])
        self.assertNotIn("spotifyStatus.announceForAccessibility(", removed_lines[0])
        self.assertNotIn("heartbeatDetail.announceForAccessibility(", removed_lines[0])
        self.assertNotIn("adamInput.announceForAccessibility(", removed_lines[0])

    def test_broad_patch_is_retained_only_as_rejected_archaeology(self) -> None:
        patch = BROAD_PATCH.read_text(encoding="utf-8")
        self.assertIn("# State: REJECTED_SUPERSEDED__DO_NOT_APPLY", patch)
        self.assertIn("historical source provenance only", patch)

    def test_every_migration_unready_consequence_has_a_named_source_blocker(self) -> None:
        policy = POLICY.read_text(encoding="utf-8")
        self.assertIn("MigrationBlocker.NONE", policy)
        self.assertIn("MigrationBlocker.SPOTIFY_REPEATABLE_RECEIPT_UNRESOLVED", policy)
        self.assertIn("MigrationBlocker.DETAIL_REPEAT_SELECTION_RECEIPT_UNRESOLVED", policy)
        self.assertIn("MigrationBlocker.ADAM_REPEAT_SEND_RESULT_UNRESOLVED", policy)


if __name__ == "__main__":
    unittest.main()
