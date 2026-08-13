#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

HOME = Path.home()
REPO = Path(os.environ.get("FORTRESS_HOME_CENTER", "/storage/emulated/0/Documents/GodotProjects/home-center"))
STATE = HOME / ".local/state/home-center/fortress-campaign"
DB = STATE / "campaign.sqlite3"
LOG = STATE / "campaign.jsonl"
KERNEL = REPO / "tools/fortress_phone_kernel.py"
FORTRESS = REPO / "tools/fortress_cli.py"
THRONE = REPO / "tools/chromium_throne_cli.mjs"
JAR_CANDIDATES = [
    HOME / ".local/share/vlad/judgment-jars",
    HOME / ".local/state/vlad/judgment-jars",
    REPO / "judgment-jars",
]


def run(argv, cwd=REPO, timeout=60):
    return subprocess.run([str(x) for x in argv], cwd=cwd, text=True, capture_output=True, timeout=timeout, check=False)


def now():
    return time.time()


def connect():
    STATE.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    con.executescript("""
    PRAGMA journal_mode=WAL;
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS events(
      seq INTEGER PRIMARY KEY AUTOINCREMENT,
      ts REAL NOT NULL,
      kind TEXT NOT NULL,
      detail TEXT NOT NULL
    );
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
    """)
    return con


def emit(con, kind, detail):
    payload = json.dumps(detail, separators=(",", ":"), ensure_ascii=False)
    con.execute("INSERT INTO events(ts,kind,detail) VALUES(?,?,?)", (now(), kind, payload))
    con.commit()
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now(), "kind": kind, "detail": detail}, separators=(",", ":"), ensure_ascii=False) + "\n")


def set_meta(con, key, value):
    con.execute("INSERT INTO meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, json.dumps(value, separators=(",", ":"))))
    con.commit()


def get_meta(con, key, default=None):
    r = con.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return json.loads(r[0]) if r else default


def git(*args, timeout=60):
    return run(["git", *args], timeout=timeout)


def dirty_tree_recovery(con):
    """Step 1: preserve dirty/untracked work into a named reversible stash and verify clean state."""
    top = git("rev-parse", "--show-toplevel")
    if top.returncode:
        raise RuntimeError("Home Center path is not a Git working tree: " + top.stderr.strip())
    status = git("status", "--porcelain=v2", "--branch")
    if status.returncode:
        raise RuntimeError("git status failed: " + status.stderr.strip())
    before = status.stdout
    set_meta(con, "dirty_tree_before", before)
    emit(con, "dirty-tree-observed", {"dirty": bool(before.strip()), "status": before[-20000:]})

    # Ignore the branch header when deciding whether there are actual changes.
    changed = [ln for ln in before.splitlines() if ln and not ln.startswith("# branch.")]
    if not changed:
        emit(con, "dirty-tree-clean", {})
        return {"changed": False, "stash": None}

    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    message = f"fortress-rescue-{stamp}"
    p = git("stash", "push", "-u", "-m", message, timeout=180)
    if p.returncode:
        raise RuntimeError("BLOCKED: could not preserve dirty tree: " + p.stderr.strip())

    stash_ref = git("rev-parse", "stash@{0}")
    if stash_ref.returncode:
        raise RuntimeError("BLOCKED: stash was created but its OID could not be proven")
    oid = stash_ref.stdout.strip()
    show = git("stash", "show", "--stat", "--include-untracked", "stash@{0}")
    after = git("status", "--porcelain=v2", "--branch")
    if after.returncode:
        raise RuntimeError("BLOCKED: post-stash status failed")
    remaining = [ln for ln in after.stdout.splitlines() if ln and not ln.startswith("# branch.")]
    if remaining:
        raise RuntimeError("BLOCKED: rescue stash did not produce a clean tracked/untracked tree; refusing bootstrap")

    receipt = {
        "message": message,
        "oid": oid,
        "stat": show.stdout[-20000:],
        "restore": "git stash apply --index stash@{0}",
    }
    set_meta(con, "dirty_tree_rescue", receipt)
    emit(con, "dirty-tree-rescued", receipt)
    return {"changed": True, "stash": receipt}


def find_jar_cache():
    env = os.environ.get("VLAD_JUDGMENT_JARS")
    candidates = ([Path(env)] if env else []) + JAR_CANDIDATES
    for p in candidates:
        try:
            if p.exists() and p.is_dir():
                return p
        except OSError:
            pass
    return None


def venice_review(con, mission, phase):
    """Consume Vlad's fast local jar cache when present. Never fabricate approval."""
    jars = find_jar_cache()
    if jars is None:
        return {"verdict": "CONTINUE_REQUIRED", "source": "no-local-jar-cache", "phase": phase}

    # A local executable adapter may be supplied by the Vlad/jar-cache campaign.
    adapters = [
        jars / "bin" / "venice-review",
        HOME / "bin" / "venice-review",
        REPO / "tools" / "venice_judgment.py",
    ]
    adapter = next((p for p in adapters if p.exists()), None)
    if adapter is None:
        return {"verdict": "CONTINUE_REQUIRED", "source": str(jars), "phase": phase, "reason": "cache-present-adapter-pending"}

    packet = {
        "phase": phase,
        "missionId": mission["id"],
        "prompt": mission["prompt"],
        "state": mission["state"],
        "attempt": mission["attempt"],
    }
    argv = [str(adapter), json.dumps(packet, separators=(",", ":"))]
    if adapter.suffix == ".py":
        argv.insert(0, sys.executable)
    p = run(argv, cwd=REPO, timeout=90)
    receipt = {"source": str(adapter), "exitCode": p.returncode, "stdout": p.stdout[-20000:], "stderr": p.stderr[-20000:], "phase": phase}
    if p.returncode != 0:
        receipt["verdict"] = "CONTINUE_REQUIRED"
        return receipt
    try:
        parsed = json.loads(p.stdout)
        verdict = parsed.get("verdict") or parsed.get("directive")
    except Exception:
        verdict = None
    receipt["verdict"] = verdict if verdict in {"PLAN_ALLOWED", "STOP_ALLOWED", "CONTINUE_REQUIRED", "HALT_REQUIRED"} else "CONTINUE_REQUIRED"
    return receipt


def worker_dispatch(con, mission):
    prompt = mission["prompt"]
    # Preferred path is existing Chromium Throne CLI. Fall back to deterministic Fortress compiler;
    # absence of either is a recoverable state, not permission to invent another worker transport.
    if THRONE.exists():
        payload = {
            "commission": prompt,
            "mode": "chat",
            "reasoning": "pro",
            "portcullis": "LOCKED",
            "campaign": "phone-swarm-coding",
        }
        p = run(["node", str(THRONE), "enqueue", json.dumps(payload, separators=(",", ":"))], timeout=60)
        return {"lane": "chromium-throne", "exitCode": p.returncode, "stdout": p.stdout[-20000:], "stderr": p.stderr[-20000:]}
    if FORTRESS.exists():
        p = run([sys.executable, str(FORTRESS), "-c", prompt], timeout=180)
        return {"lane": "fortress-cli", "exitCode": p.returncode, "stdout": p.stdout[-20000:], "stderr": p.stderr[-20000:]}
    return {"lane": "none", "exitCode": 127, "stderr": "No existing Chromium Throne or Fortress CLI adapter is installed"}


def enqueue(prompt):
    with connect() as con:
        ts = now()
        cur = con.execute("INSERT INTO missions(created,updated,state,prompt,next_eligible) VALUES(?,?,?,?,?)", (ts, ts, "queued", prompt, ts))
        mid = cur.lastrowid
        con.commit()
        emit(con, "mission-queued", {"id": mid, "sha256": hashlib.sha256(prompt.encode()).hexdigest()})
        return mid


def one_cycle(con):
    row = con.execute("SELECT * FROM missions WHERE state NOT IN ('accepted','halted') AND next_eligible<=? ORDER BY created LIMIT 1", (now(),)).fetchone()
    if not row:
        return {"acted": False, "reason": "idle"}
    mission = dict(row)

    if mission["state"] in {"queued", "retry"}:
        plan = venice_review(con, mission, "plan")
        emit(con, "venice-plan", {"mission": mission["id"], **plan})
        if plan.get("verdict") == "HALT_REQUIRED":
            con.execute("UPDATE missions SET state='halted',updated=?,venice_receipt=? WHERE id=?", (now(), json.dumps(plan), mission["id"]))
            con.commit(); return {"acted": True, "state": "halted"}
        # Missing/unfinished local jar integration may not self-approve; continue execution under existing
        # commissioned authority, but it cannot ever authorize STOP.
        receipt = worker_dispatch(con, mission)
        attempt = mission["attempt"] + 1
        if receipt.get("exitCode") == 0:
            state = "review"
            delay = 5
        else:
            state = "retry"
            delay = min(300, 5 * (2 ** min(attempt, 6)))
        con.execute("UPDATE missions SET state=?,updated=?,attempt=?,next_eligible=?,worker_receipt=?,error=? WHERE id=?",
                    (state, now(), attempt, now()+delay, json.dumps(receipt), receipt.get("stderr"), mission["id"]))
        con.commit(); emit(con, "worker-dispatch", {"mission": mission["id"], **receipt, "nextState": state, "backoffSeconds": delay})
        return {"acted": True, "state": state}

    if mission["state"] == "review":
        stop = venice_review(con, mission, "stop")
        emit(con, "venice-stop", {"mission": mission["id"], **stop})
        if stop.get("verdict") == "STOP_ALLOWED":
            con.execute("UPDATE missions SET state='accepted',updated=?,venice_receipt=? WHERE id=?", (now(), json.dumps(stop), mission["id"]))
            con.commit(); emit(con, "mission-accepted", {"mission": mission["id"]})
            return {"acted": True, "state": "accepted"}
        if stop.get("verdict") == "HALT_REQUIRED":
            con.execute("UPDATE missions SET state='halted',updated=?,venice_receipt=? WHERE id=?", (now(), json.dumps(stop), mission["id"]))
            con.commit(); return {"acted": True, "state": "halted"}
        con.execute("UPDATE missions SET state='retry',updated=?,next_eligible=?,venice_receipt=? WHERE id=?", (now(), now()+10, json.dumps(stop), mission["id"]))
        con.commit(); return {"acted": True, "state": "retry"}

    return {"acted": False, "reason": mission["state"]}


def daemon():
    STATE.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        set_meta(con, "daemon_pid", os.getpid())
        emit(con, "daemon-started", {"pid": os.getpid(), "repo": str(REPO)})
    delay = 2
    while True:
        try:
            with connect() as con:
                r = one_cycle(con)
            delay = 2 if r.get("acted") else min(30, delay + 2)
        except Exception as e:
            with connect() as con:
                emit(con, "daemon-error", {"error": repr(e), "backoff": delay})
            delay = min(300, max(5, delay * 2))
        time.sleep(delay)


def status():
    with connect() as con:
        missions = [dict(r) for r in con.execute("SELECT id,state,attempt,updated,next_eligible,error FROM missions ORDER BY updated DESC LIMIT 10")]
        return {
            "ok": True,
            "repo": str(REPO),
            "db": str(DB),
            "dirtyTreeRescue": get_meta(con, "dirty_tree_rescue"),
            "jarCache": str(find_jar_cache()) if find_jar_cache() else None,
            "missions": missions,
            "daemonPid": get_meta(con, "daemon_pid"),
        }


def main():
    ap = argparse.ArgumentParser(prog="fortress-campaign")
    sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("recover-dirty-tree")
    sp.add_parser("daemon")
    sp.add_parser("status")
    q = sp.add_parser("prompt"); q.add_argument("text")
    a = ap.parse_args()
    if a.cmd == "recover-dirty-tree":
        with connect() as con: print(json.dumps(dirty_tree_recovery(con), indent=2))
    elif a.cmd == "daemon": daemon()
    elif a.cmd == "status": print(json.dumps(status(), indent=2))
    elif a.cmd == "prompt": print(json.dumps({"ok": True, "mission": enqueue(a.text)}))


if __name__ == "__main__":
    main()
