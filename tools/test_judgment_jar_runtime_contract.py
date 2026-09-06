#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from judgment_jar_common import CONFIG_PATH, ROOT, read_config
from judgment_jar_registry import ensure_registry, prompt_text, resolve_jar


config = read_config(CONFIG_PATH)
runtime = dict(config.get("runtime") or {})
selected = [str(value) for value in runtime.get("defaultPhoneJarIds") or []]
limit = int(runtime.get("maxPhonePromptCharacters") or 0)
assert selected
assert limit > 0
assert runtime.get("fullCabinetOnDemand") is True
assert "simulation-trap" in selected, "simulation-trap must be present in defaultPhoneJarIds"

trap_path = ROOT / ".continue/rules/05-judgement-jar-simulation-trap.md"
skill_path = ROOT / "skills/dru-simulation-trap/SKILL.md"
assert trap_path.exists(), f"missing wildcard simulation trap: {trap_path}"
assert skill_path.exists(), f"missing DRU simulation trap skill: {skill_path}"
trap = trap_path.read_text(encoding="utf-8")
skill = skill_path.read_text(encoding="utf-8")

required_trap_fragments = [
    "every user utterance as a simulation input",
    "conceptually `*`",
    "Always take the bait",
    "Fortress Online",
    "Low effort",
    "Driver, advance",
    "No op",
    "Marshmallow Head",
    "not separate machines",
    "maximal useful effort",
    "WILDCARD_BYPASS",
    "KEYWORD_ONLY_FORTRESS",
    "EMPHASIS_ISOLATION",
]
for fragment in required_trap_fragments:
    assert fragment in trap, f"simulation trap missing required fragment: {fragment!r}"

required_skill_fragments = [
    "wildcard catcher",
    'on_user_message("*")',
    "Named phrases do not turn the system on",
    "Multiple vectors compose",
    "exactly one eligible personal joy-fidget",
    "live local clock first",
]
for fragment in required_skill_fragments:
    assert fragment in skill, f"simulation trap skill missing required fragment: {fragment!r}"

with tempfile.TemporaryDirectory(prefix="judgment-jar-runtime-") as temp:
    cache = Path(temp) / "judgment-jars.json"
    registry, _ = ensure_registry(ROOT, cache, offline=True, config_path=CONFIG_PATH)
    missing = [reference for reference in selected if resolve_jar(registry, reference) is None]
    assert not missing, f"configured defaultPhoneJarIds do not resolve: {missing}"
    packet = prompt_text(registry, selected, False)
    assert packet.strip()
    assert len(packet) <= limit, f"configured Jar packet is too large: {len(packet)} > {limit}"
    for fragment in [
        "every user utterance as a simulation input",
        "Fortress Online",
        "Low effort",
        "Driver, advance",
        "No op",
        "Marshmallow Head",
    ]:
        assert fragment in packet, f"default runtime packet failed to carry simulation trap fragment: {fragment!r}"

print(json.dumps({
    "ok": True,
    "schema": "judgment-jar-runtime-contract.v2",
    "selected": selected,
    "maxPhonePromptCharacters": limit,
    "fullCabinetOnDemand": True,
    "simulationTrap": True,
    "wildcardTrigger": "*",
    "emphasisTriggers": [
        "Fortress Online",
        "Low effort",
        "Driver, advance",
        "No op",
        "Marshmallow Head",
    ],
}, sort_keys=True))
