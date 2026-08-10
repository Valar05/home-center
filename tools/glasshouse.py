#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import queue
import shlex
import subprocess
import sys
import threading
import time
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

HOME = Path.home().resolve()
DEFAULT_WORKSPACE = Path(os.path.expanduser(os.getenv("HC_GLASSHOUSE_WORKSPACE", "~/workspace/home-center"))).resolve()
if not DEFAULT_WORKSPACE.exists():
    android_workspace = Path("/storage/emulated/0/Documents/GodotProjects/home-center")
    if android_workspace.exists():
        DEFAULT_WORKSPACE = android_workspace.resolve()
STATE_DIR = Path(os.path.expanduser(os.getenv("HC_GLASSHOUSE_STATE", "~/.local/state/home-center/glasshouse"))).resolve()
EVENTS_PATH = STATE_DIR / "events.jsonl"
STATE_PATH = STATE_DIR / "state.json"

_LOCK = threading.RLock()
_LISTENERS: list[queue.Queue] = []


def now_ms() -> int:
    return int(time.time() * 1000)


def _safe_json(value):
    json.dumps(value)
    return value


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if not EVENTS_PATH.exists():
        EVENTS_PATH.touch()
    if not STATE_PATH.exists():
        STATE_PATH.write_text(json.dumps({"focus": "timeline", "pins": [], "updatedAtMs": now_ms()}, indent=2) + "\n")


def load_state() -> dict:
    ensure_state_dir()
    try:
        return json.loads(STATE_PATH.read_text())
    except Exception:
        return {"focus": "timeline", "pins": [], "updatedAtMs": now_ms()}


def save_state(state: dict) -> None:
    ensure_state_dir()
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, STATE_PATH)


def append_event(kind: str, *, pane: str | None = None, title: str = "", text: str = "", path: str = "", data=None, focus: bool = True, source: str = "glasshouse") -> dict:
    ensure_state_dir()
    event = {
        "id": uuid.uuid4().hex,
        "ts": now_ms(),
        "kind": str(kind or "event"),
        "pane": str(pane or kind or "timeline"),
        "title": str(title or ""),
        "text": str(text or ""),
        "path": str(path or ""),
        "data": data if data is not None else {},
        "source": str(source or "glasshouse"),
    }
    with _LOCK:
        with EVENTS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
        if focus:
            state = load_state()
            state["focus"] = event["pane"]
            state["updatedAtMs"] = event["ts"]
            save_state(state)
        for listener in list(_LISTENERS):
            try:
                listener.put_nowait(event)
            except Exception:
                pass
    return event


def tail_events(limit: int = 300) -> list[dict]:
    ensure_state_dir()
    try:
        lines = EVENTS_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []
    out = []
    for line in lines[-max(1, min(limit, 2000)):]:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def allowed_roots(workspace: Path) -> tuple[Path, ...]:
    roots = [workspace.resolve(), STATE_DIR]
    for candidate in [
        Path("/storage/emulated/0/Download"),
        Path(os.path.expanduser("~/storage/downloads")),
        Path(os.path.expanduser("~/workspace")),
    ]:
        try:
            if candidate.exists():
                roots.append(candidate.resolve())
        except Exception:
            pass
    unique = []
    for root in roots:
        if root not in unique:
            unique.append(root)
    return tuple(unique)


def resolve_visible_path(value: str, workspace: Path, *, must_exist: bool = True) -> Path:
    raw = unquote(str(value or "")).strip()
    if not raw:
        raise ValueError("path is required")
    p = Path(os.path.expanduser(raw))
    if not p.is_absolute():
        p = workspace / p
    p = p.resolve()
    roots = allowed_roots(workspace)
    ok = False
    for root in roots:
        try:
            p.relative_to(root)
            ok = True
            break
        except ValueError:
            if p == root:
                ok = True
                break
    if not ok:
        raise PermissionError(f"path outside Glasshouse roots: {p}")
    if must_exist and not p.exists():
        raise FileNotFoundError(str(p))
    return p


HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Glasshouse</title>
<style>
:root{color-scheme:dark;background:#0d0f12;color:#e8edf2;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}
*{box-sizing:border-box} body{margin:0;background:#0d0f12} button,input{font:inherit}
header{position:sticky;top:0;z-index:10;display:flex;gap:.75rem;align-items:center;padding:.65rem .8rem;background:#11151bcc;border-bottom:1px solid #28303a;backdrop-filter:blur(8px)}
.brand{font-weight:700}.status{font-size:.8rem;color:#9fb0c0}.focus{margin-left:auto;color:#8bd5ff}
main{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:.6rem;padding:.6rem}
.pane{grid-column:span 6;min-height:260px;background:#11151b;border:1px solid #27313b;border-radius:10px;overflow:hidden;display:flex;flex-direction:column}
.pane[data-active="true"]{outline:2px solid #5cb8e6;border-color:#5cb8e6}.pane[data-pinned="true"] .pin{color:#ffd27a}
.pane h2{font-size:.86rem;margin:0;padding:.5rem .65rem;background:#161c23;border-bottom:1px solid #27313b;display:flex;gap:.5rem;align-items:center}
.pane h2 .spacer{flex:1}.pin{border:0;background:transparent;color:#647585;cursor:pointer}.body{padding:.65rem;overflow:auto;white-space:pre-wrap;word-break:break-word;flex:1;font-size:.82rem;line-height:1.38}
.timeline{grid-column:span 12;min-height:210px}.render img,.browser img,.phone img{max-width:100%;height:auto;display:block;margin:auto;background:#080a0c}
.event{padding:.35rem 0;border-bottom:1px solid #202833}.event:last-child{border:0}.event .meta{color:#71879a;font-size:.72rem}.event .title{color:#dbe8f2}
.terminal-form{display:flex;gap:.4rem;padding:.5rem;border-top:1px solid #27313b}.terminal-form input{flex:1;min-width:0;background:#080b0f;color:#eef;border:1px solid #33414e;border-radius:6px;padding:.45rem}.terminal-form button{background:#20303d;color:#dcebf5;border:1px solid #40576a;border-radius:6px;padding:.4rem .7rem}
.code-path,.image-path{color:#7fa6bd;font-size:.72rem;margin-bottom:.45rem}.receipt pre{margin:0}
@media(max-width:850px){.pane{grid-column:span 12;min-height:220px}}
</style>
</head>
<body>
<header><span class="brand">GLASSHOUSE</span><span class="status" id="connection">connecting…</span><span class="status" id="last"></span><span class="focus" id="focusLabel">focus: —</span></header>
<main>
<section class="pane code" data-pane="code"><h2>CODE <span class="spacer"></span><button class="pin" title="Pin pane">●</button></h2><div class="body"><div class="code-path" id="codePath">No file selected.</div><pre id="codeText"></pre></div></section>
<section class="pane terminal" data-pane="terminal"><h2>TERMINAL <span class="spacer"></span><button class="pin" title="Pin pane">●</button></h2><div class="body" id="terminalText">Waiting for commands…</div><div class="terminal-form"><input id="commandInput" aria-label="Run command" placeholder="command in Home Center workspace"><button id="runCommand" type="button">Run</button></div></section>
<section class="pane render" data-pane="render"><h2>RENDER <span class="spacer"></span><button class="pin" title="Pin pane">●</button></h2><div class="body"><div class="image-path" id="renderPath">No render selected.</div><img id="renderImage" alt="Latest render" hidden></div></section>
<section class="pane browser" data-pane="browser"><h2>BROWSER <span class="spacer"></span><button class="pin" title="Pin pane">●</button></h2><div class="body"><div class="image-path" id="browserPath">No browser observation.</div><img id="browserImage" alt="Latest browser observation" hidden><pre id="browserText"></pre></div></section>
<section class="pane phone" data-pane="phone"><h2>PHONE <span class="spacer"></span><button class="pin" title="Pin pane">●</button></h2><div class="body"><div class="image-path" id="phonePath">No phone observation.</div><img id="phoneImage" alt="Latest phone observation" hidden><pre id="phoneText"></pre></div></section>
<section class="pane receipt" data-pane="receipt"><h2>RECEIPTS <span class="spacer"></span><button class="pin" title="Pin pane">●</button></h2><div class="body"><pre id="receiptText">No receipts yet.</pre></div></section>
<section class="pane timeline" data-pane="timeline"><h2>LIVE EVENT TAPE <span class="spacer"></span><button class="pin" title="Pin pane">●</button></h2><div class="body" id="timeline"></div></section>
</main>
<script>
const panes=[...document.querySelectorAll('[data-pane]')];
const events=[]; let state={focus:'timeline',pins:[]};
const $=id=>document.getElementById(id);
function esc(v){return String(v??'')}
function imageUrl(path){return '/api/image?path='+encodeURIComponent(path)+'&t='+Date.now()}
function setFocus(name){state.focus=name;$('focusLabel').textContent='focus: '+name;for(const p of panes)p.dataset.active=(p.dataset.pane===name && !state.pins.includes(p.dataset.pane))?'true':'false';}
function setPins(){for(const p of panes)p.dataset.pinned=state.pins.includes(p.dataset.pane)?'true':'false'}
function applyEvent(e){events.push(e);if(events.length>500)events.shift();$('last').textContent=new Date(e.ts).toLocaleTimeString();if(!state.pins.includes(e.pane))setFocus(e.pane);
 if(e.pane==='terminal'){const el=$('terminalText');el.textContent+=(el.textContent?'\n':'')+(e.title?e.title+'\n':'')+esc(e.text||JSON.stringify(e.data||{},null,2));el.scrollTop=el.scrollHeight}
 if(e.pane==='code'){ $('codePath').textContent=e.path||e.title||'code'; if(e.path) fetch('/api/file?path='+encodeURIComponent(e.path)).then(r=>r.text()).then(t=>$('codeText').textContent=t).catch(()=>{$('codeText').textContent=e.text||''}); else $('codeText').textContent=e.text||'' }
 if(e.pane==='render' && e.path){$('renderPath').textContent=e.path;$('renderImage').src=imageUrl(e.path);$('renderImage').hidden=false}
 if(e.pane==='browser'){ $('browserPath').textContent=e.path||e.title||'browser'; if(e.path){$('browserImage').src=imageUrl(e.path);$('browserImage').hidden=false} $('browserText').textContent=e.text||'' }
 if(e.pane==='phone'){ $('phonePath').textContent=e.path||e.title||'phone'; if(e.path){$('phoneImage').src=imageUrl(e.path);$('phoneImage').hidden=false} $('phoneText').textContent=e.text||JSON.stringify(e.data||{},null,2) }
 if(e.pane==='receipt') $('receiptText').textContent=JSON.stringify(e.data&&Object.keys(e.data).length?e.data:e.text,null,2)
 const row=document.createElement('div');row.className='event';const meta=document.createElement('div');meta.className='meta';meta.textContent=new Date(e.ts).toLocaleTimeString()+' · '+e.source+' · '+e.pane;const title=document.createElement('div');title.className='title';title.textContent=e.title||e.kind;const text=document.createElement('div');text.textContent=(e.text||'').slice(0,500);row.append(meta,title,text);$('timeline').prepend(row);while($('timeline').children.length>120)$('timeline').lastElementChild.remove(); }
async function bootstrap(){const [sr,er]=await Promise.all([fetch('/api/state'),fetch('/api/events?limit=120')]);state=await sr.json();setPins();setFocus(state.focus||'timeline');const list=await er.json();for(const e of list.events||[])applyEvent(e);connect()}
function connect(){const es=new EventSource('/api/stream');es.onopen=()=>{$('connection').textContent='live'};es.onerror=()=>{$('connection').textContent='reconnecting…'};es.onmessage=ev=>{try{applyEvent(JSON.parse(ev.data))}catch(_){}}}
for(const p of panes){p.querySelector('.pin').addEventListener('click',async()=>{const name=p.dataset.pane;const pins=new Set(state.pins||[]);pins.has(name)?pins.delete(name):pins.add(name);state.pins=[...pins];setPins();await fetch('/api/state',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pins:state.pins})})})}
async function run(){const input=$('commandInput');const command=input.value.trim();if(!command)return;input.value='';await fetch('/api/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({command})})}
$('runCommand').addEventListener('click',run);$('commandInput').addEventListener('keydown',e=>{if(e.key==='Enter')run()});
bootstrap().catch(e=>{$('connection').textContent='failed: '+e});
</script>
</body></html>'''


class GlasshouseServer(ThreadingHTTPServer):
    daemon_threads = True
    def __init__(self, addr, handler, *, workspace: Path, allow_command: bool):
        super().__init__(addr, handler)
        self.workspace = workspace.resolve()
        self.allow_command = allow_command


class Handler(BaseHTTPRequestHandler):
    server: GlasshouseServer
    def log_message(self, fmt, *args):
        sys.stderr.write("glasshouse: " + (fmt % args) + "\n")

    def send_bytes(self, status: int, data: bytes, content_type="application/octet-stream"):
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers(); self.wfile.write(data)

    def send_json(self, status: int, payload):
        self.send_bytes(status, json.dumps(payload, ensure_ascii=False).encode(), "application/json; charset=utf-8")

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length < 0 or length > 1024 * 1024:
            raise ValueError("invalid body size")
        raw = self.rfile.read(length) if length else b"{}"
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON body must be an object")
        return value

    def do_GET(self):
        url = urlparse(self.path)
        try:
            if url.path == "/":
                self.send_bytes(200, HTML.encode(), "text/html; charset=utf-8"); return
            if url.path == "/api/state":
                self.send_json(200, load_state()); return
            if url.path == "/api/events":
                q = parse_qs(url.query); limit = int((q.get("limit") or [300])[0]); self.send_json(200, {"events": tail_events(limit)}); return
            if url.path == "/api/file":
                q = parse_qs(url.query); p = resolve_visible_path((q.get("path") or [""])[0], self.server.workspace)
                if not p.is_file(): raise FileNotFoundError(str(p))
                data = p.read_bytes()[:2_000_000]
                self.send_bytes(200, data, "text/plain; charset=utf-8"); return
            if url.path == "/api/image":
                q = parse_qs(url.query); p = resolve_visible_path((q.get("path") or [""])[0], self.server.workspace)
                if not p.is_file(): raise FileNotFoundError(str(p))
                ctype = mimetypes.guess_type(p.name)[0] or "application/octet-stream"
                if not ctype.startswith("image/"): raise ValueError("not an image")
                self.send_bytes(200, p.read_bytes(), ctype); return
            if url.path == "/api/stream":
                self.send_response(200); self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-store"); self.send_header("Connection", "keep-alive"); self.end_headers()
                q = queue.Queue(maxsize=256)
                with _LOCK: _LISTENERS.append(q)
                try:
                    self.wfile.write(b": glasshouse\n\n"); self.wfile.flush()
                    while True:
                        try: event = q.get(timeout=15); payload = json.dumps(event, ensure_ascii=False).encode(); self.wfile.write(b"data: " + payload + b"\n\n")
                        except queue.Empty: self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                except Exception: pass
                finally:
                    with _LOCK:
                        if q in _LISTENERS: _LISTENERS.remove(q)
                return
            self.send_json(404, {"ok": False, "error": "not found"})
        except Exception as exc:
            self.send_json(400, {"ok": False, "error": str(exc)})

    def do_POST(self):
        url = urlparse(self.path)
        try:
            body = self.read_json()
            if url.path == "/api/event":
                event = append_event(body.get("kind", "event"), pane=body.get("pane"), title=body.get("title", ""), text=body.get("text", ""), path=body.get("path", ""), data=body.get("data"), focus=bool(body.get("focus", True)), source=body.get("source", "api")); self.send_json(200, event); return
            if url.path == "/api/state":
                state = load_state();
                if "focus" in body: state["focus"] = str(body["focus"])
                if "pins" in body: state["pins"] = [str(x) for x in body["pins"] if isinstance(x, str)]
                state["updatedAtMs"] = now_ms(); save_state(state); self.send_json(200, state); return
            if url.path == "/api/command":
                if not self.server.allow_command: raise PermissionError("live terminal disabled; start Glasshouse with --allow-command")
                command = str(body.get("command") or "").strip()
                if not command: raise ValueError("command is required")
                threading.Thread(target=run_command, args=(command, self.server.workspace), daemon=True).start(); self.send_json(202, {"ok": True, "command": command}); return
            self.send_json(404, {"ok": False, "error": "not found"})
        except PermissionError as exc: self.send_json(403, {"ok": False, "error": str(exc)})
        except Exception as exc: self.send_json(400, {"ok": False, "error": str(exc)})


def run_command(command: str, workspace: Path):
    append_event("command", pane="terminal", title="$ " + command, text="", data={"cwd": str(workspace)}, source="human", focus=True)
    proc = subprocess.Popen(["/bin/sh", "-lc", command], cwd=str(workspace), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    lines = []
    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            lines.append(line.rstrip("\n")); append_event("terminal.output", pane="terminal", title="", text=line.rstrip("\n"), data={"pid": proc.pid}, source="terminal", focus=False)
        code = proc.wait()
    except Exception as exc:
        proc.kill(); code = 127; lines.append(str(exc))
    append_event("receipt", pane="receipt", title=f"command exit {code}", data={"command": command, "cwd": str(workspace), "exit": code, "tail": lines[-80:]}, source="terminal", focus=True)


def cmd_emit(args):
    data = {}
    if args.data:
        data = json.loads(args.data)
    event = append_event(args.kind, pane=args.pane, title=args.title, text=args.text, path=args.path, data=data, focus=not args.no_focus, source=args.source)
    print(json.dumps(event, ensure_ascii=False))


def cmd_focus(args):
    state = load_state(); state["focus"] = args.pane; state["updatedAtMs"] = now_ms(); save_state(state)
    append_event("focus", pane=args.pane, title=args.title or f"Focus: {args.pane}", focus=False, source=args.source)
    print(json.dumps(state))


def cmd_serve(args):
    ensure_state_dir(); workspace = Path(os.path.expanduser(args.workspace)).resolve()
    server = GlasshouseServer((args.host, args.port), Handler, workspace=workspace, allow_command=args.allow_command)
    append_event("system", pane="timeline", title="Glasshouse online", text=f"workspace={workspace} http://{args.host}:{args.port}", focus=False)
    print(f"Glasshouse: http://{args.host}:{args.port} workspace={workspace} command={'on' if args.allow_command else 'off'}", flush=True)
    server.serve_forever()


def main():
    parser = argparse.ArgumentParser(description="Home Center Glasshouse live workbench")
    sub = parser.add_subparsers(dest="cmd", required=True)
    serve = sub.add_parser("serve"); serve.add_argument("--host", default="127.0.0.1"); serve.add_argument("--port", type=int, default=8765); serve.add_argument("--workspace", default=str(DEFAULT_WORKSPACE)); serve.add_argument("--allow-command", action="store_true"); serve.set_defaults(func=cmd_serve)
    emit = sub.add_parser("emit"); emit.add_argument("kind"); emit.add_argument("--pane"); emit.add_argument("--title", default=""); emit.add_argument("--text", default=""); emit.add_argument("--path", default=""); emit.add_argument("--data", default=""); emit.add_argument("--source", default="adam"); emit.add_argument("--no-focus", action="store_true"); emit.set_defaults(func=cmd_emit)
    focus = sub.add_parser("focus"); focus.add_argument("pane", choices=["code","terminal","render","browser","phone","receipt","timeline"]); focus.add_argument("--title", default=""); focus.add_argument("--source", default="adam"); focus.set_defaults(func=cmd_focus)
    args = parser.parse_args(); args.func(args)


if __name__ == "__main__":
    main()
