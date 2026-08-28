#!/usr/bin/env python3
"""Source-only regression for the Adam UI request-admission owner probe.

This test exercises deterministic source classification only. It does not execute Android,
TalkBack, phone/P0 work, request transport, or the staged owner surgery.
"""

from try_forever_adam_accessibility_owner_probe import classify


def wrap(submit_body: str) -> str:
    return (
        "public class OperatorOverlayService {\n"
        "private void createOverlay() { }\n"
        "private Button adamModeButton() { return button; }\n"
        "private void submitAdamRequest() {\n"
        + submit_body
        + "\n}\n}\n"
    )


def main() -> int:
    legacy = classify(wrap(
        "String text = adamInput.getText().toString().trim();\n"
        "if (text.isEmpty()) return;\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert legacy["requestAdmission"]["status"] == "LEGACY_OWNER"

    wrong_order = classify(wrap(
        "CharSequence editable = adamInput.getText();\n"
        "String text = editable.toString().trim();\n"
        "if (!AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)) return;\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert wrong_order["requestAdmission"]["status"] == "PARTIAL_UNSAFE"
    assert "policy-before-materialization ordering" in wrong_order["requestAdmission"]["reason"]

    wired = classify(wrap(
        "CharSequence editable = adamInput.getText();\n"
        "if (!AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)) return;\n"
        "String text = editable.toString().trim();\n"
        "if (text.isEmpty()) return;\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert wired["requestAdmission"]["status"] == "SOURCE_WIRED"
    assert wired["requestAdmission"]["owner_policy_reference"] is True
    assert wired["requestAdmission"]["owner_semantic_state"] is True
    assert wired["schema"] == "try-forever-adam-accessibility-owner-probe.v6"

    counterfeit = classify(wrap(
        "String note = \"AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)\";\n"
        "String text = adamInput.getText().toString().trim();\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert counterfeit["requestAdmission"]["status"] == "LEGACY_OWNER"

    capability = wired["capability"]
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

    print("Adam UI request-admission owner probe ordering: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
