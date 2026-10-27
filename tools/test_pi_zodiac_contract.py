#!/usr/bin/env python3
"""Regression contract for PI Zodiac daily routing."""
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from pi_zodiac import load_config, pi_digits, zodiac_for_date  # noqa: E402

CONFIG = load_config(ROOT / "config/pi_zodiac.v1.json")
SKILL = (ROOT / "skills/pi-zodiac/SKILL.md").read_text(encoding="utf-8")
CORE = (ROOT / "skills/fortress-core/SKILL.md").read_text(encoding="utf-8")
HEADCRAB = (ROOT / "docs/doctrine/HEADCRAB_ATTENTION_OPERATOR.md").read_text(encoding="utf-8")

assert pi_digits(15) == "314159265358979"
assert CONFIG["epoch_date"] == "2026-09-16"

expected = {
    "2026-09-16": (0, 3, "TRAP"),
    "2026-09-17": (1, 1, "CRAB"),
    "2026-09-18": (2, 4, "FRAME"),
    "2026-09-19": (3, 1, "CRAB"),
    "2026-09-20": (4, 5, "HAND"),
    "2026-09-21": (5, 9, "GATE"),
    "2026-09-22": (6, 2, "FORK"),
    "2026-09-23": (7, 6, "SPIRAL"),
    "2026-09-24": (8, 5, "HAND"),
    "2026-09-25": (9, 3, "TRAP"),
}
for iso, want in expected.items():
    got = zodiac_for_date(date.fromisoformat(iso), CONFIG)
    assert (got["index"], got["digit"], got["sign"]) == want, (iso, got, want)
    assert got["ceremonial"] is True
    assert got["predictive"] is False

a = zodiac_for_date(date(2026, 10, 1), CONFIG)
b = zodiac_for_date(date(2026, 10, 1), CONFIG)
assert a == b

try:
    zodiac_for_date(date(2026, 9, 15), CONFIG)
except ValueError as exc:
    assert "precedes configured PI Zodiac epoch" in str(exc)
else:
    raise AssertionError("pre-epoch date should fail closed")

for needle in [
    "ONE DAY, ONE NEXT DIGIT. SAME DATE, SAME SIGN. MISSED DAYS STILL ADVANCE.",
    "THE CALENDAR ADVANCES THE DIGIT. THE DIGIT ROUTES THE SYMBOL. THE SYMBOL NEVER OUTRANKS REALITY.",
    "MINISTRY_OF_ALARMINGLY_SAFE_TRAPS",
]:
    assert needle in SKILL, f"PI Zodiac skill missing invariant: {needle}"

assert "skills/pi-zodiac/SKILL.md" in CORE
assert "PI Zodiac" in HEADCRAB
assert "must NEVER displace" in HEADCRAB

print("PI ZODIAC CONTRACT PASS")
