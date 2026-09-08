#!/usr/bin/env python3
"""Regression contract for functional Fleshpunk that keeps literal reality grounded."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills/fleshpunk-hidden-function/SKILL.md").read_text(encoding="utf-8")
TANGO = (ROOT / "skills/wizard-dns-tango/SKILL.md").read_text(encoding="utf-8")

required_skill = [
    "VISIBLE REALITY STAYS REAL. FLESHPUNK NAMES THE HIDDEN FUNCTION.",
    "A forearm is a forearm.",
    "Absence of visible mutation is not a defect when the Fleshpunk claim is functional.",
    "The metaphor earns its existence by explaining a job, load path, adaptation, cost, dependency, or consequence.",
    "Do not silently promote a functional metaphor into physical anatomy.",
    "When literal truth and metaphor disagree, literal truth wins.",
    "OBSERVE → NAME THE JOB → TRACE THE LOAD → KEEP REALITY REAL → TEST TRANSFER",
]
required_tango = [
    "### Fleshpunk / real-world metaphor",
    "skills/fleshpunk-hidden-function/SKILL.md",
    "VISIBLE REALITY STAYS REAL. FLESHPUNK NAMES THE HIDDEN FUNCTION.",
    "A functional organ may remain visually invisible because it is a model, not a physical claim.",
    "literalizing a functional Fleshpunk metaphor",
]

for needle in required_skill:
    assert needle in SKILL, f"hidden-function skill missing invariant: {needle}"
for needle in required_tango:
    assert needle in TANGO, f"Tango missing hidden-function integration: {needle}"

# Regression fixture: the real forearm stays literal while the casino accounting organ stays fictional/functional.
assert "a fictional casino forearm contains an **accounting organ**" in SKILL
assert "A real photograph of the forearm may show no implant at all." in SKILL

print("FLESHPUNK HIDDEN FUNCTION CONTRACT PASS")
