#!/usr/bin/env python3
"""Runtime Foley: synthesize evidence-bound sound, store the exact WAV, hash it, receipt it, optionally play it."""
from __future__ import annotations
import hashlib,json,math,os,random,struct,subprocess,time,wave
from pathlib import Path
STATE=Path(os.environ.get('WDT_STATE',Path.home()/'.local/state/wizard-dns-tango'))
EVENTS=STATE/'events.jsonl'; AUDIO=STATE/'foley'; RECEIPTS=STATE/'foley-receipts.jsonl'; RELEASE=STATE/'FOLEY_RELEASED'
AUDIO.mkdir(parents=True,exist_ok=True)
MAP={
'dispatch':('ratchet',220),'working':('loom',330),'receipt':('stamp',440),'canary_pass':('chime',660),
'canary_fail':('clank',140),'blocked':('hollow',110),'delivered':('bell',880),'mockray':('squawk',185)
}
def synth(kind,evidence):
    if kind in {'delivered','canary_pass'} and not evidence.get('verified',False): kind='mockray'
    name,hz=MAP.get(kind,MAP['working']); sr=16000; dur=.18 if kind=='working' else .32
    seed=int(hashlib.sha256(json.dumps(evidence,sort_keys=True).encode()).hexdigest()[:8],16); rng=random.Random(seed)
    samples=[]
    for i in range(int(sr*dur)):
        t=i/sr; env=max(0,1-t/dur)**2
        tone=math.sin(2*math.pi*hz*t)+.35*math.sin(2*math.pi*hz*2.01*t)
        noise=(rng.random()*2-1)*(.18 if kind in {'mockray','canary_fail'} else .05)
        samples.append(int(max(-1,min(1,(tone*.45+noise)*env))*32767))
    stamp=time.strftime('%Y%m%d-%H%M%S'); p=AUDIO/f'{stamp}-{time.time_ns()}-{kind}-{name}.wav'
    with wave.open(str(p),'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(b''.join(struct.pack('<h',x) for x in samples))
    sha=hashlib.sha256(p.read_bytes()).hexdigest()
    rec={'at':time.time(),'kind':kind,'foley':name,'path':str(p),'sha256':sha,'bytes':p.stat().st_size,'evidence':evidence}
    with RECEIPTS.open('a') as f:f.write(json.dumps(rec,sort_keys=True)+'\n')
    for player in (['termux-media-player','play',str(p)],['ffplay','-nodisp','-autoexit','-loglevel','quiet',str(p)]):
        try:
            if subprocess.run(player,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=2).returncode==0: break
        except Exception: pass
    return rec

def tail():
    EVENTS.touch(exist_ok=True)
    with EVENTS.open() as f:
        f.seek(0,2)
        while not RELEASE.exists():
            line=f.readline()
            if not line: time.sleep(.25); continue
            try: ev=json.loads(line)
            except Exception: continue
            kind=str(ev.get('kind','working'))
            if kind in MAP: synth(kind,ev)
if __name__=='__main__':tail()
