#!/usr/bin/env python3
from __future__ import annotations

import importlib
import json
import os
import socketserver
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))


class Handler(BaseHTTPRequestHandler):
    values: list[dict] = []

    def do_POST(self):  # noqa: N802
        size = int(self.headers.get("content-length") or 0)
        value = json.loads(self.rfile.read(size).decode("utf-8"))
        self.values.append(value)
        raw = json.dumps({"ok": True, "state": "DELIVERED", "receiptId": value.get("receiptId")}).encode()
        self.send_response(202)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        return


def registry_fixture() -> dict:
    local = {
        "id": "mission-boundary", "order": 0, "title": "Judgment Jar: Mission Boundary",
        "status": "active", "origin": "repository-operational-core", "sourceAuthority": "git-repository",
        "sourceCompleteness": "complete-body", "sourcePath": ".continue/rules/00-judgement-jar-mission-boundary.md",
        "sourceSha256": "1" * 64, "body": "Preserve the mission.\n", "aliases": ["mission-boundary", "judgment-jar-mission-boundary"],
    }
    cabinet = {
        "id": "vlad-the-adversary-keeps-the-edge", "order": 10000, "title": "Vlad — The Adversary Keeps the Edge",
        "status": "mature", "origin": "home-center-cabinet", "sourceAuthority": "home-center-native-registry",
        "sourceCompleteness": "cabinet-summary; native source remains controlling",
        "sourcePath": "home-center://drive/vlad-sheet", "sourceSha256": "2" * 64,
        "sourceFileId": "vlad-sheet", "sourceType": "spreadsheet", "sourceUrl": "https://docs.google.com/spreadsheets/d/vlad-sheet/edit",
        "body": "Compact law: Make it survive.\n", "aliases": ["vlad-the-adversary-keeps-the-edge", "vlad-judgment-jar"],
    }
    return {
        "schema": "home-center.judgment-jars.registry.v2", "registryDigest": "registry-digest-1",
        "sourceCommit": "commit-1", "jarCount": 2, "jars": [local, cabinet],
        "aliasIndex": {alias: local["id"] for alias in local["aliases"]} | {alias: cabinet["id"] for alias in cabinet["aliases"]},
    }


def config_fixture() -> dict:
    return {
        "schema": "home-center.judgment-jars.config.v1", "repositorySourcePattern": ".continue/rules/*judgement-jar*.md",
        "homeCenter": {},
        "receipts": {
            "schema": "home-center.judgment-jar-usage-receipt.v1",
            "outputKinds": ["context_packet", "plan", "decision", "review_verdict"],
            "atomBaseUrlEnv": "HC_ATOM_URL", "atomDefaultBaseUrl": "http://127.0.0.1:1",
            "atomReceiptPath": "/v1/atom/vlad/jars/receipts", "timeoutSeconds": 0.2,
        },
    }


class ReceiptTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.cache = Path(self.temp.name) / "judgment-jars.json"
        os.environ["HC_JUDGMENT_JAR_RECEIPT_STATE"] = str(Path(self.temp.name) / "usage")
        os.environ["HC_ATOM_URL"] = "http://127.0.0.1:1"
        sys.modules.pop("judgment_jar_receipts", None)
        self.receipts = importlib.import_module("judgment_jar_receipts")
        Handler.values.clear()

    def tearDown(self):
        self.temp.cleanup(); os.environ.pop("HC_JUDGMENT_JAR_RECEIPT_STATE", None); os.environ.pop("HC_ATOM_URL", None)
        sys.modules.pop("judgment_jar_receipts", None)

    def test_invalid_output_kind_fails_closed(self):
        with self.assertRaisesRegex(Exception, "output kind"):
            self.receipts.record_usage(registry_fixture(), config_fixture(), "mission-boundary", output_kind="vibes", output_summary="bad", source="test", cache=self.cache)

    def test_local_and_home_center_capture_preserve_authority(self):
        first = self.receipts.record_usage(registry_fixture(), config_fixture(), "mission-boundary", output_kind="plan", output_summary="bounded plan", source="test.local", cache=self.cache, input_text="commission", output_text="plan", output_refs=["receipt://plan"])
        second = self.receipts.record_usage(registry_fixture(), config_fixture(), "vlad-judgment-jar", output_kind="decision", output_summary="adversarial decision", source="test.cabinet", cache=self.cache, native_source={"state": "synced", "sourceType": "spreadsheet", "sourceFileId": "vlad-sheet", "sourceSha256": "3" * 64})
        self.assertEqual(first["receipt"]["captureState"], "CAPTURED"); self.assertEqual(first["homeCenter"]["state"], "PENDING")
        self.assertEqual(second["receipt"]["jar"]["origin"], "home-center-cabinet")
        self.assertEqual(second["receipt"]["nativeSource"]["sourceSha256"], "3" * 64)
        self.assertEqual(len(self.receipts.paths(self.cache)["history"].read_text(encoding="utf-8").splitlines()), 2)
        self.assertEqual(len(list(self.receipts.paths(self.cache)["outbox"].glob("*.json"))), 2)

    def test_oldest_pending_delivers_before_new_receipt(self):
        first = self.receipts.record_usage(registry_fixture(), config_fixture(), "mission-boundary", output_kind="plan", output_summary="first", source="test", cache=self.cache)
        self.assertEqual(first["homeCenter"]["state"], "PENDING")
        with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
            os.environ["HC_ATOM_URL"] = f"http://127.0.0.1:{server.server_address[1]}"
            second = self.receipts.record_usage(registry_fixture(), config_fixture(), "vlad-judgment-jar", output_kind="decision", output_summary="second", source="test", cache=self.cache)
            server.shutdown(); thread.join(timeout=2)
        self.assertEqual(second["homeCenter"]["state"], "DELIVERED")
        self.assertEqual([value["output"]["summary"] for value in Handler.values], ["first", "second"])
        self.assertEqual(list(self.receipts.paths(self.cache)["outbox"].glob("*.json")), [])
        self.assertEqual(len(self.receipts.paths(self.cache)["acks"].read_text(encoding="utf-8").splitlines()), 2)

    def test_record_many_one_receipt_per_jar_shared_group(self):
        values = self.receipts.record_many(registry_fixture(), config_fixture(), ["mission-boundary", "vlad-judgment-jar", "mission-boundary"], output_kind="review_verdict", output_summary="review", source="test.many", cache=self.cache)
        self.assertEqual(len(values), 2)
        self.assertEqual(len({value["receipt"]["invocation"]["groupId"] for value in values}), 1)
        self.assertEqual({value["receipt"]["output"]["kind"] for value in values}, {"review_verdict"})

    def test_changed_source_blocks_oldest_without_deleting_it(self):
        value = self.receipts.record_usage(registry_fixture(), config_fixture(), "mission-boundary", output_kind="plan", output_summary="first", source="test", cache=self.cache)
        changed = registry_fixture(); changed["jars"][0]["sourceSha256"] = "9" * 64
        result = self.receipts.sync_pending(changed, config_fixture(), self.cache)
        self.assertEqual(result["state"], "BLOCKED"); self.assertEqual(result["blocked"]["error"], "jar_source_changed_before_delivery")
        self.assertTrue(Path(value["outboxPath"]).is_file())


if __name__ == "__main__":
    unittest.main()
