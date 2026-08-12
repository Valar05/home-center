#!/usr/bin/env python3
"""Deterministic SSH Axis health gate for Fortress Online.

This tool never claims an endpoint is callable from configuration alone.  Each
endpoint is promoted only after an end-to-end command receipt succeeds.

Typical use:
  python tools/ssh_axis.py check --target cauldron
  python tools/ssh_axis.py check --target phone
  python tools/ssh_axis.py check --target all --json

Configuration is intentionally boring and overridable:
  FORTRESS_CAULDRON_SSH   default: dclar@192.168.40.213
  FORTRESS_PHONE_SSH      optional OpenSSH endpoint for Termux, e.g. user@host:8022
  FORTRESS_SSH_CONFIG     optional ssh_config path

The existing Home Center/Phone Hands `phone_shell` lane remains authoritative
for ChatGPT -> phone execution.  A missing FORTRESS_PHONE_SSH is therefore
reported as `not_configured`, not silently treated as success.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path


DEFAULT_CAULDRON = "dclar@192.168.40.213"
PROBE = "printf FORTRESS_SSH_AXIS_OK"


@dataclass
class Receipt:
    target: str
    endpoint: str | None
    state: str
    callable: bool
    transport_ok: bool
    auth_ok: bool
    command_ok: bool
    observed: str
    elapsed_ms: int


def parse_endpoint(value: str) -> tuple[str, str, int]:
    user_host, sep, port_text = value.rpartition(":")
    if sep and port_text.isdigit() and "]" not in port_text:
        endpoint = user_host
        port = int(port_text)
    else:
        endpoint = value
        port = 22
    if "@" in endpoint:
        user, host = endpoint.rsplit("@", 1)
    else:
        user, host = "", endpoint
    return user, host.strip("[]"), port


def transport_probe(host: str, port: int, timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True, f"tcp:{host}:{port}:open"
    except OSError as exc:
        return False, f"tcp:{host}:{port}:{exc.__class__.__name__}:{exc}"


def ssh_probe(name: str, endpoint: str | None, timeout: float) -> Receipt:
    started = time.monotonic()
    if not endpoint:
        return Receipt(name, None, "not_configured", False, False, False, False,
                       "endpoint missing", int((time.monotonic() - started) * 1000))

    _, host, port = parse_endpoint(endpoint)
    transport_ok, observed = transport_probe(host, port, timeout)
    if not transport_ok:
        return Receipt(name, endpoint, "transport_failed", False, False, False, False,
                       observed, int((time.monotonic() - started) * 1000))

    command = [
        "ssh", "-o", "BatchMode=yes", "-o", "PasswordAuthentication=no",
        "-o", "KbdInteractiveAuthentication=no", "-o", "StrictHostKeyChecking=accept-new",
        "-o", f"ConnectTimeout={max(1, int(timeout))}", "-p", str(port),
    ]
    config = os.environ.get("FORTRESS_SSH_CONFIG")
    if config:
        command.extend(["-F", str(Path(config).expanduser())])
    # Strip :port because -p owns it.
    user, host, _ = parse_endpoint(endpoint)
    destination = f"{user}@{host}" if user else host
    command.extend([destination, PROBE])

    try:
        proc = subprocess.run(command, text=True, capture_output=True, timeout=timeout + 3)
    except FileNotFoundError:
        return Receipt(name, endpoint, "ssh_client_missing", False, True, False, False,
                       "ssh executable not found", int((time.monotonic() - started) * 1000))
    except subprocess.TimeoutExpired:
        return Receipt(name, endpoint, "auth_or_command_timeout", False, True, False, False,
                       "ssh command timed out", int((time.monotonic() - started) * 1000))

    stdout = proc.stdout.strip()
    stderr = proc.stderr.strip()
    auth_ok = proc.returncode == 0
    command_ok = auth_ok and stdout == "FORTRESS_SSH_AXIS_OK"
    if command_ok:
        state = "callable"
    elif proc.returncode == 255:
        state = "authentication_failed"
    else:
        state = "command_failed"
    observed = f"rc={proc.returncode}; stdout={stdout!r}; stderr={stderr[-500:]!r}"
    return Receipt(name, endpoint, state, command_ok, True, auth_ok, command_ok,
                   observed, int((time.monotonic() - started) * 1000))


def configured_targets() -> dict[str, str | None]:
    return {
        "cauldron": os.environ.get("FORTRESS_CAULDRON_SSH", DEFAULT_CAULDRON),
        "phone": os.environ.get("FORTRESS_PHONE_SSH"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify Fortress SSH Axis end to end")
    sub = parser.add_subparsers(dest="cmd", required=True)
    check = sub.add_parser("check")
    check.add_argument("--target", choices=["cauldron", "phone", "all"], default="all")
    check.add_argument("--timeout", type=float, default=4.0)
    check.add_argument("--json", action="store_true")
    args = parser.parse_args()

    targets = configured_targets()
    names = list(targets) if args.target == "all" else [args.target]
    receipts = [ssh_probe(name, targets[name], args.timeout) for name in names]

    if args.json:
        print(json.dumps({"ssh_axis": [asdict(r) for r in receipts]}, indent=2, sort_keys=True))
    else:
        for r in receipts:
            mark = "OK" if r.callable else "FAIL"
            print(f"[{mark}] {r.target}: {r.state} endpoint={r.endpoint or '-'}")
            print(f"      {r.observed}")

    return 0 if all(r.callable for r in receipts) else 2


if __name__ == "__main__":
    raise SystemExit(main())
