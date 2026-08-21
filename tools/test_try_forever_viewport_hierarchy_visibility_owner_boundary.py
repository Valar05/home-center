from __future__ import annotations

import re
from pathlib import Path

from tools.try_forever_operator_accessibility_owner_probe import (
    java_lexical_code_surface,
    java_named_class_surface,
    java_private_void_method_surface,
)


OWNER = Path(
    "android/operator-overlay/app/src/main/java/com/homecenter/operatoroverlay/OperatorOverlayService.java"
)


def _private_boolean_method_surface(class_surface: str, method_name: str) -> str:
    declaration = re.compile(rf"\bprivate\s+boolean\s+{re.escape(method_name)}\s*\(")
    depth = 0
    index = 0
    while index < len(class_surface):
        char = class_surface[index]
        if char == "{":
            depth += 1
            index += 1
            continue
        if char == "}":
            depth = max(0, depth - 1)
            index += 1
            continue
        if depth != 1:
            index += 1
            continue
        match = declaration.match(class_surface, index)
        if match is None:
            index += 1
            continue
        open_brace = class_surface.find("{", match.end())
        assert open_brace >= 0, f"missing method body: {method_name}"
        method_depth = 0
        for end in range(open_brace, len(class_surface)):
            method_char = class_surface[end]
            if method_char == "{":
                method_depth += 1
            elif method_char == "}":
                method_depth -= 1
                if method_depth == 0:
                    return class_surface[match.start() : end + 1]
        raise AssertionError(f"unterminated owner method: {method_name}")
    return ""


def _owner_surface() -> str:
    code_surface = java_lexical_code_surface(OWNER.read_text(encoding="utf-8"))
    owner_surface = java_named_class_surface(code_surface, "OperatorOverlayService")
    assert owner_surface, "missing named OperatorOverlayService class"
    return owner_surface


def test_visible_viewport_contact_requires_effective_hierarchy_visibility_before_geometry() -> None:
    owner_surface = _owner_surface()
    body = _private_boolean_method_surface(owner_surface, "heartbeatHasVisibleViewportContact")
    assert body, "missing direct owner method: heartbeatHasVisibleViewportContact"

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
    owner_surface = _owner_surface()
    presentation = java_private_void_method_surface(owner_surface, "applyPresentationState")
    assert presentation, "missing direct owner method: applyPresentationState"
    assert "details.setVisibility(collapsed ? View.GONE : View.VISIBLE)" in presentation
