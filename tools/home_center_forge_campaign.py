#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, hashlib, json, os, shlex, sqlite3, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path(os.environ.get('HC_FORGE_CAMPAIGN_STATE','~/.local/state/home-center/forge-campaign')).expanduser()
DB = Path(os.environ.get('HC_PHONE_KERNEL_DB','~/.local/state/home-center/fortress-phone-kernel/kernel.sqlite3')).expanduser()
FORGE_STATE = Path(os.environ.get('HC_PRIVATE_FORGE_STATE','~/.home-center/cloud-forge/state.env')).expanduser()
FORGE_RECEIPT = Path(os.environ.get('HC_PRIVATE_FORGE_RECEIPT','~/.home-center/cloud-forge/receipt.json')).expanduser()
RECEIPTS = STATE/'receipts.jsonl'
LATEST = STATE/'latest.json'
LOCK = STATE/'run.lock'

MISSION = (
    'Make Home Center own a persistent private Git forge on the Always Free GCP VM. '
    'Gitea and its CI runner are required capabilities, reachable only through the private Tailscale lane. '
    'Portable tests default to free cloud compute when fidelity is preserved; Android truth runs on the phone; '
    'Windows truth runs on THECAULDRON. Never substitute cloud proof for platform-specific truth. '
    'Preserve Drew as owner, Judgment Jars, Venice plan review, append-only receipts, and one phone bootstrap.'
)

def mkdirs():
    STATE.mkdir(parents=True,exist_ok=True)
    DB.parent.mkdir(parents=True,exist_ok=True)

def write(stage,status,detail,**extra):
    mkdirs()
    obj={'schema':'home-center-forge-campaign-v3','stage':stage,'status':status,'detail':detail,'at':int(time.time()),**extra}
    with RECEIPTS.open('a',encoding='utf-8') as f:
        f.write(json.dumps(obj,sort_keys=True)+'\n')
    LATEST.write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps(obj,sort_keys=True),flush=True)
    return obj

def run(cmd,timeout=900,cwd=None):
    p=subprocess.run(cmd,cwd=cwd or ROOT,text=True,capture_output=True,timeout=timeout)
    return {'rc':p.returncode,'stdout':p.stdout[-20000:],'stderr':p.stderr[-12000:]}

def parse_env(path):
    out={}
    if not path.exists():
        return out
    for line in path.read_text(encoding='utf-8',errors='replace').splitlines():
        if '=' not in line or line.lstrip().startswith('#'):
            continue
        k,v=line.split('=',1)
        v=v.strip()
        try:
            parts=shlex.split(v)
            out[k.strip()]=parts[0] if parts else ''
        except ValueError:
            out[k.strip()]=v.strip("'\"")
    return out

def snapshot_jars():
    mkdirs()
    con=sqlite3.connect(DB)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('CREATE TABLE IF NOT EXISTS judgment_jars(path TEXT PRIMARY KEY,title TEXT NOT NULL,body TEXT NOT NULL,sha256 TEXT NOT NULL,source_commit TEXT NOT NULL,imported_at INTEGER NOT NULL)')
    commit=run(['git','rev-parse','HEAD'],30)['stdout'].strip()
    count=0
    for p in sorted((ROOT/'.continue/rules').glob('*.md')):
        body=p.read_text(encoding='utf-8')
        title=next((x.lstrip('# ').strip() for x in body.splitlines() if x.startswith('#')),p.name)
        sha=hashlib.sha256(body.encode()).hexdigest()
        rel=str(p.relative_to(ROOT))
        con.execute(
            'INSERT INTO judgment_jars(path,title,body,sha256,source_commit,imported_at) VALUES(?,?,?,?,?,?) '
            'ON CONFLICT(path) DO UPDATE SET title=excluded.title,body=excluded.body,sha256=excluded.sha256,source_commit=excluded.source_commit,imported_at=excluded.imported_at',
            (rel,title,body,sha,commit,int(time.time()))
        )
        count+=1
    con.commit()
    con.close()
    return {'count':count,'db':str(DB),'sourceCommit':commit}

def venice_gate():
    sys.path.insert(0,str(ROOT/'tools'))
    import adam_planned_venice as av
    packet=av.preflight(MISSION,ROOT,stop_after_steps=10)
    review=packet.get('review') or {}
    allowed=review.get('directive')=='PLAN_ALLOWED' and review.get('planPermissionGranted') is True
    write(
        'venice-plan','allowed' if allowed else 'blocked','Venice plan gate completed',
        directive=review.get('directive'),receipt=review.get('receipt'),
        selectedJars=(packet.get('packet') or {}).get('selectedJars') or []
    )
    return allowed

def forge_env():
    return parse_env(FORGE_STATE)

def forge_probe():
    env=forge_env()
    host=env.get('FORGE_TAILSCALE_IP','')
    if not host:
        raise RuntimeError('private forge Tailscale IP is not recorded; run the one bootstrap')
    user=os.environ.get('HC_FORGE_USER','forge')
    cmd=[
        'ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','StrictHostKeyChecking=accept-new',
        f'{user}@{host}',
        'set -eu; systemctl is-active --quiet gitea; systemctl is-active --quiet gitea-runner; '
        f'curl -fsS --max-time 10 http://{host}:3000/ >/dev/null; '
        'printf "PRIVATE_FORGE_OK\\n"; '
        'printf "GITEA="; /usr/local/bin/gitea --version | head -n1; '
        'printf "RUNNER="; /usr/local/bin/gitea-runner --version | head -n1'
    ]
    r=run(cmd,60)
    if r['rc'] != 0:
        raise RuntimeError('private forge probe failed: '+(r['stderr'] or r['stdout'])[-4000:])
    receipt={}
    if FORGE_RECEIPT.exists():
        try:
            receipt=json.loads(FORGE_RECEIPT.read_text())
        except Exception:
            receipt={}
    return write(
        'forge','healthy','Private Gitea forge and free-compute runner callable over Tailscale',
        host=host,dns=env.get('FORGE_DNS'),web=env.get('FORGE_WEB'),
        cloudRunner=env.get('CLOUD_RUNNER_LABEL','forge-linux-free'),
        phoneRunner=env.get('PHONE_RUNNER_LABEL','phone-android'),
        windowsRunner=env.get('WINDOWS_RUNNER_LABEL','cauldron-windows'),
        output=r['stdout'][-4000:],bootstrapReceipt=receipt
    )

def bootstrap():
    script=ROOT/'tools/bootstrap_free_cloud_forge.sh'
    if not script.exists():
        raise RuntimeError('canonical one-phone bootstrap is missing')
    write('bootstrap','running','Running the one canonical private-forge phone bootstrap',script=str(script))
    r=run(['bash',str(script)],3600)
    if r['rc'] != 0:
        raise RuntimeError('private forge bootstrap failed: '+(r['stderr'] or r['stdout'])[-6000:])
    write('bootstrap','healthy','Canonical private-forge bootstrap completed',output=r['stdout'][-6000:])
    return forge_probe()

def recover_once():
    jars=snapshot_jars()
    write('jars','healthy','Judgment Jars snapshotted into phone-kernel SQLite',**jars)
    if not venice_gate():
        raise RuntimeError('Venice did not grant PLAN_ALLOWED')
    try:
        return forge_probe()
    except Exception as exc:
        write('probe','repairing',f'{type(exc).__name__}: {exc}')
        return bootstrap()

def campaign():
    mkdirs()
    try:
        LOCK.mkdir()
    except FileExistsError:
        return write('already-running','healthy','Forge campaign already active')
    try:
        for round_no in range(1,5):
            try:
                write('campaign','running','Advancing private Gitea/Tailscale forge campaign',round=round_no)
                recover_once()
                return 0
            except Exception as exc:
                write('recover','retrying' if round_no<4 else 'blocked',f'{type(exc).__name__}: {exc}',round=round_no)
                if round_no>=4:
                    return 30
                time.sleep(min(30,2**round_no))
    finally:
        try: LOCK.rmdir()
        except OSError: pass
    return 0

def status():
    mkdirs()
    env=forge_env()
    latest=json.loads(LATEST.read_text()) if LATEST.exists() else {'schema':'home-center-forge-campaign-v3','stage':'never-run','status':'idle'}
    latest['forge']={
        'tailnetIp':env.get('FORGE_TAILSCALE_IP') or None,
        'dns':env.get('FORGE_DNS') or None,
        'web':env.get('FORGE_WEB') or None,
        'cloudRunner':env.get('CLOUD_RUNNER_LABEL') or 'forge-linux-free',
        'phoneRunner':env.get('PHONE_RUNNER_LABEL') or 'phone-android',
        'windowsRunner':env.get('WINDOWS_RUNNER_LABEL') or 'cauldron-windows',
        'publicIngressExpected':False,
        'requiredServices':['gitea','gitea-runner','tailscale']
    }
    print(json.dumps(latest,indent=2,sort_keys=True))
    return 0

def main():
    ap=argparse.ArgumentParser(prog='home-center-forge')
    sub=ap.add_subparsers(dest='cmd',required=True)
    for n in ('run','resume','recover','status','probe'):
        sub.add_parser(n)
    a=ap.parse_args()
    if a.cmd=='status': return status()
    if a.cmd=='probe':
        try:
            forge_probe(); return 0
        except Exception as exc:
            write('forge','blocked',f'{type(exc).__name__}: {exc}'); return 31
    return campaign()

if __name__=='__main__':
    raise SystemExit(main())
