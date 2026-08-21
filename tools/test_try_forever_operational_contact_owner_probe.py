#!/usr/bin/env python3

from try_forever_operational_contact_owner_probe import classify


def wrap(body: str) -> str:
    return "public class OperatorOverlayService {\n" + body + "\n}\n"


def main() -> int:
    legacy = wrap(
        "private void refreshUi() { status.setText(state); refreshHeartbeatLights(false, true, false); }\n"
        "private void applyHeartbeatCollapsedOwnerAccessibility() { dragHandle.setContentDescription(HeartbeatCollapsedOwnerAccessibility.contentDescription(collapsed, model)); }\n"
        "private void createOverlay() { Button adamSendButton = button(\"Send\"); }\n"
        "private Button adamModeButton() { return button; }\n"
        "private void submitAdamRequest() { String text = adamInput.getText().toString().trim(); if (text.isEmpty()) return; }"
    )
    result = classify(legacy)
    assert result["collapsedOperationalRefresh"]["status"] == "PARTIAL_UNSAFE"
    assert result["adamSendAvailability"]["status"] == "LEGACY_OWNER"

    collapsed_wired = wrap(
        "private void refreshUi() { status.setText(state); applyHeartbeatCollapsedOwnerAccessibility(currentHeartbeatModel()); refreshHeartbeatLights(false, true, false); }\n"
        "private void applyHeartbeatCollapsedOwnerAccessibility() {\n"
        "  String operatorStatus = status == null ? \"\" : status.getText().toString();\n"
        "  String next = HeartbeatCollapsedOwnerAccessibility.contentDescription(collapsed, operatorStatus, model);\n"
        "  if (!TextUtils.equals(dragHandle.getContentDescription(), next)) dragHandle.setContentDescription(next);\n"
        "}\n"
        "private void createOverlay() { Button adamSendButton = button(\"Send\"); }\n"
        "private Button adamModeButton() { return button; }\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(collapsed_wired)
    assert result["collapsedOperationalRefresh"]["status"] == "SOURCE_WIRED"

    collapsed_without_owner_refresh = wrap(
        "private void refreshUi() { status.setText(state); refreshHeartbeatLights(false, true, false); }\n"
        "private void applyHeartbeatCollapsedOwnerAccessibility() {\n"
        "  String operatorStatus = status.getText().toString();\n"
        "  String next = HeartbeatCollapsedOwnerAccessibility.contentDescription(collapsed, operatorStatus, model);\n"
        "  if (!TextUtils.equals(dragHandle.getContentDescription(), next)) dragHandle.setContentDescription(next);\n"
        "}\n"
        "private void createOverlay() { }\n"
        "private Button adamModeButton() { return button; }\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(collapsed_without_owner_refresh)
    assert result["collapsedOperationalRefresh"]["status"] == "PARTIAL_UNSAFE"
    assert "SKIP_UNCHANGED" in result["collapsedOperationalRefresh"]["reason"]

    adam_partial = wrap(
        "private void refreshUi() { }\n"
        "private void applyHeartbeatCollapsedOwnerAccessibility() { }\n"
        "private void createOverlay() { adamSendButton = button(\"Send\"); adamInput.addTextChangedListener(watcher); refreshAdamSendAvailability(); }\n"
        "private Button adamModeButton() { return button; }\n"
        "private void refreshAdamSendAvailability() {\n"
        "  AdamSendAvailabilityAccessibilityPolicy.Decision d = AdamSendAvailabilityAccessibilityPolicy.decisionFor(mode, value);\n"
        "  adamSendButton.setEnabled(d.enabled);\n"
        "  adamSendButton.setContentDescription(d.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(adam_partial)
    assert result["adamSendAvailability"]["status"] == "PARTIAL_UNSAFE"
    assert "editable-value refresh" in result["adamSendAvailability"]["reason"]
    assert "mode-change refresh" in result["adamSendAvailability"]["reason"]

    adam_wired = wrap(
        "private void refreshUi() { }\n"
        "private void applyHeartbeatCollapsedOwnerAccessibility() { }\n"
        "private void createOverlay() {\n"
        "  adamSendButton = button(\"Send\");\n"
        "  adamInput.addTextChangedListener(new TextWatcher() {\n"
        "    public void onTextChanged(CharSequence value, int start, int before, int count) { refreshAdamSendAvailability(); }\n"
        "  });\n"
        "  refreshAdamSendAvailability();\n"
        "}\n"
        "private Button adamModeButton() { refreshAdamSendAvailability(); return button; }\n"
        "private void refreshAdamSendAvailability() {\n"
        "  AdamSendAvailabilityAccessibilityPolicy.Decision d = AdamSendAvailabilityAccessibilityPolicy.decisionFor(adamMode, adamInput.getText());\n"
        "  adamSendButton.setEnabled(d.enabled);\n"
        "  adamSendButton.setContentDescription(d.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    )
    result = classify(adam_wired)
    assert result["adamSendAvailability"]["status"] == "SOURCE_WIRED"

    capability = result["capability"]
    assert result["schema"] == "try-forever-operational-contact-owner-probe.v1"
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

    print("Operational contact owner evidence boundaries: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
