#!/usr/bin/env python3
"""Deterministic Android text-message inbox organ for Adam.

Read-only by design. Uses the existing Shizuku/rish body lane through
android_phone_hands_bridge. Home Center/Adam may inspect and orchestrate inbox
state, but sending a message is intentionally not implemented here; outbound
communication remains an explicit operator-authorized mutation.
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

from android_phone_hands_bridge import run_rish

DEFAULT_LIMIT = 40
MAX_LIMIT = 200
PROJECTION = "_id:thread_id:address:date:date_sent:read:type:body"
ROW_RE = re.compile(r"^Row:\s*\d+\s+(.*)$")
FIELD_RE = re.compile(r"(?:^|,\s)([A-Za-z_][A-Za-z0-9_]*)=")


@dataclass
class TextMessage:
    id: str
    threadId: str
    address: str
    dateMs: int | None
    dateSentMs: int | None
    read: bool | None
    type: int | None
    body: str

    @property
    def direction(self) -> str:
        # Android Telephony.TextBasedSmsColumns: 1=inbox, 2=sent.
        if self.type == 1:
            return "incoming"
        if self.type == 2:
            return "outgoing"
        return "other"

    def to_dict(self) -> dict[str, Any]:
        obj = asdict(self)
        obj["direction"] = self.direction
        if self.dateMs is not None:
            try:
                obj["dateIso"] = datetime.fromtimestamp(self.dateMs / 1000, tz=timezone.utc).isoformat()
            except (OverflowError, OSError, ValueError):
                obj["dateIso"] = None
        else:
            obj["dateIso"] = None
        return obj


def _int_or_none(value: str | None) -> int | None:
    if value is None or value in {"NULL", "null", ""}:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _bool_or_none(value: str | None) -> bool | None:
    parsed = _int_or_none(value)
    return None if parsed is None else parsed != 0


def parse_content_rows(raw: str) -> list[TextMessage]:
    """Parse Android `content query` rows without breaking on commas in body."""
    messages: list[TextMessage] = []
    for line in str(raw or "").splitlines():
        m = ROW_RE.match(line.strip())
        if not m:
            continue
        payload = m.group(1)
        matches = list(FIELD_RE.finditer(payload))
        fields: dict[str, str] = {}
        for idx, match in enumerate(matches):
            start = match.end()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(payload)
            fields[match.group(1)] = payload[start:end]
        messages.append(TextMessage(
            id=fields.get("_id", ""),
            threadId=fields.get("thread_id", ""),
            address=fields.get("address", ""),
            dateMs=_int_or_none(fields.get("date")),
            dateSentMs=_int_or_none(fields.get("date_sent")),
            read=_bool_or_none(fields.get("read")),
            type=_int_or_none(fields.get("type")),
            body=fields.get("body", ""),
        ))
    messages.sort(key=lambda msg: msg.dateMs or 0, reverse=True)
    return messages


def _query_uri(uri: str = "content://sms") -> list[TextMessage]:
    cmd = f"content query --uri {shlex.quote(uri)} --projection {shlex.quote(PROJECTION)}"
    raw = str(run_rish(cmd, timeout=20))
    return parse_content_rows(raw)


def status() -> dict[str, Any]:
    try:
        rows = _query_uri("content://sms/inbox")
        return {
            "schema": "home-center.text-inbox.v1",
            "ok": True,
            "mode": "read_only",
            "backend": "android-content-provider-via-shizuku-rish",
            "readable": True,
            "sampleCount": min(len(rows), 1),
            "outboundAuthority": False,
        }
    except Exception as exc:
        return {
            "schema": "home-center.text-inbox.v1",
            "ok": False,
            "mode": "read_only",
            "backend": "android-content-provider-via-shizuku-rish",
            "readable": False,
            "error": str(exc),
            "outboundAuthority": False,
        }


def query(*, limit: int = DEFAULT_LIMIT, unread: bool = False, search: str = "", address: str = "", thread_id: str = "") -> dict[str, Any]:
    limit = max(1, min(int(limit), MAX_LIMIT))
    try:
        rows = _query_uri("content://sms")
    except Exception as exc:
        return {
            "schema": "home-center.text-inbox.v1",
            "ok": False,
            "operation": "query",
            "error": str(exc),
            "messages": [],
        }

    q = search.casefold().strip()
    addr = address.casefold().strip()
    tid = thread_id.strip()
    filtered: list[TextMessage] = []
    for msg in rows:
        if unread and msg.read is not False:
            continue
        if addr and addr not in msg.address.casefold():
            continue
        if tid and msg.threadId != tid:
            continue
        if q and q not in msg.body.casefold() and q not in msg.address.casefold():
            continue
        filtered.append(msg)
        if len(filtered) >= limit:
            break

    return {
        "schema": "home-center.text-inbox.v1",
        "ok": True,
        "operation": "query",
        "readOnly": True,
        "count": len(filtered),
        "messages": [msg.to_dict() for msg in filtered],
    }


def execute_tool(obj: dict[str, Any]) -> dict[str, Any]:
    op = str(obj.get("op") or "list").strip().lower()
    if op == "status":
        return status()
    if op in {"list", "unread", "search", "thread"}:
        return query(
            limit=int(obj.get("limit", DEFAULT_LIMIT)),
            unread=op == "unread" or bool(obj.get("unread")),
            search=str(obj.get("query") or "") if op == "search" else str(obj.get("search") or ""),
            address=str(obj.get("address") or ""),
            thread_id=str(obj.get("threadId") or "") if op == "thread" else str(obj.get("threadId") or ""),
        )
    return {
        "schema": "home-center.text-inbox.v1",
        "ok": False,
        "error": f"unsupported operation: {op}",
        "allowed": ["status", "list", "unread", "search", "thread"],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="adam-texts", description="Read-only Adam text-message inbox organ")
    sub = parser.add_subparsers(dest="op", required=True)
    sub.add_parser("status")
    for name in ("list", "unread"):
        p = sub.add_parser(name)
        p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
        p.add_argument("--address", default="")
    p = sub.add_parser("search")
    p.add_argument("query")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    p.add_argument("--address", default="")
    p = sub.add_parser("thread")
    p.add_argument("thread_id")
    p.add_argument("--limit", type=int, default=DEFAULT_LIMIT)

    args = parser.parse_args(argv)
    obj: dict[str, Any] = {"op": args.op}
    if hasattr(args, "limit"):
        obj["limit"] = args.limit
    if hasattr(args, "address"):
        obj["address"] = args.address
    if args.op == "search":
        obj["query"] = args.query
    if args.op == "thread":
        obj["threadId"] = args.thread_id
    result = execute_tool(obj)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
