#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import argparse, hashlib, json, os, re, shlex, subprocess, time, uuid
from pathlib import Path

STATE=Path(os.path.expanduser('~/.local/state/home-center/coding-dungeon'))
STATE.mkdir(parents=True,exist_ok=True)
MAX_OUTPUT=12000
SAFE_ENV={'PATH','HOME','PREFIX','TMPDIR','LANG','TERM'}

class DungeonError(RuntimeError): pass

def now(): return time.time()
def emit(run,kind,**data):
    event={'ts':now(),'kind':kind,**data}
    with (run/'ledger.jsonl').open('a') as f: f.write(json.dumps(event,ensure_ascii=False)+'\n')
    print(json.dumps(event,ensure_ascii=False),flush=True)

def load(path):
    p=Path(path); raw=p.read_text();
    if p.suffix=='.json': return json.loads(raw)
    try:
        import yaml
        return yaml.safe_load(raw)
    except ImportError as exc: raise DungeonError('YAML manifest requires python package pyyaml; JSON manifests need no extra dependency') from exc

def check_manifest(m):
    required=['name','owner','principal','workspace','objective','steps','stop']
    for k in required:
        if k not in m: raise DungeonError(f'manifest missing {k}')
    ws=Path(m['workspace']).expanduser().resolve()
    if not ws.is_dir(): raise DungeonError(f'workspace missing: {ws}')
    if not (ws/'.git').exists(): raise DungeonError('v1 dungeon requires a git worktree root')
    for s in m['steps']:
        if s.get('type') not in {'command','verify','local_judge'}: raise DungeonError('unsupported step type')
        if s.get('type') in {'command','verify'} and not s.get('run'): raise DungeonError('command step missing run')
    return ws

def git(ws,*args):
    return subprocess.run(['git','-C',str(ws),*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT).stdout.strip()

def fingerprint(text): return hashlib.sha256(text.encode()).hexdigest()[:16]
def run_cmd(ws,cmd,timeout):
    env={k:v for k,v in os.environ.items() if k in SAFE_ENV or k.startswith('HC_')}
    p=subprocess.run(cmd,cwd=ws,shell=True,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=timeout,env=env)
    return p.returncode,p.stdout[-MAX_OUTPUT:]

def known_scar(m,out):
    for scar in m.get('scars',[]):
        pat=scar.get('match')
        if pat and re.search(pat,out,re.I|re.M): return scar
    return None

def local_judge(prompt):
    exe=os.path.expanduser('~/bin/home-center-phone-ask')
    if not os.path.exists(exe): return {'ok':False,'say':'local judge unavailable'}
    p=subprocess.run([exe,prompt],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=90)
    try:return json.loads(p.stdout)
    except:return {'ok':False,'say':p.stdout[-2000:]}

def execute(manifest_path):
    m=load(manifest_path); ws=check_manifest(m); rid=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6]
    run=STATE/rid; run.mkdir(); (run/'manifest.json').write_text(json.dumps(m,indent=2))
    baseline=git(ws,'status','--porcelain=v1'); head=git(ws,'rev-parse','HEAD')
    emit(run,'start',run_id=rid,name=m['name'],owner=m['owner'],principal=m['principal'],objective=m['objective'],workspace=str(ws),head=head,dirty=bool(baseline))
    max_cycles=int(m['stop'].get('max_cycles',3)); timeout=int(m['stop'].get('command_timeout_seconds',300))
    failures={}
    for cycle in range(max_cycles):
        emit(run,'cycle',number=cycle+1)
        all_green=True
        for idx,step in enumerate(m['steps']):
            typ=step['type']; label=step.get('name',f'step-{idx+1}')
            if typ=='local_judge':
                result=local_judge(step.get('prompt',m['objective'])); emit(run,'judge',step=label,result=result)
                continue
            code,out=run_cmd(ws,step['run'],timeout); sig=fingerprint(out); emit(run,'command',step=label,command=step['run'],exit=code,output=out,signature=sig)
            if code==0: continue
            all_green=False; failures[sig]=failures.get(sig,0)+1
            scar=known_scar(m,out)
            if scar and failures[sig] <= int(scar.get('max_uses',1)):
                fix=scar.get('repair')
                if fix:
                    fc,fo=run_cmd(ws,fix,timeout); emit(run,'scar',name=scar.get('name','unnamed'),repair=fix,exit=fc,output=fo)
                    if fc==0: break
            emit(run,'blocked',reason='step_failed',step=label,signature=sig,repeated=failures[sig]);
            if failures[sig]>=int(m['stop'].get('same_failure_limit',2)):
                emit(run,'stop',reason='same_failure_limit'); return 2
            break
        status=git(ws,'status','--porcelain=v1'); diff=git(ws,'diff','--stat')
        emit(run,'checkpoint',cycle=cycle+1,dirty=bool(status),diff_stat=diff)
        if all_green:
            emit(run,'complete',result='green',cycles=cycle+1); return 0
    emit(run,'stop',reason='max_cycles'); return 3

def main():
    p=argparse.ArgumentParser(description='Home Center Mobile Coding Dungeon')
    sub=p.add_subparsers(dest='cmd',required=True)
    r=sub.add_parser('run'); r.add_argument('manifest')
    l=sub.add_parser('list'); l.add_argument('--limit',type=int,default=10)
    a=p.parse_args()
    if a.cmd=='run': raise SystemExit(execute(a.manifest))
    runs=sorted(STATE.glob('*'),reverse=True)[:a.limit]
    for x in runs:
        print(x.name)

if __name__=='__main__': main()
