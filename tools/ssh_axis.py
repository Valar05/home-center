#!/usr/bin/env python3
"""Deterministic SSH Axis health gate for Fortress Online.

This tool never claims an endpoint is callable from configuration alone. Each
endpoint is promoted only after an end-to-end command receipt succeeds.

Typical use:
  python tools/ssh_axis.py check --target cauldron
  python tools/ssh_axis.py check --target phone
  python tools/ssh_axis.py check --target all --json

THECAULDRON selection order is intentionally boring:
  1. FORTRESS_CAULDRON_SSH when explicitly supplied.
  2. The last endpoint actually verified by resolve_cauldron_ssh.py.
  3. dclar@THECAULDRON (or configured user/hostname), allowing normal DNS,
     mDNS, or Tailscale MagicDNS to resolve it.

No Shizuku/rish capability is required by this module.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

PROBE = "printf FORTRESS_SSH_AXIS_OK"
CAULDRON_STATE = Path.home() / '.local/state/fortress-online/cauldron-ssh-endpoint.json'


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


def cached_cauldron_endpoint() -> str | None:
    try:
        data = json.loads(CAULDRON_STATE.read_text(encoding='utf-8'))
        endpoint = str(data.get('endpoint') or '').strip()
        return endpoint or None
    except Exception:
        return None


def cauldron_endpoint() -> str:
    explicit = str(os.environ.get('FORTRESS_CAULDRON_SSH') or '').strip()
    if explicit:
        return explicit
    cached = cached_cauldron_endpoint()
    if cached:
        return cached
    user = str(os.environ.get('FORTRESS_CAULDRON_USER') or 'dclar').strip() or 'dclar'
    hostname = str(os.environ.get('FORTRESS_CAULDRON_HOSTNAME') or 'THECAULDRON').strip() or 'THECAULDRON'
    port = int(os.environ.get('FORTRESS_CAULDRON_SSH_PORT') or '22')
    base = f'{user}@{hostname}'
    return base if port == 22 else f'{base}:{port}'


def configured_targets() -> dict[str, str | None]:
    return {
        "cauldron": cauldron_endpoint(),
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
        for receipt in receipts:
            mark = "OK" if receipt.callable else "FAIL"
            print(f"[{mark}] {receipt.target}: {receipt.state} endpoint={receipt.endpoint or '-'}")
            print(f"      {receipt.observed}")

    return 0 if all(receipt.callable for receipt in receipts) else 2


if __name__ == "__main__":
    raise SystemExit(main())
