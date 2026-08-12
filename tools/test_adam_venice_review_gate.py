#!/usr/bin/env python3
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import adam_codex_phone as worker
import adam_venice_reviewed as reviewed

jars = worker.active_jars()
assert "Venice Completion and Code Review Gate" in jars
assert "Daemon Persistence and Connector Backoff" in jars

# Venice review parser accepts only the explicit governed schema.
assert reviewed.parse_review("plain prose") is None
r = reviewed.parse_review('{"verdict":"continue","quality":"mixed","code_review_first":true,"critique":"test","next":"fix it"}')
assert r and r["verdict"] == "continue" and r["code_review_first"] is True

# Backoff policy is bounded, increasing, and gentle rather than a busy loop.
assert reviewed.BACKOFF_SECONDS == (1, 2, 4, 8, 15, 30)
assert reviewed.DEFAULT_STEPS >= 24

# Fresh repo evidence must be collected for review; non-repos are handled without invention.
with tempfile.TemporaryDirectory() as td:
    ev = reviewed.git_evidence(Path(td))
    assert ev["isGitRepo"] is False

source = (ROOT / "tools/adam_venice_reviewed.py").read_text(encoding="utf-8")
for token in [
    'tool not in {"finish", "respond"}',
    'Venice denied stopping',
    'worker.call_model = lambda messages',
    'phone model unavailable after daemon backoff burst',
    'Venice Completion and Code Review Gate',
    'Daemon Persistence and Connector Backoff',
]:
    assert token in source, f"reviewed worker missing {token}"

print("Adam Venice review / daemon persistence contract: PASS")
