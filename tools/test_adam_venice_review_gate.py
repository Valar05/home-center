#!/usr/bin/env python3
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_codex_phone as core
import adam_venice_reviewed as reviewed
import venice_review as canonical

jars = core.active_jars()
assert "Venice Completion and Code Review Gate" in jars
assert "Daemon Persistence and Connector Backoff" in jars

agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
assert "Pre-execution planning — all agents and workers" in agents
assert "Research" in agents and "Plan" in agents and "Select Judgment Jars" in agents and "Antagonize" in agents and "Ask Venice" in agents
assert "Execute only after `PLAN_ALLOWED`" in agents
assert "REPLAN_REQUIRED" in agents
assert "The worker chooses whichever jars it thinks the task needs" in agents
assert "declares the controlled output kind" in agents
assert "per-Jar context/review usage receipts" in agents
assert "Judgment Jar usage receipts — all agents and workers" in agents
assert "Every actual Jar use must emit one append-only usage receipt" in agents
assert "CAPTURED" in agents and "DELIVERED" in agents
assert "retry the oldest pending receipt first" in agents
assert "Venice completion review — all agents and workers" in agents
assert "No agent or worker may certify its own completion" in agents
assert "This requirement applies to **all work**" in agents
assert "CONTINUE_REQUIRED" in agents and "HALT_REQUIRED" in agents and "STOP_ALLOWED" in agents
assert "Non-code and conversational work" in agents
assert "Venice must take durable notes" in agents
assert "Failure or latency in an optional live/local Venice path is not permission to bypass Venice" in agents

verdict, directive, findings, _ = canonical.parse_review(
    "VERDICT: PASS\nDIRECTIVE: STOP_ALLOWED\nJAR: observable evidence\nNOTE: ok"
)
assert verdict == "PASS" and directive == "STOP_ALLOWED" and not findings
verdict, directive, findings, _ = canonical.parse_review("plain prose")
assert verdict == "FAIL" and directive == "HALT_REQUIRED" and findings

assert reviewed.BACKOFF_SECONDS == (1, 2, 4, 8, 15, 30)
assert reviewed.STEADY_BACKOFF_SECONDS >= reviewed.BACKOFF_SECONDS[-1]
assert reviewed.CHECKPOINT_STEPS >= 8

docs, loaded = reviewed.codex_local_documents(ROOT)
for name in ("AGENTS.md", "MEMORIES.md", "SKILLS.md"):
    assert name in loaded, (name, loaded)
assert "Repository Agent Instructions" in docs
assert "Codex Local Memory" in docs
assert "Codex Local Skills" in docs
assert "Agent Handoff And Session Memory" in docs
assert "Venice Completion / Code Review" in docs

with tempfile.TemporaryDirectory() as td:
    ev = reviewed.git_evidence(Path(td))
    assert ev["isGitRepo"] is False

with tempfile.TemporaryDirectory() as td:
    old_state = reviewed.STATE_DIR
    reviewed.STATE_DIR = Path(td)
    try:
        path = reviewed.persist_venice_review(
            "test task",
            {"tool": "finish", "status": "done", "text": "ok"},
            {
                "verdict": "PASS",
                "directive": "STOP_ALLOWED",
                "stopPermissionGranted": True,
                "externalReviewGateSatisfied": True,
                "codeReviewFirst": True,
                "judgmentJarApplied": ["observable evidence"],
                "findings": [],
                "reviewText": "VERDICT: PASS",
                "freshEvidence": {"baseCommit": "a", "headCommit": "b", "diffFullSha256": "c"},
            },
        )
        obj = json.loads(path.read_text(encoding="utf-8"))
        assert obj["schema"] == "adam-venice-stop-review-v1"
        assert obj["externalReviewGateSatisfied"] is True
        assert obj["directive"] == "STOP_ALLOWED"
        assert (Path(td) / "venice-reviews.jsonl").is_file()
    finally:
        reviewed.STATE_DIR = old_state

source = (ROOT / "tools/adam_venice_reviewed.py").read_text(encoding="utf-8")
for token in [
    'import venice_review as canonical_venice',
    'canonical_venice.review_prompt(',
    'canonical_venice.parse_review(',
    'def codex_local_documents(',
    'CODEX LOCAL STEERING DOCUMENTS (binding)',
    'def persist_venice_review(',
    'venice-reviews.jsonl',
    'venice-review-last.json',
    'stopPermissionGranted',
    'externalReviewGateSatisfied',
    'CONTINUE_REQUIRED',
    'HALT_REQUIRED',
    'STEADY_BACKOFF_SECONDS',
    'while True:',
    'stop_after_steps',
]:
    assert token in source, f"reviewed worker missing {token}"

planned = (ROOT / "tools/adam_planned_venice.py").read_text(encoding="utf-8")
for token in [
    'def preflight(',
    'submit_plan',
    'selectedJars',
    'jarRationale',
    'antagonism',
    'PLAN_ALLOWED',
    'REPLAN_REQUIRED',
    'review_plan_phone(',
]:
    assert token in planned, f"planned worker missing {token}"

receipted = (ROOT / "tools/adam_planned_venice_receipted.py").read_text(encoding="utf-8")
for token in [
    'outputKind',
    'output_kind="context_packet"',
    'output_kind="review_verdict"',
    'output_kind=_CURRENT_OUTPUT_KIND',
    'execution.canonical_venice_review = completion_review',
]:
    assert token in receipted, f"receipt wrapper missing {token}"

assert 'step budget exhausted' not in source
assert 'raise RuntimeError(f"phone model unavailable after daemon backoff burst' not in source
print("Adam global plan + Renee/Venice + Judgment-Jar usage receipt + nonterminal-daemon contract: PASS")
