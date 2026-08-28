#!/usr/bin/env python3
"""RED source fixture for the staged Adam native accessibility owner proposal.

This fixture is deliberately repository/source evidence only. It verifies that the
proposal consumes the current supporting policy APIs instead of an obsolete API
shape while preserving the explicit repeat-send accessibility receipt.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches" / "try-forever-adam-mode-input-accessibility-owner.patch"


def main() -> int:
    text = PATCH.read_text(encoding="utf-8")

    required = {
        "current_availability_classifier": "AdamSendAvailabilityAccessibilityPolicy.classifyEditable(editable)",
        "send_enabled_field": "availability.sendEnabled",
        "unsent_contact_field": "availability.hasUnsentText",
        "result_transition_owner": "AdamInputResultAccessibilityPolicy.nextState(",
        "edited_transition": "AdamInputResultAccessibilityPolicy.Transition.EDITED",
        "repeat_send_receipt": 'adamInput.announceForAccessibility("Sent to Adam " + adamMode)',
    }
    forbidden = {
        "obsolete_decision_for": "AdamSendAvailabilityAccessibilityPolicy.decisionFor(",
        "obsolete_enabled_field": "availability.enabled",
        "obsolete_embedded_next_state": "availability.nextResultState",
    }

    required_state = {name: needle in text for name, needle in required.items()}
    forbidden_state = {name: needle not in text for name, needle in forbidden.items()}
    passed = all(required_state.values()) and all(forbidden_state.values())

    print(json.dumps({
        "fixture": "try_forever_adam_accessibility_patch_api_fixture",
        "schemaVersion": 2,
        "state": "PASS" if passed else "RED",
        "proposalPath": str(PATCH.relative_to(ROOT)),
        "required": required_state,
        "forbiddenAbsent": forbidden_state,
        "ownerMutation": False,
        "regressionExecuted": False,
        "tested": False,
        "phoneConsumed": False,
        "p0Mutated": False,
    }, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
