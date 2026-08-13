#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Iterable

DEFAULT_ROOTS = [Path(r"G:\\Judgment Jars"), Path(r"G:\\JudgmentJars"), Path(r"G:\\Fortress\\Judgment Jars")]
STATE_DIR = Path(os.environ.get("FORTRESS_JAR_INDEX_STATE", str(Path.home() / ".local" / "state" / "home-center" / "desktop-jars")))
DB_PATH = Path(os.environ.get("FORTRESS_JAR_INDEX_DB", str(STATE_DIR / "judgment-jars.sqlite3")))
SNAPSHOT_PATH = Path(os.environ.get("FORTRESS_JAR_INDEX_SNAPSHOT", str(STATE_DIR / "judgment-jars.snapshot.json")))
SUPPORTED = {".md", ".txt", ".json", ".csv", ".tsv", ".xlsx", ".xlsm"}
SCHEMA = "home-center.desktop-judgment-jars.v1"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def text_from(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".md", ".txt", ".json", ".csv", ".tsv"}:
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix in {".xlsx", ".xlsm"}:
        try:
            import openpyxl
        except ImportError as exc:
            raise RuntimeError("openpyxl required for workbook Jar indexing") from exc
        wb = openpyxl.load_workbook(path, read_only=True, data_only=False)
        chunks: list[str] = []
        for ws in wb.worksheets:
            chunks.append(f"\n# SHEET {ws.title}\n")
            for row in ws.iter_rows():
                vals = []
                for cell in row:
                    if cell.value not in (None, ""):
                        vals.append(f"{cell.coordinate}={cell.value}")
                if vals:
                    chunks.append(" | ".join(vals))
        return "\n".join(chunks)
    return ""


def canonical_id(root: Path, path: Path) -> str:
    rel = path.relative_to(root).as_posix().lower()
    return hashlib.sha256((str(root).lower() + "::" + rel).encode("utf-8")).hexdigest()[:24]


def discover(roots: list[Path]) -> list[tuple[Path, Path]]:
    out: list[tuple[Path, Path]] = []
    for root in roots:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if path.is_file() and path.suffix.lower() in SUPPORTED and not path.name.startswith("~$"):
                out.append((root, path))
    return out


def connect() -> sqlite3.Connection:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.executescript("""
    PRAGMA journal_mode=WAL;
    PRAGMA synchronous=NORMAL;
    CREATE TABLE IF NOT EXISTS jars(
      id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      root TEXT NOT NULL,
      path TEXT NOT NULL UNIQUE,
      ext TEXT NOT NULL,
      mtime_ns INTEGER NOT NULL,
      size INTEGER NOT NULL,
      sha256 TEXT NOT NULL,
      text TEXT NOT NULL,
      indexed_at INTEGER NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_jars_title ON jars(title);
    CREATE INDEX IF NOT EXISTS idx_jars_sha ON jars(sha256);
    CREATE VIRTUAL TABLE IF NOT EXISTS jars_fts USING fts5(id UNINDEXED, title, path, text, tokenize='unicode61');
    """)
    return db


def upsert_one(db: sqlite3.Connection, root: Path, path: Path, force: bool = False) -> dict:
    stat = path.stat()
    row = db.execute("SELECT id,mtime_ns,size,sha256 FROM jars WHERE path=?", (str(path),)).fetchone()
    if row and not force and row[1] == stat.st_mtime_ns and row[2] == stat.st_size:
        return {"id": row[0], "path": str(path), "changed": False, "sha256": row[3]}
    body = text_from(path)
    digest = sha256_file(path)
    jid = canonical_id(root, path)
    now = int(time.time())
    db.execute("""
      INSERT INTO jars(id,title,root,path,ext,mtime_ns,size,sha256,text,indexed_at)
      VALUES(?,?,?,?,?,?,?,?,?,?)
      ON CONFLICT(path) DO UPDATE SET
        id=excluded.id,title=excluded.title,root=excluded.root,ext=excluded.ext,
        mtime_ns=excluded.mtime_ns,size=excluded.size,sha256=excluded.sha256,
        text=excluded.text,indexed_at=excluded.indexed_at
    """, (jid, path.stem, str(root), str(path), path.suffix.lower(), stat.st_mtime_ns, stat.st_size, digest, body, now))
    db.execute("DELETE FROM jars_fts WHERE id=?", (jid,))
    db.execute("INSERT INTO jars_fts(id,title,path,text) VALUES(?,?,?,?)", (jid, path.stem, str(path), body))
    return {"id": jid, "path": str(path), "changed": True, "sha256": digest}


def write_snapshot(db: sqlite3.Connection) -> dict:
    rows = [dict(zip(["id","title","root","path","ext","mtime_ns","size","sha256","indexed_at"], row)) for row in db.execute(
        "SELECT id,title,root,path,ext,mtime_ns,size,sha256,indexed_at FROM jars ORDER BY title,path"
    )]
    payload = {"schema": SCHEMA, "generatedAtEpoch": int(time.time()), "dbPath": str(DB_PATH), "count": len(rows), "jars": rows}
    tmp = SNAPSHOT_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(SNAPSHOT_PATH)
    return payload


def sync(roots: list[Path], force: bool = False) -> dict:
    db = connect()
    live = discover(roots)
    live_paths = {str(path) for _, path in live}
    changed = 0
    with db:
        for root, path in live:
            if upsert_one(db, root, path, force=force)["changed"]:
                changed += 1
        stale = [row[0] for row in db.execute("SELECT path FROM jars") if row[0] not in live_paths]
        for path in stale:
            row = db.execute("SELECT id FROM jars WHERE path=?", (path,)).fetchone()
            if row:
                db.execute("DELETE FROM jars_fts WHERE id=?", (row[0],))
            db.execute("DELETE FROM jars WHERE path=?", (path,))
        snap = write_snapshot(db)
    return {"ok": True, "roots": [str(r) for r in roots], "count": snap["count"], "changed": changed, "removed": len(stale), "dbPath": str(DB_PATH), "snapshotPath": str(SNAPSHOT_PATH)}


def resolve(db: sqlite3.Connection, key: str) -> dict | None:
    row = db.execute("SELECT id,title,root,path,ext,mtime_ns,size,sha256,indexed_at FROM jars WHERE id=? OR lower(title)=lower(?) LIMIT 1", (key, key)).fetchone()
    if not row:
        return None
    cols = ["id","title","root","path","ext","mtime_ns","size","sha256","indexed_at"]
    return dict(zip(cols, row))


def freshness(item: dict) -> tuple[bool, str]:
    path = Path(item["path"])
    if not path.is_file():
        return False, "missing"
    stat = path.stat()
    if stat.st_mtime_ns != item["mtime_ns"] or stat.st_size != item["size"]:
        return False, "stat_changed"
    digest = sha256_file(path)
    return digest == item["sha256"], "ok" if digest == item["sha256"] else "hash_changed"


def query(q: str, limit: int) -> dict:
    db = connect()
    rows = db.execute("""
      SELECT j.id,j.title,j.path,j.sha256,bm25(jars_fts) AS score
      FROM jars_fts JOIN jars j ON j.id=jars_fts.id
      WHERE jars_fts MATCH ? ORDER BY score LIMIT ?
    """, (q, limit)).fetchall()
    return {"ok": True, "query": q, "results": [dict(zip(["id","title","path","sha256","score"], row)) for row in rows]}


def get_live(key: str) -> dict:
    db = connect()
    item = resolve(db, key)
    if not item:
        raise SystemExit(f"unknown Jar: {key}")
    ok, reason = freshness(item)
    if not ok:
        root = Path(item["root"])
        with db:
            upsert_one(db, root, Path(item["path"]), force=True)
            write_snapshot(db)
        item = resolve(db, key)
        ok, reason = freshness(item)
    if not ok:
        raise SystemExit(f"Jar freshness check failed: {reason}")
    item["text"] = text_from(Path(item["path"]))
    item["freshness"] = "live_verified"
    return item


def roots_from_args(values: list[str]) -> list[Path]:
    if values:
        return [Path(v) for v in values]
    env = [x for x in os.environ.get("FORTRESS_JAR_ROOTS", "").split(os.pathsep) if x]
    return [Path(v) for v in env] if env else DEFAULT_ROOTS


def main() -> int:
    p = argparse.ArgumentParser(description="Live G-drive Judgment Jar SQLite acceleration layer")
    p.add_argument("--root", action="append", default=[])
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sync"); s.add_argument("--force", action="store_true")
    q = sub.add_parser("query"); q.add_argument("text"); q.add_argument("--limit", type=int, default=12)
    g = sub.add_parser("get"); g.add_argument("key")
    sub.add_parser("status")
    args = p.parse_args()
    roots = roots_from_args(args.root)
    if args.cmd == "sync": out = sync(roots, args.force)
    elif args.cmd == "query": out = query(args.text, args.limit)
    elif args.cmd == "get": out = get_live(args.key)
    else:
        db = connect(); count = db.execute("SELECT count(*) FROM jars").fetchone()[0]
        out = {"ok": True, "dbPath": str(DB_PATH), "snapshotPath": str(SNAPSHOT_PATH), "count": count, "roots": [str(r) for r in roots]}
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
