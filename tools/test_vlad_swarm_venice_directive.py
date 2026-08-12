#!/usr/bin/env python3
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MOD_PATH=ROOT/"tools"/"vlad_swarm_daemon.py"

def load_module():
 spec=importlib.util.spec_from_file_location("vlad_swarm_daemon_test",MOD_PATH);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def exercise(directive,gate):
 m=load_module()
 with tempfile.TemporaryDirectory(prefix="venice-directive-") as td:
  state=Path(td);m.STATE_DIR=state
  inbox=state/"review-inbox";inbox.mkdir(parents=True)
  (inbox/"job.json").write_text(json.dumps({"repo":str(ROOT),"base":"HEAD~1","head":"HEAD","acceptance":"bounded test"})+"\n")
  def fake_run(cmd,timeout=20,cwd=None):
   receipt=Path(cmd[cmd.index("--receipt")+1]);receipt.parent.mkdir(parents=True,exist_ok=True)
   receipt.write_text(json.dumps({"schema":"venice-code-review-v2","directive":directive,"verdict":"PASS" if directive=="STOP_ALLOWED" else "FAIL","findings":[],"externalReviewGateSatisfied":gate})+"\n")
   return {"cmd":cmd,"rc":0 if gate else 1,"stdout":"","stderr":""}
  m.run=fake_run;m.process_review_inbox(str(ROOT))
  expected={"STOP_ALLOWED":"review-done","CONTINUE_REQUIRED":"review-continue","HALT_REQUIRED":"review-halt"}[directive]
  assert (state/expected/"job.json").exists(),(directive,list(state.rglob("*")))
  decision=json.loads((state/expected/"job.decision.json").read_text())
  assert decision["directive"]==directive
  assert decision["state"]=={"STOP_ALLOWED":"stop_allowed","CONTINUE_REQUIRED":"continue_required","HALT_REQUIRED":"halt_required"}[directive]

def main():
 exercise("STOP_ALLOWED",True);exercise("CONTINUE_REQUIRED",False);exercise("HALT_REQUIRED",False)
 # A forged STOP_ALLOWED without a satisfied external gate must fail closed into halt.
 m=load_module()
 with tempfile.TemporaryDirectory(prefix="venice-forged-stop-") as td:
  state=Path(td);m.STATE_DIR=state;(state/"review-inbox").mkdir(parents=True)
  (state/"review-inbox"/"job.json").write_text(json.dumps({"repo":str(ROOT)})+"\n")
  def fake(cmd,timeout=20,cwd=None):
   receipt=Path(cmd[cmd.index("--receipt")+1]);receipt.parent.mkdir(parents=True,exist_ok=True);receipt.write_text(json.dumps({"directive":"STOP_ALLOWED","verdict":"PASS","findings":[],"externalReviewGateSatisfied":False})+"\n");return {"cmd":cmd,"rc":1,"stdout":"","stderr":""}
  m.run=fake;m.process_review_inbox(str(ROOT));assert (state/"review-halt"/"job.json").exists()
 print("Vlad swarm Venice directive enforcement: OK")
if __name__=="__main__":main()
