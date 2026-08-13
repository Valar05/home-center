#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, hashlib, json, os, sqlite3, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get('HC_FORGE_CAMPAIGN_STATE','~/.local/state/home-center/forge-campaign')).expanduser()
DB = Path(os.environ.get('HC_PHONE_KERNEL_DB','~/.local/state/home-center/fortress-phone-kernel/kernel.sqlite3')).expanduser()
FORGE_STATE = Path('~/.home-center/cloud-forge/state.env').expanduser()
PROVISIONED = Path('~/.home-center/cloud-forge/gcp-provisioned.env').expanduser()
RECEIPTS = STATE/'receipts.jsonl'; LATEST = STATE/'latest.json'; LOCK = STATE/'run.lock'

MISSION = (
 'Make the Home Center free cloud forge a persistent first-class always-online body. '
 'Preserve Drew as owner, use the existing free-tier provisioning/bootstrap lane, require Judgment Jars and Venice plan review, '
 'establish phone-to-forge SSH control, keep Gitea healthy, persist receipts, retry transient failures, and leave callable status/recover/ssh operations.'
)


def mkdirs():
 STATE.mkdir(parents=True,exist_ok=True); DB.parent.mkdir(parents=True,exist_ok=True)

def write(stage,status,detail,**extra):
 mkdirs(); obj={'schema':'home-center-forge-campaign-v1','stage':stage,'status':status,'detail':detail,'at':int(time.time()),**extra}
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

def provision():
 if PROVISIONED.exists() and parse_env(PROVISIONED).get('FORGE_HOST'): return write('provision','healthy','Existing provisioned forge state retained',state=str(PROVISIONED))
 write('provision','running','Provisioning free-tier forge with canonical script')
 r=run(['sh',str(ROOT/'tools/provision_gcp_free_forge_vm.sh')],1200)
 if r['rc']!=0: raise RuntimeError('provision failed: '+(r['stderr'] or r['stdout'])[-4000:])
 return write('provision','healthy','Free-tier forge provisioned',output=r['stdout'][-4000:])

def bootstrap():
 write('bootstrap','running','Bootstrapping forge and proving SSH with canonical script')
 r=run(['sh',str(ROOT/'tools/bootstrap_free_cloud_forge.sh')],1800)
 if r['rc']!=0: raise RuntimeError('bootstrap failed: '+(r['stderr'] or r['stdout'])[-4000:])
 return write('bootstrap','healthy','Forge bootstrap completed',output=r['stdout'][-5000:])

def ssh_probe(command='printf "FORTRESS_SSH_CONTROL_OK\\n"; id; hostname; uptime; systemctl is-active gitea'):
 env={**parse_env(PROVISIONED),**parse_env(FORGE_STATE)}; host=env.get('FORGE_HOST'); user=env.get('FORGE_USER','forge'); port=env.get('FORGE_PORT','22')
 if not host: raise RuntimeError('FORGE_HOST missing from durable forge state')
 cmd=['ssh','-p',str(port),'-o','BatchMode=yes','-o','ConnectTimeout=12','-o','ServerAliveInterval=20','-o','ServerAliveCountMax=3','-o','StrictHostKeyChecking=accept-new',f'{user}@{host}',command]
 r=run(cmd,120)
 if r['rc']!=0: raise RuntimeError('ssh probe failed: '+(r['stderr'] or r['stdout'])[-4000:])
 ok='FORTRESS_SSH_CONTROL_OK' in r['stdout'] if 'FORTRESS_SSH_CONTROL_OK' in command else True
 return write('ssh','healthy' if ok else 'degraded','SSH control proven' if ok else 'SSH command returned without canary',host=host,user=user,port=port,output=r['stdout'][-6000:])

def recover_once():
 jars=snapshot_jars(); write('jars','healthy','Judgment Jars snapshotted into phone-kernel SQLite',**jars)
 if not venice_gate(): raise RuntimeError('Venice did not grant PLAN_ALLOWED')
 provision(); bootstrap(); return ssh_probe()

def campaign():
 mkdirs()
 try:LOCK.mkdir()
 except FileExistsError:return write('already-running','healthy','Forge campaign already active')
 try:
  round_no=0
  while True:
   round_no+=1
   try:
    write('campaign','running','Advancing durable forge campaign',round=round_no)
    recover_once(); return write('ready','healthy','Home Center forge is provisioned, bootstrapped, SSH-controlled, and resumable',operations=['status','resume','recover','ssh'])
   except Exception as exc:
    write('recover','retrying',f'{type(exc).__name__}: {exc}',round=round_no)
    if round_no>=8:return write('recover','blocked','Bounded automatic recovery exhausted; durable state retained',error=str(exc))
    time.sleep(min(60,2**min(round_no,5)))
 finally:
  try:LOCK.rmdir()
  except OSError:pass

def status():
 mkdirs(); latest=json.loads(LATEST.read_text()) if LATEST.exists() else {'schema':'home-center-forge-campaign-v1','stage':'never-run','status':'idle'}
 env={**parse_env(PROVISIONED),**parse_env(FORGE_STATE)}; latest['forge']={'host':env.get('FORGE_HOST'),'user':env.get('FORGE_USER','forge'),'port':env.get('FORGE_PORT','22')}; print(json.dumps(latest,indent=2,sort_keys=True)); return 0

def main():
 ap=argparse.ArgumentParser(prog='home-center-forge'); sub=ap.add_subparsers(dest='cmd',required=True)
 for n in ('run','resume','recover','status'):sub.add_parser(n)
 s=sub.add_parser('ssh'); s.add_argument('command',nargs='?',default='printf "FORTRESS_SSH_CONTROL_OK\\n"; id; hostname; uptime; systemctl is-active gitea')
 a=ap.parse_args()
 if a.cmd=='status':return status()
 if a.cmd=='ssh':ssh_probe(a.command);return 0
 campaign();return 0

if __name__=='__main__':raise SystemExit(main())
