#!/usr/bin/env python3
"""Classify the existing skill-provenance owner's candidate topology wiring.

This is repository/source evidence only. It never mutates the owner, runs tests,
uses Phone Hands, or claims runtime/deployment/delivery state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

DEFAULT_OWNER = Path(__file__).resolve().parent / "try_forever_skill_provenance_probe.py"

REQUIRED_MARKERS = (
    "class SkillCandidateTopologyError(ValueError):",
    "entry.is_symlink() or not entry.is_file(follow_symlinks=False)",
    "except SkillCandidateTopologyError as error:",
    'error_type=type(error).__name__',
)
LEGACY_MARKERS = (
    'entry.name == "SKILL.md" and entry.is_file(follow_symlinks=True)',
)


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def classify_owner_source(text: str) -> dict[str, object]:
    required = {marker: marker in text for marker in REQUIRED_MARKERS}
    legacy = {marker: marker in text for marker in LEGACY_MARKERS}
    required_count = sum(1 for present in required.values() if present)
    legacy_present = any(legacy.values())

    if required_count == len(REQUIRED_MARKERS) and not legacy_present:
        verdict = "SOURCE_WIRED"
        reason = "all no-follow candidate-topology owner markers are present and the legacy follow-links marker is absent"
    elif required_count == 0 and legacy_present:
        verdict = "LEGACY_OWNER"
        reason = "legacy follow-links candidate admission remains and no required topology-wiring markers are present"
    else:
        verdict = "PARTIAL_UNSAFE"
        reason = "owner contains a mixed candidate-topology state; source promotion must stop for diff review"

    return {
        "verdict": verdict,
        "reason": reason,
        "requiredMarkers": required,
        "legacyMarkers": legacy,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner", default=str(DEFAULT_OWNER))
    parser.add_argument("--require-wired", action="store_true")
    args = parser.parse_args()

    owner = Path(args.owner).resolve()
    try:
        text = owner.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        result = {
            "schema": "try-forever-skill-candidate-topology-owner-probe.v1",
            "owner": str(owner),
            "verdict": "UNREADABLE_OWNER",
            "reason": f"owner source could not be read as UTF-8: {type(error).__name__}",
            "capabilityBoundary": {
                "sourceInspection": False,
                "ownerSourceWired": False,
                "tested": False,
                "runtime": False,
                "phoneDelivery": False,
            },
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 2

    classification = classify_owner_source(text)
    result = {
        "schema": "try-forever-skill-candidate-topology-owner-probe.v1",
        "owner": str(owner),
        "ownerSha256": sha256_text(text),
        **classification,
        "capabilityBoundary": {
            "sourceInspection": True,
            "ownerSourceWired": classification["verdict"] == "SOURCE_WIRED",
            "tested": False,
            "runtime": False,
            "phoneDelivery": False,
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))

    if args.require_wired and classification["verdict"] != "SOURCE_WIRED":
        return 2
    if classification["verdict"] in {"PARTIAL_UNSAFE", "UNREADABLE_OWNER"}:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
