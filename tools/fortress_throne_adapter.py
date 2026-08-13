#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import sqlite3
import subprocess
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

HOME = Path.home()
REPO = Path(os.environ.get("FORTRESS_HOME_CENTER", "/storage/emulated/0/Documents/GodotProjects/home-center"))
STATE = HOME / ".local/state/home-center/fortress-campaign"
DB = STATE / "throne-adapter.sqlite3"
HOST = "127.0.0.1"
PORT = int(os.environ.get("FORTRESS_THRONE_ADAPTER_PORT", "17373"))
EXTENSION_ID = os.environ.get("FORTRESS_THRONE_EXTENSION_ID", "lccnchjcenaomhnjjaomabpajagenkaf")
SSH_ALIASES = tuple(x for x in os.environ.get("FORTRESS_CAULDRON_SSH", "THECAULDRON,thecauldron,windows-hands-01").split(",") if x)


def now(): return time.time()


def db():
    STATE.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS tasks(
      id TEXT PRIMARY KEY, created REAL NOT NULL, updated REAL NOT NULL,
      repo_root TEXT NOT NULL, prompt TEXT NOT NULL, state TEXT NOT NULL,
      job_id TEXT NOT NULL, command_id TEXT, wave INTEGER NOT NULL DEFAULT 0,
      receipt TEXT, error TEXT
    );
    CREATE TABLE IF NOT EXISTS events(seq INTEGER PRIMARY KEY AUTOINCREMENT,ts REAL NOT NULL,kind TEXT NOT NULL,detail TEXT NOT NULL);
    """)
    return con


def event(con, kind, detail):
    con.execute("INSERT INTO events(ts,kind,detail) VALUES(?,?,?)", (now(), kind, json.dumps(detail,separators=(",",":"),ensure_ascii=False))); con.commit()


def ps_encoded(script: str) -> str:
    return base64.b64encode(script.encode("utf-16le")).decode("ascii")


def ssh_ps(alias, script, timeout=30):
    return subprocess.run(
        ["ssh","-o","BatchMode=yes","-o","ConnectTimeout=5",alias,"powershell","-NoProfile","-EncodedCommand",ps_encoded(script)],
        cwd=HOME,text=True,capture_output=True,timeout=timeout,check=False,
    )


def choose_alias():
    for alias in SSH_ALIASES:
        p=ssh_ps(alias,"$env:COMPUTERNAME",timeout=10)
        if p.returncode==0 and p.stdout.strip(): return alias
    return None


def ensure_remote():
    alias=choose_alias()
    if not alias: raise RuntimeError("SSH Axis to THECAULDRON is not callable")
    script=rf'''
$ErrorActionPreference='Stop'
$root=Join-Path $env:LOCALAPPDATA 'HomeCenter\ChromiumThrone'
$cap=Join-Path $root 'relay-capability.txt'
$runtime=Join-Path $root 'runtime-config.json'
$extension=Join-Path $root 'extension'
$relayConfig=Join-Path $extension 'relay-config.mjs'
$launcher=Join-Path $root 'launch-chromium-throne.cmd'
New-Item -ItemType Directory -Force -Path $root | Out-Null
if(!(Test-Path $cap)){{ ([guid]::NewGuid().ToString('N')+[guid]::NewGuid().ToString('N')) | Set-Content -NoNewline -Encoding ascii $cap }}
$capText=(Get-Content $cap -Raw).Trim()
if($capText.Length -lt 32){{ throw 'relay capability too short' }}
$repo=Get-ChildItem -Path $env:USERPROFILE -Directory -Filter home-center -Recurse -Depth 6 -ErrorAction SilentlyContinue | Where-Object {{ $_.FullName -notmatch '\\node_modules\\' -and (Test-Path (Join-Path $_.FullName 'browser-porch\throne-relay-runner.mjs')) }} | Select-Object -First 1 -ExpandProperty FullName
if(!$repo){{ throw 'desktop home-center checkout with throne relay not found' }}
if(!(Test-Path $relayConfig)){{ throw 'installed Chromium Throne extension directory missing relay-config.mjs' }}
@"
export const THRONE_RELAY = Object.freeze({{
  enabled: true,
  baseUrl: 'http://127.0.0.1:9234/v1/throne',
  capability: '$capText',
  pollSeconds: 30,
}});
"@ | Set-Content -Encoding utf8 $relayConfig
$receipt=$null
$receiptPath=Join-Path $root 'install-receipt.json'
if(Test-Path $receiptPath){{ try {{$receipt=Get-Content $receiptPath -Raw | ConvertFrom-Json}} catch {{}} }}
$runtimeObj=[ordered]@{{relayBase='http://127.0.0.1:9234/v1/throne';extensionId='{EXTENSION_ID}';extensionDir=$extension;profileDir=if($receipt.profileDir){{$receipt.profileDir}}else{{Join-Path $root 'profile'}};browserExe=if($receipt.browserExe){{$receipt.browserExe}}else{{$null}}}}
$runtimeObj | ConvertTo-Json -Depth 4 | Set-Content -Encoding utf8 $runtime
$node=(Get-Command node.exe -ErrorAction SilentlyContinue); if(!$node){{$node=Get-Command node -ErrorAction Stop}}
$listening=Get-NetTCPConnection -LocalPort 9234 -State Listen -ErrorAction SilentlyContinue
if(!$listening){{
  $runner=Join-Path $repo 'browser-porch\throne-relay-runner.mjs'
  Start-Process -FilePath $node.Source -ArgumentList @('"'+$runner+'"') -WindowStyle Hidden
  $deadline=(Get-Date).AddSeconds(8)
  do{{Start-Sleep -Milliseconds 300;$listening=Get-NetTCPConnection -LocalPort 9234 -State Listen -ErrorAction SilentlyContinue}}while(!$listening -and (Get-Date)-lt $deadline)
}}
if(!$listening){{ throw 'Chromium Throne relay did not listen on 9234' }}
if(Test-Path $launcher){{ Start-Process -FilePath $launcher | Out-Null }}
[ordered]@{{ok=$true;alias='{alias}';repo=$repo;root=$root;client=(Join-Path $repo 'browser-porch\throne-client.mjs');relay='http://127.0.0.1:9234/v1/throne';extensionId='{EXTENSION_ID}'}} | ConvertTo-Json -Compress
'''
    p=ssh_ps(alias,script,timeout=40)
    if p.returncode: raise RuntimeError("remote Throne relay repair failed: "+(p.stderr or p.stdout)[-4000:])
    line=next((x for x in reversed(p.stdout.splitlines()) if x.strip().startswith("{")),"")
    if not line: raise RuntimeError("remote Throne repair returned no JSON receipt: "+p.stdout[-2000:])
    info=json.loads(line)
    with db() as con:
        con.execute("INSERT INTO meta(key,value) VALUES('remote',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",(json.dumps(info,separators=(",",":")),));con.commit();event(con,"remote-ready",{k:v for k,v in info.items() if k!='capability'})
    return info


def remote_info():
    with db() as con:
        r=con.execute("SELECT value FROM meta WHERE key='remote'").fetchone()
    return json.loads(r[0]) if r else ensure_remote()


def submit_command(action, jobs=None):
    info=remote_info(); alias=info["alias"]
    command={"commandId":f"phone-{int(now()*1000)}-{uuid.uuid4().hex[:8]}","action":action}
    if jobs is not None: command["jobs"]=jobs
    raw=base64.urlsafe_b64encode(json.dumps(command,separators=(",",":"),ensure_ascii=False).encode()).decode().rstrip("=")
    client=info["client"]
    script=rf'''$ErrorActionPreference='Stop';$node=(Get-Command node.exe -ErrorAction SilentlyContinue);if(!$node){{$node=Get-Command node -ErrorAction Stop}};& $node.Source '{client}' --command-b64 '{raw}';if($LASTEXITCODE -ne 0){{exit $LASTEXITCODE}}'''
    p=ssh_ps(alias,script,timeout=35)
    if p.returncode:
        # Remote relay may have died since discovery. Repair once, then caller/backoff owns later retries.
        ensure_remote(); raise RuntimeError("throne-client submit failed: "+(p.stderr or p.stdout)[-4000:])
    line=next((x for x in reversed(p.stdout.splitlines()) if x.strip().startswith("{")),"")
    if not line: raise RuntimeError("throne-client returned no JSON: "+p.stdout[-2000:])
    return command,json.loads(line)


def relay_status():
    info=remote_info(); alias=info["alias"]
    script=r'''$ErrorActionPreference='Stop';$root=Join-Path $env:LOCALAPPDATA 'HomeCenter\ChromiumThrone';$cap=(Get-Content (Join-Path $root 'relay-capability.txt') -Raw).Trim();$h=@{Authorization=('Bearer '+$cap)};Invoke-RestMethod -Uri 'http://127.0.0.1:9234/v1/throne/status' -Headers $h -Method Get | ConvertTo-Json -Depth 20 -Compress'''
    p=ssh_ps(alias,script,timeout=20)
    if p.returncode: raise RuntimeError("relay status failed: "+(p.stderr or p.stdout)[-4000:])
    line=next((x for x in reversed(p.stdout.splitlines()) if x.strip().startswith("{")),"")
    if not line: raise RuntimeError("relay status returned no JSON")
    return json.loads(line)


def enqueue_task(repo_root,prompt):
    tid=f"task-{int(now()*1000)}-{uuid.uuid4().hex[:6]}"; job=f"job-{tid}"; ts=now()
    with db() as con:
        con.execute("INSERT INTO tasks(id,created,updated,repo_root,prompt,state,job_id) VALUES(?,?,?,?,?,?,?)",(tid,ts,ts,repo_root,prompt,"queued",job));con.commit();event(con,"task-queued",{"id":tid,"jobId":job})
    advance_task(tid,force=True)
    return get_task(tid)


def get_task(tid):
    with db() as con:
        r=con.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
    if not r:return None
    d=dict(r)
    if d.get("receipt"):
        try:d.update({"remoteReceipt":json.loads(d["receipt"])})
        except Exception:pass
    d["status"]=d.pop("state")
    d["repoRoot"]=d.pop("repo_root")
    return d


def advance_task(tid,force=False):
    with db() as con:
        row=con.execute("SELECT * FROM tasks WHERE id=?",(tid,)).fetchone()
        if not row:return None
        t=dict(row)
    if t["state"] in {"done","failed","human_gate"} and not force:return get_task(tid)
    if not t.get("command_id") or force:
        wave=t["wave"]+1
        command,accepted=submit_command("swarm.enqueue",[{"jobId":t["job_id"],"commission":t["prompt"],"context":f"Desktop repository/workspace target: {t['repo_root']}"}])
        with db() as con:
            con.execute("UPDATE tasks SET state='running',updated=?,command_id=?,wave=?,receipt=?,error=NULL WHERE id=?",(now(),command["commandId"],wave,json.dumps({"accepted":accepted},separators=(",",":")),tid));con.commit();event(con,"wave-submitted",{"id":tid,"commandId":command["commandId"],"wave":wave})
        return get_task(tid)
    status=relay_status(); cmd=next((c for c in status.get("commands",[]) if c.get("commandId")==t["command_id"]),None)
    if not cmd:return get_task(tid)
    if cmd.get("state") in {"queued","leased"}:return get_task(tid)
    result=cmd.get("result") or {}
    if cmd.get("state")=="failed":
        with db() as con:con.execute("UPDATE tasks SET state='failed',updated=?,receipt=?,error=? WHERE id=?",(now(),json.dumps(cmd,separators=(",",":")),json.dumps(result,separators=(",",":")),tid));con.commit()
        return get_task(tid)
    run=result.get("run") or result.get("result",{}).get("run") or {}
    continuation=bool(run.get("continuationPending"))
    if cmd.get("state")=="completed" and continuation:
        # Reuse the same jobId: the extension de-duplicates job creation but runStoredSwarm resumes
        # the durable queue, giving another bounded wave without duplicating work.
        command,accepted=submit_command("swarm.enqueue",[{"jobId":t["job_id"],"commission":t["prompt"],"context":f"Resume existing durable job {t['job_id']} for target {t['repo_root']}."}])
        with db() as con:con.execute("UPDATE tasks SET state='running',updated=?,command_id=?,wave=wave+1,receipt=? WHERE id=?",(now(),command["commandId"],json.dumps({"previous":cmd,"accepted":accepted},separators=(",",":")),tid));con.commit();event(con,"wave-continued",{"id":tid,"commandId":command["commandId"]})
        return get_task(tid)
    final_state="done" if cmd.get("state")=="completed" else cmd.get("state","failed")
    with db() as con:con.execute("UPDATE tasks SET state=?,updated=?,receipt=?,error=NULL WHERE id=?",(final_state,now(),json.dumps({"command":cmd,"snapshot":status.get("snapshot")},separators=(",",":"),ensure_ascii=False),tid));con.commit();event(con,"task-terminal",{"id":tid,"state":final_state})
    return get_task(tid)


def state_snapshot():
    with db() as con: rows=[dict(r) for r in con.execute("SELECT * FROM tasks ORDER BY created")]
    tasks=[]
    for r in rows:
        try:advance_task(r["id"])
        except Exception as e:
            with db() as con:con.execute("UPDATE tasks SET error=?,updated=? WHERE id=?",(repr(e),now(),r["id"]));con.commit()
        tasks.append(get_task(r["id"]))
    return {"ok":True,"tasks":tasks,"adapter":{"contract":"home-center.chromium-throne.v1","transport":"SSH Axis -> THECAULDRON -> existing Chromium Throne relay"}}


class Handler(BaseHTTPRequestHandler):
    def sendj(self,status,obj):
        raw=json.dumps(obj,ensure_ascii=False).encode();self.send_response(status);self.send_header("content-type","application/json");self.send_header("content-length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def body(self):
        n=int(self.headers.get("content-length","0") or 0);return json.loads(self.rfile.read(n).decode() or "{}")
    def log_message(self,fmt,*args): return
    def do_GET(self):
        p=urlparse(self.path).path
        if p=="/health":return self.sendj(200,{"ok":True,"contract":"home-center.chromium-throne.v1","adapter":True,"transport":"ssh-axis-relay"})
        if p=="/api/state":
            try:return self.sendj(200,state_snapshot())
            except Exception as e:return self.sendj(503,{"error":repr(e)})
        return self.sendj(404,{"error":"NOT_FOUND"})
    def do_POST(self):
        p=urlparse(self.path).path
        try:
            if p=="/api/tasks":
                b=self.body();prompt=str(b.get("prompt") or "").strip();repo=str(b.get("repoRoot") or "").strip()
                if not prompt or not repo:return self.sendj(400,{"error":"repoRoot and prompt required"})
                return self.sendj(202,enqueue_task(repo,prompt))
            if p.startswith("/api/tasks/") and p.endswith("/retry"):
                tid=p.split("/")[3]
                if not get_task(tid):return self.sendj(404,{"error":"task not found"})
                return self.sendj(202,advance_task(tid,force=True))
            return self.sendj(404,{"error":"NOT_FOUND"})
        except Exception as e:return self.sendj(503,{"error":repr(e)})


def serve():
    ensure_remote()
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()


def main():
    ap=argparse.ArgumentParser();sp=ap.add_subparsers(dest="cmd",required=True);sp.add_parser("serve");sp.add_parser("diagnose")
    a=ap.parse_args()
    if a.cmd=="serve":serve()
    else:
        try:print(json.dumps({"ok":True,"remote":ensure_remote(),"relay":relay_status()},indent=2))
        except Exception as e:print(json.dumps({"ok":False,"error":repr(e)},indent=2));raise SystemExit(2)

if __name__=="__main__":main()
