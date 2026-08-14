#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

import fortress_context_sensors as sensors


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value) + "\n", encoding="utf-8")


def receipts(path):
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        sensors.STATE_DIR = root
        sensors.CONTEXT_DIR = root / "context"
        sensors.LIBRARY_SNAPSHOT = sensors.CONTEXT_DIR / "library.snapshot.json"
        sensors.SHELL_SNAPSHOT = sensors.CONTEXT_DIR / "chatgpt-shell.snapshot.json"
        sensors.LIBRARY_CMD = ""
        sensors.SHELL_CMD = ""
        sensors.STALE_SECONDS = 900
        clock = {"now": 1000}
        sensors.now = lambda: clock["now"]

        library = {
            "observedAtEpoch": 1000,
            "version": "v1",
            "bootstrap": {"digest": "boot-a"},
            "index": {"digest": "index-a"},
            "activeCampaigns": [{"id": "fortress", "state": "running"}],
            "pendingOutboxes": [],
        }
        shell = {
            "observedAtEpoch": 1000,
            "surface": "chatgpt",
            "schedulerReachable": True,
            "actuatorReachable": True,
            "workers": [{"id": "worker-a", "title": "A", "enabled": True, "lastRunEpoch": 990, "lastResult": "healthy"}],
        }
        write(sensors.LIBRARY_SNAPSHOT, library)
        write(sensors.SHELL_SNAPSHOT, shell)

        first = sensors.sense()
        assert first["wakeEmitted"] is False
        assert first["wakeRequired"] is False
        assert not (sensors.CONTEXT_DIR / "scheduler-wake-request.json").exists()

        # Timestamp-only polling churn is explicitly not meaningful.
        clock["now"] = 1001
        library["observedAtEpoch"] = 1001
        shell["observedAtEpoch"] = 1001
        shell["workers"][0]["lastRunEpoch"] = 991
        write(sensors.LIBRARY_SNAPSHOT, library)
        write(sensors.SHELL_SNAPSHOT, shell)
        quiet = sensors.sense()
        assert quiet["changed"] is False
        assert quiet["wakeEmitted"] is False
        assert quiet["wakeRequired"] is False
        assert receipts(sensors.CONTEXT_DIR / "scheduler-wake-receipts.jsonl") == []

        # A durable Library/campaign delta emits exactly one context-change wake.
        clock["now"] = 1002
        library["version"] = "v2"
        library["activeCampaigns"][0]["state"] = "needs-review"
        write(sensors.LIBRARY_SNAPSHOT, library)
        changed = sensors.sense()
        assert changed["changed"] is True
        assert changed["wakeEmitted"] is True
        assert changed["wakeReasons"] == ["context_changed"]
        wake_path = sensors.CONTEXT_DIR / "scheduler-wake-request.json"
        assert wake_path.exists()
        first_receipts = receipts(sensors.CONTEXT_DIR / "scheduler-wake-receipts.jsonl")
        assert len(first_receipts) == 1

        # Once the actuator consumes that request, unchanged state does not recreate it.
        wake_path.unlink()
        clock["now"] = 1003
        unchanged = sensors.sense()
        assert unchanged["changed"] is False
        assert unchanged["wakeEmitted"] is False
        assert unchanged["wakeRequired"] is False
        assert not wake_path.exists()
        assert len(receipts(sensors.CONTEXT_DIR / "scheduler-wake-receipts.jsonl")) == 1

        # Crossing the stale threshold emits one wake; persistent staleness stays quiet.
        clock["now"] = 2000
        shell["workers"][0]["lastRunEpoch"] = 1000
        write(sensors.SHELL_SNAPSHOT, shell)
        stale = sensors.sense()
        assert stale["wakeEmitted"] is True
        assert "stale_workers" in stale["wakeReasons"]
        stale_key = stale["wakeKey"]
        assert len(receipts(sensors.CONTEXT_DIR / "scheduler-wake-receipts.jsonl")) == 2
        wake_path.unlink()

        clock["now"] = 2001
        stale_again = sensors.sense()
        assert stale_again["wakeRequired"] is True
        assert stale_again["wakeKey"] == stale_key
        assert stale_again["wakeEmitted"] is False
        assert not wake_path.exists()
        assert len(receipts(sensors.CONTEXT_DIR / "scheduler-wake-receipts.jsonl")) == 2

    print("PASS fortress context sensors: unchanged quiet, meaningful delta wakes once, persistent stale does not nag")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
