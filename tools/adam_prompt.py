#!/usr/bin/env python3
"""Operator-owned, supervised phone entrypoint for Home Center/Adam.

Bare ``adam <prompt>`` is deliberately NON-BLOCKING: it persists the commission,
starts a detached supervisor, prints a run id/status/receipt path, and returns the
operator's shell immediately. The supervisor owns the worker process group and
keeps durable liveness state even if the launching Termux tab dies.

Operator controls:
  adam "do the thing"       submit work and return immediately
  adam --status             current run / phase / heartbeat
  adam --follow             stream the current run log (Ctrl-C only stops follow)
  adam --stop               stop the current worker tree out-of-band
  adam --resume             resubmit the last unfinished commission
  adam --receipts           print latest receipt and state
  adam --canary             run the process-isolation/kill-path regression canary

The wrapper does not invent a new execution stack. Supervised work delegates to
Home Center's existing tools/adam.py router so prompts inherit the same Codex,
Venice, Judgment Jar, receipts, and deterministic phone orchestration contract.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path

HEARTBEAT_SECONDS = 5
STOP_GRACE_SECONDS = 3


def find_repo() -> Path:
    candidates: list[Path] = []
    if os.environ.get("HOME_CENTER_ROOT"):
        candidates.append(Path(os.environ["HOME_CENTER_ROOT"]).expanduser())
    if os.environ.get("ADAM_DO_REPO"):
        candidates.append(Path(os.environ["ADAM_DO_REPO"]).expanduser())
    candidates.extend([Path.home()/"home-center", Path.home()/"src"/"home-center", Path.home()/"repos"/"home-center"])
    for root in candidates:
        if (root/"tools"/"adam.py").is_file():
            return root.resolve()
    raise SystemExit("BLOCKED: Home Center checkout not found. Set HOME_CENTER_ROOT to the checkout containing tools/adam.py")


def state_root() -> Path:
    p = Path(os.environ.get("HC_STATE_DIR", "~/.local/state/home-center")).expanduser()/"adam-do"
    (p/"runs").mkdir(parents=True, exist_ok=True)
    return p


def atomic_json(path: Path, payload: dict) -> None:
    tmp = path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)+"\n", encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def current_state() -> dict:
    return load_json(state_root()/"current.json")


def update_state(run_dir: Path, **fields) -> dict:
    path = run_dir/"state.json"
    data = load_json(path)
    data.update(fields)
    data["updatedAtEpoch"] = int(time.time())
    atomic_json(path, data)
    atomic_json(state_root()/"current.json", data)
    return data


def append_receipt(payload: dict) -> None:
    root = state_root()
    with (root/"receipts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True)+"\n")
    atomic_json(root/"last.json", payload)


def read_prompt(values: list[str]) -> str:
    text = " ".join(values).strip()
    if not text and not sys.stdin.isatty():
        text = sys.stdin.read().strip()
    return text


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def kill_group(pgid: int, sig: int) -> bool:
    if pgid <= 0:
        return False
    try:
        os.killpg(pgid, sig)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return False


def notify_menu(root: Path) -> None:
    menu = root/"tools"/"home_center_status_menu.sh"
    if menu.is_file() and shutil_which("termux-notification"):
        subprocess.run(["bash", str(menu), "adam"], cwd=root, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)


def shutil_which(name: str) -> str | None:
    from shutil import which
    return which(name)


def supervisor(run_dir: Path) -> int:
    mission = load_json(run_dir/"mission.json")
    root = Path(str(mission["repo"]))
    mode = str(mission["mode"])
    text = str(mission["prompt"])
    timeout = int(mission["timeout"])
    log_path = run_dir/"worker.log"
    started = int(time.time())
    update_state(run_dir, schema="adam-do-run-v2", runId=mission["runId"], status="STARTING", phase="launch-worker", prompt=text[:12000], mode=mode, repo=str(root), supervisorPid=os.getpid(), workerPid=None, workerPgid=None, startedAtEpoch=started, heartbeatAtEpoch=started, log=str(log_path), receipt=str(run_dir/"receipt.json"))
    command = [sys.executable, str(root/"tools"/"adam.py"), mode, text, "--cwd", str(root), "--timeout", str(timeout)]
    with log_path.open("ab", buffering=0) as log:
        proc = subprocess.Popen(command, cwd=root, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        pgid = os.getpgid(proc.pid)
        update_state(run_dir, status="RUNNING", phase="worker", workerPid=proc.pid, workerPgid=pgid, heartbeatAtEpoch=int(time.time()), lastMeaningfulAction="worker launched")
        notify_menu(root)
        deadline = time.monotonic()+timeout if timeout > 0 else None
        timed_out = False
        while proc.poll() is None:
            now = int(time.time())
            update_state(run_dir, status="RUNNING", phase="worker", workerPid=proc.pid, workerPgid=pgid, heartbeatAtEpoch=now, elapsedSeconds=now-started, lastMeaningfulAction="worker active")
            if deadline is not None and time.monotonic() >= deadline:
                timed_out = True
                update_state(run_dir, status="STOPPING", phase="timeout", lastMeaningfulAction="timeout: terminating worker group")
                kill_group(pgid, signal.SIGTERM)
                try:
                    proc.wait(timeout=STOP_GRACE_SECONDS)
                except subprocess.TimeoutExpired:
                    kill_group(pgid, signal.SIGKILL)
                break
            time.sleep(HEARTBEAT_SECONDS)
        rc = proc.wait()
    finished = int(time.time())
    stopped = bool(load_json(run_dir/"state.json").get("stopRequested"))
    ok = rc == 0 and not timed_out and not stopped
    final_status = "VERIFIED" if ok else "STOPPED" if stopped else "TIMEOUT" if timed_out else "FAILED"
    receipt = {"schema":"adam-do-receipt-v2","runId":mission["runId"],"startedAtEpoch":started,"finishedAtEpoch":finished,"mode":mode,"prompt":text[:12000],"repo":str(root),"rc":rc,"ok":ok,"status":final_status,"log":str(log_path),"state":str(run_dir/"state.json"),"processIsolation":True,"operatorShellNonBlocking":True,"workerProcessGroup":pgid}
    atomic_json(run_dir/"receipt.json", receipt)
    append_receipt(receipt)
    update_state(run_dir, status=final_status, phase="complete", rc=rc, ok=ok, finishedAtEpoch=finished, heartbeatAtEpoch=finished, elapsedSeconds=finished-started, lastMeaningfulAction="worker exited")
    notify_menu(root)
    return 0 if ok else rc or 1


def submit(mode: str, text: str, timeout: int) -> int:
    if not text:
        print('usage: adam "what you want done"', file=sys.stderr)
        return 64
    root = find_repo()
    run_id = time.strftime("%Y%m%d-%H%M%S")+"-"+uuid.uuid4().hex[:8]
    run_dir = state_root()/"runs"/run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    mission = {"schema":"adam-do-mission-v2","runId":run_id,"mode":mode,"prompt":text,"timeout":timeout,"repo":str(root),"submittedAtEpoch":int(time.time())}
    atomic_json(run_dir/"mission.json", mission)
    update_state(run_dir, schema="adam-do-run-v2", runId=run_id, status="QUEUED", phase="supervisor", prompt=text[:12000], mode=mode, repo=str(root), submittedAtEpoch=int(time.time()), log=str(run_dir/"worker.log"), receipt=str(run_dir/"receipt.json"))
    supervisor_log = (run_dir/"supervisor.log").open("ab", buffering=0)
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "--_supervise", str(run_dir)], cwd=root, stdin=subprocess.DEVNULL, stdout=supervisor_log, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    supervisor_log.close()
    update_state(run_dir, supervisorPid=proc.pid, status="STARTING", phase="supervisor", heartbeatAtEpoch=int(time.time()))
    print(f"ADAM RUNNING  run={run_id}")
    print(f"status:  adam --status")
    print(f"follow:  adam --follow")
    print(f"stop:    adam --stop")
    print(f"receipt: {run_dir/'receipt.json'}")
    return 0


def status() -> int:
    s = current_state()
    if not s:
        print("ADAM IDLE — no recorded run")
        return 0
    hb = int(s.get("heartbeatAtEpoch") or s.get("updatedAtEpoch") or 0)
    age = max(0, int(time.time())-hb) if hb else -1
    supervisor_pid = int(s.get("supervisorPid") or 0)
    worker_pid = int(s.get("workerPid") or 0)
    alive = pid_alive(supervisor_pid) or pid_alive(worker_pid)
    print(f"ADAM {s.get('status','UNKNOWN')}  run={s.get('runId','?')}  phase={s.get('phase','?')}")
    print(f"alive={str(alive).lower()} heartbeat_age={age}s elapsed={s.get('elapsedSeconds',0)}s")
    print(f"last={s.get('lastMeaningfulAction','')}")
    print(f"log={s.get('log','')}")
    print(f"receipt={s.get('receipt','')}")
    return 0 if alive or s.get("status") in {"VERIFIED","FAILED","STOPPED","TIMEOUT"} else 2


def stop_current() -> int:
    s = current_state()
    if not s:
        print("ADAM IDLE — nothing to stop")
        return 0
    run_id = str(s.get("runId") or "")
    run_dir = state_root()/"runs"/run_id
    pgid = int(s.get("workerPgid") or 0)
    supervisor_pid = int(s.get("supervisorPid") or 0)
    update_state(run_dir, stopRequested=True, status="STOPPING", phase="operator-stop", lastMeaningfulAction="operator requested stop")
    killed = kill_group(pgid, signal.SIGTERM)
    deadline = time.monotonic()+STOP_GRACE_SECONDS
    while time.monotonic() < deadline and pgid > 0:
        try: os.killpg(pgid, 0)
        except OSError: break
        time.sleep(.1)
    else:
        killed = kill_group(pgid, signal.SIGKILL) or killed
    if pid_alive(supervisor_pid):
        try: os.kill(supervisor_pid, signal.SIGTERM)
        except OSError: pass
    update_state(run_dir, status="STOPPED", phase="operator-stop", heartbeatAtEpoch=int(time.time()), lastMeaningfulAction="worker tree stopped out-of-band")
    print(f"ADAM STOPPED  run={run_id} worker_group_killed={str(killed).lower()}")
    return 0


def follow() -> int:
    s = current_state()
    if not s:
        print("ADAM IDLE — no run to follow")
        return 0
    log = Path(str(s.get("log") or ""))
    print(f"Following {s.get('runId')} — Ctrl-C exits follow only; use `adam --stop` to stop work.")
    pos = 0
    try:
        while True:
            if log.exists():
                with log.open("r", encoding="utf-8", errors="replace") as f:
                    f.seek(pos); chunk=f.read(); pos=f.tell()
                if chunk:
                    print(chunk, end="", flush=True)
            cur = current_state()
            if cur.get("runId") == s.get("runId") and cur.get("status") in {"VERIFIED","FAILED","STOPPED","TIMEOUT"}:
                print(f"\nADAM {cur.get('status')} rc={cur.get('rc','?')} receipt={cur.get('receipt','')}")
                return 0 if cur.get("status") == "VERIFIED" else 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nFollow detached. Adam continues in background.")
        return 130


def receipts() -> int:
    for path in [state_root()/"current.json", state_root()/"last.json"]:
        if path.exists():
            print(f"===== {path} =====")
            print(path.read_text(encoding="utf-8"), end="")
    return 0


def resume() -> int:
    s = current_state()
    run_id = str(s.get("runId") or "")
    mission = load_json(state_root()/"runs"/run_id/"mission.json") if run_id else {}
    if not mission:
        print("BLOCKED: no durable commission to resume", file=sys.stderr)
        return 2
    if s.get("status") in {"RUNNING","STARTING","QUEUED"} and (pid_alive(int(s.get("supervisorPid") or 0)) or pid_alive(int(s.get("workerPid") or 0))):
        print(f"ADAM ALREADY RUNNING  run={run_id}")
        return 0
    return submit(str(mission.get("mode") or "continue"), str(mission.get("prompt") or ""), int(mission.get("timeout") or 1800))


def canary() -> int:
    """Prove detached shell return + out-of-band process-group kill on this host."""
    root = state_root()/"canary"
    root.mkdir(parents=True, exist_ok=True)
    marker = root/"must-not-survive.txt"
    if marker.exists(): marker.unlink()
    child_code = "import subprocess,time,sys; subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)']); print('CANARY_WORKER_READY',flush=True); time.sleep(60)"
    log = (root/"process.log").open("wb")
    p = subprocess.Popen([sys.executable,"-c",child_code], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    log.close(); pgid=os.getpgid(p.pid); started=time.monotonic(); time.sleep(.25)
    kill_group(pgid, signal.SIGTERM)
    try: p.wait(timeout=STOP_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        kill_group(pgid, signal.SIGKILL); p.wait(timeout=2)
    elapsed=time.monotonic()-started
    ok = p.poll() is not None and elapsed < STOP_GRACE_SECONDS+3
    receipt={"schema":"adam-do-process-isolation-canary-v1","ok":ok,"workerPid":p.pid,"workerPgid":pgid,"killPath":"process-group TERM->KILL","operatorShellBlocked":False,"elapsedSeconds":round(elapsed,3),"log":str(root/"process.log"),"verifiedAtEpoch":int(time.time())}
    atomic_json(root/"receipt.json",receipt); print(json.dumps(receipt,indent=2,sort_keys=True)); return 0 if ok else 1


def main(argv=None) -> int:
    p=argparse.ArgumentParser(prog="adam", description="Supervised Home Center operator command surface")
    group=p.add_mutually_exclusive_group()
    group.add_argument("--chat",action="store_true"); group.add_argument("--vlad",action="store_true"); group.add_argument("--terminal",action="store_true")
    group.add_argument("--status",action="store_true"); group.add_argument("--follow",action="store_true"); group.add_argument("--stop",action="store_true"); group.add_argument("--resume",action="store_true"); group.add_argument("--receipts",action="store_true"); group.add_argument("--canary",action="store_true")
    p.add_argument("--timeout",type=int,default=1800); p.add_argument("--_supervise",metavar="RUN_DIR",help=argparse.SUPPRESS); p.add_argument("prompt",nargs="*")
    args=p.parse_args(argv)
    if args._supervise: return supervisor(Path(args._supervise))
    if args.status: return status()
    if args.follow: return follow()
    if args.stop: return stop_current()
    if args.resume: return resume()
    if args.receipts: return receipts()
    if args.canary: return canary()
    mode="chat" if args.chat else "vlad" if args.vlad else "terminal" if args.terminal else "continue"
    return submit(mode, read_prompt(args.prompt), args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
