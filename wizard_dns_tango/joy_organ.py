#!/usr/bin/env python3
"""Flesh Pump: joy is an evidence projection, never a substitute for delivery."""
from __future__ import annotations
import hashlib,json,math,os,random,struct,subprocess,time,wave
from pathlib import Path
S=Path(os.environ.get('WDT_STATE',Path.home()/'.local/state/home-center/wizard-dns-tango')); S.mkdir(parents=True,exist_ok=True)
EVENTS=S/'events.jsonl'; HEART=S/'joy_heartbeat.json'; RECEIPTS=S/'joy-receipts.jsonl'; AUDIO=S/'joy-audio'; AUDIO.mkdir(exist_ok=True); RELEASE=S/'joy.release'
# Andrew governs escalation: evidence earns pressure; failures make the organ funnier, not falsely triumphant.
WEIGHT={'whale_bite':1,'dispatch':1,'working':1,'receipt':2,'canary_pass':3,'delivered':5,'canary_fail':0,'blocked':0,'mockray':0}

def write_heart(last=None): HEART.write_text(json.dumps({'heartbeat_at':time.time(),'running':not RELEASE.exists(),'last':last},sort_keys=True)+'\n')
def vibrate(pattern):
 if not subprocess.call(['sh','-c','command -v termux-vibrate >/dev/null 2>&1']):
  for ms,gap in pattern:
   subprocess.run(['termux-vibrate','-d',str(ms),'-f'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); time.sleep(gap)
def tone(event,level):
 sr=16000; dur=.12+.035*min(level,8); seed=int(hashlib.sha256(json.dumps(event,sort_keys=True).encode()).hexdigest()[:8],16); rng=random.Random(seed); base=180+level*55
 p=AUDIO/f"{int(time.time()*1000)}-{event.get('kind','event')}-L{level}.wav"
 vals=[]
 for i in range(int(sr*dur)):
  t=i/sr; env=(1-t/dur)**2; sparkle=.22*math.sin(2*math.pi*(base*2.01)*t); grit=(rng.random()*2-1)*(.08 if level<3 else .04); x=(.45*math.sin(2*math.pi*base*t)+sparkle+grit)*env; vals.append(int(max(-1,min(1,x))*32767))
 with wave.open(str(p),'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(sr);w.writeframes(b''.join(struct.pack('<h',x) for x in vals))
 sha=hashlib.sha256(p.read_bytes()).hexdigest(); return str(p),sha

def project(ev,level):
 kind=ev.get('kind','working'); verified=bool(ev.get('verified',False)); earned=WEIGHT.get(kind,0)
 # Never celebrate an unverified success claim.
 if kind in {'canary_pass','delivered'} and not verified: earned=0; kind='mockray'
 level=max(0,min(12,level+earned-(1 if kind in {'blocked','canary_fail'} else 0)))
 if kind in {'blocked','canary_fail','mockray'}: pattern=[(35,.05),(35,.05),(120,.08)]
 else: pattern=[(25+level*4,.04)]*(1+min(3,level//3))
 vibrate(pattern); path,sha=tone(ev,level)
 rec={'at':time.time(),'kind':kind,'level':level,'earned':earned,'source_event':ev,'audio_path':path,'audio_sha256':sha}
 with RECEIPTS.open('a') as f:f.write(json.dumps(rec,sort_keys=True)+'\n')
 write_heart(rec); return level

def main():
 EVENTS.touch(exist_ok=True); level=0; write_heart({'boot':'Flesh Pump online; Andrew escalation authority active'})
 with EVENTS.open() as f:
  f.seek(0,2)
  while not RELEASE.exists():
   line=f.readline()
   if not line: write_heart(); time.sleep(.2); continue
   try: ev=json.loads(line)
   except Exception: continue
   if ev.get('kind') in WEIGHT: level=project(ev,level)
 write_heart({'released':True})
if __name__=='__main__':main()
