#!/usr/bin/env python3
"""Print the latest Home Center cart event for Termux RUN_COMMAND wakeups."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

EVENT_DIR = Path("/storage/emulated/0/Download/HomeCenter/cart-events")
WAKE_LOG = Path(".tmp/cart-event-wake.log")


def latest_event_file() -> Path | None:
    if not EVENT_DIR.exists():
        return None
    files = sorted(EVENT_DIR.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)
    return files[-1] if files else None


def latest_line(path: Path) -> str:
    last = ""
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                last = line.strip()
    return last


def main() -> int:
    path = latest_event_file()
    if path is None:
        print("Home Center cart event wake: no event file yet")
        return 1
    line = latest_line(path)
    if not line:
        print(f"Home Center cart event wake: {path} is empty")
        return 1
    try:
        event = json.loads(line)
    except json.JSONDecodeError:
        event = {"event": "unparseable", "raw": line}
    summary = {
        "wokeAt": datetime.now().isoformat(timespec="seconds"),
        "eventFile": str(path),
        "event": event.get("event", ""),
        "key": event.get("key", ""),
        "item": event.get("item", ""),
        "status": event.get("status", ""),
        "productUrl": event.get("productUrl", ""),
    }
    print("Home Center cart event")
    print(json.dumps(summary, indent=2, sort_keys=True))
    WAKE_LOG.parent.mkdir(parents=True, exist_ok=True)
    with WAKE_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(summary, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
