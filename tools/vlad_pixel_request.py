#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,time
from pathlib import Path

def main():
    ap=argparse.ArgumentParser(prog='vlad-pixel-request')
    ap.add_argument('prompt')
    ap.add_argument('--seed',type=int,default=0)
    ap.add_argument('--width',type=int,default=512)
    ap.add_argument('--height',type=int,default=512)
    ap.add_argument('--steps',type=int,default=4)
    ap.add_argument('--cfg',type=float,default=1.0)
    ap.add_argument('--out',required=True)
    a=ap.parse_args()
    if not 1 <= len(a.prompt) <= 600: raise SystemExit('prompt length out of bounds')
    if a.width not in (256,384,512) or a.height not in (256,384,512): raise SystemExit('unsupported bounded dimensions')
    if not 1 <= a.steps <= 8: raise SystemExit('steps out of bounds')
    req={'schema':'vlad.pixel.request.v1','prompt':a.prompt,'seed':a.seed,'width':a.width,'height':a.height,'steps':a.steps,'cfg':a.cfg,'createdAtEpoch':int(time.time())}
    canonical=json.dumps(req,sort_keys=True,separators=(',',':')).encode()
    req['requestSha256']=hashlib.sha256(canonical).hexdigest()
    p=Path(a.out); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(req,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(req,sort_keys=True))
if __name__=='__main__': main()
