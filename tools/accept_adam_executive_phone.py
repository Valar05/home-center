#!/usr/bin/env python3
from __future__ import annotations
import contextlib
import hashlib
import io
import json
import os
import signal
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_codex_phone as core
import adam_venice_reviewed as worker

PROBE = "This is an acceptance probe, not a coding task. Respond to Drew with one short greeting that makes clear you know his name. Do not run commands or edit files."


def _timeout(_signum, _frame):
    raise TimeoutError("acceptance probe exceeded its bounded harness window")


def main() -> int:
    jars = core.active_jars()
    jar_ok = "Adam Personality Gate" in jars and "Repository Truth and Evidence" in jars
    venice_ok = "Venice Completion and Code Review Gate" in jars
    daemon_ok = "Daemon Persistence and Connector Backoff" in jars
    try:
        codex_docs, loaded = worker.codex_local_documents(ROOT)
        required = {"AGENTS.md", "MEMORIES.md", "SKILLS.md"}
        codex_ok = required.issubset(set(loaded)) and all(token in codex_docs for token in (
            "Repository Agent Instructions",
            "Codex Local Memory",
            "Codex Local Skills",
            "Agent Handoff And Session Memory",
        ))
    except Exception:
        loaded = []
        codex_ok = False

    # Delete only the last-pointer so stale Venice proof cannot satisfy this run.
    last_review = worker.STATE_DIR / "venice-review-last.json"
    try:
        last_review.unlink()
    except FileNotFoundError:
        pass

    buf = io.StringIO()
    rc = 99
    timed_out = False
    old_handler = signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(max(30, int(os.environ.get("HC_ADAM_ACCEPT_TIMEOUT", "240"))))
    try:
        with contextlib.redirect_stdout(buf):
            rc = worker.run_task(PROBE, ROOT, max_steps=8, stop_after_steps=12)
    except TimeoutError as exc:
        timed_out = True
        buf.write(f"{exc}\n")
        rc = 3
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    output = buf.getvalue().strip()
    knows = "drew" in output.lower()
    generic = "how can i assist" in output.lower() or "hello, adam" in output.lower()
    try:
        venice_receipt = json.loads(last_review.read_text(encoding="utf-8"))
    except Exception:
        venice_receipt = {}
    venice_receipt_ok = (
        venice_receipt.get("schema") == "adam-venice-stop-review-v1"
        and venice_receipt.get("taskSha256") == hashlib.sha256(PROBE.encode("utf-8")).hexdigest()
        and venice_receipt.get("stopPermissionGranted") is True
        and venice_receipt.get("externalReviewGateSatisfied") is True
        and venice_receipt.get("directive") == "STOP_ALLOWED"
    )
    ok = rc == 0 and not timed_out and jar_ok and venice_ok and daemon_ok and codex_ok and venice_receipt_ok and knows and not generic
    receipt = {
        "schema": "adam-phone-codex-worker-acceptance-v6",
        "ok": ok,
        "jarGate": jar_ok,
        "veniceStopReview": venice_ok,
        "veniceReviewReceipt": str(last_review),
        "veniceReviewReceiptVerified": venice_receipt_ok,
        "veniceDirective": venice_receipt.get("directive"),
        "daemonBackoff": daemon_ok,
        "codexLocalDocs": loaded,
        "codexLocalDocsLoaded": codex_ok,
        "knowsOwner": knows,
        "genericAssistantLeak": generic,
        "timedOut": timed_out,
        "workerRc": rc,
        "output": output,
        "model": core.PHONE_LLM_MODEL,
        "endpoint": core.PHONE_LLM_URL,
    }
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
