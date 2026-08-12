#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SCHEMA = "tristanline.v0"
DEFAULT_CONFIG = Path(os.path.expanduser("~/.config/tristanline/config.json"))
DEFAULT_STATE = Path(os.path.expanduser("~/.local/state/tristanline"))
MAX_OUTPUT = 12000


def now_local() -> dt.datetime:
    return dt.datetime.now().astimezone()


def load_config(path: Path) -> dict:
    data = json.loads(path.read_text())
    if data.get("schema") != SCHEMA:
        raise ValueError(f"config schema must be {SCHEMA}")
    profiles = data.get("profiles")
    if not isinstance(profiles, dict) or not profiles:
        raise ValueError("profiles must be a non-empty object")
    default_profile = data.get("default_profile", "normal")
    if default_profile not in profiles:
        raise ValueError("default_profile must name a profile")
    return data


def find_rish() -> str:
    explicit = os.getenv("RISH")
    candidates = [
        explicit,
        shutil.which("rish"),
        os.path.expanduser("~/bin/rish"),
        os.path.expanduser("~/rish"),
        "/storage/emulated/0/Documents/rish",
        "/storage/emulated/0/Download/rish",
    ]
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    raise RuntimeError("rish not found; export it from Shizuku into Termux")


def run_rish(command: str, timeout: int = 15) -> str:
    rish = find_rish()
    proc = subprocess.run(
        [rish, "-c", command],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=timeout,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or f"rish exited {proc.returncode}").strip())
    return proc.stdout.strip()[:MAX_OUTPUT]


def parse_hhmm(value: str) -> int:
    m = re.fullmatch(r"([01]\d|2[0-3]):([0-5]\d)", str(value))
    if not m:
        raise ValueError(f"invalid HH:MM: {value}")
    return int(m.group(1)) * 60 + int(m.group(2))


def in_window(now: dt.datetime, start: str, end: str) -> bool:
    minute = now.hour * 60 + now.minute
    a, b = parse_hhmm(start), parse_hhmm(end)
    if a == b:
        return True
    if a < b:
        return a <= minute < b
    return minute >= a or minute < b


def scheduled_profile(config: dict, now: dt.datetime | None = None) -> str:
    now = now or now_local()
    for rule in config.get("schedule", []):
        if not isinstance(rule, dict):
            continue
        days = rule.get("days", list(range(7)))
        profile = rule.get("profile")
        if now.weekday() not in days or profile not in config["profiles"]:
            continue
        if in_window(now, rule.get("start", "00:00"), rule.get("end", "00:00")):
            return profile
    return config.get("default_profile", "normal")


def foreground_package() -> str:
    raw = run_rish("dumpsys window 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp' | head -2")
    matches = re.findall(r"\b([A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+){1,})/", raw)
    return matches[-1] if matches else ""


def validate_profile(profile: dict) -> None:
    allowed = {
        "go_home", "screen_timeout_ms", "brightness", "media_volume",
        "force_stop_packages", "blocked_packages", "launch_package",
        "stay_awake_while_charging",
    }
    unknown = sorted(set(profile) - allowed)
    if unknown:
        raise ValueError(f"unknown profile key: {unknown[0]}")
    if "screen_timeout_ms" in profile and not (15000 <= int(profile["screen_timeout_ms"]) <= 86_400_000):
        raise ValueError("screen_timeout_ms out of bounds")
    if "brightness" in profile and not (0 <= int(profile["brightness"]) <= 255):
        raise ValueError("brightness out of bounds")
    if "media_volume" in profile and not (0 <= int(profile["media_volume"]) <= 25):
        raise ValueError("media_volume out of bounds")
    for key in ("force_stop_packages", "blocked_packages"):
        if key in profile and not isinstance(profile[key], list):
            raise ValueError(f"{key} must be a list")


def apply_profile(name: str, config: dict, *, enforce_only: bool = False) -> dict:
    if name not in config["profiles"]:
        raise ValueError(f"unknown profile: {name}")
    profile = config["profiles"][name]
    validate_profile(profile)
    actions: list[dict] = []

    if not enforce_only:
        if profile.get("go_home"):
            run_rish("input keyevent KEYCODE_HOME")
            actions.append({"kind": "home"})
        if "screen_timeout_ms" in profile:
            value = int(profile["screen_timeout_ms"])
            run_rish(f"settings put system screen_off_timeout {value}")
            actions.append({"kind": "screen_timeout_ms", "value": value})
        if "brightness" in profile:
            value = int(profile["brightness"])
            run_rish("settings put system screen_brightness_mode 0")
            run_rish(f"settings put system screen_brightness {value}")
            actions.append({"kind": "brightness", "value": value})
        if "media_volume" in profile:
            value = int(profile["media_volume"])
            run_rish(f"cmd media_session volume --stream 3 --set {value}")
            actions.append({"kind": "media_volume", "value": value})
        if "stay_awake_while_charging" in profile:
            value = 3 if profile["stay_awake_while_charging"] else 0
            run_rish(f"settings put global stay_on_while_plugged_in {value}")
            actions.append({"kind": "stay_awake_while_charging", "value": bool(value)})
        for package in profile.get("force_stop_packages", []):
            if re.fullmatch(r"[A-Za-z0-9_.]+", package):
                run_rish(f"am force-stop {package}")
                actions.append({"kind": "force_stop", "package": package})
        package = profile.get("launch_package")
        if package and re.fullmatch(r"[A-Za-z0-9_.]+", package):
            run_rish(f"monkey -p {package} -c android.intent.category.LAUNCHER 1 >/dev/null")
            actions.append({"kind": "launch", "package": package})

    foreground = foreground_package()
    if foreground and foreground in set(profile.get("blocked_packages", [])):
        run_rish("input keyevent KEYCODE_HOME")
        run_rish(f"am force-stop {foreground}")
        actions.append({"kind": "blocked_foreground", "package": foreground})

    return {"ok": True, "profile": name, "foreground": foreground, "actions": actions}


def journal(state_dir: Path, event: dict) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    with (state_dir / "events.jsonl").open("a") as f:
        f.write(json.dumps({"ts": time.time(), **event}, separators=(",", ":")) + "\n")


def tick(config_path: Path, state_dir: Path) -> dict:
    config = load_config(config_path)
    profile = scheduled_profile(config)
    active_file = state_dir / "active-profile"
    previous = active_file.read_text().strip() if active_file.exists() else ""
    result = apply_profile(profile, config, enforce_only=(profile == previous))
    state_dir.mkdir(parents=True, exist_ok=True)
    active_file.write_text(profile + "\n")
    journal(state_dir, {"kind": "tick", "changed": profile != previous, **result})
    return {"changed": profile != previous, **result}


def doctor(config_path: Path) -> dict:
    config = load_config(config_path)
    for profile in config["profiles"].values():
        validate_profile(profile)
    probe = run_rish("id; settings get system screen_off_timeout; dumpsys window 2>/dev/null | grep -E 'mCurrentFocus|mFocusedApp' | head -1")
    return {
        "ok": True,
        "schema": config["schema"],
        "config": str(config_path),
        "rish": find_rish(),
        "profile_now": scheduled_profile(config),
        "probe": probe,
    }


def daemon(config_path: Path, state_dir: Path) -> None:
    config = load_config(config_path)
    seconds = max(5, min(int(config.get("tick_seconds", 30)), 3600))
    journal(state_dir, {"kind": "daemon_start", "pid": os.getpid(), "tick_seconds": seconds})
    while True:
        try:
            tick(config_path, state_dir)
        except Exception as exc:
            journal(state_dir, {"kind": "error", "error": str(exc)})
        time.sleep(seconds)


def main() -> int:
    p = argparse.ArgumentParser(description="Tristanline deterministic Android policy engine")
    p.add_argument("--config", default=str(DEFAULT_CONFIG))
    p.add_argument("--state", default=str(DEFAULT_STATE))
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    sub.add_parser("tick")
    apply_p = sub.add_parser("apply")
    apply_p.add_argument("profile")
    sub.add_parser("status")
    sub.add_parser("daemon")
    args = p.parse_args()
    config_path, state_dir = Path(args.config).expanduser(), Path(args.state).expanduser()

    if args.command == "doctor":
        out = doctor(config_path)
    elif args.command == "tick":
        out = tick(config_path, state_dir)
    elif args.command == "apply":
        config = load_config(config_path)
        out = apply_profile(args.profile, config)
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "active-profile").write_text(args.profile + "\n")
        journal(state_dir, {"kind": "manual_apply", **out})
    elif args.command == "status":
        config = load_config(config_path)
        out = {
            "ok": True,
            "scheduled_profile": scheduled_profile(config),
            "active_profile": (state_dir / "active-profile").read_text().strip() if (state_dir / "active-profile").exists() else "",
            "foreground": foreground_package(),
        }
    else:
        daemon(config_path, state_dir)
        return 0
    print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
