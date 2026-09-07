#!/usr/bin/env python3
"""Rebuild ASCII Kinesis 001 from its committed structured motion source."""
from __future__ import annotations
import base64, hashlib, html, json, math, os, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MOTION = json.loads((ROOT / 'motion.json').read_text(encoding='utf-8'))
W = int(MOTION['scene']['width'])
H = int(MOTION['scene']['height'])
FPS = int(MOTION['timing']['fps'])
STAIRS = MOTION['scene']['stairs']
JOINTS = [(j['id'], j['parent']) for j in MOTION['rig']['joints']]
POSES = MOTION['poses']
FONT_PATH = os.environ.get('ASCII_KINESIS_MONO_FONT', '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')


def blank(): return [[' ' for _ in range(W)] for _ in range(H)]

def put(g, x, y, ch):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < W and 0 <= y < H: g[y][x] = ch

def line(g, a, b, ch=None):
    x0, y0 = int(round(a[0])), int(round(a[1])); x1, y1 = int(round(b[0])), int(round(b[1]))
    dx, dy = abs(x1-x0), -abs(y1-y0); sx = 1 if x0 < x1 else -1; sy = 1 if y0 < y1 else -1; err = dx + dy
    if ch is None:
        ddx, ddy = x1-x0, y1-y0
        ch = '-' if abs(ddx) > 2*abs(ddy) else ('|' if abs(ddy) > 2*abs(ddx) else ('\\' if ddx*ddy >= 0 else '/'))
    while True:
        put(g, x0, y0, ch)
        if x0 == x1 and y0 == y1: break
        e2 = 2*err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy

def draw_stairs(g):
    for i, s in enumerate(STAIRS):
        for x in range(int(s['x0']), int(s['x1']) + 1): put(g, x, s['y'], '_')
        if i:
            prev = STAIRS[i-1]
            for y in range(int(prev['y']) + 1, int(s['y']) + 1): put(g, s['x0'], y, '|')

def render_pose(p):
    g = blank(); draw_stairs(g); j = p['joints']
    for name, parent in JOINTS:
        if parent != 'ROOT': line(g, j[parent], j[name])
    for name, _ in JOINTS:
        x, y, _z = j[name]
        ch = '*' if name in {'l_hand','r_hand','l_foot','r_foot','head_tip'} else ('O' if name == 'head' else ('+' if name == 'pelvis' else 'o'))
        put(g, x, y, ch)
    return '\n'.join(''.join(r).rstrip() for r in g).rstrip() + '\n'

def hcat(blocks, gap='    '):
    lines = [b.splitlines() for b in blocks]; widths = [max(map(len, ls), default=0) for ls in lines]; height = max(map(len, lines), default=0)
    out=[]
    for y in range(height): out.append(gap.join((ls[y] if y < len(ls) else '').ljust(w) for ls, w in zip(lines, widths)).rstrip())
    return '\n'.join(out)

def interp(a, b, t):
    joints={}
    for name, _ in JOINTS:
        av, bv = a['joints'][name], b['joints'][name]
        joints[name] = [av[i] + (bv[i]-av[i])*t for i in range(3)]
    return {'joints': joints}

arts = [f"[{p['name']}]\n{render_pose(p).rstrip()}" for p in POSES]
rows = [hcat(arts[i:i+2]) for i in range(0, len(arts), 2)]
contact = ('\n\n' + '\n' + '='*136 + '\n\n').join(rows) + '\n'
(ROOT / 'contact-sheet.txt').write_text(contact, encoding='utf-8')

seq=[]
for i, p in enumerate(POSES):
    seq += [p] * int(p['hold_ticks'])
    if i < len(POSES)-1:
        q = POSES[i+1]
        for k in range(1, int(p['transition_ticks'])+1):
            t = k/(int(p['transition_ticks'])+1); t = 0.5 - 0.5*math.cos(math.pi*t)
            seq.append(interp(p, q, t))

frames = ROOT / '.frames'; frames.mkdir(exist_ok=True)
font = ImageFont.truetype(FONT_PATH, 22); bbox = font.getbbox('M'); cw = bbox[2]-bbox[0]; ch = 26
for idx, p in enumerate(seq):
    im = Image.new('RGB', (W*cw+40, H*ch+40), (0,0,0)); d = ImageDraw.Draw(im); y = 20
    for ln in render_pose(p).splitlines(): d.text((20,y), ln, font=font, fill=(245,245,245)); y += ch
    im.save(frames / f'{idx:04d}.png')
mp4 = ROOT / 'backward-stairs-ascii.mp4'
subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(frames/'%04d.png'),'-vf','scale=480:-2','-c:v','libx264','-pix_fmt','yuv420p','-crf','30','-preset','veryfast','-movflags','+faststart',str(mp4)], check=True)
for p in frames.glob('*.png'): p.unlink()
frames.rmdir()

uapl = (ROOT/'motion.uapl').read_text(encoding='ascii'); uat = (ROOT/'motion.uat').read_text(encoding='ascii'); manifest=(ROOT/'manifest.json').read_text(encoding='utf-8'); motion=(ROOT/'motion.json').read_text(encoding='utf-8')
video_bytes=mp4.read_bytes(); video_b64=base64.b64encode(video_bytes).decode('ascii'); vsha=hashlib.sha256(video_bytes).hexdigest(); usha=hashlib.sha256(uapl.encode('ascii')).hexdigest()
esc=lambda s: html.escape(s, quote=False)
page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"><meta name="color-scheme" content="dark"><title>ASCII Kinesis 001 — Backward Stairs / Diagonal Hip Shift</title><style>:root{{--bg:#050505;--panel:#111;--line:#333;--text:#f5f5f5;--muted:#aaa}}*{{box-sizing:border-box}}html,body{{margin:0;min-height:100%;background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,Segoe UI,sans-serif}}main{{max-width:1100px;margin:auto;min-height:100dvh;display:grid;grid-template-rows:auto auto 1fr;gap:10px;padding:12px}}header{{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}}h1{{font-size:18px;margin:0}}.meta,.note{{font-size:12px;color:var(--muted)}}nav{{display:flex;gap:8px;overflow:auto}}button{{min-height:44px;padding:8px 14px;border-radius:12px;border:1px solid var(--line);background:var(--panel);color:var(--text);font-weight:700;white-space:nowrap}}button[aria-pressed="true"]{{background:#eee;color:#111}}.view{{display:none}}.view.active{{display:block}}.stage{{border:1px solid var(--line);border-radius:14px;background:#000;min-height:60dvh;display:grid;place-items:center;overflow:hidden}}video{{max-width:100%;max-height:78dvh;background:#000}}pre{{margin:0;font:14px/1.08 ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono","Courier New",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;background:#000;color:#fafafa;padding:14px;border:1px solid var(--line);border-radius:14px;max-height:78dvh;user-select:text}}details{{border:1px solid var(--line);border-radius:12px;background:#0b0b0b;margin-bottom:10px}}summary{{min-height:44px;padding:12px;font-weight:700;cursor:pointer}}details pre{{border:0;border-radius:0;border-top:1px solid var(--line)}}</style></head><body><main data-ascii-kinesis-anthology="1" data-entry-version="1" data-uapl-sha256="{usha}" data-video-sha256="{vsha}"><header><h1>ASCII Kinesis 001 — Backward Stairs / Diagonal Hip Shift</h1><span class="meta">anthology entry v1 · backward-compatible substrate</span></header><nav><button data-view="video" aria-pressed="true">Animation</button><button data-view="contact" aria-pressed="false">ASCII contact sheet</button><button data-view="json" aria-pressed="false">Raw JSON</button><button data-view="source" aria-pressed="false">Source</button></nav><section class="view active" data-panel="video"><p class="note">Compiled from literal ASCII motion data. The scene contains only blank space, stairs, and figure characters.</p><div class="stage"><video controls autoplay muted loop playsinline src="data:video/mp4;base64,{video_b64}"></video></div></section><section class="view" data-panel="contact"><pre>{esc(contact)}</pre></section><section class="view" data-panel="json"><pre>{esc(motion)}</pre></section><section class="view" data-panel="source"><details open><summary>UAPL v1 · {usha}</summary><pre>{esc(uapl)}</pre></details><details open><summary>UAT v1</summary><pre>{esc(uat)}</pre></details><details><summary>Manifest</summary><pre>{esc(manifest)}</pre></details></section></main><script>(()=>{{const b=[...document.querySelectorAll('[data-view]')],p=[...document.querySelectorAll('[data-panel]')];b.forEach(x=>x.onclick=()=>{{b.forEach(y=>y.setAttribute('aria-pressed',String(y===x)));p.forEach(y=>y.classList.toggle('active',y.dataset.panel===x.dataset.view));}});window.__ASCII_KINESIS_ANTHOLOGY__=Object.freeze({{schema:'ascii-kinesis.anthology-entry.v1',entry:'001-backward-stairs',uaplSha256:'{usha}',videoSha256:'{vsha}',backwardCompatible:true}});window.__ASCII_KINESIS_READY__=true;}})();</script></body></html>'''
(ROOT/'backward-stairs.motion.html').write_text(page, encoding='utf-8')
print(json.dumps({'entry':'001-backward-stairs','uapl_sha256':usha,'video_sha256':vsha,'frames':len(seq),'seconds':len(seq)/FPS}, sort_keys=True))
