#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("fortress_campaign", HERE / "fortress_campaign.py")
fc = importlib.util.module_from_spec(SPEC)
assert SPEC.loader
SPEC.loader.exec_module(fc)


def sh(cwd, *argv):
    return subprocess.run(argv, cwd=cwd, text=True, capture_output=True, check=True)


def test_dirty_tree_rescue_is_lossless_and_oid_stable():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td) / "repo"; root.mkdir()
        sh(root, "git", "init")
        sh(root, "git", "config", "user.email", "fortress@example.invalid")
        sh(root, "git", "config", "user.name", "Fortress Test")
        (root / "tracked.txt").write_text("before\n", encoding="utf-8")
        sh(root, "git", "add", "tracked.txt"); sh(root, "git", "commit", "-m", "base")
        (root / "tracked.txt").write_text("after\n", encoding="utf-8")
        (root / "untracked.txt").write_text("treasure\n", encoding="utf-8")

        state = Path(td) / "state"
        old = (fc.REPO, fc.STATE, fc.DB, fc.LOG)
        fc.REPO, fc.STATE, fc.DB, fc.LOG = root, state, state/"campaign.sqlite3", state/"campaign.jsonl"
        try:
            with fc.connect() as con:
                receipt = fc.dirty_tree_recovery(con)
            assert receipt["changed"] is True
            oid = receipt["stash"]["oid"]
            assert len(oid) >= 40
            status = sh(root, "git", "status", "--porcelain").stdout
            assert status == ""
            names = sh(root, "git", "stash", "show", "--include-untracked", "--name-only", oid).stdout
            assert "tracked.txt" in names and "untracked.txt" in names
            # Move the stash stack to prove the recorded OID, not stash@{0}, is the durable identity.
            (root / "second.txt").write_text("second\n", encoding="utf-8")
            sh(root, "git", "stash", "push", "-u", "-m", "second")
            sh(root, "git", "stash", "apply", "--index", oid)
            assert (root / "tracked.txt").read_text(encoding="utf-8") == "after\n"
            assert (root / "untracked.txt").read_text(encoding="utf-8") == "treasure\n"
        finally:
            fc.REPO, fc.STATE, fc.DB, fc.LOG = old


def test_mobile_url_parsing_keeps_secret_separate():
    p = fc.parse_mobile_url("http://192.168.1.22:17373/?token=abc123\nREPO_ROOT=C:\\work\\home-center\n")
    assert p == {"url": "http://192.168.1.22:17373", "token": "abc123"}


def test_missing_venice_cache_cannot_authorize_stop():
    with tempfile.TemporaryDirectory() as td:
        old_state, old_db, old_log, old_candidates = fc.STATE, fc.DB, fc.LOG, fc.JAR_CANDIDATES
        fc.STATE = Path(td); fc.DB = fc.STATE/"campaign.sqlite3"; fc.LOG = fc.STATE/"campaign.jsonl"; fc.JAR_CANDIDATES = []
        old_env = os.environ.pop("VLAD_JUDGMENT_JARS", None)
        try:
            mission = {"id": 1, "prompt": "x", "state": "reviewing", "attempt": 1}
            with fc.connect() as con:
                r = fc.venice_review(con, mission, "stop", [])
            assert r["verdict"] == "CONTINUE_REQUIRED"
            assert r["verdict"] != "STOP_ALLOWED"
        finally:
            if old_env is not None: os.environ["VLAD_JUDGMENT_JARS"] = old_env
            fc.STATE, fc.DB, fc.LOG, fc.JAR_CANDIDATES = old_state, old_db, old_log, old_candidates


def test_bootstrap_orders_dirty_recovery_before_branch_switch_and_uses_tmux():
    text = (HERE / "fortress_phone_swarm_bootstrap.sh").read_text(encoding="utf-8")
    assert text.index('say "1. Recover dirty tree"') < text.index('say "2. Enter exact campaign branch')
    assert "git stash apply" not in text  # bootstrap preserves; it never blindly reapplies onto a different lineage
    assert 'SESSION="fortress-swarm"' in text
    assert "tmux new-session" in text and "tmux new-window" in text
    assert 'rm -f "$BOOT/30-fortress-phone-kernel"' in text
    assert "diagnose --repair" in text


def main():
    tests = [v for k,v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for test in tests:
        test(); print("PASS", test.__name__)
    print(json.dumps({"ok": True, "tests": len(tests)}))


if __name__ == "__main__": main()
