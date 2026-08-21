from __future__ import annotations

from pathlib import Path


OWNER = Path(
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
)


def _method_body(source: str, signature: str) -> str:
    start = source.find(signature)
    assert start >= 0, f"missing owner method: {signature}"
    brace = source.find("{", start)
    assert brace >= 0, f"missing method body: {signature}"
    depth = 0
    for index in range(brace, len(source)):
        char = source[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return source[brace + 1 : index]
    raise AssertionError(f"unterminated owner method: {signature}")


def test_latest_dynamic_text_is_not_masked_by_static_content_description() -> None:
    source = OWNER.read_text(encoding="utf-8")
    create_overlay = _method_body(source, "private void createOverlay()")

    assert "latest = textView(14f, false);" in create_overlay
    assert "latest.setText(OperatorState.latestText(this));" in create_overlay
    assert "latest.setOnClickListener" in create_overlay
    assert "latest.setContentDescription(null);" in create_overlay, (
        "ACCESSIBILITY WOUND: latest is a dynamic TextView, but a static contentDescription "
        "can replace the actual Home Center message as the screen-reader semantic value"
    )
    assert "Latest Home Center or Adam message. Tap to expand or collapse text." not in create_overlay
