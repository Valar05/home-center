#!/usr/bin/env python3
import importlib.util
import json
import tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
MOD_PATH=ROOT/"tools"/"vlad_swarm_daemon.py"

def load_module():
 spec=importlib.util.spec_from_file_location("vlad_swarm_daemon_test",MOD_PATH);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def write_job(state,**extra):
 inbox=state/"review-inbox";inbox.mkdir(parents=True,exist_ok=True)
 payload={"schema":"venice-review-queue-v2","repo":str(ROOT),"base":"HEAD~1","head":"HEAD","acceptance":"bounded test","reviewerMode":"judgment_jar_emulation","localVenice":False,**extra}
 job=inbox/"job.json";payload.setdefault("reviewTextPath",str(inbox/"job.review.txt"));job.write_text(json.dumps(payload)+"\n");return job,Path(payload["reviewTextPath"])

def fake_review_runner(directive,gate,expected_mode="judgment_jar_emulation"):
 def fake_run(cmd,timeout=20,cwd=None):
  receipt=Path(cmd[cmd.index("--receipt")+1]);receipt.parent.mkdir(parents=True,exist_ok=True)
  if expected_mode=="local_venice": assert "--local-venice" in cmd
  else:
   assert "--local-venice" not in cmd
   assert "--review-text-file" in cmd
  receipt.write_text(json.dumps({"schema":"venice-code-review-v4-judgment-jar-primary","reviewerMode":expected_mode,"directive":directive,"verdict":"PASS" if directive=="STOP_ALLOWED" else "FAIL","findings":[],"externalReviewGateSatisfied":gate})+"\n")
  return {"cmd":cmd,"rc":0 if gate else 1,"stdout":"","stderr":""}
 return fake_run

def exercise_primary(directive,gate):
 m=load_module()
 with tempfile.TemporaryDirectory(prefix="venice-directive-") as td:
  state=Path(td);m.STATE_DIR=state;job,review=write_job(state)
  review.write_text(f"VERDICT: {'PASS' if directive=='STOP_ALLOWED' else 'FAIL'}\nDIRECTIVE: {directive}\nJAR: observable evidence\nNOTE: test\n")
  m.run=fake_review_runner(directive,gate);m.process_review_inbox(str(ROOT))
  expected={"STOP_ALLOWED":"review-done","CONTINUE_REQUIRED":"review-continue","HALT_REQUIRED":"review-halt"}[directive]
  assert (state/expected/"job.json").exists(),(directive,list(state.rglob("*")))
  decision=json.loads((state/expected/"job.decision.json").read_text())
  assert decision["directive"]==directive
  assert decision["reviewerMode"]=="judgment_jar_emulation"

def main():
 # Missing ChatGPT/Jar review text is a durable waiting state, not fake halt/continue.
 m=load_module()
 with tempfile.TemporaryDirectory(prefix="venice-awaiting-") as td:
  state=Path(td);m.STATE_DIR=state;job,review=write_job(state)
  called=[]
  m.run=lambda *a,**k: called.append((a,k))
  m.process_review_inbox(str(ROOT))
  assert job.exists();assert not review.exists();assert called==[]
  last=json.loads((state/"last.json").read_text());assert last["kind"]=="venice.review.awaiting_chatgpt_judgment_jar";assert last["state"]=="awaiting_review"

 exercise_primary("STOP_ALLOWED",True);exercise_primary("CONTINUE_REQUIRED",False);exercise_primary("HALT_REQUIRED",False)

 # Explicit local mode is allowed, but only when the job opts in.
 m=load_module()
 with tempfile.TemporaryDirectory(prefix="venice-local-explicit-") as td:
  state=Path(td);m.STATE_DIR=state;job,_=write_job(state,reviewerMode="local_venice",localVenice=True)
  m.run=fake_review_runner("STOP_ALLOWED",True,"local_venice");m.process_review_inbox(str(ROOT))
  assert (state/"review-done"/"job.json").exists()

 # A forged STOP_ALLOWED whose canonical gate is unsatisfied fails closed into halt.
 m=load_module()
 with tempfile.TemporaryDirectory(prefix="venice-forged-stop-") as td:
  state=Path(td);m.STATE_DIR=state;job,review=write_job(state);review.write_text("VERDICT: PASS\nDIRECTIVE: STOP_ALLOWED\nJAR: fake\nNOTE: fake\n")
  m.run=fake_review_runner("STOP_ALLOWED",False);m.process_review_inbox(str(ROOT));assert (state/"review-halt"/"job.json").exists()
 print("Vlad swarm authorized Venice inbox enforcement: OK")
if __name__=="__main__":main()
