#!/usr/bin/env python3
"""Deterministic provenance/closure gate for Ritsu episodic retrieval.

This module does not retrieve or infer episode meaning.  It answers a smaller,
more dangerous question: is there enough *primary* evidence to stop saying
CONTINUITY_GAP?

Primary evidence is intentionally strict.  A source counts only when it has:
  * exact readable transcript text; and
  * a stable ``source_id`` binding.

Accepted summaries, adjacent evidence, and text with no stable identity never
close the gate.  Corrections linked by CORRECTED_BY are independently gated so
an episode transcript cannot silently stand in for the later correction that
changed its meaning.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


PRIMARY = "primary_transcript"
SUMMARY = "accepted_summary"
UNKNOWN = "unknown"
GAP = "CONTINUITY_GAP"
COMPLETE = "PRIMARY_COMPLETE"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
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


def _stable_primary_sources(record: dict[str, Any]) -> list[dict[str, str]]:
    """Return only source bindings that are strong enough to claim primary text."""
    valid: list[dict[str, str]] = []
    sources = record.get("primary_sources") or []
    if not isinstance(sources, list):
        return valid
    for source in sources:
        if not isinstance(source, dict):
            continue
        source_id = source.get("source_id")
        text = source.get("text")
        if not isinstance(source_id, str) or not source_id.strip():
            continue
        if not isinstance(text, str) or not text.strip():
            continue
        valid.append({"source_id": source_id.strip(), "text": text.strip()})
    return valid


def _linked_correction_ids(episode: dict[str, Any]) -> list[str]:
    ids: list[str] = []
    for edge in episode.get("edges") or []:
        if not isinstance(edge, dict) or edge.get("type") != "CORRECTED_BY":
            continue
        target = edge.get("target")
        if isinstance(target, str) and target and target not in ids:
            ids.append(target)
    return ids


def _latest_open_retrieval(
    active_rows: Iterable[dict[str, Any]], episode_id: str
) -> dict[str, Any] | None:
    for row in reversed(list(active_rows)):
        if row.get("target_episode") != episode_id:
            continue
        if row.get("status") == "open":
            return row
        # A later explicit close/cancel for the same target suppresses older opens.
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

    episode_sources = _stable_primary_sources(episode)
    linked_ids = _linked_correction_ids(episode)
    corrections_by_id = {
        row.get("id"): row
        for row in ledger_rows
        if row.get("record_type") == "correction"
        and row.get("target_episode") == episode_id
        and isinstance(row.get("id"), str)
    }

    missing: list[str] = []
    if not episode_sources:
        missing.append("episode_primary_transcript")

    correction_sources: dict[str, list[str]] = {}
    for correction_id in linked_ids:
        correction = corrections_by_id.get(correction_id)
        if correction is None:
            missing.append(f"correction_record:{correction_id}")
            correction_sources[correction_id] = []
            continue
        valid = _stable_primary_sources(correction)
        correction_sources[correction_id] = [source["source_id"] for source in valid]
        if not valid:
            missing.append(f"correction_primary:{correction_id}")

    # A correction record that targets this episode but is not linked is itself a
    # provenance defect.  Silent orphan corrections are how a later meaning change
    # gets dropped while the earlier scene still looks "complete".
    orphan_corrections = sorted(
        correction_id
        for correction_id in corrections_by_id
        if correction_id not in linked_ids
    )
    for correction_id in orphan_corrections:
        missing.append(f"correction_edge_missing:{correction_id}")

    active = _latest_open_retrieval(active_rows, episode_id)
    primary_episode_ready = bool(episode_sources)
    closure_ready = not missing

    if primary_episode_ready:
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
        "linked_corrections": linked_ids,
        "correction_primary_source_ids": correction_sources,
        "orphan_corrections": orphan_corrections,
        "missing": missing,
        "can_close_active_retrieval": closure_ready,
    }
    if active is not None:
        result["retrieval_id"] = active.get("retrieval_id") or active.get("id")
        result["retrieval_target"] = active.get("goal") or active.get("target")
    return result


def audit_paths(ledger: Path, active_retrieval: Path, episode_id: str) -> dict[str, Any]:
    return audit_episode(_load_jsonl(ledger), _load_jsonl(active_retrieval), episode_id)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
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
    parser.add_argument(
        "--require-complete",
        action="store_true",
        help="exit 2 while CONTINUITY_GAP is still open",
    )
    args = parser.parse_args()
    result = audit_paths(args.ledger, args.active_retrieval, args.episode_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.require_complete and result["status"] != COMPLETE:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
