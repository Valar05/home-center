#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import types
from pathlib import Path

# Unit isolation is explicit: never accidentally half-load production modules.
if True:
    common = types.ModuleType("judgment_jar_common")
    common.CONFIG_PATH = Path("config/judgment-jars.v1.json")
    common.DEFAULT_CACHE = Path("cache.json")
    common.RegistryError = type("RegistryError", (RuntimeError,), {})
    common.read_config = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
    common.write_atomic = lambda path, value: Path(path).write_text(json.dumps(value), encoding="utf-8")
    sys.modules["judgment_jar_common"] = common
    receipts = types.ModuleType("judgment_jar_receipts")
    receipts.paths = lambda config: {"delivered": Path(config["receipts"]["delivered"])}
    sys.modules["judgment_jar_receipts"] = receipts
    truth = types.ModuleType("judgment_jar_receipt_truth")
    truth.build = lambda registry, jar, **kwargs: {
        "receiptId": "random", "dedupFingerprint": "old", "jar": {"id": jar["id"]},
        "output": {"kind": kwargs["output_kind"]},
    }
    truth.capture = lambda receipt, config: {"ok": True, "state": "PENDING_HOME_CENTER", "receipt": receipt}
    truth.fingerprint = lambda receipt: digest({k: v for k, v in receipt.items() if k != "dedupFingerprint"})
    truth.validate = lambda receipt, config: None
    sys.modules["judgment_jar_receipt_truth"] = truth
    registry_module = types.ModuleType("judgment_jar_registry")
    registry_module.ensure_registry = lambda *_args, **_kwargs: ({}, {})
    registry_module.fetch_native_source = lambda *_args, **_kwargs: {}
    registry_module.resolve_jar = lambda reg, ref: next(
        (j for j in reg.get("jars", []) if j.get("id") == reg.get("aliasIndex", {}).get(ref, ref)), None
    )
    sys.modules["judgment_jar_registry"] = registry_module

import judgment_jar_runner as runner


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


registry = {
    "schema": "registry.v1", "registryDigest": "digest", "homeCenter": {"state": "fresh"},
    "aliasIndex": {
        "android-67": "android-67", "she-raw": "she-raw", "she raw": "she-raw",
        "regnet": "regnet-qa", "venice": "venice-final",
    },
    "jars": [
        {"id": "android-67", "title": "Android 67", "status": "mature", "origin": "home_center", "sourceFileId": "a67"},
        {"id": "she-raw", "title": "She-Raw", "status": "mature", "origin": "home_center", "sourceFileId": "sraw"},
        {"id": "regnet-qa", "title": "Regnet QA", "status": "mature", "origin": "home_center", "sourceFileId": "regnet"},
        {"id": "venice-final", "title": "Venice", "status": "mature", "origin": "home_center", "sourceFileId": "venice"},
    ],
}


def ensure(*_args, **_kwargs):
    return registry, {"state": "fresh"}


def prompt(reg, keys, include_all):
    assert reg is registry and not include_all
    return "\n".join(f"JAR:{key}" for key in keys)


def native_fetch(jar, _config, _cache, **_kwargs):
    content = f"NATIVE JAR:{jar['id']}"
    return {
        "ok": True, "state": "synced", "jarId": jar["id"],
        "sourceFileId": jar.get("sourceFileId"), "sourceType": "document",
        "sourceSha256": hashlib.sha256(content.encode()).hexdigest(), "content": content,
    }


counter = 0
recorded_jar_ids = []
recorded_requests = {}


def recorder(_registry, jar, _config, **kwargs):
    global counter
    request_key = (kwargs["request_id"], jar["id"], kwargs["output_kind"], kwargs["output_text"])
    if request_key in recorded_requests:
        return recorded_requests[request_key]
    counter += 1
    recorded_jar_ids.append(jar["id"])
    result = {"ok": True, "state": recorder.state, "receipt": {
        "receiptId": f"r{counter}", "dedupFingerprint": f"f{counter}",
        "jar": {"id": jar["id"]}, "output": {"kind": kwargs["output_kind"]},
    }}
    recorded_requests[request_key] = result
    return result


recorder.state = "PENDING_HOME_CENTER"


def deterministic_primitive_contract():
    captured = {}

    def build(_registry, jar, **kwargs):
        return {"receiptId": "random", "jar": {"id": jar["id"]},
                "output": {"kind": kwargs["output_kind"]}, "payload": kwargs["output_text"]}

    def fingerprint(receipt):
        return digest({k: v for k, v in receipt.items() if k != "dedupFingerprint"})

    def capture(receipt, _config):
        duplicate = receipt["receiptId"] in captured
        captured.setdefault(receipt["receiptId"], json.loads(json.dumps(receipt)))
        return {"ok": True, "state": "PENDING_HOME_CENTER", "duplicate": duplicate,
                "receipt": captured[receipt["receiptId"]]}

    kwargs = {"output_kind": "answer", "output_text": "proof"}
    first = runner.deterministic_record(
        registry, registry["jars"][0], {}, operation_key="unit:retry",
        builder=build, capturer=capture, fingerprinter=fingerprint, **kwargs,
    )
    second = runner.deterministic_record(
        registry, registry["jars"][0], {}, operation_key="unit:retry",
        builder=build, capturer=capture, fingerprinter=fingerprint, **kwargs,
    )
    assert first["receipt"]["receiptId"] == second["receipt"]["receiptId"]
    assert first["receipt"]["dedupFingerprint"] == second["receipt"]["dedupFingerprint"]
    assert second["duplicate"] is True


def config_file(directory: Path, delivered: Path) -> Path:
    path = directory / "config.json"
    path.write_text(json.dumps({
        "runtime": {"maxPhonePromptCharacters": 18000},
        "receipts": {"delivered": str(delivered)},
    }), encoding="utf-8")
    return path


def gate_artifact(state, reviewer, verdict, source, **overrides):
    value = {
        "reviewer": reviewer, "verdict": verdict, "source": source,
        "candidateSha256": state["candidateSha256"],
        "contextPacketSha256": state["contextPacketSha256"],
        "createdOutputSha256": state["createdOutputSha256"],
        "groupId": state["groupId"], "registryDigest": state["registryDigest"],
        "jarIds": state["jarIds"],
        "nativeSourceDigests": [item["sourceSha256"] for item in state["nativeSources"]],
    }
    value.update(overrides)
    value["sha256"] = digest(value)
    return value


def write_source_receipt(delivered, state, artifact):
    gate = "regnet" if artifact["reviewer"] == "Regnet QA" else "venice"
    authority = {"receiptId": f"source-{gate}-{artifact['verdict'].lower()}",
                 "dedupFingerprint": f"source-fp-{gate}-{artifact['verdict'].lower()}"}
    value = {
        "receiptId": authority["receiptId"], "dedupFingerprint": authority["dedupFingerprint"],
        "receiptDeliveryState": "DELIVERED", "homeCenterDeliveryState": "DELIVERED",
        "homeCenter": {"readbackVerified": True}, "actor": artifact["reviewer"],
        "output": {"kind": "review_verdict", "sha256": artifact["sha256"]},
        "invocation": {"groupId": state["groupId"], "source": runner.TRUSTED_GATE_SOURCES[gate]},
        "jar": {"id": registry["aliasIndex"][gate], "registryDigest": state["registryDigest"]},
        "metadata": {"authorityRoute": runner.TRUSTED_AUTHORITY_ROUTES[gate]},
    }
    (delivered / f"{authority['receiptId']}.json").write_text(json.dumps(value), encoding="utf-8")
    return authority


def gate_request(gate, request_id, artifact):
    reviewer = "regnet" if artifact["reviewer"] == "Regnet QA" else "venice"
    verdict = artifact["verdict"].lower()
    return {
        "gate": gate, "requestId": request_id, "artifact": artifact,
        "authorityReceipt": {"receiptId": f"source-{reviewer}-{verdict}",
                             "dedupFingerprint": f"source-fp-{reviewer}-{verdict}"},
    }


def expect_error(call, contains):
    try:
        call()
        raise AssertionError(f"expected RunnerError containing {contains!r}")
    except runner.RunnerError as exc:
        assert contains in str(exc), str(exc)


def production_contract() -> dict:
    """Run real build/fingerprint/capture when this test is staged beside production modules."""
    truth_path = Path(__file__).with_name("judgment_jar_receipt_truth.py")
    if not truth_path.exists():
        return {"skipped": True, "reason": "production sibling modules unavailable in scratch"}
    code = r'''
import json, tempfile
from pathlib import Path
import judgment_jar_common as common
import judgment_jar_receipts as receipts
import judgment_jar_runner as runner

config = common.read_config(common.CONFIG_PATH)
original = receipts.paths(config)
with tempfile.TemporaryDirectory() as td:
    root = Path(td)
    replacement = {}
    for key, old in original.items():
        old = Path(old)
        target = root / (key + old.suffix if old.suffix else key)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not old.suffix:
            target.mkdir(parents=True, exist_ok=True)
        replacement[key] = target
    receipts.paths = lambda _config: replacement
    registry = {
        "schema": "home-center.judgment-jars.registry.v2",
        "registryDigest": "a" * 64,
        "sourceCommit": "production-contract-fixture",
    }
    jar = {
        "id": "contract-jar",
        "origin": "home-center-cabinet",
        "title": "Contract Jar",
        "sourceFileId": "production-contract-fixture",
        "sourceSha256": "b" * 64,
        "status": "mature",
    }
    kwargs = dict(
        output_kind="answer", output_text="crash retry proof", summary="contract",
        actor="Adam", intent="test deterministic capture", surface="jar",
        decision_action="capture", input_text="input", output_status="created",
        request_id="contract-request", group_id="contract-group", references=[],
        source="judgment-jar-runner.production-contract", metadata={"contract": True},
    )
    first = runner.deterministic_record(registry, jar, config, operation_key="contract:crash-retry", **kwargs)
    second = runner.deterministic_record(registry, jar, config, operation_key="contract:crash-retry", **kwargs)
    assert first["receipt"]["receiptId"] == second["receipt"]["receiptId"]
    assert first["receipt"]["dedupFingerprint"] == second["receipt"]["dedupFingerprint"]
    assert second["duplicate"] is True
    print(json.dumps({"skipped": False, "receiptId": second["receipt"]["receiptId"], "state": second["state"]}))
'''
    result = subprocess.run([sys.executable, "-c", code], cwd=str(Path(__file__).parent),
                            text=True, capture_output=True)
    if result.returncode:
        raise AssertionError(
            "production receipt contract subprocess failed\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    value = json.loads(result.stdout.strip())
    assert value["skipped"] is False
    return value


try:
    deterministic_primitive_contract()
    with tempfile.TemporaryDirectory() as temp:
        temp_path = Path(temp)
        delivered = temp_path / "delivered"
        delivered.mkdir()
        cfg = config_file(temp_path, delivered)

        expect_error(
            lambda: runner.prepare({"jarRefs": ["android-67"], "candidate": "Story."}, config_path=cfg, ensure=ensure, recorder=recorder),
            "requestId is required",
        )
        crash_calls = 0
        first_crash_receipt = None

        def crash_once(*args, **kwargs):
            global crash_calls, first_crash_receipt
            crash_calls += 1
            if crash_calls == 2:
                raise OSError("simulated prepare crash")
            result = recorder(*args, **kwargs)
            if first_crash_receipt is None:
                first_crash_receipt = result["receipt"]["receiptId"]
            return result

        crash_request = {
            "requestId": "crash-retry", "jarRefs": ["android-67", "she-raw"],
            "candidate": "Crash-safe candidate.",
        }
        try:
            runner.prepare(crash_request, config_path=cfg, ensure=ensure, recorder=crash_once, native_fetcher=native_fetch)
            raise AssertionError("simulated prepare crash must escape")
        except OSError as exc:
            assert "simulated prepare crash" in str(exc)
        before_retry = counter
        retry_state = runner.prepare(
            crash_request, config_path=cfg, ensure=ensure, recorder=recorder, native_fetcher=native_fetch,
        )
        assert retry_state["contextReceipts"][0]["receiptId"] == first_crash_receipt
        assert counter == before_retry + 1, "retry must deduplicate already captured per-Jar receipt"
        assert retry_state["groupId"] == runner.prepare(
            crash_request, config_path=cfg, ensure=ensure, recorder=recorder, native_fetcher=native_fetch,
        )["groupId"]

        state = runner.prepare({
            "requestId": "request-1", "groupId": "group-1",
            "jarRefs": ["android-67", "she raw"], "candidate": "Story.",
        }, config_path=cfg, ensure=ensure, recorder=recorder, native_fetcher=native_fetch)
        assert state["jarIds"] == ["android-67", "she-raw"]
        assert state["state"] == "CONTEXT_RECEIPTED" and not state["releaseAllowed"]
        assert len(state["contextReceipts"]) == 2
        assert len({x["receiptId"] for x in state["contextReceipts"]}) == 2
        assert runner._prepare_replay(state, state["prepareRequest"]) is state
        conflicting_prepare = dict(state["prepareRequest"])
        conflicting_prepare["candidate"] = "Conflict."
        expect_error(lambda: runner._prepare_replay(state, conflicting_prepare), "conflicting prepare replay")

        tampered = json.loads(json.dumps(state))
        tampered["candidate"] += " tampered"
        expect_error(lambda: runner.validate_state(tampered), "candidateSha256 does not match")
        tampered = json.loads(json.dumps(state))
        tampered["contextPacket"] += " tampered"
        expect_error(lambda: runner.validate_state(tampered), "contextPacketSha256 does not match")
        tampered = json.loads(json.dumps(state))
        tampered["contextReceipts"][1]["receiptId"] = tampered["contextReceipts"][0]["receiptId"]
        expect_error(lambda: runner.validate_state(tampered), "duplicate receiptId")

        state = runner.record_output(
            state, {"requestId": "output-1", "createdOutput": "Candidate scene.", "outputKind": "answer"},
            config_path=cfg, ensure=ensure, recorder=recorder,
        )
        assert state["state"] == "REGNET_PENDING" and len(state["outputReceipts"]) == len(state["jarIds"])
        tampered = json.loads(json.dumps(state))
        tampered["createdOutput"] += " tampered"
        expect_error(lambda: runner.validate_state(tampered), "createdOutputSha256 does not match")
        tampered = json.loads(json.dumps(state))
        tampered["outputReceipts"][0]["outputKind"] = "review_verdict"
        expect_error(lambda: runner.validate_state(tampered), "created-output receipt")
        assert runner.record_output(
            state, {"requestId": "output-replay", "createdOutput": "Candidate scene.", "outputKind": "answer"},
            config_path=cfg, ensure=ensure, recorder=recorder,
        ) is state
        expect_error(
            lambda: runner.record_output(
                state, {"requestId": "output-conflict", "createdOutput": "Different.", "outputKind": "answer"},
                config_path=cfg, ensure=ensure, recorder=recorder,
            ), "divergent replay",
        )

        venice_early = gate_artifact(state, "Venice", "CONTINUE", "venice://review/early")
        expect_error(
            lambda: runner.ingest_gate(state, gate_request("venice", "early", venice_early), config_path=cfg, ensure=ensure, recorder=recorder),
            "illegal venice gate transition",
        )
        missing_binding = gate_artifact(state, "Regnet QA", "PASS", "regnet://qa/missing")
        missing_binding.pop("groupId")
        missing_binding["sha256"] = digest({k: v for k, v in missing_binding.items() if k != "sha256"})
        expect_error(
            lambda: runner.ingest_gate(state, gate_request("regnet", "missing-binding", missing_binding), config_path=cfg, ensure=ensure, recorder=recorder),
            "artifact groupId is required",
        )
        mismatch = gate_artifact(state, "Regnet QA", "PASS", "regnet://qa/mismatch", registryDigest="wrong")
        expect_error(
            lambda: runner.ingest_gate(state, gate_request("regnet", "mismatch", mismatch), config_path=cfg, ensure=ensure, recorder=recorder),
            "artifact registryDigest does not match",
        )
        for field, wrong, message in (
            ("candidateSha256", "0" * 64, "artifact candidateSha256 does not match"),
            ("contextPacketSha256", "0" * 64, "artifact contextPacketSha256 does not match"),
            ("groupId", "wrong-group", "artifact groupId does not match"),
            ("jarIds", ["she-raw"], "artifact jarIds does not match"),
        ):
            artifact = gate_artifact(state, "Regnet QA", "PASS", f"regnet://qa/{field}", **{field: wrong})
            expect_error(
                lambda artifact=artifact: runner.ingest_gate(
                    state, gate_request("regnet", "binding-check", artifact),
                    config_path=cfg, ensure=ensure, recorder=recorder,
                ),
                message,
            )

        fail_state = runner.prepare({
            "requestId": "request-fail", "groupId": "group-fail",
            "jarRefs": ["android-67"], "candidate": "fail candidate",
        }, config_path=cfg, ensure=ensure, recorder=recorder, native_fetcher=native_fetch)
        fail_state = runner.record_output(
            fail_state, {"requestId": "output-fail", "createdOutput": "Fail output", "outputKind": "artifact"},
            config_path=cfg, ensure=ensure, recorder=recorder,
        )
        fail_artifact = gate_artifact(fail_state, "Regnet QA", "FAIL", "regnet://qa/fail")
        write_source_receipt(delivered, fail_state, fail_artifact)
        fail_state = runner.ingest_gate(
            fail_state, gate_request("regnet", "gate-regnet-fail", fail_artifact),
            config_path=cfg, ensure=ensure, recorder=recorder,
        )
        assert fail_state["state"] == "STOP" and not fail_state["releaseAllowed"]
        stop_venice = gate_artifact(fail_state, "Venice", "STOP", "venice://blocked")
        expect_error(
            lambda: runner.ingest_gate(
                fail_state, gate_request("venice", "blocked-venice", stop_venice),
                config_path=cfg, ensure=ensure, recorder=recorder,
            ),
            "illegal venice gate transition",
        )

        regnet = gate_artifact(state, "Regnet QA", "PASS", "regnet://qa/1")
        assert "sourceReceiptId" not in regnet and "sourceReceiptFingerprint" not in regnet
        expect_error(
            lambda: runner.ingest_gate(state, gate_request("regnet", "gate-regnet", regnet), config_path=cfg, ensure=ensure, recorder=recorder),
            "verified delivered regnet source receipt was not found",
        )
        authority = write_source_receipt(delivered, state, regnet)
        source_path = delivered / f"{authority['receiptId']}.json"
        wrong_source = json.loads(source_path.read_text(encoding="utf-8"))
        wrong_source["invocation"]["source"] = "untrusted"
        source_path.write_text(json.dumps(wrong_source), encoding="utf-8")
        expect_error(
            lambda: runner.ingest_gate(state, gate_request("regnet", "gate-regnet", regnet), config_path=cfg, ensure=ensure, recorder=recorder),
            "invocation source mismatch",
        )
        write_source_receipt(delivered, state, regnet)
        before_count = counter
        state = runner.ingest_gate(state, gate_request("regnet", "gate-regnet", regnet), config_path=cfg, ensure=ensure, recorder=recorder)
        assert state["state"] == "VENICE_PENDING"
        assert recorded_jar_ids[-1] == "regnet-qa"
        replay = runner.ingest_gate(state, gate_request("regnet", "gate-regnet", regnet), config_path=cfg, ensure=ensure, recorder=recorder)
        assert replay is state and counter == before_count + 1
        divergent_regnet = gate_artifact(state, "Regnet QA", "FAIL", "regnet://qa/2")
        expect_error(
            lambda: runner.ingest_gate(state, gate_request("regnet", "divergent-regnet", divergent_regnet), config_path=cfg, ensure=ensure, recorder=recorder),
            "divergent replay",
        )

        venice = gate_artifact(state, "Venice", "CONTINUE", "venice://review/1")
        write_source_receipt(delivered, state, venice)
        state = runner.ingest_gate(state, gate_request("venice", "gate-venice", venice), config_path=cfg, ensure=ensure, recorder=recorder)
        assert state["state"] == "VENICE_CONTINUE_PENDING_RECEIPTS"
        assert not state["releaseAllowed"]
        assert recorded_jar_ids[-1] == "venice-final"
        assert len(state["outputReceipts"]) == len(state["jarIds"]) + 2
        all_receipts = state["contextReceipts"] + state["outputReceipts"]
        assert len({r["receiptId"] for r in all_receipts}) == len(all_receipts)

        first = all_receipts[0]
        invalid_receipts = [
            {"receiptId": first["receiptId"], "dedupFingerprint": "wrong",
             "receiptDeliveryState": "DELIVERED", "homeCenterDeliveryState": "DELIVERED",
             "homeCenter": {"readbackVerified": True}},
            {"receiptId": first["receiptId"], "dedupFingerprint": first["dedupFingerprint"],
             "receiptDeliveryState": "PENDING", "homeCenterDeliveryState": "DELIVERED",
             "homeCenter": {"readbackVerified": True}},
            {"receiptId": first["receiptId"], "dedupFingerprint": first["dedupFingerprint"],
             "receiptDeliveryState": "DELIVERED", "homeCenterDeliveryState": "PENDING",
             "homeCenter": {"readbackVerified": True}},
            {"receiptId": first["receiptId"], "dedupFingerprint": first["dedupFingerprint"],
             "receiptDeliveryState": "DELIVERED", "homeCenterDeliveryState": "DELIVERED",
             "homeCenter": {"readbackVerified": False}},
        ]
        for index, invalid in enumerate(invalid_receipts):
            (delivered / f"invalid-{index}.json").write_text(json.dumps(invalid), encoding="utf-8")
        pending = runner.reconcile(state, config_path=cfg)
        assert pending["contextReceipts"][0]["state"] != "DELIVERED"
        assert pending["state"] == "VENICE_CONTINUE_PENDING_RECEIPTS"

        for index, receipt in enumerate(all_receipts):
            (delivered / f"receipt-{index}.json").write_text(json.dumps({"receipt": {
                "receiptId": receipt["receiptId"], "dedupFingerprint": receipt["dedupFingerprint"],
                "receiptDeliveryState": "DELIVERED", "homeCenterDeliveryState": "DELIVERED",
                "homeCenter": {"readbackVerified": True},
            }}), encoding="utf-8")
        state = runner.reconcile(state, config_path=cfg)
        assert state["state"] == "RELEASED" and state["releaseAllowed"]
        (delivered / "receipt-0.json").unlink()
        state = runner.reconcile(state, config_path=cfg)
        assert state["state"] == "VENICE_CONTINUE_PENDING_RECEIPTS" and not state["releaseAllowed"]

        replay = runner.ingest_gate(state, gate_request("venice", "gate-venice", venice), config_path=cfg, ensure=ensure, recorder=recorder)
        assert replay is state
        divergent_venice = gate_artifact(state, "Venice", "STOP", "venice://review/2")
        expect_error(
            lambda: runner.ingest_gate(state, gate_request("venice", "divergent-venice", divergent_venice), config_path=cfg, ensure=ensure, recorder=recorder),
            "divergent replay",
        )
        bad_digest = gate_artifact(state, "Venice", "CONTINUE", "venice://bad")
        bad_digest["sha256"] = "0" * 64
        expect_error(lambda: runner._artifact({"artifact": bad_digest}, "Venice", {"CONTINUE", "STOP"}), "sha256 mismatch")

        drift_state = runner.prepare({
            "requestId": "request-drift", "groupId": "group-drift",
            "jarRefs": ["android-67"], "candidate": "x",
        }, config_path=cfg, ensure=ensure, recorder=recorder, native_fetcher=native_fetch)
        drift_state = runner.record_output(
            drift_state, {"requestId": "output-drift", "createdOutput": "Drift output", "outputKind": "answer"},
            config_path=cfg, ensure=ensure, recorder=recorder,
        )
        drift_artifact = gate_artifact(drift_state, "Regnet QA", "PASS", "regnet://drift")
        write_source_receipt(delivered, drift_state, drift_artifact)
        drifted = json.loads(json.dumps(registry))
        drifted["registryDigest"] = "drifted"
        expect_error(
            lambda: runner.ingest_gate(
                drift_state, gate_request("regnet", "gate-regnet-drift", drift_artifact),
                config_path=cfg, ensure=lambda *_a, **_k: (drifted, {"state": "fresh"}), recorder=recorder,
            ),
            "registry drift detected",
        )
        expect_error(
            lambda: runner.prepare({"requestId": "missing", "jarRefs": ["missing"], "candidate": "x"}, config_path=cfg, ensure=ensure, recorder=recorder),
            "unknown Judgment Jar",
        )
finally:
    pass

print(json.dumps({"ok": True, "schema": "judgment-jar-runner-test.v3",
                  "productionContract": production_contract()}, sort_keys=True))
