#!/usr/bin/env python3
"""RED source fixture for Adam temporal-custody evidence.

This fixture is intentionally source-only and currently unexecuted. It does not run Android,
TalkBack, phone/P0 work, request transport, or owner surgery.

It pins two independent false-green shapes that probe v9 must eventually reject:
1. admitted editable source can still be mutated by executable work between the canonical
   fail-closed admission guard and detached materialization; and
2. a Send-action Decision can become stale if current mode changes between decisionFor(adamMode)
   and the description write, despite lexical decision->description data flow remaining intact.
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

    stale_send_action = classify(wrap(
        "private void createOverlay() { adamSendButton = button(\"Send\"); refreshAdamSendAction(); }\n"
        "private Button adamModeButton() { refreshAdamSendAction(); return button; }\n"
        "private void refreshAdamSendAction() {\n"
        "  AdamSendActionAccessibilityPolicy.Decision decision = "
        "AdamSendActionAccessibilityPolicy.decisionFor(adamMode);\n"
        "  adamMode = replacementMode;\n"
        "  adamSendButton.setContentDescription(decision.actionDescription);\n"
        "}\n"
        "private void submitAdamRequest() { }"
    ))
    assert stale_send_action["sendAction"]["status"] == "PARTIAL_UNSAFE", (
        "Send-action evidence must reject temporal mode drift between decision and semantic write"
    )

    capability = post_gate_mutation["capability"]
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

    print("Adam temporal-custody hostile source fixture: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
