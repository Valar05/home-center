#!/usr/bin/env python3
"""Crash-resumable, honesty-first Inner Fortress session aperture.

This module owns continuity and routing only.  It never authors a Character,
Venice, Regnet, or Judgment Jar response.  Until an authoritative cognition
adapter is present, story, critique, and direction turns are explicitly labeled
as ChatGPT rehearsal envelopes.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable

SCHEMA = "adam.inner-fortress.state.v1"
RECEIPT_SCHEMA = "adam.inner-fortress.turn.v1"
INVOKE = "Inner Fortress"
STATE_PATH = Path(os.environ.get(
    "HC_INNER_FORTRESS_STATE",
    "~/.local/state/home-center/adam/inner-fortress/state.json",
)).expanduser()
OBSERVATION_SOURCE = Path(__file__).resolve().with_name("adam_observation_ledger.py")


def _utc_ms() -> int:
    return int(time.time() * 1000)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _empty_state() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "revision": 0,
        "activeSession": None,
        "events": [],
        "requests": {},
    }


class StateCorrupt(RuntimeError):
    pass


def _load_observation_module():
    if not OBSERVATION_SOURCE.is_file():
        return None
    spec = importlib.util.spec_from_file_location("adam_observation_ledger", OBSERVATION_SOURCE)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _observation_detector(text: str) -> bool:
    module = _load_observation_module()
    if module is None:
        return False
    try:
        module.parse_observation(text)
        return True
    except module.ObservationError:
        return False


def _observation_recorder(text: str, request_id: str) -> dict[str, Any]:
    module = _load_observation_module()
    if module is None:
        raise RuntimeError("adam_observation_ledger.py is unavailable")
    return module.record(text, request_id)


class SessionStore:
    """One lock plus atomic replace keeps the active turn crash-resumable."""

    def __init__(self, path: Path = STATE_PATH):
        self.path = Path(path).expanduser()
        self.lock_path = self.path.with_suffix(self.path.suffix + ".lock")

    def transact(
        self,
        update: Callable[[dict[str, Any]], tuple[dict[str, Any], bool]],
    ) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            os.chmod(self.lock_path, 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
            state = self._read()
            result, changed = update(state)
            if changed:
                state["revision"] = int(state.get("revision") or 0) + 1
                self._write(state)
            return result

    def read(self) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.lock_path.open("a+", encoding="utf-8") as lock:
            os.chmod(self.lock_path, 0o600)
            fcntl.flock(lock.fileno(), fcntl.LOCK_SH)
            return self._read()

    def _read(self) -> dict[str, Any]:
        if not self.path.is_file():
            return _empty_state()
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StateCorrupt(f"Inner Fortress state is unreadable: {exc}") from exc
        if not isinstance(value, dict) or value.get("schema") != SCHEMA:
            raise StateCorrupt("Inner Fortress state schema is invalid")
        if not isinstance(value.get("events"), list):
            raise StateCorrupt("Inner Fortress events are invalid")
        if not isinstance(value.get("requests", {}), dict):
            raise StateCorrupt("Inner Fortress request index is invalid")
        value.setdefault("requests", {})
        return value

    def _write(self, state: dict[str, Any]) -> None:
        temp = self.path.with_name(self.path.name + f".{os.getpid()}.tmp")
        with temp.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp, 0o600)
        os.replace(temp, self.path)
        directory_fd = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)


def _turn_kind(raw: str) -> str:
    normalized = " ".join(raw.lower().split())
    if normalized.rstrip(".!?") == "story":
        return "STORY_CONTINUE"
    if normalized.rstrip(".!?") == "critique that":
        return "CRITIQUE"
    if (raw.lstrip().startswith("[") or re.match(
        r"^(stage|direction|direct|camera|lighting|tone|scene|she-ra)\b", normalized
    )):
        return "STAGE_DIRECTION"
    return "DIALOGUE"


def _is_stage_direction(raw: str) -> bool:
    return _turn_kind(raw) == "STAGE_DIRECTION"


def should_intercept(
    text: str,
    *,
    store: SessionStore | None = None,
    observation_detector: Callable[[str], bool] = _observation_detector,
) -> bool:
    """Tell Adam whether CHAT belongs to this aperture without mutating state."""
    raw = str(text if text is not None else "")
    command = raw.strip()
    if not command:
        return False
    if command == INVOKE or _is_stage_direction(command):
        if command == INVOKE:
            return True
    if observation_detector(raw):
        return True
    try:
        active = (store or SessionStore()).read().get("activeSession")
    except StateCorrupt:
        # Intercept so the caller receives the fail-closed state receipt instead
        # of silently falling through to a different cognition surface.
        return True
    return isinstance(active, dict)


def handle_turn(
    text: str,
    *,
    store: SessionStore | None = None,
    observation_detector: Callable[[str], bool] = _observation_detector,
    observation_recorder: Callable[[str, str], dict[str, Any]] = _observation_recorder,
    request_id: str = "",
) -> dict[str, Any]:
    raw = str(text if text is not None else "")
    command = raw.strip()
    store = store or SessionStore()
    request_id = str(
        request_id
        or os.environ.get("HC_COMMAND_ID")
        or os.environ.get("ADAM_EVENT_ID")
        or uuid.uuid4().hex
    ).strip()
    request_digest = _sha(f"{RECEIPT_SCHEMA}\0{raw}")
    if not command:
        return {"schema": RECEIPT_SCHEMA, "ok": False, "state": "REJECTED", "error": "empty_utterance"}

    # An explicit stage direction outranks health keywords inside its fiction.
    # Only successfully parsed after-the-fact facts enter the real ledger.
    if not _is_stage_direction(command) and observation_detector(raw):
        try:
            observation = observation_recorder(raw, request_id)
        except Exception as exc:
            return {
                "schema": RECEIPT_SCHEMA,
                "ok": False,
                "state": "OBSERVATION_LEDGER_BLOCKED",
                "route": "OBSERVATION_LEDGER",
                "requestId": request_id,
                "raw": raw,
                "rawSha256": _sha(raw),
                "error": type(exc).__name__,
                "detail": str(exc)[:1000],
            }
        return {
            "schema": RECEIPT_SCHEMA,
            "ok": bool(observation.get("ok")),
            "state": "OBSERVATION_RECORDED" if observation.get("ok") else "OBSERVATION_LEDGER_BLOCKED",
            "route": "OBSERVATION_LEDGER",
            "requestId": request_id,
            "raw": raw,
            "rawSha256": _sha(raw),
            "observation": observation,
        }

    now = _utc_ms()

    def update(state: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        requests = state.setdefault("requests", {})
        prior = requests.get(request_id)
        if isinstance(prior, dict):
            if prior.get("requestDigest") != request_digest:
                return ({
                    "schema": RECEIPT_SCHEMA,
                    "ok": False,
                    "state": "IDEMPOTENCY_CONFLICT",
                    "requestId": request_id,
                    "requestDigest": request_digest,
                    "priorRequestDigest": prior.get("requestDigest"),
                }, False)
            replay = dict(prior.get("receipt") or {})
            replay["idempotent"] = True
            return replay, False

        active = state.get("activeSession") if isinstance(state.get("activeSession"), dict) else None
        if command == INVOKE:
            if active is None:
                active = {
                    "sessionId": f"inner-fortress-{uuid.uuid4().hex}",
                    "openedAtMs": now,
                    "mode": "CHATGPT_REHEARSAL",
                    "authorityState": "AUTHORITATIVE_CHARACTER_AND_JAR_ADAPTER_UNAVAILABLE",
                    "sequence": 0,
                }
                state["activeSession"] = active
            kind = "INVOKE"
        elif command.lower().rstrip(".!?") == "exit inner fortress":
            if active is None:
                return ({
                    "schema": RECEIPT_SCHEMA,
                    "ok": False,
                    "state": "INACTIVE",
                    "error": "no_active_session",
                    "requestId": request_id,
                }, False)
            kind = "CLOSE"
        elif active is None:
            return ({
                "schema": RECEIPT_SCHEMA,
                "ok": False,
                "state": "INACTIVE",
                "error": "invoke_required",
                "invoke": INVOKE,
                "requestId": request_id,
            }, False)
        else:
            kind = _turn_kind(command)

        active = state.get("activeSession")
        if not isinstance(active, dict):
            raise RuntimeError("active session vanished during transaction")
        active["sequence"] = int(active.get("sequence") or 0) + 1
        event = {
            "eventId": f"if-{_sha(request_id)[:24]}",
            "requestId": request_id,
            "requestDigest": request_digest,
            "sessionId": active["sessionId"],
            "sequence": active["sequence"],
            "occurredAtMs": now,
            "kind": kind,
            "raw": raw,
            "rawSha256": _sha(raw),
            "authority": "CHATGPT_REHEARSAL_ONLY",
        }
        state.setdefault("events", []).append(event)
        state["events"] = state["events"][-500:]

        if kind == "CLOSE":
            state["activeSession"] = None
            receipt = {"schema": RECEIPT_SCHEMA, "ok": True, "state": "CLOSED", **event}
            requests[request_id] = {"requestDigest": request_digest, "receipt": receipt}
            return receipt, True
        if kind == "INVOKE":
            response = (
                "CHATGPT REHEARSAL OF SHE-RA — Inner Fortress is open. This is a "
                "performance, not the authoritative She-Ra Character or a Judgment Jar ruling."
            )
            state_name = "ACTIVE_REHEARSAL"
        else:
            response = (
                "CHATGPT REHEARSAL — turn captured in the active Inner Fortress session; "
                "authoritative cognition is still required to answer it."
            )
            state_name = "WAITING_CHATGPT_REHEARSAL"
        receipt = {
            "schema": RECEIPT_SCHEMA,
            "ok": True,
            "state": state_name,
            "route": kind,
            "response": response,
            "requiresCognition": kind != "INVOKE",
            "authoritativeCharacter": False,
            "judgmentJarApplied": False,
            **event,
        }
        if kind != "INVOKE":
            receipt["cognitionEnvelope"] = {
                "schema": "adam.inner-fortress.cognition-request.v1",
                "operation": "codex_rehearsal.turn",
                "requestId": request_id,
                "sessionId": active["sessionId"],
                "sequence": active["sequence"],
                "turnKind": kind,
                "exactInput": raw,
                "exactInputSha256": _sha(raw),
                "requestedPerformance": "She-Ra",
                "performanceLabel": "CHATGPT_REHEARSAL_OF_SHE_RA",
                "authoritativeCharacter": False,
                "forbiddenClaims": [
                    "AUTHORITATIVE_SHE_RA_CHARACTER",
                    "SHE_RAW_IDENTITY_OR_LINEAGE",
                    "VENICE_OR_REGNET_REVIEW",
                    "JUDGMENT_JAR_RULING",
                ],
                "context": [dict(item) for item in state["events"][-40:]],
                "resultSchema": "adam.inner-fortress.cognition-result.v1",
            }
        requests[request_id] = {"requestDigest": request_digest, "receipt": receipt}
        if len(requests) > 500:
            keep_ids = {item.get("requestId") for item in state["events"][-500:]}
            state["requests"] = {key: value for key, value in requests.items() if key in keep_ids}
        return receipt, True

    try:
        return store.transact(update)
    except StateCorrupt as exc:
        return {
            "schema": RECEIPT_SCHEMA,
            "ok": False,
            "state": "STATE_BLOCKED",
            "requestId": request_id,
            "error": "state_corrupt",
            "detail": str(exc),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="adam-inner-fortress")
    parser.add_argument("text", nargs="?", default="")
    parser.add_argument("--state", default=str(STATE_PATH))
    parser.add_argument("--request-id", default="")
    args = parser.parse_args(argv)
    raw = args.text or sys.stdin.read()
    result = handle_turn(raw, store=SessionStore(Path(args.state)), request_id=args.request_id)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
