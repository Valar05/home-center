#!/usr/bin/env python3
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "tools" / "adam.py"
spec = importlib.util.spec_from_file_location("adam_router_under_test", path)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

cases = {
    "hello adam": "chat",
    "what do you think about this?": "chat",
    "continue the overlay work": "continue",
    "fix the broken overlay": "continue",
    "build the phone canary": "continue",
    "Vlad, give me a second opinion": "vlad",
    "play music for this": "radio",
    "show recent texts": "text",
    "quit silent hunt": "continue",
}
for raw, expected in cases.items():
    actual, reason = mod.classify_mode(raw)
    assert actual == expected, (raw, expected, actual, reason)

# Natural language classification never grants arbitrary shell authority.
for raw in [
    "rm -rf whatever",
    "bash please do something",
    "run sudo command",
    "execute shell now",
]:
    actual, _ = mod.classify_mode(raw)
    assert actual != "terminal", (raw, actual)

assert "auto" in mod.ONE_SHOT_MODES
print("Adam Beard deterministic AUTO routing contract: PASS")
