#!/usr/bin/env python3
"""Record only after-the-fact substance and self-care observations.

The exact utterance is retained.  Questions, plans, imperatives, fictional stage
directions, and negated events are outside this ledger.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any

LEDGER_ID = os.environ.get(
    "HC_ADAM_OBSERVATION_LEDGER_ID",
    "1XZGYIp8CSXY1bviKmXvleli3GNxYv-BatRJxfj0SEJo",
).strip()
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


class ObservationStateError(RuntimeError):
    pass


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _number(value: str) -> int:
    lowered = value.lower()
    result = int(lowered) if lowered.isdigit() else NUMBER_WORDS[lowered]
    if not 0 <= result <= 20:
        raise ObservationError("reported count must be between 0 and 20")
    return result


def parse_observation(text: str) -> dict[str, Any]:
    raw = str(text if text is not None else "")
    lowered = " ".join(raw.lower().split())
    if not lowered:
        raise ObservationError("empty observation")
    if re.match(r"^(stage|direction|direct|camera|scene|she-ra)\b", lowered):
        raise ObservationError("fictional direction is outside the real observation ledger")
    if re.search(r"\b(in the story|in this scene|the character|she says|he says)\b", lowered):
        raise ObservationError("fictional narration is outside the real observation ledger")
    if re.search(
        r"\b(should i|can i|may i|shall i|how many|what dose|next dose|"
        r"take next|use next|plan to (?:take|use)|want to (?:take|use)|"
        r"going to (?:take|use|smoke|vape|eat|have))\b",
        lowered,
    ):
        raise ObservationError("prospective dosing requests are outside the observation ledger")
    if "no more nicotine" not in lowered and re.search(
        r"\b(did not|didn't|have not|haven't|never|do not|don't|not taken|not done)\b",
        lowered,
    ):
        raise ObservationError("negated events are not recorded as completed observations")

    if re.search(r"\bno more nicotine(?:\s+tonight)?\b", lowered):
        return {"eventType": "commitment", "substance": "nicotine", "commitment": "no_more_tonight"}
    if re.search(
        r"\b(pills?|meds?|medication)\s+(?:are\s+)?(taken|done)\b|"
        r"\bi\s+(?:took|have taken)\s+(?:my\s+)?(?:pills?|meds?|medication)\b|"
        r"\b(?:i've|ive)\s+taken\s+(?:my\s+)?(?:pills?|meds?|medication)\b",
        lowered,
    ):
        return {"eventType": "medication_adherence", "status": "confirmed_taken"}
    if re.search(
        r"\bshowered\b|\b(?:i\s+)?(?:already\s+)?took (?:my|a) shower\b|"
        r"\b(?:i\s+have\s+)?already taken a shower\b|"
        r"\b(?:my\s+)?shower (?:is\s+)?(?:complete|done)\b",
        lowered,
    ):
        return {"eventType": "self_care", "activity": "shower", "status": "complete"}
    if re.search(r"\b(going|headed|went)\s+to\s+bed\b|\bin bed\b", lowered):
        return {"eventType": "sleep_transition", "status": "bed"}

    craving = re.search(
        rf"\b(?:nicotine\s+)?(?:hunger|craving)(?:\s+(?:is|at))?\s+({NUMBER})\b",
        lowered,
    )
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
            "route": "as_reported",
        }

    cannabis = re.search(rf"\b({NUMBER})\s+(puffs?|hits?|pulls?|dabs?|gummies?)\b", lowered)
    cannabis_token = re.search(r"\b(weed|cannabis|marijuana|thc|edible|dab)\b", lowered)
    if cannabis and cannabis_token and re.search(r"\b(log|record|used|smoked|vaped|ate|had|took)\b", lowered):
        return {
            "eventType": "substance_observation",
            "substance": "cannabis",
            "count": _number(cannabis.group(1)),
            "unit": cannabis.group(2).rstrip("s"),
            "route": "as_reported",
        }
    if cannabis_token and re.search(r"\b(helped|worsened|made|caused|relieved)\b", lowered):
        return {"eventType": "effect_observation", "substance": "cannabis", "effect": raw}
    if cannabis_token and re.search(r"\b(log|record|used|smoked|vaped|ate|had|took)\b", lowered):
        return {"eventType": "substance_observation", "substance": "cannabis", "amount": "not_reported", "route": "as_reported"}
    raise ObservationError("no supported after-the-fact observation found")


def looks_like_observation(text: str) -> bool:
    try:
        parse_observation(text)
        return True
    except ObservationError:
        return False


def _load_state() -> dict[str, Any]:
    if not STATE_PATH.is_file():
        return {"schema": "adam-observation-state-v2", "events": {}}
    try:
        value = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObservationStateError(f"observation state is unreadable: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema") != "adam-observation-state-v2":
        raise ObservationStateError("observation state schema is invalid")
    if not isinstance(value.get("events"), dict):
        raise ObservationStateError("observation event index is invalid")
    return value


def _save_state(state: dict[str, Any]) -> None:
    temp = STATE_PATH.with_name(STATE_PATH.name + f".{os.getpid()}.tmp")
    with temp.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.chmod(temp, 0o600)
    os.replace(temp, STATE_PATH)


def _client():
    from home_center_mcp_client import HomeCenterMcp
    return HomeCenterMcp(timeout=60)


def _append(client, pending: dict[str, Any]) -> dict[str, Any]:
    return client.call_tool("docs_append", {
        "documentId": LEDGER_ID,
        "heading": pending["heading"],
        "text": pending["body"],
        "callerNote": "Adam observation-only natural-language event",
        "requestId": pending["appendRequestId"],
    })


def record(text: str, event_id: str = "") -> dict[str, Any]:
    raw = str(text if text is not None else "")
    parsed = parse_observation(raw)
    event_id = str(
        event_id or os.environ.get("HC_COMMAND_ID") or os.environ.get("ADAM_EVENT_ID") or uuid.uuid4().hex
    ).strip()
    if not event_id:
        raise ObservationError("event id is empty")
    digest = _sha("adam-observation-v2\0" + raw)
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_path = STATE_PATH.with_suffix(STATE_PATH.suffix + ".lock")
    with lock_path.open("a+", encoding="utf-8") as lock:
        os.chmod(lock_path, 0o600)
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        state = _load_state()
        prior = state["events"].get(event_id)
        if isinstance(prior, dict):
            if prior.get("digest") != digest:
                raise ObservationError("event id was already used for different exact input")
            if prior.get("status") == "synced":
                return {**prior["receipt"], "idempotent": True}
            pending = prior
        else:
            occurred_at_ms = int(time.time() * 1000)
            payload = {
                "schema": "adam-observation-event-v2",
                "eventId": event_id,
                "observedAtMs": occurred_at_ms,
                "raw": raw,
                "rawSha256": _sha(raw),
                **parsed,
            }
            pending = {
                "status": "pending",
                "digest": digest,
                "appendRequestId": f"adam-observation-{_sha(event_id)[:32]}",
                "heading": f"ADAM OBSERVATION — {occurred_at_ms}",
                "body": "\n".join([
                    "```json", json.dumps(payload, ensure_ascii=False, sort_keys=True), "```",
                    "Observation only; not a recommendation, target, conversion, or experiment instruction.",
                ]),
                "payload": payload,
            }
            state["events"][event_id] = pending
            _save_state(state)

        result = _append(_client(), pending)
        receipt = {
            "schema": "adam-observation-receipt-v2",
            "ok": True,
            "eventId": event_id,
            "eventType": parsed["eventType"],
            "ledgerId": LEDGER_ID,
            "auditRequestId": result.get("auditRequestId") or pending["appendRequestId"],
            "rawPreserved": True,
            "rawSha256": _sha(raw),
            "observationOnly": True,
        }
        state["events"][event_id] = {**pending, "status": "synced", "receipt": receipt}
        _save_state(state)
        return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adam-observe")
    parser.add_argument("text", nargs="?", default="")
    parser.add_argument("--event-id", default="")
    args = parser.parse_args(argv)
    raw = args.text if args.text else sys.stdin.read()
    try:
        value = record(raw, args.event_id)
    except Exception as exc:
        value = {
            "schema": "adam-observation-receipt-v2", "ok": False,
            "error": type(exc).__name__, "detail": str(exc)[:1000],
        }
    print(json.dumps(value, ensure_ascii=False, sort_keys=True))
    return 0 if value.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
