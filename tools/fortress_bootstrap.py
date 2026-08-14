#!/usr/bin/env python3
"""Fortress Online: one local-first bootstrap for Termux and desktop."""
from __future__ import annotations
import argparse, concurrent.futures, contextlib, datetime as dt, getpass, hashlib, json, os, platform, shutil, signal, socket, subprocess, sys, tempfile, time, urllib.error, urllib.request, uuid
from pathlib import Path

VERSION='1.0.0'
REPO_URL=os.environ.get('FORTRESS_REPO_URL','https://github.com/Valar05/home-center.git')
BRANCH=os.environ.get('FORTRESS_REPO_BRANCH','main')
LLAMA='http://127.0.0.1:8790'
OLLAMA='http://127.0.0.1:11434'

class FError(RuntimeError): pass

def utc(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()
def plat():
    forced=os.environ.get('FORTRESS_TEST_PLATFORM')
    if forced: return forced
    exe=sys.executable.replace('\\','/').lower()
    if os.environ.get('TERMUX_VERSION') or 'com.termux' in exe: return 'termux'
    if os.name=='nt': return 'windows'
    if os.environ.get('WSL_DISTRO_NAME') or 'microsoft' in platform.release().lower(): return 'wsl'
    return 'macos' if sys.platform=='darwin' else 'linux'

def dirs(p, test_root=None):
    h=Path.home()
    if test_root:
        root=Path(test_root).resolve(); data=root/'data'; state=root/'state'; conf=root/'config'; bindir=root/'bin'
    elif p=='windows':
        data=Path(os.environ.get('LOCALAPPDATA',h/'AppData/Local'))/'FortressOnline'; state=data/'state'; conf=Path(os.environ.get('APPDATA',h/'AppData/Roaming'))/'FortressOnline'; bindir=data/'bin'
    else:
        data=Path(os.environ.get('XDG_DATA_HOME',h/'.local/share'))/'fortress-online'; state=Path(os.environ.get('XDG_STATE_HOME',h/'.local/state'))/'fortress-online'; conf=Path(os.environ.get('XDG_CONFIG_HOME',h/'.config'))/'fortress-online'; bindir=Path(os.environ.get('PREFIX',h/'.local'))/'bin' if p=='termux' else h/'.local/bin'
    return {k:v for k,v in {
        'data':data,'state':state,'conf':conf,'bin':bindir,'testroot':Path(test_root).resolve() if test_root else None,'controller':data/'fortress_bootstrap.py','repo':data/'runtime/home-center',
        'cfg':conf/'fortress.json','queue':state/'queue','running':state/'running','done':state/'done','failed':state/'failed',
        'logs':state/'logs','receipts':state/'receipts.jsonl','latest':state/'latest.json','status':state/'status.json',
        'pid':state/'fortress.pid','lock':state/'daemon.lock','daemonlog':state/'logs/daemon.log','vladpid':state/'vlad.pid'
    }.items()}

def mkdir(path, mode=0o700):
    path.mkdir(parents=True,exist_ok=True)
    with contextlib.suppress(OSError,NotImplementedError): path.chmod(mode)
def awrite(path, text, mode=0o600):
    mkdir(path.parent); tmp=path.with_name(path.name+f'.tmp.{os.getpid()}.{uuid.uuid4().hex}')
    tmp.write_text(text,encoding='utf-8',newline='\n')
    with contextlib.suppress(OSError,NotImplementedError): tmp.chmod(mode)
    os.replace(tmp,path)
def jread(path, default=None):
    try: return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,json.JSONDecodeError): return default
def dump(v): return json.dumps(v,indent=2,sort_keys=True,ensure_ascii=False)+'\n'
def run(argv,cwd=None,timeout=None,env=None):
    e=os.environ.copy(); e.update({str(k):str(v) for k,v in (env or {}).items()})
    return subprocess.run([str(x) for x in argv],cwd=str(cwd) if cwd else None,env=e,text=True,capture_output=True,timeout=timeout,check=False)
def alive(pid):
    if not pid or pid<=0: return False
    try:
        if os.name=='nt': return run(['tasklist','/FI',f'PID eq {pid}'],timeout=5).stdout.find(str(pid))>=0
        os.kill(pid,0); return True
    except (OSError,subprocess.SubprocessError): return False
def pidof(path):
    try: return int(path.read_text().strip())
    except (OSError,ValueError): return 0

def receipt(D,p,kind,ok,**extra):
    mkdir(D['state']); event={'schema':'fortress-online-receipt-v1','id':uuid.uuid4().hex,'at':utc(),'kind':kind,'ok':bool(ok),'platform':p,'node':node(D,p),**extra}
    fd=os.open(str(D['receipts']),os.O_CREAT|os.O_WRONLY|os.O_APPEND,0o600)
    try: os.write(fd,(json.dumps(event,sort_keys=True,ensure_ascii=False)+'\n').encode())
    finally: os.close(fd)
    awrite(D['latest'],dump(event)); return event
def node(D,p):
    m=jread(D['conf']/'node.json',{}) or {}
    if m.get('id'): return m['id']
    seed=f'{socket.gethostname()}|{getpass.getuser()}|{p}|{uuid.uuid4().hex}'
    ident=f'{p}-{socket.gethostname().lower().replace(" ","-")[:24]}-{hashlib.sha256(seed.encode()).hexdigest()[:10]}'
    awrite(D['conf']/'node.json',dump({'schema':'fortress-node-v1','id':ident,'platform':p,'createdAt':utc()})); return ident

def config(D,p):
    c=jread(D['cfg'])
    if c: return c
    c={'schema':'fortress-online-config-v1','version':VERSION,'platform':p,'repo':{'url':REPO_URL,'branch':BRANCH,'path':str(D['repo']),'policy':'dedicated-fast-forward-only'},
       'daemon':{'workers':1 if p=='termux' else max(1,min(4,(os.cpu_count() or 2)//2)),'pollSeconds':.75,'heartbeatSeconds':10,'maxRetries':2,'retryBaseSeconds':2},
       'model':{'provider':'auto','llama':LLAMA,'ollama':OLLAMA,'ollamaModel':os.environ.get('FORTRESS_OLLAMA_MODEL','qwen2.5-coder:1.5b'),'cloudAllowed':False,'modelOutputMayExecute':False},
       'security':{'networkCommandListener':False,'queue':'owner-local-filesystem','runAsRoot':False},
       'batteryGovernor':{'enabled':False,'status':'deferred-by-owner','note':'Later: scale work from battery level and charging slope; neither outpace charging nor underperform.'},
       'integrations':{'vladSwarm':p=='termux'}}
    awrite(D['cfg'],dump(c)); return c

def source_repo(start):
    x=Path(start).resolve(); x=x.parent if x.is_file() else x
    for q in (x,*x.parents):
        if (q/'.git').exists() and (q/'AGENTS.md').is_file(): return q
    return None

def install_wrapper(D,p):
    mkdir(D['bin'])
    if p=='windows':
        target=D['bin']/'fortress.cmd'; text=f'@echo off\r\n"{sys.executable}" "{D["controller"]}" %*\r\n'
    else:
        target=D['bin']/'fortress'; text=f'#!/bin/sh\nexec {json.dumps(sys.executable)} {json.dumps(str(D["controller"]))} "$@"\n'
    awrite(target,text,0o700); return target

def sync_repo(D,seed=None,offline=False):
    target=D['repo']; git=shutil.which('git')
    if not git: return {'state':'git-missing','ok':False}
    if target.exists() and (target/'.git').exists():
        dirty=bool(run([git,'-C',target,'status','--porcelain'],timeout=30).stdout.strip())
        if dirty: return {'state':'preserved-dirty','ok':False,'path':str(target)}
        if offline: return {'state':'offline-existing','ok':True,'path':str(target)}
        f=run([git,'-C',target,'fetch','origin',BRANCH],timeout=180)
        if f.returncode: return {'state':'fetch-failed','ok':False,'stderr':f.stderr[-2000:]}
        m=run([git,'-C',target,'merge','--ff-only',f'origin/{BRANCH}'],timeout=120)
        return {'state':'fast-forwarded' if m.returncode==0 else 'non-fast-forward-preserved','ok':m.returncode==0,'stderr':m.stderr[-2000:]}
    if offline and not seed: return {'state':'offline-no-seed','ok':False}
    mkdir(target.parent)
    src=str(Path(seed).resolve()) if seed else REPO_URL
    r=run([git,'clone','--branch',BRANCH,'--single-branch',src,target],timeout=600)
    return {'state':'cloned' if r.returncode==0 else 'clone-failed','ok':r.returncode==0,'path':str(target),'stderr':r.stderr[-2000:]}

def ccmd(D,*args):
    out=[sys.executable,str(D['controller'])]
    if D.get('testroot'): out += ['--test-root',str(D['testroot'])]
    return out+list(args)

def persistence(D,p,test=False):
    cmd=ccmd(D,'daemon','--boot')
    rendered={'platform':p,'installed':False}
    if p=='termux':
        path=Path.home()/'.termux/boot/fortress-online.sh' if not test else D['conf']/'termux-boot.sh'
        awrite(path,'#!/data/data/com.termux/files/usr/bin/sh\n'+' '.join(json.dumps(x) for x in cmd)+' >>'+json.dumps(str(D['daemonlog']))+' 2>&1 &\n',0o700); rendered.update(path=str(path),installed=True)
    elif p in ('linux','wsl'):
        path=(Path.home()/'.config/systemd/user/fortress-online.service') if not test else D['conf']/'fortress-online.service'
        quoted=' '.join('\"'+x.replace('\\','\\\\').replace('\"','\\\"')+'\"' for x in cmd)
        unit='[Unit]\nDescription=Fortress Online local control plane\n[Service]\nType=simple\nExecStart='+quoted+'\nRestart=on-failure\nRestartSec=5\n[Install]\nWantedBy=default.target\n'
        awrite(path,unit); rendered.update(path=str(path),installed=True)
        if not test and shutil.which('systemctl'):
            run(['systemctl','--user','daemon-reload'],timeout=20); run(['systemctl','--user','enable','--now','fortress-online.service'],timeout=30)
    elif p=='macos':
        path=(Path.home()/'Library/LaunchAgents/com.homecenter.fortress-online.plist') if not test else D['conf']/'fortress.plist'
        args=''.join(f'<string>{x.replace("&","&amp;").replace("<","&lt;")}</string>' for x in cmd)
        awrite(path,'<?xml version="1.0"?><!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd"><plist version="1.0"><dict><key>Label</key><string>com.homecenter.fortress-online</string><key>ProgramArguments</key><array>'+args+'</array><key>RunAtLoad</key><true/><key>KeepAlive</key><true/></dict></plist>'); rendered.update(path=str(path),installed=True)
        if not test and shutil.which('launchctl'): run(['launchctl','bootstrap',f'gui/{os.getuid()}',path],timeout=30)
    else:
        rendered['command']='schtasks /Create /SC ONLOGON /TN FortressOnline /TR "'+subprocess.list2cmdline(cmd)+'" /F'
        if not test:
            r=run(['schtasks','/Create','/SC','ONLOGON','/TN','FortressOnline','/TR',subprocess.list2cmdline(cmd),'/F'],timeout=30); rendered['installed']=r.returncode==0; rendered['stderr']=r.stderr[-1000:]
        else: rendered['installed']=True
    return rendered

def detached(argv,log):
    mkdir(log.parent); out=open(log,'ab',buffering=0)
    kw={'stdin':subprocess.DEVNULL,'stdout':out,'stderr':subprocess.STDOUT,'close_fds':True}
    if os.name=='nt': kw['creationflags']=subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.DETACHED_PROCESS
    else: kw['start_new_session']=True
    return subprocess.Popen(argv,**kw)
def tmux_alive():
    return bool(shutil.which('tmux') and run(['tmux','has-session','-t','fortress-online'],timeout=5).returncode==0)

def start(D,p):
    old=pidof(D['pid'])
    if alive(old): return {'ok':True,'state':'already-running','pid':old,'tmux':tmux_alive()}
    if p!='windows' and shutil.which('tmux'):
        run(['tmux','kill-session','-t','fortress-online'],timeout=5)
        launched=run(['tmux','new-session','-d','-s','fortress-online',*ccmd(D,'daemon')],timeout=10)
        if launched.returncode!=0: return {'ok':False,'state':'tmux-start-failed','stderr':launched.stderr[-1000:]}
        proc=None
    else:
        proc=detached(ccmd(D,'daemon'),D['daemonlog'])
    for _ in range(30):
        if alive(pidof(D['pid'])): return {'ok':True,'state':'started','pid':pidof(D['pid'])}
        time.sleep(.1)
    return {'ok':False,'state':'start-unproven','spawnPid':proc.pid if proc else None,'tmux':tmux_alive()}
def stop(D,p):
    if p!='windows' and tmux_alive(): run(['tmux','kill-session','-t','fortress-online'],timeout=10)
    pid=pidof(D['pid'])
    if not alive(pid):
        with contextlib.suppress(OSError): D['pid'].unlink()
        return {'ok':True,'state':'already-stopped'}
    if os.name=='nt': run(['taskkill','/PID',str(pid),'/T','/F'],timeout=20)
    else:
        with contextlib.suppress(OSError): os.kill(pid,signal.SIGTERM)
        for _ in range(50):
            if not alive(pid): break
            time.sleep(.1)
    with contextlib.suppress(OSError): D['pid'].unlink()
    return {'ok':not alive(pid),'state':'stopped' if not alive(pid) else 'stop-failed','pid':pid}

def http(url,payload=None,timeout=3):
    data=None if payload is None else json.dumps(payload).encode(); req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=timeout) as r: return json.loads(r.read().decode())
def local_prompt(c,text,model=None,timeout=300):
    m=c['model']; provider=m.get('provider','auto'); errors=[]
    if provider in ('auto','llama'):
        try:
            http(m['llama']+'/health',timeout=2)
            x=http(m['llama']+'/v1/chat/completions',{'model':'local','messages':[{'role':'user','content':text}],'temperature':.2},timeout)
            return {'provider':'llama.cpp','model':'local','response':x['choices'][0]['message']['content']}
        except Exception as e: errors.append('llama:'+type(e).__name__)
    if provider in ('auto','ollama'):
        try:
            http(m['ollama']+'/api/tags',timeout=2)
            name=model or m['ollamaModel']; x=http(m['ollama']+'/api/chat',{'model':name,'messages':[{'role':'user','content':text}],'stream':False},timeout)
            return {'provider':'ollama','model':name,'response':x['message']['content']}
        except Exception as e: errors.append('ollama:'+type(e).__name__)
    raise FError('no local model is callable; deterministic run/queue remains available ('+', '.join(errors)+')')

def enqueue(D,p,job):
    mkdir(D['queue']); ident=f'{int(time.time()*1000):013d}-{uuid.uuid4().hex[:12]}'
    job={'schema':'fortress-job-v1','id':ident,'createdAt':utc(),'attempt':0,'notBefore':0,**job}
    awrite(D['queue']/(ident+'.json'),dump(job)); receipt(D,p,'job.enqueued',True,jobId=ident,jobType=job['type']); return job

def claim(D):
    for f in sorted(D['queue'].glob('*.json')):
        job=jread(f,{}) or {}
        if float(job.get('notBefore',0))>time.time(): continue
        target=D['running']/f.name; mkdir(D['running'])
        try: os.replace(f,target); return target,job
        except OSError: continue
    return None

def execute(D,p,c,path,job):
    started=time.time(); ok=False; out=''; err=''; rc=1
    try:
        if job['type']=='command':
            argv=job.get('argv') or []
            if not isinstance(argv,list) or not argv: raise FError('command job requires a non-empty argv list')
            cp=run(argv,cwd=Path(job['cwd']) if job.get('cwd') else None,timeout=float(job.get('timeout',900)))
            rc=cp.returncode; out=cp.stdout[-262144:]; err=cp.stderr[-262144:]; ok=rc==0
        elif job['type']=='prompt':
            x=local_prompt(c,str(job.get('prompt','')),job.get('model'),float(job.get('timeout',300))); out=x['response']; rc=0; ok=True
        else: raise FError('unsupported job type')
    except Exception as e: err=f'{type(e).__name__}: {e}'; rc=124 if isinstance(e,subprocess.TimeoutExpired) else 2
    result={'schema':'fortress-result-v1','jobId':job['id'],'type':job['type'],'ok':ok,'rc':rc,'stdout':out,'stderr':err,'startedAt':dt.datetime.fromtimestamp(started,dt.timezone.utc).isoformat(),'finishedAt':utc(),'modelOutputExecuted':False}
    awrite(D['state']/f'results/{job["id"]}.json',dump(result))
    attempts=int(job.get('attempt',0)); maxr=int(job.get('retries',c['daemon']['maxRetries']))
    if not ok and attempts<maxr:
        job['attempt']=attempts+1; job['notBefore']=time.time()+min(60,c['daemon']['retryBaseSeconds']*(2**attempts)); awrite(D['queue']/path.name,dump(job)); dest='retry'
    else:
        dest=D['done' if ok else 'failed']/path.name; mkdir(dest.parent); awrite(dest,dump(job)); dest=str(dest)
    with contextlib.suppress(OSError): path.unlink()
    receipt(D,p,'job.finished',ok,jobId=job['id'],jobType=job['type'],rc=rc,destination=dest)
    return result

def vlad(D,p,c):
    if p!='termux' or not c.get('integrations',{}).get('vladSwarm'): return {'state':'not-applicable'}
    pid=pidof(D['vladpid'])
    if alive(pid): return {'state':'running','pid':pid}
    script=D['repo']/'tools/vlad_swarm_daemon.py'
    if not shutil.which('rish') or not script.is_file(): return {'state':'unavailable'}
    proc=detached([sys.executable,str(script),'--repo',str(D['repo'])],D['logs']/'vlad.log'); awrite(D['vladpid'],str(proc.pid)+'\n'); return {'state':'started','pid':proc.pid}

def daemon(D,p,once=False):
    mkdir(D['state']);
    try: D['lock'].mkdir()
    except FileExistsError:
        if alive(pidof(D['pid'])): return 0
        with contextlib.suppress(OSError): D['lock'].rmdir()
        D['lock'].mkdir()
    awrite(D['pid'],str(os.getpid())+'\n'); c=config(D,p); last=0
    def end(*_): raise KeyboardInterrupt
    signal.signal(signal.SIGTERM,end)
    pool=concurrent.futures.ThreadPoolExecutor(max_workers=int(c['daemon']['workers']),thread_name_prefix='fortress')
    active=set()
    try:
        while True:
            active={f for f in active if not f.done()}
            while len(active)<int(c['daemon']['workers']):
                item=claim(D)
                if not item: break
                active.add(pool.submit(execute,D,p,c,*item))
            if time.time()-last>=10:
                awrite(D['status'],dump({'schema':'fortress-status-v1','at':utc(),'pid':os.getpid(),'platform':p,'workers':int(c['daemon']['workers']),'active':len(active),'queue':len(list(D['queue'].glob('*.json'))),'batteryGovernor':c['batteryGovernor'],'vlad':vlad(D,p,c)})); last=time.time()
            if once:
                for f in active: f.result()
                break
            time.sleep(float(c['daemon']['pollSeconds']))
    except KeyboardInterrupt: pass
    finally:
        pool.shutdown(wait=True,cancel_futures=False)
        with contextlib.suppress(OSError): D['pid'].unlink()
        with contextlib.suppress(OSError): D['lock'].rmdir()
    return 0

def wait(D,ident,timeout=1200):
    until=time.time()+timeout
    while time.time()<until:
        r=jread(D['state']/f'results/{ident}.json')
        if r and any((D[x]/f'{ident}.json').exists() for x in ('done','failed')): return r
        time.sleep(.25)
    raise FError(f'timed out waiting for {ident}')

def model_state(c):
    for name,base,path in [('llama.cpp',c['model']['llama'],'/health'),('ollama',c['model']['ollama'],'/api/tags')]:
        try: http(base+path,timeout=.5); return {'callable':True,'provider':name}
        except Exception: pass
    return {'callable':False,'provider':None}
def snapshot(D,p):
    c=config(D,p); return {'schema':'fortress-status-v1','version':VERSION,'platform':p,'installed':D['controller'].is_file(),'daemon':{'pid':pidof(D['pid']),'callable':alive(pidof(D['pid'])),'tmux':tmux_alive(),'workers':c['daemon']['workers']},'model':model_state(c),'deterministicExecution':True,'cloudTokensRequired':False,'browserOrchestrationUsed':False,'networkCommandListener':False,'batteryGovernor':c['batteryGovernor'],'paths':{k:str(D[k]) for k in ('controller','repo','cfg','queue','receipts')},'queues':{k:len(list(D[k].glob('*.json'))) for k in ('queue','running','done','failed')}}

def install(D,p,args):
    if os.name!='nt' and hasattr(os,'geteuid') and os.geteuid()==0 and not args.test_root: raise FError('refusing root; Fortress owns the current user account, not the OS security boundary')
    for k in ('data','state','conf','queue','running','done','failed','logs'): mkdir(D[k])
    src=Path(__file__).resolve(); awrite(D['controller'],src.read_text(encoding='utf-8'),0o700); config(D,p); wrapper=install_wrapper(D,p)
    seed=args.source_repo or (str(source_repo(src)) if source_repo(src) else None)
    repo=sync_repo(D,seed,args.offline); persist=persistence(D,p,bool(args.test_root)); service={'state':'not-started'} if args.no_start else start(D,p)
    degraded=[]
    if not repo.get('ok'): degraded.append('runtime-repo:'+str(repo.get('state')))
    if not persist.get('installed'): degraded.append('persistence:'+str(persist.get('state','unproven')))
    if service.get('ok') is False: degraded.append('daemon:'+str(service.get('state')))
    ev=receipt(D,p,'install',True,wrapper=str(wrapper),repo=repo,persistence=persist,service=service,batteryGovernor='deferred',degraded=degraded)
    return {'ok':True,'coreInstalled':True,'degraded':degraded,'receipt':ev,'status':snapshot(D,p),'pathNote':str(D['bin'])+' must be on PATH'}

def selftest(script):
    checks=[]
    with tempfile.TemporaryDirectory(prefix='fortress-contract-') as td:
        base=[sys.executable,str(script),'--test-root',td]
        e=os.environ.copy(); e['FORTRESS_TEST_PLATFORM']='linux'
        a=subprocess.run(base+['install','--offline','--no-start'],env=e,text=True,capture_output=True); checks.append({'name':'isolated-install','ok':a.returncode==0,'stderr':a.stderr[-1000:]})
        D=dirs('linux',td); c=config(D,'linux'); job=enqueue(D,'linux',{'type':'command','argv':[sys.executable,'-c','print("FORTRESS_OK")'],'timeout':10,'retries':0}); daemon(D,'linux',once=True); r=jread(D['state']/f'results/{job["id"]}.json',{}); checks.append({'name':'deterministic-zero-token-job','ok':r['ok'] and 'FORTRESS_OK' in r['stdout']})
        c['model']['llama']='http://127.0.0.1:9'; c['model']['ollama']='http://127.0.0.1:9'
        try: local_prompt(c,'test',timeout=.1); no_model=False
        except FError: no_model=True
        checks.append({'name':'no-model-safe-failure','ok':no_model})
        checks.append({'name':'battery-deferred','ok':c['batteryGovernor']['enabled'] is False and c['batteryGovernor']['status']=='deferred-by-owner'})
        checks.append({'name':'platform-renderers','ok':all(persistence(dirs(x,Path(td)/x),x,True)['installed'] for x in ('termux','linux','wsl','macos','windows'))})
        checks.append({'name':'closed-control-plane','ok':(not c['security']['networkCommandListener'] and not c['model']['modelOutputMayExecute'] and not c['model']['cloudAllowed'])})
    return {'schema':'fortress-contract-v1','version':VERSION,'ok':all(x['ok'] for x in checks),'checks':checks}

def parser():
    ap=argparse.ArgumentParser(prog='fortress'); ap.add_argument('--test-root',help=argparse.SUPPRESS); sub=ap.add_subparsers(dest='cmd',required=True)
    i=sub.add_parser('install',aliases=['init']); i.add_argument('--source-repo'); i.add_argument('--offline',action='store_true'); i.add_argument('--no-start',action='store_true')
    for x in ('start','stop','restart','status','doctor','sync','receipts','daemon','self-test'): sub.add_parser(x)
    for x in ('run','queue'):
        q=sub.add_parser(x); q.add_argument('--cwd'); q.add_argument('--timeout',type=float,default=900); q.add_argument('--retries',type=int,default=2); q.add_argument('--wait-timeout',type=float,default=1200); q.add_argument('argv',nargs=argparse.REMAINDER)
    a=sub.add_parser('ask'); a.add_argument('prompt'); a.add_argument('--model'); a.add_argument('--timeout',type=float,default=300); a.add_argument('--wait-timeout',type=float,default=600)
    sub.choices['daemon'].add_argument('--boot',action='store_true',help=argparse.SUPPRESS); sub.choices['daemon'].add_argument('--once',action='store_true')
    sub.choices['receipts'].add_argument('--tail',type=int,default=20)
    sub.choices['sync'].add_argument('--offline',action='store_true')
    return ap

def main(argv=None):
    a=parser().parse_args(argv); p=plat(); D=dirs(p,a.test_root)
    try:
        if a.cmd in ('install','init'): out=install(D,p,a)
        elif a.cmd=='start': out=start(D,p)
        elif a.cmd=='stop': out=stop(D,p)
        elif a.cmd=='restart': out={'stop':stop(D,p),'start':start(D,p)}
        elif a.cmd=='status': out=snapshot(D,p)
        elif a.cmd=='doctor':
            out=snapshot(D,p); out['checks']={'python':sys.version.split()[0],'wrapper':D['bin'].exists(),'git':bool(shutil.which('git')),'repo':D['repo'].exists(),'permissions':'owner-best-effort'}; out['ok']=out['installed'] and out['deterministicExecution']
        elif a.cmd=='sync': out=sync_repo(D,None,a.offline); receipt(D,p,'repo.sync',bool(out.get('ok')),detail=out)
        elif a.cmd in ('run','queue'):
            av=a.argv[1:] if a.argv[:1]==['--'] else a.argv
            if not av: raise FError('missing command after --')
            job=enqueue(D,p,{'type':'command','argv':av,'cwd':a.cwd,'timeout':a.timeout,'retries':a.retries});
            if not alive(pidof(D['pid'])): start(D,p)
            out=job if a.cmd=='queue' else wait(D,job['id'],a.wait_timeout)
        elif a.cmd=='ask':
            job=enqueue(D,p,{'type':'prompt','prompt':a.prompt,'model':a.model,'timeout':a.timeout,'retries':0});
            if not alive(pidof(D['pid'])): start(D,p)
            out=wait(D,job['id'],a.wait_timeout)
        elif a.cmd=='receipts':
            try: lines=D['receipts'].read_text(encoding='utf-8').splitlines()[-a.tail:]; out=[json.loads(x) for x in lines]
            except OSError: out=[]
        elif a.cmd=='daemon': return daemon(D,p,a.once)
        elif a.cmd=='self-test': out=selftest(Path(__file__).resolve())
        else: raise FError('unknown command')
        print(dump(out),end=''); return 0 if not isinstance(out,dict) or out.get('ok',True) is not False else 2
    except (FError,subprocess.SubprocessError,urllib.error.URLError,OSError) as e:
        ev=receipt(D,p,'error',False,command=a.cmd,error=f'{type(e).__name__}: {e}'); print(dump({'ok':False,'error':str(e),'receipt':ev}),end=''); return 2

if __name__=='__main__': raise SystemExit(main())
