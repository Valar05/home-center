#!/usr/bin/env python3
"""Adam body router for Home Center.

This file intentionally contains no conversational personality runtime.
Bare `adam` is installed to tools/adam_planned_venice_receipted.py. The Android
overlay keeps TERM/CHAT/CONT/VLAD transport names; CHAT/CONT/VLAD become bounded
commissions for the same planned, Jar-governed worker. Only terminal is an
exact no-interpretation shell body lane.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools" / "adam_planned_venice_receipted.py"
ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad")
MAX_RECEIPT_TEXT = 6000


def tail(value: str, limit: int = MAX_RECEIPT_TEXT) -> str:
    value = str(value or "")
    return value if len(value) <= limit else value[-limit:]


def receipt(mode: str, ok: bool, **data) -> int:
    print(json.dumps({
        "schema": "adam-body-router-v4-judgment-jar-usage-receipts",
        "mode": mode,
        "ok": bool(ok),
        **data,
    }, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


def run_terminal(text: str, cwd: str, timeout: int) -> int:
    if not text.strip():
        return receipt("terminal", False, error="empty_request")
    p = subprocess.run(["bash", "-lc", text], cwd=cwd, text=True, capture_output=True, timeout=timeout)
    return receipt(
        "terminal",
        p.returncode == 0,
        command=tail(text, 1000),
        cwd=str(Path(cwd).resolve()),
        rc=p.returncode,
        stdout=tail(p.stdout),
        stderr=tail(p.stderr),
    )


def worker_commission(mode: str, text: str) -> str:
    if mode == "chat":
        return f"Conversational request from Drew. Research material unknowns, make a bounded plan, select relevant Judgment Jars, declare the output kind, antagonize the plan, obtain Venice PLAN_ALLOWED, then respond usefully. Do not execute unless Drew's text clearly requests action. Drew said: {text}"
    if mode == "continue":
        return f"Coding/work commission from Drew. Research repository truth, plan, select relevant Judgment Jars, declare the output kind, antagonize, obtain Venice PLAN_ALLOWED, then work Codex-style, validate, and return exact evidence after Venice completion/code review. Commission: {text}"
    if mode == "vlad":
        return f"Drew explicitly requests an independent critical second opinion in Vlad's role. Research material unknowns, plan the bounded analysis, select relevant Judgment Jars, declare the output kind, antagonize assumptions, obtain Venice PLAN_ALLOWED, then return a concise governed response. Question: {text}"
    raise ValueError(mode)


def run_worker(mode: str, text: str, cwd: str, timeout: int) -> int:
    if not WORKER.is_file():
        return receipt(mode, False, error="worker_missing", worker=str(WORKER))
    if not text.strip():
        return receipt(mode, False, error="empty_request")
    commission = worker_commission(mode, text)
    p = subprocess.run([sys.executable, str(WORKER), commission], cwd=cwd, text=True, capture_output=True)
    return receipt(
        mode,
        p.returncode == 0,
        worker="planned-venice-reviewed-judgment-jar-receipted",
        jarGoverned=True,
        jarUsageReceipts=True,
        jarOutputKindRequired=True,
        homeCenterJarDelivery=True,
        preExecutionPlanReview=True,
        veniceReviewed=True,
        daemonBackoff=True,
        rc=p.returncode,
        stdout=tail(p.stdout),
        stderr=tail(p.stderr),
    )


def run_mode(mode: str, text: str, cwd: str, timeout: int) -> int:
    if mode not in ONE_SHOT_MODES:
        return receipt(mode, False, error="unsupported_mode")
    if mode == "terminal":
        return run_terminal(text, cwd, timeout)
    return run_worker(mode, text, cwd, timeout)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="adam", description="Home Center Adam body router")
    parser.add_argument("mode", choices=ONE_SHOT_MODES)
    parser.add_argument("text", nargs="?", default="")
    parser.add_argument("--cwd", default=str(ROOT))
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args(argv)
    text = args.text if args.text else sys.stdin.read()
    return run_mode(args.mode, text, args.cwd, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
