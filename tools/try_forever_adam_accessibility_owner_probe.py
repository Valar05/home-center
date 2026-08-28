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


def _brace_depth_at(surface: str, index: int) -> int:
    """Return lexical brace depth immediately before index on an already-blanked code surface."""
    depth = 0
    for char in surface[:max(0, index)]:
        if char == "{":
            depth += 1
        elif char == "}":
            depth = max(0, depth - 1)
    return depth


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

    SOURCE_WIRED requires one single-assignment detached editable observation, exactly one canonical
    fully-qualified bounded admission call used as an unconditional top-level fail-closed return guard,
    one exact detached materialization/trim assignment, and exact persistence of that admitted `text`,
    in order. Merely calling the right policy and ignoring its result is not admission custody. A shadow
    helper with the same method name is not policy custody, a nested conditional guard is not unconditional
    custody, and one correct guard must not hide source/text rebinding or repeated observations/work later
    in the owner.
    """
    owner = _owner_surface(source)
    send_method = _direct_method_surface(owner, "submitAdamRequest")
    policy = "AdamSendAvailabilityAccessibilityPolicy"

    source_declaration_pattern = re.compile(
        r"\bCharSequence\s+editable\s*=\s*adamInput\.getText\s*\(\s*\)\s*;"
    )
    source_declarations = list(source_declaration_pattern.finditer(send_method))
    direct_source_observation_count = send_method.count("adamInput.getText()")
    editable_assignment_count = len(re.findall(r"\beditable\s*=(?!=)", send_method))
    single_detached_source_observation = (
        len(source_declarations) == 1
        and direct_source_observation_count == 1
        and editable_assignment_count == 1
    )
    source_declaration_index = source_declarations[0].start() if len(source_declarations) == 1 else -1

    policy_call_patterns = (
        "AdamSendAvailabilityAccessibilityPolicy.hasMaterialRequest(editable)",
        "AdamSendAvailabilityAccessibilityPolicy.classifyRequest(editable)",
        "AdamSendAvailabilityAccessibilityPolicy.decisionFor(adamMode, editable)",
    )
    policy_call_count = sum(send_method.count(pattern) for pattern in policy_call_patterns)
    admission_guard_pattern = re.compile(
        r"if\s*\(\s*!\s*AdamSendAvailabilityAccessibilityPolicy\.hasMaterialRequest\s*"
        r"\(\s*editable\s*\)\s*\)\s*(?:\{\s*)?return\s*;(?:\s*\})?"
    )
    admission_guards = list(admission_guard_pattern.finditer(send_method))
    top_level_admission_guards = [
        match for match in admission_guards if _brace_depth_at(send_method, match.start()) == 1
    ]
    single_controlling_guard = len(top_level_admission_guards) == 1 and policy_call_count == 1
    policy_gate_index = top_level_admission_guards[0].start() if single_controlling_guard else -1
    canonical_policy_reference = policy in send_method and single_controlling_guard

    direct_materialization_count = send_method.count("adamInput.getText().toString()")
    detached_materialization_count = send_method.count("editable.toString()")
    materialization_pattern = re.compile(
        r"\bString\s+text\s*=\s*editable\.toString\s*\(\s*\)\.trim\s*\(\s*\)\s*;"
    )
    materializations = list(materialization_pattern.finditer(send_method))
    text_assignment_count = len(re.findall(r"\btext\s*=(?!=)", send_method))
    single_detached_materialization = (
        direct_materialization_count == 0
        and detached_materialization_count == 1
        and len(materializations) == 1
        and text_assignment_count == 1
    )
    materialization_index = materializations[0].start() if len(materializations) == 1 else -1

    persistence_pattern = re.compile(
        r"OperatorState\.submitAdamRequest\s*\(\s*this\s*,\s*adamMode\s*,\s*text\s*,"
    )
    persistence_calls = list(persistence_pattern.finditer(send_method))
    exact_text_persistence = len(persistence_calls) == 1
    submit_index = persistence_calls[0].start() if exact_text_persistence else -1

    ordered = (
        single_detached_source_observation
        and canonical_policy_reference
        and single_detached_materialization
        and exact_text_persistence
        and source_declaration_index >= 0
        and policy_gate_index >= 0
        and materialization_index >= 0
        and submit_index >= 0
        and source_declaration_index < policy_gate_index < materialization_index < submit_index
    )

    if ordered:
        return SeamVerdict(
            "SOURCE_WIRED",
            "direct Adam UI request owner observes editable source once into a single-assignment binding, uses one canonical policy result as an unconditional top-level fail-closed guard, materializes/trims exactly once afterward, and persists exactly that admitted text",
            policy,
            True,
            True,
        )

    if policy in send_method or source_declarations or direct_source_observation_count > 0:
        missing = []
        if not single_detached_source_observation:
            missing.append("exactly one single-assignment detached editable source observation")
        if not canonical_policy_reference:
            missing.append("one unconditional top-level canonical fully-qualified fail-closed request-admission policy guard")
        if not single_detached_materialization:
            missing.append("exactly one single-assignment post-gate detached trim materialization")
        if not exact_text_persistence:
            missing.append("exact persistence of the admitted text variable")
        if (
            canonical_policy_reference
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
            canonical_policy_reference,
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
        "schema": "try-forever-adam-accessibility-owner-probe.v8",
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
