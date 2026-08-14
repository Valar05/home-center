#!/usr/bin/env python3
"""Offline event-driven governor for ChatGPT scheduler orchestration.

The phone owns policy and health. ChatGPT is an actuator used only when local
state says a bounded scheduler transition is required. No hourly polling loop is
required: the governor reacts to context-sensor wake requests and backs off
locally after failed actuator attempts.

An actuator is deliberately external and explicit. Set HC_CHATGPT_SCHEDULER_ACTUATOR_CMD
once a proved Chromium/ChatGPT-shell controller exists. The command receives the
wake-request path as its final argument and must return JSON describing the
scheduler mutation/receipt. Until then the governor fails closed and preserves
the pending request rather than pretending ChatGPT was invoked.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

STATE_DIR = Path(os.environ.get("HC_SWARM_STATE_DIR", "~/.local/state/home-center/vlad-swarm")).expanduser()
CONTEXT_DIR = Path(os.environ.get("HC_CONTEXT_SENSOR_DIR", str(STATE_DIR / "context"))).expanduser()
WAKE_PATH = CONTEXT_DIR / "scheduler-wake-request.json"
GOVERNOR_STATE = CONTEXT_DIR / "scheduler-governor.json"
ACTUATOR_CMD = os.environ.get("HC_CHATGPT_SCHEDULER_ACTUATOR_CMD", "").strip()
MIN_RETRY = int(os.environ.get("HC_CHATGPT_ACTUATOR_MIN_RETRY_SECONDS", "15"))
MAX_RETRY = int(os.environ.get("HC_CHATGPT_ACTUATOR_MAX_RETRY_SECONDS", "900"))


def now() -> int:
    return int(time.time())


def read_json(path: Path) -> dict[str, Any]:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def atomic_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def invoke() -> dict[str, Any]:
    wake = read_json(WAKE_PATH)
    state = read_json(GOVERNOR_STATE)
    current = now()
    if not wake:
        result = {"schema": "fortress.scheduler-governor.v1", "state": "idle", "atEpoch": current}
        atomic_json(GOVERNOR_STATE, result)
        return result

    digest = str(wake.get("meaningfulDigest") or "")
    if digest and digest == state.get("lastAcceptedDigest"):
        try:
            WAKE_PATH.unlink()
        except FileNotFoundError:
            pass
        result = {**state, "state": "already_consumed", "atEpoch": current}
        atomic_json(GOVERNOR_STATE, result)
        return result

    retry_at = int(state.get("nextRetryEpoch") or 0)
    if current < retry_at:
        return {**state, "state": "backoff", "atEpoch": current}

    if not ACTUATOR_CMD:
        result = {
            "schema": "fortress.scheduler-governor.v1",
            "state": "actuator_unavailable",
            "atEpoch": current,
            "wakeDigest": digest,
            "wakeReasons": wake.get("reasons") or [],
            "pendingWakePath": str(WAKE_PATH),
            "requiredCapability": "HC_CHATGPT_SCHEDULER_ACTUATOR_CMD",
            "nextRetryEpoch": current + MAX_RETRY,
            "attempts": int(state.get("attempts") or 0),
        }
        atomic_json(GOVERNOR_STATE, result)
        return result

    attempts = int(state.get("attempts") or 0) + 1
    cmd = f"{ACTUATOR_CMD} {json.dumps(str(WAKE_PATH))}"
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True, timeout=120)
        payload: dict[str, Any]
        try:
            parsed = json.loads(p.stdout)
            payload = parsed if isinstance(parsed, dict) else {"stdout": p.stdout[-4000:]}
        except Exception:
            payload = {"stdout": p.stdout[-4000:], "stderr": p.stderr[-4000:]}
        ok = p.returncode == 0 and payload.get("ok", True) is not False
    except Exception as exc:
        p = None
        payload = {"error": f"{type(exc).__name__}: {exc}"}
        ok = False

    if ok:
        result = {
            "schema": "fortress.scheduler-governor.v1",
            "state": "actuated",
            "ok": True,
            "atEpoch": current,
            "attempts": attempts,
            "lastAcceptedDigest": digest,
            "wakeReasons": wake.get("reasons") or [],
            "actuatorReceipt": payload,
            "nextRetryEpoch": 0,
        }
        atomic_json(GOVERNOR_STATE, result)
        try:
            WAKE_PATH.unlink()
        except FileNotFoundError:
            pass
        return result

    delay = min(MAX_RETRY, max(MIN_RETRY, MIN_RETRY * (2 ** min(attempts - 1, 6))))
    result = {
        "schema": "fortress.scheduler-governor.v1",
        "state": "actuator_failed",
        "ok": False,
        "atEpoch": current,
        "attempts": attempts,
        "wakeDigest": digest,
        "wakeReasons": wake.get("reasons") or [],
        "actuatorReceipt": payload,
        "nextRetryEpoch": current + delay,
        "backoffSeconds": delay,
    }
    atomic_json(GOVERNOR_STATE, result)
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description="Fortress event-driven ChatGPT scheduler governor")
    ap.add_argument("--pretty", action="store_true")
    args = ap.parse_args()
    result = invoke()
    print(json.dumps(result, indent=2 if args.pretty else None, sort_keys=True))
    return 0 if result.get("state") not in {"actuator_failed"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
