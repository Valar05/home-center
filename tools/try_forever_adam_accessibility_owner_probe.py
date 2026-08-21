#!/usr/bin/env python3
"""Deterministic source-capability probe for Adam accessibility owner seams.

This probe reads repository source only. It does not execute Android, render UI,
exercise TalkBack, touch the phone/P0 chain, or promote source evidence into TESTED,
runtime, deployed, delivered, or accepted capability.

Comments and literals are blanked first. Positive owner evidence must then occur in the
direct OperatorOverlayService methods that own the Adam mode and send consequences;
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
    method = _direct_method_surface(owner, "adamModeButton")
    policy = "AdamModeSelectionAccessibilityPolicy"
    policy_reference = policy in method
    has_persistent_state = "setSelected(" in method or "setChecked(" in method
    if policy_reference and has_persistent_state:
        return SeamVerdict(
            "SOURCE_WIRED",
            "direct Adam mode owner consumes the one-of-many policy and exposes native persistent selection state",
            policy,
            True,
            True,
        )
    if policy_reference or has_persistent_state:
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "direct Adam mode owner contains only part of the persistent selection contract",
            policy,
            policy_reference,
            has_persistent_state,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "direct Adam mode owner changes mode/focus but exposes no persistent selected/checked semantic state",
        policy,
        False,
        False,
    )


def classify_input_result(source: str) -> SeamVerdict:
    owner = _owner_surface(source)
    mode_method = _direct_method_surface(owner, "adamModeButton")
    send_method = _direct_method_surface(owner, "submitAdamRequest")
    policy = "AdamInputResultAccessibilityPolicy"
    ready_policy = policy in mode_method
    sent_policy = policy in send_method
    ready_state = "adamInput.setStateDescription(" in mode_method
    sent_state = "adamInput.setStateDescription(" in send_method
    policy_reference = ready_policy and sent_policy
    has_result_state = ready_state and sent_state
    if policy_reference and has_result_state:
        return SeamVerdict(
            "SOURCE_WIRED",
            "direct Adam mode/send owners expose READY and SENT persistent input-result state through one policy",
            policy,
            True,
            True,
        )
    if ready_policy or sent_policy or ready_state or sent_state:
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "direct Adam owners contain only part of the READY/SENT persistent input-result contract",
            policy,
            ready_policy or sent_policy,
            ready_state or sent_state,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "mode/send owners use input hint/legacy receipt without persistent READY/SENT state semantics",
        policy,
        False,
        False,
    )


def classify(source: str) -> dict[str, object]:
    return {
        "schema": "try-forever-adam-accessibility-owner-probe.v2",
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
