#!/usr/bin/env python3
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

MODULE = Path(__file__).with_name("eve_humane_session_daemon.py")
spec = importlib.util.spec_from_file_location("eve_humane_session_daemon", MODULE)
eve = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(eve)


class EveHumaneSessionTests(unittest.TestCase):
    def cfg(self):
        return {
            "enabled": True,
            "session_window_minutes": 45,
            "minimum_recovery_minutes": 360,
            "max_session_windows_per_day": 1,
            "schedule": [{"time": "19:30", "days": list(range(7))}],
            "quiet_hours": {"start": "22:30", "end": "09:00"},
            "eve": {},
        }

    def state(self):
        return eve.blank_state()

    def dt(self, hour, minute=0):
        return datetime(2026, 8, 11, hour, minute, tzinfo=timezone(timedelta(hours=-5)))

    def test_quiet_hours_wrap_midnight(self):
        cfg = self.cfg()
        self.assertTrue(eve.in_quiet_hours(self.dt(23), cfg))
        self.assertTrue(eve.in_quiet_hours(self.dt(8, 59), cfg))
        self.assertFalse(eve.in_quiet_hours(self.dt(12), cfg))

    def test_scheduled_window_opens(self):
        win = eve.window_for_now(self.cfg(), self.state(), self.dt(19, 40))
        self.assertIsNotNone(win)

    def test_window_closes_after_45_minutes(self):
        win = eve.window_for_now(self.cfg(), self.state(), self.dt(20, 16))
        self.assertIsNone(win)

    def test_recovery_blocks_scheduled_window(self):
        state = self.state()
        state["recovery_until"] = self.dt(21).isoformat()
        self.assertIsNone(eve.window_for_now(self.cfg(), state, self.dt(19, 40)))

    def test_daily_limit_blocks_second_session(self):
        state = self.state()
        state["session_dates"] = ["2026-08-11"]
        self.assertIsNone(eve.window_for_now(self.cfg(), state, self.dt(19, 40)))

    def test_skip_blocks_today(self):
        state = self.state()
        state["skipped_dates"] = ["2026-08-11"]
        self.assertIsNone(eve.window_for_now(self.cfg(), state, self.dt(19, 40)))


if __name__ == "__main__":
    unittest.main()
