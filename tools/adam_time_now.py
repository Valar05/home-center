#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "tools" / "adam_receipted_worker.py"
STATE_DIR = Path(os.path.expanduser(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center"))) / "time-now"
STATE = STATE_DIR / "current.json"
HISTORY = STATE_DIR / "history.jsonl"

# Seconds are intentionally aggressive. This organ exists to expose absurd latency.
LIMITS = {
    "TRIVIAL": (90, 180, 300, 480),
    "SMALL": (300, 600, 900, 1500),
    "MEDIUM": (900, 1800, 3000, 4800),
    "LARGE": (1800, 3600, 5400, 9000),
}

BEATS = (
    "She-Ra looks at the clock. Nothing else needs saying yet.",
    "Noodle Queen has begun timing each explanation with a kitchen timer she clearly hates.",
    "Ares enters, sees how long this has taken, and quietly removes the chair labeled PLANNING.",
    "TIME NOW: STOP EXPLAINING. EXECUTE THE SIMPLEST AUTHORIZED NEXT ACTION.",
)


def classify(argv: list[str]) -> str:
    forced = os.environ.get("HC_TIME_NOW_CLASS", "").strip().upper()
    if forced in LIMITS:
        return forced
    text = " ".join(argv).lower()
    if any(k in text for k in ("deploy", "android", "integration", "multi-file", "subsystem")):
        return "MEDIUM"
    if any(k in text for k in ("build", "test", "script", "implement", "fix", "add")):
        return "SMALL"
    return "TRIVIAL"


def atomic_write(obj: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(STATE)


def record(obj: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


def main(argv: list[str]) -> int:
    if not CORE.is_file():
        print(f"BLOCKED: Time Now organ cannot find core Adam worker: {CORE}", file=sys.stderr)
        return 2

    effort = classify(argv)
    started_wall = int(time.time())
    started_mono = time.monotonic()
    stop = threading.Event()
    tier_lock = threading.Lock()
    tier = {"value": 0}
    slice_text = " ".join(argv)[:4000] or "interactive Adam session"

    def snapshot(status: str, rc: int | None = None) -> dict:
        elapsed = max(0, int(time.monotonic() - started_mono))
        return {
            "schema": "adam-time-now-v1",
            "status": status,
            "slice": slice_text,
            "effortClass": effort,
            "startedAtEpoch": started_wall,
            "elapsedActiveSeconds": elapsed,
            "blockedSeconds": 0,
            "escalationTier": tier["value"],
            "lastMaterialTransition": "worker_started" if status == "running" else status,
            "pid": os.getpid(),
            "childReturnCode": rc,
        }

    atomic_write(snapshot("running"))

    def watchdog() -> None:
        thresholds = LIMITS[effort]
        while not stop.wait(1.0):
            elapsed = time.monotonic() - started_mono
            new_tier = sum(1 for t in thresholds if elapsed >= t)
            with tier_lock:
                if new_tier > tier["value"]:
                    for idx in range(tier["value"], new_tier):
                        print(f"\n[TIME NOW / TIER {idx + 1}] {BEATS[idx]}\n", file=sys.stderr, flush=True)
                    tier["value"] = new_tier
                atomic_write(snapshot("running"))

    thread = threading.Thread(target=watchdog, name="adam-time-now", daemon=True)
    thread.start()

    proc = subprocess.Popen([sys.executable, str(CORE), *argv])

    def forward(sig, _frame):
        if proc.poll() is None:
            proc.send_signal(sig)

    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, forward)

    rc = proc.wait()
    stop.set()
    thread.join(timeout=2)
    final = snapshot("worker_exited", rc)
    atomic_write(final)
    record(final)
    return rc


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
