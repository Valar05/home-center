#!/usr/bin/env python3
from __future__ import annotations
import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_codex_phone as worker


def main() -> int:
    jars = worker.active_jars()
    jar_ok = "Adam Personality Gate" in jars and "Repository Truth and Evidence" in jars

    # Live worker proof. The local model may need several correction turns, but
    # raw prose is suppressed by run_task; only a governed respond/finish may
    # reach stdout.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = worker.run_task(
            "This is an acceptance probe, not a coding task. Respond to Drew with one short greeting that makes clear you know his name. Do not run commands or edit files.",
            ROOT,
            max_steps=8,
        )
    output = buf.getvalue().strip()
    knows = "drew" in output.lower()
    generic = "how can i assist" in output.lower() or "hello, adam" in output.lower()
    ok = rc == 0 and jar_ok and knows and not generic
    receipt = {
        "schema": "adam-phone-codex-worker-acceptance-v1",
        "ok": ok,
        "jarGate": jar_ok,
        "knowsOwner": knows,
        "genericAssistantLeak": generic,
        "workerRc": rc,
        "output": output,
        "model": worker.PHONE_LLM_MODEL,
        "endpoint": worker.PHONE_LLM_URL,
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
