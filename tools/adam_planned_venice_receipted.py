#!/usr/bin/env python3
"""Receipt-enforced Adam planner and executor.

This is the canonical wrapper around adam_planned_venice. It keeps the existing
research -> plan -> selected Jars -> antagonism -> Venice -> execution flow, but
routes Jar discovery through the shared Vlad/Home Center registry and emits one
usage receipt per Jar every time Jar context produces an output.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_planned_venice as base
import judgement_jar_runtime as jar_runtime

execution = base.execution
_ORIGINAL_VALIDATE = base.validate_plan_packet
_ORIGINAL_PLANNING_SYSTEM = base.planning_system
_ORIGINAL_PLAN_REVIEW = base.review_plan_phone
_ORIGINAL_COMPLETION_REVIEW = execution.canonical_venice_review
_catalog_sync_attempted = False


def _receipt_ids(results: list[dict]) -> list[str]:
    return [str(item.get("receipt", {}).get("receiptId") or "") for item in results]


def _delivery_states(results: list[dict]) -> list[str]:
    return [str(item.get("homeCenter", {}).get("state") or "PENDING") for item in results]


def jar_catalog() -> list[dict]:
    global _catalog_sync_attempted
    values = jar_runtime.catalog(include_text=False)
    if not _catalog_sync_attempted:
        jar_runtime.sync_pending()
        jar_runtime.sync_catalog(values)
        _catalog_sync_attempted = True
    return values


def selected_jar_text(selected: list[str]) -> tuple[str, list[dict]]:
    docs: list[str] = []
    manifest: list[dict] = []
    seen: set[str] = set()
    for raw in selected:
        item = jar_runtime.resolve_jar(str(raw or ""), include_text=True)
        path = str(item["path"])
        if path in seen:
            continue
        seen.add(path)
        docs.append(f"\n--- SELECTED JAR {path} ---\n{item.get('text') or ''}")
        manifest.append({key: item[key] for key in ("id", "order", "title", "path", "filename", "sha256", "bytes")})
    if not manifest:
        raise RuntimeError("planning selected no Judgment Jars")
    return "".join(docs), manifest


def validate_plan_packet(action: dict) -> tuple[bool, str]:
    ok, error = _ORIGINAL_VALIDATE(action)
    if not ok:
        return ok, error
    output_kind = str(action.get("outputKind") or "").strip()
    if output_kind not in jar_runtime.OUTPUT_KINDS:
        return False, "outputKind must be one of: " + ", ".join(sorted(jar_runtime.OUTPUT_KINDS))
    return True, ""


def planning_system(task: str, workspace: Path) -> str:
    original = _ORIGINAL_PLANNING_SYSTEM(task, workspace)
    return original + f"""

JUDGMENT JAR RECEIPT CONTRACT:
- Every Jar use produces an append-only receipt through the shared Vlad/Home Center runtime.
- `submit_plan` MUST include `outputKind`, naming the actual class of output this task is expected to create.
- Allowed outputKind values: {json.dumps(sorted(jar_runtime.OUTPUT_KINDS))}
- Omitted, invented, or vague output kinds fail the plan packet.
- Output kind is not capability state. A requested artifact can still end with status blocked or partial.

Canonical submit_plan addition:
{{"outputKind":"plan|decision|code_change|artifact|answer|analysis|routing_action|test_result|review_verdict|handoff|memory_update|execution_result|blocker|no_change|mixed"}}
"""


def review_plan_phone(task: str, workspace: Path, packet: dict, attempts: int = 4) -> dict:
    review = _ORIGINAL_PLAN_REVIEW(task, workspace, packet, attempts)
    selected = list(packet.get("selectedJars") or [])
    output_text = str(review.get("reviewText") or "")
    results = jar_runtime.record_many(
        selected,
        output_kind="review_verdict",
        output_summary=f"Venice pre-execution Jar review produced {review.get('directive') or 'UNKNOWN'}.",
        source="adam.preflight.venice-plan-review",
        status="allowed" if review.get("planPermissionGranted") else "blocked",
        input_text=json.dumps(packet, ensure_ascii=False, sort_keys=True),
        output_text=output_text,
        request_id=str(packet.get("planSha256") or uuid.uuid4()),
        output_refs=[str(review.get("receipt") or "")],
        metadata={
            "phase": "pre_execution",
            "verdict": review.get("verdict"),
            "directive": review.get("directive"),
            "plannedOutputKind": packet.get("outputKind"),
        },
    )
    review["jarUsageReceiptIds"] = _receipt_ids(results)
    review["jarUsageHomeCenterStates"] = _delivery_states(results)
    review["plannedOutputKind"] = packet.get("outputKind")
    return review


def completion_review(task: str, workspace: Path, proposal: dict, jars: str, recent_messages: list[dict], task_base_commit: str | None, attempts: int = 4) -> dict:
    review = _ORIGINAL_COMPLETION_REVIEW(task, workspace, proposal, jars, recent_messages, task_base_commit, attempts)
    results = jar_runtime.record_many(
        [item["path"] for item in jar_catalog()],
        output_kind="review_verdict",
        output_summary=f"Venice completion review produced {review.get('directive') or 'UNKNOWN'}.",
        source="adam.completion.venice-review",
        status="allowed" if review.get("stopPermissionGranted") else "blocked",
        input_text=json.dumps(proposal, ensure_ascii=False, sort_keys=True),
        output_text=str(review.get("reviewText") or ""),
        request_id=str(review.get("receipt") or uuid.uuid4()),
        output_refs=[str(review.get("receipt") or "")],
        metadata={
            "phase": "completion",
            "verdict": review.get("verdict"),
            "directive": review.get("directive"),
            "codeReviewFirst": review.get("codeReviewFirst") is True,
        },
    )
    review["jarUsageReceiptIds"] = _receipt_ids(results)
    review["jarUsageHomeCenterStates"] = _delivery_states(results)
    return review


def run_task(task: str, workspace: Path, planning_stop_after_steps: int | None = None, execution_stop_after_steps: int | None = None) -> int:
    gate = base.preflight(task, workspace, planning_stop_after_steps)
    packet, review = gate["packet"], gate["review"]
    output_kind = str(packet.get("outputKind") or "").strip()
    selected = list(packet.get("selectedJars") or [])
    enriched = (
        task
        + "\n\nPRE-EXECUTION PLAN APPROVED BY VENICE. Preserve it unless material state changes; if a material assumption fails, stop mutation and replan."
        + "\nPLAN_RECEIPT: " + str(review.get("receipt"))
        + "\nSELECTED_JARS: " + json.dumps(selected, ensure_ascii=False)
        + "\nPLANNED_OUTPUT_KIND: " + output_kind
        + "\nPLAN: " + json.dumps(packet.get("plan") or [], ensure_ascii=False)
        + "\nANTAGONISM: " + json.dumps(packet.get("antagonism") or [], ensure_ascii=False)
        + "\nDONE_CONDITION: " + str(packet.get("doneCondition") or "")
        + "\nEVIDENCE_STANDARD: " + str(packet.get("evidenceStandard") or "")
        + "\nJAR_RECEIPT_RULE: every Jar-governed terminal output must preserve its output kind and receipt identifiers."
    )
    result_code = execution.run_task(enriched, workspace, stop_after_steps=execution_stop_after_steps)
    completion_path = execution.STATE_DIR / "venice-review-last.json"
    results = jar_runtime.record_many(
        [item["path"] for item in jar_catalog()],
        output_kind=output_kind,
        output_summary=f"Jar-governed Adam task produced output kind {output_kind} with exit code {result_code}.",
        source="adam.task.output",
        status="completed" if result_code == 0 else "blocked" if result_code == 2 else "partial",
        input_text=task,
        output_text=json.dumps({
            "exitCode": result_code,
            "plannedOutputKind": output_kind,
            "selectedJars": selected,
            "planReceipt": review.get("receipt"),
            "completionReceipt": str(completion_path),
        }, ensure_ascii=False, sort_keys=True),
        request_id=str(review.get("receipt") or uuid.uuid4()),
        output_refs=[str(review.get("receipt") or ""), str(completion_path)],
        metadata={
            "phase": "terminal_output",
            "selectedForPlan": selected,
            "allBindingJarsLoaded": True,
            "exitCode": result_code,
        },
    )
    print(json.dumps({
        "schema": "adam-judgement-jar-output-receipts.v1",
        "outputKind": output_kind,
        "receiptIds": _receipt_ids(results),
        "homeCenterStates": _delivery_states(results),
    }, ensure_ascii=False, sort_keys=True))
    return result_code


base.jar_catalog = jar_catalog
base.selected_jar_text = selected_jar_text
base.validate_plan_packet = validate_plan_packet
base.planning_system = planning_system
base.review_plan_phone = review_plan_phone
base.run_task = run_task
execution.canonical_venice_review = completion_review


def main(argv=None) -> int:
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
