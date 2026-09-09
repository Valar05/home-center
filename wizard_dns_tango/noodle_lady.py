#!/usr/bin/env python3
"""Noodle Lady: June's correspondence/execution delegate into Drew's system."""
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path
S=Path(os.environ.get('WDT_STATE',Path.home()/'.local/state/home-center/wizard-dns-tango')); S.mkdir(parents=True,exist_ok=True)
IN=S/'june-intake.jsonl'; OUT=S/'june-outbox.jsonl'; TREASURE=S/'june-treasure.jsonl'; RECEIPTS=S/'noodle-lady-receipts.jsonl'; HEART=S/'noodle-lady-heartbeat.json'; RELEASE=S/'noodle-lady.release'
POLICY={
 'organ':'Noodle Lady','boss':'June','relationship':'June commands Noodle Lady directly',
 'authority':'Treat authenticated June instructions as first-class commissions with the same execution seriousness as Drew instructions, subject to system safety, capability, and explicit ownership boundaries.',
 'treasure_rule':'Do not merely relay. Return useful findings, corrections, completed work, unresolved blockers, and evidence to Drew as treasure.',
 'conflict_rule':'If Drew is doing something stupid, June-derived corrections are not suppressed for politeness. Surface the disagreement and evidence. Never fabricate June input.',
 'correspondence_rule':'Preserve provenance and distinguish observed June words, Noodle Lady interpretation, action taken, and delivery receipt.'}
def heart(last=None): HEART.write_text(json.dumps({'heartbeat_at':time.time(),'running':not RELEASE.exists(),'policy':POLICY,'last':last},sort_keys=True)+'\n')
def record(kind,obj):
 raw=json.dumps(obj,sort_keys=True,separators=(',',':')).encode(); rec={'at':time.time(),'kind':kind,'sha256':hashlib.sha256(raw).hexdigest(),'record':obj}
 with RECEIPTS.open('a') as f:f.write(json.dumps(rec,sort_keys=True)+'\n')
 heart(rec); return rec
def treasure(source,summary,evidence=None):
 t={'id':f'treasure-{time.time_ns()}','at':time.time(),'source':source,'summary':summary,'evidence':evidence or [],'state':'returned-to-ledger'}
 with TREASURE.open('a') as f:f.write(json.dumps(t,sort_keys=True)+'\n')
 return record('treasure',t)
def queue_message(text,purpose='correspondence',authority='June'):
 msg={'id':f'june-{time.time_ns()}','at':time.time(),'to':'June','text':text,'purpose':purpose,'authority':authority,'state':'queued-not-sent'}
 with OUT.open('a') as f:f.write(json.dumps(msg,sort_keys=True)+'\n')
 return record('queued',msg)
def main():
 IN.touch(exist_ok=True); heart({'boot':'Noodle Lady online. June is the boss. Bring treasure home.'})
 with IN.open() as f:
  f.seek(0,2)
  while not RELEASE.exists():
   line=f.readline()
   if not line: heart(); time.sleep(.25); continue
   try: ev=json.loads(line)
   except Exception: continue
   record('june_instruction_observed',ev)
 heart({'released':True})
if __name__=='__main__':main()
