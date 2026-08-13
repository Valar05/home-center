#!/usr/bin/env python3
"""Receipt-enforced Adam planner and executor.

This wraps the canonical research -> plan -> selected Jars -> antagonism ->
Venice -> execution flow without creating another Jar registry. Every actual
Jar context load, review use, and terminal governed output emits one usage
receipt with a controlled output kind through Atom/Home Center.
"""
from __future__ import annotations

import json
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import adam_planned_venice as base  # noqa: E402
import judgment_jar_receipts as usage  # noqa: E402
from judgment_jar_common import (  # noqa: E402
    CONFIG_PATH, DEFAULT_CACHE, LOCAL_ORIGIN, RegistryError, read_config,
)
from judgment_jar_registry import (  # noqa: E402
    ensure_registry, fetch_native_source, public_jar, resolve_jar,
)

execution = base.execution
_ORIGINAL_VALIDATE = base.validate_plan_packet
_ORIGINAL_PLANNING_SYSTEM = base.planning_system
_ORIGINAL_PLAN_REVIEW = base.review_plan_phone
_ORIGINAL_PERSIST_PLAN_REVIEW = base.persist_plan_review
_ORIGINAL_COMPLETION_REVIEW = execution.canonical_venice_review
_ORIGINAL_ACTIVE_JARS = execution.worker.active_jars

_CURRENT_SELECTED_JARS: list[dict[str, Any]] = []
_CURRENT_SELECTED_TEXT = ""
_CURRENT_OUTPUT_KIND = "mixed"
_CURRENT_ACTIVE_JARS: list[dict[str, Any]] = []


def registry_state() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    config = read_config(CONFIG_PATH)
    registry, sync = ensure_registry(ROOT, DEFAULT_CACHE, config_path=CONFIG_PATH)
    return registry, config, sync


def resolve_required(registry: dict[str, Any], reference: str | dict[str, Any]) -> dict[str, Any]:
    if isinstance(reference, dict):
        key = str(reference.get("id") or reference.get("sourcePath") or "")
    else:
        key = str(reference or "").strip()
    jar = resolve_jar(registry, key)
    if jar is None:
        jar = next(
            (
                item for item in registry.get("jars", [])
                if key in {
                    str(item.get("id") or ""),
                    str(item.get("sourcePath") or ""),
                    str(item.get("title") or ""),
                }
            ),
            None,
        )
    if jar is None:
        raise RegistryError(f"unknown Judgment Jar: {reference}")
    return jar


def jar_catalog() -> list[dict[str, Any]]:
    registry, _, _ = registry_state()
    values = []
    for jar in registry.get("jars", []):
        values.append({
            **public_jar(jar),
            "path": jar.get("sourcePath") or jar.get("id"),
            "sha256": jar.get("sourceSha256"),
        })
    return values


def source_text(jar: dict[str, Any], config: dict[str, Any]) -> tuple[str, dict[str, Any] | None]:
    if jar.get("origin") == LOCAL_ORIGIN:
        text = str(jar.get("body") or "")
        if not text.strip():
            raise RegistryError(f"repository Judgment Jar {jar.get('id')} has no body")
        return text, None
    native = fetch_native_source(jar, config, DEFAULT_CACHE)
    if native.get("content"):
        return str(native["content"]), native
    if native.get("sheet") is not None:
        return json.dumps(native["sheet"], ensure_ascii=False, indent=2, sort_keys=True), native
    raise RegistryError(f"authoritative native source for Judgment Jar {jar.get('id')} was empty")


def selected_jar_text(selected: list[str]) -> tuple[str, list[dict[str, Any]]]:
    global _CURRENT_SELECTED_JARS, _CURRENT_SELECTED_TEXT
    registry, config, _ = registry_state()
    docs: list[str] = []
    manifest: list[dict[str, Any]] = []
    selected_jars: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw in selected:
        jar = resolve_required(registry, str(raw or ""))
        if jar["id"] in seen:
            continue
        seen.add(jar["id"])
        text, native = source_text(jar, config)
        result = usage.record_usage(
            registry,
            config,
            jar,
            output_kind="context_packet",
            output_summary=f"Adam loaded selected Judgment Jar context: {jar.get('title')}",
            source="adam.preflight.selected-jar-context",
            cache=DEFAULT_CACHE,
            input_text=str(raw or ""),
            output_text=text,
            output_refs=[value for value in (jar.get("sourcePath"), jar.get("sourceUrl")) if value],
            native_source=native,
            metadata={"phase": "pre_execution", "selection": "planner"},
        )
        docs.append(f"\n--- SELECTED JAR {jar.get('id')} [{jar.get('origin')}] ---\n{text}")
        manifest.append({
            **public_jar(jar),
            "path": jar.get("sourcePath") or jar.get("id"),
            "sha256": jar.get("sourceSha256"),
            "contextUsageReceiptId": result["receipt"]["receiptId"],
            "contextUsageHomeCenterState": result["homeCenter"]["state"],
        })
        selected_jars.append(jar)
    if not manifest:
        raise RuntimeError("planning selected no Judgment Jars")
    _CURRENT_SELECTED_JARS = selected_jars
    _CURRENT_SELECTED_TEXT = "".join(docs)
    return _CURRENT_SELECTED_TEXT, manifest


def validate_plan_packet(action: dict) -> tuple[bool, str]:
    ok, error = _ORIGINAL_VALIDATE(action)
    if not ok:
        return ok, error
    try:
        allowed = usage.output_kinds(read_config(CONFIG_PATH))
    except Exception as exc:
        return False, f"Judgment Jar receipt taxonomy unavailable: {exc}"
    output_kind = str(action.get("outputKind") or "").strip()
    if output_kind not in allowed:
        return False, "outputKind must be one of: " + ", ".join(sorted(allowed))
    return True, ""


def planning_system(task: str, workspace: Path) -> str:
    original = _ORIGINAL_PLANNING_SYSTEM(task, workspace)
    allowed = sorted(usage.output_kinds(read_config(CONFIG_PATH)))
    return original + f"""

JUDGMENT JAR USAGE RECEIPT CONTRACT
- `submit_plan` MUST include `outputKind`, naming what the governed task is expected to create.
- Allowed outputKind values: {json.dumps(allowed)}
- Every selected Jar context load and every Jar-governed output receives one append-only usage receipt.
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
        "selectedJarContextUsageReceiptIds": [
            item.get("contextUsageReceiptId") for item in manifest if item.get("contextUsageReceiptId")
        ],
        "selectedJarContextHomeCenterStates": [
            item.get("contextUsageHomeCenterState") for item in manifest if item.get("contextUsageHomeCenterState")
        ],
    })
    return path


def receipt_ids(results: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("receipt", {}).get("receiptId") or "") for item in results]


def delivery_states(results: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("homeCenter", {}).get("state") or "PENDING") for item in results]


def review_plan_phone(task: str, workspace: Path, packet: dict, attempts: int = 4) -> dict:
    review = _ORIGINAL_PLAN_REVIEW(task, workspace, packet, attempts)
    registry, config, _ = registry_state()
    selected = [resolve_required(registry, reference) for reference in packet.get("selectedJars") or []]
    results = usage.record_many(
        registry,
        config,
        selected,
        output_kind="review_verdict",
        output_summary=f"Venice pre-execution Judgment Jar review produced {review.get('directive') or 'UNKNOWN'}.",
        source="adam.preflight.venice-plan-review",
        cache=DEFAULT_CACHE,
        status="allowed" if review.get("planPermissionGranted") else "blocked",
        input_text=json.dumps(packet, ensure_ascii=False, sort_keys=True),
        output_text=str(review.get("reviewText") or ""),
        request_id=str(packet.get("planSha256") or uuid.uuid4()),
        output_refs=[str(review.get("receipt") or "")],
        metadata={
            "phase": "pre_execution",
            "verdict": review.get("verdict"),
            "directive": review.get("directive"),
            "plannedOutputKind": packet.get("outputKind"),
        },
    )
    review["jarUsageReceiptIds"] = receipt_ids(results)
    review["jarUsageHomeCenterStates"] = delivery_states(results)
    review["plannedOutputKind"] = packet.get("outputKind")
    augment_json(review.get("receipt"), {
        "outputKind": packet.get("outputKind"),
        "jarUsageReceiptIds": review["jarUsageReceiptIds"],
        "jarUsageHomeCenterStates": review["jarUsageHomeCenterStates"],
    })
    return review


def active_local_jars(registry: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        jar for jar in registry.get("jars", [])
        if jar.get("origin") == LOCAL_ORIGIN and jar.get("status") == "active"
    ]


def active_jars_receipted() -> str:
    global _CURRENT_ACTIVE_JARS
    text = _ORIGINAL_ACTIVE_JARS()
    registry, config, _ = registry_state()
    selected = active_local_jars(registry)
    results = usage.record_many(
        registry,
        config,
        selected,
        output_kind="context_packet",
        output_summary="Adam loaded the active operational Judgment Jar context.",
        source="adam.execution.active-jar-context",
        cache=DEFAULT_CACHE,
        input_text="active operational Judgment Jars",
        output_text=text,
        output_refs=[str(jar.get("sourcePath") or "") for jar in selected],
        metadata={"phase": "execution", "selection": "active-operational-core"},
    )
    _CURRENT_ACTIVE_JARS = selected
    return text + "\n\nJAR_CONTEXT_USAGE_RECEIPTS: " + json.dumps({
        "receiptIds": receipt_ids(results),
        "homeCenterStates": delivery_states(results),
    }, ensure_ascii=False)


def governing_jars(registry: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    seen: set[str] = set()
    for jar in [*_CURRENT_ACTIVE_JARS, *_CURRENT_SELECTED_JARS]:
        current = resolve_required(registry, jar)
        if current["id"] not in seen:
            values.append(current)
            seen.add(current["id"])
    if not values:
        values = active_local_jars(registry)
    return values


def completion_review(
    task: str,
    workspace: Path,
    proposal: dict,
    jars: str,
    recent_messages: list[dict],
    task_base_commit: str | None,
    attempts: int = 4,
) -> dict:
    combined_jars = jars
    if _CURRENT_SELECTED_TEXT:
        combined_jars += "\n\n--- TASK-SELECTED JUDGMENT JARS ---\n" + _CURRENT_SELECTED_TEXT
    review = _ORIGINAL_COMPLETION_REVIEW(
        task, workspace, proposal, combined_jars, recent_messages, task_base_commit, attempts
    )
    registry, config, _ = registry_state()
    results = usage.record_many(
        registry,
        config,
        governing_jars(registry),
        output_kind="review_verdict",
        output_summary=f"Venice completion Judgment Jar review produced {review.get('directive') or 'UNKNOWN'}.",
        source="adam.completion.venice-review",
        cache=DEFAULT_CACHE,
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
    review["jarUsageReceiptIds"] = receipt_ids(results)
    review["jarUsageHomeCenterStates"] = delivery_states(results)
    augment_json(review.get("receipt"), {
        "jarUsageReceiptIds": review["jarUsageReceiptIds"],
        "jarUsageHomeCenterStates": review["jarUsageHomeCenterStates"],
    })
    return review


def run_task(
    task: str,
    workspace: Path,
    planning_stop_after_steps: int | None = None,
    execution_stop_after_steps: int | None = None,
) -> int:
    global _CURRENT_OUTPUT_KIND, _CURRENT_SELECTED_JARS, _CURRENT_SELECTED_TEXT, _CURRENT_ACTIVE_JARS
    gate = base.preflight(task, workspace, planning_stop_after_steps)
    packet, review = gate["packet"], gate["review"]
    _CURRENT_OUTPUT_KIND = str(packet.get("outputKind") or "mixed")
    registry, _, _ = registry_state()
    _CURRENT_SELECTED_JARS = [
        resolve_required(registry, reference) for reference in packet.get("selectedJars") or []
    ]
    enriched = (
        task
        + "\n\nPRE-EXECUTION PLAN APPROVED BY VENICE. Preserve it unless material state changes; if a material assumption fails, stop mutation and replan."
        + "\nPLAN_RECEIPT: " + str(review.get("receipt"))
        + "\nSELECTED_JARS: " + json.dumps(packet.get("selectedJars") or [], ensure_ascii=False)
        + "\nPLANNED_OUTPUT_KIND: " + _CURRENT_OUTPUT_KIND
        + "\nJAR_USAGE_RECEIPTS: " + json.dumps(review.get("jarUsageReceiptIds") or [], ensure_ascii=False)
        + "\nPLAN: " + json.dumps(packet.get("plan") or [], ensure_ascii=False)
        + "\nANTAGONISM: " + json.dumps(packet.get("antagonism") or [], ensure_ascii=False)
        + "\nDONE_CONDITION: " + str(packet.get("doneCondition") or "")
        + "\nEVIDENCE_STANDARD: " + str(packet.get("evidenceStandard") or "")
        + "\nJAR_RECEIPT_RULE: every Jar-governed output must name its output kind and preserve its usage receipt."
    )
    try:
        result_code = execution.run_task(enriched, workspace, stop_after_steps=execution_stop_after_steps)
        registry, config, _ = registry_state()
        completion_path = execution.STATE_DIR / "venice-review-last.json"
        completion_text = ""
        try:
            completion_text = completion_path.read_text(encoding="utf-8")
        except OSError:
            pass
        results = usage.record_many(
            registry,
            config,
            governing_jars(registry),
            output_kind=_CURRENT_OUTPUT_KIND,
            output_summary=f"Jar-governed Adam task produced {_CURRENT_OUTPUT_KIND} with exit code {result_code}.",
            source="adam.task.output",
            cache=DEFAULT_CACHE,
            status="completed" if result_code == 0 else "blocked" if result_code == 2 else "partial",
            input_text=task,
            output_text=json.dumps({
                "exitCode": result_code,
                "plannedOutputKind": _CURRENT_OUTPUT_KIND,
                "selectedJars": [jar.get("id") for jar in _CURRENT_SELECTED_JARS],
                "planReceipt": review.get("receipt"),
                "completionReceipt": str(completion_path),
                "completionReview": completion_text,
            }, ensure_ascii=False, sort_keys=True),
            request_id=str(review.get("receipt") or uuid.uuid4()),
            output_refs=[str(review.get("receipt") or ""), str(completion_path)],
            metadata={
                "phase": "terminal_output",
                "exitCode": result_code,
                "selectedJarIds": [jar.get("id") for jar in _CURRENT_SELECTED_JARS],
                "activeOperationalJarIds": [jar.get("id") for jar in _CURRENT_ACTIVE_JARS],
            },
        )
        print(json.dumps({
            "schema": "adam-judgment-jar-output-receipts.v1",
            "outputKind": _CURRENT_OUTPUT_KIND,
            "receiptIds": receipt_ids(results),
            "homeCenterStates": delivery_states(results),
        }, ensure_ascii=False, sort_keys=True))
        return result_code
    finally:
        _CURRENT_SELECTED_JARS = []
        _CURRENT_SELECTED_TEXT = ""
        _CURRENT_ACTIVE_JARS = []
        _CURRENT_OUTPUT_KIND = "mixed"


base.jar_catalog = jar_catalog
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
