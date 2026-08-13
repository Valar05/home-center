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
import adam_venice_reviewed as execution
import adam_planned_venice_receipted as worker

PROBE = "This is an acceptance probe, not a coding task. Respond to Drew with one short greeting that makes clear you know his name. Do not run commands or edit files."


class AcceptanceTimeout(BaseException):
    """Explicit bounded-test cancellation; production daemon retries do not catch it."""


def _timeout(_signum, _frame):
    raise AcceptanceTimeout("acceptance probe exceeded its bounded harness window")


def read_json(path: Path) -> dict:
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def main() -> int:
    jars = core.active_jars()
    jar_ok = "Adam Personality Gate" in jars and "Repository Truth and Evidence" in jars
    venice_ok = "Venice Completion and Code Review Gate" in jars
    daemon_ok = "Daemon Persistence and Connector Backoff" in jars
    try:
        codex_docs, loaded = execution.codex_local_documents(ROOT)
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

    plan_review = worker.base.PLAN_LAST
    stop_review = execution.STATE_DIR / "venice-review-last.json"
    for path in (plan_review, stop_review):
        try:
            path.unlink()
        except FileNotFoundError:
            pass

    buf = io.StringIO()
    rc = 99
    timed_out = False
    old_handler = signal.signal(signal.SIGALRM, _timeout)
    signal.alarm(max(30, int(os.environ.get("HC_ADAM_ACCEPT_TIMEOUT", "360"))))
    try:
        with contextlib.redirect_stdout(buf):
            rc = worker.run_task(PROBE, ROOT, planning_stop_after_steps=12, execution_stop_after_steps=12)
    except AcceptanceTimeout as exc:
        timed_out = True
        buf.write(f"{exc}\n")
        rc = 3
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)

    output = buf.getvalue().strip()
    knows = "drew" in output.lower()
    generic = "how can i assist" in output.lower() or "hello, adam" in output.lower()
    terminal_receipt = "adam-judgment-jar-output-receipts.v1" in output
    plan_receipt = read_json(plan_review)
    stop_receipt = read_json(stop_review)
    task_hash = hashlib.sha256(PROBE.encode("utf-8")).hexdigest()
    plan_receipt_ok = (
        plan_receipt.get("schema") == "adam-venice-plan-review-v1"
        and plan_receipt.get("taskSha256") == task_hash
        and plan_receipt.get("planPermissionGranted") is True
        and plan_receipt.get("externalReviewGateSatisfied") is True
        and plan_receipt.get("directive") == "PLAN_ALLOWED"
        and bool(plan_receipt.get("selectedJars"))
        and bool(plan_receipt.get("antagonism"))
        and bool(plan_receipt.get("researchSummary"))
        and bool(plan_receipt.get("outputKind"))
        and bool(plan_receipt.get("selectedJarContextUsageReceiptIds"))
        and bool(plan_receipt.get("jarUsageReceiptIds"))
    )
    stop_receipt_ok = (
        stop_receipt.get("schema") == "adam-venice-stop-review-v1"
        and stop_receipt.get("stopPermissionGranted") is True
        and stop_receipt.get("externalReviewGateSatisfied") is True
        and stop_receipt.get("directive") == "STOP_ALLOWED"
        and PROBE in str(stop_receipt.get("task") or "")
        and bool(stop_receipt.get("jarUsageReceiptIds"))
    )
    ok = (
        rc == 0 and not timed_out and jar_ok and venice_ok and daemon_ok and codex_ok
        and plan_receipt_ok and stop_receipt_ok and terminal_receipt and knows and not generic
    )
    receipt = {
        "schema": "adam-phone-codex-worker-acceptance-v9-judgment-jar-usage-receipts",
        "ok": ok,
        "jarGate": jar_ok,
        "judgmentJarUsageReceipts": True,
        "judgmentJarOutputKindRequired": bool(plan_receipt.get("outputKind")),
        "venicePlanReview": True,
        "venicePlanReviewReceipt": str(plan_review),
        "venicePlanReviewReceiptVerified": plan_receipt_ok,
        "venicePlanDirective": plan_receipt.get("directive"),
        "selectedJudgmentJars": plan_receipt.get("selectedJars") or [],
        "selectedJarContextUsageReceiptIds": plan_receipt.get("selectedJarContextUsageReceiptIds") or [],
        "planReviewJarUsageReceiptIds": plan_receipt.get("jarUsageReceiptIds") or [],
        "planReviewJarUsageHomeCenterStates": plan_receipt.get("jarUsageHomeCenterStates") or [],
        "veniceStopReview": venice_ok,
        "veniceStopReviewReceipt": str(stop_review),
        "veniceStopReviewReceiptVerified": stop_receipt_ok,
        "veniceStopDirective": stop_receipt.get("directive"),
        "stopReviewJarUsageReceiptIds": stop_receipt.get("jarUsageReceiptIds") or [],
        "stopReviewJarUsageHomeCenterStates": stop_receipt.get("jarUsageHomeCenterStates") or [],
        "terminalJarUsageReceiptVerified": terminal_receipt,
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
