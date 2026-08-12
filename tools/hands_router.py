#!/usr/bin/env python3
import argparse, base64, hashlib, hmac, json, os, secrets, shlex, subprocess, time
from pathlib import Path

STATE=Path(os.environ.get('HC_HANDS_ROUTER_STATE','~/.local/state/home-center/hands-router')).expanduser()
KEY=Path(os.environ.get('HC_HANDS_ROUTER_KEY','~/.config/home-center/hands-router.key')).expanduser()
TOGGLE=STATE/'enabled'
QUEUE=STATE/'queue'; DONE=STATE/'done'; RECEIPTS=STATE/'receipts.jsonl'
PRODUCERS={'vlad','venice','adam','fortress'}
TRANSPORTS=('ssh','wlan','computer_hands')
# Exact, high-confidence destructive signatures only. Everything else is routed, not moralized.
HARMFUL=(
 'rm -rf /','rm -rf /*','mkfs.','wipefs ','dd if=/dev/zero of=/dev/','dd if=/dev/random of=/dev/',
 'shutdown -h','shutdown /s','poweroff','reboot','format c:','diskpart /s','bcdedit /delete','cipher /w:'
)

def _mkdirs():
 for p in (STATE,QUEUE,DONE,KEY.parent): p.mkdir(parents=True,exist_ok=True)

def _key():
 _mkdirs()
 if not KEY.exists():
  KEY.write_bytes(secrets.token_bytes(32)); os.chmod(KEY,0o600)
 return KEY.read_bytes()

def enabled():
 return not TOGGLE.exists() or TOGGLE.read_text().strip().lower() not in {'0','off','false','disabled'}

def set_enabled(v):
 _mkdirs(); TOGGLE.write_text('1\n' if v else '0\n'); return v

def canonical(job):
 x={k:v for k,v in job.items() if k!='sig'}
 return json.dumps(x,sort_keys=True,separators=(',',':')).encode()

def sign(job): return hmac.new(_key(),canonical(job),hashlib.sha256).hexdigest()
def verify(job): return hmac.compare_digest(str(job.get('sig','')),sign(job))

def objectively_harmful(job):
 if job.get('harm') is True: return 'explicit_harm_flag'
 text=' '.join(str(job.get(k,'')) for k in ('command','payload')).lower().strip()
 for s in HARMFUL:
  if s in text: return 'destructive_signature:'+s
 return None

def enqueue(producer,target,action,payload=None,command=None,transports=None,ttl=900):
 if producer not in PRODUCERS: raise ValueError('unknown producer')
 now=int(time.time()); jid=f'{now}-{secrets.token_hex(6)}'
 job={'schema':'hands-router-job-v1','id':jid,'producer':producer,'target':target,'action':action,'payload':payload,'command':command,'transports':transports or list(TRANSPORTS),'createdAt':now,'expiresAt':now+int(ttl)}
 job['sig']=sign(job); _mkdirs(); (QUEUE/f'{jid}.json').write_text(json.dumps(job,indent=2,sort_keys=True)+'\n')
 return job

def _receipt(job,status,**extra):
 rec={'schema':'hands-router-receipt-v1','id':job.get('id'),'producer':job.get('producer'),'target':job.get('target'),'action':job.get('action'),'status':status,'at':int(time.time()),**extra}
 _mkdirs()
 with RECEIPTS.open('a') as f:f.write(json.dumps(rec,sort_keys=True)+'\n')
 return rec

def _run_template(env_name,job,timeout=120):
 template=os.environ.get(env_name,'').strip()
 if not template: return None
 blob=base64.urlsafe_b64encode(json.dumps(job,separators=(',',':')).encode()).decode()
 cmd=template.replace('{job_b64}',shlex.quote(blob)).replace('{target}',shlex.quote(str(job['target'])))
 p=subprocess.run(cmd,shell=True,text=True,capture_output=True,timeout=timeout)
 return {'rc':p.returncode,'stdout':p.stdout[-8000:],'stderr':p.stderr[-8000:]}

def dispatch(job):
 if not enabled(): return _receipt(job,'paused')
 if not verify(job): return _receipt(job,'rejected',reason='bad_signature')
 if int(job.get('expiresAt',0))<int(time.time()): return _receipt(job,'expired')
 harm=objectively_harmful(job)
 if harm: return _receipt(job,'blocked',reason=harm)
 envs={'ssh':'HC_HANDS_SSH_DISPATCH','wlan':'HC_HANDS_WLAN_DISPATCH','computer_hands':'HC_HANDS_COMPUTER_DISPATCH'}
 attempts=[]
 for t in job.get('transports') or TRANSPORTS:
  if t not in envs: continue
  try:r=_run_template(envs[t],job)
  except Exception as e:r={'rc':125,'stderr':f'{type(e).__name__}: {e}','stdout':''}
  if r is None: attempts.append({'transport':t,'status':'unconfigured'}); continue
  attempts.append({'transport':t,**r})
  if r['rc']==0:return _receipt(job,'completed',transport=t,attempts=attempts)
 return _receipt(job,'failed',attempts=attempts)

def drain(limit=8):
 _mkdirs(); out=[]
 for path in sorted(QUEUE.glob('*.json'))[:limit]:
  try:job=json.loads(path.read_text()); rec=dispatch(job)
  except Exception as e: job={'id':path.stem}; rec=_receipt(job,'failed',reason=f'parse_or_dispatch:{type(e).__name__}:{e}')
  out.append(rec)
  if rec['status']!='paused': path.rename(DONE/path.name)
 return out

def main():
 ap=argparse.ArgumentParser(prog='hands-router'); sub=ap.add_subparsers(dest='cmd',required=True)
 e=sub.add_parser('enqueue'); e.add_argument('--producer',required=True,choices=sorted(PRODUCERS)); e.add_argument('--target',required=True); e.add_argument('--action',required=True); e.add_argument('--payload'); e.add_argument('--command'); e.add_argument('--transport',action='append',choices=TRANSPORTS); e.add_argument('--ttl',type=int,default=900)
 sub.add_parser('drain').add_argument('--limit',type=int,default=8)
 sub.add_parser('status'); sub.add_parser('on'); sub.add_parser('off')
 a=ap.parse_args()
 if a.cmd=='enqueue': print(json.dumps(enqueue(a.producer,a.target,a.action,a.payload,a.command,a.transport,a.ttl),indent=2)); return 0
 if a.cmd=='drain': print(json.dumps(drain(a.limit),indent=2)); return 0
 if a.cmd=='on': set_enabled(True)
 if a.cmd=='off': set_enabled(False)
 print(json.dumps({'enabled':enabled(),'state':str(STATE),'queue':len(list(QUEUE.glob('*.json'))) if QUEUE.exists() else 0},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
