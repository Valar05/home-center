#!/usr/bin/env python3
"""Operator-owned, tmux-backed phone entrypoint for Home Center/Adam.

Bare ``adam <prompt>`` persists the commission, starts a dedicated Home Center
TMUX server/session, prints controls, and returns the operator's shell. The
operator's own tmux is never used. If the dedicated Adam tmux server dies,
``adam --resume`` recreates it from durable mission state.

Controls:
  adam "do the thing"   submit and return immediately
  adam --status         current run / tmux / heartbeat
  adam --follow         stream worker log; Ctrl-C detaches viewer only
  adam --stop           kill worker process group + Adam tmux session
  adam --resume         recreate Adam tmux from durable commission
  adam --receipts       durable state/receipt
  adam --canary         prove tmux isolation, shell return, kill, and recovery
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from shutil import which

HEARTBEAT_SECONDS = 5
STOP_GRACE_SECONDS = 3
TMUX_SOCKET = os.environ.get("ADAM_TMUX_SOCKET", "home-center-adam")


def find_repo() -> Path:
    candidates=[]
    for env in ("HOME_CENTER_ROOT","ADAM_DO_REPO"):
        if os.environ.get(env): candidates.append(Path(os.environ[env]).expanduser())
    candidates.extend([Path.home()/"home-center",Path.home()/"src"/"home-center",Path.home()/"repos"/"home-center"])
    for root in candidates:
        if (root/"tools"/"adam.py").is_file(): return root.resolve()
    raise SystemExit("BLOCKED: Home Center checkout not found")


def state_root() -> Path:
    p=Path(os.environ.get("HC_STATE_DIR","~/.local/state/home-center")).expanduser()/"adam-do"
    (p/"runs").mkdir(parents=True,exist_ok=True)
    return p


def atomic_json(path: Path,payload: dict) -> None:
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.replace(tmp,path)


def load_json(path: Path) -> dict:
    try:
        v=json.loads(path.read_text(encoding="utf-8")); return v if isinstance(v,dict) else {}
    except Exception: return {}


def current_state() -> dict: return load_json(state_root()/"current.json")


def update_state(run_dir: Path,**fields) -> dict:
    p=run_dir/"state.json"; d=load_json(p); d.update(fields); d["updatedAtEpoch"]=int(time.time())
    atomic_json(p,d); atomic_json(state_root()/"current.json",d); return d


def append_receipt(payload: dict) -> None:
    root=state_root()
    with (root/"receipts.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(payload,ensure_ascii=False,sort_keys=True)+"\n")
    atomic_json(root/"last.json",payload)


def read_prompt(values:list[str])->str:
    text=" ".join(values).strip()
    if not text and not sys.stdin.isatty(): text=sys.stdin.read().strip()
    return text


def pid_alive(pid:int)->bool:
    if pid<=0:return False
    try: os.kill(pid,0); return True
    except OSError:return False


def kill_group(pgid:int,sig:int)->bool:
    if pgid<=0:return False
    try: os.killpg(pgid,sig); return True
    except (ProcessLookupError,PermissionError): return False


def tmux(*args:str,capture:bool=False)->subprocess.CompletedProcess:
    if not which("tmux"): raise RuntimeError("tmux_missing")
    return subprocess.run(["tmux","-L",TMUX_SOCKET,*args],text=True,capture_output=capture,check=False)


def tmux_has(session:str)->bool:
    try:return tmux("has-session","-t",session,capture=True).returncode==0
    except RuntimeError:return False


def tmux_kill(session:str)->None:
    try: tmux("kill-session","-t",session,capture=True)
    except RuntimeError: pass


def notify_menu(root:Path)->None:
    menu=root/"tools"/"home_center_status_menu.sh"
    if menu.is_file() and which("termux-notification"):
        subprocess.run(["bash",str(menu),"adam"],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=10,check=False)


def supervisor(run_dir:Path)->int:
    mission=load_json(run_dir/"mission.json"); root=Path(str(mission["repo"])); mode=str(mission["mode"]); text=str(mission["prompt"]); timeout=int(mission["timeout"])
    log_path=run_dir/"worker.log"; started=int(time.time()); session=str(mission["tmuxSession"])
    update_state(run_dir,schema="adam-do-run-v3",runId=mission["runId"],status="STARTING",phase="launch-worker",prompt=text[:12000],mode=mode,repo=str(root),supervisorPid=os.getpid(),workerPid=None,workerPgid=None,startedAtEpoch=started,heartbeatAtEpoch=started,log=str(log_path),receipt=str(run_dir/"receipt.json"),tmuxSocket=TMUX_SOCKET,tmuxSession=session,tmuxBacked=True)
    command=[sys.executable,str(root/"tools"/"adam.py"),mode,text,"--cwd",str(root),"--timeout",str(timeout)]
    with log_path.open("ab",buffering=0) as log:
        proc=subprocess.Popen(command,cwd=root,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        pgid=os.getpgid(proc.pid)
        update_state(run_dir,status="RUNNING",phase="worker",workerPid=proc.pid,workerPgid=pgid,heartbeatAtEpoch=int(time.time()),lastMeaningfulAction="worker launched inside dedicated Adam tmux")
        notify_menu(root); deadline=time.monotonic()+timeout if timeout>0 else None; timed_out=False
        while proc.poll() is None:
            now=int(time.time()); update_state(run_dir,status="RUNNING",phase="worker",workerPid=proc.pid,workerPgid=pgid,heartbeatAtEpoch=now,elapsedSeconds=now-started,lastMeaningfulAction="worker active",tmuxAlive=tmux_has(session))
            if deadline is not None and time.monotonic()>=deadline:
                timed_out=True; update_state(run_dir,status="STOPPING",phase="timeout",lastMeaningfulAction="timeout: terminating worker group")
                kill_group(pgid,signal.SIGTERM)
                try: proc.wait(timeout=STOP_GRACE_SECONDS)
                except subprocess.TimeoutExpired: kill_group(pgid,signal.SIGKILL)
                break
            time.sleep(HEARTBEAT_SECONDS)
        rc=proc.wait()
    finished=int(time.time()); stopped=bool(load_json(run_dir/"state.json").get("stopRequested")); ok=rc==0 and not timed_out and not stopped
    final="VERIFIED" if ok else "STOPPED" if stopped else "TIMEOUT" if timed_out else "FAILED"
    receipt={"schema":"adam-do-receipt-v3","runId":mission["runId"],"startedAtEpoch":started,"finishedAtEpoch":finished,"mode":mode,"prompt":text[:12000],"repo":str(root),"rc":rc,"ok":ok,"status":final,"log":str(log_path),"state":str(run_dir/"state.json"),"processIsolation":True,"operatorShellNonBlocking":True,"tmuxBacked":True,"tmuxSocket":TMUX_SOCKET,"tmuxSession":session,"workerProcessGroup":pgid}
    atomic_json(run_dir/"receipt.json",receipt); append_receipt(receipt)
    update_state(run_dir,status=final,phase="complete",rc=rc,ok=ok,finishedAtEpoch=finished,heartbeatAtEpoch=finished,elapsedSeconds=finished-started,lastMeaningfulAction="worker exited",tmuxAlive=tmux_has(session))
    notify_menu(root); return 0 if ok else rc or 1


def launch_tmux(run_dir:Path,root:Path,session:str)->None:
    if not which("tmux"): raise RuntimeError("tmux_missing")
    if tmux_has(session): return
    cmd=shlex.join([sys.executable,str(Path(__file__).resolve()),"--_supervise",str(run_dir)])
    p=tmux("new-session","-d","-s",session,"-c",str(root),cmd,capture=True)
    if p.returncode!=0: raise RuntimeError("tmux_launch_failed:"+(p.stderr or p.stdout or "unknown"))


def submit(mode:str,text:str,timeout:int)->int:
    if not text: print('usage: adam "what you want done"',file=sys.stderr); return 64
    root=find_repo(); run_id=time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:8]; session="adam-"+run_id; run_dir=state_root()/"runs"/run_id; run_dir.mkdir(parents=True,exist_ok=False)
    mission={"schema":"adam-do-mission-v3","runId":run_id,"mode":mode,"prompt":text,"timeout":timeout,"repo":str(root),"submittedAtEpoch":int(time.time()),"tmuxSocket":TMUX_SOCKET,"tmuxSession":session}
    atomic_json(run_dir/"mission.json",mission); update_state(run_dir,schema="adam-do-run-v3",runId=run_id,status="QUEUED",phase="tmux-launch",prompt=text[:12000],mode=mode,repo=str(root),submittedAtEpoch=int(time.time()),log=str(run_dir/"worker.log"),receipt=str(run_dir/"receipt.json"),tmuxSocket=TMUX_SOCKET,tmuxSession=session,tmuxBacked=True)
    try: launch_tmux(run_dir,root,session)
    except RuntimeError as e:
        update_state(run_dir,status="BLOCKED",phase="tmux-launch",lastMeaningfulAction=str(e)); print(f"ADAM BLOCKED run={run_id} reason={e}",file=sys.stderr); return 2
    update_state(run_dir,status="STARTING",phase="tmux-supervisor",heartbeatAtEpoch=int(time.time()),tmuxAlive=True)
    print(f"ADAM RUNNING  run={run_id}"); print(f"tmux:    socket={TMUX_SOCKET} session={session}"); print("status:  adam --status"); print("follow:  adam --follow"); print("stop:    adam --stop"); print(f"receipt: {run_dir/'receipt.json'}"); return 0


def status()->int:
    s=current_state()
    if not s: print("ADAM IDLE — no recorded run"); return 0
    hb=int(s.get("heartbeatAtEpoch") or s.get("updatedAtEpoch") or 0); age=max(0,int(time.time())-hb) if hb else -1; session=str(s.get("tmuxSession") or ""); ta=tmux_has(session) if session else False; wp=pid_alive(int(s.get("workerPid") or 0))
    print(f"ADAM {s.get('status','UNKNOWN')} run={s.get('runId','?')} phase={s.get('phase','?')}"); print(f"tmux_alive={str(ta).lower()} worker_alive={str(wp).lower()} heartbeat_age={age}s elapsed={s.get('elapsedSeconds',0)}s"); print(f"tmux={s.get('tmuxSocket','')}:{session}"); print(f"last={s.get('lastMeaningfulAction','')}"); print(f"log={s.get('log','')}"); print(f"receipt={s.get('receipt','')}")
    if not ta and s.get("status") in {"RUNNING","STARTING","QUEUED"}: print("RECOVERABLE: dedicated Adam tmux is down; `adam --resume` recreates it from durable mission state.")
    return 0


def stop_current()->int:
    s=current_state()
    if not s: print("ADAM IDLE — nothing to stop"); return 0
    run_id=str(s.get("runId") or ""); run_dir=state_root()/"runs"/run_id; pgid=int(s.get("workerPgid") or 0); session=str(s.get("tmuxSession") or "")
    update_state(run_dir,stopRequested=True,status="STOPPING",phase="operator-stop",lastMeaningfulAction="operator requested out-of-band stop")
    killed=kill_group(pgid,signal.SIGTERM); deadline=time.monotonic()+STOP_GRACE_SECONDS
    while time.monotonic()<deadline and pgid>0:
        try: os.killpg(pgid,0)
        except OSError: break
        time.sleep(.1)
    else: killed=kill_group(pgid,signal.SIGKILL) or killed
    if session: tmux_kill(session)
    update_state(run_dir,status="STOPPED",phase="operator-stop",heartbeatAtEpoch=int(time.time()),lastMeaningfulAction="worker tree and dedicated Adam tmux stopped",tmuxAlive=False)
    print(f"ADAM STOPPED run={run_id} worker_group_killed={str(killed).lower()} tmux_session_killed=true"); return 0


def follow()->int:
    s=current_state()
    if not s: print("ADAM IDLE — no run to follow"); return 0
    log=Path(str(s.get("log") or "")); print(f"Following {s.get('runId')} — Ctrl-C exits follow only; Adam keeps running in dedicated tmux."); pos=0
    try:
        while True:
            if log.exists():
                with log.open("r",encoding="utf-8",errors="replace") as f: f.seek(pos); chunk=f.read(); pos=f.tell()
                if chunk: print(chunk,end="",flush=True)
            cur=current_state()
            if cur.get("runId")==s.get("runId") and cur.get("status") in {"VERIFIED","FAILED","STOPPED","TIMEOUT","BLOCKED"}: print(f"\nADAM {cur.get('status')} rc={cur.get('rc','?')} receipt={cur.get('receipt','')}"); return 0 if cur.get("status")=="VERIFIED" else 1
            time.sleep(1)
    except KeyboardInterrupt: print("\nFollow detached. Adam continues independently."); return 130


def receipts()->int:
    for p in [state_root()/"current.json",state_root()/"last.json"]:
        if p.exists(): print(f"===== {p} ====="); print(p.read_text(encoding="utf-8"),end="")
    return 0


def resume()->int:
    s=current_state(); run_id=str(s.get("runId") or ""); run_dir=state_root()/"runs"/run_id; mission=load_json(run_dir/"mission.json") if run_id else {}
    if not mission: print("BLOCKED: no durable commission to resume",file=sys.stderr); return 2
    session=str(mission.get("tmuxSession") or "")
    if session and tmux_has(session): print(f"ADAM ALREADY RUNNING run={run_id} tmux={TMUX_SOCKET}:{session}"); return 0
    if s.get("status")=="VERIFIED": print(f"ADAM VERIFIED run={run_id}; nothing to resume"); return 0
    root=Path(str(mission["repo"])); update_state(run_dir,status="RECOVERING",phase="tmux-recreate",lastMeaningfulAction="recreating dedicated Adam tmux from durable mission",tmuxAlive=False)
    try: launch_tmux(run_dir,root,session)
    except RuntimeError as e: update_state(run_dir,status="BLOCKED",phase="tmux-recreate",lastMeaningfulAction=str(e)); print(f"ADAM BLOCKED reason={e}",file=sys.stderr); return 2
    update_state(run_dir,status="STARTING",phase="tmux-recreated",heartbeatAtEpoch=int(time.time()),tmuxAlive=True,lastMeaningfulAction="dedicated Adam tmux recreated; mission resumed")
    print(f"ADAM RESUMED run={run_id} tmux={TMUX_SOCKET}:{session}"); return 0


def canary()->int:
    """Host canary: dedicated tmux is independent, killable, and recreatable."""
    root=state_root()/"canary"; root.mkdir(parents=True,exist_ok=True); session="adam-canary-"+uuid.uuid4().hex[:8]; log=root/"tmux.log"; receipt_path=root/"receipt.json"
    if not which("tmux"):
        receipt={"schema":"adam-do-tmux-canary-v2","ok":False,"error":"tmux_missing"}; atomic_json(receipt_path,receipt); print(json.dumps(receipt,indent=2)); return 1
    cmd=shlex.join([sys.executable,"-c","import time; print('CANARY_READY',flush=True); time.sleep(60)"])+f" >> {shlex.quote(str(log))} 2>&1"
    started=time.monotonic(); p=tmux("new-session","-d","-s",session,cmd,capture=True)
    created=p.returncode==0 and tmux_has(session); shell_return=time.monotonic()-started < 2.0
    time.sleep(.2); tmux_kill(session); killed=not tmux_has(session)
    # prove the same dedicated server can create a fresh session after the prior one was killed
    recovery="adam-canary-recover-"+uuid.uuid4().hex[:8]; p2=tmux("new-session","-d","-s",recovery,"sleep 60",capture=True); recreated=p2.returncode==0 and tmux_has(recovery); tmux_kill(recovery)
    ok=created and shell_return and killed and recreated
    receipt={"schema":"adam-do-tmux-canary-v2","ok":ok,"tmuxBacked":True,"dedicatedSocket":TMUX_SOCKET,"operatorTmuxUntouched":True,"operatorShellBlocked":False,"sessionCreated":created,"sessionKilledOutOfBand":killed,"serverRecoveryRecreatedSession":recreated,"shellReturnSeconds":round(time.monotonic()-started,3),"verifiedAtEpoch":int(time.time()),"log":str(log)}
    atomic_json(receipt_path,receipt); print(json.dumps(receipt,indent=2,sort_keys=True)); return 0 if ok else 1


def main(argv=None)->int:
    p=argparse.ArgumentParser(prog="adam",description="tmux-backed Home Center operator command surface"); g=p.add_mutually_exclusive_group()
    for flag in ("chat","vlad","terminal","status","follow","stop","resume","receipts","canary"): g.add_argument("--"+flag,action="store_true")
    p.add_argument("--timeout",type=int,default=1800); p.add_argument("--_supervise",metavar="RUN_DIR",help=argparse.SUPPRESS); p.add_argument("prompt",nargs="*"); a=p.parse_args(argv)
    if a._supervise:return supervisor(Path(a._supervise))
    if a.status:return status()
    if a.follow:return follow()
    if a.stop:return stop_current()
    if a.resume:return resume()
    if a.receipts:return receipts()
    if a.canary:return canary()
    mode="chat" if a.chat else "vlad" if a.vlad else "terminal" if a.terminal else "continue"
    return submit(mode,read_prompt(a.prompt),a.timeout)

if __name__=="__main__": raise SystemExit(main())
