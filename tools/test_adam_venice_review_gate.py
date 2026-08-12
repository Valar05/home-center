#!/usr/bin/env python3
from pathlib import Path
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

verdict, directive, findings, _ = canonical.parse_review(
    "VERDICT: PASS\nDIRECTIVE: STOP_ALLOWED\nJAR: observable evidence\nNOTE: ok"
)
assert verdict == "PASS" and directive == "STOP_ALLOWED" and not findings
verdict, directive, findings, _ = canonical.parse_review("plain prose")
assert verdict == "FAIL" and directive == "HALT_REQUIRED" and findings

assert reviewed.BACKOFF_SECONDS == (1, 2, 4, 8, 15, 30)
assert reviewed.CHECKPOINT_STEPS >= 8

# The researched Codex local steering is content, not filenames: all three
# project-local organs must load into the worker context.
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

source = (ROOT / "tools/adam_venice_reviewed.py").read_text(encoding="utf-8")
for token in [
    'import venice_review as canonical_venice',
    'canonical_venice.review_prompt(',
    'canonical_venice.parse_review(',
    'def codex_local_documents(',
    'CODEX LOCAL STEERING DOCUMENTS (binding)',
    'stopPermissionGranted',
    'externalReviewGateSatisfied',
    'CONTINUE_REQUIRED',
    'HALT_REQUIRED',
    'phone model unavailable after daemon backoff burst',
    'DAEMON_CHECKPOINT',
    'while True:',
    'stop_after_steps',
    'Venice Completion and Code Review Gate',
    'Daemon Persistence and Connector Backoff',
]:
    assert token in source, f"reviewed worker missing {token}"

assert 'step budget exhausted' not in source
print("Adam Codex-local / canonical Venice / daemon persistence contract: PASS")
