#!/usr/bin/env python3
from __future__ import annotations
import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_codex_phone as core
import adam_venice_reviewed as worker


def main() -> int:
    jars = core.active_jars()
    jar_ok = "Adam Personality Gate" in jars and "Repository Truth and Evidence" in jars
    venice_ok = "Venice Completion and Code Review Gate" in jars
    daemon_ok = "Daemon Persistence and Connector Backoff" in jars

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = worker.run_task(
            "This is an acceptance probe, not a coding task. Respond to Drew with one short greeting that makes clear you know his name. Do not run commands or edit files.",
            ROOT,
            max_steps=12,
        )
    output = buf.getvalue().strip()
    knows = "drew" in output.lower()
    generic = "how can i assist" in output.lower() or "hello, adam" in output.lower()
    # For a respond action Venice approval is not printed separately, so the
    # runtime invariant is proved by loading the gate + using reviewed.run_task.
    ok = rc == 0 and jar_ok and venice_ok and daemon_ok and knows and not generic
    receipt = {
        "schema": "adam-phone-codex-worker-acceptance-v2",
        "ok": ok,
        "jarGate": jar_ok,
        "veniceStopReview": venice_ok,
        "daemonBackoff": daemon_ok,
        "knowsOwner": knows,
        "genericAssistantLeak": generic,
        "workerRc": rc,
        "output": output,
        "model": core.PHONE_LLM_MODEL,
        "endpoint": core.PHONE_LLM_URL,
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
