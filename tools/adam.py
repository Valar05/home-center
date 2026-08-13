#!/usr/bin/env python3
"""Adam body router for Home Center and the phone-local governed scene loop."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools" / "adam_planned_venice.py"
CANON_SOURCER = ROOT / "tools" / "canon_sourcer.py"
ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad", "scene")
MAX_RECEIPT_TEXT = 6000
MAX_CANON_PACKET = 18000


def tail(value: str, limit: int = MAX_RECEIPT_TEXT) -> str:
    value = str(value or "")
    return value if len(value) <= limit else value[-limit:]


def receipt(mode: str, ok: bool, **data) -> int:
    print(json.dumps({"schema": "adam-body-router-v4", "mode": mode, "ok": bool(ok), **data}, ensure_ascii=False, sort_keys=True))
    return 0 if ok else 1


def run_terminal(text: str, cwd: str, timeout: int) -> int:
    if not text.strip():
        return receipt("terminal", False, error="empty_request")
    p = subprocess.run(["bash", "-lc", text], cwd=cwd, text=True, capture_output=True, timeout=timeout)
    return receipt("terminal", p.returncode == 0, command=tail(text, 1000), cwd=str(Path(cwd).resolve()), rc=p.returncode, stdout=tail(p.stdout), stderr=tail(p.stderr))


def worker_commission(mode: str, text: str) -> str:
    if mode == "chat":
        return f"Conversational request from Drew. Research material unknowns, make a bounded plan, select relevant Judgment Jars, antagonize the plan, obtain Venice PLAN_ALLOWED, then respond usefully. Do not execute unless Drew clearly requests action. Drew said: {text}"
    if mode == "continue":
        return f"Coding/work commission from Drew. Research repository truth, plan, select relevant Judgment Jars, antagonize, obtain Venice PLAN_ALLOWED, then work Codex-style, validate, and return exact evidence after Venice completion/code review. Commission: {text}"
    if mode == "vlad":
        return f"Drew requests an independent critical second opinion in Vlad's role. Research material unknowns, plan the bounded analysis, select relevant Judgment Jars, antagonize assumptions, obtain Venice PLAN_ALLOWED, then return a concise governed response. Question: {text}"
    raise ValueError(mode)


def run_worker_commission(mode: str, commission: str, cwd: str) -> int:
    if not WORKER.is_file():
        return receipt(mode, False, error="worker_missing", worker=str(WORKER))
    p = subprocess.run([sys.executable, str(WORKER), commission], cwd=cwd, text=True, capture_output=True)
    return receipt(mode, p.returncode == 0, worker="codex-phone-planned-venice-reviewed", jarGoverned=True, preExecutionPlanReview=True, veniceReviewed=True, daemonBackoff=True, rc=p.returncode, stdout=tail(p.stdout), stderr=tail(p.stderr))


def run_worker(mode: str, text: str, cwd: str) -> int:
    if not text.strip():
        return receipt(mode, False, error="empty_request")
    return run_worker_commission(mode, worker_commission(mode, text), cwd)


def run_scene(text: str, cwd: str, timeout: int) -> int:
    if not text.strip():
        return receipt("scene", False, error="empty_request")
    if not CANON_SOURCER.is_file():
        return receipt("scene", False, error="canon_sourcer_missing", sourcer=str(CANON_SOURCER))
    canary = "Vanguard kicks Android 67's ass proper. Android puts up a good fight, visibly improves, and gets weirder. Vanguard remains a woman, Alexis De’arc, and her established authority, grounded Zornhau, and victory may not be flattened or transferred to Android."
    query = f"Vanguard Alexis De’arc Android 67 Zornhau Fleshpunk spar canon {text}"
    source = subprocess.run([sys.executable, str(CANON_SOURCER), "packet", query], cwd=cwd, text=True, capture_output=True, timeout=timeout)
    if source.returncode != 0:
        return receipt("scene", False, error="canon_packet_failed", rc=source.returncode, stdout=tail(source.stdout), stderr=tail(source.stderr))
    try:
        packet = json.loads(source.stdout)
        canon_text = str(packet["text"])[:MAX_CANON_PACKET]
        canon_hash = str(packet["sha256"])
        canon_sources = packet["sources"]
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        return receipt("scene", False, error=f"invalid_canon_packet:{exc}", stdout=tail(source.stdout))
    commission = f"""PHONE-LOCAL INNER FORTRESS SCENE TURN

Drew's scene request:
{text}

Acceptance canary:
{canary}

Deterministic canon packet SHA-256: {canon_hash}
{canon_text}

Required route:
1. Treat the canon packet and Drew's current words as evidence; do not promote guesses.
2. Select only the narrowest relevant Character/Judgment Jar context.
3. Draft one playable scene turn.
4. Regnet QA must return VERDICT: PASS|FAIL, BLOCKERS, and NEXT. A FAIL revises only the failed slice.
5. Venice must give the final CONTINUE or STOP_ALLOWED ruling.
6. Return the scene plus compact provenance and rulings. Never call the scene canon merely because the pipeline ran.

Hard canary gate: Vanguard wins decisively after a real fight. Android improves and gets weirder without defeating, diminishing, masculinizing, or replacing Vanguard."""
    if not WORKER.is_file():
        return receipt("scene", False, error="worker_missing", worker=str(WORKER))
    p = subprocess.run([sys.executable, str(WORKER), commission], cwd=cwd, text=True, capture_output=True)
    return receipt("scene", p.returncode == 0, worker="codex-phone-planned-venice-reviewed", canonSourcer="deterministic", canonPacketSha256=canon_hash, canonSources=canon_sources, canary="vanguard-wins-android-improves-and-gets-weirder", regnetRequired=True, veniceReviewed=True, rc=p.returncode, stdout=tail(p.stdout), stderr=tail(p.stderr))


def run_mode(mode: str, text: str, cwd: str, timeout: int) -> int:
    if mode not in ONE_SHOT_MODES:
        return receipt(mode, False, error="unsupported_mode")
    if mode == "terminal":
        return run_terminal(text, cwd, timeout)
    if mode == "scene":
        return run_scene(text, cwd, timeout)
    return run_worker(mode, text, cwd)


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
