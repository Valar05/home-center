#!/usr/bin/env python3
import argparse, json, sys
from pathlib import Path
import hands_router as hr

def emit(job):
 print(json.dumps(job,indent=2)); return 0

def main():
 ap=argparse.ArgumentParser(prog='hands',description='Drew-first deterministic Phone/Computer Hands runner')
 sub=ap.add_subparsers(dest='cmd',required=True)
 run=sub.add_parser('run',help='queue a finite JSON step script'); run.add_argument('target'); run.add_argument('job_file'); run.add_argument('--transport',action='append',choices=hr.TRANSPORTS); run.add_argument('--ttl',type=int,default=900); run.add_argument('--max-runtime',type=int,default=120)
 op=sub.add_parser('op',help='queue one explicit operation'); op.add_argument('target'); op.add_argument('operation',choices=sorted(hr.OPS)); op.add_argument('--args',default='{}'); op.add_argument('--expect'); op.add_argument('--transport',action='append',choices=hr.TRANSPORTS); op.add_argument('--ttl',type=int,default=900); op.add_argument('--max-runtime',type=int,default=120)
 ex=sub.add_parser('exec',help='queue one bounded shell command'); ex.add_argument('target'); ex.add_argument('command',nargs=argparse.REMAINDER); ex.add_argument('--transport',action='append',choices=hr.TRANSPORTS); ex.add_argument('--ttl',type=int,default=900); ex.add_argument('--max-runtime',type=int,default=120)
 sub.add_parser('status'); sub.add_parser('on'); sub.add_parser('off'); sub.add_parser('drain').add_argument('--limit',type=int,default=8)
 a=ap.parse_args()
 if a.cmd=='run': return emit(hr.enqueue('drew',a.target,json.loads(Path(a.job_file).read_text()),a.transport,a.ttl,a.max_runtime))
 if a.cmd=='op':
  step={'op':a.operation,'args':json.loads(a.args)}
  if a.expect: step['expect']=json.loads(a.expect)
  return emit(hr.enqueue('drew',a.target,[step],a.transport,a.ttl,a.max_runtime))
 if a.cmd=='exec':
  if not a.command: ap.error('exec requires a command after target')
  cmd=' '.join(a.command)
  return emit(hr.enqueue('drew',a.target,[{'op':'shell.exec','args':{'command':cmd}}],a.transport,a.ttl,a.max_runtime))
 if a.cmd=='on': hr.set_enabled(True)
 elif a.cmd=='off': hr.set_enabled(False)
 elif a.cmd=='drain': print(json.dumps(hr.drain(a.limit),indent=2)); return 0
 print(json.dumps({'enabled':hr.enabled(),'queue':len(list(hr.QUEUE.glob('*.json'))) if hr.QUEUE.exists() else 0,'producer':'drew','transportOrder':list(hr.TRANSPORTS),'contract':'finite-script-v2'},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
