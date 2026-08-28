#!/usr/bin/env python3
"""Source fixture for the staged Adam native accessibility owner proposal.

This fixture is deliberately repository/source evidence only. It verifies that the
proposal consumes the authenticated supporting policy APIs instead of a fabricated
or stale API shape while preserving the explicit repeat-send accessibility receipt.
It does not apply the proposal or claim Android/TalkBack runtime behavior.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches" / "try-forever-adam-mode-input-accessibility-owner.patch"


def main() -> int:
    text = PATCH.read_text(encoding="utf-8")

    required = {
        "authenticated_availability_dependency": (
            "Availability dependency: AdamSendAvailabilityAccessibilityPolicy blob "
            "2e15869dcab81995fbac849c98596a6cf2cd50c5."
        ),
        "current_availability_decision": (
            "AdamSendAvailabilityAccessibilityPolicy.decisionFor(adamMode, editable)"
        ),
        "send_enabled_field": "availability.enabled",
        "unsent_contact_field": "availability.hasUnsentText",
        "result_transition_owner": "AdamInputResultAccessibilityPolicy.nextState(",
        "edited_transition": "AdamInputResultAccessibilityPolicy.Transition.EDITED",
        "repeat_send_receipt": 'adamInput.announceForAccessibility("Sent to Adam " + adamMode)',
    }
    forbidden = {
        "fabricated_classifier": "AdamSendAvailabilityAccessibilityPolicy.classifyEditable(",
        "fabricated_send_enabled_field": "availability.sendEnabled",
        "obsolete_embedded_next_state": "availability.nextResultState",
    }

    required_state = {name: needle in text for name, needle in required.items()}
    forbidden_state = {name: needle not in text for name, needle in forbidden.items()}
    passed = all(required_state.values()) and all(forbidden_state.values())

    print(json.dumps({
        "fixture": "try_forever_adam_accessibility_patch_api_fixture",
        "schemaVersion": 3,
        "state": "PASS" if passed else "RED",
        "proposalPath": str(PATCH.relative_to(ROOT)),
        "availabilityPolicyBlob": "2e15869dcab81995fbac849c98596a6cf2cd50c5",
        "required": required_state,
        "forbiddenAbsent": forbidden_state,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "runtimeTalkBack": False,
        "phoneConsumed": False,
        "p0Mutated": False,
    }, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
