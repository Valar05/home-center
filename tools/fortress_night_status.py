#!/usr/bin/env python3
"""Cheap phone-local Night Core status probe.

Battery truth prefers Termux API/sysfs and only falls back to bounded rish.
No inference, Chromium inspection, screenshot, or UI dump is performed.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path

STATE = Path(os.environ.get("HC_STATE", "~/.local/state/home-center")).expanduser()
HEARTBEAT = Path(os.environ.get("HC_PHONE_RELAY_HEARTBEAT", str(STATE / "phone-relay-heartbeat.json"))).expanduser()


def run(cmd: list[str], timeout: int = 3) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (subprocess.TimeoutExpired, OSError) as exc:
        return 124, f"{type(exc).__name__}: {exc}"


def termux_battery() -> dict | None:
    rc, out = run(["termux-battery-status"], 3)
    if rc != 0:
        return None
    try:
        value = json.loads(out)
    except json.JSONDecodeError:
        return None
    pct = value.get("percentage")
    if not isinstance(pct, (int, float)):
        return None
    plugged = str(value.get("plugged", "UNPLUGGED")).upper() not in {"UNPLUGGED", "UNKNOWN", ""}
    return {
        "source": "termux-battery-status",
        "level": int(pct),
        "plugged": plugged,
        "status": str(value.get("status", "unknown")).lower(),
        "temperatureC": value.get("temperature"),
    }


def sysfs_battery() -> dict | None:
    base = Path("/sys/class/power_supply/battery")
    try:
        level = int((base / "capacity").read_text().strip())
    except (OSError, ValueError):
        return None
    try:
        status = (base / "status").read_text().strip().lower()
    except OSError:
        status = "unknown"
    plugged = status in {"charging", "full", "not charging"}
    temp = None
    for name in ("temp", "temperature"):
        try:
            raw = float((base / name).read_text().strip())
            temp = raw / 10.0 if abs(raw) > 80 else raw
            break
        except (OSError, ValueError):
            pass
    return {"source": "sysfs", "level": level, "plugged": plugged, "status": status, "temperatureC": temp}


def rish_battery() -> dict | None:
    candidates = [os.environ.get("RISH", ""), os.path.expanduser("~/bin/rish")]
    rish = next((p for p in candidates if p and os.path.isfile(p) and os.access(p, os.X_OK)), "")
    if not rish:
        return None
    rc, out = run([rish, "-c", "dumpsys battery"], 3)
    if rc != 0:
        return None
    fields: dict[str, str] = {}
    for line in out.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip().lower()] = v.strip()
    try:
        level = int(fields.get("level", "-1"))
    except ValueError:
        return None
    if level < 0:
        return None
    plugged = any(fields.get(k, "false").lower() == "true" for k in ("ac powered", "usb powered", "wireless powered", "dock powered"))
    status_code = fields.get("status", "1")
    status = {"1":"unknown", "2":"charging", "3":"discharging", "4":"not_charging", "5":"full"}.get(status_code, status_code)
    try:
        temp = int(fields.get("temperature", "-1")) / 10.0
        if temp < 0:
            temp = None
    except ValueError:
        temp = None
    return {"source": "rish-dumpsys", "level": level, "plugged": plugged, "status": status, "temperatureC": temp}


def battery() -> dict:
    return termux_battery() or sysfs_battery() or rish_battery() or {
        "source": "unavailable", "level": -1, "plugged": False, "status": "unknown", "temperatureC": None
    }


def relay() -> dict:
    if not HEARTBEAT.is_file():
        return {"heartbeatPath": str(HEARTBEAT), "present": False, "fresh": False, "ageSeconds": None}
    try:
        value = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"heartbeatPath": str(HEARTBEAT), "present": True, "fresh": False, "ageSeconds": None, "error": f"{type(exc).__name__}: {exc}"}
    last = int(value.get("lastSuccessAtEpoch") or 0)
    age = max(0, int(time.time()) - last) if last else None
    return {
        "heartbeatPath": str(HEARTBEAT),
        "present": True,
        "fresh": value.get("deviceId") == "primary-phone" and age is not None and age <= 15,
        "ageSeconds": age,
        "state": value.get("state", ""),
        "pid": value.get("pid", 0),
    }


def policy(b: dict) -> dict:
    level = int(b.get("level", -1))
    plugged = bool(b.get("plugged"))
    if plugged and 0 <= level < 30:
        mode, poll, heavy = "CHARGE_RECOVERY", 20, False
    elif plugged:
        mode, poll, heavy = "POWERED_ACTIVE", 5, True
    elif level >= 60:
        mode, poll, heavy = "BATTERY_ACTIVE", 15, True
    elif level >= 30:
        mode, poll, heavy = "BATTERY_BALANCED", 30, False
    elif level >= 0:
        mode, poll, heavy = "BATTERY_CONSERVE", 60, False
    else:
        mode, poll, heavy = "UNKNOWN_CONSERVATIVE", 30, False
    return {
        "mode": mode,
        "recommendedPollSeconds": poll,
        "heavyWorkAllowed": heavy,
        "reason": "battery/charging policy; no inference, Chromium screenshot, or UI dump",
    }


def main() -> int:
    b = battery()
    result = {
        "schema": "fortress.night-core.status.v2",
        "ok": int(b.get("level", -1)) >= 0,
        "device": socket.gethostname(),
        "atEpoch": int(time.time()),
        "nightCore": policy(b),
        "battery": b,
        "relay": relay(),
    }
    print(json.dumps(result, sort_keys=True))
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
