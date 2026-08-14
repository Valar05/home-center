#!/usr/bin/env python3
"""Single local service supervisor for Fortress swarm + context organs.

Runs Vlad/Adam phone daemon as the body. In the supervisor loop, sensors observe
Library/ChatGPT-shell snapshots and the scheduler governor acts only when a
meaningful one-shot wake request exists. This replaces needy periodic ChatGPT
follow-ups with cheap local deterministic polling.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

STATE_DIR = Path(os.environ.get("HC_SWARM_STATE_DIR", "~/.local/state/home-center/vlad-swarm")).expanduser()
SENSE_INTERVAL = float(os.environ.get("HC_CONTEXT_SENSE_INTERVAL", "5"))
BODY_RESTART_MIN = float(os.environ.get("HC_SWARM_BODY_RESTART_MIN_SECONDS", "1"))
BODY_RESTART_MAX = float(os.environ.get("HC_SWARM_BODY_RESTART_MAX_SECONDS", "60"))


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def run_json(cmd: list[str], cwd: str, timeout: float = 40) -> dict:
    try:
        p = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, timeout=timeout)
        try:
            value = json.loads(p.stdout)
            payload = value if isinstance(value, dict) else {"stdout": p.stdout[-4000:]}
        except Exception:
            payload = {"stdout": p.stdout[-4000:], "stderr": p.stderr[-4000:]}
        return {"ok": p.returncode == 0, "rc": p.returncode, "payload": payload}
    except Exception as exc:
        return {"ok": False, "rc": 2, "payload": {"error": f"{type(exc).__name__}: {exc}"}}


def main() -> int:
    ap = argparse.ArgumentParser(description="Fortress local swarm supervisor")
    ap.add_argument("--repo", default=os.environ.get("HC_REPO_ROOT", "."))
    args = ap.parse_args()
    repo = str(Path(args.repo).resolve())
    tools = Path(repo) / "tools"
    body = tools / "vlad_swarm_daemon.py"
    sensors = tools / "fortress_context_sensors.py"
    governor = tools / "fortress_scheduler_governor.py"
    for path in (body, sensors, governor):
        if not path.is_file():
            raise SystemExit(f"BLOCKED: missing {path}")

    STATE_DIR.mkdir(parents=True, exist_ok=True)
    status_path = STATE_DIR / "supervisor-status.json"
    stopping = False
    body_proc = None
    restart_delay = BODY_RESTART_MIN

    def stop(_sig=None, _frame=None):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    next_sense = 0.0
    while not stopping:
        if body_proc is None or body_proc.poll() is not None:
            if body_proc is not None:
                time.sleep(restart_delay)
                restart_delay = min(BODY_RESTART_MAX, max(BODY_RESTART_MIN, restart_delay * 2))
            body_proc = subprocess.Popen(
                ["python3", str(body), "--repo", repo],
                cwd=repo,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            atomic_json(status_path, {
                "schema": "fortress.swarm-supervisor.v1",
                "state": "body_started",
                "bodyPid": body_proc.pid,
                "atEpoch": int(time.time()),
            })

        current = time.monotonic()
        if current >= next_sense:
            sense = run_json(["python3", str(sensors)], repo)
            govern = run_json(["python3", str(governor)], repo)
            atomic_json(status_path, {
                "schema": "fortress.swarm-supervisor.v1",
                "state": "healthy" if body_proc.poll() is None else "body_down",
                "bodyPid": body_proc.pid,
                "bodyReturnCode": body_proc.poll(),
                "sense": sense,
                "governor": govern,
                "atEpoch": int(time.time()),
            })
            next_sense = current + max(1.0, SENSE_INTERVAL)
            if body_proc.poll() is None:
                restart_delay = BODY_RESTART_MIN
        time.sleep(0.25)

    if body_proc is not None and body_proc.poll() is None:
        body_proc.terminate()
        try:
            body_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            body_proc.kill()
    atomic_json(status_path, {"schema": "fortress.swarm-supervisor.v1", "state": "stopped", "atEpoch": int(time.time())})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
