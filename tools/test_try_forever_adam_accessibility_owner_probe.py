#!/usr/bin/env python3
"""Broad source-only regression for Adam accessibility owner evidence.

Focused request and temporal fixtures carry the exhaustive hostile matrices. This fixture keeps
cross-seam convergence: lexical counterfeits fail, selection requires native 1x5 context, editable
value/result state remain distinct, Send action requires current-mode temporal and lifecycle custody,
and source evidence never promotes TESTED/runtime/phone capability.
"""

from try_forever_adam_accessibility_owner_probe import classify


def wrap(body: str) -> str:
    return "public class OperatorOverlayService {\n" + body + "\n}\n"


def main() -> int:
    legacy = wrap(
        "private void createOverlay() { adamInput.setContentDescription(generic); Button adamSendButton = button(\"Send\"); }\n"
        "private Button adamModeButton() { adamMode = mode; adamInput.requestFocus(); return button; }\n"
        "private void submitAdamRequest() { adamInput.announceForAccessibility(\"sent\"); }"
    )
    result = classify(legacy)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"
    assert result["inputResult"]["status"] == "LEGACY_OWNER"
    assert result["sendAction"]["status"] == "LEGACY_OWNER"
    assert result["requestAdmission"]["status"] == "LEGACY_OWNER"

    counterfeit = wrap(
        "// AdamModeSelectionAccessibilityPolicy AdamInputResultAccessibilityPolicy AdamSendActionAccessibilityPolicy AdamSendAvailabilityAccessibilityPolicy setSelected setStateDescription addTextChangedListener refreshAdamSendAction AccessibilityNodeInfo.CollectionInfo.obtain AccessibilityNodeInfo.CollectionItemInfo.obtain\n"
        "private void createOverlay() { String x = \"AdamInputResultAccessibilityPolicy Transition.EDITED adamInput.addTextChangedListener AdamSendActionAccessibilityPolicy\"; }\n"
        "private Button adamModeButton() { String x = \"AdamModeSelectionAccessibilityPolicy setSelected refreshAdamSendAction\"; return button; }\n"
        "private void submitAdamRequest() { String x = \"AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)\"; }"
    )
    result = classify(counterfeit)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"
    assert result["inputResult"]["status"] == "LEGACY_OWNER"
    assert result["sendAction"]["status"] == "LEGACY_OWNER"
    assert result["requestAdmission"]["status"] == "LEGACY_OWNER"

    wrong_method_counterfeit = wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() { return button; }\n"
        "private void unrelated() { AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate); button.setSelected(true); refreshAdamModeSelection(); AdamSendActionAccessibilityPolicy.decisionFor(mode); adamSendButton.setContentDescription(x); refreshAdamSendAction(); AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable); }\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(wrong_method_counterfeit)
    assert result["modeSelection"]["status"] == "LEGACY_OWNER"
    assert result["sendAction"]["status"] == "LEGACY_OWNER"
    assert result["requestAdmission"]["status"] == "LEGACY_OWNER"

    selected_only = wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() {\n"
        "  AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate);\n"
        "  button.setSelected(true);\n"
        "  refreshAdamModeSelection(); return button;\n"
        "}\n"
        "private void refreshAdamModeSelection() {\n"
        "  AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate);\n"
        "  button.setSelected(true);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(selected_only)
    assert result["modeSelection"]["status"] == "PARTIAL_UNSAFE"
    assert "policy-owned single-selection collection geometry" in result["modeSelection"]["reason"]
    assert "policy-owned per-mode item geometry" in result["modeSelection"]["reason"]

    copied_geometry_is_not_policy_geometry = wrap(
        "private void createOverlay() {\n"
        "  adamModeRow.setAccessibilityDelegate(delegate);\n"
        "  AccessibilityNodeInfo.CollectionInfo.obtain(1, AdamModeSelectionAccessibilityPolicy.SET_SIZE, false, AccessibilityNodeInfo.CollectionInfo.SELECTION_MODE_SINGLE);\n"
        "}\n"
        "private Button adamModeButton() {\n"
        "  AdamModeSelectionAccessibilityPolicy.Decision decision = AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate);\n"
        "  button.setSelected(decision.selected);\n"
        "  button.setAccessibilityDelegate(delegate);\n"
        "  AccessibilityNodeInfo.CollectionItemInfo.obtain(0, 1, decision.positionInSet - 1, 1, false, decision.selected);\n"
        "  refreshAdamModeSelection(); return button;\n"
        "}\n"
        "private void refreshAdamModeSelection() {\n"
        "  AdamModeSelectionAccessibilityPolicy.Decision decision = AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate);\n"
        "  button.setSelected(decision.selected);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(copied_geometry_is_not_policy_geometry)
    assert result["modeSelection"]["status"] == "PARTIAL_UNSAFE"

    mode_wired = wrap(
        "private void createOverlay() {\n"
        "  adamModeRow.setAccessibilityDelegate(delegate);\n"
        "  AccessibilityNodeInfo.CollectionInfo.obtain(AdamModeSelectionAccessibilityPolicy.ROW_COUNT, AdamModeSelectionAccessibilityPolicy.COLUMN_COUNT, false, AccessibilityNodeInfo.CollectionInfo.SELECTION_MODE_SINGLE);\n"
        "}\n"
        "private Button adamModeButton() {\n"
        "  AdamModeSelectionAccessibilityPolicy.Decision decision = AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate);\n"
        "  button.setSelected(decision.selected);\n"
        "  button.setAccessibilityDelegate(delegate);\n"
        "  AccessibilityNodeInfo.CollectionItemInfo.obtain(decision.rowIndex, decision.rowSpan, decision.columnIndex, decision.columnSpan, false, decision.selected);\n"
        "  refreshAdamModeSelection(); return button;\n"
        "}\n"
        "private void refreshAdamModeSelection() {\n"
        "  AdamModeSelectionAccessibilityPolicy.Decision decision = AdamModeSelectionAccessibilityPolicy.decisionFor(active, candidate);\n"
        "  button.setSelected(decision.selected);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(mode_wired)
    assert result["modeSelection"]["status"] == "SOURCE_WIRED"

    input_state_without_edit_recovery = wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() {\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.MODE_SELECTED, false);\n"
        "  applyAdamInputResultState(state); return button;\n"
        "}\n"
        "private void submitAdamRequest() {\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.SUBMIT_SUCCEEDED, false);\n"
        "  applyAdamInputResultState(state);\n"
        "}\n"
        "private void applyAdamInputResultState() {\n"
        "  AdamInputResultAccessibilityPolicy.decisionFor(mode, state);\n"
        "  adamInput.setContentDescription(null); adamInput.setStateDescription(description);\n"
        "}"
    )
    result = classify(input_state_without_edit_recovery)
    assert result["inputResult"]["status"] == "PARTIAL_UNSAFE"

    input_state_that_masks_editable_value = wrap(
        "private void createOverlay() {\n"
        "  adamInput.addTextChangedListener(watcher);\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.EDITED, true);\n"
        "  applyAdamInputResultState(state);\n"
        "}\n"
        "private Button adamModeButton() {\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.MODE_SELECTED, false);\n"
        "  applyAdamInputResultState(state); return button;\n"
        "}\n"
        "private void submitAdamRequest() {\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.SUBMIT_SUCCEEDED, false);\n"
        "  applyAdamInputResultState(state);\n"
        "}\n"
        "private void applyAdamInputResultState() {\n"
        "  AdamInputResultAccessibilityPolicy.decisionFor(mode, state);\n"
        "  adamInput.setContentDescription(generic); adamInput.setStateDescription(description);\n"
        "}"
    )
    result = classify(input_state_that_masks_editable_value)
    assert result["inputResult"]["status"] == "PARTIAL_UNSAFE"

    input_wired_with_legacy_announcement = wrap(
        "private void createOverlay() {\n"
        "  adamInput.addTextChangedListener(watcher);\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.EDITED, true);\n"
        "  applyAdamInputResultState(state);\n"
        "}\n"
        "private Button adamModeButton() {\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.MODE_SELECTED, false);\n"
        "  applyAdamInputResultState(state); return button;\n"
        "}\n"
        "private void submitAdamRequest() {\n"
        "  AdamInputResultAccessibilityPolicy.nextState(state, AdamInputResultAccessibilityPolicy.Transition.SUBMIT_SUCCEEDED, false);\n"
        "  applyAdamInputResultState(state); adamInput.announceForAccessibility(announcement);\n"
        "}\n"
        "private void applyAdamInputResultState() {\n"
        "  AdamInputResultAccessibilityPolicy.decisionFor(mode, state);\n"
        "  adamInput.setContentDescription(null); adamInput.setStateDescription(description);\n"
        "}"
    )
    result = classify(input_wired_with_legacy_announcement)
    assert result["inputResult"]["status"] == "SOURCE_WIRED"

    send_action_binding_counterfeit = wrap(
        "private void createOverlay() { adamSendButton = button(\"Send\"); refreshAdamSendAction(); }\n"
        "private Button adamModeButton() { refreshAdamSendAction(); return button; }\n"
        "private void refreshAdamSendAction() {\n"
        "  String modeSnapshot = adamMode;\n"
        "  AdamSendActionAccessibilityPolicy.Decision ignored = AdamSendActionAccessibilityPolicy.decisionFor(modeSnapshot);\n"
        "  adamSendButton.setContentDescription(stale.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(send_action_binding_counterfeit)
    assert result["sendAction"]["status"] == "PARTIAL_UNSAFE"

    direct_mode_without_snapshot = wrap(
        "private void createOverlay() { adamSendButton = button(\"Send\"); refreshAdamSendAction(); }\n"
        "private Button adamModeButton() { refreshAdamSendAction(); return button; }\n"
        "private void refreshAdamSendAction() {\n"
        "  AdamSendActionAccessibilityPolicy.Decision decision = AdamSendActionAccessibilityPolicy.decisionFor(adamMode);\n"
        "  adamSendButton.setContentDescription(decision.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(direct_mode_without_snapshot)
    assert result["sendAction"]["status"] == "PARTIAL_UNSAFE"

    send_wired = wrap(
        "private void createOverlay() { adamSendButton = button(\"Send\"); refreshAdamSendAction(); }\n"
        "private Button adamModeButton() { adamMode = mode; refreshAdamSendAction(); return button; }\n"
        "private void refreshAdamSendAction() {\n"
        "  String modeSnapshot = adamMode;\n"
        "  AdamSendActionAccessibilityPolicy.Decision decision = AdamSendActionAccessibilityPolicy.decisionFor(modeSnapshot);\n"
        "  adamSendButton.setText(decision.visibleLabel);\n"
        "  adamSendButton.setContentDescription(decision.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(send_wired)
    assert result["sendAction"]["status"] == "SOURCE_WIRED"

    request_wired = wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() { return button; }\n"
        "private void submitAdamRequest() {\n"
        "  CharSequence editable = adamInput.getText();\n"
        "  if (!AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)) return;\n"
        "  String text = editable.toString().trim();\n"
        "  OperatorState.submitAdamRequest(this, adamMode, text, now);\n"
        "}"
    )
    result = classify(request_wired)
    assert result["requestAdmission"]["status"] == "SOURCE_WIRED"

    assert result["schema"] == "try-forever-adam-accessibility-owner-probe.v11"
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

    print("Adam accessibility owner evidence boundaries v11: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
