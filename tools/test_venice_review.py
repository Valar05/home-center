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
    calls = 0
    def do_POST(self):
        type(self).calls += 1
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
        self.send_response(200); self.send_header("Content-Type", "application/json"); self.send_header("Content-Length", str(len(data))); self.end_headers(); self.wfile.write(data)
    def log_message(self, *_): pass


def cmd(*args, cwd=None, check=True, env=None): return subprocess.run(args, cwd=cwd, check=check, text=True, capture_output=True, env=env)
def git(repo, *args): return cmd("git", *args, cwd=repo)

def make_repo():
    td = tempfile.TemporaryDirectory(prefix="venice-review-"); repo = Path(td.name)
    git(repo, "init", "-q"); git(repo, "config", "user.email", "venice@example.invalid"); git(repo, "config", "user.name", "Venice Test")
    (repo / "a.py").write_text("print('before')\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "base")
    (repo / "a.py").write_text("print('after')\n"); git(repo, "add", "."); git(repo, "commit", "-qm", "change")
    return td, repo

def env_for(state):
    env = os.environ.copy(); env["HC_STATE_DIR"] = str(state); env["VENICE_REVIEW_MEMORY"] = str(state / "venice" / "review-memory.jsonl"); env["VENICE_REVIEW_MEMORY_LATEST"] = str(state / "venice" / "review-memory-latest.json"); return env

def review_file(state, verdict="PASS", directive="STOP_ALLOWED", finding=""):
    p = state / "review.txt"; lines=[f"VERDICT: {verdict}", f"DIRECTIVE: {directive}", "JAR: unknowns remain unknown"]
    if finding: lines.append(f"FINDING: {finding}")
    lines.append("NOTE: ChatGPT Judgment-Jar review")
    p.write_text("\n".join(lines)+"\n", encoding="utf-8"); return p

def run_primary(repo, state, review=None, extra=()):
    args=["python3",str(REVIEWER),"--repo",str(repo),"--base","HEAD~1","--head","HEAD","--acceptance","a.py should still be valid Python"]
    if review: args += ["--review-text-file", str(review)]
    args += list(extra)
    p=cmd(*args,check=False,env=env_for(state)); return p.returncode,json.loads(p.stdout)

def run_local(repo, host, state):
    p=cmd("python3",str(REVIEWER),"--repo",str(repo),"--base","HEAD~1","--head","HEAD","--acceptance","a.py should still be valid Python","--local-venice","--ollama",host,"--model","stub",check=False,env=env_for(state)); return p.returncode,json.loads(p.stdout)

def main():
    server=HTTPServer(("127.0.0.1",0),OllamaStub); thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start(); host=f"http://127.0.0.1:{server.server_port}"
    try:
        td,repo=make_repo(); state_td=tempfile.TemporaryDirectory(prefix="venice-state-"); state=Path(state_td.name)
        try:
            # Primary path is ChatGPT Judgment-Jar text; it must not call Ollama.
            OllamaStub.calls=0
            code,receipt=run_primary(repo,state,review_file(state))
            assert code==0,receipt
            assert receipt["schema"]=="venice-code-review-v4-judgment-jar-primary"
            assert receipt["reviewerMode"]=="judgment_jar_emulation"
            assert receipt["reviewer"]=="chatgpt-venice-judgment-jar"
            assert receipt["independentReviewPass"] is True
            assert receipt["independentOfChatGPT"] is False
            assert receipt["model"] is None and receipt["ollama"] is None
            assert receipt["stopPermissionGranted"] is True and receipt["veniceReviewGateSatisfied"] is True
            assert OllamaStub.calls==0

            # Missing semantic Jar ruling is CONTINUE_REQUIRED, never an implicit local-model call or stop.
            code,receipt=run_primary(repo,state)
            assert code==1
            assert receipt["directive"]=="CONTINUE_REQUIRED"
            assert "judgment_jar_review_text_required" in receipt["findings"]
            assert OllamaStub.calls==0

            code,receipt=run_primary(repo,state,review_file(state,"FAIL","CONTINUE_REQUIRED","worker stopped without Venice review receipt"))
            assert code==1 and receipt["continuationRequired"] is True and receipt["stopPermissionGranted"] is False
            assert receipt["durableMemoryEntriesWritten"]==1
            memory=Path(receipt["durableMemoryPath"]); assert memory.is_file()
            entries=[json.loads(x) for x in memory.read_text(encoding="utf-8").splitlines() if x.strip()]
            assert entries[-1]["category"]=="venice_bypass"

            code,receipt=run_primary(repo,state,review_file(state))
            assert code==0 and "worker stopped without Venice review receipt" in receipt["precedentLoaded"]

            code,receipt=run_primary(repo,state,review_file(state,"FAIL","HALT_REQUIRED","authority broken"))
            assert code==2 and receipt["haltRequired"] is True

            code,receipt=run_primary(repo,state,review_file(state,"PASS","CONTINUE_REQUIRED"))
            assert code==2 and receipt["verdict"]=="FAIL" and receipt["directive"]=="HALT_REQUIRED" and "inconsistent_pass_directive" in receipt["findings"]

            code,receipt=run_primary(repo,state,None,("--deterministic-only",))
            assert code==1 and "semantic_judgment_jar_review_not_run" in receipt["findings"]

            # Local Venice still exists, but only via explicit --local-venice.
            before=OllamaStub.calls; OllamaStub.verdict="PASS"; OllamaStub.directive="STOP_ALLOWED"; OllamaStub.finding=""
            code,receipt=run_local(repo,host,state)
            assert code==0 and receipt["reviewerMode"]=="local_venice" and receipt["reviewer"]=="venice-local"
            assert receipt["independentOfChatGPT"] is True and receipt["model"]=="stub" and OllamaStub.calls==before+1

            (repo/"bad.txt").write_text("<<<<<<< ours\n=======\n>>>>>>> theirs\n"); git(repo,"add","."); git(repo,"commit","-qm","bad")
            code,receipt=run_primary(repo,state,review_file(state))
            assert code==1 and receipt["continuationRequired"] is True
            assert any(x["name"]=="conflict_markers" and not x["ok"] for x in receipt["deterministicChecks"])
        finally:
            state_td.cleanup(); td.cleanup()
    finally:
        server.shutdown(); server.server_close()
    print("Venice review CLI primary Judgment-Jar + explicit local mode: OK")

if __name__=="__main__": main()
