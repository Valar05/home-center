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


def test_latest_dynamic_text_is_not_masked_by_static_content_description() -> None:
    code_surface = java_lexical_code_surface(OWNER.read_text(encoding="utf-8"))
    owner_surface = java_named_class_surface(code_surface, "OperatorOverlayService")
    assert owner_surface, "missing named OperatorOverlayService class"
    create_overlay = java_private_void_method_surface(owner_surface, "createOverlay")
    assert create_overlay, "missing direct owner method: createOverlay"

    assert "latest = textView(14f, false);" in create_overlay
    assert "latest.setText(OperatorState.latestText(this));" in create_overlay
    assert "latest.setOnClickListener" in create_overlay
    assert "latest.setContentDescription(null);" in create_overlay, (
        "ACCESSIBILITY WOUND: latest is a dynamic TextView, but a non-null "
        "contentDescription can replace the actual Home Center message as the "
        "screen-reader semantic value"
    )
