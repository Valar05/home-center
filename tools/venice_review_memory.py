#!/usr/bin/env python3
"""Append-only durable memory for Venice review precedent."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path

STATE_DIR = Path(os.path.expanduser(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center"))) / "venice"
MEMORY_PATH = Path(os.path.expanduser(os.environ.get("VENICE_REVIEW_MEMORY", str(STATE_DIR / "review-memory.jsonl"))))
LATEST_PATH = Path(os.path.expanduser(os.environ.get("VENICE_REVIEW_MEMORY_LATEST", str(STATE_DIR / "review-memory-latest.json"))))
MAX_PROMPT_ENTRIES = int(os.environ.get("VENICE_REVIEW_MEMORY_MAX_PROMPT", "24"))
PASS_DIRECTIVES = {"STOP_ALLOWED", "PLAN_ALLOWED"}

CATEGORY_RULES = (
    ("venice_bypass", re.compile(r"venice|review receipt|self-certif|stop gate|plan gate", re.I)),
    ("plan_failure", re.compile(r"plan|research|antagon|judgment jar|replan", re.I)),
    ("premature_stop", re.compile(r"premature|stop early|not done|continue|required", re.I)),
    ("code_review_omission", re.compile(r"code review|diff|regression|test coverage", re.I)),
    ("codex_bootstrap_omission", re.compile(r"codex|AGENTS\.md|MEMORIES\.md|SKILLS\.md|bootstrap|steering", re.I)),
    ("daemon_backoff_violation", re.compile(r"daemon|backoff|retry|timeout|give up|hammer", re.I)),
    ("evidence_laundering", re.compile(r"evidence|receipt|runtime proof|deployed|callable|delivered|accepted", re.I)),
    ("body_lane_bypass", re.compile(r"phone hands|computer hands|body lane|ssh|transport", re.I)),
    ("unsafe_inferred_authority", re.compile(r"authority|shell|destructive|mutation|permission", re.I)),
    ("duplicate_side_effect", re.compile(r"duplicate|idempot|side effect|acknowledg|delivery", re.I)),
    ("correction_regression", re.compile(r"again|regression|forgot|correction|reintroduced", re.I)),
)


def classify_finding(text: str) -> str:
    for name, rx in CATEGORY_RULES:
        if rx.search(text or ""):
            return name
    return "review_finding"


def prevention_rule(category: str, finding: str) -> str:
    rules = {
        "venice_bypass": "No worker may begin substantive execution or terminate without the fresh Venice review receipt required for that gate.",
        "plan_failure": "Research, plan, select relevant Judgment Jars, antagonize, and obtain Venice PLAN_ALLOWED before substantive execution.",
        "premature_stop": "Treat unfinished work and transient blockers as continuation conditions, not completion.",
        "code_review_omission": "Review the actual current delta and prioritize correctness/regression findings before style.",
        "codex_bootstrap_omission": "Load applicable Codex steering documents before planning, execution, or stop review.",
        "daemon_backoff_violation": "Preserve mission state and back off sanely through transient dependency failures; do not terminate the mission.",
        "evidence_laundering": "Do not advance capability state beyond the exact evidence produced on the commissioned surface.",
        "body_lane_bypass": "Exhaust authorized configured body lanes before handing execution back to Drew.",
        "unsafe_inferred_authority": "Model inference may not silently acquire destructive or broader execution authority.",
        "duplicate_side_effect": "Persist execution result before delivery retry; retry delivery rather than repeating side effects.",
        "correction_regression": "Every correction must preserve all earlier non-conflicting constraints and regression locks.",
    }
    return rules.get(category, f"Prevent recurrence of this reviewed failure: {finding}")


def recovery_rule(category: str, class_occurrence: int) -> str:
    """Describe how a repeated failure is allowed to cost the human less, not more."""
    n = max(1, int(class_occurrence or 1))
    if n == 1:
        return (
            "Apply the repair and preserve enough structured precedent that a later analogous failure can be "
            "corrected from the smallest new delta rather than a full restatement."
        )
    if category == "correction_regression":
        return (
            "RECURRENCE_RATCHET: load the prior correction before asking for anything; never require Drew to "
            "restate the earlier correction or evidence. Accept the smallest available new delta, including a "
            "word, screenshot, example, gesture-description, or behavioral contradiction. When more than one "
            "recovery surface is available, prefer a different lower-burden surface from the one that previously "
            "failed. Preserve unresolved ambiguity unless consequence requires resolution."
        )
    return (
        "RECURRENCE_RATCHET: prior precedent is mandatory input. Repair from stored evidence plus the smallest "
        "new delta; do not send the operator through the same explanatory load path merely because it is easy "
        "for the worker. Prefer behavior/readback/canary evidence over another prose re-teach when available."
    )


def regression_target(category: str) -> str:
    return f"future worker test/contract rejects recurrence category={category} before Venice allows the relevant gate"


def _read_entries() -> list[dict]:
    if not MEMORY_PATH.is_file():
        return []
    out = []
    for line in MEMORY_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out


def load_memory(repo: str | None = None, limit: int = MAX_PROMPT_ENTRIES) -> list[dict]:
    entries = _read_entries()
    if repo:
        same = [e for e in entries if str(e.get("repo") or "") == str(repo)]
        generic = [e for e in entries if not e.get("repo")]
        entries = same + generic if same or generic else entries
    return entries[-max(1, int(limit)):]


def render_memory(repo: str | None = None, limit: int = MAX_PROMPT_ENTRIES) -> str:
    entries = load_memory(repo, limit)
    if not entries:
        return "(no durable Venice review precedent available on this runtime)"
    lines = []
    for e in entries:
        lines.append(
            f"- [{e.get('category','review_finding')}] occurrence={e.get('occurrence',1)} "
            f"classOccurrence={e.get('classOccurrence',e.get('occurrence',1))} "
            f"finding={e.get('finding','')} rule={e.get('rule','')} "
            f"recovery={e.get('recoveryRule','')} regression={e.get('regressionTarget','')}"
        )
    return "\n".join(lines)


def persist_review(receipt: dict) -> list[dict]:
    directive = str(receipt.get("directive") or "")
    findings = [str(x).strip() for x in (receipt.get("findings") or []) if str(x).strip()]
    if directive in PASS_DIRECTIVES and not findings:
        return []
    if not findings:
        findings = [f"review directive {directive} without explicit finding"]
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    prior = _read_entries()
    counts: dict[str, int] = {}
    category_counts: dict[str, int] = {}
    for e in prior:
        fp = str(e.get("fingerprint") or "")
        if fp:
            counts[fp] = max(counts.get(fp, 0), int(e.get("occurrence") or 1))
        category = str(e.get("category") or "review_finding")
        category_counts[category] = max(
            category_counts.get(category, 0),
            int(e.get("classOccurrence") or 0),
        )
    created = []
    for finding in findings:
        category = classify_finding(finding)
        rule = prevention_rule(category, finding)
        fp = hashlib.sha256(f"{category}\0{finding.lower().strip()}".encode("utf-8")).hexdigest()
        occurrence = counts.get(fp, 0) + 1
        counts[fp] = occurrence
        class_occurrence = category_counts.get(category, 0) + 1
        category_counts[category] = class_occurrence
        entry = {
            "schema": "venice-review-memory-v2",
            "createdAtEpoch": int(time.time()),
            "repo": receipt.get("repo"),
            "baseCommit": receipt.get("baseCommit"),
            "headCommit": receipt.get("headCommit"),
            "fullDiffSha256": receipt.get("fullDiffSha256") or receipt.get("fullDiffHash"),
            "directive": directive,
            "verdict": receipt.get("verdict"),
            "category": category,
            "finding": finding,
            "observation": finding,
            "inference": "This finding is reusable reviewer precedent, not proof that future tasks share the same state.",
            "rule": rule,
            "recoveryRule": recovery_rule(category, class_occurrence),
            "regressionTarget": regression_target(category),
            "judgmentJarApplied": receipt.get("judgmentJarApplied") or [],
            "correctionRoute": str(receipt.get("correctionRoute") or "unspecified"),
            "fingerprint": fp,
            "occurrence": occurrence,
            "classOccurrence": class_occurrence,
        }
        with MEMORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        created.append(entry)
    projection = {
        "schema": "venice-review-memory-latest-v2",
        "updatedAtEpoch": int(time.time()),
        "entries": load_memory(str(receipt.get("repo") or ""), MAX_PROMPT_ENTRIES),
    }
    tmp = LATEST_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(LATEST_PATH)
    return created


if __name__ == "__main__":
    print(render_memory())
