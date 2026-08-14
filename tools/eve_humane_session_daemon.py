#!/data/data/com.termux/files/usr/bin/python
"""Local-only humane session scheduler for Android/Termux.

This daemon schedules *availability windows*, not doses. It never recommends an
amount, never asks for redosing, and defaults to long recovery/quiet periods.
Eve commentary is deterministic template selection: no model, no chat, no network.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

HOME = Path.home()
CFG_PATH = HOME / ".config/home-center/eve-humane-session.json"
STATE_PATH = HOME / ".local/state/home-center/eve-humane-session-state.json"
LOG_PATH = HOME / ".local/state/home-center/eve-humane-session.log"

DEFAULT_CONFIG: dict[str, Any] = {
    "enabled": True,
    "session_window_minutes": 45,
    "minimum_recovery_minutes": 360,
    "max_session_windows_per_day": 1,
    "schedule": [
        {"time": "19:30", "days": [0, 1, 2, 3, 4, 5, 6]},
    ],
    "quiet_hours": {"start": "22:30", "end": "09:00"},
    "eve": {
        "enabled": True,
        "speak": False,
        "title": "Eve — Fortress intermission",
        "window_lines": [
            "The theater has opened one curtain. No sequel has been ordered.",
            "Tonight's feature is optional. The recovery credits are mandatory.",
            "A window exists. This is not a command performance.",
        ],
        "session_lines": [
            "Feature started. Eve has confiscated the sequel button until recovery.",
            "One scene, then intermission. The tiny critic in the balcony has spoken.",
            "Session marked. No redose prompts will be issued; enjoy the movie, not the treadmill.",
        ],
        "recovery_lines": [
            "Intermission. Hydrate, eat if useful, sleep on time, let the projector cool.",
            "Credits are rolling. The next useful special effect is being sober again.",
            "Recovery block engaged. Eve is guarding the sequel from bad pacing.",
        ],
        "skip_lines": [
            "Tonight's episode has been pre-empted by competent executive function.",
            "Skipped. The audience survives the cliffhanger.",
            "No feature tonight. Eve awards one deeply unfashionable point for restraint.",
        ],
    },
}


def now_local() -> datetime:
    return datetime.now().astimezone()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    ensure_parent(path)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        atomic_json(path, default)
        return json.loads(json.dumps(default))
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def log(message: str) -> None:
    ensure_parent(LOG_PATH)
    stamp = now_local().isoformat(timespec="seconds")
    with LOG_PATH.open("a", encoding="utf-8") as fh:
        fh.write(f"{stamp} {message}\n")


def parse_hhmm(value: str) -> tuple[int, int]:
    h, m = value.split(":", 1)
    return int(h), int(m)


def minute_of_day(value: str) -> int:
    h, m = parse_hhmm(value)
    return h * 60 + m


def in_quiet_hours(dt: datetime, cfg: dict[str, Any]) -> bool:
    q = cfg.get("quiet_hours") or {}
    start = minute_of_day(q.get("start", "23:00"))
    end = minute_of_day(q.get("end", "08:00"))
    cur = dt.hour * 60 + dt.minute
    if start == end:
        return False
    if start < end:
        return start <= cur < end
    return cur >= start or cur < end


def stable_line(lines: list[str], key: str) -> str:
    if not lines:
        return ""
    digest = hashlib.sha256(key.encode("utf-8")).digest()
    return lines[int.from_bytes(digest[:4], "big") % len(lines)]


def notify(cfg: dict[str, Any], body: str, event_id: str) -> None:
    if not body:
        return
    eve = cfg.get("eve") or {}
    title = eve.get("title", "Eve")
    cmd = [
        "termux-notification",
        "--id", "eve-humane-session",
        "--title", str(title),
        "--content", body,
        "--priority", "default",
    ]
    try:
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        pass
    if eve.get("speak"):
        try:
            subprocess.run(["termux-tts-speak", body], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            pass
    log(f"notify event={event_id} body={body!r}")


def blank_state() -> dict[str, Any]:
    return {
        "last_window_notice": None,
        "active_window": None,
        "session_started_at": None,
        "recovery_until": None,
        "skipped_dates": [],
        "session_dates": [],
    }


def load_state() -> dict[str, Any]:
    return load_json(STATE_PATH, blank_state())


def save_state(state: dict[str, Any]) -> None:
    atomic_json(STATE_PATH, state)


def parse_iso(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def today_key(dt: datetime) -> str:
    return dt.date().isoformat()


def sessions_today(state: dict[str, Any], dt: datetime) -> int:
    key = today_key(dt)
    return sum(1 for x in state.get("session_dates", []) if x == key)


def in_recovery(state: dict[str, Any], dt: datetime) -> bool:
    until = parse_iso(state.get("recovery_until"))
    return bool(until and dt < until)


def window_for_now(cfg: dict[str, Any], state: dict[str, Any], dt: datetime) -> dict[str, Any] | None:
    if not cfg.get("enabled", True) or in_quiet_hours(dt, cfg) or in_recovery(state, dt):
        return None
    if today_key(dt) in state.get("skipped_dates", []):
        return None
    if sessions_today(state, dt) >= int(cfg.get("max_session_windows_per_day", 1)):
        return None
    length = int(cfg.get("session_window_minutes", 45))
    for item in cfg.get("schedule", []):
        if dt.weekday() not in item.get("days", list(range(7))):
            continue
        h, m = parse_hhmm(item["time"])
        start = dt.replace(hour=h, minute=m, second=0, microsecond=0)
        end = start + timedelta(minutes=length)
        if start <= dt < end:
            return {"start": start, "end": end, "id": f"{start.date()}@{item['time']}"}
    return None


def reconcile(cfg: dict[str, Any], state: dict[str, Any], dt: datetime) -> None:
    # End an active session automatically when its chosen window length expires.
    started = parse_iso(state.get("session_started_at"))
    if started:
        length = int(cfg.get("session_window_minutes", 45))
        if dt >= started + timedelta(minutes=length):
            state["session_started_at"] = None
            state["active_window"] = None
            recovery = dt + timedelta(minutes=int(cfg.get("minimum_recovery_minutes", 360)))
            existing = parse_iso(state.get("recovery_until"))
            if existing and existing > recovery:
                recovery = existing
            state["recovery_until"] = recovery.isoformat()
            line = stable_line((cfg.get("eve") or {}).get("recovery_lines", []), f"recover:{dt.date()}")
            notify(cfg, line, "recovery")
            save_state(state)

    win = window_for_now(cfg, state, dt)
    if win and not state.get("session_started_at") and state.get("last_window_notice") != win["id"]:
        state["last_window_notice"] = win["id"]
        state["active_window"] = {
            "id": win["id"],
            "start": win["start"].isoformat(),
            "end": win["end"].isoformat(),
        }
        line = stable_line((cfg.get("eve") or {}).get("window_lines", []), win["id"])
        notify(cfg, line, "window")
        save_state(state)


def command_begin(cfg: dict[str, Any], state: dict[str, Any], dt: datetime) -> int:
    win = window_for_now(cfg, state, dt)
    if not win:
        reason = "quiet/recovery/limit/no scheduled window"
        print(f"BLOCKED: {reason}")
        return 2
    state["session_started_at"] = dt.isoformat()
    state["active_window"] = {"id": win["id"], "start": win["start"].isoformat(), "end": win["end"].isoformat()}
    state.setdefault("session_dates", []).append(today_key(dt))
    # Bound unbounded state growth.
    state["session_dates"] = state["session_dates"][-120:]
    save_state(state)
    line = stable_line((cfg.get("eve") or {}).get("session_lines", []), f"session:{dt.isoformat()}")
    notify(cfg, line, "session")
    print(f"SESSION WINDOW STARTED until {(dt + timedelta(minutes=int(cfg.get('session_window_minutes',45)))).isoformat(timespec='minutes')}")
    return 0


def command_end(cfg: dict[str, Any], state: dict[str, Any], dt: datetime) -> int:
    state["session_started_at"] = None
    state["active_window"] = None
    recovery = dt + timedelta(minutes=int(cfg.get("minimum_recovery_minutes", 360)))
    state["recovery_until"] = recovery.isoformat()
    save_state(state)
    line = stable_line((cfg.get("eve") or {}).get("recovery_lines", []), f"manual-end:{dt.isoformat()}")
    notify(cfg, line, "recovery")
    print(f"RECOVERY until {recovery.isoformat(timespec='minutes')}")
    return 0


def command_skip(cfg: dict[str, Any], state: dict[str, Any], dt: datetime) -> int:
    key = today_key(dt)
    state.setdefault("skipped_dates", []).append(key)
    state["skipped_dates"] = sorted(set(state["skipped_dates"]))[-120:]
    state["active_window"] = None
    save_state(state)
    line = stable_line((cfg.get("eve") or {}).get("skip_lines", []), f"skip:{key}")
    notify(cfg, line, "skip")
    print(f"SKIPPED {key}")
    return 0


def command_status(cfg: dict[str, Any], state: dict[str, Any], dt: datetime) -> int:
    reconcile(cfg, state, dt)
    state = load_state()
    payload = {
        "now": dt.isoformat(timespec="seconds"),
        "quiet": in_quiet_hours(dt, cfg),
        "in_recovery": in_recovery(state, dt),
        "recovery_until": state.get("recovery_until"),
        "session_started_at": state.get("session_started_at"),
        "sessions_today": sessions_today(state, dt),
        "window": state.get("active_window"),
        "config": str(CFG_PATH),
        "state": str(STATE_PATH),
    }
    print(json.dumps(payload, indent=2))
    return 0


def daemon(cfg: dict[str, Any]) -> int:
    log("daemon start")
    while True:
        try:
            state = load_state()
            reconcile(cfg, state, now_local())
        except Exception as exc:  # daemon must survive malformed transient state
            log(f"ERROR {type(exc).__name__}: {exc}")
        time.sleep(30)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["daemon", "status", "begin", "end", "skip", "init"], nargs="?", default="status")
    args = parser.parse_args(argv)

    cfg = load_json(CFG_PATH, DEFAULT_CONFIG)
    state = load_state()
    dt = now_local()

    if args.command == "init":
        print(CFG_PATH)
        return 0
    if args.command == "daemon":
        return daemon(cfg)
    if args.command == "status":
        return command_status(cfg, state, dt)
    if args.command == "begin":
        return command_begin(cfg, state, dt)
    if args.command == "end":
        return command_end(cfg, state, dt)
    if args.command == "skip":
        return command_skip(cfg, state, dt)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
