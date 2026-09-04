#!/usr/bin/env python3
import inspect
import json
import tempfile
from pathlib import Path

import fortress_night_status as night_status
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

        # Context cadence must reuse Night Core battery truth and never call the
        # daemon's generic 20-second rish helper for dumpsys battery.
        original_battery = night_status.battery
        original_rish = daemon.rish
        try:
            daemon.rish = lambda _cmd: (_ for _ in ()).throw(AssertionError("context cadence called generic rish"))
            night_status.battery = lambda: {"source": "termux-battery-status", "level": 80, "plugged": True, "status": "charging"}
            assert daemon.context_sensor_delay() == max(30, daemon.CONTEXT_SENSOR_CHARGING_INTERVAL)
            night_status.battery = lambda: {"source": "sysfs", "level": 35, "plugged": False, "status": "discharging"}
            assert daemon.context_sensor_delay() == max(60, daemon.CONTEXT_SENSOR_LOW_BATTERY_INTERVAL)
            night_status.battery = lambda: {"source": "rish-dumpsys", "level": 15, "plugged": False, "status": "discharging"}
            assert daemon.context_sensor_delay() == max(60, daemon.CONTEXT_SENSOR_CRITICAL_BATTERY_INTERVAL)
        finally:
            night_status.battery = original_battery
            daemon.rish = original_rish

        cadence_source = inspect.getsource(daemon.context_sensor_delay)
        assert 'result=rish("dumpsys battery")' not in cadence_source
        assert "night_status.battery()" in cadence_source
        fallback_source = inspect.getsource(night_status.rish_battery)
        assert 'run([rish, "-c", "dumpsys battery"], 3)' in fallback_source

    print("PASS Vlad context integration: same daemon heartbeat, deferred sensing, bounded Night Core battery cadence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
