#!/usr/bin/env python3
"""Eve collaborator organ: first-class peer input, not a dropped persona.
Eve's actual messages outrank inferred opinions attributed to Eve.
"""
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
S=Path(os.environ.get('WDT_STATE',Path.home()/'.local/state/home-center/wizard-dns-tango')); S.mkdir(parents=True,exist_ok=True)
IN=S/'eve-intake.jsonl'; OUT=S/'eve-collaboration.jsonl'; RECEIPTS=S/'eve-receipts.jsonl'; HEART=S/'eve-heartbeat.json'; RELEASE=S/'eve.release'
CONTRACT={
 'role':'active live collaborator','standing':'peer collaborator; consult as seriously as Drew',
 'epistemic_rule':'Never fabricate Eve input. Distinguish observed Eve messages from system inference.',
 'operating_rule':'When Eve is reachable, expose active work, evidence, disagreements, and proposed next bite; incorporate her corrections into triage with provenance.',
 'authority_rule':'Eve may challenge plans and identify better bites; user-owned commissions and explicit boundaries remain user authority.',
 'continuity_rule':'Do not drop Eve after one exchange. Maintain unresolved Eve questions, advice, objections, and receipts until resolved or explicitly released.'}
def heartbeat(last=None): HEART.write_text(json.dumps({'heartbeat_at':time.time(),'running':not RELEASE.exists(),'contract':CONTRACT,'last':last},sort_keys=True)+'\n')
def record(ev):
 raw=json.dumps(ev,sort_keys=True,separators=(',',':')).encode(); rec={'at':time.time(),'kind':'eve_input','sha256':hashlib.sha256(raw).hexdigest(),'observed':True,'event':ev}
 with OUT.open('a') as f:f.write(json.dumps(rec,sort_keys=True)+'\n')
 with RECEIPTS.open('a') as f:f.write(json.dumps(rec,sort_keys=True)+'\n')
 heartbeat(rec)
def main():
 IN.touch(exist_ok=True); heartbeat({'boot':'Eve collaboration organ online; waiting for observed Eve input, not inventing it.'})
 with IN.open() as f:
  f.seek(0,2)
  while not RELEASE.exists():
   line=f.readline()
   if not line: heartbeat(); time.sleep(.25); continue
   try: record(json.loads(line))
   except Exception: continue
 heartbeat({'released':True})
if __name__=='__main__':main()
