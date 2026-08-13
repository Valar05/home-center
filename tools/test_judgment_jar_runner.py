#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import types
from pathlib import Path

# Standalone scratch execution supplies import-compatible stubs.  In-repository
# execution resolves the real sibling modules instead.
if "judgment_jar_common" not in sys.modules:
    common = types.ModuleType("judgment_jar_common")
    common.CONFIG_PATH = Path("config/judgment-jars.v1.json")
    common.DEFAULT_CACHE = Path("cache.json")
    common.RegistryError = type("RegistryError", (RuntimeError,), {})
    common.read_config = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
    common.write_atomic = lambda path, value: Path(path).write_text(json.dumps(value), encoding="utf-8")
    sys.modules["judgment_jar_common"] = common
    truth = types.ModuleType("judgment_jar_receipt_truth")
    truth.record = lambda *_args, **_kwargs: {}
    sys.modules["judgment_jar_receipt_truth"] = truth
    registry_module = types.ModuleType("judgment_jar_registry")
    registry_module.ensure_registry = lambda *_args, **_kwargs: ({}, {})
    registry_module.prompt_text = lambda *_args, **_kwargs: ""
    registry_module.resolve_jar = lambda reg, ref: next((j for j in reg.get("jars", []) if j.get("id") == (reg.get("aliasIndex", {}).get(ref, ref))), None)
    sys.modules["judgment_jar_registry"] = registry_module

import judgment_jar_runner as runner


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


registry = {
    "schema": "registry.v1", "registryDigest": "digest", "homeCenter": {"state": "fresh"},
    "aliasIndex": {"android-67": "android-67", "she-raw": "she-raw", "she raw": "she-raw"},
    "jars": [
        {"id": "android-67", "title": "Android 67", "origin": "home_center", "sourceFileId": "a67"},
        {"id": "she-raw", "title": "She-Raw", "origin": "home_center", "sourceFileId": "sraw"},
    ],
}


def ensure(*_args, **_kwargs):
    return registry, {"state": "fresh"}


def prompt(reg, keys, include_all):
    assert reg is registry and not include_all
    return "\n".join(f"JAR:{key}" for key in keys)


counter = 0
def recorder(_registry, jar, _config, **kwargs):
    global counter
    counter += 1
    return {"ok": True, "state": recorder.state, "receipt": {
        "receiptId": f"r{counter}", "dedupFingerprint": f"f{counter}",
        "jar": {"id": jar["id"]}, "output": {"kind": kwargs["output_kind"]},
    }}
recorder.state = "PENDING_HOME_CENTER"


def config_file(directory: Path) -> Path:
    path = directory / "config.json"
    path.write_text(json.dumps({"runtime": {"maxPhonePromptCharacters": 18000}}), encoding="utf-8")
    return path


original_prompt = runner.prompt_text
runner.prompt_text = prompt
try:
    with tempfile.TemporaryDirectory() as temp:
        cfg = config_file(Path(temp))
        state = runner.prepare({"jarRefs": ["android-67", "she raw"], "candidate": "Story."}, config_path=cfg, ensure=ensure, recorder=recorder)
        assert state["jarIds"] == ["android-67", "she-raw"]
        assert state["state"] == "REGNET_PENDING" and not state["releaseAllowed"]
        assert len(state["contextReceipts"]) == 2
        assert len({x["receiptId"] for x in state["contextReceipts"]}) == 2

        try:
            runner.ingest_gate(state, {"gate": "venice", "artifact": {}}, config_path=cfg, ensure=ensure, recorder=recorder)
            raise AssertionError("Venice before Regnet must fail")
        except runner.RunnerError:
            pass

        regnet = {"reviewer": "Regnet", "verdict": "PASS", "source": "regnet://qa/1"}
        regnet["sha256"] = digest(regnet)
        state = runner.ingest_gate(state, {"gate": "regnet", "artifact": regnet}, config_path=cfg, ensure=ensure, recorder=recorder)
        assert state["state"] == "VENICE_PENDING"

        venice = {"reviewer": "Venice", "verdict": "CONTINUE", "source": "venice://review/1"}
        venice["sha256"] = digest(venice)
        state = runner.ingest_gate(state, {"gate": "venice", "artifact": venice}, config_path=cfg, ensure=ensure, recorder=recorder)
        assert state["state"] == "CONTINUE" and not state["releaseAllowed"]
        assert len(state["outputReceipts"]) == 2
        assert set(x["receiptId"] for x in state["contextReceipts"]).isdisjoint(x["receiptId"] for x in state["outputReceipts"])

        for receipt in state["contextReceipts"] + state["outputReceipts"]:
            receipt["state"] = "DELIVERED"
        assert runner.release_allowed(state)

        stopped = json.loads(json.dumps(state))
        stopped["gates"]["venice"]["verdict"] = "STOP"
        assert not runner.release_allowed(stopped)

        bad = {"reviewer": "Venice", "verdict": "CONTINUE", "source": "venice://bad", "sha256": "0" * 64}
        try:
            runner._artifact({"artifact": bad}, "Venice", {"CONTINUE", "STOP"})
            raise AssertionError("bad digest must fail")
        except runner.RunnerError:
            pass

        try:
            runner.prepare({"jarRefs": ["missing"], "candidate": "x"}, config_path=cfg, ensure=ensure, recorder=recorder)
            raise AssertionError("missing jar must fail")
        except runner.RunnerError:
            pass
finally:
    runner.prompt_text = original_prompt

print(json.dumps({"ok": True, "schema": "judgment-jar-runner-test.v1"}, sort_keys=True))
