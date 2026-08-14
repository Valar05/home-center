#!/usr/bin/env python3
import json
import tempfile
from pathlib import Path

import vlad_swarm_daemon as daemon


def main():
    with tempfile.TemporaryDirectory() as temp:
        daemon.STATE_DIR = Path(temp)
        events = []
        calls = {"sense": 0}
        daemon.append_receipt = lambda event: events.append(event)
        daemon.sync_judgment_jars = lambda _repo: {"ok": True, "state": "synced"}
        daemon.phone_health = lambda: True
        daemon.ensure_phone_ssh = lambda _repo: True
        daemon.ensure_operator_overlay = lambda _repo: True
        daemon.operator_heartbeat = lambda: None
        daemon.process_review_inbox = lambda _repo: None

        def fake_sense(_repo):
            calls["sense"] += 1
            return {
                "ok": True,
                "state": "wake_emitted",
                "wakeEmitted": True,
                "wakeReasons": ["context_changed"],
                "meaningfulDigest": "abc",
            }

        daemon.sense_context = fake_sense

        deferred = daemon.heartbeat("/repo", context_due=False)
        assert calls["sense"] == 0
        assert deferred["contextSenses"]["state"] == "deferred"

        sensed = daemon.heartbeat("/repo", context_due=True)
        assert calls["sense"] == 1
        assert sensed["contextSenses"]["state"] == "wake_emitted"
        assert events[-1]["kind"] == "swarm.heartbeat"
        assert events[-1]["contextSenses"]["wakeReasons"] == ["context_changed"]

        original_rish = daemon.rish
        try:
            daemon.rish = lambda _cmd: {"rc": 0, "stdout": "level: 80\nUSB powered: true\nstatus: 2\n", "stderr": ""}
            assert daemon.context_sensor_delay() == max(30, daemon.CONTEXT_SENSOR_CHARGING_INTERVAL)
            daemon.rish = lambda _cmd: {"rc": 0, "stdout": "level: 35\nUSB powered: false\nstatus: 3\n", "stderr": ""}
            assert daemon.context_sensor_delay() == max(60, daemon.CONTEXT_SENSOR_LOW_BATTERY_INTERVAL)
            daemon.rish = lambda _cmd: {"rc": 0, "stdout": "level: 15\nUSB powered: false\nstatus: 3\n", "stderr": ""}
            assert daemon.context_sensor_delay() == max(60, daemon.CONTEXT_SENSOR_CRITICAL_BATTERY_INTERVAL)
        finally:
            daemon.rish = original_rish

    print("PASS Vlad context integration: same daemon heartbeat, deferred sensing, battery-aware cadence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
