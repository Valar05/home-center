#!/usr/bin/env python3
"""Deterministic structural tests for the ASCII Kinesis corpus index.

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
            "files": [
                "contact-sheet.txt",
                "manifest.json",
                "motion.json",
                "receipt.json",
            ],
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
            "motion_name": "Fixture Bind",
            "fps": 24,
            "source_role": "grapple",
            "keys": [
                {"key": "guard", "t": 0.0, "support": "left"},
                {"key": "contact", "t": 0.25, "support": "left"},
                {"key": "recover", "t": 0.5, "support": "right"},
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

        assert row["experiment_id"] == "v2-contact-001-test"
        assert row["lane"] == "contact"
        assert row["candidate_role"] == "grounded_release"
        assert row["motion_name"] == "Fixture Bind"
        assert row["key_names"] == ["guard", "contact", "recover"]
        assert row["event_names"] == ["contact"]
        assert row["support_states"] == ["left", "right"]
        assert row["duration_seconds"] == 0.5
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
        hits = corpus.search_records(loaded, "grounded release")
        assert hits and hits[0][1]["experiment_id"] == "v2-contact-001-test"
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
        assert len(records2) == 1, "malformed V2 specimen must fail closed"
        assert len(rejected2) == 1
        assert "missing motion.json" in rejected2[0]["reason"]

        wrong = root / "experiments" / "ascii-kinesis" / "v2-defense-999-wrong-id"
        wrong.mkdir(parents=True)
        write_json(
            wrong / "manifest.json",
            {
                "schema": "ascii-kinesis.swarm-manifest.v2",
                "format_version": 2,
                "experiment_id": "different-id",
                "lane": "defense",
            },
        )
        write_json(wrong / "motion.json", {"keys": []})
        records3, rejected3 = corpus.build_corpus(root)
        assert len(records3) == 1
        assert len(rejected3) == 2
        assert any("experiment_id/path mismatch" in item["reason"] for item in rejected3)

        report = corpus.render_outputs(records3, rejected3)["motion_index_report.md"]
        assert "Fail-closed V2 records" in report
        assert "contact-sheet.txt" in outputs_a["motion_source_refs.jsonl"]

    print(
        json.dumps(
            {
                "schema": "ascii-kinesis.motion-corpus-test.v1",
                "ok": True,
                "proves": [
                    "deterministic compact indexing",
                    "specimen provenance retained",
                    "raw ASCII body excluded",
                    "query surface works",
                    "malformed V2 fails closed",
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
