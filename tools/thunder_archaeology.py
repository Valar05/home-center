#!/usr/bin/env python3
"""Thunder Archaeology — gentle reusable-pattern miner.

Cross-platform, standard-library only. Intended for Android/Termux, Linux, macOS,
and Windows. It slowly scans mounted/local drives and optionally GitHub repos,
extracts bounded examples and reusable-pattern signals, stores a SQLite catalog,
and writes append-only JSONL receipts.

This is archaeology, not ingestion: it records provenance and small excerpts while
leaving source material in place.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

TEXT_EXTS = {
    '.gd','.gdshader','.shader','.tscn','.tres','.cfg','.ini','.py','.js','.mjs','.cjs',
    '.ts','.tsx','.jsx','.html','.css','.cs','.cpp','.cc','.c','.h','.hpp','.java','.kt',
    '.kts','.lua','.rs','.go','.rb','.sh','.ps1','.json','.toml','.yaml','.yml','.md',
    '.txt','.xml','.glsl','.wgsl','.vert','.frag','.sql','.proto','.graphql','.gradle'
}
ASSET_EXTS = {
    '.png','.jpg','.jpeg','.webp','.gif','.svg','.ase','.aseprite','.blend','.glb','.gltf',
    '.fbx','.obj','.wav','.ogg','.mp3','.flac'
}
SKIP_DIRS = {
    '.git','.hg','.svn','node_modules','.godot','.import','Library','Temp','Cache','Caches',
    '__pycache__','.venv','venv','dist','build','.gradle','.idea','.vscode'
}
SIGNALS = {
    'mechanic': [r'\bstate machine\b',r'\bcombo\b',r'\bcooldown\b',r'\bhitbox\b',r'\bhurtbox\b',r'\bpathfind',r'\bsteering\b',r'\bprocedural\b',r'\bspawn\b',r'\bquest\b',r'\bphysics\b',r'\braycast\b'],
    'animation': [r'\banimation(player|tree)?\b',r'\btween\b',r'\bblend(space|tree)?\b',r'\bskeleton\b',r'\bbone\b',r'\bik\b',r'\bmorph\b',r'\bparallax\b',r'\bkeyframe\b'],
    'art': [r'\bpalette\b',r'\bdither',r'\bpixel art\b',r'\btoon\b',r'\bcel[- ]?shad',r'\boutline\b',r'\bpost[- ]?process',r'\bcolor grade\b',r'\bmaterial\b',r'\bparticles?\b'],
    'architecture': [r'\bevent bus\b',r'\bmessage bus\b',r'\bdependency injection\b',r'\bplugin\b',r'\badapter\b',r'\bregistry\b',r'\bdispatcher\b',r'\bworker\b',r'\bqueue\b',r'\bstate store\b'],
    'data': [r'\bsqlite\b',r'\bwal\b',r'\bschema\b',r'\bmigration\b',r'\bindex\b',r'\bcache\b',r'\bserialization\b',r'\bjsonl\b'],
    'cli': [r'\bargparse\b',r'\bclick\b',r'\btyper\b',r'\bsubcommand\b',r'\bcommand parser\b',r'\bstdin\b',r'\bstdout\b'],
    'agent': [r'\bagent\b',r'\borchestrat',r'\btool call\b',r'\bprompt\b',r'\bplanner\b',r'\bmemory\b',r'\bcapability\b'],
    'reliability': [r'\bidempoten',r'\bretry\b',r'\bbackoff\b',r'\brecovery\b',r'\breceipt\b',r'\bcheckpoint\b',r'\bwatchdog\b',r'\bhealth check\b'],
    'testing': [r'\bunit test\b',r'\bintegration test\b',r'\bacceptance\b',r'\bfixture\b',r'\bmock\b',r'\bfuzz',r'\bproperty[- ]based\b'],
    'deployment': [r'\bdocker\b',r'\bcloud run\b',r'\bgithub actions\b',r'\bci/cd\b',r'\bdeploy\b',r'\bbootstrap\b',r'\bprovision\b'],
    'accessibility': [r'\baccessib',r'\balt text\b',r'\bscreen reader\b',r'\btts\b',r'\bvoice control\b',r'\bkeyboard navigation\b',r'\bsemantic\b'],
    'performance': [r'\bpooling\b',r'\bbatching\b',r'\bthrottl',r'\bdebounce\b',r'\bprofil',r'\blazy\b',r'\bstreaming\b',r'\bzero[- ]copy\b'],
    'security': [r'\bleast privilege\b',r'\boauth\b',r'\btoken\b',r'\bsandbox\b',r'\bpermission\b',r'\bsecret\b',r'\bvalidation\b']
}
RX = {k:[re.compile(p,re.I) for p in v] for k,v in SIGNALS.items()}


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def home_dir() -> Path:
    return Path(os.environ.get('THUNDER_ARCHAEOLOGY_HOME', str(Path.home()/'.thunder-archaeology'))).expanduser()


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.execute('PRAGMA journal_mode=WAL')
    con.execute('PRAGMA synchronous=NORMAL')
    con.executescript('''
    CREATE TABLE IF NOT EXISTS artifacts(
      id INTEGER PRIMARY KEY, source TEXT NOT NULL, locator TEXT NOT NULL UNIQUE,
      kind TEXT NOT NULL, ext TEXT, size INTEGER, mtime REAL, sha256 TEXT,
      title TEXT, snippet TEXT, tags TEXT, updated_at TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS idx_artifacts_tags ON artifacts(tags);
    CREATE INDEX IF NOT EXISTS idx_artifacts_title ON artifacts(title);
    CREATE TABLE IF NOT EXISTS runs(
      id INTEGER PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
      source TEXT NOT NULL, root TEXT NOT NULL, scanned INTEGER DEFAULT 0,
      changed INTEGER DEFAULT 0, errors INTEGER DEFAULT 0);
    ''')
    return con


def write_receipt(path: Path, event: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps({'ts':utcnow(), **event}, ensure_ascii=False, sort_keys=True)+'\n')


def classify(text: str) -> list[str]:
    return [name for name, regs in RX.items() if any(r.search(text) for r in regs)]


def snippet(text: str, tags: list[str], max_chars: int=2600) -> str:
    lines=text.splitlines(); hits=[]; regs=[r for t in tags for r in RX.get(t,[])]
    for i,line in enumerate(lines):
        if any(r.search(line) for r in regs):
            hits.append(i)
            if len(hits)>=5: break
    if not hits: return '\n'.join(lines[:40])[:max_chars]
    out=[]; seen=set()
    for hit in hits:
        for j in range(max(0,hit-4), min(len(lines),hit+8)):
            if j not in seen:
                seen.add(j); out.append(f'{j+1}: {lines[j]}')
    return '\n'.join(out)[:max_chars]


def upsert(con, *, source, locator, kind, ext, size, mtime, digest, title, excerpt, tags) -> bool:
    old=con.execute('SELECT sha256 FROM artifacts WHERE locator=?',(locator,)).fetchone()
    if old and old[0]==digest: return False
    con.execute('''INSERT INTO artifacts(source,locator,kind,ext,size,mtime,sha256,title,snippet,tags,updated_at)
      VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(locator) DO UPDATE SET
      source=excluded.source,kind=excluded.kind,ext=excluded.ext,size=excluded.size,
      mtime=excluded.mtime,sha256=excluded.sha256,title=excluded.title,
      snippet=excluded.snippet,tags=excluded.tags,updated_at=excluded.updated_at''',
      (source,locator,kind,ext,size,mtime,digest,title,excerpt,','.join(tags),utcnow()))
    return True


def walk(root: Path) -> Iterable[Path]:
    for cur, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.cache')]
        for name in files: yield Path(cur)/name


def scan_fs(args, con, receipts: Path) -> None:
    root=Path(args.root).expanduser().resolve(); scanned=changed=errors=0
    run=con.execute('INSERT INTO runs(started_at,source,root) VALUES(?,?,?)',(utcnow(),'filesystem',str(root))).lastrowid
    for p in walk(root):
        if args.max_files and scanned>=args.max_files: break
        ext=p.suffix.lower()
        if ext not in TEXT_EXTS and ext not in ASSET_EXTS: continue
        try:
            st=p.stat()
            if st.st_size>args.max_bytes: continue
            scanned+=1; data=p.read_bytes(); digest=hashlib.sha256(data).hexdigest(); tags=[]; excerpt=''; kind='asset'
            if ext in TEXT_EXTS:
                kind='text'; text=data.decode('utf-8',errors='replace'); tags=classify(text)
                if tags: excerpt=snippet(text,tags)
            else:
                if ext in {'.blend','.glb','.gltf','.fbx','.obj'}: tags.append('art')
                if ext in {'.gif','.ase','.aseprite'} or 'anim' in p.name.lower(): tags.append('animation')
            if upsert(con,source='filesystem',locator=str(p),kind=kind,ext=ext,size=st.st_size,mtime=st.st_mtime,digest=digest,title=p.name,excerpt=excerpt,tags=tags):
                changed+=1; con.commit(); write_receipt(receipts,{'event':'artifact-indexed','source':'filesystem','locator':str(p),'sha256':digest,'tags':tags})
        except (OSError,PermissionError) as e:
            errors+=1; write_receipt(receipts,{'event':'scan-error','source':'filesystem','locator':str(p),'error':str(e)[:500]})
        time.sleep(args.sleep)
    con.execute('UPDATE runs SET finished_at=?,scanned=?,changed=?,errors=? WHERE id=?',(utcnow(),scanned,changed,errors,run)); con.commit()
    write_receipt(receipts,{'event':'run-complete','run_id':run,'source':'filesystem','root':str(root),'scanned':scanned,'changed':changed,'errors':errors})
    print(json.dumps({'run_id':run,'source':'filesystem','root':str(root),'scanned':scanned,'changed':changed,'errors':errors}))


def gh(args:list[str], raw:bool=False):
    p=subprocess.run(['gh',*args],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    return p.stdout if raw else json.loads(p.stdout.decode())


def scan_github(args, con, receipts: Path) -> None:
    if not shutil.which('gh'): raise SystemExit('GitHub scan requires an authenticated `gh` CLI.')
    repo=args.repo; scanned=changed=errors=0
    run=con.execute('INSERT INTO runs(started_at,source,root) VALUES(?,?,?)',(utcnow(),'github',repo)).lastrowid
    try:
        meta=gh(['api',f'repos/{repo}']); branch=args.ref or meta.get('default_branch','main')
        tree=gh(['api',f'repos/{repo}/git/trees/{branch}?recursive=1'])
        for ent in tree.get('tree',[]):
            if args.max_files and scanned>=args.max_files: break
            if ent.get('type')!='blob': continue
            path=ent.get('path',''); ext=Path(path).suffix.lower(); size=int(ent.get('size') or 0)
            if ext not in TEXT_EXTS and ext not in ASSET_EXTS: continue
            if size>args.max_bytes or any(part in SKIP_DIRS for part in Path(path).parts): continue
            scanned+=1; locator=f'github://{repo}@{branch}/{path}'; digest=str(ent.get('sha') or '')
            old=con.execute('SELECT sha256 FROM artifacts WHERE locator=?',(locator,)).fetchone()
            if old and old[0]==digest: time.sleep(args.sleep); continue
            tags=[]; excerpt=''; kind='asset'
            if ext in TEXT_EXTS:
                kind='text'
                try:
                    raw=gh(['api',f'repos/{repo}/contents/{path}','-f',f'ref={branch}','-H','Accept: application/vnd.github.raw+json'],raw=True)
                    text=raw.decode('utf-8',errors='replace'); tags=classify(text)
                    if tags: excerpt=snippet(text,tags)
                except subprocess.CalledProcessError as e:
                    errors+=1; write_receipt(receipts,{'event':'scan-error','source':'github','locator':locator,'error':str(e)[:500]}); time.sleep(args.sleep); continue
            else:
                if ext in {'.blend','.glb','.gltf','.fbx','.obj'}: tags.append('art')
                if ext in {'.gif','.ase','.aseprite'}: tags.append('animation')
            if upsert(con,source='github',locator=locator,kind=kind,ext=ext,size=size,mtime=None,digest=digest,title=path,excerpt=excerpt,tags=tags):
                changed+=1; con.commit(); write_receipt(receipts,{'event':'artifact-indexed','source':'github','locator':locator,'sha256':digest,'tags':tags})
            time.sleep(args.sleep)
    except subprocess.CalledProcessError as e:
        errors+=1; write_receipt(receipts,{'event':'run-error','source':'github','root':repo,'error':str(e)[:500]})
    con.execute('UPDATE runs SET finished_at=?,scanned=?,changed=?,errors=? WHERE id=?',(utcnow(),scanned,changed,errors,run)); con.commit()
    write_receipt(receipts,{'event':'run-complete','run_id':run,'source':'github','root':repo,'scanned':scanned,'changed':changed,'errors':errors})
    print(json.dumps({'run_id':run,'source':'github','repo':repo,'scanned':scanned,'changed':changed,'errors':errors}))


def lookup(args, con) -> None:
    q=f'%{args.query.lower()}%'
    rows=con.execute('''SELECT source,locator,title,tags,snippet,updated_at FROM artifacts
      WHERE lower(title) LIKE ? OR lower(tags) LIKE ? OR lower(snippet) LIKE ? OR lower(locator) LIKE ?
      ORDER BY updated_at DESC LIMIT ?''',(q,q,q,q,args.limit)).fetchall()
    for source,locator,title,tags,excerpt,updated in rows:
        print(f'\n[{source}] {title}\n{locator}\ntags: {tags or "-"}  updated: {updated}')
        if excerpt: print(excerpt[:args.snippet_chars])


def export_json(args, con) -> None:
    cols=['source','locator','kind','ext','size','sha256','title','snippet','tags','updated_at']
    rows=con.execute('SELECT '+','.join(cols)+' FROM artifacts ORDER BY updated_at DESC').fetchall()
    out=Path(args.output); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps([dict(zip(cols,r)) for r in rows],ensure_ascii=False,indent=2),encoding='utf-8'); print(out)


def main() -> None:
    home=home_dir(); ap=argparse.ArgumentParser(description='Gentle Thunderbrainstorm archaeology crawler')
    ap.add_argument('--db',default=str(home/'catalog.sqlite3')); ap.add_argument('--receipts',default=str(home/'receipts.jsonl'))
    sub=ap.add_subparsers(dest='cmd',required=True)
    fs=sub.add_parser('scan',help='scan filesystem root / mounted drive'); fs.add_argument('root'); fs.add_argument('--sleep',type=float,default=.15); fs.add_argument('--max-files',type=int,default=0); fs.add_argument('--max-bytes',type=int,default=8*1024*1024)
    gp=sub.add_parser('github',help='scan one GitHub repo read-only using gh'); gp.add_argument('repo'); gp.add_argument('--ref'); gp.add_argument('--sleep',type=float,default=.35); gp.add_argument('--max-files',type=int,default=500); gp.add_argument('--max-bytes',type=int,default=2*1024*1024)
    lp=sub.add_parser('lookup',help='search the archaeology catalog'); lp.add_argument('query'); lp.add_argument('--limit',type=int,default=20); lp.add_argument('--snippet-chars',type=int,default=1400)
    ep=sub.add_parser('export',help='export catalog JSON for Drive/other consumers'); ep.add_argument('output')
    args=ap.parse_args(); con=connect(Path(args.db)); receipts=Path(args.receipts)
    {'scan':scan_fs,'github':scan_github,'lookup':lookup,'export':export_json}[args.cmd](args,con,receipts) if args.cmd in {'scan','github'} else ({'lookup':lookup,'export':export_json}[args.cmd](args,con))

if __name__=='__main__': main()
