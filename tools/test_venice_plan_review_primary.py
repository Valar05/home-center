#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = ROOT / "tools" / "venice_plan_review.py"


def cmd(*args, cwd=None, check=True, env=None):
    return subprocess.run(args, cwd=cwd, check=check, text=True, capture_output=True, env=env)


def main():
    td = tempfile.TemporaryDirectory(prefix="venice-plan-primary-")
    repo = Path(td.name)
    try:
        cmd("git", "init", "-q", cwd=repo)
        cmd("git", "config", "user.email", "venice@example.invalid", cwd=repo)
        cmd("git", "config", "user.name", "Venice Test", cwd=repo)
        (repo / "README.md").write_text("x\n", encoding="utf-8")
        cmd("git", "add", ".", cwd=repo); cmd("git", "commit", "-qm", "base", cwd=repo)
        state = repo / "state"; state.mkdir()
        research = repo / "research.txt"; research.write_text("Authoritative repository inspected.\n", encoding="utf-8")
        plan = repo / "plan.txt"; plan.write_text("Make one bounded doctrine change and test it.\n", encoding="utf-8")
        antagonism = repo / "antagonism.txt"; antagonism.write_text("Risk: stale local-model Venice dependency.\n", encoding="utf-8")
        jar = repo / "jar.md"; jar.write_text("# Jar\nNo Venice receipt, no stop.\n", encoding="utf-8")
        review = repo / "review.txt"; review.write_text("VERDICT: PASS\nDIRECTIVE: PLAN_ALLOWED\nJAR: no Venice receipt, no stop\nNOTE: bounded plan is allowed\n", encoding="utf-8")
        env = os.environ.copy(); env["HC_STATE_DIR"] = str(state); env["VENICE_REVIEW_MEMORY"] = str(state / "venice" / "review-memory.jsonl")
        base = ["python3", str(REVIEWER), "--repo", str(repo), "--commission", "repair Venice doctrine", "--research-file", str(research), "--plan-file", str(plan), "--antagonism-file", str(antagonism), "--jar-file", str(jar), "--jar-rationale", "stop doctrine"]

        # No review text never invokes an implicit model; it remains REPLAN_REQUIRED.
        p = cmd(*base, check=False, env=env); receipt = json.loads(p.stdout)
        assert p.returncode == 1, receipt
        assert receipt["directive"] == "REPLAN_REQUIRED"
        assert receipt["reviewerMode"] == "judgment_jar_emulation"
        assert receipt["model"] is None and receipt["ollama"] is None
        assert "judgment_jar_plan_review_text_required" in receipt["findings"]

        # Primary ChatGPT Judgment-Jar text grants plan permission without Ollama.
        p = cmd(*base, "--review-text-file", str(review), check=False, env=env); receipt = json.loads(p.stdout)
        assert p.returncode == 0, receipt
        assert receipt["planPermissionGranted"] is True
        assert receipt["veniceReviewGateSatisfied"] is True
        assert receipt["reviewerMode"] == "judgment_jar_emulation"
        assert receipt["reviewer"] == "chatgpt-venice-judgment-jar"
        assert receipt["model"] is None and receipt["ollama"] is None
    finally:
        td.cleanup()
    print("Venice plan review primary Judgment-Jar mode: OK")


if __name__ == "__main__":
    main()
