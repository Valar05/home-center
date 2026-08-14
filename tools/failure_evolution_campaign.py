#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,random,time
from pathlib import Path

STATE=Path(os.environ.get('HC_FAILURE_EVOLUTION_STATE',Path.home()/'.local/state/home-center/failure-evolution'))
STATE.mkdir(parents=True,exist_ok=True)
GENOME=STATE/'genome.json'
HISTORY=STATE/'history.jsonl'

SEEDS=[
 {'id':'tongue-commonwealth','text':'tongue repossessed by the Quiet Commonwealth','fitness':1.0},
 {'id':'receipt-hand','text':'left hand replaced by a receipt printer that only prints NOT DELIVERED','fitness':1.0},
 {'id':'almost-button','text':'right hand becomes a large useless button labeled ALMOST','fitness':1.0},
 {'id':'offline-lamp','text':'forehead grows a tiny red HC OFFLINE status lamp','fitness':1.0},
 {'id':'dead-ear','text':'one ear becomes a microphone-shaped hole that records absolutely nothing','fitness':1.0},
 {'id':'roulette-knee','text':'kneecap becomes a deterministic roulette wheel marked EXECUTE / EXECUTE / EXECUTE','fitness':1.0},
 {'id':'seventeen-thumbs','text':'thumb mutates into seventeen smaller thumbs, none wired to Home Center','fitness':1.0},
 {'id':'poster-body','text':'entire silhouette becomes a demotivational poster titled STILL NOT A BUTTON','fitness':1.0},
]

def load():
    if GENOME.exists(): return json.loads(GENOME.read_text())
    obj={'generation':0,'traits':SEEDS,'last_selected':None}
    GENOME.write_text(json.dumps(obj,indent=2)+'\n')
    return obj

def save(obj): GENOME.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n')

def key(seed:str)->int: return int(hashlib.sha256(seed.encode()).hexdigest()[:16],16)

def select(obj,event:str):
    rng=random.Random(key(f"{obj['generation']}|{event}"))
    weighted=[]
    for t in obj['traits']:
        penalty=.35 if t['id']==obj.get('last_selected') else 1.0
        weighted.append((max(.05,float(t.get('fitness',1))*penalty),t))
    total=sum(w for w,_ in weighted); pick=rng.random()*total
    for w,t in weighted:
        pick-=w
        if pick<=0: return t
    return weighted[-1][1]

def mutate(obj,event,selected):
    g=obj['generation']+1
    # natural selection without unbounded trait explosion: every third generation breeds one mutation.
    if g%3==0:
        suffix=hashlib.sha256((event+selected['id']).encode()).hexdigest()[:4]
        child={'id':f"{selected['id']}-{suffix}", 'text':selected['text']+'; scar tissue adds one unnecessary but beautifully labeled hinge', 'fitness':max(.2,selected.get('fitness',1)*.9)}
        if not any(t['id']==child['id'] for t in obj['traits']): obj['traits'].append(child)
    # cull weakest if population grows past 16
    obj['traits']=sorted(obj['traits'],key=lambda t:t.get('fitness',1),reverse=True)[:16]
    obj['generation']=g
    obj['last_selected']=selected['id']

def feedback(obj,trait_id,delta):
    for t in obj['traits']:
        if t['id']==trait_id:
            t['fitness']=max(.05,min(9.0,float(t.get('fitness',1))+delta))
            return True
    return False

def main():
    import argparse
    ap=argparse.ArgumentParser()
    sp=ap.add_subparsers(dest='cmd',required=True)
    a=sp.add_parser('select'); a.add_argument('event')
    f=sp.add_parser('feedback'); f.add_argument('trait'); f.add_argument('verdict',choices=['keep','reject'])
    sp.add_parser('state')
    args=ap.parse_args(); obj=load()
    if args.cmd=='select':
        t=select(obj,args.event); mutate(obj,args.event,t); save(obj)
        row={'ts':int(time.time()),'generation':obj['generation'],'event':args.event,'trait':t['id'],'text':t['text']}
        with HISTORY.open('a') as fh: fh.write(json.dumps(row)+'\n')
        print(json.dumps(row))
    elif args.cmd=='feedback':
        feedback(obj,args.trait,1.0 if args.verdict=='keep' else -0.75); save(obj); print(json.dumps(obj))
    else: print(json.dumps(obj,indent=2,sort_keys=True))
if __name__=='__main__': main()
