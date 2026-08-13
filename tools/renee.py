#!/usr/bin/env python3
"""Deterministic Regnet QA CLI.

Regnet QA is the unified quality/evidence interface synthesized from the former
Renee QA office and Regnet. Synthetic output is always marked
SYNTHETIC_REGNET and can never self-promote.
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
HUMAN_PROVENANCE = {"REGNET_DIRECT", "REGNET_CORRECTION", "RENEE_DIRECT", "RENEE_CORRECTION", "DREW_RECALL"}
DIRECT_REGNET_PROVENANCE = {"REGNET_DIRECT", "REGNET_CORRECTION", "RENEE_DIRECT", "RENEE_CORRECTION"}
RECORDABLE_PROVENANCE = HUMAN_PROVENANCE | {"DERIVED_RULE"}


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
        raise SystemExit(f"Regnet QA config missing or invalid: {CONFIG_PATH}")
    return data


def state_paths(home: Path) -> dict[str, Path]:
    return {"corpus": home / "corpus.jsonl", "receipts": home / "receipts", "corrections": home / "corrections.jsonl"}


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")


def iter_jsonl(path: Path):
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            yield row


def digest(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()[:20]


def emit(value: Any, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True)); return
    if isinstance(value, dict):
        for key, val in value.items():
            print(f"{key}: {json.dumps(val, sort_keys=True) if isinstance(val, (dict, list)) else val}")
    else:
        print(value)


def review(args: argparse.Namespace) -> int:
    cfg = config()
    evidence = []
    for item in args.evidence or []:
        p = Path(item)
        evidence.append({"path": str(p), "exists": p.exists(), "size": p.stat().st_size if p.exists() else None})
    evidence_refs = [ref.strip() for ref in (args.evidence_ref or []) if ref.strip()]
    has_evidence = bool(evidence or evidence_refs)
    blockers, warnings = [], []
    if not args.claim.strip(): blockers.append("claim is empty")
    if not args.acceptance: blockers.append("no explicit acceptance criterion supplied")
    if args.require_evidence and not has_evidence: blockers.append("evidence required but none supplied")
    missing = [e["path"] for e in evidence if not e["exists"]]
    if missing: blockers.append(f"missing evidence: {', '.join(missing)}")
    if args.state in {"tested", "deployed", "callable", "delivered", "accepted"} and not has_evidence:
        blockers.append(f"{args.state} claim has no supplied receipt/evidence")
    if args.actual_regnet and args.provenance not in DIRECT_REGNET_PROVENANCE:
        blockers.append("direct Regnet attribution requires REGNET_DIRECT or REGNET_CORRECTION; legacy RENEE_DIRECT/RENEE_CORRECTION remain accepted lineage; DREW_RECALL stays explicitly Drew-reported")
    if args.unresolved:
        blockers.extend(f"unresolved material QA issue: {item}" for item in args.unresolved)
    if not args.failure_path:
        warnings.append("no reachable failure path recorded; confirm this is genuinely immaterial")
    verdict = "REVISE_REQUIRED" if blockers else "PASS"
    payload = {
        "schema":"home-center.regnet-qa.review.v1","reviewer":"Regnet QA","provenance":"SYNTHETIC_REGNET","created_at":now(),
        "claim":args.claim,"capability_state":args.state,"acceptance":args.acceptance or [],"evidence":evidence,"evidence_refs":evidence_refs,
        "reachable_failure_paths":args.failure_path or [],"dissent":args.dissent or [],"unresolved":args.unresolved or [],
        "blockers":blockers,"warnings":warnings,"questions":cfg["questions"],"verdict":verdict,
        "can_grant_final_stop":False,"next_gate":"Venice" if verdict == "PASS" else "repair current QA slice"
    }
    payload["receipt_id"] = "rqa-" + digest(payload)
    receipt_path = Path(args.home) / "receipts" / f"{payload['receipt_id']}.json"
    write_json(receipt_path, payload); payload["receipt_path"] = str(receipt_path); emit(payload, args.json)
    return 0 if verdict == "PASS" else 2


def record(args: argparse.Namespace) -> int:
    if args.provenance not in RECORDABLE_PROVENANCE: raise SystemExit("synthetic output cannot be recorded as calibration evidence")
    if args.provenance == "DERIVED_RULE" and not args.derived_from: raise SystemExit("DERIVED_RULE requires at least one --derived-from source fingerprint/locator")
    row = {"schema":"home-center.regnet-qa.precedent.v1","created_at":now(),"provenance":args.provenance,"source":args.source,
           "finding":args.finding,"tags":sorted(set(args.tag or [])),"derived_from":args.derived_from or [],
           "authoritative_about_regnet":args.provenance in DIRECT_REGNET_PROVENANCE}
    row["fingerprint"] = digest(row); append_jsonl(Path(args.home) / "corpus.jsonl", row); emit(row, args.json); return 0


def correct(args: argparse.Namespace) -> int:
    row = {"schema":"home-center.regnet-qa.correction.v1","created_at":now(),"receipt_id":args.receipt,"provenance":args.provenance,
           "source":args.source,"correction":args.text,"regression_target":args.regression_target,
           "authoritative_about_regnet":args.provenance in DIRECT_REGNET_PROVENANCE}
    row["fingerprint"] = digest(row); append_jsonl(Path(args.home) / "corrections.jsonl", row); emit(row, args.json); return 0


def precedent(args: argparse.Namespace) -> int:
    cfg, rows = config(), []
    for path in [Path(args.home) / "corrections.jsonl", Path(args.home) / "corpus.jsonl"]:
        for row in iter_jsonl(path) or []:
            if args.query.lower() in json.dumps(row).lower(): rows.append(row)
    rows.sort(key=lambda r: cfg["provenance_classes"].get(r.get("provenance"), {"rank":0})["rank"], reverse=True)
    emit({"query":args.query,"matches":rows[:args.limit]}, args.json); return 0


def explain(args: argparse.Namespace) -> int:
    cfg = config(); emit({k:cfg[k] for k in ["keyword","authority","questions","hard_gates","synthetic_policy","integration"]}, args.json); return 0


def status(args: argparse.Namespace) -> int:
    paths = state_paths(Path(args.home)); counts = {}
    for name in ("corpus","corrections"): counts[name] = sum(1 for _ in (iter_jsonl(paths[name]) or []))
    counts["receipts"] = len(list(paths["receipts"].glob("*.json"))) if paths["receipts"].exists() else 0
    emit({"keyword":config()["keyword"],"config":str(CONFIG_PATH),"home":args.home,"paths":{k:str(v) for k,v in paths.items()},"counts":counts}, args.json); return 0


def diff_judgment(args: argparse.Namespace) -> int:
    a,b = load_json(Path(args.left),None), load_json(Path(args.right),None)
    if not isinstance(a,dict) or not isinstance(b,dict): raise SystemExit("diff-judgment expects two JSON review receipts")
    changes = {k:{"left":a.get(k),"right":b.get(k)} for k in sorted(set(a)|set(b)) if a.get(k)!=b.get(k)}
    emit({"left":args.left,"right":args.right,"changes":changes}, args.json); return 0


def regress(args: argparse.Namespace) -> int:
    home=Path(args.home); receipts=sorted((home/"receipts").glob("*.json")) if (home/"receipts").exists() else []
    non_pass=[]
    for p in receipts:
        row=load_json(p,{})
        if row.get("verdict")!="PASS": non_pass.append({"receipt_id":row.get("receipt_id"),"claim":row.get("claim"),"blockers":row.get("blockers",[])})
    corrections=[row for row in (iter_jsonl(home/"corrections.jsonl") or []) if row.get("regression_target")]
    emit({"receipt_count":len(receipts),"non_pass_receipts":non_pass,"human_regression_targets":corrections}, args.json); return 0 if not non_pass else 3


def parser() -> argparse.ArgumentParser:
    p=argparse.ArgumentParser(prog="regnet",description="Deterministic Regnet QA interface"); p.add_argument("--home",default=str(DEFAULT_STATE)); p.add_argument("--json",action="store_true"); sub=p.add_subparsers(dest="command",required=True)
    r=sub.add_parser("review"); r.add_argument("claim"); r.add_argument("--state",choices=["requested","intended","implemented","tested","deployed","callable","delivered","accepted"],default="implemented"); r.add_argument("--acceptance",action="append"); r.add_argument("--evidence",action="append",help="Local evidence file; existence is verified"); r.add_argument("--evidence-ref",action="append",help="External receipt/reference such as GitHub/Drive/runtime ID or URL; attribution is preserved but not fetched by this CLI"); r.add_argument("--failure-path",action="append"); r.add_argument("--unresolved",action="append"); r.add_argument("--dissent",action="append"); r.add_argument("--require-evidence",action="store_true"); r.add_argument("--actual-regnet","--actual-renee",dest="actual_regnet",action="store_true",help="Directly attributes judgment to Regnet; legacy flag retained"); r.add_argument("--provenance",choices=["REGNET_DIRECT","REGNET_CORRECTION","RENEE_DIRECT","RENEE_CORRECTION","DREW_RECALL","DERIVED_RULE","SYNTHETIC_REGNET","SYNTHETIC_RENEE"],default="SYNTHETIC_REGNET"); r.set_defaults(func=review)
    n=sub.add_parser("record"); n.add_argument("finding"); n.add_argument("--provenance",required=True,choices=sorted(RECORDABLE_PROVENANCE)); n.add_argument("--source",required=True); n.add_argument("--tag",action="append"); n.add_argument("--derived-from",action="append"); n.set_defaults(func=record)
    c=sub.add_parser("correct"); c.add_argument("receipt"); c.add_argument("text"); c.add_argument("--provenance",required=True,choices=sorted(HUMAN_PROVENANCE)); c.add_argument("--source",required=True); c.add_argument("--regression-target"); c.set_defaults(func=correct)
    e=sub.add_parser("explain"); e.set_defaults(func=explain)
    q=sub.add_parser("precedent"); q.add_argument("query"); q.add_argument("--limit",type=int,default=20); q.set_defaults(func=precedent)
    d=sub.add_parser("diff-judgment"); d.add_argument("left"); d.add_argument("right"); d.set_defaults(func=diff_judgment)
    g=sub.add_parser("regress"); g.set_defaults(func=regress)
    s=sub.add_parser("status"); s.set_defaults(func=status); return p


def main() -> int:
    args=parser().parse_args(); return args.func(args)

if __name__ == "__main__": raise SystemExit(main())
