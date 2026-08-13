#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, hashlib, json, os, shutil, sqlite3, subprocess, sys, time, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get('HC_FORGE_CAMPAIGN_STATE','~/.local/state/home-center/forge-campaign')).expanduser()
DB = Path(os.environ.get('HC_PHONE_KERNEL_DB','~/.local/state/home-center/fortress-phone-kernel/kernel.sqlite3')).expanduser()
GEMINI_STATE = Path(os.environ.get('HC_GEMINI_STATE','~/.local/state/home-center/gemini-worker')).expanduser()
FORGE_STATE = Path('~/.home-center/cloud-forge/state.env').expanduser()
PROVISIONED = Path('~/.home-center/cloud-forge/gcp-provisioned.env').expanduser()
RECEIPTS = STATE/'receipts.jsonl'; LATEST = STATE/'latest.json'; LOCK = STATE/'run.lock'

MISSION = (
 'Make Home Center own a persistent always-online free-compute lane backed by the Gemini API on serverless Google Cloud. '
 'Preserve Drew as owner, require Judgment Jars and Venice plan review, keep durable receipts and retries, and expose status/run/recover operations. '
 'A public VM, IPv6, Gitea, and SSH are optional machine-body capabilities and must never gate Gemini compute readiness.'
)

def mkdirs():
 STATE.mkdir(parents=True,exist_ok=True); DB.parent.mkdir(parents=True,exist_ok=True); GEMINI_STATE.mkdir(parents=True,exist_ok=True)

def write(stage,status,detail,**extra):
 mkdirs(); obj={'schema':'home-center-forge-campaign-v2','stage':stage,'status':status,'detail':detail,'at':int(time.time()),**extra}
 with RECEIPTS.open('a',encoding='utf-8') as f:f.write(json.dumps(obj,sort_keys=True)+'\n')
 LATEST.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8'); print(json.dumps(obj,sort_keys=True),flush=True); return obj

def run(cmd,timeout=900,cwd=None):
 p=subprocess.run(cmd,cwd=cwd or ROOT,text=True,capture_output=True,timeout=timeout)
 return {'rc':p.returncode,'stdout':p.stdout[-20000:],'stderr':p.stderr[-12000:]}

def parse_env(path):
 out={}
 if not path.exists():return out
 for line in path.read_text(encoding='utf-8',errors='replace').splitlines():
  if '=' not in line or line.lstrip().startswith('#'):continue
  k,v=line.split('=',1); out[k.strip()]=v.strip().strip("'\"")
 return out

def snapshot_jars():
 mkdirs(); con=sqlite3.connect(DB); con.execute('PRAGMA journal_mode=WAL')
 con.execute('CREATE TABLE IF NOT EXISTS judgment_jars(path TEXT PRIMARY KEY,title TEXT NOT NULL,body TEXT NOT NULL,sha256 TEXT NOT NULL,source_commit TEXT NOT NULL,imported_at INTEGER NOT NULL)')
 commit=run(['git','rev-parse','HEAD'],30)['stdout'].strip(); count=0
 for p in sorted((ROOT/'.continue/rules').glob('*.md')):
  body=p.read_text(encoding='utf-8'); title=next((x.lstrip('# ').strip() for x in body.splitlines() if x.startswith('#')),p.name); sha=hashlib.sha256(body.encode()).hexdigest(); rel=str(p.relative_to(ROOT))
  con.execute('INSERT INTO judgment_jars(path,title,body,sha256,source_commit,imported_at) VALUES(?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET title=excluded.title,body=excluded.body,sha256=excluded.sha256,source_commit=excluded.source_commit,imported_at=excluded.imported_at',(rel,title,body,sha,commit,int(time.time()))); count+=1
 con.commit(); con.close(); return {'count':count,'db':str(DB),'sourceCommit':commit}

def venice_gate():
 sys.path.insert(0,str(ROOT/'tools')); import adam_planned_venice as av
 packet=av.preflight(MISSION,ROOT,stop_after_steps=10); review=packet.get('review') or {}; allowed=review.get('directive')=='PLAN_ALLOWED' and review.get('planPermissionGranted') is True
 write('venice-plan','allowed' if allowed else 'blocked','Venice plan gate completed',directive=review.get('directive'),receipt=review.get('receipt'),selectedJars=(packet.get('packet') or {}).get('selectedJars') or [])
 return allowed

def gemini_url():
 explicit=os.environ.get('HC_GEMINI_WORKER_URL','').strip()
 if explicit:return explicit.rstrip('/')
 path=GEMINI_STATE/'url'
 return path.read_text(encoding='utf-8').strip().rstrip('/') if path.exists() else ''

def http_json(url,payload=None,timeout=30):
 data=None; headers={}
 if payload is not None:data=json.dumps(payload).encode(); headers['content-type']='application/json'
 req=urllib.request.Request(url,data=data,headers=headers,method='POST' if payload is not None else 'GET')
 with urllib.request.urlopen(req,timeout=timeout) as response:return json.loads(response.read().decode())

def gemini_probe(require_canary=True):
 url=gemini_url()
 if not url:raise RuntimeError('Gemini worker URL is not recorded yet')
 health=http_json(url+'/health',timeout=20)
 if not health.get('ok') or not health.get('configured'):raise RuntimeError('Gemini worker health is not configured/healthy')
 canary=None
 if require_canary:
  canary=http_json(url+'/v1/run',{'prompt':'Return exactly: GEMINI_WORKER_OK','temperature':0},timeout=90)
  if not canary.get('ok') or 'GEMINI_WORKER_OK' not in str(canary.get('text','')):raise RuntimeError('Gemini worker canary failed')
 return write('gemini','healthy','Always-online Gemini worker callable',url=url,health=health,canary=canary,sshRequired=False,ipv6Required=False)

def deploy_gemini():
 # Deployment is a machine-body task; once deployed, ordinary Gemini work has no SSH or IPv6 dependency.
 script=ROOT/'tools/deploy_gemini_free_worker.sh'
 if not script.exists():raise RuntimeError('Gemini worker deploy script missing')
 if shutil.which('gcloud'):
  write('gemini-deploy','running','Deploying Gemini worker through local gcloud body')
  r=run(['bash',str(script)],1800)
  if r['rc']!=0:raise RuntimeError('Gemini worker deploy failed: '+(r['stderr'] or r['stdout'])[-5000:])
  return gemini_probe()
 # If a worker URL already exists, a phone without gcloud does not need a machine body.
 if gemini_url():return gemini_probe()
 raise RuntimeError('Gemini worker is implemented but needs one gcloud-capable Home Center machine body for first deployment')

def optional_ssh_probe():
 env={**parse_env(PROVISIONED),**parse_env(FORGE_STATE)}; host=env.get('FORGE_HOST'); user=env.get('FORGE_USER','forge'); port=env.get('FORGE_PORT','22')
 if not host:return write('ssh','optional','No VM forge configured; Gemini compute remains healthy',sshRequired=False)
 r=run(['ssh','-p',str(port),'-o','BatchMode=yes','-o','ConnectTimeout=8','-o','StrictHostKeyChecking=accept-new',f'{user}@{host}','printf "FORTRESS_SSH_CONTROL_OK\\n"; hostname; uptime'],30)
 return write('ssh','healthy' if r['rc']==0 else 'degraded','Optional SSH body probe complete',host=host,output=(r['stdout'] or r['stderr'])[-3000:],sshRequired=False)

def recover_once():
 jars=snapshot_jars(); write('jars','healthy','Judgment Jars snapshotted into phone-kernel SQLite',**jars)
 if not venice_gate():raise RuntimeError('Venice did not grant PLAN_ALLOWED')
 deploy_gemini(); optional_ssh_probe()
 return write('ready','healthy','Home Center Gemini compute is callable; machine-body transports are optional',operations=['status','resume','recover','run','ssh-status'])

def campaign():
 mkdirs()
 try:LOCK.mkdir()
 except FileExistsError:return write('already-running','healthy','Forge campaign already active')
 try:
  for round_no in range(1,9):
   try:
    write('campaign','running','Advancing Gemini-first Home Center campaign',round=round_no)
    return recover_once()
   except Exception as exc:
    write('recover','retrying' if round_no<8 else 'blocked',f'{type(exc).__name__}: {exc}',round=round_no)
    if round_no>=8:return 30
    time.sleep(min(60,2**min(round_no,5)))
 finally:
  try:LOCK.rmdir()
  except OSError:pass
 return 0

def run_prompt(prompt):
 if not prompt.strip():raise RuntimeError('prompt required')
 url=gemini_url()
 if not url:raise RuntimeError('Gemini worker URL missing; run recover after first deployment')
 receipt=http_json(url+'/v1/run',{'prompt':prompt},timeout=100)
 write('gemini-run','healthy' if receipt.get('ok') else 'failed','Gemini worker invocation complete',receipt=receipt)
 print(json.dumps(receipt,indent=2,sort_keys=True)); return 0 if receipt.get('ok') else 31

def status():
 mkdirs(); latest=json.loads(LATEST.read_text()) if LATEST.exists() else {'schema':'home-center-forge-campaign-v2','stage':'never-run','status':'idle'}
 latest['gemini']={'url':gemini_url() or None,'sshRequired':False,'ipv6Required':False}; print(json.dumps(latest,indent=2,sort_keys=True)); return 0

def main():
 ap=argparse.ArgumentParser(prog='home-center-forge'); sub=ap.add_subparsers(dest='cmd',required=True)
 for n in ('run','resume','recover','status','ssh-status'):sub.add_parser(n)
 p=sub.add_parser('ask'); p.add_argument('prompt',nargs='+')
 a=ap.parse_args()
 if a.cmd=='status':return status()
 if a.cmd=='ask':return run_prompt(' '.join(a.prompt))
 if a.cmd=='ssh-status':optional_ssh_probe();return 0
 return campaign()

if __name__=='__main__':raise SystemExit(main())
