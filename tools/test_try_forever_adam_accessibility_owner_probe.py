#!/usr/bin/env python3

from try_forever_adam_accessibility_owner_probe import classify


def wrap(body: str) -> str:
    return "public class OperatorOverlayService {\n" + body + "\n}\n"


def main() -> int:
    legacy = wrap(
        "private void createOverlay() { adamInput.requestFocus(); }\n"
        "private void submitAdamRequest() { adamInput.announceForAccessibility(\"sent\"); }"
    )
    result = classify(legacy)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"
    assert result["inputResult"]["status"] == "LEGACY_OWNER"

    counterfeit = wrap(
        "// AdamModeSelectionAccessibilityPolicy setSelected setStateDescription\n"
        "private void createOverlay() { String x = \"AdamInputResultAccessibilityPolicy adamInput.setStateDescription\"; }"
    )
    result = classify(counterfeit)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"
    assert result["inputResult"]["status"] == "LEGACY_OWNER"

    mode_partial = wrap(
        "private void createOverlay() { AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate); }"
    )
    result = classify(mode_partial)
    assert result["modeSelection"]["status"] == "PARTIAL_UNSAFE"

    mode_wired = wrap(
        "private void createOverlay() {\n"
        "  AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate);\n"
        "  button.setSelected(true);\n"
        "  button.setStateDescription(state);\n"
        "}"
    )
    result = classify(mode_wired)
    assert result["modeSelection"]["status"] == "SOURCE_WIRED"

    input_partial = wrap(
        "private void submitAdamRequest() { AdamInputResultAccessibilityPolicy.decisionFor(mode, state); }"
    )
    result = classify(input_partial)
    assert result["inputResult"]["status"] == "PARTIAL_UNSAFE"

    input_wired_with_legacy_announcement = wrap(
        "private void submitAdamRequest() {\n"
        "  AdamInputResultAccessibilityPolicy.decisionFor(mode, state);\n"
        "  adamInput.setStateDescription(description);\n"
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
