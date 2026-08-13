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

with tempfile.TemporaryDirectory(prefix="judgment-jar-runtime-") as temp:
    cache = Path(temp) / "judgment-jars.json"
    registry, _ = ensure_registry(ROOT, cache, offline=True, config_path=CONFIG_PATH)
    missing = [reference for reference in selected if resolve_jar(registry, reference) is None]
    assert not missing, f"configured defaultPhoneJarIds do not resolve: {missing}"
    packet = prompt_text(registry, selected, False)
    assert packet.strip()
    assert len(packet) <= limit, f"configured Jar packet is too large: {len(packet)} > {limit}"

print(json.dumps({
    "ok": True,
    "schema": "judgment-jar-runtime-contract.v1",
    "selected": selected,
    "maxPhonePromptCharacters": limit,
    "fullCabinetOnDemand": True,
}, sort_keys=True))
