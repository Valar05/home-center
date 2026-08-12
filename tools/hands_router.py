#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, hmac, json, os, secrets, shlex, subprocess, sys, time
from pathlib import Path

TOOL_DIR=Path(__file__).resolve().parent
STATE=Path(os.environ.get('HC_HANDS_ROUTER_STATE','~/.local/state/home-center/hands-router')).expanduser()
KEY=Path(os.environ.get('HC_HANDS_ROUTER_KEY','~/.config/home-center/hands-router.key')).expanduser()
TOGGLE=STATE/'enabled'; QUEUE=STATE/'queue'; DONE=STATE/'done'; RECEIPTS=STATE/'receipts.jsonl'
PRODUCERS={'drew','vlad','venice','adam','fortress'}
TRANSPORTS=('ssh','wlan','computer_hands')
MAX_STEPS=int(os.environ.get('HC_HANDS_MAX_STEPS','64'))
MAX_JOB_BYTES=int(os.environ.get('HC_HANDS_MAX_JOB_BYTES','65536'))
MAX_RUNTIME=int(os.environ.get('HC_HANDS_MAX_RUNTIME','300'))
OPS={
 'system.status','screen.capture','window.list','process.list','window.focus','input.type','input.key','input.mouse',
 'process.start','process.stop','shell.exec','clipboard.get','clipboard.set',
 'phone.observe','phone.tap','phone.swipe','phone.text','phone.keyevent','phone.home','phone.back','phone.recents',
 'phone.launch','phone.open_uri','phone.force_stop'
}
PHONE_ACTIONS={
 'phone.tap':'tap','phone.swipe':'swipe','phone.text':'text','phone.keyevent':'keyevent','phone.home':'home',
 'phone.back':'back','phone.recents':'recents','phone.launch':'launch','phone.open_uri':'open_uri','phone.force_stop':'force_stop'
}
HARMFUL_TOKENS=(
 ('rm','-rf','/'),('mkfs',),('wipefs',),('dd','if=','of=/dev/'),('shutdown',),('poweroff',),('reboot',),
 ('format','c:'),('diskpart',),('bcdedit','/delete'),('cipher','/w:')
)

def _mkdirs():
 for p in (STATE,QUEUE,DONE,KEY.parent): p.mkdir(parents=True,exist_ok=True)

def _key():
 _mkdirs()
 if not KEY.exists(): KEY.write_bytes(secrets.token_bytes(32)); os.chmod(KEY,0o600)
 return KEY.read_bytes()

def enabled(): return not TOGGLE.exists() or TOGGLE.read_text().strip().lower() not in {'0','off','false','disabled'}
def set_enabled(v): _mkdirs(); TOGGLE.write_text('1\n' if v else '0\n',encoding='utf-8'); return v

def canonical(job): return json.dumps({k:v for k,v in job.items() if k!='sig'},sort_keys=True,separators=(',',':')).encode()
def sign(job): return hmac.new(_key(),canonical(job),hashlib.sha256).hexdigest()
def verify(job): return hmac.compare_digest(str(job.get('sig','')),sign(job))

def validate(job):
 if job.get('schema')!='hands-router-job-v2': return 'bad_schema'
 if job.get('producer') not in PRODUCERS: return 'unknown_producer'
 if not isinstance(job.get('target'),str) or not job['target'].strip(): return 'target_required'
 steps=job.get('steps')
 if not isinstance(steps,list) or not steps: return 'steps_required'
 if len(steps)>MAX_STEPS: return 'too_many_steps'
 if len(canonical(job))>MAX_JOB_BYTES: return 'job_too_large'
 runtime=int(job.get('maxRuntimeSeconds',0))
 if runtime<1 or runtime>MAX_RUNTIME: return 'invalid_runtime_bound'
 for i,s in enumerate(steps):
  if not isinstance(s,dict) or s.get('op') not in OPS: return f'invalid_step:{i}'
  if set(s)-{'op','args','expect'}: return f'unrecognized_step_fields:{i}'
  if 'args' in s and not isinstance(s['args'],dict): return f'invalid_args:{i}'
  if 'expect' in s and not isinstance(s['expect'],dict): return f'invalid_expect:{i}'
 return None

def objectively_harmful(job):
 for step in job.get('steps') or []:
  args=step.get('args') or {}
  if args.get('harm') is True:return 'explicit_harm_flag'
  text=json.dumps(args,sort_keys=True).lower()
  for signature in HARMFUL_TOKENS:
   if all(token in text for token in signature):return 'destructive_signature'
 return None

def enqueue(producer,target,steps,transports=None,ttl=900,max_runtime=120,job_id=None):
 now=int(time.time()); jid=job_id or f'{now}-{secrets.token_hex(6)}'
 job={'schema':'hands-router-job-v2','id':jid,'producer':producer,'target':target,'steps':steps,
      'transports':transports or list(TRANSPORTS),'createdAt':now,'expiresAt':now+int(ttl),'maxRuntimeSeconds':int(max_runtime)}
 reason=validate(job)
 if reason:raise ValueError(reason)
 job['sig']=sign(job); _mkdirs(); (QUEUE/f'{jid}.json').write_text(json.dumps(job,indent=2,sort_keys=True)+'\n',encoding='utf-8')
 return job

def _receipt(job,status,**extra):
 rec={'schema':'hands-router-receipt-v2','id':job.get('id'),'producer':job.get('producer'),'target':job.get('target'),
      'status':status,'at':int(time.time()),**extra}
 _mkdirs()
 with RECEIPTS.open('a',encoding='utf-8') as f:f.write(json.dumps(rec,sort_keys=True)+'\n')
 return rec

def _expect(actual,expected):
 if not expected:return None
 if not isinstance(actual,dict):return 'result_not_object'
 for key,value in expected.items():
  if actual.get(key)!=value:return f'expect_mismatch:{key}'
 return None

def _local_phone(job):
 if job.get('target')!='primary-phone':return None
 from android_phone_home_center_relay import execute_action
 results=[]
 for i,step in enumerate(job['steps']):
  op=step['op']; args=dict(step.get('args') or {})
  if op=='phone.observe':action={'action':'observe','ui':bool(args.get('ui',False)),'screen':bool(args.get('screen',False))}
  elif op in PHONE_ACTIONS:action={'action':PHONE_ACTIONS[op],**args}
  else:return {'rc':64,'stdout':'','stderr':f'unsupported_local_phone_op:{op}','steps':results}
  result=execute_action(action); mismatch=_expect(result,step.get('expect') or {})
  results.append({'index':i,'op':op,'result':result,'expectFailure':mismatch})
  if mismatch:return {'rc':65,'stdout':'','stderr':mismatch,'steps':results}
 return {'rc':0,'stdout':json.dumps(results,ensure_ascii=False),'stderr':'','steps':results}

def _job_blob(job):return base64.urlsafe_b64encode(json.dumps(job,separators=(',',':')).encode()).decode()

def _parse_last_json(text):
 for line in reversed(str(text or '').splitlines()):
  try:
   value=json.loads(line.strip())
   if isinstance(value,dict):return value
  except Exception:pass
 return None

def _run_template(env_name,job):
 template=os.environ.get(env_name,'').strip()
 if not template:return None
 blob=_job_blob(job)
 cmd=template.replace('{job_b64}',shlex.quote(blob)).replace('{target}',shlex.quote(str(job['target'])))
 p=subprocess.run(cmd,shell=True,text=True,capture_output=True,timeout=int(job['maxRuntimeSeconds'])+20)
 structured=_parse_last_json(p.stdout)
 return {'rc':p.returncode,'stdout':p.stdout[-12000:],'stderr':p.stderr[-8000:],'structured':structured,'safeToFallback':bool(structured and structured.get('safeToFallback') is True)}

def _run_builtin(script_name,job):
 script=TOOL_DIR/script_name
 if not script.exists():return None
 p=subprocess.run([sys.executable,str(script),'--job-b64',_job_blob(job)],text=True,capture_output=True,timeout=int(job['maxRuntimeSeconds'])+25)
 structured=_parse_last_json(p.stdout)
 return {'rc':p.returncode,'stdout':p.stdout[-12000:],'stderr':p.stderr[-8000:],'structured':structured,'safeToFallback':bool(structured and structured.get('safeToFallback') is True)}

def _transport(transport,job):
 envs={'ssh':'HC_HANDS_SSH_DISPATCH','wlan':'HC_HANDS_WLAN_DISPATCH','computer_hands':'HC_HANDS_COMPUTER_DISPATCH'}
 if os.environ.get(envs[transport],'').strip():return _run_template(envs[transport],job)
 if transport=='ssh':return _run_builtin('hands_transport_ssh.py',job)
 if transport=='computer_hands':return _run_builtin('hands_transport_computer.py',job)
 return None

def dispatch(job):
 if not enabled():return _receipt(job,'paused')
 if not verify(job):return _receipt(job,'rejected',reason='bad_signature')
 reason=validate(job)
 if reason:return _receipt(job,'rejected',reason=reason)
 if int(job.get('expiresAt',0))<int(time.time()):return _receipt(job,'expired')
 harm=objectively_harmful(job)
 if harm:return _receipt(job,'blocked',reason=harm)
 attempts=[]
 try:local=_local_phone(job)
 except Exception as e:local={'rc':125,'stdout':'','stderr':f'{type(e).__name__}: {e}'}
 if local is not None:
  attempts.append({'transport':'local_phone',**local})
  return _receipt(job,'completed' if local['rc']==0 else 'failed',transport='local_phone',attempts=attempts)
 for transport in job.get('transports') or TRANSPORTS:
  if transport not in TRANSPORTS:continue
  try:result=_transport(transport,job)
  except subprocess.TimeoutExpired as exc:result={'rc':124,'stdout':'','stderr':f'{transport} adapter timeout: {exc}','safeToFallback':False}
  except Exception as exc:result={'rc':125,'stdout':'','stderr':f'{type(exc).__name__}: {exc}','safeToFallback':False}
  if result is None:
   attempts.append({'transport':transport,'status':'unconfigured','safeToFallback':True});continue
  attempts.append({'transport':transport,**result})
  if result['rc']==0:return _receipt(job,'completed',transport=transport,attempts=attempts)
  if not result.get('safeToFallback',False):return _receipt(job,'failed',transport=transport,attempts=attempts,reason='transport_execution_started_or_ambiguous')
 return _receipt(job,'failed',attempts=attempts,reason='all_transports_unavailable_before_execution')

def drain(limit=8):
 _mkdirs(); out=[]
 for path in sorted(QUEUE.glob('*.json'))[:limit]:
  try:job=json.loads(path.read_text(encoding='utf-8')); rec=dispatch(job)
  except Exception as e:job={'id':path.stem};rec=_receipt(job,'failed',reason=f'parse_or_dispatch:{type(e).__name__}:{e}')
  out.append(rec)
  if rec['status']!='paused':path.rename(DONE/path.name)
 return out

def status():
 _mkdirs(); return {'enabled':enabled(),'state':str(STATE),'queue':len(list(QUEUE.glob('*.json'))),'done':len(list(DONE.glob('*.json'))),
                    'contract':'finite-script-v2','primaryProducer':'drew','maxSteps':MAX_STEPS,'maxRuntimeSeconds':MAX_RUNTIME,'modelInExecutor':False,
                    'transportOrder':list(TRANSPORTS),'builtIn':{'ssh':(TOOL_DIR/'hands_transport_ssh.py').exists(),'wlan':False,'computer_hands':(TOOL_DIR/'hands_transport_computer.py').exists()},
                    'wlanConfigured':bool(os.environ.get('HC_HANDS_WLAN_DISPATCH','').strip())}

def main(default_producer=None):
 ap=argparse.ArgumentParser(prog='hands-router'); sub=ap.add_subparsers(dest='cmd',required=True)
 e=sub.add_parser('enqueue'); e.add_argument('--producer',choices=sorted(PRODUCERS),default=default_producer); e.add_argument('--target',required=True); e.add_argument('--job-file',required=True); e.add_argument('--transport',action='append',choices=TRANSPORTS); e.add_argument('--ttl',type=int,default=900); e.add_argument('--max-runtime',type=int,default=120)
 sub.add_parser('drain').add_argument('--limit',type=int,default=8); sub.add_parser('status'); sub.add_parser('on'); sub.add_parser('off')
 a=ap.parse_args()
 if a.cmd=='enqueue':
  if not a.producer:ap.error('--producer required')
  print(json.dumps(enqueue(a.producer,a.target,json.loads(Path(a.job_file).read_text()),a.transport,a.ttl,a.max_runtime),indent=2));return 0
 if a.cmd=='drain':print(json.dumps(drain(a.limit),indent=2));return 0
 if a.cmd=='on':set_enabled(True)
 elif a.cmd=='off':set_enabled(False)
 print(json.dumps(status(),indent=2));return 0
if __name__=='__main__':raise SystemExit(main(default_producer='drew'))
