#!/usr/bin/env python3
"""Source boundary for the full-screen technical touch guard.

The guard is an interception layer, not operator content. The sole OperatorOverlayService
owner now consumes the supporting accessibility policy. This is source evidence only, not
Android/TalkBack runtime proof.
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


class TouchGuardAccessibilityOwnerBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        source = OWNER.read_text(encoding="utf-8")
        lexical = java_lexical_code_surface(source)
        owner = java_named_class_surface(lexical, "OperatorOverlayService")
        self.body = java_private_void_method_surface(owner, "createOverlay")
        self.assertTrue(self.body, "missing direct owner method: createOverlay")

    def test_technical_guard_is_not_an_accessibility_semantic_surface(self) -> None:
        self.assertIn(
            "touchGuard.setImportantForAccessibility(TechnicalTouchGuardAccessibilityPolicy.importantForAccessibility())",
            self.body,
        )
        self.assertIn(
            "touchGuard.setContentDescription(TechnicalTouchGuardAccessibilityPolicy.contentDescription())",
            self.body,
        )
        self.assertNotIn('touchGuard.setContentDescription("Remote input active")', self.body)


if __name__ == "__main__":
    unittest.main()
