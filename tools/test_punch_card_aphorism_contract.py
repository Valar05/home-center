#!/usr/bin/env python3
"""Regression contract for Punch-Card Aphorism deterministic triggering and punch delivery."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from punch_card_judge import judge  # noqa: E402

SKILL = (ROOT / "skills/punch-card-aphorism/SKILL.md").read_text(encoding="utf-8")
CORE = (ROOT / "skills/fortress-core/SKILL.md").read_text(encoding="utf-8")
RITSU = (ROOT / "skills/haraway-hotel-operator/SKILL.md").read_text(encoding="utf-8")
TANGO = (ROOT / "skills/wizard-dns-tango/SKILL.md").read_text(encoding="utf-8")
FUCK = (ROOT / "skills/improper-fuck-lexicon/SKILL.md").read_text(encoding="utf-8")

for needle in [
    "A PUNCH LINE ENDS. A PUNCH CARD EXECUTES.",
    "STATE + INPUT + RULE → NEXT STATE + OBSERVABLE CONSEQUENCE",
    "deterministic gameplay logic judgment",
    "Do not require Drew to say the skill name when the task class already matches.",
    "GAMEPLAY_LOGIC_INCOMPLETE",
    "NONDETERMINISTIC_RANDOMNESS",
    "THE PUN IS THE HANDLE. THE MODEL IS THE MACHINE.",
    "Fast punch lane — conversational aphorism",
    "Tourette's-type timing with legibility",
    "The output MUST contain the exact word `fuck` unless Drew explicitly waives it.",
    "LIVE MECHANISM → ABRUPT WRONG-GRAMMAR FUCK → SECOND-BEAT LEGIBILITY → STOP",
    "answering `punch me` with explanation instead of one line",
]:
    assert needle in SKILL, f"Punch-Card skill missing invariant: {needle}"

for needle in [
    "`punch me` fast path",
    "Tourette's-type timing with legibility",
    "tic-shaped semantic event",
    "ABRUPT FUCK → WRONG GRAMMAR → LEGIBLE MECHANISM → STOP",
    "INTERRUPTION + SURPRISE + COMPRESSION + LEGIBILITY",
    "`punch me` omits `fuck` without an explicit waiver",
]:
    assert needle in FUCK, f"Improper Fuck skill missing punch invariant: {needle}"

assert "Never simulate a verbal tic by inserting profanity automatically" not in FUCK

for text, label in [(CORE, "Fortress Core"), (RITSU, "Ritsu"), (TANGO, "Tango"), (FUCK, "Improper Fuck Lexicon")]:
    assert "skills/punch-card-aphorism/SKILL.md" in text, f"{label} does not route Punch-Card Aphorism"

base = {
    "phrase": "Not the floor",
    "retrieval": "reliability debt",
    "reconstruction": "actor is single structural dependency",
    "execution": "create redundancy before assigning more load",
    "transfer": "apply to any worker/system dependency",
    "correction": "temporary emergency support is not permanent capture",
    "gameplay_required": True,
    "gameplay": {
        "state": ["dependency_count", "actor_load"],
        "input": "assign_load",
        "rule": "if dependency_count == 1, require redundancy",
        "next_state": "assignment pauses until redundancy exists",
        "observable": "stop-work state is visible",
        "correction": "emergency override must be explicit",
        "randomness": {"used": False},
    },
}
assert judge(base)["verdict"] == "EXECUTABLE_GAMEPLAY_CARD"

missing = {**base, "gameplay": {**base["gameplay"], "state": []}}
assert judge(missing)["verdict"] == "GAMEPLAY_LOGIC_INCOMPLETE"

random_hidden = {**base, "gameplay": {**base["gameplay"], "randomness": {"used": True}}}
assert judge(random_hidden)["verdict"] == "NONDETERMINISTIC_RANDOMNESS"

mnemonic = {
    "phrase": "Sex in a box",
    "retrieval": "Punnett square",
    "reconstruction": "parents on axes, offspring combinations inside",
    "execution": "",
    "transfer": "",
    "correction": "simplified inheritance only",
}
assert judge(mnemonic)["verdict"] == "MNEMONIC_ONLY"

print("PUNCH CARD APHORISM CONTRACT PASS")
