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


class _Handler(BaseHTTPRequestHandler):
    receipts: list[dict] = []
    catalogs: list[dict] = []

    def do_POST(self):  # noqa: N802
        length = int(self.headers.get("content-length") or 0)
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if self.path.endswith("/sync"):
            self.catalogs.append(payload)
        else:
            self.receipts.append(payload)
        raw = json.dumps({"ok": True, "state": "DELIVERED"}).encode("utf-8")
        self.send_response(202)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *_args):
        return


class JudgmentJarRuntimeTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        os.environ["HC_STATE_DIR"] = self.temp.name
        os.environ["HC_ATOM_URL"] = "http://127.0.0.1:1"
        sys.modules.pop("judgement_jar_runtime", None)
        self.runtime = importlib.import_module("judgement_jar_runtime")

    def tearDown(self):
        self.temp.cleanup()
        os.environ.pop("HC_STATE_DIR", None)
        os.environ.pop("HC_ATOM_URL", None)
        sys.modules.pop("judgement_jar_runtime", None)
        _Handler.receipts.clear()
        _Handler.catalogs.clear()

    def test_catalog_is_exact_active_eight(self):
        jars = self.runtime.catalog()
        self.assertEqual([item["order"] for item in jars], [0, 10, 20, 30, 40, 50, 70, 80])
        self.assertEqual(len(jars), 8)
        self.assertFalse(any("personality-gate" in item["path"] for item in jars))
        snapshot = self.runtime.catalog_snapshot(jars)
        expected = self.runtime._sha_text("\n".join(f"{item['path']}:{item['sha256']}" for item in jars))
        self.assertEqual(snapshot["catalogSha256"], expected)

    def test_usage_requires_output_kind_and_survives_daemon_outage(self):
        with self.assertRaises(ValueError):
            self.runtime.record_usage(
                "mission-boundary",
                output_kind="vibes",
                output_summary="invalid",
                source="test",
            )
        result = self.runtime.record_usage(
            "mission-boundary",
            output_kind="plan",
            output_summary="bounded plan",
            source="test.runtime",
            input_text="commission",
            output_text="plan body",
            output_refs=["receipt://plan"],
        )
        receipt = result["receipt"]
        self.assertEqual(receipt["captureState"], "CAPTURED")
        self.assertEqual(receipt["output"]["kind"], "plan")
        self.assertEqual(result["homeCenter"]["state"], "PENDING")
        self.assertTrue(Path(result["outboxPath"]).is_file())
        lines = self.runtime.RECEIPTS_PATH.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(lines), 1)

    def test_oldest_pending_delivers_before_new_receipt(self):
        first = self.runtime.record_usage(
            "mission-boundary",
            output_kind="plan",
            output_summary="first",
            source="test",
        )
        self.assertEqual(first["homeCenter"]["state"], "PENDING")
        with socketserver.TCPServer(("127.0.0.1", 0), _Handler) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            os.environ["HC_ATOM_URL"] = f"http://127.0.0.1:{server.server_address[1]}"
            second = self.runtime.record_usage(
                "local-first",
                output_kind="decision",
                output_summary="second",
                source="test",
            )
            server.shutdown()
            thread.join(timeout=2)
        self.assertEqual(second["homeCenter"]["state"], "DELIVERED")
        self.assertEqual([item["output"]["summary"] for item in _Handler.receipts], ["first", "second"])
        self.assertEqual(list(self.runtime.OUTBOX_DIR.glob("*.json")), [])

    def test_record_many_emits_one_receipt_per_jar_with_shared_group(self):
        results = self.runtime.record_many(
            ["mission-boundary", "local-first", "mission-boundary"],
            output_kind="analysis",
            output_summary="analysis",
            source="test.many",
        )
        self.assertEqual(len(results), 2)
        group_ids = {item["receipt"]["metadata"]["usageGroupId"] for item in results}
        self.assertEqual(len(group_ids), 1)
        self.assertEqual({item["receipt"]["output"]["kind"] for item in results}, {"analysis"})


if __name__ == "__main__":
    unittest.main()
