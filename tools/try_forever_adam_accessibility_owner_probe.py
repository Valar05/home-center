#!/usr/bin/env python3
"""Deterministic source-capability probe for Adam accessibility owner seams.

This probe reads repository source only. It does not execute Android, render UI,
exercise TalkBack, touch the phone/P0 chain, or promote source evidence into TESTED,
runtime, deployed, delivered, or accepted capability.

Comments and literals are blanked first. Positive owner evidence must then occur in the
direct OperatorOverlayService methods that own the Adam mode, send, and edit lifecycle;
unrelated state setters elsewhere in the large owner cannot counterfeit wiring.
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
    mode_method = _direct_method_surface(owner, "adamModeButton")
    refresh_method = _direct_method_surface(owner, "refreshAdamModeSelection")
    policy = "AdamModeSelectionAccessibilityPolicy"
    policy_reference = policy in mode_method and policy in refresh_method
    initial_state = "setSelected(" in mode_method
    refresh_state = "setSelected(" in refresh_method
    refresh_call = "refreshAdamModeSelection(" in mode_method
    has_persistent_state = initial_state and refresh_state and refresh_call
    if policy_reference and has_persistent_state:
        return SeamVerdict(
            "SOURCE_WIRED",
            "direct Adam mode owner initializes and refreshes one-of-many native selection through the policy",
            policy,
            True,
            True,
        )
    if policy in mode_method or policy in refresh_method or initial_state or refresh_state or refresh_call:
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "Adam mode owner contains only part of the persistent one-of-many selection lifecycle",
            policy,
            policy in mode_method or policy in refresh_method,
            initial_state or refresh_state,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "direct Adam mode owner changes mode/focus but exposes no persistent selected/checked semantic lifecycle",
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
            "direct Adam owner exposes READY/SENT state and returns SENT to READY on real new editing while preserving empty programmatic clears",
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
    ):
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "Adam owner contains only part of the READY/SENT/edit-recovery lifecycle; stale SENT can still describe newly typed unsent text",
            policy,
            policy in create_method or policy in mode_method or policy in send_method or policy in apply_method,
            "adamInput.setStateDescription(" in owner,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "mode/send owners use input hint/legacy receipt without persistent READY/SENT state or edit recovery",
        policy,
        False,
        False,
    )


def classify(source: str) -> dict[str, object]:
    return {
        "schema": "try-forever-adam-accessibility-owner-probe.v3",
        "modeSelection": asdict(classify_mode_selection(source)),
        "inputResult": asdict(classify_input_result(source)),
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
