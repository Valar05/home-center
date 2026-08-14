#!/usr/bin/env python3
"""Exercise real receipt build/fingerprint/capture/import when installed.

Scratch intentionally does not vendor production modules.  A skipped result is
therefore explicit and can never be confused with a production pass.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import os
import tempfile
from pathlib import Path

try:
    import judgment_jar_gate_import as importer
    import judgment_jar_runner as runner
    from judgment_jar_common import CONFIG_PATH, read_config
    from judgment_jar_receipts import build, capture, fingerprint, paths, validate
except (ImportError, ModuleNotFoundError) as exc:
    # This scratch handoff intentionally does not vendor production modules.
    print(json.dumps({
        "ok": True, "skipped": True,
        "schema": "judgment-jar-gate-import-production-contract.v1",
        "reason": f"production module not present in scratch: {exc}",
    }, sort_keys=True))
else:
    assert callable(build) and callable(capture) and callable(fingerprint)
    dummy_receipt, dummy_config = {}, {}
    try:
        inspect.signature(capture).bind(dummy_receipt, dummy_config)
    except (TypeError, ValueError) as exc:
        raise AssertionError("capture must support capture(receipt, config)") from exc
    config = read_config(CONFIG_PATH)
    registry = {
        "schema": "home-center.judgment-jars.registry.v2",
        "registryDigest": "gate-import-production-fixture",
        "sourceCommit": "fixture",
        "jars": [{
            "id": "regnet-qa", "origin": "home-center-cabinet", "title": "Regnet QA",
            "sourceFileId": "fixture-regnet-file", "status": "mature",
        }, {
            "id": "venice-final", "origin": "home-center-cabinet", "title": "Venice",
            "sourceFileId": "fixture-venice-file", "status": "mature",
        }],
        "aliasIndex": {
            "regnet": "regnet-qa", "regnet-qa": "regnet-qa",
            "venice": "venice-final", "venice-final": "venice-final",
        },
    }
    jar = registry["jars"][0]
    probe = build(
        registry, jar, output_kind="review_verdict", output_text="production probe",
        summary="Gate importer production API probe", actor="Regnet QA",
        intent="exercise production receipt build/fingerprint/capture", surface="vlad",
        decision_action="PASS", input_text="fixture", request_id="fixture-probe",
        group_id="fixture-group", references=[],
        source=runner.TRUSTED_GATE_SOURCES["regnet"],
        metadata={"authorityRoute": runner.TRUSTED_AUTHORITY_ROUTES["regnet"]},
    )
    assert fingerprint(probe)

    # Full import exercise uses the real APIs and isolated config/spools.  If
    # this production version cannot support isolated capture, that is a hard
    # contract failure rather than a misleading skipped:false result.
    with tempfile.TemporaryDirectory() as temporary:
        temp = Path(temporary)
        config_copy = json.loads(json.dumps(config))
        receipt_config = config_copy.setdefault("receipts", {})
        receipt_root = temp / "receipt-state"
        receipt_root.mkdir()
        state_dir_env = "HC_JAR_GATE_IMPORT_PRODUCTION_CONTRACT_STATE_DIR"
        os.environ[state_dir_env] = str(receipt_root)
        receipt_config["stateDirEnv"] = state_dir_env
        receipt_config["stateDir"] = str(receipt_root)
        config_path = temp / "config.json"
        config_path.write_text(json.dumps(config_copy), encoding="utf-8")
        isolated_paths = paths(config_copy)
        resolved_receipt_root = Path(isolated_paths["root"]).resolve()
        assert resolved_receipt_root == receipt_root.resolve()
        assert resolved_receipt_root.is_relative_to(temp.resolve())
        candidate, context, output = "candidate", "context", "output"
        sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
        prepare_request = {
            "requestId": "fixture-prepare", "groupId": "fixture-group",
            "jarRefs": ["fixture-jar"], "candidate": candidate, "actor": "Adam",
            "offline": True, "allowStaleNative": False,
        }
        canonical = lambda value: json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        state = {
            "schema": runner.SCHEMA, "state": "REGNET_PENDING", "releaseAllowed": False,
            "requestId": "fixture-prepare",
            "prepareRequest": prepare_request, "prepareRequestSha256": sha(canonical(prepare_request)),
            "candidate": candidate, "candidateSha256": sha(candidate),
            "contextPacket": context, "contextPacketSha256": sha(context),
            "createdOutput": output, "createdOutputKind": "answer", "createdOutputSha256": sha(output),
            "groupId": "fixture-group", "jarIds": ["fixture-jar"],
            "registryDigest": registry["registryDigest"],
            "nativeSources": [{"jarId": "fixture-jar", "sourceSha256": sha("native")}],
            "contextReceipts": [{"receiptId": "context", "dedupFingerprint": "context-fp",
                                 "jarId": "fixture-jar", "outputKind": "context_packet", "state": "DELIVERED"}],
            "outputReceipts": [{"receiptId": "output", "dedupFingerprint": "output-fp",
                                "jarId": "fixture-jar", "outputKind": "answer", "state": "DELIVERED"}],
            "gates": {},
        }
        state_path = temp / "state.json"
        state_path.write_text(json.dumps(state), encoding="utf-8")
        runner.validate_state(state)
        review_request = importer.review_request_for_state(state, "regnet")
        source_payload = {
            "schema": "home-center.regnet-qa.review.v1", "reviewer": "Regnet QA",
            "provenance": "SYNTHETIC_REGNET", "created_at": "fixture", "claim": review_request,
            "capability_state": "tested", "acceptance": [], "evidence": [], "evidence_refs": [],
            "reachable_failure_paths": [], "dissent": [], "unresolved": [], "blockers": [],
            "warnings": [], "questions": [], "verdict": "PASS", "can_grant_final_stop": False,
            "next_gate": "Venice",
        }
        source_payload["receipt_id"] = "rqa-" + sha(json.dumps(
            source_payload, sort_keys=True, separators=(",", ":")
        ))[:20]
        source_root = temp / "renee" / "receipts"
        source_root.mkdir(parents=True)
        source_path = source_root / f"{source_payload['receipt_id']}.json"
        source_path.write_text(json.dumps(source_payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        imported = importer.import_gate(
            state_path, "regnet", source_path, 1, roots={"regnet": source_root},
            config_path=config_path,
            ensure=lambda *_args, **_kwargs: (registry, {}),
            resolver=lambda _registry, _gate: jar,
        )
        assert imported["ingestRequest"]["artifact"]["verdict"] == "PASS"
        assert imported["auditReceipt"]["dedupFingerprint"]

        # Retry the exact native record through the real builder/capture path.
        # The deterministic authority identity must deduplicate rather than
        # minting a second receipt after a caller or process retry.
        receipt_paths = isolated_paths
        pending_root = Path(receipt_paths["pending"])
        before_replay = sorted(path.relative_to(pending_root) for path in pending_root.rglob("*.json"))
        replay = importer.import_gate(
            state_path, "regnet", source_path, 1, roots={"regnet": source_root},
            config_path=config_path,
            ensure=lambda *_args, **_kwargs: (registry, {}),
            resolver=lambda _registry, _gate: jar,
        )
        after_replay = sorted(path.relative_to(pending_root) for path in pending_root.rglob("*.json"))
        assert replay["auditReceipt"] == imported["auditReceipt"]
        assert after_replay == before_replay

        # Promote the exact importer-produced authority receipt into an
        # isolated delivered/readback shard.  Validate that production receipt
        # before asking the real Runner to accept the ingest envelope.
        matching = []
        for pending_path in pending_root.rglob("*.json"):
            document = json.loads(pending_path.read_text(encoding="utf-8"))
            receipt_document = runner._receipt_document(document)
            if receipt_document and receipt_document.get("receiptId") == imported["authorityReceipt"]["receiptId"]:
                matching.append(receipt_document)
        assert len(matching) == 1
        delivered_receipt = {
            **matching[0],
            "receiptDeliveryState": "DELIVERED",
            "homeCenterDeliveryState": "DELIVERED",
            "homeCenter": {"readbackVerified": True},
        }
        validate(delivered_receipt, config_copy)
        delivered_root = Path(receipt_paths["delivered"])
        delivered_root.mkdir(parents=True, exist_ok=True)
        (delivered_root / "imported-regnet-authority.json").write_text(
            json.dumps(delivered_receipt, sort_keys=True), encoding="utf-8"
        )
        advanced = runner.ingest_gate(
            state, imported["ingestRequest"], config_path=config_path,
            ensure=lambda *_args, **_kwargs: (registry, {}),
            path_resolver=lambda _config: {"delivered": delivered_root},
        )
        assert advanced["state"] == "VENICE_PENDING"
        assert advanced["gates"]["regnet"]["verdict"] == "PASS"

        # Continue the same real transaction through the mandatory Venice
        # completion authority, proving STOP_ALLOWED maps only to the Runner's
        # receipt-pending CONTINUE transition—not directly to release.
        state_path.write_text(json.dumps(advanced), encoding="utf-8")
        venice_request = importer.review_request_for_state(advanced, "venice")
        venice_payload = {
            "schema": "adam-venice-stop-review-v1",
            "task": venice_request[:4000],
            "taskSha256": sha(venice_request),
            "proposal": {
                "tool": "finish",
                "judgmentJarRunner": importer.venice_proposal_binding_for_state(advanced),
            },
            "verdict": "PASS", "directive": "STOP_ALLOWED",
            "stopPermissionGranted": True, "externalReviewGateSatisfied": True,
            "reviewerMode": "production-contract-fixture",
        }
        venice_root = temp / "adam-daemon"
        venice_root.mkdir()
        venice_path = venice_root / "venice-reviews.jsonl"
        venice_path.write_text(json.dumps(venice_payload, sort_keys=True) + "\n", encoding="utf-8")
        venice_jar = registry["jars"][1]
        venice_imported = importer.import_gate(
            state_path, "venice", venice_path, 1, roots={"venice": venice_root},
            config_path=config_path,
            ensure=lambda *_args, **_kwargs: (registry, {}),
            resolver=lambda _registry, _gate: venice_jar,
        )
        assert venice_imported["ingestRequest"]["artifact"]["verdict"] == "CONTINUE"
        venice_replay = importer.import_gate(
            state_path, "venice", venice_path, 1, roots={"venice": venice_root},
            config_path=config_path,
            ensure=lambda *_args, **_kwargs: (registry, {}),
            resolver=lambda _registry, _gate: venice_jar,
        )
        assert venice_replay["auditReceipt"] == venice_imported["auditReceipt"]
        venice_matching = []
        for pending_path in pending_root.rglob("*.json"):
            document = json.loads(pending_path.read_text(encoding="utf-8"))
            receipt_document = runner._receipt_document(document)
            if receipt_document and receipt_document.get("receiptId") == venice_imported["authorityReceipt"]["receiptId"]:
                venice_matching.append(receipt_document)
        assert len(venice_matching) == 1
        delivered_venice = {
            **venice_matching[0],
            "receiptDeliveryState": "DELIVERED",
            "homeCenterDeliveryState": "DELIVERED",
            "homeCenter": {"readbackVerified": True},
        }
        validate(delivered_venice, config_copy)
        (delivered_root / "imported-venice-authority.json").write_text(
            json.dumps(delivered_venice, sort_keys=True), encoding="utf-8"
        )
        venice_advanced = runner.ingest_gate(
            advanced, venice_imported["ingestRequest"], config_path=config_path,
            ensure=lambda *_args, **_kwargs: (registry, {}),
            path_resolver=lambda _config: {"delivered": delivered_root},
        )
        assert venice_advanced["state"] == "VENICE_CONTINUE_PENDING_RECEIPTS"
        assert venice_advanced["releaseAllowed"] is False
        assert venice_advanced["gates"]["venice"]["verdict"] == "CONTINUE"
    print(json.dumps({
        "ok": True, "skipped": False,
        "schema": "judgment-jar-gate-import-production-contract.v1",
    }, sort_keys=True))
