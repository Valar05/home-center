#!/usr/bin/env python3
"""Deterministic provenance/closure gate for Ritsu episodic retrieval.

This module does not retrieve or infer episode meaning. It answers the smaller,
more dangerous question: is there enough *primary* evidence to stop saying
CONTINUITY_GAP?

A primary source counts only when it has readable transcript ``text`` and a
stable ``source_id``. Accepted summaries, adjacent evidence, screenshots of a
failure, and anonymous text never close the gate. CORRECTED_BY evidence is
independently gated so the original scene cannot silently stand in for a later
correction that changed its meaning.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

PRIMARY = "primary_transcript"
SUMMARY = "accepted_summary"
UNKNOWN = "unknown"
GAP = "CONTINUITY_GAP"
COMPLETE = "PRIMARY_COMPLETE"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            row = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: malformed JSONL: {exc}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"{path}:{line_no}: JSONL record must be an object")
        rows.append(row)
    return rows


def stable_primary_sources(record: Mapping[str, Any]) -> list[dict[str, str]]:
    """Return only transcript sources with a stable durable binding."""
    valid: list[dict[str, str]] = []
    sources = record.get("primary_sources") or []
    if not isinstance(sources, list):
        return valid
    for source in sources:
        if not isinstance(source, Mapping):
            continue
        source_id = source.get("source_id")
        text = source.get("text")
        if not isinstance(source_id, str) or not source_id.strip():
            continue
        if not isinstance(text, str) or not text.strip():
            continue
        valid.append({"source_id": source_id.strip(), "text": text.strip()})
    return valid


def _targets_episode(record: Mapping[str, Any], episode_id: str) -> bool:
    # ``episode_id`` is the current ledger spelling. ``target_episode`` is accepted
    # for synthetic/older fixtures so the gate can detect migration regressions.
    return record.get("episode_id") == episode_id or record.get("target_episode") == episode_id


def _latest_open_retrieval(
    active_rows: Iterable[dict[str, Any]], episode_id: str
) -> dict[str, Any] | None:
    for row in reversed(list(active_rows)):
        if not _targets_episode(row, episode_id):
            continue
        if row.get("status") == "open":
            return row
        if row.get("status") in {"closed", "cancelled", "canceled"}:
            return None
    return None


def audit_episode(
    ledger_rows: list[dict[str, Any]],
    active_rows: list[dict[str, Any]],
    episode_id: str,
) -> dict[str, Any]:
    episode = next(
        (
            row
            for row in ledger_rows
            if row.get("record_type") == "episode" and row.get("id") == episode_id
        ),
        None,
    )
    if episode is None:
        return {
            "episode_id": episode_id,
            "status": GAP,
            "provenance": UNKNOWN,
            "missing": ["episode_record"],
            "can_close_active_retrieval": False,
        }

    episode_sources = stable_primary_sources(episode)
    all_corrections = [
        row
        for row in ledger_rows
        if row.get("record_type") == "correction" and _targets_episode(row, episode_id)
    ]
    linked_corrections = [row for row in all_corrections if row.get("edge") == "CORRECTED_BY"]
    orphan_corrections = [row for row in all_corrections if row.get("edge") != "CORRECTED_BY"]

    missing: list[str] = []
    if not episode_sources:
        missing.append("episode_primary_transcript")

    correction_source_ids: dict[str, list[str]] = {}
    for correction in linked_corrections:
        correction_id = correction.get("id")
        if not isinstance(correction_id, str) or not correction_id:
            missing.append("correction_record_without_id")
            continue
        valid = stable_primary_sources(correction)
        correction_source_ids[correction_id] = [source["source_id"] for source in valid]
        if not valid:
            missing.append(f"correction_primary:{correction_id}")

    orphan_ids: list[str] = []
    for correction in orphan_corrections:
        correction_id = correction.get("id")
        label = correction_id if isinstance(correction_id, str) and correction_id else "<missing-id>"
        orphan_ids.append(label)
        missing.append(f"correction_edge_missing:{label}")

    active = _latest_open_retrieval(active_rows, episode_id)
    closure_ready = not missing
    if episode_sources:
        provenance = PRIMARY
    elif episode.get("accepted_summary"):
        provenance = SUMMARY
    else:
        provenance = UNKNOWN

    result: dict[str, Any] = {
        "episode_id": episode_id,
        "status": COMPLETE if closure_ready else GAP,
        "provenance": provenance,
        "episode_primary_source_ids": [source["source_id"] for source in episode_sources],
        "linked_corrections": [row.get("id") for row in linked_corrections],
        "correction_primary_source_ids": correction_source_ids,
        "orphan_corrections": orphan_ids,
        "missing": missing,
        "can_close_active_retrieval": closure_ready,
    }
    if active is not None:
        result["retrieval_id"] = active.get("id") or active.get("retrieval_id")
        result["retrieval_target"] = active.get("goal") or active.get("target")
    return result


def audit_paths(ledger: Path, active_retrieval: Path, episode_id: str) -> dict[str, Any]:
    return audit_episode(load_jsonl(ledger), load_jsonl(active_retrieval), episode_id)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("episode_id")
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("fixtures/ritsu-continuity/episode-ledger.v0.jsonl"),
    )
    parser.add_argument(
        "--active-retrieval",
        type=Path,
        default=Path("fixtures/ritsu-continuity/active-retrieval.v0.jsonl"),
    )
    parser.add_argument("--require-complete", action="store_true")
    args = parser.parse_args()
    result = audit_paths(args.ledger, args.active_retrieval, args.episode_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_complete and result["status"] != COMPLETE:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
