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

CATEGORY_RULES = (
    ("venice_bypass", re.compile(r"venice|review receipt|self-certif|stop gate", re.I)),
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
        "venice_bypass": "No worker may terminate without a fresh durable Venice review receipt for the current slice.",
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


def regression_target(category: str) -> str:
    return f"future worker test/contract rejects recurrence category={category} before STOP_ALLOWED"


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
            f"finding={e.get('finding','')} rule={e.get('rule','')} regression={e.get('regressionTarget','')}"
        )
    return "\n".join(lines)


def persist_review(receipt: dict) -> list[dict]:
    directive = str(receipt.get("directive") or "")
    findings = [str(x).strip() for x in (receipt.get("findings") or []) if str(x).strip()]
    if directive == "STOP_ALLOWED" and not findings:
        return []
    if not findings:
        findings = [f"review directive {directive} without explicit finding"]
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    prior = _read_entries()
    counts: dict[str, int] = {}
    for e in prior:
        fp = str(e.get("fingerprint") or "")
        if fp:
            counts[fp] = max(counts.get(fp, 0), int(e.get("occurrence") or 1))
    created = []
    for finding in findings:
        category = classify_finding(finding)
        rule = prevention_rule(category, finding)
        fp = hashlib.sha256(f"{category}\0{finding.lower().strip()}".encode("utf-8")).hexdigest()
        occurrence = counts.get(fp, 0) + 1
        counts[fp] = occurrence
        entry = {
            "schema": "venice-review-memory-v1",
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
            "regressionTarget": regression_target(category),
            "judgmentJarApplied": receipt.get("judgmentJarApplied") or [],
            "fingerprint": fp,
            "occurrence": occurrence,
        }
        with MEMORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        created.append(entry)
    projection = {
        "schema": "venice-review-memory-latest-v1",
        "updatedAtEpoch": int(time.time()),
        "entries": load_memory(str(receipt.get("repo") or ""), MAX_PROMPT_ENTRIES),
    }
    tmp = LATEST_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(projection, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(LATEST_PATH)
    return created


if __name__ == "__main__":
    print(render_memory())
