#!/usr/bin/env python3
"""RED source boundary for the latest-message expanded inspection surface.

Supporting policy is not owner wiring. This fixture uses the existing Java lexical owner
surface and remains source-only; it proves neither Android execution nor TalkBack behavior.
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


class LatestMessageSurfaceOwnerBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        source = OWNER.read_text(encoding="utf-8")
        lexical = java_lexical_code_surface(source)
        owner = java_named_class_surface(lexical, "OperatorOverlayService")
        self.body = java_private_void_method_surface(owner, "applyExpandedTextState")
        self.assertTrue(self.body, "missing direct owner method: applyExpandedTextState")

    def test_expanded_surface_uses_policy_and_no_finite_line_amputation(self) -> None:
        self.assertIn("LatestMessageAccessibilityPolicy.maxLines(true)", self.body)
        self.assertIn("LatestMessageAccessibilityPolicy.maxLines(false)", self.body)
        self.assertIn("LatestMessageAccessibilityPolicy.expandedMaxHeightDp()", self.body)
        self.assertNotIn("setMaxLines(30)", self.body)


if __name__ == "__main__":
    unittest.main()
