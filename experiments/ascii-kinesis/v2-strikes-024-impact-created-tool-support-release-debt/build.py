#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, json, subprocess, tempfile, hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=json.loads((ROOT/'motion.json').read_text(encoding='utf-8'))
GW=MOTION['rig']['grid']['width']; GH=MOTION['rig']['grid']['height']
W=MOTION['compile']['width']; H=MOTION['compile']['height']; FPS=MOTION['compile']['fps']
HOLDS=MOTION['compile']['timing_frames']
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
VIDEO_NAME='impact-created-tool-support-release-debt.mp4'
SPA_NAME='impact-created-tool-support-release-debt.motion.html'

def bres(a,b):
    x0,y0=a; x1,y1=b; pts=[]; dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return pts

def put(g,x,y,ch):
    if 0<=x<GW and 0<=y<GH: g[y][x]=ch

def line(g,a,b,ch):
    for x,y in bres(tuple(a),tuple(b)): put(g,x,y,ch)

def foot_symbol(state):
    return {'ACTIVE':'*','LIGHT':'.','AIR':'o','PROBE':'?'}[state]

def ascii_state(k,label=True):
    g=[[' ']*GW for _ in range(GH)]
    # ground
    for x in range(2,GW-2): put(g,x,22,'_')
    root=k['root']; head=k['head']
    neck=[round((root[0]+head[0])/2), max(root[1]-3,0)]
    line(g,root,neck,'|'); line(g,neck,head,'|'); put(g,*head,'O')
    line(g,neck,k['rear_hand'],'/'); line(g,neck,k['front_hand'],'\\')
    put(g,*k['rear_hand'],'+'); put(g,*k['front_hand'],'+')
    line(g,root,k['rear_knee'],'/'); line(g,k['rear_knee'],k['rear_foot'],'/')
    line(g,root,k['front_knee'],'\\'); line(g,k['front_knee'],k['front_foot'],'\\')
    put(g,*k['rear_knee'],'o'); put(g,*k['front_knee'],'o')
    put(g,*k['rear_foot'],foot_symbol(k['rear_foot_state']))
    put(g,*k['front_foot'],foot_symbol(k['front_foot_state']))
    put(g,*root,'@')
    # two-handed tool. Draw the handle as one authored line from rear hand to front hand to head.
    line(g,k['rear_hand'],k['front_hand'],'=')
    line(g,k['front_hand'],k['tool_head'],'=')
    put(g,*k['rear_hand'],'+'); put(g,*k['front_hand'],'+')
    th=k['tool_head']; put(g,*th,'H')
    if k['contact'] in {'TOOL_GROUND_HIT','TOOL_GROUND_PIN'}:
        if th[1]+1<GH: put(g,th[0],min(th[1]+1,22),'X')
    rows=[''.join(r).rstrip() for r in g]
    body='\n'.join(rows)
    if not label: return body
    return f"{k['key_id']} {k['name']}\n{body}"

def make_contact_sheet():
    legend=(
        "ASCII KINESIS V2 STRIKES024 - IMPACT-CREATED TOOL SUPPORT / RELEASE DEBT\n"
        "Legend: O head | @ pelvis/root | + hands | o knees | * active support | . light | ? probe | H abstract heavy-tool head | = handle | X environment contact | _ ground\n"
        "Principle: THE TOOL BECOMES A LEG AT IMPACT. THE BODY MUST STOP USING IT AS SUPPORT BEFORE THE TOOL CAN FLY AGAIN.\n"
        "Source evidence: STRIKES PASS 004 / TSR asset 2879 / Hammer Kirby — Kirby Super Star — SNES. Source art is evidence only and is not embedded.\n"
        "OBSERVED: grouped hammer-swing family + separate ground-collision branch. Source timing: UNKNOWN.\n"
        "INFERRED: every pose, support path, contact/release causality, timing class, rebound, lag, and recovery. Direction profile: STREET_FIGHTER/CAPCOM.\n"
        "Rights: independent abstract ASCII rig only; no source pixels, palette, costume, contours, layout, tracing, source choreography, audio, redistribution, or close imitation.\n\n"
    )
    chunks=[]
    for k in MOTION['keys']:
        meta=(
            f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']} | causal_role={k['causal_role']}\n"
            f"support={k['support_contact']} | contact={k['contact']} | tool_support={k['tool_support']}\n"
            f"root_note={k['motion_arc_root_note']}\n"
            f"rear_foot={k['rear_foot_state']} | front_foot={k['front_foot_state']}"
        )
        chunks.append(ascii_state(k)+"\n"+meta)
    return legend+'\n\n'.join(chunks)+'\n'

def render_frame(k,path):
    img=Image.new('RGB',(W,H),'black'); d=ImageDraw.Draw(img)
    font=ImageFont.truetype(FONT,11); small=ImageFont.truetype(FONT,10)
    d.text((10,7),f"STRIKES024 | {k['key_id']} | {k['name']}",font=small,fill='white')
    d.multiline_text((10,24),ascii_state(k,label=False),font=font,fill='white',spacing=0)
    d.text((10,H-48),f"SUPPORT: {k['support_contact']} | TOOL: {k['tool_support']} | CONTACT: {k['contact']}",font=small,fill='white')
    d.text((10,H-34),"CAUSAL CLOCK: COIL -> DROP -> PRECONTACT -> THIRD SUPPORT -> BODY OVERRUN -> FOOT HANDOFF -> TOOL RELEASE -> REBOUND",font=small,fill='white')
    d.text((10,H-20),"DEBT: tool support must be relinquished before rebound; rebound overshoots before hands/support settle at a displaced ready",font=small,fill='white')
    img.save(path)

def compile_frames():
    frames=[]
    for k in MOTION['keys']:
        frames.extend([k]*HOLDS[k['timing_class']])
    return frames

def build_video(out):
    frames=compile_frames()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,k in enumerate(frames): render_frame(k,td/f'{i:04d}.png')
        subprocess.run([
            'ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(td/'%04d.png'),
            '-c:v','libx264','-crf','34','-preset','veryslow','-pix_fmt','yuv420p','-movflags','+faststart',str(out)
        ],check=True)
    return len(frames)

def make_spa(ascii_text,motion_text,video_bytes):
    a64=base64.b64encode(gzip.compress(ascii_text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
    j64=base64.b64encode(gzip.compress(motion_text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
    v64=base64.b64encode(video_bytes).decode('ascii')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Strikes024 - Impact-Created Tool Support / Release Debt</title>
<style>body{{margin:0;background:#0b0c0f;color:#f3f3f3;font-family:ui-monospace,Menlo,Consolas,monospace}}nav{{position:sticky;top:0;background:#15171d;padding:10px;display:flex;gap:8px}}button{{font:inherit;padding:8px 14px}}main{{padding:12px}}section{{display:none}}section.active{{display:block}}pre{{white-space:pre;overflow:auto;font-variant-ligatures:none;line-height:1}}video{{max-width:100%;height:auto;background:black}}</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><main>
<section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls loop playsinline src="data:video/mp4;base64,{v64}"></video></section>
</main><script>
const ss=[...document.querySelectorAll('section')];for(const b of document.querySelectorAll('button[data-view]'))b.onclick=()=>{{ss.forEach(s=>s.classList.toggle('active',s.id===b.dataset.view));}};
async function gunzip(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip')));return r.text();}}
Promise.all([gunzip('{a64}'),gunzip('{j64}')]).then(([a,j])=>{{document.getElementById('a').textContent=a;document.getElementById('j').textContent=j;}});
</script></body></html>"""

def main():
    contact=make_contact_sheet()
    (ROOT/'contact-sheet.txt').write_text(contact,encoding='utf-8')
    video=ROOT/VIDEO_NAME
    n=build_video(video)
    motion_text=(ROOT/'motion.json').read_text(encoding='utf-8')
    (ROOT/SPA_NAME).write_text(make_spa(contact,motion_text,video.read_bytes()),encoding='utf-8')
    print(json.dumps({'frames':n,'fps':FPS,'video':str(video),'spa':str(ROOT/SPA_NAME),
                      'video_bytes':video.stat().st_size,'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest()},sort_keys=True))
if __name__=='__main__': main()
