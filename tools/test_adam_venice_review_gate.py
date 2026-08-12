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

assert reviewed.parse_review("plain prose") is None
r = reviewed.parse_review('{"verdict":"continue","quality":"mixed","code_review_first":true,"critique":"test","next":"fix it"}')
assert r and r["verdict"] == "continue" and r["code_review_first"] is True

assert reviewed.BACKOFF_SECONDS == (1, 2, 4, 8, 15, 30)
assert reviewed.CHECKPOINT_STEPS >= 8

with tempfile.TemporaryDirectory() as td:
    ev = reviewed.git_evidence(Path(td))
    assert ev["isGitRepo"] is False

source = (ROOT / "tools/adam_venice_reviewed.py").read_text(encoding="utf-8")
for token in [
    'tool in {"finish", "respond"}',
    'Venice denied stopping',
    'worker.call_model = lambda messages',
    'phone model unavailable after daemon backoff burst',
    'DAEMON_CHECKPOINT',
    'checkpoint(task, workspace, step, messages)',
    'while True:',
    'Venice Completion and Code Review Gate',
    'Daemon Persistence and Connector Backoff',
]:
    assert token in source, f"reviewed worker missing {token}"

assert 'step budget exhausted' not in source
print("Adam Venice review / daemon persistence contract: PASS")
