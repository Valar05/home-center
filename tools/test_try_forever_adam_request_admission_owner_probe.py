#!/usr/bin/env python3
"""Source-only regression for the Adam UI request-admission owner probe.

This test exercises deterministic source classification only. It does not execute Android,
TalkBack, phone/P0 work, request transport, or the staged owner surgery.

The hostile cases pin policy custody plus single-observation and control-flow custody: a consumer
must not earn SOURCE_WIRED from a shadow helper, an ignored canonical policy call, or by observing
the editable source, request-admission policy, or whole-source materialization more than once.
Probe v7 rejects those counterfeit shapes as PARTIAL_UNSAFE; this fixture remains source only until
an execution lane supplies a test receipt.
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
    assert wired["schema"] == "try-forever-adam-accessibility-owner-probe.v7"

    counterfeit_literal = classify(wrap(
        "String note = \"AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)\";\n"
        "String text = adamInput.getText().toString().trim();\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert counterfeit_literal["requestAdmission"]["status"] == "LEGACY_OWNER"

    shadow_gate = classify(wrap(
        "CharSequence editable = adamInput.getText();\n"
        "if (!hasMaterialRequest(editable)) return;\n"
        "String text = editable.toString().trim();\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert shadow_gate["requestAdmission"]["status"] == "PARTIAL_UNSAFE"
    assert shadow_gate["requestAdmission"]["owner_policy_reference"] is False
    assert "canonical fully-qualified fail-closed request-admission policy guard" in (
        shadow_gate["requestAdmission"]["reason"]
    )

    other_owner_gate = classify(wrap(
        "CharSequence editable = adamInput.getText();\n"
        "if (!OtherAvailabilityPolicy.hasMaterialRequest(editable)) return;\n"
        "String text = editable.toString().trim();\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert other_owner_gate["requestAdmission"]["status"] == "PARTIAL_UNSAFE"
    assert other_owner_gate["requestAdmission"]["owner_policy_reference"] is False

    ignored_canonical_call = classify(wrap(
        "CharSequence editable = adamInput.getText();\n"
        "AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable);\n"
        "String text = editable.toString().trim();\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert ignored_canonical_call["requestAdmission"]["status"] == "PARTIAL_UNSAFE"
    assert ignored_canonical_call["requestAdmission"]["owner_policy_reference"] is False
    assert "fail-closed request-admission policy guard" in (
        ignored_canonical_call["requestAdmission"]["reason"]
    )

    observed_but_unenforced = classify(wrap(
        "CharSequence editable = adamInput.getText();\n"
        "boolean admitted = AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable);\n"
        "String text = editable.toString().trim();\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert observed_but_unenforced["requestAdmission"]["status"] == "PARTIAL_UNSAFE"
    assert observed_but_unenforced["requestAdmission"]["owner_policy_reference"] is False

    duplicate_source_observation = classify(wrap(
        "CharSequence editable = adamInput.getText();\n"
        "if (!AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)) return;\n"
        "CharSequence second = adamInput.getText();\n"
        "String text = editable.toString().trim();\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert duplicate_source_observation["requestAdmission"]["status"] == "PARTIAL_UNSAFE"
    assert "exactly one detached editable source observation" in (
        duplicate_source_observation["requestAdmission"]["reason"]
    )

    duplicate_policy_gate = classify(wrap(
        "CharSequence editable = adamInput.getText();\n"
        "if (!AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)) return;\n"
        "if (!AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)) return;\n"
        "String text = editable.toString().trim();\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert duplicate_policy_gate["requestAdmission"]["status"] == "PARTIAL_UNSAFE"
    assert "canonical fully-qualified fail-closed request-admission policy guard" in (
        duplicate_policy_gate["requestAdmission"]["reason"]
    )

    duplicate_materialization = classify(wrap(
        "CharSequence editable = adamInput.getText();\n"
        "if (!AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)) return;\n"
        "String ignored = editable.toString();\n"
        "String text = editable.toString().trim();\n"
        "OperatorState.submitAdamRequest(this, adamMode, text, now);"
    ))
    assert duplicate_materialization["requestAdmission"]["status"] == "PARTIAL_UNSAFE"
    assert "exactly one post-gate detached request materialization" in (
        duplicate_materialization["requestAdmission"]["reason"]
    )

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

    print("Adam UI request-admission owner probe control-flow, canonical-policy, and single-observation custody: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
