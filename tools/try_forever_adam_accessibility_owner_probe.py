#!/usr/bin/env python3
"""Deterministic source-capability probe for Adam accessibility owner seams.

This probe reads repository source only. It does not execute Android, render UI,
exercise TalkBack, touch the phone/P0 chain, or promote source evidence into TESTED,
runtime, deployed, delivered, or accepted capability.
"""

from __future__ import annotations

import argparse
import json
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


def classify_mode_selection(source: str) -> SeamVerdict:
    owner = _owner_surface(source)
    policy = "AdamModeSelectionAccessibilityPolicy"
    policy_reference = policy in owner
    has_persistent_state = (
        "setStateDescription(" in owner
        and ("setSelected(" in owner or "setChecked(" in owner)
    )
    if policy_reference and has_persistent_state:
        return SeamVerdict(
            "SOURCE_WIRED",
            "existing owner consumes the Adam one-of-many policy and exposes persistent selection state",
            policy,
            True,
            True,
        )
    if policy_reference or has_persistent_state:
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "owner contains only part of the persistent mode-selection contract",
            policy,
            policy_reference,
            has_persistent_state,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "mode changes are owned, but the five mutually-exclusive controls expose no persistent selected/checked semantic state",
        policy,
        False,
        False,
    )


def classify_input_result(source: str) -> SeamVerdict:
    owner = _owner_surface(source)
    policy = "AdamInputResultAccessibilityPolicy"
    policy_reference = policy in owner
    has_result_state = "adamInput.setStateDescription(" in owner
    if policy_reference and has_result_state:
        return SeamVerdict(
            "SOURCE_WIRED",
            "existing owner exposes persistent Adam input mode/result state through the supporting policy",
            policy,
            True,
            True,
        )
    if policy_reference or has_result_state:
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "owner contains only part of the persistent Adam input-result semantic contract",
            policy,
            policy_reference,
            has_result_state,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "sent state is carried by hint/legacy announcement while the editable field lacks persistent mode/result state semantics",
        policy,
        False,
        False,
    )


def classify(source: str) -> dict[str, object]:
    return {
        "schema": "try-forever-adam-accessibility-owner-probe.v1",
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
