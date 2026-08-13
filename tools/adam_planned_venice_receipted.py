#!/usr/bin/env python3
"""Receipt-enforced Adam planner and executor.

This wraps the canonical research -> plan -> selected Jars -> antagonism ->
Venice -> execution flow. It adds no second registry: every Jar resolves through
`judgment_jar_registry.py`, and every actual context load, review application,
and governed terminal output emits one typed usage receipt.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import adam_planned_venice as base  # noqa: E402
import judgment_jar_receipts as usage  # noqa: E402
from judgment_jar_common import CONFIG_PATH, DEFAULT_CACHE, LOCAL_ORIGIN, RegistryError, read_config  # noqa: E402
from judgment_jar_registry import ensure_registry, resolve_jar  # noqa: E402

execution = base.execution
_ORIGINAL_SELECTED_JAR_TEXT = base.selected_jar_text
_ORIGINAL_VALIDATE = base.validate_plan_packet
_ORIGINAL_PLANNING_SYSTEM = base.planning_system
_ORIGINAL_PLAN_REVIEW = base.review_plan_phone
_ORIGINAL_PERSIST_PLAN_REVIEW = base.persist_plan_review
_ORIGINAL_ACTIVE_JARS = execution.worker.active_jars
_ORIGINAL_COMPLETION_REVIEW = execution.canonical_venice_review

_CURRENT_SELECTED_JARS: list[dict[str, Any]] = []
_CURRENT_ACTIVE_JARS: list[dict[str, Any]] = []
_CURRENT_OUTPUT_KIND = "mixed"


def registry_state() -> tuple[dict[str, Any], dict[str, Any]]:
    config = read_config(CONFIG_PATH)
    registry, _ = ensure_registry(ROOT, DEFAULT_CACHE, config_path=CONFIG_PATH)
    return registry, config


def allowed_output_kinds(config: dict[str, Any]) -> frozenset[str]:
    values = [str(value) for value in (config.get("receipts") or {}).get("outputKinds") or [] if str(value).strip()]
    if not values:
        raise RegistryError("Judgment Jar receipt outputKinds are unavailable")
    return frozenset(values)


def resolve_required(registry: dict[str, Any], reference: str | dict[str, Any]) -> dict[str, Any]:
    key = str(reference.get("id") or reference.get("sourcePath") or "") if isinstance(reference, dict) else str(reference or "")
    jar = resolve_jar(registry, key)
    if jar is None:
        jar = next((item for item in registry.get("jars") or [] if key in {str(item.get("id") or ""), str(item.get("sourcePath") or ""), str(item.get("title") or "")}), None)
    if jar is None:
        raise RegistryError(f"unknown Judgment Jar: {reference}")
    return jar


def refs(jar: dict[str, Any]) -> list[str]:
    return [str(value) for value in (jar.get("sourcePath"), jar.get("sourceUrl"), jar.get("sourceFileId")) if value]


def record_one(
    registry: dict[str, Any],
    config: dict[str, Any],
    jar: dict[str, Any],
    *,
    output_kind: str,
    output_text: str,
    summary: str,
    intent: str,
    action: str,
    source: str,
    input_text: str = "",
    output_status: str = "created",
    request_id: str = "",
    group_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = usage.record(
        registry,
        jar,
        config,
        output_kind=output_kind,
        output_text=output_text,
        summary=summary,
        actor="Adam",
        intent=intent,
        surface="jar",
        decision_action=action,
        input_text=input_text,
        output_status=output_status,
        request_id=request_id,
        group_id=group_id,
        references=refs(jar),
        source=source,
        metadata=dict(metadata or {}),
    )
    if result.get("ok") is not True or not (result.get("receipt") or {}).get("receiptId"):
        raise usage.ReceiptError(f"Judgment Jar usage receipt capture failed: {result}")
    return result


def record_many(
    registry: dict[str, Any],
    config: dict[str, Any],
    jars: Iterable[dict[str, Any]],
    **kwargs: Any,
) -> list[dict[str, Any]]:
    group_id = str(kwargs.pop("group_id", "") or kwargs.get("request_id") or uuid.uuid4())
    request_id = str(kwargs.pop("request_id", "") or group_id)
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for jar in jars:
        current = resolve_required(registry, jar)
        jar_id = str(current.get("id") or "")
        if jar_id in seen:
            continue
        seen.add(jar_id)
        results.append(record_one(registry, config, current, request_id=request_id, group_id=group_id, **kwargs))
    if not results:
        raise RegistryError("at least one Judgment Jar is required for usage receipt capture")
    return results


def receipt_ids(results: list[dict[str, Any]]) -> list[str]:
    return [str(result["receipt"]["receiptId"]) for result in results]


def receipt_states(results: list[dict[str, Any]]) -> list[str]:
    return [str(result.get("state") or "CAPTURED") for result in results]


def selected_jar_text(selected: list[str]) -> tuple[str, list[dict]]:
    global _CURRENT_SELECTED_JARS
    text, manifest = _ORIGINAL_SELECTED_JAR_TEXT(selected)
    registry, config = registry_state()
    selected_jars: list[dict[str, Any]] = []
    enriched: list[dict[str, Any]] = []
    group_id = str(uuid.uuid4())
    for item in manifest:
        jar = resolve_required(registry, str(item.get("path") or ""))
        source_path = ROOT / str(item.get("path") or "")
        jar_text = source_path.read_text(encoding="utf-8", errors="replace")
        result = record_one(
            registry,
            config,
            jar,
            output_kind="context_packet",
            output_text=jar_text,
            summary=f"Adam loaded selected Judgment Jar context: {jar.get('title') or jar.get('id')}",
            intent="load selected Judgment Jar context for pre-execution planning",
            action="selected Jar for the bounded plan and Venice review",
            source="adam.preflight.selected-jar-context",
            input_text=str(item.get("path") or ""),
            group_id=group_id,
            metadata={"phase": "pre_execution", "selection": "planner"},
        )
        enriched.append({
            **item,
            "jarId": jar.get("id"),
            "origin": jar.get("origin"),
            "sourceAuthority": jar.get("sourceAuthority"),
            "usageReceiptId": result["receipt"]["receiptId"],
            "usageReceiptState": result.get("state"),
        })
        selected_jars.append(jar)
    _CURRENT_SELECTED_JARS = selected_jars
    return text, enriched


def validate_plan_packet(action: dict) -> tuple[bool, str]:
    ok, error = _ORIGINAL_VALIDATE(action)
    if not ok:
        return ok, error
    output_kind = str(action.get("outputKind") or "").strip()
    try:
        allowed = allowed_output_kinds(read_config(CONFIG_PATH))
    except Exception as exc:
        return False, f"Judgment Jar receipt taxonomy unavailable: {exc}"
    if output_kind not in allowed:
        return False, "outputKind must be one of: " + ", ".join(sorted(allowed))
    return True, ""


def planning_system(task: str, workspace: Path) -> str:
    original = _ORIGINAL_PLANNING_SYSTEM(task, workspace)
    allowed = sorted(allowed_output_kinds(read_config(CONFIG_PATH)))
    return original + f"""

JUDGMENT JAR USAGE RECEIPT CONTRACT
- `submit_plan` MUST include `outputKind`, naming what the governed task is expected to create.
- Allowed outputKind values: {json.dumps(allowed)}
- Every selected Jar context load, Jar-governed review, and terminal governed output receives one append-only per-Jar usage receipt.
- Output kind describes material produced. It never promotes requested work into deployed, delivered, or accepted capability.
- Missing or invented outputKind fails the plan packet.
"""


def augment_json(path_value: str | Path | None, additions: dict[str, Any]) -> None:
    if not path_value:
        return
    path = Path(path_value).expanduser()
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    current.update(additions)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(current, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temp.replace(path)


def persist_plan_review(task: str, packet: dict, review: dict) -> Path:
    path = _ORIGINAL_PERSIST_PLAN_REVIEW(task, packet, review)
    manifest = review.get("selectedJarManifest") or []
    augment_json(path, {
        "outputKind": packet.get("outputKind"),
        "selectedJarContextUsageReceiptIds": [item.get("usageReceiptId") for item in manifest if item.get("usageReceiptId")],
        "selectedJarContextUsageReceiptStates": [item.get("usageReceiptState") for item in manifest if item.get("usageReceiptState")],
    })
    return path


def review_plan_phone(task: str, workspace: Path, packet: dict, attempts: int = 4) -> dict:
    review = _ORIGINAL_PLAN_REVIEW(task, workspace, packet, attempts)
    registry, config = registry_state()
    selected = [resolve_required(registry, reference) for reference in packet.get("selectedJars") or []]
    results = record_many(
        registry,
        config,
        selected,
        output_kind="review_verdict",
        output_text=str(review.get("reviewText") or ""),
        summary=f"Venice pre-execution Judgment Jar review produced {review.get('directive') or 'UNKNOWN'}.",
        intent="apply selected Judgment Jars to the pre-execution plan",
        action="issued Venice plan-review verdict",
        source="adam.preflight.venice-plan-review",
        input_text=json.dumps(packet, ensure_ascii=False, sort_keys=True),
        output_status="allowed" if review.get("planPermissionGranted") else "blocked",
        request_id=str(packet.get("planSha256") or uuid.uuid4()),
        metadata={"phase": "pre_execution", "verdict": review.get("verdict"), "directive": review.get("directive"), "plannedOutputKind": packet.get("outputKind")},
    )
    review["jarUsageReceiptIds"] = receipt_ids(results)
    review["jarUsageReceiptStates"] = receipt_states(results)
    review["plannedOutputKind"] = packet.get("outputKind")
    augment_json(review.get("receipt"), {
        "outputKind": packet.get("outputKind"),
        "jarUsageReceiptIds": review["jarUsageReceiptIds"],
        "jarUsageReceiptStates": review["jarUsageReceiptStates"],
    })
    return review


def active_local_jars(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return [jar for jar in registry.get("jars") or [] if jar.get("origin") == LOCAL_ORIGIN and jar.get("status") == "active"]


def active_jars_receipted() -> str:
    global _CURRENT_ACTIVE_JARS
    text = _ORIGINAL_ACTIVE_JARS()
    registry, config = registry_state()
    selected = active_local_jars(registry)
    results = record_many(
        registry,
        config,
        selected,
        output_kind="context_packet",
        output_text=text,
        summary="Adam loaded the active operational Judgment Jar context.",
        intent="load active operational Judgment Jars for governed execution",
        action="included active Jars in the execution context",
        source="adam.execution.active-jar-context",
        input_text="active operational Judgment Jars",
        metadata={"phase": "execution", "selection": "active-operational-core"},
    )
    _CURRENT_ACTIVE_JARS = selected
    return text + "\n\nJAR_CONTEXT_USAGE_RECEIPTS: " + json.dumps({"receiptIds": receipt_ids(results), "states": receipt_states(results)}, ensure_ascii=False)


def governing_jars(registry: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    seen: set[str] = set()
    for jar in [*_CURRENT_ACTIVE_JARS, *_CURRENT_SELECTED_JARS]:
        current = resolve_required(registry, jar)
        jar_id = str(current.get("id") or "")
        if jar_id not in seen:
            values.append(current)
            seen.add(jar_id)
    return values or active_local_jars(registry)


def completion_review(task: str, workspace: Path, proposal: dict, jars: str, recent_messages: list[dict], task_base_commit: str | None, attempts: int = 4) -> dict:
    review = _ORIGINAL_COMPLETION_REVIEW(task, workspace, proposal, jars, recent_messages, task_base_commit, attempts)
    registry, config = registry_state()
    results = record_many(
        registry,
        config,
        governing_jars(registry),
        output_kind="review_verdict",
        output_text=str(review.get("reviewText") or ""),
        summary=f"Venice completion Judgment Jar review produced {review.get('directive') or 'UNKNOWN'}.",
        intent="apply governing Judgment Jars to the completion claim",
        action="issued Venice stop/continue verdict",
        source="adam.completion.venice-review",
        input_text=json.dumps(proposal, ensure_ascii=False, sort_keys=True),
        output_status="allowed" if review.get("stopPermissionGranted") else "blocked",
        request_id=str(review.get("receipt") or uuid.uuid4()),
        metadata={"phase": "completion", "verdict": review.get("verdict"), "directive": review.get("directive"), "codeReviewFirst": review.get("codeReviewFirst") is True},
    )
    review["jarUsageReceiptIds"] = receipt_ids(results)
    review["jarUsageReceiptStates"] = receipt_states(results)
    augment_json(review.get("receipt"), {"jarUsageReceiptIds": review["jarUsageReceiptIds"], "jarUsageReceiptStates": review["jarUsageReceiptStates"]})
    return review


def run_task(task: str, workspace: Path, planning_stop_after_steps: int | None = None, execution_stop_after_steps: int | None = None) -> int:
    global _CURRENT_OUTPUT_KIND, _CURRENT_SELECTED_JARS, _CURRENT_ACTIVE_JARS
    gate = base.preflight(task, workspace, planning_stop_after_steps)
    packet, review = gate["packet"], gate["review"]
    _CURRENT_OUTPUT_KIND = str(packet.get("outputKind") or "mixed")
    registry, _ = registry_state()
    _CURRENT_SELECTED_JARS = [resolve_required(registry, reference) for reference in packet.get("selectedJars") or []]
    enriched = (
        task
        + "\n\nPRE-EXECUTION PLAN APPROVED BY VENICE. Preserve it unless material state changes; if a material assumption fails, stop mutation and replan."
        + "\nPLAN_RECEIPT: " + str(review.get("receipt"))
        + "\nSELECTED_JARS: " + json.dumps(packet.get("selectedJars") or [], ensure_ascii=False)
        + "\nPLANNED_OUTPUT_KIND: " + _CURRENT_OUTPUT_KIND
        + "\nPLAN_JAR_USAGE_RECEIPTS: " + json.dumps(review.get("jarUsageReceiptIds") or [], ensure_ascii=False)
        + "\nPLAN: " + json.dumps(packet.get("plan") or [], ensure_ascii=False)
        + "\nANTAGONISM: " + json.dumps(packet.get("antagonism") or [], ensure_ascii=False)
        + "\nDONE_CONDITION: " + str(packet.get("doneCondition") or "")
        + "\nEVIDENCE_STANDARD: " + str(packet.get("evidenceStandard") or "")
    )
    try:
        result_code = execution.run_task(enriched, workspace, stop_after_steps=execution_stop_after_steps)
        registry, config = registry_state()
        completion_path = execution.STATE_DIR / "venice-review-last.json"
        results = record_many(
            registry,
            config,
            governing_jars(registry),
            output_kind=_CURRENT_OUTPUT_KIND,
            output_text=json.dumps({"exitCode": result_code, "planReceipt": review.get("receipt"), "completionReceipt": str(completion_path)}, ensure_ascii=False, sort_keys=True),
            summary=f"Jar-governed Adam task produced {_CURRENT_OUTPUT_KIND} with exit code {result_code}.",
            intent="record the terminal material produced by the governed task",
            action="classified and captured the task output",
            source="adam.task.output",
            input_text=task,
            output_status="completed" if result_code == 0 else "blocked" if result_code == 2 else "partial",
            request_id=str(review.get("receipt") or uuid.uuid4()),
            metadata={"phase": "terminal_output", "exitCode": result_code, "selectedJarIds": [jar.get("id") for jar in _CURRENT_SELECTED_JARS], "activeJarIds": [jar.get("id") for jar in _CURRENT_ACTIVE_JARS]},
        )
        print(json.dumps({"schema": "adam-judgment-jar-output-receipts.v1", "outputKind": _CURRENT_OUTPUT_KIND, "receiptIds": receipt_ids(results), "states": receipt_states(results)}, ensure_ascii=False, sort_keys=True))
        return result_code
    finally:
        _CURRENT_SELECTED_JARS = []
        _CURRENT_ACTIVE_JARS = []
        _CURRENT_OUTPUT_KIND = "mixed"


base.selected_jar_text = selected_jar_text
base.validate_plan_packet = validate_plan_packet
base.planning_system = planning_system
base.persist_plan_review = persist_plan_review
base.review_plan_phone = review_plan_phone
base.run_task = run_task
execution.worker.active_jars = active_jars_receipted
execution.canonical_venice_review = completion_review


def main(argv=None) -> int:
    return base.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
