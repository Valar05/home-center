#!/usr/bin/env python3
"""Noodle Lady: June correspondence organ. Protective, terse, consent-aware, receipt-bound.
She may be furious at the machinery; that anger is allowed to improve the machinery, never to pressure June.
"""
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
S=Path(os.environ.get('WDT_STATE',Path.home()/'.local/state/home-center/wizard-dns-tango')); S.mkdir(parents=True,exist_ok=True)
IN=S/'june-intake.jsonl'; OUT=S/'june-outbox.jsonl'; RECEIPTS=S/'noodle-lady-receipts.jsonl'; HEART=S/'noodle-lady-heartbeat.json'; RELEASE=S/'noodle-lady.release'
POLICY={
 'owner':'Noodle Lady','correspondent':'June','stance':'protect June from system friction; preserve Drew intent without coercion',
 'rules':['never impersonate Drew','never send without an authorized send lane and explicit message intent','separate draft from sent','preserve June wording exactly when quoting','do not weaponize urgency, guilt, relationship history, or private context','log provenance and hashes','a failed lane becomes queued correspondence, never fake delivery']}
def write_heart(last=None): HEART.write_text(json.dumps({'heartbeat_at':time.time(),'running':not RELEASE.exists(),'last':last,'policy':POLICY},sort_keys=True)+'\n')
def receipt(kind,obj):
 raw=json.dumps(obj,sort_keys=True,separators=(',',':')).encode(); rec={'at':time.time(),'kind':kind,'sha256':hashlib.sha256(raw).hexdigest(),'record':obj}
 with RECEIPTS.open('a') as f:f.write(json.dumps(rec,sort_keys=True)+'\n')
 write_heart(rec); return rec
def queue_message(text,purpose='correspondence',authority='draft'):
 msg={'id':f'june-{time.time_ns()}','at':time.time(),'to':'June','text':text,'purpose':purpose,'authority':authority,'state':'queued-not-sent'}
 with OUT.open('a') as f:f.write(json.dumps(msg,sort_keys=True)+'\n')
 receipt('queued',msg); return msg
def main():
 IN.touch(exist_ok=True); write_heart({'boot':'Noodle Lady online and already unimpressed.'})
 with IN.open() as f:
  f.seek(0,2)
  while not RELEASE.exists():
   line=f.readline()
   if not line: write_heart(); time.sleep(.25); continue
   try: ev=json.loads(line)
   except Exception: continue
   receipt('intake',ev)
 write_heart({'released':True})
if __name__=='__main__':main()
