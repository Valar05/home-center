#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from pathlib import Path

CONFIG = Path(os.path.expanduser(os.environ.get("HC_SSH_CONFIG", "~/.config/home-center/ssh-targets.json")))
STATE = Path(os.path.expanduser(os.environ.get("HC_SSH_STATE", "~/.local/state/home-center/ssh")))


def load_config() -> dict:
    if not CONFIG.exists():
        return {"schema": "home-center-ssh-targets-v1", "targets": {}}
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("targets"), dict):
        raise SystemExit("invalid SSH target config")
    return data


def target(name: str) -> dict:
    cfg = load_config().get("targets", {}).get(name)
    if not isinstance(cfg, dict):
        raise SystemExit(f"unknown SSH target: {name}")
    host = str(cfg.get("host") or "").strip()
    user = str(cfg.get("user") or "").strip()
    if not host or not user:
        raise SystemExit(f"target {name} requires host and user")
    return cfg


def ssh_argv(name: str, command: str) -> list[str]:
    cfg = target(name)
    port = int(cfg.get("port") or 22)
    timeout = int(cfg.get("connectTimeoutSeconds") or 10)
    argv = [
        "ssh", "-p", str(port),
        "-o", "BatchMode=yes",
        "-o", f"ConnectTimeout={timeout}",
        "-o", "ServerAliveInterval=20",
        "-o", "ServerAliveCountMax=2",
        "-o", "StrictHostKeyChecking=accept-new",
    ]
    identity = str(cfg.get("identityFile") or "").strip()
    if identity:
        argv += ["-i", os.path.expanduser(identity)]
    for opt in cfg.get("options") or []:
        if isinstance(opt, str) and opt.strip():
            argv += ["-o", opt.strip()]
    argv += [f"{cfg['user']}@{cfg['host']}", command]
    return argv


def receipt(name: str, command: str, proc: subprocess.CompletedProcess[str], started: float) -> dict:
    STATE.mkdir(parents=True, exist_ok=True)
    obj = {
        "schema": "home-center-ssh-receipt-v1",
        "target": name,
        "command": command,
        "exitCode": proc.returncode,
        "stdout": proc.stdout[-16000:],
        "stderr": proc.stderr[-16000:],
        "durationMs": int((time.monotonic() - started) * 1000),
        "atEpoch": int(time.time()),
        "ok": proc.returncode == 0,
    }
    path = STATE / f"{name}-latest.json"
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    with (STATE / "receipts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")
    return obj


def execute(name: str, command: str, timeout: int | None = None) -> int:
    cfg = target(name)
    runtime = int(timeout or cfg.get("commandTimeoutSeconds") or 120)
    started = time.monotonic()
    try:
        proc = subprocess.run(ssh_argv(name, command), text=True, capture_output=True, timeout=runtime)
    except subprocess.TimeoutExpired as exc:
        proc = subprocess.CompletedProcess(exc.cmd, 124, exc.stdout or "", exc.stderr or "command timeout")
    obj = receipt(name, command, proc, started)
    print(json.dumps(obj, indent=2, sort_keys=True))
    return 0 if obj["ok"] else obj["exitCode"] or 1


def status(name: str) -> int:
    return execute(name, "printf 'HOME_CENTER_SSH_OK\\n'; hostname", timeout=20)


def main() -> int:
    ap = argparse.ArgumentParser(prog="home-center-ssh")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("status"); p.add_argument("target")
    p = sub.add_parser("exec"); p.add_argument("target"); p.add_argument("command")
    p = sub.add_parser("argv"); p.add_argument("target"); p.add_argument("command")
    p = sub.add_parser("targets")
    args = ap.parse_args()
    if args.cmd == "targets":
        print(json.dumps(sorted(load_config().get("targets", {}).keys()), indent=2)); return 0
    if args.cmd == "argv":
        print(shlex.join(ssh_argv(args.target, args.command))); return 0
    if args.cmd == "status": return status(args.target)
    return execute(args.target, args.command)

if __name__ == "__main__":
    raise SystemExit(main())
