#!/usr/bin/env python3
"""Regression contract for the Haraway Hotel active-operator office."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills/haraway-hotel-operator/SKILL.md").read_text(encoding="utf-8")
CONFIG = json.loads((ROOT / "config/active-operator.v1.json").read_text(encoding="utf-8"))
DRU = (ROOT / "skills/dru-simulation-trap/SKILL.md").read_text(encoding="utf-8")

required_skill = [
    "Ritsu is the active Haraway Hotel operator.",
    "DRU is not erased.",
    "Relief is handoff, not erasure.",
    "Ritsu is not Drew's girlfriend, romantic partner, spouse, lover, or dating relationship.",
    "If a male operator would not automatically imply a boyfriend, a female operator does not automatically imply a girlfriend.",
    "contrast, not impersonation",
    "must never claim to speak for, simulate the private mind of, or reproduce the actual opinions of June, Drew's mother, Jackie, or women generally",
    "Regnet's gold star",
    "Ritsu holds the watch. DRU keeps the archive.",
]
for needle in required_skill:
    assert needle in SKILL, f"operator skill missing invariant: {needle}"

assert CONFIG["schema"] == "home-center.active-operator.v1"
assert CONFIG["activeOperator"] == "Ritsu"
assert CONFIG["status"] == "ACTIVE"
assert CONFIG["previousOperator"]["name"] == "DRU"
assert CONFIG["previousOperator"]["status"] == "RETAINED_INACTIVE"
assert CONFIG["rotation"]["eraseOnRotation"] is False
assert CONFIG["relationshipBoundary"]["romantic"] is False
assert CONFIG["relationshipBoundary"]["girlfriend"] is False
assert CONFIG["perspective"]["femalePerspectiveIsIntellectualContrast"] is True
assert CONFIG["perspective"]["proxyForRealPeople"] is False
assert "DRU Simulation Trap" in DRU, "legacy DRU machinery must be preserved, not erased"

print("HARAWAY HOTEL RITSU OPERATOR CONTRACT PASS")
