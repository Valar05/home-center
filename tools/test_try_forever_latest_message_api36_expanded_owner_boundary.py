#!/usr/bin/env python3
"""RED source boundary for Android 16 expanded-state semantics on latest message.

This source fixture does not execute Android or TalkBack. It prevents policy existence,
stateDescription fallback, comments, literals, or wrong-owner code from being reported as
API-36 owner wiring. The module currently compiles against SDK 35, so real owner wiring is
also blocked until the Android build contract deliberately advances to compileSdk >= 36.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

from try_forever_operator_accessibility_owner_probe import (
    java_lexical_code_surface,
    java_named_class_surface,
    java_private_void_method_surface,
)

ROOT = Path(__file__).resolve().parents[1]
OWNER = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
POLICY = ROOT / "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/LatestMessageAccessibilityPolicy.java"
BUILD = ROOT / "android/operator-overlay/app/build.gradle"


def compile_sdk() -> int:
    source = BUILD.read_text(encoding="utf-8")
    match = re.search(r"\bcompileSdk\s+(\d+)\b", source)
    if not match:
        raise AssertionError("compileSdk not found in operator-overlay app build.gradle")
    return int(match.group(1))


class LatestMessageApi36ExpandedOwnerBoundaryTest(unittest.TestCase):
    def setUp(self) -> None:
        source = OWNER.read_text(encoding="utf-8")
        lexical = java_lexical_code_surface(source)
        self.owner = java_named_class_surface(lexical, "OperatorOverlayService")
        self.assertTrue(self.owner, "missing direct OperatorOverlayService source surface")
        self.create_overlay = java_private_void_method_surface(self.owner, "createOverlay")
        self.assertTrue(self.create_overlay, "missing direct owner createOverlay method")

    def test_supporting_policy_has_compilesdk_safe_api36_state_values(self) -> None:
        policy = POLICY.read_text(encoding="utf-8")
        self.assertIn("expandedStateApi36", policy)
        self.assertIn("API36_EXPANDED_STATE_FULL = 3", policy)
        self.assertIn("API36_EXPANDED_STATE_COLLAPSED = 1", policy)
        self.assertNotIn("import android.view.accessibility.AccessibilityNodeInfo", policy)

    def test_existing_owner_requires_api36_build_contract_and_direct_wiring(self) -> None:
        # Intentionally RED under the current compileSdk 35. Owner promotion requires the
        # build contract and the direct accessibility delegate wiring to move together.
        self.assertGreaterEqual(compile_sdk(), 36)
        self.assertIn("Build.VERSION.SDK_INT >= 36", self.create_overlay)
        self.assertIn("info.setExpandedState(", self.create_overlay)
        self.assertIn("LatestMessageAccessibilityPolicy.expandedStateApi36(expandedText)", self.create_overlay)

    def test_comments_and_literals_cannot_counterfeit_owner_wiring(self) -> None:
        counterfeit = r'''
            class OperatorOverlayService {
                private void createOverlay() {
                    // info.setExpandedState(LatestMessageAccessibilityPolicy.expandedStateApi36(expandedText));
                    String fake = "Build.VERSION.SDK_INT >= 36 info.setExpandedState(";
                }
            }
        '''
        lexical = java_lexical_code_surface(counterfeit)
        owner = java_named_class_surface(lexical, "OperatorOverlayService")
        method = java_private_void_method_surface(owner, "createOverlay")
        self.assertNotIn("info.setExpandedState(", method)
        self.assertNotIn("Build.VERSION.SDK_INT >= 36", method)


if __name__ == "__main__":
    unittest.main()
