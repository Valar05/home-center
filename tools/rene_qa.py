#!/usr/bin/env python3
"""Rene QA — deterministic QA CLI.

The CLI is intentionally model-optional. It loads the durable QA policy corpus,
accepts evidence from stdin/files/arguments, and emits structured verdicts.
Future mined judgment examples may enrich policy data without changing the CLI
surface.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_POLICY = ROOT / "config" / "rene_qa.v1.json"


def load_policy(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def gather_text(args: argparse.Namespace) -> str:
    chunks: list[str] = []
    if args.text:
        chunks.append(args.text)
    for filename in args.file or []:
        chunks.append(Path(filename).read_text(encoding="utf-8"))
    if not sys.stdin.isatty():
        piped = sys.stdin.read()
        if piped.strip():
            chunks.append(piped)
    return "\n\n".join(chunks).strip()


def evaluate(policy: dict[str, Any], evidence: str) -> dict[str, Any]:
    text = evidence.lower()
    findings: list[dict[str, str]] = []

    if not evidence:
        findings.append({"severity": "blocker", "id": "missing_evidence", "finding": "No evidence supplied."})

    # Deterministic minimum checks. These do not pretend to understand arbitrary
    # projects; they enforce evidence shape and state separation before any later
    # model-assisted or human judgment layer is allowed to claim PASS.
    state_terms = ["requested", "implemented", "tested", "deployed", "callable", "delivered", "accepted"]
    present_states = [term for term in state_terms if term in text]
    if evidence and len(present_states) < 2:
        findings.append({
            "severity": "warning",
            "id": "state_separation",
            "finding": "Evidence does not clearly distinguish multiple capability states (requested/implemented/tested/deployed/callable/delivered/accepted).",
        })

    test_signals = ["test", "assert", "expected", "actual", "reproduce", "receipt", "readback", "status", "exit code"]
    if evidence and not any(sig in text for sig in test_signals):
        findings.append({
            "severity": "blocker",
            "id": "not_testable",
            "finding": "No observable test, expected/actual result, receipt, readback, or reproducible check found.",
        })

    regression_signals = ["constraint", "regression", "previous", "preserve", "supersede", "rejected"]
    if evidence and not any(sig in text for sig in regression_signals):
        findings.append({
            "severity": "warning",
            "id": "regression_memory",
            "finding": "No explicit regression/constraint preservation check found.",
        })

    blockers = [f for f in findings if f["severity"] == "blocker"]
    warnings = [f for f in findings if f["severity"] == "warning"]
    verdict = "FAIL" if blockers else ("REVISE" if warnings else "PASS")

    return {
        "reviewer": "Rene QA",
        "policy_version": policy["version"],
        "verdict": verdict,
        "findings": findings,
        "evidence_chars": len(evidence),
        "next_action": "Fix blocker findings and rerun Rene QA." if blockers else ("Address warnings or explicitly justify them, then rerun." if warnings else "QA gate passed for the supplied evidence shape."),
        "note": "PASS certifies only the supplied evidence against this deterministic policy; it is not runtime/deployment proof by itself.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="rene-qa", description="Rene QA deterministic quality gate")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY), help="Policy JSON path")
    parser.add_argument("--text", help="Evidence text")
    parser.add_argument("--file", action="append", help="Evidence file; repeatable")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument("--show-policy", action="store_true", help="Print the loaded policy and exit")
    args = parser.parse_args()

    policy = load_policy(Path(args.policy))
    if args.show_policy:
        print(json.dumps(policy, indent=2, ensure_ascii=False))
        return 0

    result = evaluate(policy, gather_text(args))
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"RENE QA: {result['verdict']}")
        for finding in result["findings"]:
            print(f"- {finding['severity'].upper()} {finding['id']}: {finding['finding']}")
        print(f"NEXT: {result['next_action']}")
        print(result["note"])
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
