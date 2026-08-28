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


def _owner_method_surface(method_name: str) -> str:
    code_surface = java_lexical_code_surface(OWNER.read_text(encoding="utf-8"))
    owner_surface = java_named_class_surface(code_surface, "OperatorOverlayService")
    assert owner_surface, "missing named OperatorOverlayService class"
    method = java_private_void_method_surface(owner_surface, method_name)
    assert method, f"missing direct owner method: {method_name}"
    return method


def test_latest_message_preserves_text_value_and_exposes_interaction_semantics() -> None:
    create_overlay = _owner_method_surface("createOverlay")

    assert "latest.setContentDescription(null);" in create_overlay, (
        "ACCESSIBILITY REGRESSION: the changing latest-message text must remain the "
        "native TextView semantic value"
    )
    assert "latest.setAccessibilityDelegate" in create_overlay, (
        "ACCESSIBILITY WOUND: clickable latest-message text has no explicit source "
        "surface for expand/collapse accessibility action semantics"
    )
    assert "LatestMessageAccessibilityPolicy.clickActionLabel(expandedText)" in create_overlay
    assert "AccessibilityNodeInfo.AccessibilityAction.ACTION_CLICK.getId()" in create_overlay
    assert "latest.announceForAccessibility" not in create_overlay, (
        "ACCESSIBILITY REGRESSION: a simple expand/collapse action should use semantic "
        "state/action instead of a forced accessibility announcement"
    )


def test_latest_message_state_stays_synchronized_for_click_and_programmatic_collapse() -> None:
    create_overlay = _owner_method_surface("createOverlay")
    apply_expanded = _owner_method_surface("applyExpandedTextState")
    set_collapsed = _owner_method_surface("setCollapsed")

    assert "expandedText = !expandedText;" in create_overlay
    assert "applyExpandedTextState();" in create_overlay

    assert "Build.VERSION.SDK_INT >= Build.VERSION_CODES.R" in apply_expanded
    assert "latest.setStateDescription(" in apply_expanded, (
        "ACCESSIBILITY WOUND: expanded/collapsed state must be synchronized in the "
        "shared presentation-state owner, not only in the click callback"
    )
    assert "LatestMessageAccessibilityPolicy.stateDescription(expandedText)" in apply_expanded
    assert "latest.announceForAccessibility" not in apply_expanded

    assert "expandedText = false;" in set_collapsed, (
        "REGRESSION PRECONDITION: panel collapse must reset expanded latest-message state"
    )
    assert "applyExpandedTextState();" in set_collapsed, (
        "ACCESSIBILITY REGRESSION: programmatic collapse must flow through the same "
        "semantic state synchronization path as direct clicks"
    )
