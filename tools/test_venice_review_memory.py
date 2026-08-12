#!/usr/bin/env python3
from pathlib import Path
import json
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import venice_review_memory as memory

with tempfile.TemporaryDirectory() as td:
    old_state, old_memory, old_latest = memory.STATE_DIR, memory.MEMORY_PATH, memory.LATEST_PATH
    memory.STATE_DIR = Path(td)
    memory.MEMORY_PATH = Path(td) / "review-memory.jsonl"
    memory.LATEST_PATH = Path(td) / "review-memory-latest.json"
    try:
        receipt = {
            "repo": "/repo",
            "baseCommit": "a",
            "headCommit": "b",
            "fullDiffSha256": "deadbeef",
            "directive": "CONTINUE_REQUIRED",
            "verdict": "FAIL",
            "findings": ["worker stopped without Venice review receipt"],
            "judgmentJarApplied": ["observable evidence"],
        }
        first = memory.persist_review(receipt)
        second = memory.persist_review(receipt)
        assert len(first) == 1 and len(second) == 1
        assert first[0]["category"] == "venice_bypass"
        assert first[0]["occurrence"] == 1
        assert second[0]["occurrence"] == 2
        assert first[0]["fingerprint"] == second[0]["fingerprint"]
        assert "No worker may terminate" in second[0]["rule"]
        assert memory.MEMORY_PATH.is_file()
        lines = memory.MEMORY_PATH.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert memory.LATEST_PATH.is_file()
        projection = json.loads(memory.LATEST_PATH.read_text(encoding="utf-8"))
        assert projection["schema"] == "venice-review-memory-latest-v1"
        rendered = memory.render_memory("/repo")
        assert "occurrence=2" in rendered
        assert "venice_bypass" in rendered
        assert "review receipt" in rendered

        passed = dict(receipt, directive="STOP_ALLOWED", verdict="PASS", findings=[])
        assert memory.persist_review(passed) == []
        assert len(memory.MEMORY_PATH.read_text(encoding="utf-8").splitlines()) == 2
    finally:
        memory.STATE_DIR, memory.MEMORY_PATH, memory.LATEST_PATH = old_state, old_memory, old_latest

print("Venice durable review memory contract: PASS")
