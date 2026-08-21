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


def _refresh_ui_surface() -> str:
    code_surface = java_lexical_code_surface(OWNER.read_text(encoding="utf-8"))
    owner = java_named_class_surface(code_surface, "OperatorOverlayService")
    assert owner, "missing named OperatorOverlayService class"
    refresh_ui = java_private_void_method_surface(owner, "refreshUi")
    assert refresh_ui, "missing direct owner method: refreshUi"
    return refresh_ui


def test_full_text_action_buttons_expose_the_exact_current_action() -> None:
    refresh_ui = _refresh_ui_surface()

    assert 'muteButton.setText(muted ? "Unmute speech" : "Mute speech");' in refresh_ui
    assert 'muteButton.setContentDescription(muted ? "Unmute speech" : "Mute speech");' in refresh_ui, (
        "ACCESSIBILITY WOUND: muteButton text changes with the current action while its "
        "semantic description remains generic"
    )

    assert "controlButton.setText(fullControlLabel);" in refresh_ui
    assert "controlButton.setContentDescription(fullControlLabel);" in refresh_ui, (
        "ACCESSIBILITY WOUND: full control action changes among Enable, Disable, and "
        "Confirm disable while its semantic description remains generic"
    )


def test_compact_control_button_exposes_exact_full_current_action() -> None:
    refresh_ui = _refresh_ui_surface()

    assert "compactControlButton.setText(compactControlLabel);" in refresh_ui
    assert "compactControlButton.setContentDescription(fullControlLabel);" in refresh_ui, (
        "ACCESSIBILITY WOUND: compact STOP/ENABLE/CONFIRM text needs the exact full "
        "current action as its semantic description"
    )
    assert 'fullControlLabel = "Confirm disable";' in refresh_ui, (
        "SAFETY REGRESSION: confirm-disable must remain a distinct action state"
    )
