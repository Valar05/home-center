#!/usr/bin/env python3
"""Fallback-fixture contract tests for judgment_jar_gate_import.

The injected modules below are explicitly fixtures.  Production API
compatibility is checked separately by test_judgment_jar_gate_import_production_contract.py.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import types
from pathlib import Path


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha(value):
    return hashlib.sha256(value.encode()).hexdigest()


runner = types.ModuleType("judgment_jar_runner")
runner.ROOT = Path(".")
runner.TRUSTED_GATE_SOURCES = {
    "regnet": "judgment-jar-gate-import.regnet-qa",
    "venice": "judgment-jar-gate-import.venice-completion",
}
runner.TRUSTED_AUTHORITY_ROUTES = {
    "regnet": "fixed-durable-source:renee-qa-receipts",
    "venice": "fixed-durable-source:adam-daemon-venice-reviews",
}
runner.TRUSTED_GATE_REVIEWERS = {"regnet": "Regnet QA", "venice": "Venice"}
runner.RunnerError = type("RunnerError", (RuntimeError,), {})
runner.validate_state = lambda state: None


def fixture_ingest_gate(_state, request):
    if not isinstance(request.get("artifact"), dict) or not isinstance(request.get("authorityReceipt"), dict):
        raise runner.RunnerError("artifact/authority pair required")
    return {"transitioned": True}


runner.ingest_gate = fixture_ingest_gate
sys.modules["judgment_jar_runner"] = runner

common = types.ModuleType("judgment_jar_common")
common.CONFIG_PATH = Path("config.json")
common.DEFAULT_CACHE = Path("cache.json")
common.read_config = lambda _path: {"fixture": True}
sys.modules["judgment_jar_common"] = common

receipts = types.ModuleType("judgment_jar_receipts")
receipts.build = lambda registry, jar, **kwargs: {
    "receiptId": "fixture-builder-random-id", "dedupFingerprint": "old",
    "jar": {"id": jar["id"], "registryDigest": registry["registryDigest"]},
    "output": {"kind": kwargs["output_kind"], "sha256": sha(kwargs["output_text"])},
    "invocation": {"source": kwargs["source"], "groupId": kwargs["group_id"]},
    "actor": kwargs["actor"], "metadata": kwargs["metadata"],
}
receipts.fingerprint = lambda receipt: sha(canonical({k: v for k, v in receipt.items() if k != "dedupFingerprint"}))
captured = []


def capture(receipt, config):
    assert config == {"fixture": True}
    captured.append(json.loads(json.dumps(receipt)))
    return {"ok": True, "receipt": receipt}


receipts.capture = capture
sys.modules["judgment_jar_receipts"] = receipts

registry_module = types.ModuleType("judgment_jar_registry")
registry = {
    "registryDigest": "registry-1",
    "jars": {"regnet": {"id": "regnet-qa"}, "venice": {"id": "venice-final"}},
}
registry_module.ensure_registry = lambda *_args, **_kwargs: (registry, {})
registry_module.resolve_jar = lambda reg, gate: reg["jars"].get(gate)
sys.modules["judgment_jar_registry"] = registry_module

import judgment_jar_gate_import as importer


state = {
    "schema": "home-center.judgment-jar-runner.v1", "state": "REGNET_PENDING",
    "candidate": "candidate", "candidateSha256": sha("candidate"),
    "contextPacket": "context", "contextPacketSha256": sha("context"),
    "createdOutput": "output", "createdOutputKind": "answer", "createdOutputSha256": sha("output"),
    "groupId": "group-1", "jarIds": ["story-jar"], "registryDigest": "registry-1",
    "nativeSources": [{"sourceSha256": sha("native")}],
}


def expect_error(call, contains):
    try:
        call()
        raise AssertionError(f"expected ImportError containing {contains!r}")
    except importer.ImportError as exc:
        assert contains in str(exc), str(exc)


with tempfile.TemporaryDirectory() as temporary:
    temp = Path(temporary)
    regnet_root = temp / "regnet" / "receipts"
    venice_root = temp / "state" / "adam-daemon"
    regnet_root.mkdir(parents=True)
    venice_root.mkdir(parents=True)
    state_path = temp / "runner-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    roots = {"regnet": regnet_root, "venice": venice_root}

    review_request = importer.review_request_for_state(state, "regnet")
    request_object = json.loads(review_request)
    assert request_object["candidate"] == "candidate"
    assert request_object["createdOutput"] == "output"
    assert request_object["contextPacket"] == "context"
    assert request_object["jarIds"] == ["story-jar"]
    payload = {
        "schema": "home-center.regnet-qa.review.v1", "reviewer": "Regnet QA",
        "provenance": "SYNTHETIC_REGNET", "created_at": "fixture",
        "claim": review_request, "capability_state": "tested", "acceptance": [],
        "evidence": [], "evidence_refs": [], "reachable_failure_paths": [], "dissent": [],
        "unresolved": [], "blockers": [], "warnings": [], "questions": [], "verdict": "PASS",
        "can_grant_final_stop": False, "next_gate": "Venice",
    }
    payload["receipt_id"] = "rqa-" + sha(canonical(payload))[:20]
    regnet_path = regnet_root / f"{payload['receipt_id']}.json"
    # tools/renee.py writes a pretty-printed JSON file, not JSONL.
    regnet_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = importer.import_gate(state_path, "regnet", regnet_path, 1, roots=roots)
    assert result["advanceAllowed"] is True and result["repairRequired"] is False
    assert result["artifact"]["verdict"] == "PASS"
    assert result["artifact"]["reviewer"] == "Regnet QA"
    assert result["artifact"]["sourceProvenance"] == "SYNTHETIC_REGNET"
    assert result["authorityReceipt"]["receiptId"] == result["requestId"]
    assert result["ingestRequest"]["artifact"] == result["artifact"]
    assert captured[-1]["metadata"]["provenance"] == "SYNTHETIC_REGNET"
    replay = importer.import_gate(state_path, "regnet", regnet_path, 1, roots=roots)
    assert replay["auditReceipt"] == result["auditReceipt"]

    outside = temp / "outside.json"
    outside.write_text(json.dumps(payload), encoding="utf-8")
    expect_error(lambda: importer.import_gate(state_path, "regnet", outside, 1, roots=roots), "outside")
    broken = dict(payload)
    broken["receipt_id"] = "rqa-00000000000000000000"
    broken_path = regnet_root / f"{broken['receipt_id']}.json"
    broken_path.write_text(json.dumps(broken), encoding="utf-8")
    expect_error(lambda: importer.import_gate(state_path, "regnet", broken_path, 1, roots=roots), "digest mismatch")

    content_blind = dict(payload)
    content_blind["claim"] = canonical(importer.binding_for_state(state, "regnet"))
    content_blind.pop("receipt_id", None)
    content_blind["receipt_id"] = "rqa-" + sha(canonical(content_blind))[:20]
    content_blind_path = regnet_root / f"{content_blind['receipt_id']}.json"
    content_blind_path.write_text(json.dumps(content_blind), encoding="utf-8")
    expect_error(
        lambda: importer.import_gate(state_path, "regnet", content_blind_path, 1, roots=roots),
        "exact full runner review request",
    )

    revise = dict(payload)
    revise["verdict"] = "REVISE_REQUIRED"
    revise["blockers"] = ["repair this slice"]
    revise.pop("receipt_id", None)
    revise["receipt_id"] = "rqa-" + sha(canonical(revise))[:20]
    revise_path = regnet_root / f"{revise['receipt_id']}.json"
    revise_path.write_text(json.dumps(revise), encoding="utf-8")
    revise_result = importer.import_gate(state_path, "regnet", revise_path, 1, roots=roots)
    assert revise_result["advanceAllowed"] is False and revise_result["repairRequired"] is True
    assert revise_result["transitionAllowed"] is False and revise_result["ingestRequest"] is None
    assert "artifact" not in revise_result and "authorityReceipt" not in revise_result
    assert revise_result["sourceResult"]["mappedResult"] == "REVISE_REQUIRED"
    assert revise_result["auditReceipt"]["outputKind"] == "review_verdict"
    assert revise_result["runnerStateAfterImport"] == "REGNET_PENDING"
    assert json.loads(state_path.read_text())["state"] == "REGNET_PENDING"
    try:
        runner.ingest_gate(state, revise_result)
        raise AssertionError("repair result unexpectedly formed an ingest transition")
    except runner.RunnerError as exc:
        assert "artifact/authority" in str(exc)

    venice_state = dict(state)
    venice_state["state"] = "VENICE_PENDING"
    state_path.write_text(json.dumps(venice_state), encoding="utf-8")
    venice_request = importer.review_request_for_state(venice_state, "venice")
    venice = {
        "schema": "adam-venice-stop-review-v1", "task": venice_request[:4000],
        "taskSha256": sha(venice_request),
        "proposal": {
            "tool": "finish",
            "judgmentJarRunner": importer.venice_proposal_binding_for_state(venice_state),
        },
        "verdict": "PASS", "directive": "STOP_ALLOWED", "stopPermissionGranted": True,
        "externalReviewGateSatisfied": True, "reviewerMode": "phone-local-fixture",
    }
    venice_path = venice_root / "venice-reviews.jsonl"
    venice_path.write_text(json.dumps({"schema": "ignored"}) + "\n" + json.dumps(venice) + "\n", encoding="utf-8")
    result = importer.import_gate(state_path, "venice", venice_path, 2, roots=roots)
    assert result["artifact"]["verdict"] == "CONTINUE"
    assert result["artifact"]["sourceReviewerMode"] == "phone-local-fixture"
    assert captured[-1]["metadata"]["directive"] == "STOP_ALLOWED"
    assert captured[-1]["metadata"]["sourceLine"] == 2
    assert captured[-1]["metadata"]["reviewerMode"] == "phone-local-fixture"

    wrong = dict(venice)
    wrong["taskSha256"] = "0" * 64
    with venice_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(wrong) + "\n")
    expect_error(lambda: importer.import_gate(state_path, "venice", venice_path, 3, roots=roots), "taskSha256")

    wrong_prefix = dict(venice)
    wrong_prefix["task"] = "hash-only"
    with venice_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(wrong_prefix) + "\n")
    expect_error(lambda: importer.import_gate(state_path, "venice", venice_path, 4, roots=roots), "defined prefix")

    unbound_proposal = dict(venice)
    unbound_proposal["proposal"] = {"tool": "finish"}
    with venice_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(unbound_proposal) + "\n")
    expect_error(lambda: importer.import_gate(state_path, "venice", venice_path, 5, roots=roots), "terminal action")

    continue_review = dict(venice)
    continue_review.update({
        "verdict": "FAIL", "directive": "CONTINUE_REQUIRED",
        "stopPermissionGranted": False, "externalReviewGateSatisfied": False,
    })
    with venice_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(continue_review) + "\n")
    continue_result = importer.import_gate(state_path, "venice", venice_path, 6, roots=roots)
    assert continue_result["advanceAllowed"] is False and continue_result["repairRequired"] is True
    assert continue_result["transitionAllowed"] is False and continue_result["ingestRequest"] is None
    assert "artifact" not in continue_result and "authorityReceipt" not in continue_result
    assert continue_result["sourceResult"]["mappedResult"] == "CONTINUE_REQUIRED"
    assert continue_result["auditReceipt"]["decisionAction"] == "CONTINUE_REQUIRED"
    assert continue_result["runnerStateAfterImport"] == "VENICE_PENDING"
    assert json.loads(state_path.read_text())["state"] == "VENICE_PENDING"
    try:
        runner.ingest_gate(venice_state, continue_result)
        raise AssertionError("repair result unexpectedly formed an ingest transition")
    except runner.RunnerError as exc:
        assert "artifact/authority" in str(exc)

    halt_review = dict(venice)
    halt_review.update({
        "verdict": "FAIL", "directive": "HALT_REQUIRED",
        "stopPermissionGranted": False, "externalReviewGateSatisfied": False,
    })
    with venice_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(halt_review) + "\n")
    halt_result = importer.import_gate(state_path, "venice", venice_path, 7, roots=roots)
    assert halt_result["advanceAllowed"] is False and halt_result["repairRequired"] is False
    assert halt_result["transitionAllowed"] is True
    assert halt_result["ingestRequest"]["artifact"]["verdict"] == "STOP"

    # Selection stops at line 2; a huge later append-only tail is not read or rejected.
    with venice_path.open("ab") as stream:
        stream.write(b"x" * (importer.MAX_SOURCE_LINE_BYTES + 1) + b"\n")
    selected_again = importer.import_gate(state_path, "venice", venice_path, 2, roots=roots)
    assert selected_again["sourceRecord"]["line"] == 2
    expect_error(
        lambda: importer.import_gate(state_path, "venice", venice_path, 8, roots=roots),
        "line exceeds",
    )

print(json.dumps({"ok": True, "schema": "judgment-jar-gate-import-fixture-test.v1"}, sort_keys=True))
