#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, re, time
from pathlib import Path
from android_operator_overlay import update as overlay_update
from android_phone_status_tts import execute as tts_execute

STATE=Path.home()/'.local/state/home-center/venice-reactor'
TRANSCRIPTS=STATE/'transcripts.jsonl'

RULES=[
 (re.compile(r'\b(kill|murder|dead|dies|blood)\b',re.I),'That escalated quickly.'),
 (re.compile(r'\b(love|kiss|beautiful|darling)\b',re.I),'Oh, now we are paying attention.'),
 (re.compile(r'\b(run|hurry|escape|behind you)\b',re.I),'Move. Move. Move.'),
 (re.compile(r'\b(what|why|how|who)\b',re.I),'Excellent question. Suspicious timing.'),
 (re.compile(r'\b(sorry|forgive|apolog)\w*\b',re.I),'Mm. We will see if they earned that.'),
]

def react(text:str)->str:
 text=' '.join(str(text or '').split())
 for rx,line in RULES:
  if rx.search(text): return line
 words=text.split()
 if not words: return ''
 return 'I heard that.' if len(words)<8 else 'I am listening. Keep going.'

def ingest(text:str, source='phone-audio', speak=True):
 STATE.mkdir(parents=True,exist_ok=True)
 clean=' '.join(str(text or '').split())
 if not clean: return {'ok':True,'skipped':True}
 line=react(clean)
 event={'ts':time.time(),'source':source,'transcript':clean,'reaction':line}
 with TRANSCRIPTS.open('a',encoding='utf-8') as f: f.write(json.dumps(event,ensure_ascii=False)+'\n')
 overlay_update('VENICE LISTENS\n'+clean+'\n\nVENICE\n'+line,'Venice')
 if speak and line: tts_execute({'action':'status_say','text':line})
 return {'ok':True,**event,'transcriptPath':str(TRANSCRIPTS)}

def mine(limit=200):
 if not TRANSCRIPTS.exists(): return {'ok':True,'events':0,'phrases':[]}
 rows=[]
 for raw in TRANSCRIPTS.read_text(encoding='utf-8').splitlines()[-limit:]:
  try: rows.append(json.loads(raw))
  except Exception: pass
 counts={}
 for row in rows:
  for token in re.findall(r"[A-Za-z']{4,}",row.get('transcript','').lower()): counts[token]=counts.get(token,0)+1
 return {'ok':True,'events':len(rows),'phrases':sorted(counts.items(),key=lambda x:(-x[1],x[0]))[:20]}

def execute(payload):
 action=str(payload.get('action') or 'ingest')
 if action=='ingest': return ingest(payload.get('text',''),payload.get('source','phone-audio'),bool(payload.get('speak',True)))
 if action=='mine': return mine(int(payload.get('limit',200)))
 if action=='status': return {'ok':True,'transcriptPath':str(TRANSCRIPTS),'exists':TRANSCRIPTS.exists()}
 raise ValueError('unsupported Venice reactor action: '+action)

if __name__=='__main__':
 import sys
 print(json.dumps(execute(json.loads(sys.stdin.read() or '{}')),ensure_ascii=False))
