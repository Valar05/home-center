from __future__ import annotations

from pathlib import Path

from tools.try_forever_operator_accessibility_owner_probe import (
    java_lexical_code_surface,
    java_named_class_surface,
    java_private_void_method_surface,
)


OWNER = Path(
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
)


def _create_overlay_surface() -> str:
    code_surface = java_lexical_code_surface(OWNER.read_text(encoding="utf-8"))
    owner_surface = java_named_class_surface(code_surface, "OperatorOverlayService")
    assert owner_surface, "missing named OperatorOverlayService class"
    create_overlay = java_private_void_method_surface(owner_surface, "createOverlay")
    assert create_overlay, "missing direct owner method: createOverlay"
    return create_overlay


def test_latest_message_preserves_text_value_and_exposes_interaction_semantics() -> None:
    create_overlay = _create_overlay_surface()

    assert "latest.setContentDescription(null);" in create_overlay, (
        "ACCESSIBILITY REGRESSION: the changing latest-message text must remain the "
        "native TextView semantic value"
    )
    assert "latest.setAccessibilityDelegate" in create_overlay, (
        "ACCESSIBILITY WOUND: clickable latest-message text has no explicit source "
        "surface for expand/collapse accessibility action/state semantics"
    )
    assert "LatestMessageAccessibilityPolicy.clickActionLabel(expandedText)" in create_overlay
    assert "AccessibilityNodeInfo.AccessibilityAction.ACTION_CLICK.getId()" in create_overlay
    assert "LatestMessageAccessibilityPolicy.stateDescription(expandedText)" in create_overlay
    assert "Build.VERSION.SDK_INT >= Build.VERSION_CODES.R" in create_overlay


def test_latest_message_click_confirmation_honors_mute_contract() -> None:
    create_overlay = _create_overlay_surface()

    assert "LatestMessageAccessibilityPolicy.confirmationAnnouncement(expandedText)" in create_overlay
    assert "!OperatorState.muted(this)" in create_overlay, (
        "ACCESSIBILITY WOUND: explicit expand/collapse confirmation must not bypass "
        "the overlay's existing mute contract"
    )
    assert "latest.announceForAccessibility" in create_overlay
