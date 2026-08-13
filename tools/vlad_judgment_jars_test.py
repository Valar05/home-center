#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from vlad_judgment_jars import Registry


class VladJudgmentJarsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.db = Path(self.tempdir.name) / "jars.sqlite3"
        self.registry = Registry(self.db)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def snapshot(self, complete: bool = True) -> dict:
        return {
            "schema_version": 1,
            "source": "home-center-test",
            "complete": complete,
            "observed_at": "2026-08-13T10:00:00Z",
            "jars": [
                {
                    "jar_id": "venice",
                    "title": "Venice",
                    "aliases": ["Ven", "Portcullis"],
                    "jurisdiction": "taste, autonomy, and humane friction",
                    "body": "Review independently and return a verdict.",
                    "source_ref": "drive:venice",
                    "source_revision": "rev-7",
                    "updated_at": "2026-08-13T09:00:00Z",
                    "status": "active",
                },
                {
                    "jar_id": "saint-andrew",
                    "title": "Saint Andrew",
                    "aliases": ["St Andrew", "Andrew"],
                    "jurisdiction": "unconstrained invention and consequences",
                    "body": "Ask what the work becomes when allowed to continue.",
                    "source_ref": "drive:andrew",
                    "source_revision": "rev-2",
                    "status": "active",
                },
            ],
        }

    def test_complete_snapshot_builds_alias_lookup(self) -> None:
        result = self.registry.import_snapshot(self.snapshot())
        self.assertEqual(2, result["inserted"])
        self.assertEqual("venice", self.registry.resolve("VEN")["jar_id"])
        self.assertEqual("saint-andrew", self.registry.resolve("St. Andrew")["jar_id"])
        self.assertEqual(2, len(self.registry.list_jars()))

    def test_snapshot_is_idempotent(self) -> None:
        first = self.registry.import_snapshot(self.snapshot())
        second = self.registry.import_snapshot(self.snapshot())
        self.assertEqual(2, first["inserted"])
        self.assertEqual(0, second["inserted"])
        self.assertEqual(2, second["unchanged"])
        self.assertEqual(first["snapshot_sha256"], second["snapshot_sha256"])

    def test_complete_snapshot_tombstones_missing_jar(self) -> None:
        self.registry.import_snapshot(self.snapshot())
        smaller = self.snapshot()
        smaller["observed_at"] = "2026-08-13T11:00:00Z"
        smaller["jars"] = smaller["jars"][:1]
        result = self.registry.import_snapshot(smaller)
        self.assertEqual(1, result["tombstoned"])
        self.assertIsNone(self.registry.resolve("saint-andrew"))
        self.assertEqual(
            "tombstoned",
            self.registry.resolve("saint-andrew", include_tombstoned=True)["status"],
        )

    def test_partial_snapshot_does_not_tombstone(self) -> None:
        self.registry.import_snapshot(self.snapshot())
        partial = self.snapshot(complete=False)
        partial["jars"] = partial["jars"][:1]
        result = self.registry.import_snapshot(partial)
        self.assertEqual(0, result["tombstoned"])
        self.assertIsNotNone(self.registry.resolve("saint-andrew"))

    def test_actual_use_requires_and_opens_receipt(self) -> None:
        self.registry.import_snapshot(self.snapshot())
        result = self.registry.open_use(
            "Portcullis",
            request_id="req-123",
            worker="vlad",
            campaign="fortress",
            input_text="Review this plan",
        )
        self.assertEqual("venice", result["jar"]["jar_id"])
        receipt = result["receipt"]
        self.assertEqual("open", receipt["status"])
        self.assertEqual("rev-7", receipt["jar_revision"])
        self.assertEqual(64, len(receipt["input_sha256"]))
        self.assertEqual(0, len(self.registry.pending_receipts()))

    def test_complete_receipt_records_output_kind_and_queues_delivery(self) -> None:
        self.registry.import_snapshot(self.snapshot())
        opened = self.registry.open_use(
            "venice", "req-456", "vlad", "fortress", "Plan"
        )["receipt"]
        closed = self.registry.complete_use(
            opened["receipt_id"],
            output_kind="plan_review",
            output_ref="drive:review-1",
            output_text="VERDICT: PASS",
        )
        self.assertEqual("plan_review", closed["output_kind"])
        self.assertEqual("pending", closed["delivery_state"])
        pending = self.registry.pending_receipts()
        self.assertEqual([opened["receipt_id"]], [item["receipt_id"] for item in pending])
        self.assertEqual(1, self.registry.mark_receipts_delivered([opened["receipt_id"]]))
        self.assertEqual([], self.registry.pending_receipts())

    def test_same_jar_cannot_open_twice_for_same_request(self) -> None:
        self.registry.import_snapshot(self.snapshot())
        self.registry.open_use("venice", "req-dupe", "vlad", "", "one")
        with self.assertRaisesRegex(ValueError, "already used"):
            self.registry.open_use("Ven", "req-dupe", "vlad", "", "two")

    def test_search_finds_jurisdiction_and_body(self) -> None:
        self.registry.import_snapshot(self.snapshot())
        self.assertEqual("venice", self.registry.search("humane friction")[0]["jar_id"])
        self.assertEqual(
            "saint-andrew", self.registry.search("continue consequences")[0]["jar_id"]
        )

    def test_status_separates_cache_and_receipt_states(self) -> None:
        self.registry.import_snapshot(self.snapshot())
        opened = self.registry.open_use("venice", "req-status", "vlad", "", "x")
        status = self.registry.status()
        self.assertEqual(2, status["jars"]["active"])
        self.assertEqual(1, status["receipts"]["open"])
        self.registry.complete_use(
            opened["receipt"]["receipt_id"], "verdict", "", "PASS"
        )
        status = self.registry.status()
        self.assertEqual(1, status["receipts"]["pending"])


if __name__ == "__main__":
    unittest.main()
