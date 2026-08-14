#!/usr/bin/env python3
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("fortress_prompt", ROOT / "tools/fortress_prompt.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(mod)

cfg = json.loads((ROOT / "config/fortress-prompt.json").read_text())

assert mod.resolve("git status", cfg)["name"] == "git-status"
assert mod.resolve("  GIT   STATUS ", cfg)["name"] == "git-status"
assert mod.resolve("please maybe git status", cfg) is None
assert "git status" in mod.suggest("git stats", cfg)
argv = mod.render_argv(mod.resolve("eve status", cfg), cfg)
assert argv[-1] == "status"
assert "eve-session" in argv[0]

base = {"a": 1, "nested": {"x": 1, "y": 2}, "items": [1, 2]}
over = {"nested": {"y": 9}, "items": [7]}
merged = mod.deep_merge(base, over)
assert merged == {"a": 1, "nested": {"x": 1, "y": 9}, "items": [7]}

print("fortress prompt tests: OK")
