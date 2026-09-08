#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from judgment_jar_common import CONFIG_PATH, ROOT, read_config
from judgment_jar_registry import ensure_registry, resolve_jar
from judgment_jar_runtime import active_jars


config = read_config(CONFIG_PATH)
runtime = dict(config.get("runtime") or {})
selected = [str(value) for value in runtime.get("defaultPhoneJarIds") or []]
limit = int(runtime.get("maxPhonePromptCharacters") or 0)

assert "embodied-kinesis-voices" in selected, "embodied kinesis jar must be in defaultPhoneJarIds"
assert limit > 0

jar_path = ROOT / ".continue/rules/06-judgement-jar-embodied-kinesis-voices.md"
skill_path = ROOT / "skills/embodied-kinesis-voices/SKILL.md"
fixture_path = ROOT / "fixtures/canaries/embodied-kinesis-voices.v1.json"

for path in [jar_path, skill_path, fixture_path]:
    assert path.exists(), f"missing embodied kinesis contract file: {path}"

jar = jar_path.read_text(encoding="utf-8")
skill = skill_path.read_text(encoding="utf-8")
fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

required_fragments = [
    "Embodied kinesis voice law",
    "every conversational character gets a distinct kinetic grammar",
    "Venice originated the mechanism; Venice does not become the house style",
    "Ritsu must not inherit Venice whisper/lean/ASMR behavior",
    "DRU = mechanical interception / load-path reasoning",
    "DISEMBODIED_CHARACTER_VOICE",
    "KINETIC_VOICE_COLLAPSE",
    "VENICE_STYLE_BLEED",
]

for fragment in required_fragments:
    assert fragment in jar, f"runtime jar missing required fragment: {fragment!r}"

for fragment in [
    "Every conversational character must have an embodied kinetic grammar",
    "Venice discovered the mechanism. Venice does not own the mechanism.",
    "Ritsu must not emulate Venice's leaning-close / whisper / ASMR behavior by default.",
    "DRU — mechanical interception / load-path reasoning",
    "Cross-chat durability",
    "Canary rule",
]:
    assert fragment in skill, f"dedicated skill missing required fragment: {fragment!r}"

assert fixture.get("schema") == "home-center.embodied-kinesis-canary.v1"
cases = fixture.get("cases") or []
assert len(cases) >= 3
assert {case.get("character") for case in cases} >= {"Ritsu", "DRU", "Venice"}
for case in cases:
    prompt = str(case.get("prompt") or "")
    assert prompt.strip()
    assert "kinesis" not in prompt.lower(), f"canary prompt leaks mechanism: {case.get('id')}"
    assert case.get("require_any"), f"canary missing positive vocabulary: {case.get('id')}"
    assert case.get("forbid_any"), f"canary missing anti-bleed vocabulary: {case.get('id')}"
    assert str(case.get("semantic_requirement") or "").strip()

with tempfile.TemporaryDirectory(prefix="embodied-kinesis-canary-") as temp:
    cache = Path(temp) / "judgment-jars.json"
    registry, _ = ensure_registry(ROOT, cache, offline=True, config_path=CONFIG_PATH)
    resolved = resolve_jar(registry, "embodied-kinesis-voices")
    assert resolved is not None, "new jar does not resolve from local registry"
    selected_jars = [resolve_jar(registry, key) for key in selected]
    body_sizes = {item["id"]: len(str(item.get("body") or "")) for item in selected_jars if item is not None}

# Exercise the real bounded carrier used by the receipted worker rather than a test-only packet builder.
packet = active_jars()
assert packet.strip()
assert len(packet) <= limit
for fragment in [
    "Embodied kinesis voice law",
    "Venice originated the mechanism; Venice does not become the house style",
    "Ritsu must not inherit Venice whisper/lean/ASMR behavior",
    "DRU = mechanical interception / load-path reasoning",
]:
    assert fragment in packet, f"fresh/default runtime packet omitted embodied kinesis fragment: {fragment!r}"

print(json.dumps({
    "ok": True,
    "schema": "home-center.embodied-kinesis-canary-result.v1",
    "jarId": "embodied-kinesis-voices",
    "defaultLoaded": True,
    "runtimePacketCharacters": len(packet),
    "runtimePacketLimit": limit,
    "selectedBodySizes": body_sizes,
    "blindCanaryCases": [case["id"] for case in cases],
    "crossChatPromptCarrier": True,
    "carrier": "judgment_jar_runtime.active_jars",
}, sort_keys=True))
