#!/usr/bin/env python3
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


obs = load("adam_observation_ledger", ROOT / "tools" / "adam_observation_ledger.py")
adam = load("adam", ROOT / "tools" / "adam.py")


assert obs.parse_observation("Log three more drops") == {
    "eventType": "substance_observation", "substance": "nicotine_e_liquid",
    "count": 3, "unit": "drop", "route": "oral_reported",
}
assert obs.parse_observation("No more nicotine tonight")["eventType"] == "commitment"
assert obs.parse_observation("Pills taken")["status"] == "confirmed_taken"
assert obs.parse_observation("Hunger seven")["score"] == 7
assert obs.parse_observation("Log two puffs of weed")["substance"] == "cannabis"
assert obs.parse_observation("Weed helped nausea")["eventType"] == "effect_observation"
assert adam.classify_mode("Log three more drops")[0] == "observation"
assert adam.classify_mode("No more nicotine tonight")[0] == "observation"
assert adam.classify_mode("Pills taken")[0] == "observation"
try:
    obs.parse_observation("How many drops should I take next?")
except obs.ObservationError:
    pass
else:
    raise AssertionError("prospective dosing must fail closed")

print("adam_observation_ledger contract passed")
