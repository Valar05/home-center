#!/usr/bin/env python3
"""Dependency-free local swarm with durable dispatcher cutover.

The SQLite database is the state owner. Dispatchers are replaceable generations;
worker leases remain valid while an old generation drains, so cutover does not
interrupt useful in-flight work.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import socket
import sqlite3
import subprocess
import sys
import time
import uuid
from pathlib import Path

DEFAULT_DB = Path(os.environ.get("HOME_CENTER_SWARM_DB", Path.home() / ".local/state/home-center-swarm/swarm.sqlite3"))
JOB_STATES = {"READY", "RUNNING", "RETRY_WAIT", "SUCCEEDED", "WAITING_EVIDENCE", "FAILED_TERMINAL", "CANCELLED"}
DISPATCHER_STATES = {"REGISTERED", "ACTIVE", "DRAINING", "RETIRED", "LOST"}
TERMINAL_JOB_STATES = {"SUCCEEDED", "FAILED_TERMINAL", "CANCELLED"}
ROUTE_TOKENS = {"NS", "VLAD", "REGNET_QA", "VENICE"}


class SwarmError(RuntimeError):
    pass


def now_epoch() -> int:
    return int(time.time())


def canonical(value) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(value: bytes | str) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=5, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=FULL")
    db.execute("PRAGMA foreign_keys=ON")
    db.execute("PRAGMA busy_timeout=5000")
    return db


SCHEMA = """
CREATE TABLE IF NOT EXISTS control(singleton INTEGER PRIMARY KEY CHECK(singleton=1),schema_version INTEGER NOT NULL,active_generation INTEGER,next_generation INTEGER NOT NULL DEFAULT 1,updated_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS dispatchers(generation INTEGER PRIMARY KEY,dispatcher_id TEXT NOT NULL,instance_token_hash TEXT NOT NULL UNIQUE,state TEXT NOT NULL CHECK(state IN ('REGISTERED','ACTIVE','DRAINING','RETIRED','LOST')),registered_at INTEGER NOT NULL,activated_at INTEGER,heartbeat_at INTEGER,drain_deadline INTEGER,retired_at INTEGER);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_dispatcher ON dispatchers(state) WHERE state='ACTIVE';
CREATE TABLE IF NOT EXISTS jobs(job_id TEXT PRIMARY KEY,idempotency_key TEXT NOT NULL UNIQUE,lane TEXT NOT NULL,payload_json TEXT NOT NULL,payload_sha256 TEXT NOT NULL,argv_json TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN ('READY','RUNNING','RETRY_WAIT','SUCCEEDED','WAITING_EVIDENCE','FAILED_TERMINAL','CANCELLED')),priority INTEGER NOT NULL DEFAULT 0,available_at INTEGER NOT NULL,attempt_count INTEGER NOT NULL DEFAULT 0,max_attempts INTEGER NOT NULL DEFAULT 3,retry_safe INTEGER NOT NULL CHECK(retry_safe IN (0,1)),lease_token INTEGER NOT NULL DEFAULT 0,owner_generation INTEGER,owner_worker_id TEXT,lease_until INTEGER,heartbeat_at INTEGER,version INTEGER NOT NULL DEFAULT 0,result_sha256 TEXT,last_error TEXT,created_at INTEGER NOT NULL,updated_at INTEGER NOT NULL,FOREIGN KEY(owner_generation) REFERENCES dispatchers(generation));
CREATE INDEX IF NOT EXISTS runnable_jobs ON jobs(state,available_at,priority DESC,created_at,job_id);
CREATE TABLE IF NOT EXISTS attempts(attempt_id TEXT PRIMARY KEY,job_id TEXT NOT NULL,attempt_number INTEGER NOT NULL,lease_token INTEGER NOT NULL,dispatcher_generation INTEGER NOT NULL,worker_id TEXT NOT NULL,state TEXT NOT NULL CHECK(state IN ('RUNNING','SUCCEEDED','FAILED','EXPIRED','AMBIGUOUS')),claimed_at INTEGER NOT NULL,lease_until INTEGER NOT NULL,heartbeat_at INTEGER NOT NULL,finished_at INTEGER,exit_code INTEGER,result_sha256 TEXT,error TEXT,UNIQUE(job_id,attempt_number),UNIQUE(job_id,lease_token),FOREIGN KEY(job_id) REFERENCES jobs(job_id),FOREIGN KEY(dispatcher_generation) REFERENCES dispatchers(generation));
CREATE TABLE IF NOT EXISTS receipts(receipt_id TEXT PRIMARY KEY,job_id TEXT NOT NULL UNIQUE,idempotency_key TEXT NOT NULL UNIQUE,lease_token INTEGER NOT NULL,result_sha256 TEXT NOT NULL,receipt_json TEXT NOT NULL,created_at INTEGER NOT NULL,FOREIGN KEY(job_id) REFERENCES jobs(job_id));
CREATE TABLE IF NOT EXISTS events(sequence INTEGER PRIMARY KEY AUTOINCREMENT,event_id TEXT NOT NULL UNIQUE,kind TEXT NOT NULL,job_id TEXT,dispatcher_generation INTEGER,lease_token INTEGER,payload_json TEXT NOT NULL,created_at INTEGER NOT NULL);
"""


def initialize(db: sqlite3.Connection, at: int | None = None) -> None:
    at = now_epoch() if at is None else at
    db.executescript(SCHEMA)
    db.execute("INSERT OR IGNORE INTO control(singleton,schema_version,next_generation,updated_at) VALUES(1,1,1,?)", (at,))


def event(db, kind, *, job_id=None, generation=None, lease_token=None, payload=None, at=None):
    db.execute("INSERT INTO events(event_id,kind,job_id,dispatcher_generation,lease_token,payload_json,created_at) VALUES(?,?,?,?,?,?,?)", (str(uuid.uuid4()), kind, job_id, generation, lease_token, canonical(payload or {}), now_epoch() if at is None else at))


def _identity(path: Path) -> str:
    try:
        token = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError as exc:
        raise SwarmError(f"identity file missing: {path}") from exc
    if not token:
        raise SwarmError("identity file is empty")
    return sha256(token)


def register_dispatcher(db, dispatcher_id: str, identity_file: Path, at=None) -> dict:
    at = now_epoch() if at is None else at
    token = secrets.token_urlsafe(32)
    identity_file.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(identity_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(token + "\n")
    try:
        db.execute("BEGIN IMMEDIATE")
        row = db.execute("SELECT next_generation FROM control WHERE singleton=1").fetchone()
        generation = row[0]
        db.execute("UPDATE control SET next_generation=?,updated_at=? WHERE singleton=1", (generation + 1, at))
        db.execute("INSERT INTO dispatchers(generation,dispatcher_id,instance_token_hash,state,registered_at,heartbeat_at) VALUES(?,?,?,'REGISTERED',?,?)", (generation, dispatcher_id, sha256(token), at, at))
        event(db, "dispatcher.registered", generation=generation, payload={"dispatcher_id": dispatcher_id}, at=at)
        db.commit()
        return {"generation": generation, "dispatcher_id": dispatcher_id, "state": "REGISTERED", "identity_file": str(identity_file)}
    except Exception:
        db.rollback()
        identity_file.unlink(missing_ok=True)
        raise


def _dispatcher(db, generation: int, identity_file: Path):
    row = db.execute("SELECT * FROM dispatchers WHERE generation=?", (generation,)).fetchone()
    if not row or row["instance_token_hash"] != _identity(identity_file):
        raise SwarmError("dispatcher identity mismatch")
    return row


def activate_dispatcher(db, generation: int, identity_file: Path, drain_seconds=60, at=None) -> dict:
    at = now_epoch() if at is None else at
    db.execute("BEGIN IMMEDIATE")
    try:
        target = _dispatcher(db, generation, identity_file)
        if target["state"] not in {"REGISTERED", "ACTIVE"}:
            raise SwarmError(f"dispatcher cannot activate from {target['state']}")
        current = db.execute("SELECT active_generation FROM control WHERE singleton=1").fetchone()[0]
        if current and current != generation:
            db.execute("UPDATE dispatchers SET state='DRAINING',drain_deadline=?,heartbeat_at=? WHERE generation=? AND state='ACTIVE'", (at + drain_seconds, at, current))
        db.execute("UPDATE dispatchers SET state='ACTIVE',activated_at=COALESCE(activated_at,?),heartbeat_at=?,drain_deadline=NULL WHERE generation=?", (at, at, generation))
        db.execute("UPDATE control SET active_generation=?,updated_at=? WHERE singleton=1", (generation, at))
        event(db, "dispatcher.cutover", generation=generation, payload={"from_generation": current, "to_generation": generation, "drain_deadline": at + drain_seconds if current and current != generation else None}, at=at)
        db.commit()
        return {"from_generation": current, "active_generation": generation, "draining_generation": current if current != generation else None}
    except Exception:
        db.rollback(); raise


def dispatcher_heartbeat(db, generation, identity_file, at=None):
    at = now_epoch() if at is None else at
    db.execute("BEGIN IMMEDIATE")
    try:
        row = _dispatcher(db, generation, identity_file)
        if row["state"] not in {"ACTIVE", "DRAINING"}:
            raise SwarmError(f"dispatcher is {row['state']}")
        if row["state"] == "DRAINING" and row["drain_deadline"] is not None and at >= row["drain_deadline"]:
            raise SwarmError("dispatcher drain deadline elapsed")
        db.execute("UPDATE dispatchers SET heartbeat_at=? WHERE generation=?", (at, generation)); db.commit()
        return {"generation": generation, "state": row["state"], "heartbeat_at": at}
    except Exception:
        db.rollback(); raise


def enqueue(db, key, lane, argv, payload=None, retry_safe=False, max_attempts=3, priority=0, at=None):
    at = now_epoch() if at is None else at
    if lane not in ROUTE_TOKENS:
        raise SwarmError(f"unresolved route: {lane}; configured tokens are {sorted(ROUTE_TOKENS)}")
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) and x for x in argv):
        raise SwarmError("argv must be a non-empty JSON string array")
    payload = {} if payload is None else payload
    payload_json, argv_json = canonical(payload), canonical(argv)
    digest = sha256(canonical({"lane": lane, "payload": payload, "argv": argv}))
    db.execute("BEGIN IMMEDIATE")
    try:
        old = db.execute("SELECT * FROM jobs WHERE idempotency_key=?", (key,)).fetchone()
        if old:
            if old["payload_sha256"] != digest:
                raise SwarmError("idempotency key conflicts with different job content")
            db.commit(); return dict(old)
        job_id = str(uuid.uuid4())
        db.execute("INSERT INTO jobs(job_id,idempotency_key,lane,payload_json,payload_sha256,argv_json,state,priority,available_at,max_attempts,retry_safe,created_at,updated_at) VALUES(?,?,?,?,?,?,'READY',?,?,?,?,?,?)", (job_id, key, lane, payload_json, digest, argv_json, priority, at, max_attempts, int(retry_safe), at, at))
        event(db, "job.enqueued", job_id=job_id, payload={"lane": lane, "idempotency_key": key, "payload_sha256": digest}, at=at)
        db.commit(); return dict(db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone())
    except Exception:
        db.rollback(); raise


def claim(db, generation, identity_file, worker_id, lease_seconds=60, at=None):
    at = now_epoch() if at is None else at
    db.execute("BEGIN IMMEDIATE")
    try:
        dispatcher = _dispatcher(db, generation, identity_file)
        active = db.execute("SELECT active_generation FROM control WHERE singleton=1").fetchone()[0]
        if active != generation or dispatcher["state"] != "ACTIVE":
            raise SwarmError("only the active dispatcher generation may claim new work")
        row = db.execute("SELECT * FROM jobs WHERE state IN ('READY','RETRY_WAIT') AND available_at<=? ORDER BY priority DESC,created_at,job_id LIMIT 1", (at,)).fetchone()
        if not row:
            db.commit(); return None
        token, attempt = row["lease_token"] + 1, row["attempt_count"] + 1
        lease_until = at + lease_seconds
        changed = db.execute("UPDATE jobs SET state='RUNNING',attempt_count=?,lease_token=?,owner_generation=?,owner_worker_id=?,lease_until=?,heartbeat_at=?,version=version+1,updated_at=? WHERE job_id=? AND version=? AND state IN ('READY','RETRY_WAIT')", (attempt, token, generation, worker_id, lease_until, at, at, row["job_id"], row["version"])).rowcount
        if changed != 1:
            raise SwarmError("claim compare-and-swap lost")
        db.execute("INSERT INTO attempts(attempt_id,job_id,attempt_number,lease_token,dispatcher_generation,worker_id,state,claimed_at,lease_until,heartbeat_at) VALUES(?,?,?,?,?,?,'RUNNING',?,?,?)", (str(uuid.uuid4()), row["job_id"], attempt, token, generation, worker_id, at, lease_until, at))
        event(db, "job.claimed", job_id=row["job_id"], generation=generation, lease_token=token, payload={"worker_id": worker_id, "lease_until": lease_until}, at=at)
        db.commit(); return dict(db.execute("SELECT * FROM jobs WHERE job_id=?", (row["job_id"],)).fetchone())
    except Exception:
        db.rollback(); raise


def lease_heartbeat(db, job_id, token, worker_id, lease_seconds=60, at=None):
    at = now_epoch() if at is None else at
    db.execute("BEGIN IMMEDIATE")
    try:
        job = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        if not job or job["state"] != "RUNNING" or job["lease_token"] != token or job["owner_worker_id"] != worker_id or at >= job["lease_until"]:
            raise SwarmError("worker lease is stale, expired, or mismatched")
        dispatcher = db.execute("SELECT * FROM dispatchers WHERE generation=?", (job["owner_generation"],)).fetchone()
        new_until = at + lease_seconds
        if dispatcher["state"] == "DRAINING":
            if dispatcher["drain_deadline"] is None or at >= dispatcher["drain_deadline"]:
                raise SwarmError("draining dispatcher deadline elapsed")
            new_until = min(new_until, dispatcher["drain_deadline"])
        elif dispatcher["state"] != "ACTIVE":
            raise SwarmError("owning dispatcher is not active or draining")
        db.execute("UPDATE jobs SET heartbeat_at=?,lease_until=?,updated_at=? WHERE job_id=?", (at, new_until, at, job_id))
        db.execute("UPDATE attempts SET heartbeat_at=?,lease_until=? WHERE job_id=? AND lease_token=? AND state='RUNNING'", (at, new_until, job_id, token))
        db.commit(); return {"job_id": job_id, "lease_token": token, "lease_until": new_until}
    except Exception:
        db.rollback(); raise


def complete(db, job_id, token, worker_id, result: bytes, exit_code=0, at=None):
    at = now_epoch() if at is None else at
    result_hash = sha256(result)
    db.execute("BEGIN IMMEDIATE")
    try:
        job = db.execute("SELECT * FROM jobs WHERE job_id=?", (job_id,)).fetchone()
        existing = db.execute("SELECT * FROM receipts WHERE job_id=?", (job_id,)).fetchone()
        if existing:
            if existing["result_sha256"] != result_hash:
                raise SwarmError("completed job replay has a different result")
            db.commit(); return json.loads(existing["receipt_json"])
        if not job or job["state"] != "RUNNING" or job["lease_token"] != token or job["owner_worker_id"] != worker_id or at >= job["lease_until"]:
            raise SwarmError("completion lease is stale, expired, or mismatched")
        receipt = {"schema": "home-center.local-swarm.receipt.v1", "receipt_id": str(uuid.uuid4()), "job_id": job_id, "idempotency_key": job["idempotency_key"], "lane": job["lane"], "lease_token": token, "worker_id": worker_id, "dispatcher_generation": job["owner_generation"], "exit_code": exit_code, "result_sha256": result_hash, "created_at": at, "gate_order": ["NS", "REGNET_QA", "VENICE"]}
        state = "SUCCEEDED" if exit_code == 0 else ("RETRY_WAIT" if job["retry_safe"] and job["attempt_count"] < job["max_attempts"] else "FAILED_TERMINAL")
        available = at + min(300, 2 ** min(job["attempt_count"], 8)) if state == "RETRY_WAIT" else job["available_at"]
        db.execute("UPDATE jobs SET state=?,available_at=?,result_sha256=?,last_error=?,lease_until=NULL,heartbeat_at=NULL,version=version+1,updated_at=? WHERE job_id=?", (state, available, result_hash if exit_code == 0 else None, None if exit_code == 0 else result.decode("utf-8", "replace")[-4000:], at, job_id))
        db.execute("UPDATE attempts SET state=?,finished_at=?,exit_code=?,result_sha256=?,error=? WHERE job_id=? AND lease_token=?", ("SUCCEEDED" if exit_code == 0 else "FAILED", at, exit_code, result_hash, None if exit_code == 0 else result.decode("utf-8", "replace")[-4000:], job_id, token))
        if exit_code == 0:
            db.execute("INSERT INTO receipts(receipt_id,job_id,idempotency_key,lease_token,result_sha256,receipt_json,created_at) VALUES(?,?,?,?,?,?,?)", (receipt["receipt_id"], job_id, job["idempotency_key"], token, result_hash, canonical(receipt), at))
        event(db, "job.completed" if exit_code == 0 else "job.failed", job_id=job_id, generation=job["owner_generation"], lease_token=token, payload={"state": state, "result_sha256": result_hash, "exit_code": exit_code}, at=at)
        db.commit(); return receipt | {"state": state}
    except Exception:
        db.rollback(); raise


def recover(db, at=None):
    at = now_epoch() if at is None else at
    recovered = []
    db.execute("BEGIN IMMEDIATE")
    try:
        for job in db.execute("SELECT * FROM jobs WHERE state='RUNNING' AND lease_until<=? ORDER BY created_at,job_id", (at,)).fetchall():
            if job["retry_safe"] and job["attempt_count"] < job["max_attempts"]:
                state, attempt_state, available = "RETRY_WAIT", "EXPIRED", at + min(300, 2 ** min(job["attempt_count"], 8))
            elif job["retry_safe"]:
                state, attempt_state, available = "FAILED_TERMINAL", "EXPIRED", job["available_at"]
            else:
                state, attempt_state, available = "WAITING_EVIDENCE", "AMBIGUOUS", job["available_at"]
            db.execute("UPDATE attempts SET state=?,finished_at=?,error='lease expired' WHERE job_id=? AND lease_token=? AND state='RUNNING'", (attempt_state, at, job["job_id"], job["lease_token"]))
            db.execute("UPDATE jobs SET state=?,available_at=?,owner_generation=NULL,owner_worker_id=NULL,lease_until=NULL,heartbeat_at=NULL,last_error='lease expired',version=version+1,updated_at=? WHERE job_id=?", (state, available, at, job["job_id"]))
            event(db, "job.recovered", job_id=job["job_id"], generation=job["owner_generation"], lease_token=job["lease_token"], payload={"state": state}, at=at)
            recovered.append({"job_id": job["job_id"], "state": state})
        db.commit(); return recovered
    except Exception:
        db.rollback(); raise


def run_one(db_path, generation, identity_file, worker_id, lease_seconds=60):
    db = connect(db_path); initialize(db)
    job = claim(db, generation, identity_file, worker_id, lease_seconds)
    if not job:
        return None
    argv = json.loads(job["argv_json"])
    try:
        process = subprocess.run(argv, shell=False, capture_output=True)
        output = process.stdout + (b"\n" if process.stdout and process.stderr else b"") + process.stderr
        return complete(db, job["job_id"], job["lease_token"], worker_id, output, process.returncode)
    except OSError as exc:
        return complete(db, job["job_id"], job["lease_token"], worker_id, str(exc).encode(), 127)


def status(db):
    active = db.execute("SELECT active_generation FROM control WHERE singleton=1").fetchone()[0]
    jobs = {row["state"]: row["n"] for row in db.execute("SELECT state,COUNT(*) n FROM jobs GROUP BY state")}
    dispatchers = [dict(row) for row in db.execute("SELECT generation,dispatcher_id,state,heartbeat_at,drain_deadline FROM dispatchers ORDER BY generation")]
    return {"schema": "home-center.local-swarm.status.v1", "active_generation": active, "jobs": jobs, "dispatchers": dispatchers, "route_tokens": sorted(ROUTE_TOKENS), "ns_expansion": None, "state_owner": "sqlite"}


def main(argv=None):
    p = argparse.ArgumentParser(prog="swarm"); p.add_argument("--db", type=Path, default=DEFAULT_DB); p.add_argument("--json", action="store_true")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    r=sub.add_parser("dispatcher-register"); r.add_argument("--id", required=True); r.add_argument("--identity-file", type=Path, required=True)
    a=sub.add_parser("dispatcher-activate"); a.add_argument("--generation", type=int, required=True); a.add_argument("--identity-file", type=Path, required=True); a.add_argument("--drain-seconds", type=int, default=60)
    h=sub.add_parser("dispatcher-heartbeat"); h.add_argument("--generation", type=int, required=True); h.add_argument("--identity-file", type=Path, required=True)
    e=sub.add_parser("enqueue"); e.add_argument("--key", required=True); e.add_argument("--lane", required=True); e.add_argument("--argv-json", required=True); e.add_argument("--payload-json", default="{}"); e.add_argument("--retry-safe", action="store_true"); e.add_argument("--max-attempts", type=int, default=3); e.add_argument("--priority", type=int, default=0)
    c=sub.add_parser("claim"); c.add_argument("--generation", type=int, required=True); c.add_argument("--identity-file", type=Path, required=True); c.add_argument("--worker", required=True); c.add_argument("--lease-seconds", type=int, default=60)
    hb=sub.add_parser("lease-heartbeat"); hb.add_argument("--job", required=True); hb.add_argument("--lease-token", type=int, required=True); hb.add_argument("--worker", required=True); hb.add_argument("--lease-seconds", type=int, default=60)
    co=sub.add_parser("complete"); co.add_argument("--job", required=True); co.add_argument("--lease-token", type=int, required=True); co.add_argument("--worker", required=True); co.add_argument("--result-file", type=Path, required=True); co.add_argument("--exit-code", type=int, default=0)
    ro=sub.add_parser("run-one"); ro.add_argument("--generation", type=int, required=True); ro.add_argument("--identity-file", type=Path, required=True); ro.add_argument("--worker", default=f"{socket.gethostname()}-{os.getpid()}"); ro.add_argument("--lease-seconds", type=int, default=60)
    sub.add_parser("recover"); sub.add_parser("status")
    ev=sub.add_parser("events"); ev.add_argument("--after", type=int, default=0)
    args=p.parse_args(argv); db=connect(args.db); initialize(db)
    if args.command=="init": out={"database":str(args.db),"initialized":True}
    elif args.command=="dispatcher-register": out=register_dispatcher(db,args.id,args.identity_file)
    elif args.command=="dispatcher-activate": out=activate_dispatcher(db,args.generation,args.identity_file,args.drain_seconds)
    elif args.command=="dispatcher-heartbeat": out=dispatcher_heartbeat(db,args.generation,args.identity_file)
    elif args.command=="enqueue": out=enqueue(db,args.key,args.lane,json.loads(args.argv_json),json.loads(args.payload_json),args.retry_safe,args.max_attempts,args.priority)
    elif args.command=="claim": out=claim(db,args.generation,args.identity_file,args.worker,args.lease_seconds)
    elif args.command=="lease-heartbeat": out=lease_heartbeat(db,args.job,args.lease_token,args.worker,args.lease_seconds)
    elif args.command=="complete": out=complete(db,args.job,args.lease_token,args.worker,args.result_file.read_bytes(),args.exit_code)
    elif args.command=="run-one": out=run_one(args.db,args.generation,args.identity_file,args.worker,args.lease_seconds)
    elif args.command=="recover": out=recover(db)
    elif args.command=="status": out=status(db)
    else: out=[dict(row) for row in db.execute("SELECT * FROM events WHERE sequence>? ORDER BY sequence",(args.after,))]
    print(json.dumps(out,indent=2,sort_keys=True) if args.json else canonical(out)); return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (SwarmError, ValueError, json.JSONDecodeError) as exc:
        print(f"swarm: {exc}", file=sys.stderr); raise SystemExit(2)
