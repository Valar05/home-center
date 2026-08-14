#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_ROOT = Path(os.path.expanduser(os.getenv("HC_VENICE_GARDEN_STATE", "~/.local/state/home-center/venice-garden")))
STATUS = STATE_ROOT / "status.json"
HISTORY = STATE_ROOT / "history.jsonl"
LOCK = STATE_ROOT / "run.lock"
DEFAULT_INTERVAL = int(os.getenv("HC_VENICE_GARDEN_INTERVAL", "60"))
RESERVE_MB = int(os.getenv("HC_VENICE_GARDEN_RESERVE_MB", "3072"))
MAX_WORKERS = int(os.getenv("HC_VENICE_GARDEN_MAX_WORKERS", "3"))


@dataclass
class Resources:
    battery_percent: int | None
    charging: bool | None
    ram_total_mb: int
    ram_available_mb: int
    mode: str


def run(cmd, timeout=20):
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout)


def read_linux_ram():
    p = Path("/proc/meminfo")
    if not p.is_file():
        return None
    vals = {}
    for line in p.read_text(encoding="utf-8").splitlines():
        key, value = line.split(":", 1)
        vals[key] = int(value.strip().split()[0]) // 1024
    return vals.get("MemTotal", 0), vals.get("MemAvailable", 0)


def read_windows_ram():
    if os.name != "nt":
        return None
    ps = run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize,FreePhysicalMemory | ConvertTo-Json -Compress)"])
    if ps.returncode:
        return None
    obj = json.loads(ps.stdout)
    return int(obj["TotalVisibleMemorySize"]) // 1024, int(obj["FreePhysicalMemory"]) // 1024


def read_ram():
    return read_linux_ram() or read_windows_ram() or (0, 0)


def read_termux_battery():
    exe = shutil.which("termux-battery-status")
    if not exe:
        return None
    p = run([exe])
    if p.returncode:
        return None
    obj = json.loads(p.stdout)
    return int(obj.get("percentage")), str(obj.get("status", "")).upper() in {"CHARGING", "FULL"}


def read_linux_battery():
    roots = sorted(Path("/sys/class/power_supply").glob("BAT*"))
    if not roots:
        return None
    bat = roots[0]
    try:
        pct = int((bat / "capacity").read_text().strip())
        status = (bat / "status").read_text().strip().lower()
        return pct, status in {"charging", "full"}
    except Exception:
        return None


def read_windows_battery():
    if os.name != "nt":
        return None
    p = run(["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Battery | Select-Object -First 1 EstimatedChargeRemaining,BatteryStatus | ConvertTo-Json -Compress)"])
    if p.returncode or not p.stdout.strip() or p.stdout.strip() == "null":
        return None
    obj = json.loads(p.stdout)
    return int(obj["EstimatedChargeRemaining"]), int(obj.get("BatteryStatus", 0)) in {2, 6, 7, 8, 9, 11}


def read_battery():
    return read_termux_battery() or read_linux_battery() or read_windows_battery() or (None, None)


def previous_mode():
    try:
        return json.loads(STATUS.read_text(encoding="utf-8")).get("resources", {}).get("mode")
    except Exception:
        return None


def choose_mode(pct, charging, available_mb, previous):
    if available_mb and available_mb < RESERVE_MB:
        return "CONSERVE"
    if pct is None:
        return "NORMAL" if available_mb >= RESERVE_MB else "CONSERVE"
    if previous == "CONSERVE" and pct < 45 and not charging:
        return "CONSERVE"
    if not charging and pct < 35:
        return "CONSERVE"
    if previous == "BLOOM" and charging and pct >= 65 and available_mb >= RESERVE_MB * 2:
        return "BLOOM"
    if charging and pct >= 75 and available_mb >= RESERVE_MB * 2:
        return "BLOOM"
    return "NORMAL"


def observe():
    total, available = read_ram()
    pct, charging = read_battery()
    mode = choose_mode(pct, charging, available, previous_mode())
    return Resources(pct, charging, total, available, mode)


def tmux_sessions():
    if not shutil.which("tmux"):
        return []
    p = run(["tmux", "list-sessions", "-F", "#{session_name}"], timeout=5)
    if p.returncode:
        return []
    return [x for x in p.stdout.splitlines() if x.startswith("venice-garden-")]


def worker_budget(resources: Resources):
    if resources.mode == "CONSERVE":
        return 0
    if resources.mode == "BLOOM":
        return MAX_WORKERS
    return min(1, MAX_WORKERS)


def decision_prompt(resources: Resources, active: list[str]):
    return f"""VENICE'S GARDEN — autonomous Fortress cultivation turn.
You are Venice. Decide what is most useful to Fortress now; do not wait for Drew to prescribe a task.
Preserve the commission boundary and prefer durable, deterministic, local-first improvements.
Current machine resources: {json.dumps(asdict(resources), sort_keys=True)}
Active garden workers: {active}
Choose ONE bounded improvement or consolidation action that fits the resource mode. If nothing deserves inference, do cheap deterministic maintenance and exit.
Produce a receipt describing observation, choice, action, evidence, and what became cheaper/more deterministic.
Do not merely brainstorm: use Home Center's existing tools and repository when a safe useful change can actually be made.
"""


def launch_worker(resources: Resources):
    active = tmux_sessions()
    budget = worker_budget(resources)
    if len(active) >= budget:
        return {"launched": False, "reason": "worker_budget_full", "budget": budget, "active": active}
    if budget == 0:
        return {"launched": False, "reason": "conserve", "budget": 0, "active": active}
    adam = ROOT / "tools" / "adam.py"
    if not adam.is_file():
        return {"launched": False, "reason": "adam_missing"}
    prompt = decision_prompt(resources, active)
    stamp = int(time.time())
    session = f"venice-garden-{stamp}"
    receipt = STATE_ROOT / "receipts" / f"{stamp}.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    command = [sys.executable, str(adam), "continue", prompt, "--cwd", str(ROOT), "--timeout", "300"]
    if shutil.which("tmux"):
        wrapped = " ".join(subprocess.list2cmdline([part]) for part in command)
        shell = f"{wrapped}; rc=$?; printf '%s\\n' '{{\"schema\":\"venice-garden-worker-v1\",\"exitCode\":'\"$rc\"',\"finishedAt\":'\"$(date +%s)\"'}}' > {subprocess.list2cmdline([str(receipt)])}"
        p = run(["tmux", "new-session", "-d", "-s", session, shell])
        return {"launched": p.returncode == 0, "session": session, "receipt": str(receipt), "stderr": p.stderr[-1000:]}
    # Portable fallback: detached child process, no tmux dependency.
    log = receipt.with_suffix(".log")
    with log.open("a", encoding="utf-8") as fh:
        subprocess.Popen(command, cwd=ROOT, stdout=fh, stderr=subprocess.STDOUT, start_new_session=True)
    return {"launched": True, "session": None, "pidMode": True, "log": str(log)}


def prune_if_needed(resources: Resources):
    active = tmux_sessions()
    budget = worker_budget(resources)
    killed = []
    for session in active[budget:]:
        p = run(["tmux", "kill-session", "-t", session], timeout=5)
        if p.returncode == 0:
            killed.append(session)
    return killed


def write_status(resources, launch, pruned):
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    row = {
        "schema": "home-center.venice-garden.v1",
        "time": int(time.time()),
        "host": platform.node(),
        "platform": platform.platform(),
        "resources": asdict(resources),
        "active": tmux_sessions(),
        "launch": launch,
        "pruned": pruned,
    }
    STATUS.write_text(json.dumps(row, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, sort_keys=True) + "\n")
    return row


def cycle(dispatch=True):
    resources = observe()
    pruned = prune_if_needed(resources)
    launch = launch_worker(resources) if dispatch else {"launched": False, "reason": "observe_only"}
    return write_status(resources, launch, pruned)


def daemon(interval):
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    if LOCK.exists():
        try:
            pid = int(LOCK.read_text().strip())
            os.kill(pid, 0)
            raise SystemExit(f"Venice Garden already running as pid {pid}")
        except ProcessLookupError:
            LOCK.unlink(missing_ok=True)
        except (ValueError, PermissionError):
            LOCK.unlink(missing_ok=True)
    LOCK.write_text(str(os.getpid()), encoding="utf-8")
    try:
        while True:
            print(json.dumps(cycle(dispatch=True), sort_keys=True), flush=True)
            time.sleep(interval)
    finally:
        LOCK.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description="Portable Home Center governor for Venice's autonomous Garden")
    ap.add_argument("command", choices=["once", "observe", "daemon", "status"])
    ap.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)
    args = ap.parse_args()
    if args.command == "status":
        print(STATUS.read_text(encoding="utf-8") if STATUS.is_file() else json.dumps({"ok": False, "reason": "no_status_yet"}))
        return 0
    if args.command == "observe":
        print(json.dumps(cycle(dispatch=False), indent=2, sort_keys=True))
        return 0
    if args.command == "once":
        print(json.dumps(cycle(dispatch=True), indent=2, sort_keys=True))
        return 0
    daemon(max(15, args.interval))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
