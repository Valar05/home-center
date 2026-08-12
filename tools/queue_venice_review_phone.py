#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,time
from pathlib import Path
STATE=Path.home()/'.local/state/home-center/vlad-swarm/review-inbox'

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True)
    ap.add_argument('--base',default='HEAD~1')
    ap.add_argument('--head',default='HEAD')
    ap.add_argument('--acceptance',required=True)
    ap.add_argument('--timeout',type=int,default=240)
    a=ap.parse_args()
    STATE.mkdir(parents=True,exist_ok=True)
    job=STATE/f'fortress-{int(time.time()*1000)}.json'
    payload={'repo':a.repo,'base':a.base,'head':a.head,'acceptance':a.acceptance,'timeout':a.timeout}
    job.write_text(json.dumps(payload,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'schema':'venice-review-queue-v1','ok':True,'job':str(job)},sort_keys=True))
if __name__=='__main__': main()
