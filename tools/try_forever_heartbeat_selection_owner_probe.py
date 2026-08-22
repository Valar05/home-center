#!/usr/bin/env python3
"""Source-capability probe for native heartbeat persistent-selection semantics.

Repository/source evidence only. This does not execute Android, exercise TalkBack,
touch the phone/P0 chain, or promote policy/probe existence into owner wiring.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from try_forever_adam_accessibility_owner_probe import _direct_method_surface, _owner_surface


@dataclass(frozen=True)
class SeamVerdict:
    status: str
    reason: str
    supporting_policy: str


def classify_native_selection(source: str) -> SeamVerdict:
    owner = _owner_surface(source)
    apply_light = _direct_method_surface(owner, "applyHeartbeatLight")
    apply_collection = _direct_method_surface(owner, "applyHeartbeatSelectionAccessibility")
    policy = "HeartbeatSelectionAccessibilityPolicy"

    native_selected_state = "light.setSelected(" in apply_light
    policy_projection = policy in apply_collection and ".fromModel(" in apply_collection
    collection_context = (
        "heartbeatLights.setAccessibilityDelegate(" in apply_collection
        and "AccessibilityNodeInfo.CollectionInfo.obtain(" in apply_collection
        and "AccessibilityNodeInfo.CollectionInfo.SELECTION_MODE_SINGLE" in apply_collection
    )
    item_context = (
        "AccessibilityNodeInfo.CollectionItemInfo.obtain(" in apply_collection
        and "positionInSet" in apply_collection
        and "setSize" in apply_collection
        and "selected" in apply_collection
    )
    owner_call = "applyHeartbeatSelectionAccessibility(" in apply_light

    if all((native_selected_state, policy_projection, collection_context, item_context, owner_call)):
        return SeamVerdict(
            "SOURCE_WIRED",
            "existing heartbeat owner exposes persistent native selected state plus single-selection collection and stable per-light set-position semantics",
            policy,
        )
    if native_selected_state or policy in owner or "CollectionInfo.obtain(" in owner:
        missing = []
        if not native_selected_state:
            missing.append("native selected-state lifecycle")
        if not policy_projection:
            missing.append("selection collection policy projection")
        if not collection_context:
            missing.append("single-selection collection context")
        if not item_context:
            missing.append("per-light position-in-set context")
        if not owner_call:
            missing.append("direct heartbeat-light owner consumption")
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "heartbeat persistent selection is incomplete: missing " + ", ".join(missing),
            policy,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "heartbeat controls expose no persistent selected-state or collection/set-position semantics",
        policy,
    )


def classify(source: str) -> dict[str, object]:
    return {
        "schema": "try-forever-heartbeat-selection-owner-probe.v1",
        "nativePersistentSelection": asdict(classify_native_selection(source)),
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
