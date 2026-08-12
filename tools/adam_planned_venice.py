#!/usr/bin/env python3
"""Adam phone entrypoint with mandatory pre-execution planning.

Every substantive task goes through:
research -> plan -> select relevant Judgment Jars -> antagonize -> Venice
PLAN_ALLOWED -> existing Codex/Venice execution loop.

The planning phase is read-only. It cannot write files, dispatch Phone Hands, or
use inferred shell mutation. Blocking Venice findings are durable reviewer memory.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_codex_phone as core
import adam_venice_reviewed as execution
import venice_plan_review
import venice_review_memory

STATE_DIR = Path(os.path.expanduser(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center"))) / "adam-daemon"
PLAN_HISTORY = STATE_DIR / "venice-plan-reviews.jsonl"
PLAN_LAST = STATE_DIR / "venice-plan-review-last.json"
PLANNING_TOOLS = {"read_file", "list_dir", "search_files", "run_command", "submit_plan"}


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def jar_catalog() -> list[dict]:
    rule_dir = ROOT / ".continue" / "rules"
    out = []
    for path in sorted(rule_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        heading = next((line.lstrip("# ").strip() for line in text.splitlines() if line.startswith("#")), path.name)
        out.append({"path": str(path.relative_to(ROOT)), "title": heading, "sha256": _sha(text)})
    return out


def selected_jar_text(selected: list[str]) -> tuple[str, list[dict]]:
    catalog = {item["path"]: item for item in jar_catalog()}
    docs, manifest = [], []
    seen = set()
    for raw in selected:
        rel = str(raw or "").strip()
        if not rel or rel in seen:
            continue
        seen.add(rel)
        item = catalog.get(rel)
        if not item:
            raise RuntimeError(f"planning selected unknown Judgment Jar: {rel}")
        path = ROOT / rel
        text = path.read_text(encoding="utf-8", errors="replace")
        docs.append(f"\n--- SELECTED JAR {rel} ---\n{text}")
        manifest.append(item)
    if not manifest:
        raise RuntimeError("planning selected no Judgment Jars")
    return "".join(docs), manifest


def persist_plan_review(task: str, packet: dict, review: dict) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    receipt = {
        "schema": "adam-venice-plan-review-v1",
        "createdAtEpoch": int(time.time()),
        "task": task[:4000],
        "taskSha256": _sha(task),
        "researchSummary": str(packet.get("researchSummary") or "")[:12000],
        "plan": packet.get("plan") or [],
        "selectedJars": packet.get("selectedJars") or [],
        "jarRationale": str(packet.get("jarRationale") or "")[:6000],
        "antagonism": packet.get("antagonism") or [],
        "doneCondition": str(packet.get("doneCondition") or "")[:6000],
        "evidenceStandard": str(packet.get("evidenceStandard") or "")[:6000],
        "planSha256": _sha(json.dumps(packet, ensure_ascii=False, sort_keys=True)),
        "verdict": review.get("verdict"),
        "directive": review.get("directive"),
        "planPermissionGranted": review.get("planPermissionGranted") is True,
        "externalReviewGateSatisfied": review.get("externalReviewGateSatisfied") is True,
        "judgmentJarApplied": review.get("judgmentJarApplied") or [],
        "findings": review.get("findings") or [],
        "reviewText": str(review.get("reviewText") or "")[:10000],
        "selectedJarManifest": review.get("selectedJarManifest") or [],
        "reviewerMemorySha256": review.get("reviewerMemorySha256"),
    }
    with PLAN_HISTORY.open("a", encoding="utf-8") as f:
        f.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")
    tmp = PLAN_LAST.with_suffix(".tmp")
    tmp.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(PLAN_LAST)
    return PLAN_LAST


def review_plan_phone(task: str, workspace: Path, packet: dict, attempts: int = 4) -> dict:
    jar_text, manifest = selected_jar_text(list(packet.get("selectedJars") or []))
    precedent = venice_review_memory.render_memory(str(execution.repo_root(workspace) or workspace))
    prompt = venice_plan_review.build_prompt(
        task,
        str(packet.get("researchSummary") or ""),
        json.dumps(packet.get("plan") or [], ensure_ascii=False, indent=2),
        json.dumps(packet.get("antagonism") or [], ensure_ascii=False, indent=2),
        jar_text,
        manifest,
        str(packet.get("jarRationale") or ""),
        precedent,
        json.dumps({
            "workspace": str(workspace),
            "initialGitEvidence": execution.git_evidence(workspace),
            "doneCondition": packet.get("doneCondition"),
            "evidenceStandard": packet.get("evidenceStandard"),
        }, ensure_ascii=False, indent=2),
    )
    messages = [
        {"role": "system", "content": "You are Venice performing the mandatory pre-execution Judgment Jar plan review. Return only VERDICT/DIRECTIVE/JAR/FINDING/NOTE fields."},
        {"role": "user", "content": prompt},
    ]
    result = None
    for _ in range(max(1, attempts)):
        raw = execution.resilient_call_model(core.call_model, messages, timeout=120)
        verdict, directive, findings, applied = venice_plan_review.parse_plan_review(raw)
        malformed = {"plan_reviewer_output_missing_strict_verdict", "plan_reviewer_output_missing_strict_directive", "inconsistent_plan_pass_directive", "failed_plan_cannot_be_allowed"}
        if not any(x in malformed for x in findings):
            allowed = verdict == "PASS" and directive == "PLAN_ALLOWED"
            result = {
                "schema": "venice-plan-review-v1-phone",
                "verdict": verdict,
                "directive": directive,
                "planPermissionGranted": allowed,
                "externalReviewGateSatisfied": allowed,
                "findings": findings,
                "judgmentJarApplied": applied,
                "reviewText": raw,
                "selectedJarManifest": manifest,
                "reviewerMemorySha256": _sha(precedent),
            }
            break
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": "Malformed plan review. Return canonical PLAN_ALLOWED/REPLAN_REQUIRED/HALT_REQUIRED fields only; fail closed."})
    if result is None:
        result = {
            "schema": "venice-plan-review-v1-phone",
            "verdict": "FAIL",
            "directive": "HALT_REQUIRED",
            "planPermissionGranted": False,
            "externalReviewGateSatisfied": False,
            "findings": ["venice_plan_review_unavailable_after_recovery"],
            "judgmentJarApplied": ["unknowns remain unknown"],
            "reviewText": "",
            "selectedJarManifest": manifest,
            "reviewerMemorySha256": _sha(precedent),
        }
    memory_receipt = {
        "repo": str(execution.repo_root(workspace) or workspace),
        "directive": result["directive"],
        "verdict": result["verdict"],
        "findings": result["findings"],
        "judgmentJarApplied": result["judgmentJarApplied"],
    }
    try:
        venice_review_memory.persist_review(memory_receipt)
    except Exception as exc:
        result.update({
            "verdict": "FAIL",
            "directive": "HALT_REQUIRED",
            "planPermissionGranted": False,
            "externalReviewGateSatisfied": False,
        })
        result.setdefault("findings", []).append(f"venice_memory_persist_failed:{type(exc).__name__}:{exc}")
    result["receipt"] = str(persist_plan_review(task, packet, result))
    return result


def validate_plan_packet(action: dict) -> tuple[bool, str]:
    if action.get("tool") != "submit_plan":
        return False, "not submit_plan"
    research = str(action.get("researchSummary") or "").strip()
    plan = action.get("plan")
    selected = action.get("selectedJars")
    rationale = str(action.get("jarRationale") or "").strip()
    antagonism = action.get("antagonism")
    done = str(action.get("doneCondition") or "").strip()
    evidence = str(action.get("evidenceStandard") or "").strip()
    if not research:
        return False, "researchSummary missing"
    if not isinstance(plan, list) or not plan:
        return False, "plan must be a non-empty list"
    if not isinstance(selected, list) or not selected:
        return False, "selectedJars must be a non-empty list"
    if not rationale:
        return False, "jarRationale missing"
    if not isinstance(antagonism, list) or not antagonism:
        return False, "antagonism must be a non-empty list"
    if not done or not evidence:
        return False, "doneCondition/evidenceStandard missing"
    try:
        selected_jar_text(selected)
    except Exception as exc:
        return False, str(exc)
    return True, ""


def planning_system(task: str, workspace: Path) -> str:
    codex_docs, loaded = execution.codex_local_documents(workspace)
    precedent = venice_review_memory.render_memory(str(execution.repo_root(workspace) or workspace))
    return f"""You are Adam's PRE-EXECUTION PLANNER. You may research but you may not mutate or dispatch anything.

Required sequence: research -> plan -> select relevant Judgment Jars -> antagonize -> submit_plan -> Venice.
Do not guess blindly. Use read/list/search/run_command for authoritative research. `run_command` is inspection/build/test only and mutation is blocked by the deterministic core.

Allowed JSON tools:
{{"tool":"read_file","path":"...","start":1,"lines":220}}
{{"tool":"list_dir","path":"..."}}
{{"tool":"search_files","query":"...","path":"."}}
{{"tool":"run_command","command":"git status -sb","timeout":30}}
{{"tool":"submit_plan","researchSummary":"what real state you established","plan":["bounded step"],"selectedJars":[".continue/rules/file.md"],"jarRationale":"why these jars","antagonism":["how this plan could fail"],"doneCondition":"testable commissioned outcome","evidenceStandard":"what evidence proves each claimed state"}}

No prose outside one JSON object. Never use write_file, phone_intent, finish, or respond in planning.

TASK FROM DREW:
{task}

WORKSPACE: {workspace}
CODEX DOCS LOADED: {json.dumps(loaded)}
AVAILABLE JUDGMENT JARS:
{json.dumps(jar_catalog(), ensure_ascii=False, indent=2)}

DURABLE VENICE REVIEW MEMORY:
{precedent}

CODEX LOCAL STEERING:
{codex_docs}
"""


def preflight(task: str, workspace: Path, stop_after_steps: int | None = None) -> dict:
    messages = [
        {"role": "system", "content": planning_system(task, workspace)},
        {"role": "user", "content": "Begin research. Inspect real state before submitting a plan."},
    ]
    step = 0
    while True:
        step += 1
        if stop_after_steps is not None and step > stop_after_steps:
            raise RuntimeError("bounded planning acceptance window exhausted before PLAN_ALLOWED")
        raw = execution.resilient_call_model(core.call_model, messages, timeout=120)
        action = core.parse_action(raw)
        if not isinstance(action, dict):
            messages.extend([
                {"role": "assistant", "content": raw},
                {"role": "user", "content": "FORMAT_ERROR: planning requires exactly one allowed JSON action."},
            ])
            continue
        tool = str(action.get("tool") or "").strip()
        if tool not in PLANNING_TOOLS:
            messages.extend([
                {"role": "assistant", "content": json.dumps(action, ensure_ascii=False)},
                {"role": "user", "content": f"PLAN_GATE_BLOCKED: {tool!r} is not allowed before Venice PLAN_ALLOWED. Research and plan first."},
            ])
            continue
        if tool == "submit_plan":
            ok, error = validate_plan_packet(action)
            if not ok:
                messages.extend([
                    {"role": "assistant", "content": json.dumps(action, ensure_ascii=False)},
                    {"role": "user", "content": "PLAN_PACKET_INVALID: " + error},
                ])
                continue
            review = review_plan_phone(task, workspace, action)
            if review.get("planPermissionGranted"):
                return {"packet": action, "review": review}
            if review.get("directive") == "REPLAN_REQUIRED":
                messages.extend([
                    {"role": "assistant", "content": json.dumps(action, ensure_ascii=False)},
                    {"role": "user", "content": "VENICE PLAN REVIEW: REPLAN_REQUIRED. Findings: " + json.dumps(review.get("findings") or [], ensure_ascii=False) + f" Receipt: {review.get('receipt')}. Research/revise/reselect jars/antagonize and submit again."},
                ])
                continue
            raise RuntimeError(f"Venice plan gate HALT_REQUIRED receipt={review.get('receipt')} findings={review.get('findings')}")
        terminal, observation = core.execute_tool(workspace, action)
        if terminal:
            observation = {"ok": False, "error": "terminal action blocked during planning"}
        messages.extend([
            {"role": "assistant", "content": json.dumps(action, ensure_ascii=False)},
            {"role": "user", "content": "RESEARCH OBSERVATION:\n" + json.dumps(observation, ensure_ascii=False)},
        ])


def run_task(task: str, workspace: Path, planning_stop_after_steps: int | None = None, execution_stop_after_steps: int | None = None) -> int:
    gate = preflight(task, workspace, planning_stop_after_steps)
    packet, review = gate["packet"], gate["review"]
    enriched = (
        task
        + "\n\nPRE-EXECUTION PLAN APPROVED BY VENICE. Preserve it unless material state changes; if a material assumption fails, stop mutation and replan."
        + "\nPLAN_RECEIPT: " + str(review.get("receipt"))
        + "\nSELECTED_JARS: " + json.dumps(packet.get("selectedJars") or [], ensure_ascii=False)
        + "\nPLAN: " + json.dumps(packet.get("plan") or [], ensure_ascii=False)
        + "\nANTAGONISM: " + json.dumps(packet.get("antagonism") or [], ensure_ascii=False)
        + "\nDONE_CONDITION: " + str(packet.get("doneCondition") or "")
        + "\nEVIDENCE_STANDARD: " + str(packet.get("evidenceStandard") or "")
    )
    return execution.run_task(enriched, workspace, stop_after_steps=execution_stop_after_steps)


def run_interactive(cwd: str | None = None) -> int:
    workspace = Path(cwd or Path.cwd()).expanduser().resolve()
    if not workspace.is_dir():
        workspace = ROOT
    print("Adam online. Every task researches, plans, selects Judgment Jars, antagonizes, asks Venice, then executes. Venice also reviews every stop.")
    while True:
        try:
            text = input(f"adam {workspace}$ ")
        except EOFError:
            print()
            return 0
        except KeyboardInterrupt:
            print("\n^C")
            continue
        stripped = text.strip()
        if not stripped:
            continue
        if stripped in {":exit", ":quit"}:
            return 0
        if stripped == ":help":
            print(core.help_text() + "\nPre-execution: research -> plan -> relevant jars -> antagonize -> Venice. Completion: Venice stop/code review.")
            continue
        if stripped == ":status":
            print(json.dumps({
                "schema": "adam-planned-venice-status-v1",
                "workspace": str(workspace),
                "preExecutionPlanGate": True,
                "planReviewLast": str(PLAN_LAST),
                "planReviewHistory": str(PLAN_HISTORY),
                "completionReviewLast": str(execution.STATE_DIR / "venice-review-last.json"),
                "reviewMemory": str(venice_review_memory.MEMORY_PATH),
            }, indent=2))
            continue
        if stripped == ":cwd" or stripped.startswith(":cwd "):
            raw = stripped[len(":cwd"):].strip()
            target = (workspace / raw).resolve() if raw and not Path(raw).expanduser().is_absolute() else Path(raw or workspace).expanduser().resolve()
            if target.is_dir():
                workspace = target
                print(f"Adam: workspace {workspace}")
            else:
                print(f"Adam: not a directory: {target}")
            continue
        try:
            run_task(stripped, workspace)
        except Exception as exc:
            print(f"Adam [plan/execution blocked]: {exc}")


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args:
        return run_task(" ".join(args), Path.cwd().resolve())
    return run_interactive()


if __name__ == "__main__":
    raise SystemExit(main())
