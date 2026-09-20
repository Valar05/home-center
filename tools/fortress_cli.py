#!/usr/bin/env python3
"""Neutral deterministic Fortress CLI.

Read-only first slice. This CLI owns no persona and invokes no model.
It exposes current machine-shop health by delegating to existing
Home Center/Fortress health gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SSH_AXIS = ROOT / "tools" / "ssh_axis.py"
DEFAULT_WIKO_STATUS_URL = "https://thecauldron-2.tail574fdf.ts.net/brain/api/status"
SCHEMA = "fortress-cli-status-v1"


def source_sha256() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _load_json(text: str) -> dict[str, Any]:
    value = json.loads(text)
    if not isinstance(value, dict):
        raise ValueError("expected JSON object")
    return value


def cauldron_status(
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    if not SSH_AXIS.is_file():
        return {
            "surface": "cauldron",
            "ok": False,
            "state": "ssh_axis_missing",
            "detail": str(SSH_AXIS),
        }
    command = [sys.executable, str(SSH_AXIS), "check", "--target", "cauldron", "--json"]
    try:
        proc = runner(command, cwd=ROOT, text=True, capture_output=True, timeout=12)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "surface": "cauldron",
            "ok": False,
            "state": "ssh_axis_execution_failed",
            "detail": f"{exc.__class__.__name__}: {exc}",
        }

    try:
        payload = _load_json(proc.stdout)
        receipts = payload.get("ssh_axis") or []
        receipt = receipts[0] if isinstance(receipts, list) and receipts else {}
        if not isinstance(receipt, dict):
            receipt = {}
    except (ValueError, json.JSONDecodeError) as exc:
        return {
            "surface": "cauldron",
            "ok": False,
            "state": "ssh_axis_invalid_json",
            "rc": proc.returncode,
            "detail": f"{exc.__class__.__name__}: {exc}",
            "stderr": proc.stderr[-1000:],
        }

    return {
        "surface": "cauldron",
        "ok": bool(receipt.get("callable")) and proc.returncode == 0,
        "state": str(receipt.get("state") or "unknown"),
        "endpoint": receipt.get("endpoint"),
        "callable": bool(receipt.get("callable")),
        "transport_ok": bool(receipt.get("transport_ok")),
        "auth_ok": bool(receipt.get("auth_ok")),
        "command_ok": bool(receipt.get("command_ok")),
        "elapsed_ms": receipt.get("elapsed_ms"),
        "detail": receipt.get("observed"),
        "rc": proc.returncode,
    }


def _urlopen_json(url: str, timeout: float) -> tuple[int, dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": "fortress-cli/1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        status = int(getattr(response, "status", response.getcode()))
        payload = _load_json(response.read().decode("utf-8", errors="strict"))
        return status, payload


def wiko_status(
    opener: Callable[[str, float], tuple[int, dict[str, Any]]] = _urlopen_json,
) -> dict[str, Any]:
    url = str(os.environ.get("FORTRESS_WIKO_STATUS_URL") or DEFAULT_WIKO_STATUS_URL).strip()
    try:
        http_status, payload = opener(url, 8.0)
    except urllib.error.HTTPError as exc:
        return {
            "surface": "wiko",
            "ok": False,
            "state": "http_error",
            "url": url,
            "http": exc.code,
            "detail": str(exc),
        }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "surface": "wiko",
            "ok": False,
            "state": "unreachable",
            "url": url,
            "detail": f"{exc.__class__.__name__}: {exc}",
        }

    home_center = payload.get("home_center")
    ollama = payload.get("ollama")
    ready = http_status == 200 and home_center is True and ollama is True
    return {
        "surface": "wiko",
        "ok": ready,
        "state": "callable" if ready else "degraded",
        "url": url,
        "http": http_status,
        "home_center": home_center,
        "ollama": ollama,
        "model": payload.get("model"),
        "index": payload.get("index"),
        "source_hash": payload.get("source_hash"),
    }


def aggregate() -> dict[str, Any]:
    cauldron = cauldron_status()
    wiko = wiko_status()
    return {
        "schema": SCHEMA,
        "source_sha256": source_sha256(),
        "cauldron": cauldron,
        "wiko": wiko,
        "ok": bool(cauldron.get("ok")) and bool(wiko.get("ok")),
    }


def _human_surface(value: dict[str, Any]) -> str:
    surface = str(value.get("surface") or "surface")
    mark = "OK" if value.get("ok") else "FAIL"
    state = str(value.get("state") or "unknown")
    detail = []
    if value.get("endpoint"):
        detail.append(f"endpoint={value['endpoint']}")
    if value.get("http") is not None:
        detail.append(f"http={value['http']}")
    if surface == "wiko":
        detail.append(f"home_center={value.get('home_center')}")
        detail.append(f"ollama={value.get('ollama')}")
    suffix = " " + " ".join(detail) if detail else ""
    return f"[{mark}] {surface}: {state}{suffix}"


def emit(value: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
        return
    if "cauldron" in value and "wiko" in value:
        print(_human_surface(value["cauldron"]))
        print(_human_surface(value["wiko"]))
        print(f"[{'OK' if value.get('ok') else 'FAIL'}] fortress: {'callable' if value.get('ok') else 'degraded'}")
    else:
        print(_human_surface(value))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="fortress", description="Neutral deterministic Fortress command line")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--version", action="store_true")
    sub = parser.add_subparsers(dest="command")
    for name in ("status", "doctor", "cauldron", "wiko"):
        child = sub.add_parser(name)
        child.add_argument("--json", action="store_true", dest="child_json")
    args = parser.parse_args(argv)

    if args.version:
        print(f"fortress-cli-v1 sha256={source_sha256()}")
        return 0

    command = args.command or "status"
    as_json = bool(args.as_json or getattr(args, "child_json", False))

    if command == "cauldron":
        value = cauldron_status()
        emit(value, as_json)
        return 0 if value.get("ok") else 2

    if command == "wiko":
        value = wiko_status()
        emit(value, as_json)
        return 0 if value.get("ok") else 2

    value = aggregate()
    emit(value, as_json)
    if command == "doctor":
        return 0 if value.get("ok") else 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
