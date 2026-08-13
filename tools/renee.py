#!/usr/bin/env python3
"""Deterministic Renee QA CLI.

Renee CLI is a quality/evidence interface, not a counterfeit of the human Renee.
Synthetic output is always marked SYNTHETIC_RENEE and can never self-promote.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "renee_qa.v1.json"
DEFAULT_STATE = Path(os.environ.get("RENEE_QA_HOME", Path.home() / ".home-center" / "renee-qa"))


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def config() -> dict[str, Any]:
    data = load_json(CONFIG_PATH, None)
    if not isinstance(data, dict):
        raise SystemExit(f"Renee QA config missing or invalid: {CONFIG_PATH}")
    return data


def state_paths(home: Path) -> dict[str, Path]:
    return {
        "corpus": home / "corpus.jsonl",
        "receipts": home / "receipts",
        "corrections": home / "corrections.jsonl",
    }


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()[:20]


def emit(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    if isinstance(value, dict):
        for key, val in value.items():
            if isinstance(val, (dict, list)):
                print(f"{key}: {json.dumps(val, sort_keys=True)}")
            else:
                print(f"{key}: {val}")
    else:
        print(value)


def review(args: argparse.Namespace) -> int:
    cfg = config()
    evidence = []
    for item in args.evidence or []:
        p = Path(item)
        evidence.append({"path": str(p), "exists": p.exists(), "size": p.stat().st_size if p.exists() else None})

    blockers: list[str] = []
    warnings: list[str] = []
    if not args.claim.strip():
        blockers.append("claim is empty")
    if args.require_evidence and not evidence:
        blockers.append("evidence required but none supplied")
    missing = [e["path"] for e in evidence if not e["exists"]]
    if missing:
        blockers.append(f"missing evidence: {', '.join(missing)}")
    if args.state in {"deployed", "callable", "delivered", "accepted"} and not evidence:
        blockers.append(f"{args.state} claim has no supplied receipt/evidence")
    if args.actual_renee and args.provenance not in {"RENEE_DIRECT", "RENEE_CORRECTION", "DREW_RECALL"}:
        blockers.append("actual-Renee attribution requires human provenance; synthetic/derived provenance is forbidden")
    if not args.acceptance:
        warnings.append("no explicit acceptance criterion supplied")

    verdict = "REVISE_REQUIRED" if blockers else "PASS"
    payload = {
        "schema": "home-center.renee-qa.review.v1",
        "reviewer": "Rene QA",
        "provenance": "SYNTHETIC_RENEE",
        "created_at": now(),
        "claim": args.claim,
        "capability_state": args.state,
        "acceptance": args.acceptance or [],
        "evidence": evidence,
        "blockers": blockers,
        "warnings": warnings,
        "questions": cfg["questions"],
        "verdict": verdict,
        "can_grant_final_stop": False,
        "next_gate": "Venice" if verdict == "PASS" else "repair current QA slice",
    }
    payload["receipt_id"] = "rqa-" + digest(payload)
    receipt_path = Path(args.home) / "receipts" / f"{payload['receipt_id']}.json"
    write_json(receipt_path, payload)
    payload["receipt_path"] = str(receipt_path)
    emit(payload, args.json)
    return 0 if verdict == "PASS" else 2


def correct(args: argparse.Namespace) -> int:
    allowed = {"RENEE_DIRECT", "RENEE_CORRECTION", "DREW_RECALL"}
    if args.provenance not in allowed:
        raise SystemExit(f"correction provenance must be one of: {', '.join(sorted(allowed))}")
    row = {
        "schema": "home-center.renee-qa.correction.v1",
        "created_at": now(),
        "receipt_id": args.receipt,
        "provenance": args.provenance,
        "source": args.source,
        "correction": args.text,
        "authoritative_about_actual_renee": args.provenance in {"RENEE_DIRECT", "RENEE_CORRECTION"},
    }
    row["fingerprint"] = digest(row)
    append_jsonl(Path(args.home) / "corrections.jsonl", row)
    emit(row, args.json)
    return 0


def precedent(args: argparse.Namespace) -> int:
    rows = []
    for path in [Path(args.home) / "corrections.jsonl", Path(args.home) / "corpus.jsonl"]:
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                hay = json.dumps(row).lower()
                if args.query.lower() in hay:
                    rows.append(row)
    rows.sort(key=lambda r: config()["provenance_classes"].get(r.get("provenance"), {"rank": 0})["rank"], reverse=True)
    emit({"query": args.query, "matches": rows[: args.limit]}, args.json)
    return 0


def explain(args: argparse.Namespace) -> int:
    cfg = config()
    emit({"keyword": cfg["keyword"], "authority": cfg["authority"], "questions": cfg["questions"], "hard_gates": cfg["hard_gates"], "synthetic_policy": cfg["synthetic_policy"]}, args.json)
    return 0


def status(args: argparse.Namespace) -> int:
    paths = state_paths(Path(args.home))
    out = {"keyword": config()["keyword"], "config": str(CONFIG_PATH), "home": args.home, "paths": {k: str(v) for k, v in paths.items()}, "exists": {k: v.exists() for k, v in paths.items()}}
    emit(out, args.json)
    return 0


def diff_judgment(args: argparse.Namespace) -> int:
    a = load_json(Path(args.left), None)
    b = load_json(Path(args.right), None)
    if not isinstance(a, dict) or not isinstance(b, dict):
        raise SystemExit("diff-judgment expects two JSON review receipts")
    keys = sorted(set(a) | set(b))
    changes = {k: {"left": a.get(k), "right": b.get(k)} for k in keys if a.get(k) != b.get(k)}
    emit({"left": args.left, "right": args.right, "changes": changes}, args.json)
    return 0


def regress(args: argparse.Namespace) -> int:
    home = Path(args.home)
    receipts = sorted((home / "receipts").glob("*.json")) if (home / "receipts").exists() else []
    failures = []
    for p in receipts:
        row = load_json(p, {})
        if row.get("verdict") != "PASS":
            failures.append({"receipt_id": row.get("receipt_id"), "claim": row.get("claim"), "blockers": row.get("blockers", [])})
    emit({"receipt_count": len(receipts), "non_pass_receipts": failures}, args.json)
    return 0 if not failures else 3


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="renee", description="Deterministic Renee QA interface")
    p.add_argument("--home", default=str(DEFAULT_STATE))
    p.add_argument("--json", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)

    r = sub.add_parser("review")
    r.add_argument("claim")
    r.add_argument("--state", choices=["requested","intended","implemented","tested","deployed","callable","delivered","accepted"], default="implemented")
    r.add_argument("--acceptance", action="append")
    r.add_argument("--evidence", action="append")
    r.add_argument("--require-evidence", action="store_true")
    r.add_argument("--actual-renee", action="store_true", help="Claim attributes judgment to actual Renee; requires human provenance")
    r.add_argument("--provenance", choices=["RENEE_DIRECT","RENEE_CORRECTION","DREW_RECALL","DERIVED_RULE","SYNTHETIC_RENEE"], default="SYNTHETIC_RENEE")
    r.set_defaults(func=review)

    c = sub.add_parser("correct")
    c.add_argument("receipt")
    c.add_argument("text")
    c.add_argument("--provenance", required=True, choices=["RENEE_DIRECT","RENEE_CORRECTION","DREW_RECALL"])
    c.add_argument("--source", required=True, help="Attributable source locator; do not paste proprietary content by default")
    c.set_defaults(func=correct)

    e = sub.add_parser("explain")
    e.set_defaults(func=explain)

    q = sub.add_parser("precedent")
    q.add_argument("query")
    q.add_argument("--limit", type=int, default=20)
    q.set_defaults(func=precedent)

    d = sub.add_parser("diff-judgment")
    d.add_argument("left")
    d.add_argument("right")
    d.set_defaults(func=diff_judgment)

    g = sub.add_parser("regress")
    g.set_defaults(func=regress)

    s = sub.add_parser("status")
    s.set_defaults(func=status)
    return p


def main() -> int:
    args = parser().parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
