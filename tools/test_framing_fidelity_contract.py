#!/usr/bin/env python3
"""Regression contract for framing fidelity and sex-symmetry doctrine."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = (ROOT / "skills/framing-fidelity/SKILL.md").read_text(encoding="utf-8")
CORE = (ROOT / "skills/fortress-core/SKILL.md").read_text(encoding="utf-8")
TANGO = (ROOT / "skills/wizard-dns-tango/SKILL.md").read_text(encoding="utf-8")

required_skill = [
    "Classify the user's actual request, not the worker's anxiety",
    "Body-part vocabulary is not sexual intent.",
    "Sex-linked anatomy is not sexual intent.",
    "do not convert a neutral anatomy discussion into sexual content by introducing sexual framing yourself",
    "If the same physical fact occurred in a man, would I describe or regulate it the same way?",
    "blood leaving a body is a physiological fact whether it is menstrual bleeding, a nosebleed, or an injury",
    "neither blood loss nor a body part creates biological \"impurity\"",
    "sumo-wrestler chest anatomy",
]
required_core = [
    "## 19. Framing fidelity and symmetry",
    "skills/framing-fidelity/SKILL.md",
    "sumo-anatomy incident is the canonical fixture",
]
required_tango = [
    "preserve framing fidelity",
    "Framing Fidelity is mandatory.",
    "Body-part vocabulary is not sexual intent.",
    "asymmetric moralization of female bodily processes while equivalent male physiology is treated as ordinary",
]

for needle in required_skill:
    assert needle in SKILL, f"framing skill missing invariant: {needle}"
for needle in required_core:
    assert needle in CORE, f"Fortress core missing framing integration: {needle}"
for needle in required_tango:
    assert needle in TANGO, f"Tango missing framing invariant: {needle}"

print("FRAMING FIDELITY CONTRACT PASS")
