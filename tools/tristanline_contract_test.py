#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("tristanline", HERE / "tristanline.py")
MOD = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MOD)


def expect(condition, message):
    if not condition:
        raise AssertionError(message)


def main():
    expect(MOD.in_window(dt.datetime(2026, 8, 11, 23, 0), "22:00", "07:00"), "overnight window late side")
    expect(MOD.in_window(dt.datetime(2026, 8, 12, 6, 30), "22:00", "07:00"), "overnight window early side")
    expect(not MOD.in_window(dt.datetime(2026, 8, 12, 12, 0), "22:00", "07:00"), "overnight window outside")

    cfg = {
        "schema": "tristanline.v0",
        "default_profile": "normal",
        "profiles": {"normal": {}, "quiet": {"go_home": True}},
        "schedule": [{"days": [1], "start": "22:00", "end": "07:00", "profile": "quiet"}],
    }
    expect(MOD.scheduled_profile(cfg, dt.datetime(2026, 8, 11, 23, 0)) == "quiet", "Tuesday quiet selection")
    expect(MOD.scheduled_profile(cfg, dt.datetime(2026, 8, 11, 12, 0)) == "normal", "daytime normal selection")

    try:
        MOD.validate_profile({"arbitrary_shell": "rm -rf /"})
    except ValueError:
        pass
    else:
        raise AssertionError("unknown/arbitrary action was accepted")

    calls = []
    with patch.object(MOD, "run_rish", side_effect=lambda command, timeout=15: calls.append(command) or ""), \
         patch.object(MOD, "foreground_package", return_value="com.example.blocked"):
        out = MOD.apply_profile("quiet", {
            "profiles": {"quiet": {"go_home": True, "blocked_packages": ["com.example.blocked"]}},
        })
    expect(out["ok"], "apply profile failed")
    expect(calls.count("input keyevent KEYCODE_HOME") == 2, "expected configured home + blocked-app escape")
    expect("am force-stop com.example.blocked" in calls, "blocked foreground was not stopped")

    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "config.json"
        p.write_text(json.dumps(cfg))
        loaded = MOD.load_config(p)
        expect(loaded["schema"] == "tristanline.v0", "config load failed")

    print("tristanline deterministic schedule + bounded config + enforcement contract: PASS")


if __name__ == "__main__":
    main()
