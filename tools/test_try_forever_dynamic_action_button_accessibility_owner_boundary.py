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


def _owner_methods() -> tuple[str, str]:
    code_surface = java_lexical_code_surface(OWNER.read_text(encoding="utf-8"))
    owner = java_named_class_surface(code_surface, "OperatorOverlayService")
    assert owner, "missing named OperatorOverlayService class"
    create_overlay = java_private_void_method_surface(owner, "createOverlay")
    refresh_ui = java_private_void_method_surface(owner, "refreshUi")
    assert create_overlay, "missing direct owner method: createOverlay"
    assert refresh_ui, "missing direct owner method: refreshUi"
    return create_overlay, refresh_ui


def test_full_text_action_buttons_do_not_hide_current_action_with_generic_description() -> None:
    create_overlay, refresh_ui = _owner_methods()

    assert 'muteButton.setText(muted ? "Unmute speech" : "Mute speech");' in refresh_ui
    assert "controlButton.setText(fullControlLabel);" in refresh_ui

    assert "muteButton.setContentDescription(null);" in create_overlay, (
        "ACCESSIBILITY WOUND: muteButton has current action text but a static generic "
        "contentDescription can mask whether the current action is Mute or Unmute"
    )
    assert "controlButton.setContentDescription(null);" in create_overlay, (
        "ACCESSIBILITY WOUND: full control button text changes among Enable, Disable, "
        "and Confirm disable, but a generic static contentDescription can hide that state"
    )


def test_compact_control_button_exposes_exact_full_current_action() -> None:
    _create_overlay, refresh_ui = _owner_methods()

    assert "compactControlButton.setText(compactControlLabel);" in refresh_ui
    assert "compactControlButton.setContentDescription(fullControlLabel);" in refresh_ui, (
        "ACCESSIBILITY WOUND: compact STOP/ENABLE/CONFIRM text needs the exact full "
        "current action as its semantic description"
    )
    assert 'fullControlLabel = "Confirm disable";' in refresh_ui, (
        "SAFETY REGRESSION: confirm-disable must remain a distinct action state"
    )
