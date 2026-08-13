#!/usr/bin/env python3
"""Adam body router for Home Center.

Bare `adam` is installed to tools/adam_planned_venice.py. The Android overlay
keeps explicit TERM/CHAT/CONT/VLAD/RADIO modes. RADIO is deterministic: it
passes Drew's exact prompt to the local Spotify radio policy/compiler and never
invokes a conversational worker, generic media key, Activity, or screen path.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools" / "adam_planned_venice.py"
RADIO_SOURCE = ROOT / "tools" / "spotify_radio.py"
RADIO_INSTALLED = Path(os.environ.get("HC_SPOTIFY_RADIO_BIN", "~/bin/spotify-radio")).expanduser()
ONE_SHOT_MODES = ("terminal", "chat", "continue", "vlad", "radio")
MAX_RECEIPT_TEXT = 6000


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
        return f"Conversational request from Drew. Research any material unknowns, make a bounded plan, select relevant Judgment Jars, antagonize the plan, obtain Venice PLAN_ALLOWED, then respond usefully. Do not execute unless Drew's text clearly requests action. Drew said: {text}"
    if mode == "continue":
        return f"Coding/work commission from Drew. Research repository truth, plan, select relevant Judgment Jars, antagonize, obtain Venice PLAN_ALLOWED, then work Codex-style, validate, and return exact evidence after Venice completion/code review. Commission: {text}"
    if mode == "vlad":
        return f"Drew explicitly requests an independent critical second opinion in Vlad's role. Research material unknowns, plan the bounded analysis, select relevant Judgment Jars, antagonize assumptions, obtain Venice PLAN_ALLOWED, then return a concise governed response. Question: {text}"
    raise ValueError(mode)


def run_worker(mode: str, text: str, cwd: str, timeout: int) -> int:
    if not WORKER.is_file():
        return receipt(mode, False, error="worker_missing", worker=str(WORKER))
    if not text.strip():
        return receipt(mode, False, error="empty_request")
    commission = worker_commission(mode, text)
    p = subprocess.run([sys.executable, str(WORKER), commission], cwd=cwd, text=True, capture_output=True)
    return receipt(mode, p.returncode == 0, worker="codex-phone-planned-venice-reviewed", jarGoverned=True, preExecutionPlanReview=True, veniceReviewed=True, daemonBackoff=True, rc=p.returncode, stdout=tail(p.stdout), stderr=tail(p.stderr))


def _radio_command(text: str) -> list[str] | None:
    if RADIO_INSTALLED.is_file():
        return [str(RADIO_INSTALLED), "prompt", text]
    if RADIO_SOURCE.is_file():
        return [sys.executable, str(RADIO_SOURCE), "prompt", text]
    return None


def _last_json_line(stdout: str) -> dict:
    for line in reversed(str(stdout or "").splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return {}


def run_radio(text: str, cwd: str, timeout: int) -> int:
    if not text.strip():
        return receipt("radio", False, error="empty_request")
    command = _radio_command(text)
    if command is None:
        return receipt("radio", False, error="spotify_radio_controller_missing")
    p = subprocess.run(command, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    parsed = _last_json_line(p.stdout)
    detail = str(parsed.get("detail") or parsed.get("error") or "")
    result = parsed.get("result") if isinstance(parsed.get("result"), dict) else {}
    playlist = str(result.get("playlistName") or "")
    item_count = result.get("itemCount")
    if p.returncode == 0:
        response = detail or "Spotify background radio command completed."
        if playlist:
            response += f" {playlist}"
            if isinstance(item_count, int): response += f" has {item_count} tracks."
    else:
        response = f"Spotify background radio blocked: {detail or 'controller returned failure'}."
    return receipt(
        "radio",
        p.returncode == 0,
        response=tail(response, 2000),
        controller="spotify-radio",
        deterministic=True,
        targetPackage="com.spotify.music",
        activityLaunchUsed=False,
        genericMediaKeyUsed=False,
        screenAutomationUsed=False,
        rc=p.returncode,
        stdout=tail(p.stdout),
        stderr=tail(p.stderr),
    )


def run_mode(mode: str, text: str, cwd: str, timeout: int) -> int:
    if mode not in ONE_SHOT_MODES:
        return receipt(mode, False, error="unsupported_mode")
    if mode == "terminal":
        return run_terminal(text, cwd, timeout)
    if mode == "radio":
        return run_radio(text, cwd, timeout)
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
