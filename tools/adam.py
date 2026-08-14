#!/usr/bin/env python3
"""Adam body router for Home Center.

Bare `adam` is installed to tools/adam_planned_venice.py. The Android Beard exposes
one natural-language input. This deterministic router preserves Drew's exact text,
selects the existing bounded lane, defaults to local/included execution, and never
selects arbitrary shell execution from natural language. RADIO remains deterministic.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "tools" / "adam_planned_venice.py"
RADIO_SOURCE = ROOT / "tools" / "spotify_radio.py"
RADIO_INSTALLED = Path(os.environ.get("HC_SPOTIFY_RADIO_BIN", "~/bin/spotify-radio")).expanduser()
ONE_SHOT_MODES = ("auto", "terminal", "text", "chat", "continue", "vlad", "radio")
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


def classify_mode(text: str) -> tuple[str, str]:
    """Deterministic Beard routing. Raw text is preserved; classification grants no new authority."""
    lowered = " ".join(str(text or "").lower().split())
    if re.search(r"\b(vlad|second opinion|independent critique)\b", lowered):
        return "vlad", "explicit_second_opinion"
    if re.search(r"\b(spotify|radio|playlist|play music|music for)\b", lowered):
        return "radio", "bounded_music_intent"
    if re.search(r"\b(recent texts?|text messages?|sms|message inbox)\b", lowered):
        return "text", "bounded_read_only_text_intent"
    # Drew's correction is literal: this phrase means stop silence and keep hunting.
    if "quit silent hunt" in lowered:
        return "continue", "quit_silent_hunt_means_continue"
    if re.search(r"\b(continue|advance|keep working|wire|build|make|fix|repair|implement|deploy|test|run|finish|ship)\b", lowered):
        return "continue", "work_bearing_intent"
    return "chat", "general_cognition"


def worker_commission(mode: str, text: str) -> str:
    policy = (
        "Beard contract: preserve Drew's exact raw words beside every interpretation; "
        "uncensored language is the default; explicit sexual content appears only by Drew's request; "
        "no paid provider or new credit spend without explicit authorization; "
        "do not infer permission to quit, cancel, or stop the mission; 'quit Silent Hunt' means "
        "stop being silent and continue hunting. "
    )
    if mode == "chat":
        return policy + f"Conversational request from Drew. Research any material unknowns, make a bounded plan, select relevant Judgment Jars, antagonize the plan, obtain Venice PLAN_ALLOWED, then respond usefully. Do not execute unless Drew's text clearly requests action. Drew said: {text}"
    if mode == "continue":
        return policy + f"Coding/work commission from Drew. Research repository truth, plan, select relevant Judgment Jars, antagonize, obtain Venice PLAN_ALLOWED, then work Codex-style, validate, and return exact evidence after Venice completion/code review. Commission: {text}"
    if mode == "vlad":
        return policy + f"Drew explicitly requests an independent critical second opinion in Vlad's role. Research material unknowns, plan the bounded analysis, select relevant Judgment Jars, antagonize assumptions, obtain Venice PLAN_ALLOWED, then return a concise governed response. Question: {text}"
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
    if mode == "auto":
        mode, _reason = classify_mode(text)
    if mode == "terminal":
        return run_terminal(text, cwd, timeout)
    if mode == "text":
        return run_text(text, cwd, timeout)
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
