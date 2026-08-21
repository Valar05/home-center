#!/usr/bin/env python3

from try_forever_adam_accessibility_owner_probe import classify


def wrap(body: str) -> str:
    return "public class OperatorOverlayService {\n" + body + "\n}\n"


def main() -> int:
    legacy = wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() { adamMode = mode; adamInput.requestFocus(); return button; }\n"
        "private void submitAdamRequest() { adamInput.announceForAccessibility(\"sent\"); }"
    )
    result = classify(legacy)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"
    assert result["inputResult"]["status"] == "LEGACY_OWNER"

    counterfeit = wrap(
        "// AdamModeSelectionAccessibilityPolicy setSelected setStateDescription addTextChangedListener\n"
        "private void createOverlay() { String x = \"AdamInputResultAccessibilityPolicy Transition.EDITED adamInput.addTextChangedListener applyAdamInputResultState\"; }\n"
        "private Button adamModeButton() { String x = \"AdamInputResultAccessibilityPolicy setSelected setStateDescription\"; return button; }\n"
        "private void submitAdamRequest() { String x = \"AdamInputResultAccessibilityPolicy adamInput.setStateDescription\"; }"
    )
    result = classify(counterfeit)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"
    assert result["inputResult"]["status"] == "LEGACY_OWNER"

    wrong_method_counterfeit = wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() { return button; }\n"
        "private void unrelated() { AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate); button.setSelected(true); refreshAdamModeSelection(); }\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(wrong_method_counterfeit)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"

    mode_partial = wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() { AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate); button.setSelected(true); return button; }\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(mode_partial)
    assert result["modeSelection"]["status"] == "PARTIAL_UNSAFE"

    mode_wired = wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() {\n"
        "  AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate);\n"
        "  button.setSelected(true);\n"
        "  refreshAdamModeSelection();\n"
        "  return button;\n"
        "}\n"
        "private void refreshAdamModeSelection() {\n"
        "  AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate);\n"
        "  button.setSelected(true);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(mode_wired)
    assert result["modeSelection"]["status"] == "SOURCE_WIRED"

    input_state_without_edit_recovery = wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() {\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.MODE_SELECTED, false);\n"
        "  applyAdamInputResultState(state);\n"
        "  return button;\n"
        "}\n"
        "private void submitAdamRequest() {\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.SUBMIT_SUCCEEDED, false);\n"
        "  applyAdamInputResultState(state);\n"
        "}\n"
        "private void applyAdamInputResultState() {\n"
        "  AdamInputResultAccessibilityPolicy.decisionFor(mode, state);\n"
        "  adamInput.setContentDescription(null);\n"
        "  adamInput.setStateDescription(description);\n"
        "}"
    )
    result = classify(input_state_without_edit_recovery)
    assert result["inputResult"]["status"] == "PARTIAL_UNSAFE"

    input_wired_with_legacy_announcement = wrap(
        "private void createOverlay() {\n"
        "  adamInput.addTextChangedListener(watcher);\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.EDITED, true);\n"
        "  applyAdamInputResultState(state);\n"
        "}\n"
        "private Button adamModeButton() {\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.MODE_SELECTED, false);\n"
        "  applyAdamInputResultState(state);\n"
        "  return button;\n"
        "}\n"
        "private void submitAdamRequest() {\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.SUBMIT_SUCCEEDED, false);\n"
        "  applyAdamInputResultState(state);\n"
        "  adamInput.announceForAccessibility(announcement);\n"
        "}\n"
        "private void applyAdamInputResultState() {\n"
        "  AdamInputResultAccessibilityPolicy.decisionFor(mode, state);\n"
        "  adamInput.setContentDescription(null);\n"
        "  adamInput.setStateDescription(description);\n"
        "}"
    )
    result = classify(input_wired_with_legacy_announcement)
    assert result["inputResult"]["status"] == "SOURCE_WIRED"

    capability = result["capability"]
    assert result["schema"] == "try-forever-adam-accessibility-owner-probe.v3"
    assert capability["sourceInspection"] is True
    for key in (
        "regressionExecuted",
        "tested",
        "runtimeUi",
        "runtimeTalkBack",
        "deployed",
        "phoneDelivered",
        "accepted",
    ):
        assert capability[key] is False

    print("Adam accessibility owner evidence boundaries: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
