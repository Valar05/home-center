#!/usr/bin/env python3
"""Deterministic, read-only context organs for the Fortress phone daemon.

Raw adapters may refresh Library and ChatGPT/scheduler snapshots. This module
normalizes them, fingerprints only meaningful state, and emits a durable,
one-shot scheduler wake request when local evidence says the ChatGPT actuator
needs to observe or repair state.

Sensors never mutate ChatGPT, Library, scheduler tasks, or project state.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

STATE_DIR = Path(os.environ.get("HC_SWARM_STATE_DIR", "~/.local/state/home-center/vlad-swarm")).expanduser()
CONTEXT_DIR = Path(os.environ.get("HC_CONTEXT_SENSOR_DIR", str(STATE_DIR / "context"))).expanduser()
LIBRARY_SNAPSHOT = Path(os.environ.get("HC_LIBRARY_SENSOR_SNAPSHOT", str(CONTEXT_DIR / "library.snapshot.json"))).expanduser()
SHELL_SNAPSHOT = Path(os.environ.get("HC_CHATGPT_SHELL_SENSOR_SNAPSHOT", str(CONTEXT_DIR / "chatgpt-shell.snapshot.json"))).expanduser()
LIBRARY_CMD = os.environ.get("HC_LIBRARY_SENSOR_CMD", "").strip()
SHELL_CMD = os.environ.get("HC_CHATGPT_SHELL_SENSOR_CMD", "").strip()
STALE_SECONDS = int(os.environ.get("HC_CHATGPT_WORKER_STALE_SECONDS", "900"))
MAX_BYTES = int(os.environ.get("HC_CONTEXT_SENSOR_MAX_BYTES", "524288"))


def now() -> int:
    return int(time.time())


def stable_digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n")


def read_json(path: Path) -> dict[str, Any]:
    try:
        if not path.is_file() or path.stat().st_size > MAX_BYTES:
            return {}
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def refresh_snapshot(command: str, destination: Path, source: str) -> dict[str, Any]:
    if not command:
        return {"attempted": False, "source": source}
    try:
        process = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=30)
        if process.returncode != 0:
            return {
                "attempted": True,
                "ok": False,
                "source": source,
                "rc": process.returncode,
                "stderr": process.stderr[-2000:],
            }
        payload = json.loads(process.stdout)
        if not isinstance(payload, dict):
            raise ValueError("sensor command must emit one JSON object")
        payload.setdefault("observedAtEpoch", now())
        payload.setdefault("source", source)
        atomic_json(destination, payload)
        return {"attempted": True, "ok": True, "source": source, "path": str(destination)}
    except Exception as exc:
        return {"attempted": True, "ok": False, "source": source, "error": f"{type(exc).__name__}: {exc}"}


def normalize_library(raw: dict[str, Any]) -> dict[str, Any]:
    bootstrap = raw.get("bootstrap") or raw.get("fortressBootstrap") or {}
    index = raw.get("index") or raw.get("libraryIndex") or {}
    campaigns = raw.get("activeCampaigns") or raw.get("campaigns") or []
    outboxes = raw.get("pendingOutboxes") or raw.get("outboxes") or []
    return {
        "available": bool(raw),
        "observedAtEpoch": int(raw.get("observedAtEpoch") or raw.get("at") or 0),
        "bootstrap": bootstrap,
        "index": index,
        "activeCampaigns": campaigns,
        "pendingOutboxes": outboxes,
        "version": raw.get("version") or raw.get("cursor") or raw.get("revision"),
    }


def _worker_state(worker: dict[str, Any], current: int) -> dict[str, Any]:
    last = int(worker.get("lastRunEpoch") or worker.get("last_run_epoch") or 0)
    next_due = int(worker.get("nextDueEpoch") or worker.get("next_due_epoch") or 0)
    enabled = worker.get("enabled", True) is not False
    terminal = bool(worker.get("terminal") or worker.get("accepted") or worker.get("complete"))
    blocked = bool(worker.get("blocked"))
    stale = enabled and not terminal and (
        (last > 0 and current - last > STALE_SECONDS)
        or (last <= 0 and next_due > 0 and current > next_due + 60)
    )
    return {
        "id": worker.get("id") or worker.get("taskId") or worker.get("title"),
        "title": worker.get("title") or worker.get("name"),
        "enabled": enabled,
        "terminal": terminal,
        "blocked": blocked,
        "lastRunEpoch": last,
        "nextDueEpoch": next_due,
        "stale": stale,
        "lastResult": worker.get("lastResult") or worker.get("result") or worker.get("state"),
        "receipt": worker.get("receipt") or worker.get("lastReceipt"),
    }


def normalize_shell(raw: dict[str, Any], current: int) -> dict[str, Any]:
    workers_raw = raw.get("workers") or raw.get("tasks") or raw.get("automations") or []
    workers = [_worker_state(worker, current) for worker in workers_raw if isinstance(worker, dict)]
    return {
        "available": bool(raw),
        "observedAtEpoch": int(raw.get("observedAtEpoch") or raw.get("at") or 0),
        "surface": raw.get("surface") or "chatgpt",
        "session": raw.get("session") or raw.get("conversation"),
        "workers": workers,
        "staleWorkerIds": [worker["id"] for worker in workers if worker["stale"]],
        "blockedWorkerIds": [worker["id"] for worker in workers if worker["blocked"] and not worker["terminal"]],
        "pendingUserBoundary": raw.get("pendingUserBoundary"),
        "schedulerReachable": raw.get("schedulerReachable"),
        "actuatorReachable": raw.get("actuatorReachable"),
    }


def load_previous() -> dict[str, Any]:
    return read_json(CONTEXT_DIR / "normalized.json")


def meaningful_projection(context: dict[str, Any]) -> dict[str, Any]:
    """Drop observation clocks and due/run timestamps so polling itself is quiet."""
    library = dict(context["library"])
    library.pop("observedAtEpoch", None)

    shell = context["chatgptShell"]
    workers = []
    for worker in shell.get("workers", []):
        workers.append(
            {
                "id": worker.get("id"),
                "title": worker.get("title"),
                "enabled": worker.get("enabled"),
                "terminal": worker.get("terminal"),
                "blocked": worker.get("blocked"),
                "stale": worker.get("stale"),
                "lastResult": worker.get("lastResult"),
                "receipt": worker.get("receipt"),
            }
        )
    shell_projection = {
        "available": shell.get("available"),
        "surface": shell.get("surface"),
        "workers": workers,
        "staleWorkerIds": shell.get("staleWorkerIds", []),
        "blockedWorkerIds": shell.get("blockedWorkerIds", []),
        "pendingUserBoundary": shell.get("pendingUserBoundary"),
        "schedulerReachable": shell.get("schedulerReachable"),
        "actuatorReachable": shell.get("actuatorReachable"),
    }
    return {"library": library, "chatgptShell": shell_projection}


def _wake_reasons(library: dict[str, Any], shell: dict[str, Any], changed: bool, had_previous: bool) -> list[str]:
    reasons: list[str] = []
    if shell["staleWorkerIds"]:
        reasons.append("stale_workers")
    if shell["blockedWorkerIds"]:
        reasons.append("blocked_workers")
    if shell.get("pendingUserBoundary"):
        reasons.append("operator_boundary")
    if library.get("pendingOutboxes"):
        reasons.append("pending_outbox")
    if changed and had_previous:
        reasons.append("context_changed")
    return reasons


def sense() -> dict[str, Any]:
    CONTEXT_DIR.mkdir(parents=True, exist_ok=True)
    refresh = {
        "library": refresh_snapshot(LIBRARY_CMD, LIBRARY_SNAPSHOT, "library") if LIBRARY_CMD else {"attempted": False},
        "chatgptShell": refresh_snapshot(SHELL_CMD, SHELL_SNAPSHOT, "chatgpt-shell") if SHELL_CMD else {"attempted": False},
    }
    current = now()
    library = normalize_library(read_json(LIBRARY_SNAPSHOT))
    shell = normalize_shell(read_json(SHELL_SNAPSHOT), current)
    context = {
        "schema": "fortress.context-senses.v2",
        "observedAtEpoch": current,
        "library": library,
        "chatgptShell": shell,
        "refresh": refresh,
    }
    digest = stable_digest(meaningful_projection(context))
    previous = load_previous()
    previous_digest = previous.get("meaningfulDigest")
    changed = digest != previous_digest
    reasons = _wake_reasons(library, shell, changed, bool(previous_digest))

    wake_path = CONTEXT_DIR / "scheduler-wake-request.json"
    ledger_path = CONTEXT_DIR / "scheduler-wake-ledger.json"
    ledger = read_json(ledger_path)
    # context_changed is a transition marker, not a persistent condition. If a
    # stronger condition exists (stale/blocked/outbox/boundary), key the wake on
    # that condition so the next quiet poll cannot emit a second copy merely
    # because context_changed dropped out of the reason list.
    persistent_reasons = [reason for reason in reasons if reason != "context_changed"]
    key_reasons = persistent_reasons or reasons
    wake_key = stable_digest(
        {
            "meaningfulDigest": digest,
            "reasons": key_reasons,
            "staleWorkerIds": shell["staleWorkerIds"],
            "blockedWorkerIds": shell["blockedWorkerIds"],
        }
    ) if reasons else ""
    emitted = False
    if reasons and ledger.get("lastEmittedKey") != wake_key:
        wake = {
            "schema": "fortress.scheduler-wake.v2",
            "createdAtEpoch": current,
            "wakeKey": wake_key,
            "meaningfulDigest": digest,
            "reasons": reasons,
            "staleWorkerIds": shell["staleWorkerIds"],
            "blockedWorkerIds": shell["blockedWorkerIds"],
            "requestedAction": "observe_and_repair_scheduler_state",
            "authority": "chatgpt_scheduler_or_chromium_actuator_only",
            "consumeOnce": True,
        }
        atomic_json(wake_path, wake)
        atomic_json(
            ledger_path,
            {
                "schema": "fortress.scheduler-wake-ledger.v1",
                "lastEmittedAtEpoch": current,
                "lastEmittedKey": wake_key,
                "meaningfulDigest": digest,
                "reasons": key_reasons,
            },
        )
        append_jsonl(CONTEXT_DIR / "scheduler-wake-receipts.jsonl", wake)
        emitted = True

    context["meaningfulDigest"] = digest
    context["changed"] = changed
    context["wakeRequired"] = bool(reasons)
    context["wakeReasons"] = reasons
    context["wakeEmitted"] = emitted
    context["wakeKey"] = wake_key or None
    context["wakePending"] = wake_path.exists()
    atomic_json(CONTEXT_DIR / "normalized.json", context)
    return context


def main() -> int:
    parser = argparse.ArgumentParser(description="Fortress deterministic context sensory organs")
    parser.add_argument("--pretty", action="store_true")
    args = parser.parse_args()
    result = sense()
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
