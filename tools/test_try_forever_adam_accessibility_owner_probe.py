#!/usr/bin/env python3

from try_forever_adam_accessibility_owner_probe import classify


def wrap(body: str) -> str:
    return "public class OperatorOverlayService {\n" + body + "\n}\n"


def main() -> int:
    legacy = wrap(
        "private Button adamModeButton() { adamMode = mode; adamInput.requestFocus(); return button; }\n"
        "private void submitAdamRequest() { adamInput.announceForAccessibility(\"sent\"); }"
    )
    result = classify(legacy)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"
    assert result["inputResult"]["status"] == "LEGACY_OWNER"

    counterfeit = wrap(
        "// AdamModeSelectionAccessibilityPolicy setSelected setStateDescription\n"
        "private Button adamModeButton() { String x = \"AdamInputResultAccessibilityPolicy setSelected setStateDescription\"; return button; }\n"
        "private void submitAdamRequest() { String x = \"AdamInputResultAccessibilityPolicy adamInput.setStateDescription\"; }"
    )
    result = classify(counterfeit)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"
    assert result["inputResult"]["status"] == "LEGACY_OWNER"

    wrong_method_counterfeit = wrap(
        "private Button adamModeButton() { return button; }\n"
        "private void unrelated() { AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate); button.setSelected(true); button.setStateDescription(state); }\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(wrong_method_counterfeit)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"

    mode_partial = wrap(
        "private Button adamModeButton() { AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate); return button; }\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(mode_partial)
    assert result["modeSelection"]["status"] == "PARTIAL_UNSAFE"

    mode_wired = wrap(
        "private Button adamModeButton() {\n"
        "  AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate);\n"
        "  button.setSelected(true);\n"
        "  button.setStateDescription(state);\n"
        "  return button;\n"
        "}\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(mode_wired)
    assert result["modeSelection"]["status"] == "SOURCE_WIRED"

    input_partial = wrap(
        "private Button adamModeButton() { AdamInputResultAccessibilityPolicy.decisionFor(mode, ready); return button; }\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(input_partial)
    assert result["inputResult"]["status"] == "PARTIAL_UNSAFE"

    input_wired_with_legacy_announcement = wrap(
        "private Button adamModeButton() {\n"
        "  AdamInputResultAccessibilityPolicy.decisionFor(mode, ready);\n"
        "  adamInput.setStateDescription(readyDescription);\n"
        "  return button;\n"
        "}\n"
        "private void submitAdamRequest() {\n"
        "  AdamInputResultAccessibilityPolicy.decisionFor(mode, sent);\n"
        "  adamInput.setStateDescription(sentDescription);\n"
        "  adamInput.announceForAccessibility(announcement);\n"
        "}"
    )
    result = classify(input_wired_with_legacy_announcement)
    assert result["inputResult"]["status"] == "SOURCE_WIRED"

    capability = result["capability"]
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
