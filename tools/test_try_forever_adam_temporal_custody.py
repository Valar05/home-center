#!/usr/bin/env python3
"""Source-only regression for Adam temporal-custody evidence.

This fixture exercises deterministic source classification only. It does not run Android,
TalkBack, phone/P0 work, request transport, or owner surgery.

It pins four independent temporal custody failures and their positive counterparts:
1. admitted mutable Editable source cannot have executable work between canonical admission
   and detached materialization;
2. Send-action semantics must derive from one current-mode snapshot with no intervening owner
   mutation or arbitrary executable work before the action description is written;
3. the persistent Send owner must exist before createOverlay refreshes its semantics; and
4. a mode mutation must occur before the mode-change path refreshes Send semantics.

The last two cases are intentionally RED against owner-probe v10. Their existence demotes the
optimistic Send-action evidence label until the existing probe is repaired; source presence is
not regression execution or TESTED capability.
"""

from try_forever_adam_accessibility_owner_probe import classify


def wrap(body: str) -> str:
    return "public class OperatorOverlayService {\n" + body + "\n}\n"


def main() -> int:
    post_gate_mutation = classify(wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() { return button; }\n"
        "private void submitAdamRequest() {\n"
        "  CharSequence editable = adamInput.getText();\n"
        "  if (!AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)) return;\n"
        "  mutateAdamInputAfterAdmission();\n"
        "  String text = editable.toString().trim();\n"
        "  OperatorState.submitAdamRequest(this, adamMode, text, now);\n"
        "}"
    ))
    assert post_gate_mutation["requestAdmission"]["status"] == "PARTIAL_UNSAFE", (
        "request evidence must reject executable work between admission and materialization; "
        "an aliased Editable can change after the policy decision"
    )
    assert "immediate materialization after canonical admission" in (
        post_gate_mutation["requestAdmission"]["reason"]
    )

    request_wired = classify(wrap(
        "private void createOverlay() { }\n"
        "private Button adamModeButton() { return button; }\n"
        "private void submitAdamRequest() {\n"
        "  CharSequence editable = adamInput.getText();\n"
        "  if (!AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)) return;\n"
        "  String text = editable.toString().trim();\n"
        "  if (text.isEmpty()) return;\n"
        "  OperatorState.submitAdamRequest(this, adamMode, text, now);\n"
        "}"
    ))
    assert request_wired["requestAdmission"]["status"] == "SOURCE_WIRED"

    stale_send_action = classify(wrap(
        "private void createOverlay() { adamSendButton = button(\"Send\"); refreshAdamSendAction(); }\n"
        "private Button adamModeButton() { refreshAdamSendAction(); return button; }\n"
        "private void refreshAdamSendAction() {\n"
        "  String modeSnapshot = adamMode;\n"
        "  AdamSendActionAccessibilityPolicy.Decision decision = "
        "AdamSendActionAccessibilityPolicy.decisionFor(modeSnapshot);\n"
        "  adamMode = replacementMode;\n"
        "  adamSendButton.setContentDescription(decision.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    ))
    assert stale_send_action["sendAction"]["status"] == "PARTIAL_UNSAFE", (
        "Send-action evidence must reject temporal mode drift between decision and semantic write"
    )

    arbitrary_send_work = classify(wrap(
        "private void createOverlay() { adamSendButton = button(\"Send\"); refreshAdamSendAction(); }\n"
        "private Button adamModeButton() { refreshAdamSendAction(); return button; }\n"
        "private void refreshAdamSendAction() {\n"
        "  String modeSnapshot = adamMode;\n"
        "  AdamSendActionAccessibilityPolicy.Decision decision = "
        "AdamSendActionAccessibilityPolicy.decisionFor(modeSnapshot);\n"
        "  auditCurrentAction();\n"
        "  adamSendButton.setContentDescription(decision.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    ))
    assert arbitrary_send_work["sendAction"]["status"] == "PARTIAL_UNSAFE"

    create_refresh_before_owner = classify(wrap(
        "private void createOverlay() {\n"
        "  refreshAdamSendAction();\n"
        "  adamSendButton = button(\"Send\");\n"
        "}\n"
        "private Button adamModeButton() {\n"
        "  adamMode = mode;\n"
        "  refreshAdamSendAction();\n"
        "  return button;\n"
        "}\n"
        "private void refreshAdamSendAction() {\n"
        "  String modeSnapshot = adamMode;\n"
        "  AdamSendActionAccessibilityPolicy.Decision decision = "
        "AdamSendActionAccessibilityPolicy.decisionFor(modeSnapshot);\n"
        "  adamSendButton.setContentDescription(decision.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    ))
    assert create_refresh_before_owner["sendAction"]["status"] == "PARTIAL_UNSAFE", (
        "Send-action evidence must reject createOverlay refresh before persistent Send owner assignment"
    )

    mode_refresh_before_mutation = classify(wrap(
        "private void createOverlay() {\n"
        "  adamSendButton = button(\"Send\");\n"
        "  refreshAdamSendAction();\n"
        "}\n"
        "private Button adamModeButton() {\n"
        "  refreshAdamSendAction();\n"
        "  adamMode = mode;\n"
        "  return button;\n"
        "}\n"
        "private void refreshAdamSendAction() {\n"
        "  String modeSnapshot = adamMode;\n"
        "  AdamSendActionAccessibilityPolicy.Decision decision = "
        "AdamSendActionAccessibilityPolicy.decisionFor(modeSnapshot);\n"
        "  adamSendButton.setContentDescription(decision.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    ))
    assert mode_refresh_before_mutation["sendAction"]["status"] == "PARTIAL_UNSAFE", (
        "Send-action evidence must reject semantic refresh that precedes the mode mutation it claims to expose"
    )

    send_wired = classify(wrap(
        "private void createOverlay() { adamSendButton = button(\"Send\"); refreshAdamSendAction(); }\n"
        "private Button adamModeButton() { adamMode = mode; refreshAdamSendAction(); return button; }\n"
        "private void refreshAdamSendAction() {\n"
        "  String modeSnapshot = adamMode;\n"
        "  AdamSendActionAccessibilityPolicy.Decision decision = "
        "AdamSendActionAccessibilityPolicy.decisionFor(modeSnapshot);\n"
        "  adamSendButton.setText(decision.visibleLabel);\n"
        "  adamSendButton.setContentDescription(decision.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    ))
    assert send_wired["sendAction"]["status"] == "SOURCE_WIRED"

    assert send_wired["schema"] == "try-forever-adam-accessibility-owner-probe.v10"
    capability = send_wired["capability"]
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

    print("Adam temporal-custody source regression: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
