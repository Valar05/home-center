#!/usr/bin/env python3
"""Durable Home Center scheduler for local maintenance jobs.

This is a small cron-like runner intended for Termux/tmux. Jobs live in
tools/home_center_scheduler_jobs.json so backend, Drive, and Android/Shizuku
maintenance can share one durable loop.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "tools/home_center_scheduler_jobs.json"
DEFAULT_STATE = ROOT / "generated/home_center_scheduler/state.json"
DEFAULT_LOG_DIR = ROOT / "generated/home_center_scheduler/logs"
SHIZUKU_REPORT = ROOT / "generated/shizuku_setup/home_center_shizuku_readiness.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_config(path: Path) -> dict[str, Any]:
    config = load_json(path, {})
    jobs = config.get("jobs") or []
    if not isinstance(jobs, list):
        raise SystemExit(f"scheduler config has non-list jobs: {path}")
    return config


def job_map(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for job in config.get("jobs") or []:
        if not isinstance(job, dict) or not job.get("id"):
            continue
        out[str(job["id"])] = job
    return out


def append_log(log_dir: Path, job_id: str, message: str) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    with (log_dir / f"{job_id}.log").open("a", encoding="utf-8") as handle:
        handle.write(f"{utc_now()} {message}\n")


def shizuku_ready(job: dict[str, Any], log_dir: Path) -> bool:
    if not job.get("requiresShizuku"):
        return True
    cmd = ["sh", "tools/home_center_shizuku_setup_probe.sh", "--report-only", "--no-network-install"]
    result = subprocess.run(cmd, cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=90)
    append_log(log_dir, str(job["id"]), f"shizuku probe exit={result.returncode}")
    try:
        report = json.loads(SHIZUKU_REPORT.read_text(encoding="utf-8"))
    except Exception as exc:
        append_log(log_dir, str(job["id"]), f"shizuku report unreadable: {exc}")
        return False
    ok = bool(report.get("shizuku", {}).get("authorized") and report.get("rish", {}).get("probe_ok"))
    if not ok:
        append_log(log_dir, str(job["id"]), f"shizuku not ready status={report.get('status')} blockers={report.get('blockers')}")
    return ok


def run_job(job: dict[str, Any], state: dict[str, Any], log_dir: Path, force: bool = False) -> dict[str, Any]:
    job_id = str(job["id"])
    now = time.time()
    jobs_state = state.setdefault("jobs", {})
    current = jobs_state.setdefault(job_id, {})
    interval = int(job.get("intervalSeconds") or 0)
    due_at = float(current.get("nextRunAtEpoch") or 0)
    if not force and interval > 0 and due_at > now:
        return {"jobId": job_id, "status": "not_due", "nextRunAtEpoch": due_at}
    if job.get("enabled") is False:
        return {"jobId": job_id, "status": "disabled"}
    if not shizuku_ready(job, log_dir):
        current.update({"lastStatus": "skipped_shizuku_not_ready", "lastRunAt": utc_now(), "lastExitCode": None})
        if interval > 0:
            current["nextRunAtEpoch"] = now + interval
        return {"jobId": job_id, "status": "skipped_shizuku_not_ready"}

    command = job.get("command")
    if not isinstance(command, list) or not command:
        raise SystemExit(f"job {job_id} has no command array")
    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in (job.get("env") or {}).items()})
    timeout = int(job.get("timeoutSeconds") or 900)
    append_log(log_dir, job_id, "start " + " ".join(map(str, command)))
    started = time.time()
    try:
        result = subprocess.run(command, cwd=ROOT, env=env, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
        output = result.stdout or ""
        exit_code = result.returncode
        status = "ok" if exit_code == 0 else "failed"
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or "") if isinstance(exc.stdout, str) else ""
        exit_code = 124
        status = "timeout"
    duration_ms = int((time.time() - started) * 1000)
    log_path = log_dir / f"{job_id}.log"
    with log_path.open("a", encoding="utf-8") as handle:
        if output:
            handle.write(output.rstrip() + "\n")
        handle.write(f"{utc_now()} finish status={status} exit={exit_code} durationMs={duration_ms}\n")
    current.update({
        "lastRunAt": utc_now(),
        "lastStatus": status,
        "lastExitCode": exit_code,
        "lastDurationMs": duration_ms,
        "logPath": str(log_path.relative_to(ROOT)),
    })
    if interval > 0:
        current["nextRunAtEpoch"] = time.time() + interval
    return {"jobId": job_id, "status": status, "exitCode": exit_code, "durationMs": duration_ms, "logPath": str(log_path.relative_to(ROOT))}


def due_jobs(config: dict[str, Any], state: dict[str, Any], only: str | None = None, force: bool = False) -> list[dict[str, Any]]:
    jobs = job_map(config)
    if only:
        if only not in jobs:
            raise SystemExit(f"unknown scheduler job: {only}")
        return [jobs[only]]
    if force:
        return list(jobs.values())
    out = []
    now = time.time()
    for job in jobs.values():
        if job.get("enabled") is False:
            continue
        current = state.get("jobs", {}).get(str(job["id"]), {})
        if float(current.get("nextRunAtEpoch") or 0) <= now:
            out.append(job)
    return out


def print_status(config: dict[str, Any], state: dict[str, Any]) -> None:
    rows = []
    for job_id, job in job_map(config).items():
        current = state.get("jobs", {}).get(job_id, {})
        rows.append({
            "id": job_id,
            "enabled": job.get("enabled") is not False,
            "intervalSeconds": job.get("intervalSeconds"),
            "requiresShizuku": bool(job.get("requiresShizuku")),
            "lastStatus": current.get("lastStatus"),
            "lastRunAt": current.get("lastRunAt"),
            "nextRunAtEpoch": current.get("nextRunAtEpoch"),
            "logPath": current.get("logPath"),
        })
    print(json.dumps({"ok": True, "generatedAt": utc_now(), "jobs": rows}, indent=2))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(DEFAULT_CONFIG))
    ap.add_argument("--state", default=str(DEFAULT_STATE))
    ap.add_argument("--log-dir", default=str(DEFAULT_LOG_DIR))
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--loop", action="store_true")
    ap.add_argument("--job")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--sleep-seconds", type=int, default=60)
    args = ap.parse_args()

    config_path = Path(args.config)
    state_path = Path(args.state)
    log_dir = Path(args.log_dir)
    config = load_config(config_path)
    state = load_json(state_path, {"version": 1, "jobs": {}})

    if args.list or args.status:
        print_status(config, state)
        return 0

    if not args.loop:
        selected = due_jobs(config, state, args.job, force=args.force or bool(args.job))
        results = [run_job(job, state, log_dir, force=args.force or bool(args.job)) for job in selected]
        state["updatedAt"] = utc_now()
        write_json(state_path, state)
        print(json.dumps({"ok": all(r.get("status") in {"ok", "not_due", "disabled", "skipped_shizuku_not_ready"} for r in results), "results": results, "statePath": str(state_path.relative_to(ROOT))}, indent=2))
        return 0 if all(r.get("status") != "failed" for r in results) else 1

    while True:
        state = load_json(state_path, {"version": 1, "jobs": {}})
        results = [run_job(job, state, log_dir, force=False) for job in due_jobs(config, state)]
        state["updatedAt"] = utc_now()
        write_json(state_path, state)
        if results:
            print(json.dumps({"at": utc_now(), "results": results}), flush=True)
        time.sleep(max(5, args.sleep_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
