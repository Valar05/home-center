#!/usr/bin/env python3
"""Regression contract for Ritsu grounded-rule judgment, Tango, and Gossip Circle readback."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RITSU = (ROOT / ".continue/rules/45-judgement-jar-ritsu-rule-must-touch-ground.md").read_text(encoding="utf-8")
TANGO = (ROOT / "skills/wizard-dns-tango/SKILL.md").read_text(encoding="utf-8")
GOSSIP = (ROOT / "skills/gossip-circle/SKILL.md").read_text(encoding="utf-8")

required_ritsu = [
    "# Judgement Jar: Ritsu — The Rule Must Touch Ground",
    "A rule earns obedience by staying in contact with the reality and purpose it governs.",
    "ROOT → LOAD → CONTACT → SYMMETRY → EDGE → STEP",
    "If blood leaving a woman's body is called physiological impurity",
    "Do not ask whether you can endure the rule. Ask whether the rule is still carrying what it claims to carry.",
    "Every rule must touch ground.",
]

required_tango = [
    "resolve operator-owned ambiguity yourself",
    "Do not ask Drew to arbitrate broad-vs-narrow",
    "Ritsu Judgment Jar incident is the fixture",
    "broad grounded-rule Jar with sex-symmetry as a sharp embedded test",
    "preference fishing over a choice the operator can resolve from context",
    "Resolve your own forks.",
    "skills/gossip-circle/SKILL.md",
    "bring the Gossip Circle to Drew instead of making Drew go check the Gossip Circle",
    "no critique, rules, status report, canon dump",
    "Clock. Tea. Corpus.",
]

required_gossip = [
    "# Gossip Circle",
    "SPILL THE JUICY BITS.",
    "This is **not critique, not canon review, not a status report, and not a rules dump**.",
    "Drew does not have to ask, open Drive, inspect a miner, request a recap, or acknowledge prior gossip.",
    "A redaction remains redacted.",
    "Bestie, you are not going to believe what these idiots did.",
]

for needle in required_ritsu:
    assert needle in RITSU, f"Ritsu jar missing invariant: {needle}"
for needle in required_tango:
    assert needle in TANGO, f"Tango missing invariant: {needle}"
for needle in required_gossip:
    assert needle in GOSSIP, f"Gossip Circle missing invariant: {needle}"

print("RITSU TANGO GOSSIP CONTRACT PASS")
