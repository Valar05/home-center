#!/usr/bin/env python3
"""Deterministic, read-only context organs for the Fortress phone daemon.

The daemon must be able to decide whether ChatGPT needs waking without spending
inference or depending on an hourly poll.  Sensors are deliberately provider-
agnostic: a local/browser/Drive adapter may refresh the raw snapshots, while
this module normalizes them, fingerprints meaningful state, and emits a bounded
wake request only on change, staleness, or an explicit unresolved transition.

No sensor mutates ChatGPT, Library, scheduler tasks, or project state.
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
        p = subprocess.run(command, shell=True, text=True, capture_output=True, timeout=30)
        if p.returncode != 0:
            return {"attempted": True, "ok": False, "source": source, "rc": p.returncode, "stderr": p.stderr[-2000:]}
        payload = json.loads(p.stdout)
        if not isinstance(payload, dict):
            raise ValueError("sensor command must emit one JSON object")
        payload.setdefault("observedAtEpoch", now())
        payload.setdefault("source", source)
        atomic_json(destination, payload)
        return {"attempted": True, "ok": True, "source": source, "path": str(destination)}
    except Exception as exc:
        return {"attempted": True, "ok": False, "source": source, "error": f"{type(exc).__name__}: {exc}"}


def normalize_library(raw: dict[str, Any]) -> dict[str, Any]:
    # Expected adapters may provide richer fields.  Keep only state that matters
    # to resumption and avoid mirroring an entire Library corpus into daemon RAM.
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
    stale = enabled and not terminal and ((last > 0 and current - last > STALE_SECONDS) or (last <= 0 and next_due > 0 and current > next_due + 60))
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
    workers = [_worker_state(w, current) for w in workers_raw if isinstance(w, dict)]
    return {
        "available": bool(raw),
        "observedAtEpoch": int(raw.get("observedAtEpoch") or raw.get("at") or 0),
        "surface": raw.get("surface") or "chatgpt",
        "session": raw.get("session") or raw.get("conversation"),
        "workers": workers,
        "staleWorkerIds": [w["id"] for w in workers if w["stale"]],
        "blockedWorkerIds": [w["id"] for w in workers if w["blocked"] and not w["terminal"]],
        "pendingUserBoundary": raw.get("pendingUserBoundary"),
        "schedulerReachable": raw.get("schedulerReachable"),
        "actuatorReachable": raw.get("actuatorReachable"),
    }


def load_previous() -> dict[str, Any]:
    return read_json(CONTEXT_DIR / "normalized.json")


def meaningful_projection(context: dict[str, Any]) -> dict[str, Any]:
    """Exclude observation timestamps so unchanged polling stays silent."""
    lib = dict(context["library"])
    shell = dict(context["chatgptShell"])
    lib.pop("observedAtEpoch", None)
    shell.pop("observedAtEpoch", None)
    return {"library": lib, "chatgptShell": shell}


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
        "schema": "fortress.context-senses.v1",
        "observedAtEpoch": current,
        "library": library,
        "chatgptShell": shell,
        "refresh": refresh,
    }
    projection = meaningful_projection(context)
    digest = stable_digest(projection)
    previous = load_previous()
    previous_digest = previous.get("meaningfulDigest")
    changed = digest != previous_digest

    reasons: list[str] = []
    if shell["staleWorkerIds"]:
        reasons.append("stale_workers")
    if shell["blockedWorkerIds"]:
        reasons.append("blocked_workers")
    if shell.get("pendingUserBoundary"):
        reasons.append("operator_boundary")
    if library.get("pendingOutboxes"):
        reasons.append("pending_outbox")
    if changed and previous_digest:
        reasons.append("context_changed")

    context["meaningfulDigest"] = digest
    context["changed"] = changed
    context["wakeRequired"] = bool(reasons)
    context["wakeReasons"] = reasons
    atomic_json(CONTEXT_DIR / "normalized.json", context)

    wake_path = CONTEXT_DIR / "scheduler-wake-request.json"
    if reasons:
        wake = {
            "schema": "fortress.scheduler-wake.v1",
            "createdAtEpoch": current,
            "meaningfulDigest": digest,
            "reasons": reasons,
            "staleWorkerIds": shell["staleWorkerIds"],
            "blockedWorkerIds": shell["blockedWorkerIds"],
            "requestedAction": "observe_and_repair_scheduler_state",
            "consumeOnce": True,
        }
        atomic_json(wake_path, wake)
    elif wake_path.exists():
        wake_path.unlink()
    return context


def main() -> int:
    ap = argparse.ArgumentParser(description="Fortress deterministic context sensory organs")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args()
    result = sense()
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
