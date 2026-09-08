#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
MANIFEST=HERE/'manifest.json'
MP4=HERE/'gravity-earned-apex-turn.mp4'
SPA=HERE/'gravity-earned-apex-turn.motion.html'
W,H,GROUND_Y=78,34,31
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
JOINTS=['head','neck','shoulder_l','shoulder_r','elbow_l','elbow_r','hand_l','hand_r','pelvis','knee_l','knee_r','foot_l','foot_r']
LINKS=[('head','neck'),('neck','shoulder_l'),('neck','shoulder_r'),('shoulder_l','elbow_l'),('elbow_l','hand_l'),('shoulder_r','elbow_r'),('elbow_r','hand_r'),('neck','pelvis'),('pelvis','knee_l'),('knee_l','foot_l'),('pelvis','knee_r'),('knee_r','foot_r')]

def pose(obj):
    return dict(zip(JOINTS,obj['pose']))

def bres(a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;out=[]
    while True:
        out.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy;x0+=sx
        if e2<=dx: err+=dx;y0+=sy
    return out

def glyph(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if abs(dx)>abs(dy)*1.8:return '-'
    if abs(dy)>abs(dx)*1.8:return '|'
    return '\\' if dx*dy>0 else '/'

def render_ascii(obj,label=True):
    p=pose(obj);g=[[' ']*W for _ in range(H)]
    def put(x,y,c):
        if 0<=x<W and 0<=y<H:g[y][x]=c
    for a,b in LINKS:
        c=glyph(p[a],p[b])
        for x,y in bres(p[a],p[b])[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==' ':put(x,y,c)
    for name,(x,y) in p.items():
        put(x,y,'O' if name=='head' else ('@' if name=='pelvis' else 'o'))
    hx,hy=p['head'];put(hx+2,hy,'>')
    sc=obj['support_contact']
    if 'BOTH' in sc:
        for foot in ('foot_l','foot_r'):
            x,y=p[foot];put(x,min(H-1,y+1),'=')
    elif 'LEFT' in sc:
        x,y=p['foot_l'];put(x,min(H-1,y+1),'=')
    elif 'RIGHT' in sc:
        x,y=p['foot_r'];put(x,min(H-1,y+1),'=')
    for x in range(W):
        if g[GROUND_Y][x]==' ':g[GROUND_Y][x]='_'
    if label:
        px,py=p['pelvis'];ph=obj['vertical_phase']
        m='^' if ph in ('LAUNCH','RISE') else ('~' if ph in ('APEX_APPROACH','APEX') else ('v' if ph in ('DESCENT_BEGIN','DESCENT','PRECONTACT') else ('!' if ph in ('CONTACT','LAND_COMPRESSION') else '+')))
        put(max(0,px-4),py,m)
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet(d):
    chunks=[
        "ASCII KINESIS V2 — AIRBORNE 012 — GRAVITY-EARNED APEX TURN",
        "REVISES: experiments/ascii-kinesis/v2-airborne-003-apex-spacing-window/",
        "NEGATIVE_FIXTURE: experiments/ascii-kinesis/v2-airborne-003-apex-spacing-window/",
        "RIGHTS: abstract ASCII only; no source pixels. Timing is INFERRED / STREET_FIGHTER-CAPCOM.",
        ""
    ]
    for k in d['keys']:
        chunks.append(
            f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | "
            f"support={k['support_contact']} | contact={k['contact_state']} | phase={k['vertical_phase']} | force={k['force_owner']}\n"
            + render_ascii(k)
        )
    chunks.append(f"--- AUTHORED CONNECTIVE KEYS ---\n{len(d['bridge_keys'])} explicit geometry-only bridge keys are encoded in JSON. They never invent support/contact state; causal changes hard-cut at decisive keys.")
    return '\n\n'.join(chunks)

def sequence(d):
    bm={(b['from_key'],b['to_key']):b for b in d['bridge_keys']};out=[];ks=d['keys']
    for i,k in enumerate(ks):
        txt=render_ascii(k);out += [(k['key_id'],txt,'decisive')]*HOLD[k['timing_class']]
        if i+1<len(ks):
            n=ks[i+1];b=bm.get((k['key_id'],n['key_id']))
            if b and (k['support_contact'],k['contact_state'])==(n['support_contact'],n['contact_state']):
                out += [(b['bridge_id'],render_ascii(b,False),'bridge')]*HOLD[b['timing_class']]
    return out

def font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'):
        if Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def frame(text,path,label):
    im=Image.new('RGB',(720,400),'black');d=ImageDraw.Draw(im)
    d.text((12,8),'ASCII KINESIS V2 — GRAVITY-EARNED APEX TURN',font=font(10),fill='white')
    d.text((12,22),label,font=font(10),fill='white')
    d.multiline_text((8,40),text,font=font(10),fill='white',spacing=0)
    im.save(path)

def make_video(d):
    seq=sequence(d)
    with tempfile.TemporaryDirectory(prefix='air012-') as td:
        td=Path(td)
        for i,(lab,txt,kind) in enumerate(seq):
            frame(txt,td/f'f-{i:04d}.png',f'{lab} [{kind}]')
        subprocess.run([
            'ffmpeg','-hide_banner','-loglevel','error','-y',
            '-framerate',str(d['compile']['fps']),'-i',str(td/'f-%04d.png'),
            '-c:v','libx264','-preset','veryslow','-crf','38','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)
        ],check=True)
    return seq

def html_page(d,sheet,media):
    pretty=json.dumps(d,indent=2,sort_keys=True)
    video_b64=base64.b64encode(media).decode('ascii')
    ascii_gz=base64.b64encode(gzip.compress(sheet.encode(),compresslevel=9,mtime=0)).decode('ascii')
    json_gz=base64.b64encode(gzip.compress(pretty.encode(),compresslevel=9,mtime=0)).decode('ascii')
    def js_chunks(value,n=3800):
        return '[\n'+',\n'.join(json.dumps(value[i:i+n]) for i in range(0,len(value),n))+'\n]'
    V,A,J=map(js_chunks,(video_b64,ascii_gz,json_gz))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Airborne 012 — Gravity-Earned Apex Turn</title>
<style>:root{{color-scheme:dark;background:#0d0d0d;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1200px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#0d0d0d;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:86ch;line-height:1.45}}</style></head>
<body><h1>Gravity-Earned Apex Turn</h1><p class="note">Repair successor of v2-airborne-003-apex-spacing-window. Same Sonic Advance 2 whole-sheet evidence family; no source pixels embedded. Apex readability comes from authored deceleration, one velocity sign change, task/facing continuity, gravity-earned descent, and landing debt.</p>
<nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button></nav>
<section id="ascii" role="tabpanel"><pre id="ascii-pre"></pre></section>
<section id="json" role="tabpanel" hidden><pre id="json-pre"></pre></section>
<section id="video" role="tabpanel" hidden><video id="motion-video" controls loop playsinline preload="metadata"></video></section>
<script>
const V={V},A={A},J={J};
const video=document.getElementById("motion-video");video.src="data:video/mp4;base64,"+V.join("");
async function gun(parts){{const b=parts.join("");const u=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const r=new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip")));return r.text()}}
Promise.all([gun(A),gun(J)]).then(([a,j])=>{{document.getElementById("ascii-pre").textContent=a;document.getElementById("json-pre").textContent=j}});
const tabs=[...document.querySelectorAll('button[data-view]')],panels=[...document.querySelectorAll('section[role=tabpanel]')];for(const t of tabs)t.addEventListener('click',()=>{{for(const b of tabs)b.setAttribute('aria-selected',b===t?'true':'false');for(const p of panels)p.hidden=p.id!==t.dataset.view;}});
</script></body></html>'''

def main():
    d=json.loads(MOTION.read_text())
    seq=make_video(d);media=MP4.read_bytes();sha=hashlib.sha256(media).hexdigest();sheet=contact_sheet(d);sheet_sha=hashlib.sha256(sheet.encode()).hexdigest()
    d['compile'].update(media_sha256=sha,media_bytes=len(media),semantic_frames_per_loop=len(seq),video_frames_total=len(seq),video_file=MP4.name)
    d['ascii_sheet_sha256']=sheet_sha
    MOTION.write_text(json.dumps(d,sort_keys=True,separators=(',',':'))+'\n')
    m=json.loads(MANIFEST.read_text())
    m.update(media_sha256=sha,media_bytes=len(media),ascii_sheet_sha256=sheet_sha)
    m['motion_dungeon'].update(semantic_frames_per_loop=len(seq),video_frames_total=len(seq))
    MANIFEST.write_text(json.dumps(m,sort_keys=True,separators=(',',':'))+'\n')
    SPA.write_text(html_page(d,sheet,media))
    print(json.dumps({'media_sha256':sha,'media_bytes':len(media),'frames':len(seq),'ascii_sha256':sheet_sha},sort_keys=True))
if __name__=='__main__':main()
