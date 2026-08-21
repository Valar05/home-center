#!/usr/bin/env python3
"""Source-capability probe for collapsed operational truth and Adam Send availability.

This is repository/source evidence only. It does not execute Android, exercise TalkBack,
touch the phone/P0 chain, or promote helper/patch existence into owner wiring.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from try_forever_adam_accessibility_owner_probe import _direct_method_surface, _owner_surface


@dataclass(frozen=True)
class SeamVerdict:
    status: str
    reason: str
    supporting_policy: str


def _nested_public_void_callback_surface(method_surface: str, callback_name: str) -> str:
    """Return one public void callback body nested inside a direct owner method.

    The input is already a Java lexical code surface through _owner_surface, so comments
    and string/text-block literals cannot counterfeit a callback declaration. Requiring
    the declaration and extracting its braces is stronger than merely seeing a watcher,
    an onTextChanged token, and some refresh calls somewhere nearby in createOverlay.
    """
    declaration = re.compile(
        rf"\bpublic\s+void\s+{re.escape(callback_name)}\s*\("
    )
    match = declaration.search(method_surface)
    if match is None:
        return ""
    open_brace = method_surface.find("{", match.end())
    if open_brace < 0:
        return ""
    depth = 0
    for end in range(open_brace, len(method_surface)):
        char = method_surface[end]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return method_surface[match.start():end + 1]
    return ""


def classify_collapsed_operational_refresh(source: str) -> SeamVerdict:
    owner = _owner_surface(source)
    refresh = _direct_method_surface(owner, "refreshUi")
    apply = _direct_method_surface(owner, "applyHeartbeatCollapsedOwnerAccessibility")
    policy = "HeartbeatCollapsedOwnerAccessibility"

    owner_status = "status.getText()" in apply
    three_way_projection = (
        policy + ".contentDescription(" in apply
        and "operatorStatus" in apply
    )
    owner_refresh = "applyHeartbeatCollapsedOwnerAccessibility(currentHeartbeatModel())" in refresh
    change_dedupe = "TextUtils.equals(" in apply and "dragHandle.setContentDescription(" in apply

    if owner_status and three_way_projection and owner_refresh and change_dedupe:
        return SeamVerdict(
            "SOURCE_WIRED",
            "collapsed drag-handle semantics refresh from current owner status independently of heartbeat persisted-snapshot dedupe and avoid redundant contentDescription writes",
            policy,
        )
    if policy in apply or owner_status or owner_refresh or change_dedupe:
        missing = []
        if not owner_status or not three_way_projection:
            missing.append("current owner operational-status projection")
        if not owner_refresh:
            missing.append("owner-refresh cadence independent of heartbeat SKIP_UNCHANGED")
        if not change_dedupe:
            missing.append("idempotent contentDescription write guard")
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "collapsed operational truth is incomplete: missing " + ", ".join(missing),
            policy,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "collapsed drag handle exposes no owner operational-status projection",
        policy,
    )


def classify_adam_send_availability(source: str) -> SeamVerdict:
    owner = _owner_surface(source)
    create = _direct_method_surface(owner, "createOverlay")
    mode = _direct_method_surface(owner, "adamModeButton")
    refresh = _direct_method_surface(owner, "refreshAdamSendAvailability")
    on_text_changed = _nested_public_void_callback_surface(create, "onTextChanged")
    policy = "AdamSendAvailabilityAccessibilityPolicy"

    persistent_button = "adamSendButton = button(\"Send\")" in create
    watcher_installed = "adamInput.addTextChangedListener(" in create
    callback_refresh = "refreshAdamSendAvailability(" in on_text_changed
    create_without_callback = create.replace(on_text_changed, "", 1) if on_text_changed else create
    initial_refresh = "refreshAdamSendAvailability(" in create_without_callback
    edit_refresh = watcher_installed and callback_refresh and initial_refresh
    mode_refresh = "refreshAdamSendAvailability(" in mode
    policy_projection = policy in refresh
    native_enabled = "adamSendButton.setEnabled(" in refresh
    action_semantics = "adamSendButton.setContentDescription(" in refresh

    if all((persistent_button, edit_refresh, mode_refresh, policy_projection, native_enabled, action_semantics)):
        return SeamVerdict(
            "SOURCE_WIRED",
            "existing Adam Send owner tracks the exact trim-based admission boundary on real onTextChanged edits and mode changes using native enabled state plus current-mode action semantics",
            policy,
        )
    if policy in owner or "refreshAdamSendAvailability(" in owner or "adamSendButton.setEnabled(" in owner:
        missing = []
        if not persistent_button:
            missing.append("persistent native Send owner")
        if not edit_refresh:
            missing.append("edit callback plus independent initial availability projection")
        if not mode_refresh:
            missing.append("mode-change refresh")
        if not policy_projection:
            missing.append("availability policy projection")
        if not native_enabled:
            missing.append("native enabled/disabled consequence")
        if not action_semantics:
            missing.append("current-mode action description")
        return SeamVerdict(
            "PARTIAL_UNSAFE",
            "Adam Send availability is incomplete: missing " + ", ".join(missing),
            policy,
        )
    return SeamVerdict(
        "LEGACY_OWNER",
        "Send remains enabled/focusable even when submitAdamRequest is guaranteed to trim to an empty no-op",
        policy,
    )


def classify(source: str) -> dict[str, object]:
    return {
        "schema": "try-forever-operational-contact-owner-probe.v2",
        "collapsedOperationalRefresh": asdict(classify_collapsed_operational_refresh(source)),
        "adamSendAvailability": asdict(classify_adam_send_availability(source)),
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
