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
    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = json.loads(self.rfile.read(size) or b"{}")
        assert body.get("stream") is False
        assert body.get("options", {}).get("temperature") == 0
        response = {"response": f"VERDICT: {self.verdict}\nNOTE: deterministic stub review"}
        data = json.dumps(response).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)
    def log_message(self, *_):
        pass


def cmd(*args, cwd=None, check=True):
    return subprocess.run(args, cwd=cwd, check=check, text=True, capture_output=True)


def git(repo, *args):
    return cmd("git", *args, cwd=repo)


def make_repo():
    td = tempfile.TemporaryDirectory(prefix="venice-review-")
    repo = Path(td.name)
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "venice@example.invalid")
    git(repo, "config", "user.name", "Venice Test")
    (repo / "a.py").write_text("print('before')\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "base")
    (repo / "a.py").write_text("print('after')\n")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "change")
    return td, repo


def run_review(repo, host, extra=()):
    p = cmd("python3", str(REVIEWER), "--repo", str(repo), "--base", "HEAD~1", "--head", "HEAD", "--ollama", host, "--model", "stub", "--acceptance", "a.py should still be valid Python", *extra, check=False)
    return p.returncode, json.loads(p.stdout)


def main():
    server = HTTPServer(("127.0.0.1", 0), OllamaStub)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host = f"http://127.0.0.1:{server.server_port}"
    try:
        td, repo = make_repo()
        try:
            code, receipt = run_review(repo, host)
            assert code == 0, receipt
            assert receipt["verdict"] == "PASS"
            assert receipt["externalReviewGateSatisfied"] is True
            assert receipt["independentOfChatGPT"] is True
            assert receipt["model"] == "stub"

            code, receipt = run_review(repo, host, ("--deterministic-only",))
            assert code == 1
            assert receipt["externalReviewGateSatisfied"] is False
            assert "semantic_external_review_not_run" in receipt["findings"]

            (repo / "bad.txt").write_text("<<<<<<< ours\n=======\n>>>>>>> theirs\n")
            git(repo, "add", ".")
            git(repo, "commit", "-qm", "bad")
            code, receipt = run_review(repo, host)
            assert code == 1
            assert receipt["externalReviewGateSatisfied"] is False
            assert any(x["name"] == "conflict_markers" and not x["ok"] for x in receipt["deterministicChecks"])
        finally:
            td.cleanup()
    finally:
        server.shutdown()
        server.server_close()
    print("Venice review CLI: OK")


if __name__ == "__main__":
    main()
