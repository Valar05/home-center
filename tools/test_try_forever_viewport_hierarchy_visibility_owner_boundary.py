from __future__ import annotations

from pathlib import Path

from tools.try_forever_operator_accessibility_owner_probe import java_lexical_code_surface


OWNER = Path(
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
)


def _method_body(code_surface: str, signature: str) -> str:
    start = code_surface.find(signature)
    assert start >= 0, f"missing owner method: {signature}"
    brace = code_surface.find("{", start)
    assert brace >= 0, f"missing method body: {signature}"
    depth = 0
    for index in range(brace, len(code_surface)):
        char = code_surface[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return code_surface[brace + 1 : index]
    raise AssertionError(f"unterminated owner method: {signature}")


def _owner_code_surface() -> str:
    return java_lexical_code_surface(OWNER.read_text(encoding="utf-8"))


def test_visible_viewport_contact_requires_effective_hierarchy_visibility_before_geometry() -> None:
    source = _owner_code_surface()
    body = _method_body(
        source,
        "private boolean heartbeatHasVisibleViewportContact(View control)",
    )

    geometry_call = "HeartbeatViewportRestorePolicy.hasVisibleViewportContact("
    geometry_index = body.find(geometry_call)
    assert geometry_index >= 0, "existing bounded horizontal geometry organ disappeared"

    accepted_visibility_markers = (
        "control.isShown()",
        "heartbeatIsEffectivelyShown(control)",
        "heartbeatIsEffectivelyVisible(control)",
    )
    marker_positions = [
        body.find(marker) for marker in accepted_visibility_markers if body.find(marker) >= 0
    ]
    assert marker_positions, (
        "PARTIAL_UNSAFE: owner calls horizontal intersection without proving the "
        "heartbeat control is effectively visible through its Android ancestor hierarchy"
    )
    assert min(marker_positions) < geometry_index, (
        "effective hierarchy visibility must be admitted before horizontal geometry is "
        "promoted to visible viewport contact"
    )


def test_hidden_details_ancestor_is_a_real_owner_state_not_a_hypothetical_fixture() -> None:
    source = _owner_code_surface()
    presentation = _method_body(source, "private void applyPresentationState()")
    assert "details.setVisibility(collapsed ? View.GONE : View.VISIBLE)" in presentation
