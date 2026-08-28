#!/usr/bin/env python3
"""Deterministic source-capability probe for Adam accessibility owner seams.

This probe reads repository source only. It does not execute Android, render UI,
exercise TalkBack, touch the phone/P0 chain, or promote source evidence into TESTED,
runtime, deployed, delivered, or accepted capability.

Comments and literals are blanked first. Positive owner evidence must then occur in the
direct OperatorOverlayService methods that own the Adam mode, send, edit, and request-admission
lifecycle; unrelated state setters elsewhere in the large owner cannot counterfeit wiring.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from try_forever_operator_accessibility_owner_probe import (
    java_lexical_code_surface,
    java_named_class_surface,
)


@dataclass(frozen=True)
class SeamVerdict:
    status: str
    reason: str
    supporting_policy: str
    owner_policy_reference: bool
    owner_semantic_state: bool


def _owner_surface(source: str) -> str:
    lexical = java_lexical_code_surface(source)
    return java_named_class_surface(lexical, "OperatorOverlayService")


def _direct_method_surface(class_surface: str, method_name: str) -> str:
    """Return one direct private owner method with any ordinary Java return type."""
    declaration = re.compile(
        rf"\bprivate\s+(?:static\s+)?[A-Za-z0-9_$.<>\[\],?]+\s+"
        rf"{re.escape(method_name)}\s*\("
    )
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
        if open_brace < 0:
            return ""
        method_depth = 0
        for end in range(open_brace, len(class_surface)):
            method_char = class_surface[end]
            if method_char == "{":
                method_depth += 1
            elif method_char == "}":
                method_depth -= 1
                if method_depth == 0:
                    return class_surface[match.start():end + 1]
        return ""
    return ""


def classify_mode_selection(source: str) -> SeamVerdict:
    owner = _owner_surface(source)
    create_method = _direct_method_surface(owner, "createOverlay")
    mode_method = _direct_method_surface(owner, "adamModeButton")
    refresh_method = _direct_method_surface(owner, "refreshAdamModeSelection")
    policy = "AdamModeSelectionAccessibilityPolicy"

    policy_reference = policy in mode_method and policy in refresh_method
    initial_state = "setSelected(" in mode_method
    refresh_state = "setSelected(" in refresh_method
    refresh_call = "refreshAdamModeSelection(" in mode_method
    has_persistent_state = initial_state and refresh_state and refresh_call

    row_set_context = (
        "adamModeRow.setAccessibilityDelegate(" in create_method
        and "AccessibilityNodeInfo.CollectionInfo.obtain(" in create_method
        and "AccessibilityNodeInfo.CollectionInfo.SELECTION_MODE_SINGLE" in create_method
        and "AdamModeSelectionAccessibilityPolicy.ROW_COUNT" in create_method
        and "AdamModeSelectionAccessibilityPolicy.COLUMN_COUNT" in create_method
    )
    item_set_context = (
        "setAccessibilityDelegate(" in mode_method
        and "AccessibilityNodeInfo.CollectionItemInfo.obtain(" in mode_method
        and "decision.rowIndex" in mode_method
        and "decision.rowSpan" in mode_method
        and "decision.columnIndex" in mode_method
        and "decision.columnSpan" in mode_method
        and "decision.selected" in mode_method
    )
    has_native_set_context = row_set_context and item_set_context

    if policy_reference and has_persistent_state and has_native_set_context:
        return SeamVerdict(
            "SOURCE_WIRED",
            "direct Adam mode owner initializes and refreshes one-of-many native selection and consumes policy-owned horizontal collection/item geometry",
            policy,
            True,
            True,
        )
    if (
        policy in mode_method
        or policy in refresh_method
        or initial_state
        or refresh_state
        or refresh_call
        or row_set_context
        or item_set_context
    ):
        missing = []
        if not has_persistent_state:
            missing.append("persistent selected-state lifecycle")
        if not row_set_context:
            missing.append("policy-owned single-selection collection geometry")
        if not item_set_context:
            missing.append("policy-owned per-mode item geometry")
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "Adam mode owner is incomplete: missing " + ", ".join(missing),
            policy,
            policy in mode_method or policy in refresh_method,
            has_persistent_state or has_native_set_context,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "direct Adam mode owner changes mode/focus but exposes no persistent selected/checked semantic lifecycle or native one-of-many collection geometry",
        policy,
        False,
        False,
    )


def classify_input_result(source: str) -> SeamVerdict:
    owner = _owner_surface(source)
    create_method = _direct_method_surface(owner, "createOverlay")
    mode_method = _direct_method_surface(owner, "adamModeButton")
    send_method = _direct_method_surface(owner, "submitAdamRequest")
    apply_method = _direct_method_surface(owner, "applyAdamInputResultState")
    policy = "AdamInputResultAccessibilityPolicy"

    ready_transition = (
        policy in mode_method
        and "Transition.MODE_SELECTED" in mode_method
        and "applyAdamInputResultState(" in mode_method
    )
    sent_transition = (
        policy in send_method
        and "Transition.SUBMIT_SUCCEEDED" in send_method
        and "applyAdamInputResultState(" in send_method
    )
    edit_transition = (
        "adamInput.addTextChangedListener(" in create_method
        and policy in create_method
        and "Transition.EDITED" in create_method
        and "applyAdamInputResultState(" in create_method
    )
    semantic_surface = (
        policy in apply_method
        and "adamInput.setStateDescription(" in apply_method
        and "adamInput.setContentDescription(null)" in apply_method
    )
    policy_reference = ready_transition and sent_transition and edit_transition and semantic_surface
    has_result_state = semantic_surface

    if policy_reference and has_result_state:
        return SeamVerdict(
            "SOURCE_WIRED",
            "direct Adam owner preserves the editable text as value, exposes READY/SENT state, and returns SENT to READY on real new editing while preserving empty programmatic clears",
            policy,
            True,
            True,
        )
    if (
        policy in create_method
        or policy in mode_method
        or policy in send_method
        or policy in apply_method
        or "adamInput.setStateDescription(" in owner
        or "adamInput.addTextChangedListener(" in owner
        or "adamInput.setContentDescription(null)" in owner
    ):
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "Adam owner contains only part of editable-value preservation plus the READY/SENT/edit-recovery lifecycle",
            policy,
            policy in create_method or policy in mode_method or policy in send_method or policy in apply_method,
            "adamInput.setStateDescription(" in owner and "adamInput.setContentDescription(null)" in owner,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "Adam input is masked by generic contentDescription/hint semantics and has no persistent READY/SENT edit-recovery lifecycle",
        policy,
        False,
        False,
    )


def classify_send_action(source: str) -> SeamVerdict:
    owner = _owner_surface(source)
    create_method = _direct_method_surface(owner, "createOverlay")
    mode_method = _direct_method_surface(owner, "adamModeButton")
    refresh_method = _direct_method_surface(owner, "refreshAdamSendAction")
    policy = "AdamSendActionAccessibilityPolicy"

    # Creation owns the native button, but the shared refresh method owns semantic projection.
    # Requiring a direct policy reference in createOverlay would reject the intended DRY owner shape.
    created_owner = "adamSendButton" in create_method and "refreshAdamSendAction(" in create_method
    refresh_policy = policy in refresh_method and "adamSendButton.setContentDescription(" in refresh_method
    mode_refresh = "refreshAdamSendAction(" in mode_method
    policy_reference = created_owner and refresh_policy and mode_refresh

    if policy_reference:
        return SeamVerdict(
            "SOURCE_WIRED",
            "direct Adam Send owner initializes and refreshes the exact current-mode action consequence through one shared policy method",
            policy,
            True,
            True,
        )
    if (
        policy in create_method
        or policy in refresh_method
        or "refreshAdamSendAction(" in create_method
        or "refreshAdamSendAction(" in mode_method
    ):
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "Adam Send owner contains only part of the mode-specific action-semantic lifecycle",
            policy,
            policy in create_method or policy in refresh_method,
            "adamSendButton.setContentDescription(" in refresh_method,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "Send action uses a generic semantic label that does not expose which selected Adam mode will receive the request",
        policy,
        False,
        False,
    )


def classify_request_admission(source: str) -> SeamVerdict:
    """Classify the native UI request-work throat independently from supporting policy safety.

    SOURCE_WIRED requires one detached editable observation, one bounded policy gate, and one
    whole-source materialization, in that order, before request persistence. Merely placing one
    correct gate before the first materialization must not hide repeated observations/work later in
    the same owner method.
    """
    owner = _owner_surface(source)
    send_method = _direct_method_surface(owner, "submitAdamRequest")
    policy = "AdamSendAvailabilityAccessibilityPolicy"

    direct_source_observation_count = send_method.count("adamInput.getText()")
    detached_source = (
        "CharSequence editable = adamInput.getText()" in send_method
        or "CharSequence editable=adamInput.getText()" in send_method
    )
    single_detached_source_observation = detached_source and direct_source_observation_count == 1

    gate_patterns = (
        "hasMaterialRequest(editable)",
        "classifyRequest(editable)",
        "decisionFor(adamMode, editable)",
    )
    gate_count = sum(send_method.count(pattern) for pattern in gate_patterns)
    gate_indices = [
        send_method.find(pattern)
        for pattern in gate_patterns
        if send_method.find(pattern) >= 0
    ]
    policy_gate_index = min(gate_indices) if gate_indices else -1
    single_policy_gate = gate_count == 1

    direct_materialization_count = send_method.count("adamInput.getText().toString()")
    detached_materialization_count = send_method.count("editable.toString()")
    materialization_count = direct_materialization_count + detached_materialization_count
    materialization_index = send_method.find("editable.toString()")
    single_detached_materialization = (
        direct_materialization_count == 0
        and detached_materialization_count == 1
        and materialization_count == 1
    )

    submit_index = send_method.find("OperatorState.submitAdamRequest(")
    ordered = (
        single_detached_source_observation
        and single_policy_gate
        and single_detached_materialization
        and policy_gate_index >= 0
        and materialization_index >= 0
        and submit_index >= 0
        and policy_gate_index < materialization_index < submit_index
    )

    if ordered:
        return SeamVerdict(
            "SOURCE_WIRED",
            "direct Adam UI request owner observes editable source once, consumes one bounded request-admission gate, materializes once afterward, and persists only after materialization",
            policy,
            True,
            True,
        )

    if policy in send_method or detached_source or direct_source_observation_count > 0:
        missing = []
        if not single_detached_source_observation:
            missing.append("exactly one detached editable source observation")
        if not single_policy_gate:
            missing.append("exactly one bounded request-admission policy gate")
        if not single_detached_materialization:
            missing.append("exactly one post-gate detached request materialization")
        if (
            single_policy_gate
            and single_detached_materialization
            and policy_gate_index >= 0
            and materialization_index >= 0
            and policy_gate_index > materialization_index
        ):
            missing.append("policy-before-materialization ordering")
        if submit_index < 0 or (materialization_index >= 0 and submit_index < materialization_index):
            missing.append("materialization-before-request-persistence ordering")
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "Adam UI request owner is incomplete: missing " + ", ".join(missing),
            policy,
            policy in send_method,
            False,
        )

    return SeamVerdict(
        "LEGACY_OWNER",
        "direct Adam UI request owner materializes/trims editable text before consuming the bounded request-admission policy",
        policy,
        False,
        False,
    )


def classify(source: str) -> dict[str, object]:
    return {
        "schema": "try-forever-adam-accessibility-owner-probe.v6",
        "modeSelection": asdict(classify_mode_selection(source)),
        "inputResult": asdict(classify_input_result(source)),
        "sendAction": asdict(classify_send_action(source)),
        "requestAdmission": asdict(classify_request_admission(source)),
        "capability": {
            "sourceInspection": True,
            "regressionExecuted": False,
            "tested": False,
            "runtimeUi": False,
            "runtimeTalkBack": False,
            "deployed": False,
            "phoneDelivered": False,
            "accepted": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--owner",
        default=(
            "android/operator-overlay/app/src/main/java/com/homecenter/"
            "operatoroverlay/OperatorOverlayService.java"
        ),
    )
    args = parser.parse_args()
    source = Path(args.owner).read_text(encoding="utf-8")
    print(json.dumps(classify(source), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
