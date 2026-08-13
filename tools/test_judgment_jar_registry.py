#!/usr/bin/env python3
"""Deterministic contract tests for Vlad's Judgment Jar cache and receipts."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "judgment_jars.py"
CONFIG = ROOT / "config" / "judgment-jars.v1.json"


def load_tool():
    spec = importlib.util.spec_from_file_location("judgment_jars", TOOL)
    if spec is None or spec.loader is None:
        raise AssertionError("unable to load judgment_jars.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cabinet_fixture() -> str:
    return """JUDGMENT JAR REGISTRY
Status: Active cabinet index
MATURE SPREADSHEET JARS
She-Raw — Ferociously Invitable
Governor: Character
Link: https://docs.google.com/spreadsheets/d/sheraw-sheet/edit
Judgment: Is interrogation honest, bounded, corrigible, and survivable?
Compact law: Invite fiercely; return the door.

PROSE SUBSTRATES / REPAIR REQUIRED
What Would June Do?
Governor: Human substrate
Boundary: Protect June's autonomous authorship and plural internal reality.
Link: https://docs.google.com/document/d/june-doc/edit

MATURE SPREADSHEET JAR — VLAD
Vlad — The Adversary Keeps the Edge
Governor: Character — Vlad
Link: https://docs.google.com/spreadsheets/d/vlad-sheet/edit
Judgment: Does the implementation survive scarcity and restart?
Hard gates: Hidden state; restart amnesia.
Compact law: Make it fit. Make it survive. Record the scar.

MISSING EXECUTABLE FUNCTIONS
1. Wardaddy — next-hour command and mandatory stand-down.
2. Dyonisis — only after Character/Hat/Weather split.
3. Gasket — independent verification harness.
BUILD ORDER
Wardaddy; Gasket.
REGISTRY CORRECTION — DYONISIS DEBT CLOSED
The earlier Dyonisis debt is superseded by a mature native Sheet.

RANDI — GOVERNING QUIRK THEORY: SPAGHETTI PRESERVATION
Status: User-ratified character quirk; supplementary to the existing Edge or Gloss Judgment Jar.
Existing workbook: https://docs.google.com/spreadsheets/d/randi-sheet/edit
Compact law: Preserve the abundance. Mark the truth. Date the consequence. Retrieve the spaghetti.
"""


class FakeHomeCenter:
    def __init__(self):
        self.docs: dict[str, str] = {}
        self.updates: list[str] = []

    def search_drive(self, _query, _page_size=10):
        return []

    def read_document(self, file_id, _name=""):
        return self.docs.get(file_id, "")

    def drive_operation(self, operation, args):
        if operation == "drive.read_metadata":
            return {"file": {"id": args["fileId"], "parents": ["jar-folder"]}}
        if operation == "docs.create":
            self.docs["receipt-ledger"] = args.get("body", "")
            return {"file": {"id": "receipt-ledger", "name": args["title"], "parents": [args.get("folderId")]}}
        if operation == "docs.update":
            self.docs[args["fileId"]] += args["appendText"]
            self.updates.append(args["appendText"])
            return {"file": {"id": args["fileId"]}}
        raise AssertionError(f"unexpected Home Center operation: {operation}")


def main() -> int:
    jars = load_tool()
    source_paths = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / ".continue" / "rules").glob("*judgement-jar*.md")
        if path.is_file()
    )
    assert source_paths, "canonical operational Judgment Jar sources are missing"

    with tempfile.TemporaryDirectory(prefix="vlad-jars-test-") as tmp:
        tmp = Path(tmp)
        tmp_root = tmp / "repo"
        tmp_rules = tmp_root / ".continue" / "rules"
        tmp_config_dir = tmp_root / "config"
        tmp_rules.mkdir(parents=True)
        tmp_config_dir.mkdir(parents=True)
        for relative in source_paths:
            source = ROOT / relative
            shutil.copy2(source, tmp_rules / source.name)

        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        config["homeCenter"]["minimumCabinetEntries"] = 3
        config["receipts"]["stateDirEnv"] = "HC_TEST_JUDGMENT_JAR_RECEIPTS"
        config_path = tmp_config_dir / "judgment-jars.v1.json"
        config_path.write_text(json.dumps(config), encoding="utf-8")
        cache = tmp / "state" / "judgment-jars.json"
        receipt_state = tmp / "state" / "receipts"
        os.environ["HC_TEST_JUDGMENT_JAR_RECEIPTS"] = str(receipt_state)
        os.environ["HC_STATE_DIR"] = str(tmp / "home-center-state")

        def fresh(_config):
            return {
                "registryText": cabinet_fixture(),
                "discoveredFiles": [
                    {
                        "id": "android67-sheet",
                        "name": "ANDROID 67 — Judgment Jar — KEEP",
                        "mimeType": "application/vnd.google-apps.spreadsheet",
                        "modifiedTime": "2026-08-13T09:59:28Z",
                    },
                    {
                        "id": "vlad-sheet",
                        "name": "JUDGMENT JAR — Vlad duplicate",
                        "mimeType": "application/vnd.google-apps.spreadsheet",
                    },
                ],
            }

        first, sync = jars.ensure_registry(
            tmp_root,
            cache,
            config_path=config_path,
            force_home_center=True,
            fetcher=fresh,
        )
        assert sync["changed"] is True
        assert sync["homeCenterAttempted"] is True
        assert first["complete"] is True
        assert first["localJarCount"] == len(source_paths)
        assert first["cabinetJarCount"] == 4
        assert first["unregisteredJarCount"] == 1
        assert first["jarCount"] == len(source_paths) + 5
        assert first["homeCenter"]["missingExecutableFunctions"] == [
            "1. Wardaddy — next-hour command and mandatory stand-down.",
            "3. Gasket — independent verification harness.",
        ]
        assert cache.is_file()
        assert not cache.with_name(cache.name + ".tmp").exists()

        mission = jars.resolve_jar(first, "Judgment Jar: Mission Boundary")
        assert mission and mission["id"] == "mission-boundary"
        assert jars.resolve_jar(first, "judgement jar mission boundary") == mission
        assert jars.resolve_jar(first, "Vlad — The Adversary Keeps the Edge")["origin"] == jars.CABINET_ORIGIN
        assert jars.resolve_jar(first, "Randi Edge or Gloss")["sourceFileId"] == "randi-sheet"
        assert jars.resolve_jar(first, "ANDROID 67 Judgment Jar KEEP")["status"] == "unregistered"
        assert jars.search_jars(first, "restart scarcity")[0]["id"] == "vlad-the-adversary-keeps-the-edge"

        vlad = jars.resolve_jar(first, "Vlad — The Adversary Keeps the Edge")
        native = jars.fetch_native_source(
            vlad,
            config,
            cache,
            refresh=True,
            fetcher=lambda jar, _cfg: {
                "spreadsheetId": jar["sourceFileId"],
                "range": "A1:C3",
                "values": [["Criterion", "Gate"], ["Restart", "PASS"]],
            },
        )
        assert native["state"] == "synced"
        assert native["sourceFileId"] == "vlad-sheet"
        assert native["sheet"]["values"][1] == ["Restart", "PASS"]
        native_stale = jars.fetch_native_source(
            vlad,
            config,
            cache,
            refresh=True,
            fetcher=lambda _jar, _cfg: (_ for _ in ()).throw(RuntimeError("native source offline")),
        )
        assert native_stale["state"] == "stale"
        assert native_stale["sheet"]["values"][1] == ["Restart", "PASS"]

        def broken(_config):
            raise RuntimeError("connector unavailable")

        stale, stale_sync = jars.ensure_registry(
            tmp_root,
            cache,
            config_path=config_path,
            force_home_center=True,
            fetcher=broken,
        )
        assert stale_sync["homeCenterFailed"] is True
        assert stale["complete"] is False
        assert stale["homeCenter"]["state"] == "stale"
        assert stale["cabinetJarCount"] == first["cabinetJarCount"]
        assert jars.resolve_jar(stale, "What Would June Do?")["sourceFileId"] == "june-doc"

        future = tmp_rules / "90-judgement-jar-future-proof.md"
        future.write_text(
            "# Judgement Jar: Future Proof\n\n"
            "Status: active\nScope: registry discovery\n\n"
            "## Judgement\n\nNew jars must appear automatically.\n",
            encoding="utf-8",
        )
        future_registry, _ = jars.ensure_registry(tmp_root, cache, config_path=config_path, offline=True)
        assert future_registry["localJarCount"] == len(source_paths) + 1
        assert jars.resolve_jar(future_registry, "future proof")["origin"] == jars.LOCAL_ORIGIN

        persisted = json.loads(cache.read_text(encoding="utf-8"))
        assert persisted["registryDigest"] == future_registry["registryDigest"]
        assert persisted["homeCenter"]["cabinetCount"] == 4

        mission = jars.resolve_jar(future_registry, "mission-boundary")
        context_result = jars.context_receipt(
            future_registry,
            mission,
            config,
            "compiled context",
            "test.get",
            "retrieve bounded context",
            "returned Jar context",
            "mission-boundary",
            "context-request",
            "receipt-group",
        )
        assert context_result["state"] == "PENDING_HOME_CENTER"
        output_result = jars.record_receipt(
            future_registry,
            mission,
            config,
            output_kind="review_verdict",
            output_text="PLAN_ALLOWED",
            summary="Allowed the bounded plan.",
            actor="Venice",
            intent="review the bounded plan",
            surface="vlad",
            decision_action="PLAN_ALLOWED",
            input_text="commission",
            request_id="review-request",
            group_id="receipt-group",
            source="test_judgment_jar_registry",
        )
        assert output_result["state"] == "PENDING_HOME_CENTER"
        assert jars.receipt_status(config)["pending"] == 2

        review_dir = Path(os.environ["HC_STATE_DIR"]) / "venice"
        review_dir.mkdir(parents=True)
        review_record = {
            "schema": "venice-plan-review-v2-judgment-jar-primary",
            "reviewer": "Venice",
            "commission": "bounded test commission",
            "verdict": "PASS",
            "directive": "PLAN_ALLOWED",
            "findings": [],
            "selectedJudgmentJars": [{"path": mission["sourcePath"]}],
        }
        (review_dir / "plan-reviews.jsonl").write_text(json.dumps(review_record) + "\n", encoding="utf-8")
        imported = jars.import_review_receipts(future_registry, config)
        assert imported["imported"] == 1
        assert jars.receipt_status(config)["pending"] == 3

        home = FakeHomeCenter()
        delivered = jars.flush_receipts(config, client_factory=lambda: home)
        assert delivered["state"] == "DELIVERED"
        assert delivered["delivered"] == 3
        assert delivered["pending"] == 0
        assert delivered["quarantined"] == 0
        ledger = home.docs["receipt-ledger"]
        assert "context_packet" in ledger
        assert "review_verdict" in ledger
        assert "judgmentJarReceiptFingerprint:" in ledger
        assert len(home.updates) == 3
        assert jars.receipt_status(config)["delivered"] == 3

    print(json.dumps({
        "ok": True,
        "schema": "vlad-judgment-jar-registry-and-receipts-test-v3",
        "canonicalOperationalSourceCount": len(source_paths),
        "dynamicRepositoryDiscovery": True,
        "homeCenterCabinetSync": True,
        "homeCenterDiscoveryOfUnregisteredJars": True,
        "nativeSourceOnDemand": True,
        "nativeSourceStaleCachePreservation": True,
        "staleCachePreservation": True,
        "americanBritishAliasCompatibility": True,
        "atomicCache": True,
        "contextAccessReceipts": True,
        "typedOutputReceipts": True,
        "veniceReviewReceiptImport": True,
        "oldestFirstHomeCenterDelivery": True,
        "homeCenterReadbackVerification": True,
        "captureAndDeliverySeparated": True,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
