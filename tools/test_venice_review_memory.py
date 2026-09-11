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
        assert first[0]["classOccurrence"] == 1
        assert second[0]["classOccurrence"] == 2
        assert first[0]["fingerprint"] == second[0]["fingerprint"]
        rule = second[0]["rule"]
        assert "No worker may begin substantive execution" in rule
        assert "terminate" in rule
        assert "fresh Venice review receipt" in rule
        assert "RECURRENCE_RATCHET" in second[0]["recoveryRule"]
        assert "same explanatory load path" in second[0]["recoveryRule"]
        assert memory.MEMORY_PATH.is_file()
        lines = memory.MEMORY_PATH.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert memory.LATEST_PATH.is_file()
        projection = json.loads(memory.LATEST_PATH.read_text(encoding="utf-8"))
        assert projection["schema"] == "venice-review-memory-latest-v1"
        rendered = memory.render_memory("/repo")
        assert "occurrence=2" in rendered
        assert "classOccurrence=2" in rendered
        assert "RECURRENCE_RATCHET" in rendered
        assert "venice_bypass" in rendered
        assert "review receipt" in rendered

        # Different wording in the same failure class must still advance the class-level ratchet.
        correction_a = dict(
            receipt,
            findings=["user correction was forgotten and the same bad behavior happened again"],
            correctionRoute="prose",
        )
        correction_b = dict(
            receipt,
            findings=["regression reintroduced a previously corrected interpretation"],
            correctionRoute="screenshot",
        )
        corr_first = memory.persist_review(correction_a)[0]
        corr_second = memory.persist_review(correction_b)[0]
        assert corr_first["category"] == "correction_regression"
        assert corr_second["category"] == "correction_regression"
        assert corr_first["fingerprint"] != corr_second["fingerprint"]
        assert corr_first["occurrence"] == 1
        assert corr_second["occurrence"] == 1
        assert corr_first["classOccurrence"] == 1
        assert corr_second["classOccurrence"] == 2
        assert "RECURRENCE_RATCHET" in corr_second["recoveryRule"]
        assert "never require Drew to restate" in corr_second["recoveryRule"]
        assert "word, screenshot, example, gesture-description, or behavioral contradiction" in corr_second["recoveryRule"]
        assert "Preserve unresolved ambiguity" in corr_second["recoveryRule"]
        assert corr_first["correctionRoute"] == "prose"
        assert corr_second["correctionRoute"] == "screenshot"

        passed = dict(receipt, directive="STOP_ALLOWED", verdict="PASS", findings=[])
        assert memory.persist_review(passed) == []
        planned = dict(receipt, directive="PLAN_ALLOWED", verdict="PASS", findings=[])
        assert memory.persist_review(planned) == []
        assert len(memory.MEMORY_PATH.read_text(encoding="utf-8").splitlines()) == 4

        # Legacy v1 entries had only exact occurrence. Their existing recurrence count must seed
        # the new broader class counter instead of resetting history at upgrade time.
        legacy = {
            "schema": "venice-review-memory-v1",
            "repo": "/repo",
            "category": "code_review_omission",
            "finding": "legacy code review omission",
            "fingerprint": "legacy-code-review",
            "occurrence": 4,
        }
        with memory.MEMORY_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(legacy, sort_keys=True) + "\n")
        migrated = memory.persist_review(dict(
            receipt,
            findings=["code review regression test coverage missing"],
            correctionRoute="contract-test",
        ))[0]
        assert migrated["category"] == "code_review_omission"
        assert migrated["classOccurrence"] == 5
        assert "RECURRENCE_RATCHET" in migrated["recoveryRule"]
    finally:
        memory.STATE_DIR, memory.MEMORY_PATH, memory.LATEST_PATH = old_state, old_memory, old_latest

print("Venice durable review memory contract: PASS")
