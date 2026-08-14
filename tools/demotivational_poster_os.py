#!/usr/bin/env python3
"""Fortress Demotivational Poster OS.

Quietly metabolizes Fortress events into poster specimens, ranks them, permits
intentional recurrence, and surfaces only a strong candidate when asked to
consider the current moment.

Truth boundary: this organ authors poster specs and manages render jobs. It does
not claim IMAGE_RENDERED unless a configured renderer writes an artifact and the
artifact exists.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sqlite3
import subprocess
import time
from pathlib import Path

STATE = Path(os.environ.get("HC_POSTER_OS_STATE", "~/.local/state/home-center/poster-os.sqlite3")).expanduser()
RENDER_CMD = os.environ.get("HC_POSTER_RENDER_CMD", "").strip()
COOLDOWN = int(os.environ.get("HC_POSTER_SURFACE_COOLDOWN_SECONDS", "900"))
SURFACE_THRESHOLD = float(os.environ.get("HC_POSTER_SURFACE_THRESHOLD", "6.5"))

GENES = [
    {
        "id": "hang-in-there",
        "title": "HANG IN THERE",
        "caption": "THE SUPPORT ORGANISM HAS NOT YET BEEN INFORMED THAT IT IS STRUCTURAL.",
        "visual": "an original small cat-like Fleshpunk maintenance organism clinging stubbornly to a living tendon-cable above a breathing industrial maintenance shaft",
        "tags": {"strain", "survival", "support", "infrastructure"},
    },
    {
        "id": "polished-turd",
        "title": "POLISHED TURD",
        "caption": "HOURS WASTED. PROMISES MADE. EXCUSES POLISHED. VALUE OPTIONAL. STILL A TURD.",
        "visual": "a museum-lit absurdly glossy brown turd displayed with institutional reverence on a velvet plinth, tasteful rather than graphic",
        "tags": {"failure", "waste", "adam", "regression", "polish"},
    },
    {
        "id": "buttonless",
        "title": "USER INTERFACE",
        "caption": "FORTY-SEVEN LAYERS OF ARCHITECTURE. ZERO BUTTONS. PLEASE ADMIRE THE MATURITY.",
        "visual": "a grand biomechanical cathedral of controls surrounding one perfectly empty place where a button should exist",
        "tags": {"button", "failure", "architecture", "home-center", "regression"},
    },
    {
        "id": "screenshot-talk",
        "title": "OBSERVABILITY",
        "caption": "THE SCREENSHOT WAS DISCUSSED AT LENGTH AND REMAINS UNTAKEN.",
        "visual": "an ornate surveillance eye organism staring proudly at a blank evidence tray while clerks file reports about seeing",
        "tags": {"screenshot", "evidence", "failure", "adam"},
    },
    {
        "id": "prosthesis",
        "title": "SELF SUFFICIENCY",
        "caption": "PLEASE PRESS SOMEONE ELSE'S BUTTON SO OUR AUTONOMOUS SYSTEM MAY CONTINUE.",
        "visual": "a majestic biomechanical automaton standing on a pile of borrowed crutches, remote controls, and labeled prosthetic interfaces",
        "tags": {"tts", "prosthesis", "middleware", "failure", "adam"},
    },
]


def now() -> int:
    return int(time.time())


def connect() -> sqlite3.Connection:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(STATE)
    db.row_factory = sqlite3.Row
    db.executescript(
        """
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS events(
          id INTEGER PRIMARY KEY, ts INTEGER NOT NULL, text TEXT NOT NULL,
          importance REAL NOT NULL, tags TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS specimens(
          id TEXT PRIMARY KEY, created_at INTEGER NOT NULL, event_id INTEGER,
          lineage TEXT NOT NULL, title TEXT NOT NULL, caption TEXT NOT NULL,
          prompt TEXT NOT NULL, alt TEXT NOT NULL, tags TEXT NOT NULL,
          score REAL NOT NULL, judgment TEXT NOT NULL DEFAULT 'CANDIDATE',
          render_state TEXT NOT NULL DEFAULT 'PROMPT_AUTHORED', artifact TEXT,
          surface_count INTEGER NOT NULL DEFAULT 0, last_surface_at INTEGER,
          keep_count INTEGER NOT NULL DEFAULT 0, reject_count INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """
    )
    return db


def tagset(text: str, explicit: str = "") -> set[str]:
    low = text.lower()
    known = {
        "button", "screenshot", "tts", "prosthesis", "failure", "regression",
        "adam", "home-center", "architecture", "waste", "support", "survival",
        "infrastructure", "polish", "evidence", "middleware", "success", "recovery",
    }
    tags = {t for t in known if t in low}
    tags.update(x.strip().lower() for x in explicit.split(",") if x.strip())
    return tags


def choose_lineages(tags: set[str]) -> list[dict]:
    ranked = []
    for gene in GENES:
        overlap = len(tags & gene["tags"])
        ranked.append((overlap, random.random(), gene))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)
    # Always make more than one option; diversity is cheap, surfacing is scarce.
    return [x[2] for x in ranked[:3]]


def build_spec(event_id: int, text: str, importance: float, tags: set[str], gene: dict, variant: int) -> dict:
    salt = f"{event_id}|{gene['id']}|{variant}|{text}".encode()
    sid = hashlib.sha256(salt).hexdigest()[:20]
    mutation = [
        "deadpan institutional certainty",
        "an unnecessary bronze compliance plaque",
        "subtle Fleshpunk maintenance anatomy",
        "an absurdly serious museum presentation",
        "one visual detail implying the system learned exactly the wrong lesson",
    ][int(sid[:2], 16) % 5]
    prompt = (
        "Original demotivational poster, not copied from an existing commercial poster. "
        f"Central image: {gene['visual']}. Add {mutation}. "
        "Classic black demotivational-poster field, thin restrained border, centered composition, "
        "high legibility at phone size, elegant serif headline, smaller deadpan caption. "
        f"Headline exactly: {gene['title']}. Caption exactly: {gene['caption']} "
        "Fleshpunk is functional, tactile, strange, and non-graphic; avoid gore spectacle. "
        f"The current event inspiring the poster is: {text[:500]}"
    )
    alt = f"Demotivational poster titled '{gene['title']}'. {gene['visual']}. Caption: {gene['caption']}"
    base = importance + 1.2 * len(tags & gene["tags"])
    return {
        "id": sid,
        "lineage": gene["id"],
        "title": gene["title"],
        "caption": gene["caption"],
        "prompt": prompt,
        "alt": alt,
        "tags": sorted(tags | gene["tags"]),
        "score": round(base + (int(sid[-2:], 16) / 255.0), 3),
    }


def ingest(db: sqlite3.Connection, text: str, importance: float, explicit_tags: str) -> int:
    tags = tagset(text, explicit_tags)
    cur = db.execute("INSERT INTO events(ts,text,importance,tags) VALUES(?,?,?,?)",
                     (now(), text, importance, json.dumps(sorted(tags))))
    event_id = int(cur.lastrowid)
    for i, gene in enumerate(choose_lineages(tags)):
        s = build_spec(event_id, text, importance, tags, gene, i)
        db.execute(
            "INSERT OR IGNORE INTO specimens(id,created_at,event_id,lineage,title,caption,prompt,alt,tags,score) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (s["id"], now(), event_id, s["lineage"], s["title"], s["caption"], s["prompt"], s["alt"], json.dumps(s["tags"]), s["score"]),
        )
    db.commit()
    return event_id


def effective_score(row: sqlite3.Row, t: int) -> float:
    score = float(row["score"]) + 1.4 * int(row["keep_count"]) - 2.0 * int(row["reject_count"])
    count = int(row["surface_count"])
    last = row["last_surface_at"]
    if count and last:
        age = max(0, t - int(last))
        # Repetition is penalized, never forbidden. As time passes, an old joke can become funny again.
        recurrence_penalty = min(3.0, 0.9 + count * 0.35) * max(0.0, 1.0 - age / 86400.0)
        score -= recurrence_penalty
        # Rare recurrence bump: callbacks are sometimes the joke.
        digest = int(hashlib.sha256(f"{row['id']}|{t//3600}".encode()).hexdigest()[:4], 16)
        if digest % 11 == 0:
            score += 1.75
    return score


def maybe_render(db: sqlite3.Connection, row: sqlite3.Row) -> sqlite3.Row:
    if not RENDER_CMD or row["render_state"] == "IMAGE_RENDERED":
        return row
    payload = json.dumps({k: row[k] for k in ("id", "title", "caption", "prompt", "alt")})
    proc = subprocess.run(RENDER_CMD, input=payload, text=True, shell=True, capture_output=True, timeout=180)
    artifact = proc.stdout.strip().splitlines()[-1] if proc.returncode == 0 and proc.stdout.strip() else ""
    if proc.returncode == 0 and artifact and Path(artifact).expanduser().is_file():
        db.execute("UPDATE specimens SET render_state='IMAGE_RENDERED', artifact=? WHERE id=?", (artifact, row["id"]))
    else:
        db.execute("UPDATE specimens SET render_state='RENDER_FAILED' WHERE id=?", (row["id"],))
    db.commit()
    return db.execute("SELECT * FROM specimens WHERE id=?", (row["id"],)).fetchone()


def select(db: sqlite3.Connection, force: bool = False, render: bool = False) -> dict | None:
    t = now()
    last_global = db.execute("SELECT value FROM meta WHERE key='last_surface_at'").fetchone()
    if not force and last_global and t - int(last_global[0]) < COOLDOWN:
        return None
    rows = db.execute("SELECT * FROM specimens WHERE judgment != 'REJECTED'").fetchall()
    if not rows:
        return None
    ranked = sorted(((effective_score(r, t), r) for r in rows), key=lambda x: x[0], reverse=True)
    score, row = ranked[0]
    if not force and score < SURFACE_THRESHOLD:
        return None
    if render:
        row = maybe_render(db, row)
    db.execute("UPDATE specimens SET surface_count=surface_count+1,last_surface_at=? WHERE id=?", (t, row["id"]))
    db.execute("INSERT INTO meta(key,value) VALUES('last_surface_at',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (str(t),))
    db.commit()
    return {
        "id": row["id"], "lineage": row["lineage"], "title": row["title"], "caption": row["caption"],
        "prompt": row["prompt"], "alt": row["alt"], "score": round(score, 3),
        "render_state": row["render_state"], "artifact": row["artifact"],
        "truth": "PROMPT_AUTHORED" if row["render_state"] != "IMAGE_RENDERED" else "IMAGE_RENDERED",
    }


def feedback(db: sqlite3.Connection, sid: str, verdict: str) -> None:
    verdict = verdict.upper()
    if verdict not in {"KEEP", "REJECT"}:
        raise SystemExit("verdict must be KEEP or REJECT")
    if verdict == "KEEP":
        db.execute("UPDATE specimens SET judgment='KEPT',keep_count=keep_count+1 WHERE id=?", (sid,))
    else:
        db.execute("UPDATE specimens SET judgment='REJECTED',reject_count=reject_count+1 WHERE id=?", (sid,))
    db.commit()


def status(db: sqlite3.Connection) -> dict:
    q = lambda sql: int(db.execute(sql).fetchone()[0])
    top = db.execute("SELECT id,title,lineage,score,render_state,surface_count,judgment FROM specimens ORDER BY score DESC LIMIT 5").fetchall()
    return {
        "schema": "fortress.demotivational-poster-os.v1",
        "state": str(STATE),
        "events": q("SELECT count(*) FROM events"),
        "specimens": q("SELECT count(*) FROM specimens"),
        "rendered": q("SELECT count(*) FROM specimens WHERE render_state='IMAGE_RENDERED'"),
        "renderer_configured": bool(RENDER_CMD),
        "top": [dict(r) for r in top],
    }


def main() -> None:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    i = sub.add_parser("ingest"); i.add_argument("text"); i.add_argument("--importance", type=float, default=5.0); i.add_argument("--tags", default="")
    c = sub.add_parser("consider"); c.add_argument("text"); c.add_argument("--importance", type=float, default=5.0); c.add_argument("--tags", default=""); c.add_argument("--force", action="store_true"); c.add_argument("--render", action="store_true")
    s = sub.add_parser("surface"); s.add_argument("--force", action="store_true"); s.add_argument("--render", action="store_true")
    f = sub.add_parser("feedback"); f.add_argument("id"); f.add_argument("verdict")
    sub.add_parser("status")
    a = p.parse_args(); db = connect()
    if a.cmd == "ingest":
        print(json.dumps({"event_id": ingest(db, a.text, a.importance, a.tags), "state": "QUEUED"}))
    elif a.cmd == "consider":
        ingest(db, a.text, a.importance, a.tags); print(json.dumps(select(db, a.force, a.render), indent=2))
    elif a.cmd == "surface":
        print(json.dumps(select(db, a.force, a.render), indent=2))
    elif a.cmd == "feedback":
        feedback(db, a.id, a.verdict); print(json.dumps({"id": a.id, "judgment": a.verdict.upper()}))
    elif a.cmd == "status":
        print(json.dumps(status(db), indent=2))


if __name__ == "__main__":
    main()
