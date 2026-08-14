#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, sqlite3, subprocess, sys, time, uuid
from pathlib import Path

HOME = Path.home()
REPO = Path(os.environ.get('FORTRESS_HOME_CENTER', '/storage/emulated/0/Documents/GodotProjects/home-center'))
CONFIG = REPO / 'config/fortress-phone-kernel.json'
STATE = HOME / '.local/state/home-center/fortress-phone-kernel'
DB = STATE / 'kernel.sqlite3'
LOG = STATE / 'kernel.jsonl'


def cfg():
    raw = json.loads(CONFIG.read_text(encoding='utf-8'))
    raw['stateDir'] = os.path.expandvars(os.path.expanduser(raw.get('stateDir', str(STATE))))
    return raw


def connect():
    STATE.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript('''
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS jobs(
      id TEXT PRIMARY KEY, created REAL NOT NULL, updated REAL NOT NULL,
      state TEXT NOT NULL, lane TEXT NOT NULL, kind TEXT NOT NULL,
      payload TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
      result TEXT, error TEXT, receipt TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_jobs_state_created ON jobs(state, created);
    CREATE TABLE IF NOT EXISTS events(
      seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL,
      job_id TEXT, event TEXT NOT NULL, detail TEXT
    );
    ''')
    return con


def event(con, name, job_id=None, detail=None):
    ts = time.time()
    con.execute('INSERT INTO events(ts,job_id,event,detail) VALUES(?,?,?,?)', (ts, job_id, name, json.dumps(detail or {}, separators=(',', ':'))))
    con.commit()
    with LOG.open('a', encoding='utf-8') as f:
        f.write(json.dumps({'ts': ts, 'job': job_id, 'event': name, 'detail': detail or {}}, separators=(',', ':')) + '\n')


def enqueue(lane, kind, payload):
    c = cfg(); lanes = c.get('lanes', {})
    if lane not in lanes or not lanes[lane].get('enabled', False):
        raise SystemExit(f'BLOCKED: lane disabled or unknown: {lane}')
    now=time.time(); jid=str(uuid.uuid4())
    with connect() as con:
        con.execute('INSERT INTO jobs(id,created,updated,state,lane,kind,payload) VALUES(?,?,?,?,?,?,?)',
                    (jid, now, now, 'queued', lane, kind, json.dumps(payload, separators=(',', ':'))))
        con.commit(); event(con, 'queued', jid, {'lane': lane, 'kind': kind})
    return jid


def network_up():
    try:
        import socket
        s=socket.create_connection(('1.1.1.1',53),0.35); s.close(); return True
    except Exception: return False


def command_for(job):
    payload=json.loads(job['payload'])
    kind=job['kind']; lane=job['lane']
    if lane=='local':
        if kind=='fortress-prompt':
            return [sys.executable, str(REPO/'tools/fortress_prompt.py'), str(payload['prompt'])]
        if kind=='multimedia-plan':
            return [sys.executable, str(REPO/'tools/fortress_multimedia.py'), 'plan']
        if kind=='venice-status':
            return [sys.executable, str(REPO/'tools/fortress_multimedia.py'), 'run', 'venice-status']
        if kind=='shell-argv':
            argv=payload.get('argv') or []
            if not isinstance(argv,list) or not argv: raise ValueError('argv required')
            return [str(x) for x in argv]
    if lane=='chromium-throne' and kind=='throne-task':
        tool=REPO/'tools/chromium_throne_cli.mjs'
        if tool.exists(): return ['node', str(tool), 'enqueue', json.dumps(payload, separators=(',',':'))]
        raise RuntimeError('Chromium Throne CLI not installed in this lineage')
    if lane=='gemini-free' and kind=='gemini-task':
        tool=REPO/'tools/gemini_free_worker.py'
        if tool.exists(): return [sys.executable, str(tool), 'run', json.dumps(payload, separators=(',',':'))]
        raise RuntimeError('Gemini free worker adapter not installed')
    if lane=='fleet' and kind=='fleet-task':
        tool=REPO/'tools/fortress_multimedia.py'
        return [sys.executable, str(tool), 'run', str(payload.get('recipe','multimedia-status'))]
    if lane=='ollama':
        raise RuntimeError('Ollama is not an execution lane; classifier adapter only')
    raise ValueError(f'unsupported job: {lane}/{kind}')


def run_one(con, row):
    c=cfg(); lane_cfg=c['lanes'][row['lane']]
    if lane_cfg.get('requiresNetwork') and not network_up():
        event(con,'deferred-offline',row['id'],{'lane':row['lane']}); return False
    con.execute('UPDATE jobs SET state=?,updated=?,attempts=attempts+1 WHERE id=?',('running',time.time(),row['id'])); con.commit()
    event(con,'started',row['id'],{'lane':row['lane'],'kind':row['kind']})
    try:
        cmd=command_for(row)
        p=subprocess.run(cmd,cwd=REPO,text=True,capture_output=True,timeout=180,check=False)
        receipt={'argv':cmd,'exitCode':p.returncode,'stdout':p.stdout[-20000:],'stderr':p.stderr[-20000:]}
        state='done' if p.returncode==0 else 'failed'
        con.execute('UPDATE jobs SET state=?,updated=?,result=?,error=?,receipt=? WHERE id=?',
                    (state,time.time(),p.stdout,p.stderr,json.dumps(receipt,separators=(',',':')),row['id']))
        con.commit(); event(con,state,row['id'],{'exitCode':p.returncode}); return True
    except Exception as e:
        con.execute('UPDATE jobs SET state=?,updated=?,error=? WHERE id=?',('failed',time.time(),repr(e),row['id'])); con.commit()
        event(con,'failed',row['id'],{'error':repr(e)}); return True


def tick(limit=None):
    c=cfg(); limit=limit or int(c.get('maxConcurrent',2))
    with connect() as con:
        rows=con.execute("SELECT * FROM jobs WHERE state='queued' ORDER BY created LIMIT ?",(limit,)).fetchall()
        count=0
        for row in rows:
            if run_one(con,row): count+=1
        return {'processed':count,'queuedSeen':len(rows)}


def status():
    with connect() as con:
        counts={r['state']:r['n'] for r in con.execute('SELECT state,COUNT(*) n FROM jobs GROUP BY state')}
        latest=[dict(r) for r in con.execute('SELECT id,state,lane,kind,updated,error FROM jobs ORDER BY updated DESC LIMIT 8')]
    return {'ok':True,'db':str(DB),'offlineFirst':cfg().get('offlineFirst',True),'networkUp':network_up(),'counts':counts,'latest':latest,'ollama':cfg().get('ollama',{})}


def daemon():
    c=cfg(); poll=max(5,int(c.get('pollSeconds',15)))
    STATE.mkdir(parents=True,exist_ok=True)
    event(connect(),'daemon-started',detail={'pollSeconds':poll})
    while True:
        try: tick()
        except Exception as e:
            with connect() as con: event(con,'daemon-error',detail={'error':repr(e)})
        time.sleep(poll)


def main():
    p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='cmd',required=True)
    sub.add_parser('status'); sub.add_parser('tick'); sub.add_parser('daemon')
    e=sub.add_parser('enqueue'); e.add_argument('lane'); e.add_argument('kind'); e.add_argument('payload',nargs='?',default='{}')
    a=p.parse_args()
    if a.cmd=='status': out=status()
    elif a.cmd=='tick': out=tick()
    elif a.cmd=='daemon': return daemon()
    else:
        try: payload=json.loads(a.payload)
        except Exception: payload={'prompt':a.payload}
        out={'ok':True,'id':enqueue(a.lane,a.kind,payload)}
    print(json.dumps(out,indent=2,ensure_ascii=False))

if __name__=='__main__': main()
