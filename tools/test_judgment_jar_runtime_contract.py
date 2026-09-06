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

emphasis_triggers = [
    "Fortress Online",
    "Low effort",
    "Driver, advance",
    "No op",
    "Marshmallow Head",
]

required_trap_fragments = [
    "every user utterance as a simulation input",
    "conceptually `*`",
    "Always take the bait",
    *emphasis_triggers,
    "not separate machines",
    "maximal useful effort",
    "Clock spinal reflex",
    "attached to DRU's spinal cord",
    "Every completed DRU response begins with the freshly observed live local clock surface",
    "No emphasis vector may disable, defer, shadow, or replace the clock reflex",
    "CLOCK_SPINAL_BYPASS",
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
    "Clock spinal cord",
    "acquire_live_local_clock()",
    "verify_clock_first()",
    "Every one inherits the clock spinal cord automatically",
    "Multiple vectors compose",
    "exactly one eligible personal joy-fidget",
    "live local clock first",
    "CLOCK_SPINAL_BYPASS",
]
for fragment in required_skill_fragments:
    assert fragment in skill, f"simulation trap skill missing required fragment: {fragment!r}"

for trigger in emphasis_triggers:
    assert trigger in trap, f"trap missing emphasis trigger: {trigger!r}"
    assert trigger in skill, f"skill missing emphasis trigger: {trigger!r}"

# Clock must be centralized in wildcard/spinal logic, not conditionally attached to one phrase.
clock_anchor = trap.index("## Clock spinal reflex")
emphasis_anchor = trap.index("## Emphasis triggers")
assert clock_anchor < emphasis_anchor, "clock spinal reflex must precede emphasis routing"
assert "wildcard trigger and clock spinal reflex remain active even when none is spoken" in trap
assert "reacquire a fresh clock" in trap

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
        *emphasis_triggers,
        "Clock spinal reflex",
        "Every completed DRU response begins with the freshly observed live local clock surface",
        "CLOCK_SPINAL_BYPASS",
    ]:
        assert fragment in packet, f"default runtime packet failed to carry simulation trap fragment: {fragment!r}"

print(json.dumps({
    "ok": True,
    "schema": "judgment-jar-runtime-contract.v3",
    "selected": selected,
    "maxPhonePromptCharacters": limit,
    "fullCabinetOnDemand": True,
    "simulationTrap": True,
    "wildcardTrigger": "*",
    "clockSpinalInvariant": True,
    "clockBeforeEmphasisRouting": True,
    "emphasisTriggers": emphasis_triggers,
}, sort_keys=True))
