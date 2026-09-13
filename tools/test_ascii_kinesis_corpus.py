#!/usr/bin/env python3
"""Deterministic structural tests for ASCII Kinesis compact corpus retrieval.

These tests prove indexing/retrieval behavior only. They do not claim artistic
acceptance of any motion specimen.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import ascii_kinesis_corpus as corpus


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def fixture(root: Path, name: str = "v2-contact-001-test") -> Path:
    entry = root / "experiments" / "ascii-kinesis" / name
    entry.mkdir(parents=True, exist_ok=True)
    write_json(
        entry / "manifest.json",
        {
            "schema": "ascii-kinesis.swarm-manifest.v2",
            "format_version": 2,
            "experiment_id": name,
            "lane": "contact",
            "candidate": {"role": "grounded_release"},
            "quality_gates": {"tango": {"status": "PASS"}},
            "contract_verification": "PASS_CANDIDATE_ISOLATED_OFFICIAL_V2",
            "files": ["contact-sheet.txt", "manifest.json", "motion.json", "receipt.json"],
            "source": {
                "provider": "fixture",
                "asset_id": "TEST-1",
                "source_timing": "UNKNOWN",
                "authored_timing_provenance": "INFERRED",
            },
        },
    )
    write_json(
        entry / "motion.json",
        {
            "schema": "ascii-kinesis.motion.v2",
            "primitive": "RELATIONSHIP_FRAME_TRANSFER",
            "motion_name": "Fixture Bind",
            "compile": {"fps": 24, "duration_seconds": 0.5},
            "source_role": "grapple",
            "keys": [
                {
                    "key_id": "R00",
                    "name": "GUARD",
                    "t": 0.0,
                    "causal_role": "establish",
                    "contact_state": "OFF",
                    "contact_points": [],
                    "support_contact": "LEFT_SUPPORT",
                    "root_owner": "LEFT_GROUND_SUPPORT",
                    "root_velocity_class": "READY",
                    "actuator_state": "ON",
                    "timing_class": "FOURS",
                    "timing_provenance": "INFERRED",
                    "A": {"support": "LEFT"},
                },
                {
                    "key_id": "R01",
                    "name": "CONTACT",
                    "t": 0.25,
                    "causal_role": "transfer load",
                    "contact_state": "LOCKED",
                    "contact_points": ["A_HAND", "B_HAND"],
                    "support_contact": "DUAL_SUPPORT",
                    "root_owner": "SHARED_FRAME",
                    "root_velocity_class": "TRANSFER",
                    "actuator_state": "ON",
                    "timing_class": "TWOS",
                    "timing_provenance": "INFERRED",
                    "A": {"support": "LEFT"},
                    "B": {"support": "RIGHT"},
                },
                {
                    "key_id": "R02",
                    "name": "RECOVER",
                    "t": 0.5,
                    "causal_role": "settle",
                    "contact_state": "OFF",
                    "contact_points": [],
                    "support_contact": "RIGHT_SUPPORT",
                    "root_owner": "RIGHT_GROUND_SUPPORT",
                    "root_velocity_class": "SETTLED",
                    "actuator_state": "RESTORE",
                    "timing_class": "FOURS",
                    "timing_provenance": "INFERRED",
                    "B": {"support": "RIGHT"},
                },
            ],
            "events": [{"event": "contact", "t": 0.25}],
        },
    )
    write_json(entry / "receipt.json", {"status": "fixture"})
    (entry / "contact-sheet.txt").write_text(
        "RAW_ASCII_BODY_MUST_NOT_ENTER_COMPACT_INDEX\n", encoding="utf-8"
    )
    return entry


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture(root)
        records, rejected = corpus.build_corpus(root)
        assert not rejected, rejected
        assert len(records) == 1
        row = records[0]
        terms = row["authored_terms"]

        assert row["experiment_id"] == "v2-contact-001-test"
        assert row["lane"] == "contact"
        assert row["candidate_role"] == "grounded_release"
        assert row["motion_name"] == "Fixture Bind"
        assert row["fps"] == 24
        assert row["duration_seconds"] == 0.5
        assert terms["primitive"][0] == "RELATIONSHIP_FRAME_TRANSFER"
        assert terms["key_ids"] == ["R00", "R01", "R02"]
        assert terms["key_names"] == ["GUARD", "CONTACT", "RECOVER"]
        assert terms["contact_states"] == ["OFF", "LOCKED"]
        assert terms["contact_points"] == ["A_HAND", "B_HAND"]
        assert terms["support_contacts"] == ["LEFT_SUPPORT", "DUAL_SUPPORT", "RIGHT_SUPPORT"]
        assert terms["support_states"] == ["A:LEFT", "B:RIGHT"]
        assert terms["root_owners"] == ["LEFT_GROUND_SUPPORT", "SHARED_FRAME", "RIGHT_GROUND_SUPPORT"]
        assert terms["root_velocity_classes"] == ["READY", "TRANSFER", "SETTLED"]
        assert terms["actuator_states"] == ["ON", "RESTORE"]
        assert terms["causal_roles"] == ["establish", "transfer load", "settle"]
        assert row["authority"]["specimen_is_authoritative"] is True
        assert row["authority"]["generated_inference_allowed"] is False

        outputs_a = corpus.render_outputs(records, rejected)
        outputs_b = corpus.render_outputs(*corpus.build_corpus(root))
        assert outputs_a == outputs_b, "deterministic regeneration changed"
        assert "RAW_ASCII_BODY_MUST_NOT_ENTER_COMPACT_INDEX" not in outputs_a[
            "motion_source_refs.jsonl"
        ]

        out = root / "generated" / "ascii-kinesis-corpus"
        corpus.write_outputs(out, outputs_a)
        loaded = corpus.load_index(out / "motion_source_refs.jsonl")
        hits = corpus.search_records(loaded, "transfer load")
        assert hits and hits[0][1]["experiment_id"] == "v2-contact-001-test"
        assert corpus.search_records(loaded, "right ground support")
        assert corpus.search_records(loaded, "missing phrase") == []

        broken = root / "experiments" / "ascii-kinesis" / "v2-airborne-999-broken"
        broken.mkdir(parents=True)
        write_json(
            broken / "manifest.json",
            {
                "schema": "ascii-kinesis.swarm-manifest.v2",
                "format_version": 2,
                "experiment_id": broken.name,
                "lane": "airborne",
            },
        )
        records2, rejected2 = corpus.build_corpus(root)
        assert len(records2) == 1, "missing motion must fail closed"
        assert len(rejected2) == 1
        assert "missing file" in rejected2[0]["reason"]

        empty = root / "experiments" / "ascii-kinesis" / "v2-defense-999-empty"
        empty.mkdir(parents=True)
        write_json(
            empty / "manifest.json",
            {
                "schema": "ascii-kinesis.swarm-manifest.v2",
                "format_version": 2,
                "experiment_id": empty.name,
                "lane": "defense",
            },
        )
        write_json(empty / "motion.json", {"keys": []})
        records3, rejected3 = corpus.build_corpus(root)
        assert len(records3) == 1, "empty semantic motion must fail closed"
        assert len(rejected3) == 2
        assert any("no keys/poses" in item["reason"] for item in rejected3)

        report = corpus.render_outputs(records3, rejected3)["motion_index_report.md"]
        assert "Fail-closed V2 specimens" in report
        assert "contact-sheet.txt" in outputs_a["motion_source_refs.jsonl"]

    # A persisted report is a snapshot, never a hidden global latest pointer.
    # Default queries must see newly committed specimens immediately instead of
    # silently preferring a stale generated index.
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture(root, "v2-contact-001-old")
        records, rejected = corpus.build_corpus(root)
        out = root / "generated" / "ascii-kinesis-corpus"
        corpus.write_outputs(out, corpus.render_outputs(records, rejected))
        snapshot = out / "motion_source_refs.jsonl"
        assert len(corpus.query_records(root, str(snapshot))) == 1

        fixture(root, "v2-contact-002-new")
        assert len(corpus.query_records(root, None)) == 2
        assert len(corpus.query_records(root, str(snapshot))) == 1

    print(
        json.dumps(
            {
                "schema": "ascii-kinesis.motion-corpus-test.v1",
                "ok": True,
                "proves": [
                    "deterministic compact indexing",
                    "exact authored semantic terms retained",
                    "contact/support/root/actuator states retained",
                    "nested support state retained",
                    "specimen provenance retained",
                    "raw ASCII body excluded",
                    "default queries read current specimens, not stale snapshots",
                    "explicit snapshot queries remain reproducible",
                    "malformed or empty V2 fails closed",
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
