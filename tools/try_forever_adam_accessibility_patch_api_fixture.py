#!/usr/bin/env python3
"""Source fixture for the staged Adam native accessibility owner proposal.

This fixture is deliberately repository/source evidence only. It binds the proposal
to the authenticated supporting-policy blob and API shape, rejects invented API
names, and preserves the explicit repeat-send accessibility receipt. It does not
apply the proposal or claim Android/TalkBack runtime behavior.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCH = ROOT / "patches" / "try-forever-adam-mode-input-accessibility-owner.patch"
AVAILABILITY_POLICY = (
    ROOT
    / "android"
    / "operator-overlay"
    / "app"
    / "src"
    / "main"
    / "java"
    / "com"
    / "homecenter"
    / "operatoroverlay"
    / "AdamSendAvailabilityAccessibilityPolicy.java"
)
EXPECTED_AVAILABILITY_BLOB = "2e15869dcab81995fbac849c98596a6cf2cd50c5"


def git_blob_sha(payload: bytes) -> str:
    header = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def main() -> int:
    patch_text = PATCH.read_text(encoding="utf-8")
    policy_bytes = AVAILABILITY_POLICY.read_bytes()
    policy_text = policy_bytes.decode("utf-8")
    actual_policy_blob = git_blob_sha(policy_bytes)

    required_patch = {
        "authenticated_availability_dependency": (
            "Availability dependency: AdamSendAvailabilityAccessibilityPolicy blob "
            + EXPECTED_AVAILABILITY_BLOB
            + "."
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
    forbidden_patch = {
        "fabricated_classifier": "AdamSendAvailabilityAccessibilityPolicy.classifyEditable(",
        "fabricated_send_enabled_field": "availability.sendEnabled",
        "obsolete_embedded_next_state": "availability.nextResultState",
    }
    required_policy = {
        "decision_api": "public static Decision decisionFor(String mode, CharSequence editableValue)",
        "enabled_field": "public final boolean enabled;",
        "unsent_contact_field": "public final boolean hasUnsentText;",
        "bounded_classifier": "public static RequestState classifyRequest(CharSequence editableValue)",
        "material_gate": "public static boolean hasMaterialRequest(CharSequence editableValue)",
    }
    forbidden_policy = {
        "fabricated_classifier": "classifyEditable(",
        "fabricated_send_enabled_field": "sendEnabled",
    }

    required_patch_state = {
        name: needle in patch_text for name, needle in required_patch.items()
    }
    forbidden_patch_state = {
        name: needle not in patch_text for name, needle in forbidden_patch.items()
    }
    required_policy_state = {
        name: needle in policy_text for name, needle in required_policy.items()
    }
    forbidden_policy_state = {
        name: needle not in policy_text for name, needle in forbidden_policy.items()
    }
    policy_blob_matches = actual_policy_blob == EXPECTED_AVAILABILITY_BLOB

    passed = (
        policy_blob_matches
        and all(required_patch_state.values())
        and all(forbidden_patch_state.values())
        and all(required_policy_state.values())
        and all(forbidden_policy_state.values())
    )

    print(json.dumps({
        "fixture": "try_forever_adam_accessibility_patch_api_fixture",
        "schemaVersion": 4,
        "state": "PASS" if passed else "RED",
        "proposalPath": str(PATCH.relative_to(ROOT)),
        "availabilityPolicyPath": str(AVAILABILITY_POLICY.relative_to(ROOT)),
        "expectedAvailabilityPolicyBlob": EXPECTED_AVAILABILITY_BLOB,
        "actualAvailabilityPolicyBlob": actual_policy_blob,
        "availabilityPolicyBlobMatches": policy_blob_matches,
        "requiredPatch": required_patch_state,
        "forbiddenPatchAbsent": forbidden_patch_state,
        "requiredPolicy": required_policy_state,
        "forbiddenPolicyAbsent": forbidden_policy_state,
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
