#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOME = Path.home()
REPO = Path(os.environ.get("FORTRESS_HOME_CENTER", "/storage/emulated/0/Documents/GodotProjects/home-center"))
STATE = HOME / ".local/state/home-center/fortress-campaign"
DB = STATE / "campaign.sqlite3"
LOG = STATE / "campaign.jsonl"
PEER_FILE = HOME / ".config/home-center/chromium-throne-peer.json"
JAR_CANDIDATES = [
    HOME / ".local/share/vlad/judgment-jars",
    HOME / ".local/state/vlad/judgment-jars",
    REPO / "judgment-jars",
]
SSH_ALIASES = tuple(x for x in os.environ.get("FORTRESS_CAULDRON_SSH", "THECAULDRON,thecauldron,windows-hands-01").split(",") if x)


def run(argv, cwd=REPO, timeout=60):
    return subprocess.run([str(x) for x in argv], cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)


def now(): return time.time()


def connect():
    STATE.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL, kind TEXT NOT NULL, detail TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS missions(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      created REAL NOT NULL,
      updated REAL NOT NULL,
      state TEXT NOT NULL,
      prompt TEXT NOT NULL,
      attempt INTEGER NOT NULL DEFAULT 0,
      next_eligible REAL NOT NULL DEFAULT 0,
      worker_receipt TEXT,
      venice_receipt TEXT,
      error TEXT
    );
    CREATE TABLE IF NOT EXISTS workers(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      mission_id INTEGER NOT NULL,
      role TEXT NOT NULL,
      remote_task_id TEXT,
      state TEXT NOT NULL,
      created REAL NOT NULL,
      updated REAL NOT NULL,
      prompt TEXT NOT NULL,
      receipt TEXT,
      UNIQUE(mission_id, role)
    );
    """)
    return con


def emit(con, kind, detail):
    STATE.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(detail, separators=(",", ":"), ensure_ascii=False)
    con.execute("INSERT INTO events(ts,kind,detail) VALUES(?,?,?)", (now(), kind, payload)); con.commit()
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now(), "kind": kind, "detail": detail}, separators=(",", ":"), ensure_ascii=False) + "\n")


def set_meta(con, key, value):
    con.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value, separators=(",", ":"), ensure_ascii=False))); con.commit()


def get_meta(con, key, default=None):
    r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(r[0]) if r else default


def git(*args, timeout=60): return run(["git", *args], timeout=timeout)


def dirty_tree_recovery(con):
    """STEP ONE. Preserve dirty + untracked work reversibly before the campaign changes branches."""
    top = git("rev-parse", "--show-toplevel")
    if top.returncode: raise RuntimeError("Home Center path is not a Git worktree: " + top.stderr.strip())
    status = git("status", "--porcelain=v2", "--branch")
    if status.returncode: raise RuntimeError("git status failed: " + status.stderr.strip())
    before = status.stdout
    set_meta(con, "dirty_tree_before", before)
    changed = [ln for ln in before.splitlines() if ln and not ln.startswith("# branch.")]
    emit(con, "dirty-tree-observed", {"changedLines": len(changed), "status": before[-20000:]})
    if not changed:
        emit(con, "dirty-tree-clean", {})
        return {"changed": False, "stash": None}

    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    message = f"fortress-rescue-{stamp}"
    p = git("stash", "push", "-u", "-m", message, timeout=180)
    if p.returncode: raise RuntimeError("BLOCKED: dirty tree could not be preserved: " + p.stderr.strip())
    oid_p = git("rev-parse", "stash@{0}")
    if oid_p.returncode: raise RuntimeError("BLOCKED: rescue stash OID cannot be proven")
    oid = oid_p.stdout.strip()
    stat = git("stash", "show", "--stat", "--include-untracked", "stash@{0}")
    after = git("status", "--porcelain=v2", "--branch")
    remaining = [ln for ln in after.stdout.splitlines() if ln and not ln.startswith("# branch.")]
    if after.returncode or remaining: raise RuntimeError("BLOCKED: rescue stash did not leave a clean tree")
    receipt = {"message": message, "oid": oid, "stat": stat.stdout[-20000:], "restore": f"git stash apply --index {oid}"}
    set_meta(con, "dirty_tree_rescue", receipt); emit(con, "dirty-tree-rescued", receipt)
    return {"changed": True, "stash": receipt}


def find_jar_cache():
    env = os.environ.get("VLAD_JUDGMENT_JARS")
    for p in ([Path(env)] if env else []) + JAR_CANDIDATES:
        try:
            if p.exists() and p.is_dir(): return p
        except OSError: pass
    return None


def venice_review(con, mission, phase, worker_receipts=None):
    jars = find_jar_cache()
    if jars is None:
        return {"verdict": "CONTINUE_REQUIRED", "source": "no-local-jar-cache", "phase": phase, "reason": "Vlad jar cache campaign not landed yet"}
    adapters = [jars/"bin"/"venice-review", HOME/"bin"/"venice-review", REPO/"tools"/"venice_judgment.py"]
    adapter = next((p for p in adapters if p.exists()), None)
    if adapter is None:
        return {"verdict": "CONTINUE_REQUIRED", "source": str(jars), "phase": phase, "reason": "cache-present-adapter-pending"}
    packet = {"phase": phase, "missionId": mission["id"], "prompt": mission["prompt"], "state": mission["state"], "attempt": mission["attempt"], "workers": worker_receipts or []}
    argv = [str(adapter), json.dumps(packet, separators=(",", ":"), ensure_ascii=False)]
    if adapter.suffix == ".py": argv.insert(0, sys.executable)
    p = run(argv, timeout=120)
    receipt = {"source": str(adapter), "exitCode": p.returncode, "stdout": p.stdout[-20000:], "stderr": p.stderr[-20000:], "phase": phase}
    if p.returncode != 0:
        receipt["verdict"] = "CONTINUE_REQUIRED"; return receipt
    try:
        parsed = json.loads(p.stdout); verdict = parsed.get("verdict") or parsed.get("directive")
    except Exception: verdict = None
    receipt["verdict"] = verdict if verdict in {"PLAN_ALLOWED","STOP_ALLOWED","CONTINUE_REQUIRED","HALT_REQUIRED"} else "CONTINUE_REQUIRED"
    return receipt


def http_json(method, url, token=None, payload=None, timeout=8):
    data = None if payload is None else json.dumps(payload).encode()
    headers = {"accept": "application/json"}
    if data is not None: headers["content-type"] = "application/json"
    if token: headers["x-throne-token"] = token
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors="replace")[-4000:]
        return e.code, {"error": body}


def load_peer():
    url = os.environ.get("FORTRESS_THRONE_URL")
    token = os.environ.get("FORTRESS_THRONE_TOKEN")
    repo_root = os.environ.get("FORTRESS_DESKTOP_REPO_ROOT")
    if url:
        return {"url": url.rstrip("/"), "token": token or "", "repoRoot": repo_root or ""}
    try:
        p = json.loads(PEER_FILE.read_text(encoding="utf-8"))
        p["url"] = str(p.get("url", "")).rstrip("/")
        return p
    except Exception: return None


def save_peer(peer):
    PEER_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = PEER_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(peer, indent=2, ensure_ascii=False), encoding="utf-8")
    os.chmod(tmp, 0o600); tmp.replace(PEER_FILE)


def parse_mobile_url(raw):
    for line in raw.splitlines():
        line = line.strip().strip('"')
        if line.startswith("http://") or line.startswith("https://"):
            u = urllib.parse.urlparse(line)
            q = urllib.parse.parse_qs(u.query)
            token = (q.get("token") or [""])[0]
            return {"url": f"{u.scheme}://{u.hostname}:{u.port or 17373}", "token": token}
    return None


def ssh_discover_peer(con):
    """Use existing SSH Axis only as discovery/recovery fast path. No new remote-control architecture."""
    remote_ps = r'''$ErrorActionPreference='SilentlyContinue'; $root=Join-Path $env:LOCALAPPDATA 'HomeCenter\ChromiumThrone'; $u=Join-Path $root 'mobile-url.txt'; if(!(Test-Path $u)){ $task=Get-ScheduledTask -TaskName HomeCenterChromiumThrone -ErrorAction SilentlyContinue; if($task){Start-ScheduledTask -TaskName HomeCenterChromiumThrone; Start-Sleep -Seconds 2} }; if(Test-Path $u){Get-Content $u}; $repo=Get-ChildItem -Path $env:USERPROFILE -Directory -Filter home-center -Recurse -Depth 6 -ErrorAction SilentlyContinue | Where-Object {$_.FullName -notmatch '\\node_modules\\'} | Select-Object -First 1 -ExpandProperty FullName; if($repo){Write-Output ('REPO_ROOT='+$repo)}'''
    for alias in SSH_ALIASES:
        p = run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4", alias, "powershell", "-NoProfile", "-Command", remote_ps], cwd=HOME, timeout=18)
        if p.returncode: continue
        peer = parse_mobile_url(p.stdout)
        if not peer: continue
        for line in p.stdout.splitlines():
            if line.startswith("REPO_ROOT="): peer["repoRoot"] = line.split("=",1)[1].strip()
        peer["sshAlias"] = alias; peer["discoveredAt"] = now()
        code, health = http_json("GET", peer["url"] + "/health", timeout=4)
        if code == 200 and health.get("contract") == "home-center.chromium-throne.v1":
            save_peer(peer); set_meta(con, "throne_peer", peer); emit(con, "throne-peer-discovered", {k:v for k,v in peer.items() if k != "token"})
            return peer
    return None


def ensure_peer(con):
    peer = load_peer()
    if peer and peer.get("url"):
        code, health = http_json("GET", peer["url"] + "/health", timeout=4)
        if code == 200 and health.get("contract") == "home-center.chromium-throne.v1":
            return peer
        emit(con, "throne-peer-unhealthy", {"url": peer.get("url"), "status": code, "health": health})
    return ssh_discover_peer(con)


def task_state(peer):
    code, body = http_json("GET", peer["url"] + "/api/state", token=peer.get("token"), timeout=8)
    if code != 200: raise RuntimeError(f"Throne state HTTP {code}: {body}")
    return body


def remote_task(peer, task_id):
    state = task_state(peer)
    return next((t for t in state.get("tasks", []) if t.get("id") == task_id), None)


def dispatch_worker(con, mission, role, prompt):
    existing = con.execute("SELECT * FROM workers WHERE mission_id=? AND role=?", (mission["id"], role)).fetchone()
    if existing and existing["remote_task_id"]: return dict(existing)
    peer = ensure_peer(con)
    if not peer: raise RuntimeError("Chromium Throne peer not currently callable; daemon will keep recovering")
    repo_root = peer.get("repoRoot") or os.environ.get("FORTRESS_DESKTOP_REPO_ROOT", "")
    if not repo_root: raise RuntimeError("Chromium Throne is callable but desktop Home Center repo root is unresolved")
    full = f"PORTCULLIS LOCKED. Chat mode, Pro reasoning where configurable. Role: {role}. Campaign: phone-swarm-coding.\n\n{prompt}\n\nWork directly in the commissioned repository. Preserve dirty/unique work. Test through native/local deterministic lanes, not GitHub Actions. Produce receipts. Do not stop at a plan."
    code, body = http_json("POST", peer["url"] + "/api/tasks", token=peer.get("token"), payload={"repoRoot": repo_root, "prompt": full}, timeout=12)
    if code != 202 or not body.get("id"): raise RuntimeError(f"Throne task enqueue failed HTTP {code}: {body}")
    ts = now()
    con.execute("INSERT OR REPLACE INTO workers(mission_id,role,remote_task_id,state,created,updated,prompt,receipt) VALUES(?,?,?,?,?,?,?,?)",
                (mission["id"], role, body["id"], body.get("status","queued"), ts, ts, full, json.dumps(body,separators=(",",":"))))
    con.commit(); emit(con, "worker-enqueued", {"mission": mission["id"], "role": role, "remoteTaskId": body["id"], "peer": peer.get("url")})
    return dict(con.execute("SELECT * FROM workers WHERE mission_id=? AND role=?", (mission["id"], role)).fetchone())


def refresh_workers(con, mission):
    peer = ensure_peer(con)
    if not peer: raise RuntimeError("Chromium Throne peer unavailable during worker refresh")
    rows = [dict(r) for r in con.execute("SELECT * FROM workers WHERE mission_id=? ORDER BY id", (mission["id"],))]
    out=[]
    for w in rows:
        remote = remote_task(peer, w["remote_task_id"])
        if remote:
            con.execute("UPDATE workers SET state=?,updated=?,receipt=? WHERE id=?", (remote.get("status","unknown"), now(), json.dumps(remote,separators=(",",":"),ensure_ascii=False), w["id"])); con.commit()
            w["state"] = remote.get("status","unknown"); w["receipt"] = json.dumps(remote,separators=(",",":"),ensure_ascii=False)
        out.append(w)
    return out


def enqueue(prompt):
    with connect() as con:
        ts=now(); cur=con.execute("INSERT INTO missions(created,updated,state,prompt,next_eligible) VALUES(?,?,?,?,?)",(ts,ts,"queued",prompt,ts)); mid=cur.lastrowid; con.commit()
        emit(con,"mission-queued",{"id":mid,"sha256":hashlib.sha256(prompt.encode()).hexdigest()}); return mid


def set_mission(con, mission_id, state, delay=2, error=None, receipt=None, venice=None):
    con.execute("UPDATE missions SET state=?,updated=?,next_eligible=?,attempt=attempt+1,error=?,worker_receipt=COALESCE(?,worker_receipt),venice_receipt=COALESCE(?,venice_receipt) WHERE id=?",
                (state, now(), now()+delay, error, json.dumps(receipt,separators=(",",":"),ensure_ascii=False) if receipt is not None else None, json.dumps(venice,separators=(",",":"),ensure_ascii=False) if venice is not None else None, mission_id)); con.commit()


def one_cycle(con):
    row=con.execute("SELECT * FROM missions WHERE state NOT IN ('accepted','halted') AND next_eligible<=? ORDER BY created LIMIT 1",(now(),)).fetchone()
    if not row: return {"acted":False,"reason":"idle"}
    m=dict(row)
    try:
        if m["state"] == "queued":
            # Drew explicitly commissioned Venice-approved execution for this campaign. A runtime Jar
            # adapter still owns all subsequent review/STOP authority.
            emit(con,"plan-authority",{"mission":m["id"],"source":"operator commission: Venice approves","stopAuthority":False})
            dispatch_worker(con,m,"builder",m["prompt"])
            set_mission(con,m["id"],"building",delay=5); return {"acted":True,"state":"building"}

        if m["state"] == "building":
            ws=refresh_workers(con,m); builder=next((w for w in ws if w["role"]=="builder"),None)
            if not builder: set_mission(con,m["id"],"queued",delay=2,error="builder record missing"); return {"acted":True,"state":"queued"}
            if builder["state"] in {"queued","running"}: con.execute("UPDATE missions SET next_eligible=?,updated=? WHERE id=?",(now()+8,now(),m["id"]));con.commit();return {"acted":False,"reason":"builder-in-flight"}
            if builder["state"] == "human_gate": set_mission(con,m["id"],"retry",delay=30,error="builder reached human_gate; recovery required",receipt=ws); return {"acted":True,"state":"retry"}
            if builder["state"] != "done":
                peer=ensure_peer(con)
                if peer and builder["remote_task_id"]:
                    http_json("POST",peer["url"]+f"/api/tasks/{builder['remote_task_id']}/retry",token=peer.get("token"),timeout=8)
                set_mission(con,m["id"],"building",delay=min(300,10*(2**min(m["attempt"],5))),error=f"builder {builder['state']}",receipt=ws);return {"acted":True,"state":"building"}
            review_prompt=f"Review and repair the implementation for this original commission:\n\n{m['prompt']}\n\nThe builder has finished. Inspect the actual current repository diff and tests. Find regressions, incomplete behavior, accessibility problems, brittle recovery, dirty-tree loss risks, daemon/tmux lifecycle faults, and evidence laundering. Fix every issue you can through the same repository lane."
            dispatch_worker(con,m,"repair-reviewer",review_prompt)
            set_mission(con,m["id"],"reviewing",delay=5,receipt=ws);return {"acted":True,"state":"reviewing"}

        if m["state"] == "reviewing":
            ws=refresh_workers(con,m); reviewer=next((w for w in ws if w["role"]=="repair-reviewer"),None)
            if not reviewer: set_mission(con,m["id"],"building",delay=2,error="reviewer record missing");return {"acted":True,"state":"building"}
            if reviewer["state"] in {"queued","running"}: con.execute("UPDATE missions SET next_eligible=?,updated=? WHERE id=?",(now()+8,now(),m["id"]));con.commit();return {"acted":False,"reason":"reviewer-in-flight"}
            if reviewer["state"] != "done":
                peer=ensure_peer(con)
                if peer and reviewer["remote_task_id"]: http_json("POST",peer["url"]+f"/api/tasks/{reviewer['remote_task_id']}/retry",token=peer.get("token"),timeout=8)
                set_mission(con,m["id"],"reviewing",delay=min(300,10*(2**min(m["attempt"],5))),error=f"reviewer {reviewer['state']}",receipt=ws);return {"acted":True,"state":"reviewing"}
            stop=venice_review(con,m,"stop",ws); emit(con,"venice-stop",{"mission":m["id"],**stop})
            if stop.get("verdict")=="STOP_ALLOWED": set_mission(con,m["id"],"accepted",delay=0,receipt=ws,venice=stop);emit(con,"mission-accepted",{"mission":m["id"]});return {"acted":True,"state":"accepted"}
            if stop.get("verdict")=="HALT_REQUIRED": set_mission(con,m["id"],"halted",delay=0,receipt=ws,venice=stop);return {"acted":True,"state":"halted"}
            # Venice says continue (or no adapter yet): commission another repair pass. The UNIQUE role
            # includes the attempt so it cannot overwrite prior evidence.
            role=f"venice-repair-{m['attempt']+1}"
            prompt=f"Venice did not permit STOP for mission {m['id']}. Re-open the original commission, inspect all prior worker results and current repository state, and continue repairing until the acceptance evidence is stronger. Original commission:\n\n{m['prompt']}"
            dispatch_worker(con,m,role,prompt)
            set_mission(con,m["id"],"venice-repair",delay=5,receipt=ws,venice=stop);return {"acted":True,"state":"venice-repair"}

        if m["state"] == "venice-repair":
            ws=refresh_workers(con,m); repairs=[w for w in ws if w["role"].startswith("venice-repair-")]
            if not repairs: set_mission(con,m["id"],"reviewing",delay=2,error="Venice repair worker missing");return {"acted":True,"state":"reviewing"}
            latest=repairs[-1]
            if latest["state"] in {"queued","running"}: con.execute("UPDATE missions SET next_eligible=?,updated=? WHERE id=?",(now()+8,now(),m["id"]));con.commit();return {"acted":False,"reason":"venice-repair-in-flight"}
            if latest["state"] != "done":
                peer=ensure_peer(con)
                if peer: http_json("POST",peer["url"]+f"/api/tasks/{latest['remote_task_id']}/retry",token=peer.get("token"),timeout=8)
                con.execute("UPDATE missions SET next_eligible=?,updated=?,error=? WHERE id=?",(now()+30,now(),f"{latest['role']} {latest['state']}",m["id"]));con.commit();return {"acted":True,"state":"venice-repair"}
            con.execute("UPDATE missions SET state='reviewing',next_eligible=?,updated=?,error=NULL WHERE id=?",(now()+2,now(),m["id"]));con.commit();return {"acted":True,"state":"reviewing"}

        if m["state"] == "retry":
            peer=ensure_peer(con)
            if peer:
                con.execute("UPDATE missions SET state='building',next_eligible=?,updated=?,error=NULL WHERE id=?",(now()+2,now(),m["id"]));con.commit();return {"acted":True,"state":"building"}
            con.execute("UPDATE missions SET next_eligible=?,updated=? WHERE id=?",(now()+min(300,10*(2**min(m["attempt"],5))),now(),m["id"]));con.commit();return {"acted":False,"reason":"peer-recovery-backoff"}
    except Exception as e:
        delay=min(300,10*(2**min(m["attempt"],5)))
        set_mission(con,m["id"],"retry",delay=delay,error=repr(e)); emit(con,"mission-error",{"mission":m["id"],"error":repr(e),"backoff":delay});return {"acted":True,"state":"retry"}
    return {"acted":False,"reason":m["state"]}


def daemon():
    STATE.mkdir(parents=True, exist_ok=True)
    with connect() as con: set_meta(con,"daemon_pid",os.getpid());emit(con,"daemon-started",{"pid":os.getpid(),"repo":str(REPO)})
    delay=2
    while True:
        try:
            with connect() as con: r=one_cycle(con)
            delay=2 if r.get("acted") else min(30,delay+2)
        except Exception as e:
            with connect() as con: emit(con,"daemon-error",{"error":repr(e),"backoff":delay})
            delay=min(300,max(5,delay*2))
        time.sleep(delay)


def status():
    with connect() as con:
        missions=[dict(r) for r in con.execute("SELECT id,state,attempt,updated,next_eligible,error FROM missions ORDER BY updated DESC LIMIT 10")]
        workers=[dict(r) for r in con.execute("SELECT mission_id,role,remote_task_id,state,updated FROM workers ORDER BY updated DESC LIMIT 20")]
        peer=load_peer()
        peer_public={k:v for k,v in (peer or {}).items() if k!="token"}
        return {"ok":True,"repo":str(REPO),"db":str(DB),"dirtyTreeRescue":get_meta(con,"dirty_tree_rescue"),"jarCache":str(find_jar_cache()) if find_jar_cache() else None,"thronePeer":peer_public or None,"missions":missions,"workers":workers,"daemonPid":get_meta(con,"daemon_pid")}


def diagnose(repair=False):
    with connect() as con:
        peer=ensure_peer(con) if repair else load_peer()
        throne=None
        if peer and peer.get("url"):
            try:
                code,body=http_json("GET",peer["url"]+"/health",timeout=4); throne={"status":code,"body":body,"url":peer["url"]}
            except Exception as e: throne={"error":repr(e),"url":peer["url"]}
        return {"ok":True,"repair":repair,"git":git("status","--porcelain=v2","--branch").stdout,"tmuxExpected":"fortress-swarm","jarCache":str(find_jar_cache()) if find_jar_cache() else None,"throne":throne,"status":status()}


def main():
    ap=argparse.ArgumentParser(prog="fortress-campaign");sp=ap.add_subparsers(dest="cmd",required=True)
    sp.add_parser("recover-dirty-tree");sp.add_parser("daemon");sp.add_parser("status")
    d=sp.add_parser("diagnose");d.add_argument("--repair",action="store_true")
    q=sp.add_parser("prompt");q.add_argument("text")
    a=ap.parse_args()
    if a.cmd=="recover-dirty-tree":
        with connect() as con: print(json.dumps(dirty_tree_recovery(con),indent=2))
    elif a.cmd=="daemon": daemon()
    elif a.cmd=="status": print(json.dumps(status(),indent=2))
    elif a.cmd=="diagnose": print(json.dumps(diagnose(a.repair),indent=2))
    elif a.cmd=="prompt": print(json.dumps({"ok":True,"mission":enqueue(a.text)}))

if __name__=="__main__": main()
