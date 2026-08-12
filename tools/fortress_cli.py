#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, shlex, sqlite3, subprocess, sys, time, uuid
from pathlib import Path

HOME=Path.home()
REPO=Path(os.environ.get('FORTRESS_HOME_CENTER','/storage/emulated/0/Documents/GodotProjects/home-center'))
KERNEL=REPO/'tools/fortress_phone_kernel.py'
PROMPT=REPO/'tools/fortress_prompt.py'
STATE=HOME/'.local/state/home-center/fortress-phone-kernel'
DB=STATE/'kernel.sqlite3'
SESSIONS=STATE/'sessions.jsonl'

BANNER='Fortress CLI — phone sovereign / deterministic first / offline capable'
HELP='''Commands:\n  /status              kernel status\n  /queue               recent jobs\n  /resume <job-id>     show receipt/result\n  /tick                advance queue now\n  /tools               deterministic prompt catalog\n  /raw <argv...>       enqueue explicit local argv (no shell)\n  /quit                exit\n\nEverything else is compiled through Fortress deterministic prompt grammar first.\nIf it cannot compile, the CLI reports nearby legal forms; it does not guess with a model.\n'''

def run(argv, timeout=30):
    return subprocess.run(argv,cwd=REPO,text=True,capture_output=True,timeout=timeout,check=False)

def kernel(*args):
    p=run([sys.executable,str(KERNEL),*args],60)
    return p

def ensure_db():
    STATE.mkdir(parents=True,exist_ok=True)
    kernel('status')

def rows(limit=12):
    ensure_db(); con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    try: return [dict(r) for r in con.execute('SELECT id,state,lane,kind,updated,error FROM jobs ORDER BY updated DESC LIMIT ?',(limit,))]
    finally: con.close()

def receipt(job_id):
    ensure_db(); con=sqlite3.connect(DB); con.row_factory=sqlite3.Row
    try:
        r=con.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone(); return dict(r) if r else None
    finally: con.close()

def log_session(session,event,detail=None):
    STATE.mkdir(parents=True,exist_ok=True)
    with SESSIONS.open('a',encoding='utf-8') as f:
        f.write(json.dumps({'ts':time.time(),'session':session,'event':event,'detail':detail or {}},separators=(',',':'))+'\n')

def print_receipt(r):
    if not r: print('not found'); return
    print(f"[{r['state']}] {r['id']}  {r['lane']}/{r['kind']}")
    if r.get('result'): print(r['result'].rstrip())
    if r.get('error'): print(r['error'].rstrip(),file=sys.stderr)

def submit_prompt(text, wait=True):
    # First prove the phrase is legal by asking the deterministic compiler in dry discovery mode.
    p=run([sys.executable,str(PROMPT),text],30)
    # fortress_prompt currently executes legal intents. That is acceptable for direct interactive use;
    # its output remains the receipt. If unknown, it fails closed with suggestions.
    sys.stdout.write(p.stdout); sys.stderr.write(p.stderr)
    return p.returncode

def enqueue_raw(argv):
    payload=json.dumps({'argv':argv},separators=(',',':'))
    p=kernel('enqueue','local','shell-argv',payload)
    if p.returncode: sys.stderr.write(p.stderr); return None
    out=json.loads(p.stdout); jid=out['id']; print('queued',jid); return jid

def queue_view():
    for r in rows():
        age=max(0,int(time.time()-r['updated']))
        err=('  ! '+r['error'][:70]) if r.get('error') else ''
        print(f"{r['id'][:8]}  {r['state']:<9} {r['lane']}/{r['kind']}  {age}s{err}")

def repl():
    ensure_db(); session=str(uuid.uuid4()); log_session(session,'start')
    print(BANNER); print('Type /help for controls.')
    while True:
        try: text=input('fortress> ').strip()
        except (EOFError,KeyboardInterrupt): print(); break
        if not text: continue
        log_session(session,'input',{'text':text})
        if text in {'/quit','/exit'}: break
        if text=='/help': print(HELP); continue
        if text=='/status': print(kernel('status').stdout.rstrip()); continue
        if text=='/queue': queue_view(); continue
        if text=='/tick': print(kernel('tick').stdout.rstrip()); continue
        if text=='/tools':
            p=run([sys.executable,str(PROMPT),'--list']); print(p.stdout.rstrip()); continue
        if text.startswith('/resume '): print_receipt(receipt(text.split(None,1)[1].strip())); continue
        if text.startswith('/raw '):
            try: argv=shlex.split(text[5:])
            except ValueError as e: print('BLOCKED:',e); continue
            if not argv: print('BLOCKED: explicit argv required'); continue
            jid=enqueue_raw(argv)
            if jid: kernel('tick'); print_receipt(receipt(jid))
            continue
        rc=submit_prompt(text)
        log_session(session,'result',{'exitCode':rc})
    log_session(session,'stop')

def main():
    ap=argparse.ArgumentParser(prog='fortress',description=BANNER)
    ap.add_argument('-c','--command',help='run one deterministic prompt and exit')
    ap.add_argument('--status',action='store_true')
    ap.add_argument('--queue',action='store_true')
    ap.add_argument('--resume')
    a=ap.parse_args()
    if a.status: print(kernel('status').stdout.rstrip()); return
    if a.queue: queue_view(); return
    if a.resume: print_receipt(receipt(a.resume)); return
    if a.command is not None: raise SystemExit(submit_prompt(a.command))
    repl()

if __name__=='__main__': main()
