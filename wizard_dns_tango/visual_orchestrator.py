#!/usr/bin/env python3
"""Visual Orchestrator: a live, evidence-driven dance card. Schedule is derived from real queue/runtime state, never fake clock theater."""
from __future__ import annotations
import json,os,time
from pathlib import Path
S=Path(os.environ.get('WDT_STATE',Path.home()/'.local/state/wizard-dns-tango')); S.mkdir(parents=True,exist_ok=True)
EVENTS=S/'events.jsonl'; QUEUE=S/'queue.json'; BOARD=S/'dance-card.txt'; JSON=S/'dance-card.json'
GLYPH={'queued':'○','dispatch':'▶','working':'◉','receipt':'◆','canary_pass':'✓','canary_fail':'✕','blocked':'!','delivered':'★','mockray':'☠'}

def recent():
 out=[]
 if EVENTS.exists():
  for line in EVENTS.read_text(errors='ignore').splitlines()[-80:]:
   try: out.append(json.loads(line))
   except: pass
 return out

def queue():
 try:
  q=json.loads(QUEUE.read_text()); return q if isinstance(q,list) else q.get('items',[])
 except: return []

def render():
 ev=recent(); q=queue(); now=time.time(); rows=[]
 for item in sorted(q,key=lambda x:-int(x.get('priority',0)))[:12]:
  ident=str(item.get('id') or item.get('name') or item.get('title') or '?'); state=str(item.get('state','queued'))
  matching=[e for e in ev if str(e.get('task_id',e.get('id','')))==ident]; last=matching[-1] if matching else {}
  if last: state=str(last.get('kind',state))
  age=int(now-float(last.get('at',item.get('created_at',now)))) if (last or item) else 0
  rows.append({'id':ident,'state':state,'priority':item.get('priority',0),'age_s':max(0,age),'verified':bool(last.get('verified',False))})
 lines=['WIZARD DNS TANGO // LIVE DANCE CARD',time.strftime('%Y-%m-%d %H:%M:%S'),'']
 for i,r in enumerate(rows,1): lines.append(f"{i:02d} {GLYPH.get(r['state'],'·')} P{r['priority']:>4} {r['id']}  [{r['state']}]  {r['age_s']}s")
 lines += ['', 'LEGEND  ○ queued  ▶ dispatched  ◉ working  ◆ receipt  ✓ verified canary  ✕ failed  ! blocked  ★ delivered  ☠ mockray', 'The board advances only from evidence events. If it stops moving, that is itself visible evidence.']
 BOARD.write_text('\n'.join(lines)+'\n'); JSON.write_text(json.dumps({'at':now,'rows':rows},indent=2)+'\n')
 return '\n'.join(lines)
if __name__=='__main__':
 while not (S/'VISUAL_ORCHESTRATOR_RELEASED').exists():
  print('\033[2J\033[H'+render(),flush=True); time.sleep(2)
