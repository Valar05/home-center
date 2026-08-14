#!/usr/bin/env python3
"""Deterministic, observation-only substance and self-care logger for Adam.

This records Drew's reports. It never recommends, schedules, converts, or
optimizes nicotine/cannabis use.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

LEDGER_TITLE = "ADAM — Substance and Self-Care Observation Ledger"
STATE_PATH = Path(os.environ.get(
    "HC_ADAM_OBSERVATION_STATE",
    "~/.local/state/home-center/adam/observation-events.json",
)).expanduser()
NUMBER_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20,
}
NUMBER = r"(?:\d{1,2}|" + "|".join(NUMBER_WORDS) + r")"


class ObservationError(ValueError):
    pass


def _number(value: str) -> int:
    value = value.lower()
    result = int(value) if value.isdigit() else NUMBER_WORDS[value]
    if not 0 <= result <= 20:
        raise ObservationError("reported count must be between 0 and 20")
    return result


def looks_like_observation(text: str) -> bool:
    lowered = " ".join(str(text or "").lower().split())
    return bool(re.search(
        r"\b(drop|drip|nicotine|vape|weed|cannabis|marijuana|puff|hit|dab|gummy|"
        r"hunger|craving|pills?|meds?|medication|shower|going to bed|went to bed|"
        r"no more nicotine)\b",
        lowered,
    ))


def parse_observation(text: str) -> dict[str, Any]:
    raw = str(text or "").strip()
    lowered = " ".join(raw.lower().split())
    if not lowered:
        raise ObservationError("empty observation")
    if re.search(r"\b(should i|can i|may i|how many|what dose|next dose)\b", lowered):
        raise ObservationError("prospective dosing requests are outside the observation ledger")

    if re.search(r"\bno more nicotine\b", lowered):
        return {"eventType": "commitment", "substance": "nicotine", "commitment": "no_more_tonight"}
    if re.search(r"\b(pills?|meds?|medication)\s+(taken|done)\b|\b(i|i've|ive)\s+(took|taken)\s+(my\s+)?(pills?|meds?|medication)\b", lowered):
        return {"eventType": "medication_adherence", "status": "confirmed_taken"}
    if re.search(r"\b(shower|showered)\b", lowered):
        return {"eventType": "self_care", "activity": "shower", "status": "complete"}
    if re.search(r"\b(going|headed|went)\s+to\s+bed\b|\bin bed\b", lowered):
        return {"eventType": "sleep_transition", "status": "bed"}

    craving = re.search(rf"\b(?:nicotine\s+)?(?:hunger|craving)(?:\s+(?:is|at))?\s+({NUMBER})\b", lowered)
    if craving:
        score = _number(craving.group(1))
        if score > 10:
            raise ObservationError("craving score must be between 0 and 10")
        return {"eventType": "craving", "substance": "nicotine", "score": score, "scaleMax": 10}

    drops = re.search(rf"\b({NUMBER})\s+(?:more\s+)?(drops?|drips?)\b", lowered)
    if drops:
        if not re.search(r"\b(log|record|took|taken|had|tasted|consumed|swallowed|more)\b", lowered):
            raise ObservationError("state that the drop event already happened or say log/record")
        return {
            "eventType": "substance_observation",
            "substance": "nicotine_e_liquid",
            "count": _number(drops.group(1)),
            "unit": "drop",
            "route": "oral_reported",
        }

    cannabis = re.search(rf"\b({NUMBER})\s+(puffs?|hits?|pulls?|dabs?|gummies?)\b", lowered)
    if cannabis and re.search(r"\b(weed|cannabis|marijuana|thc|edible|dab)\b", lowered):
        return {
            "eventType": "substance_observation",
            "substance": "cannabis",
            "count": _number(cannabis.group(1)),
            "unit": cannabis.group(2).rstrip("s"),
            "route": "as_reported",
        }
    if re.search(r"\b(weed|cannabis|marijuana|thc)\b", lowered) and re.search(r"\b(helped|worsened|made|caused|relieved)\b", lowered):
        return {"eventType": "effect_observation", "substance": "cannabis", "effect": raw}
    if re.search(r"\b(log|record|used|smoked|vaped|ate|had|took)\b", lowered) and re.search(r"\b(weed|cannabis|marijuana|thc|edible|dab)\b", lowered):
        return {"eventType": "substance_observation", "substance": "cannabis", "amount": "not_reported", "route": "as_reported"}
    raise ObservationError("no supported after-the-fact observation found")


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {"schema": "adam-observation-state-v1", "events": {}}
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"schema": "adam-observation-state-v1", "events": {}}
    return value if isinstance(value, dict) else {"schema": "adam-observation-state-v1", "events": {}}


def _save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATE_PATH.with_name(STATE_PATH.name + ".tmp")
    temp.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(temp, 0o600)
    os.replace(temp, STATE_PATH)


def _client():
    from home_center_mcp_client import HomeCenterMcp
    return HomeCenterMcp(timeout=60)


def _resolve_ledger(client) -> str:
    configured = os.environ.get("HC_ADAM_OBSERVATION_LEDGER_ID", "").strip()
    if configured:
        return configured
    value = client.call_tool("drive_search", {"query": LEDGER_TITLE, "limit": 10})
    for item in value.get("results") or []:
        if item.get("name") == LEDGER_TITLE and item.get("id"):
            return str(item["id"])
    raise RuntimeError(f"Home Center ledger not found: {LEDGER_TITLE}")


def _read_total(client, ledger_id: str) -> int | None:
    value = client.call_tool("drive_read", {"fileId": ledger_id, "exportFormat": "text/plain"})
    matches = re.findall(r"NICOTINE_SESSION_TOTAL_DROPS=(\d+)", str(value.get("text") or ""))
    return int(matches[-1]) if matches else None


def _append_event(client, event: dict[str, Any]) -> dict[str, Any]:
    return client.call_tool("docs_append", {
        "documentId": event["ledgerId"],
        "heading": event["heading"],
        "text": event["body"],
        "callerNote": "Adam observation-only natural-language event",
        "requestId": event["requestId"],
    })


def record(text: str, event_id: str = "") -> dict[str, Any]:
    parsed = parse_observation(text)
    event_id = (event_id or os.environ.get("HC_COMMAND_ID") or os.environ.get("ADAM_EVENT_ID") or uuid.uuid4().hex).strip()
    safe_id = re.sub(r"[^A-Za-z0-9_.-]", "-", event_id)[:100]
    state = _load_state()
    events = state.setdefault("events", {})
    if safe_id in events and events[safe_id].get("status") == "synced":
        return {**events[safe_id]["receipt"], "idempotent": True}

    client = _client()
    ledger_id = _resolve_ledger(client)
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    next_total = None
    if parsed.get("substance") == "nicotine_e_liquid":
        current = _read_total(client, ledger_id)
        if current is not None:
            next_total = current + int(parsed["count"])
    payload = {
        "schema": "adam-observation-event-v1",
        "eventId": safe_id,
        "observedAtUtc": now,
        "raw": text,
        **parsed,
    }
    lines = [
        "```json", json.dumps(payload, ensure_ascii=False, sort_keys=True), "```",
        "Observation only; not a dose recommendation, target, conversion, or experiment instruction.",
    ]
    if next_total is not None:
        lines.append(f"NICOTINE_SESSION_TOTAL_DROPS={next_total}")
    pending = {
        "status": "pending",
        "ledgerId": ledger_id,
        "requestId": f"adam-observation-{safe_id}",
        "heading": f"ADAM OBSERVATION — {now}",
        "body": "\n".join(lines),
        "payload": payload,
    }
    events[safe_id] = pending
    _save_state(state)
    result = _append_event(client, pending)
    receipt = {
        "schema": "adam-observation-receipt-v1",
        "ok": True,
        "eventId": safe_id,
        "eventType": parsed["eventType"],
        "substance": parsed.get("substance"),
        "reportedCount": parsed.get("count"),
        "reportedUnit": parsed.get("unit"),
        "nicotineSessionTotalDrops": next_total,
        "ledgerId": ledger_id,
        "auditRequestId": result.get("auditRequestId") or pending["requestId"],
        "rawPreserved": True,
        "observationOnly": True,
    }
    events[safe_id] = {**pending, "status": "synced", "receipt": receipt}
    _save_state(state)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(prog="adam-observe")
    parser.add_argument("text", nargs="?", default="")
    parser.add_argument("--event-id", default="")
    args = parser.parse_args()
    raw = args.text or os.sys.stdin.read()
    try:
        value = record(raw, args.event_id)
    except Exception as exc:
        value = {"schema": "adam-observation-receipt-v1", "ok": False, "error": type(exc).__name__, "detail": str(exc)[:1000]}
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0 if value.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
