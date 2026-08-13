#!/usr/bin/env python3
"""Adam body router for Home Center.

This file intentionally contains no conversational personality runtime.
Bare `adam` is installed to tools/adam_planned_venice.py. The Android overlay
keeps explicit transport names. CHAT/CONT/VLAD become bounded commissions for
the same planned, Jar-governed Codex worker. TERM is an exact shell body lane.
TEXT is deterministic read-only Home Center SMS evidence access; it does not
invoke a model and has no message-send authority.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools" / "adam_planned_venice.py"
ONE_SHOT_MODES = ("terminal", "text", "chat", "continue", "vlad")
MAX_RECEIPT_TEXT = 6000
SMS_ID = re.compile(r"^sms_[a-f0-9]{32,64}$")


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


def _text_result(value: dict) -> str:
    """Render only the bounded/redacted sms_calendar public record surface."""
    if isinstance(value.get("items"), list):
        rows = value.get("items") or []
    elif isinstance(value.get("messages"), list):
        rows = value.get("messages") or []
    elif isinstance(value.get("records"), list):
        rows = value.get("records") or []
    else:
        rows = []
    if rows:
        out = []
        for item in rows[:50]:
            if not isinstance(item, dict):
                continue
            ref = str(item.get("sourceMessageReference") or item.get("messageId") or "")
            sender = str(item.get("sender") or "unknown_sender")
            state = str(item.get("state") or "")
            classification = item.get("classification") or {}
            excerpt = str(classification.get("sourceExcerpt") or "") if isinstance(classification, dict) else ""
            received = item.get("receivedAtMs") or ""
            out.append(" | ".join(x for x in [ref, sender, state, str(received), excerpt] if x))
        return "\n".join(out) or "No bounded SMS evidence returned."
    # `sms_calendar.get` returns one bounded public record.
    if value:
        classification = value.get("classification") or {}
        excerpt = str(classification.get("sourceExcerpt") or "") if isinstance(classification, dict) else ""
        fields = [
            str(value.get("sourceMessageReference") or value.get("messageId") or ""),
            str(value.get("sender") or "unknown_sender"),
            str(value.get("state") or ""),
            excerpt,
        ]
        return " | ".join(x for x in fields if x)
    return "No bounded SMS evidence returned."


def run_text(text: str, cwd: str, timeout: int) -> int:
    """Deterministic read-only SMS-calendar evidence lane through Home Center MCP."""
    try:
        from home_center_mcp_client import HomeCenterError, HomeCenterMcp
    except Exception as exc:
        return receipt("text", False, error="home_center_client_unavailable", detail=tail(str(exc), 1000))

    words = text.strip().split()
    command = words[0].lower() if words else "recent"
    try:
        client = HomeCenterMcp(timeout=max(5, min(timeout, 120)))
        if command in {"recent", "inbox", "list", "status"}:
            limit = 10
            if len(words) > 1:
                try:
                    limit = max(1, min(50, int(words[1])))
                except ValueError:
                    return receipt("text", False, error="invalid_limit", usage="TEXT: recent [1..50] | get <sms_id>")
            value = client.drive_operation("sms_calendar.inbox", {"limit": limit})
            return receipt(
                "text", True,
                operation="sms_calendar.inbox",
                readOnly=True,
                rawMessageBodyExposed=False,
                authoritativeUnreadState=False,
                authoritativeProviderThreadId=False,
                outboundAuthority=False,
                response=_text_result(value),
            )
        if command == "get":
            message_id = words[1] if len(words) > 1 else ""
            if not SMS_ID.fullmatch(message_id):
                return receipt("text", False, error="invalid_message_id", usage="TEXT: get <sms_id>")
            value = client.drive_operation("sms_calendar.get", {"messageId": message_id})
            return receipt(
                "text", True,
                operation="sms_calendar.get",
                readOnly=True,
                rawMessageBodyExposed=False,
                authoritativeUnreadState=False,
                authoritativeProviderThreadId=False,
                outboundAuthority=False,
                response=_text_result(value),
            )
        return receipt("text", False, error="unsupported_text_command", usage="TEXT: recent [1..50] | get <sms_id>")
    except HomeCenterError as exc:
        return receipt("text", False, error="home_center_text_read_failed", detail=tail(str(exc), 1500))
    except Exception as exc:
        return receipt("text", False, error="text_read_failed", detail=tail(f"{type(exc).__name__}: {exc}", 1500))


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


def run_mode(mode: str, text: str, cwd: str, timeout: int) -> int:
    if mode not in ONE_SHOT_MODES:
        return receipt(mode, False, error="unsupported_mode")
    if mode == "terminal":
        return run_terminal(text, cwd, timeout)
    if mode == "text":
        return run_text(text, cwd, timeout)
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
