#!/usr/bin/env python3
import json
import os
import subprocess
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEWER = ROOT / "tools" / "venice_review.py"


class OllamaStub(BaseHTTPRequestHandler):
    verdict = "PASS"
    directive = "STOP_ALLOWED"
    finding = ""
    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size) or b"{}")
        assert body.get("stream") is False
        assert body.get("options", {}).get("temperature") == 0
        prompt = body.get("prompt", "")
        assert "Judgment Jar" in prompt
        assert "DURABLE VENICE REVIEW PRECEDENT" in prompt
        finding = f"\nFINDING: {self.finding}" if self.finding else ""
        response = {"response": f"VERDICT: {self.verdict}\nDIRECTIVE: {self.directive}\nJAR: unknowns remain unknown{finding}\nNOTE: deterministic stub review"}
        data = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *_): pass


def cmd(*args, cwd=None, check=True, env=None): return subprocess.run(args, cwd=cwd, check=check, text=True, capture_output=True, env=env)
def git(repo, *args): return cmd("git", *args, cwd=repo)

def make_repo():
    td = tempfile.TemporaryDirectory(prefix="venice-review-")
    repo = Path(td.name)
    git(repo, "init", "-q"); git(repo, "config", "user.email", "venice@example.invalid"); git(repo, "config", "user.name", "Venice Test")
    (repo / "a.py").write_text("print('before')\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "base")
    (repo / "a.py").write_text("print('after')\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "change")
    return td, repo

def run_review(repo, host, state, extra=()):
    env = os.environ.copy()
    env["HC_STATE_DIR"] = str(state)
    env["VENICE_REVIEW_MEMORY"] = str(state / "venice" / "review-memory.jsonl")
    env["VENICE_REVIEW_MEMORY_LATEST"] = str(state / "venice" / "review-memory-latest.json")
    p = cmd("python3", str(REVIEWER), "--repo", str(repo), "--base", "HEAD~1", "--head", "HEAD", "--ollama", host, "--model", "stub", "--acceptance", "a.py should still be valid Python", *extra, check=False, env=env)
    return p.returncode, json.loads(p.stdout)

def main():
    server = HTTPServer(("127.0.0.1", 0), OllamaStub); thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start(); host=f"http://127.0.0.1:{server.server_port}"
    try:
        td, repo = make_repo()
        state_td = tempfile.TemporaryDirectory(prefix="venice-state-")
        state = Path(state_td.name)
        try:
            OllamaStub.verdict="PASS"; OllamaStub.directive="STOP_ALLOWED"; OllamaStub.finding=""
            code, receipt = run_review(repo, host, state)
            assert code == 0, receipt
            assert receipt["schema"] == "venice-code-review-v3-memory"
            assert receipt["verdict"] == "PASS"
            assert receipt["directive"] == "STOP_ALLOWED"
            assert receipt["stopPermissionGranted"] is True
            assert receipt["continuationRequired"] is False
            assert receipt["externalReviewGateSatisfied"] is True
            assert receipt["judgmentJarApplied"]
            assert receipt["durableMemoryEntriesWritten"] == 0

            OllamaStub.verdict="FAIL"; OllamaStub.directive="CONTINUE_REQUIRED"; OllamaStub.finding="worker stopped without Venice review receipt"
            code, receipt = run_review(repo, host, state)
            assert code == 1
            assert receipt["stopPermissionGranted"] is False
            assert receipt["continuationRequired"] is True
            assert receipt["haltRequired"] is False
            assert receipt["durableMemoryEntriesWritten"] == 1
            memory = Path(receipt["durableMemoryPath"])
            assert memory.is_file()
            entries = [json.loads(x) for x in memory.read_text(encoding="utf-8").splitlines() if x.strip()]
            assert entries[-1]["category"] == "venice_bypass"

            # A later review must load the prior scar into its prompt; the stub asserts the section exists.
            OllamaStub.verdict="PASS"; OllamaStub.directive="STOP_ALLOWED"; OllamaStub.finding=""
            code, receipt = run_review(repo, host, state)
            assert code == 0
            assert "worker stopped without Venice review receipt" in receipt["precedentLoaded"]

            OllamaStub.verdict="FAIL"; OllamaStub.directive="HALT_REQUIRED"; OllamaStub.finding="authority broken"
            code, receipt = run_review(repo, host, state)
            assert code == 2
            assert receipt["haltRequired"] is True

            OllamaStub.verdict="PASS"; OllamaStub.directive="CONTINUE_REQUIRED"; OllamaStub.finding=""
            code, receipt = run_review(repo, host, state)
            assert code == 2
            assert receipt["verdict"] == "FAIL"
            assert receipt["directive"] == "HALT_REQUIRED"
            assert "inconsistent_pass_directive" in receipt["findings"]

            code, receipt = run_review(repo, host, state, ("--deterministic-only",))
            assert code == 1
            assert receipt["stopPermissionGranted"] is False
            assert receipt["continuationRequired"] is True
            assert "semantic_external_review_not_run" in receipt["findings"]

            (repo / "bad.txt").write_text("<<<<<<< ours\n=======\n>>>>>>> theirs\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "bad")
            code, receipt = run_review(repo, host, state)
            assert code == 1
            assert receipt["stopPermissionGranted"] is False
            assert receipt["continuationRequired"] is True
            assert any(x["name"] == "conflict_markers" and not x["ok"] for x in receipt["deterministicChecks"])
        finally:
            state_td.cleanup(); td.cleanup()
    finally: server.shutdown(); server.server_close()
    print("Venice review CLI v3 + durable memory: OK")

if __name__ == "__main__": main()
