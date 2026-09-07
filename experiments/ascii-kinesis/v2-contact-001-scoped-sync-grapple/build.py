#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / 'motion.json'
OUT_MP4 = HERE / 'scoped-sync-grapple.mp4'
OUT_HTML = HERE / 'scoped-sync-grapple.motion.html'
W, H = 48, 18
HOLD = {'ONES':1,'TWOS':2,'FOURS':4}
JOINT_LINKS = [('head','shoulder_l'),('head','shoulder_r'),('shoulder_l','shoulder_r'),('shoulder_l','hand_l'),('shoulder_r','hand_r'),('shoulder_l','pelvis'),('shoulder_r','pelvis'),('pelvis','knee_l'),('pelvis','knee_r'),('knee_l','foot_l'),('knee_r','foot_r')]

def lerp(a,b,t): return [round(a[0]+(b[0]-a[0])*t), round(a[1]+(b[1]-a[1])*t)]

def bres(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    pts=[]
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy
    return pts

def line_glyph(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx) > abs(dy)*2: return '-'
    if abs(dy) > abs(dx)*2: return '|'
    return '\\' if dx*dy>0 else '/'

def render_ascii(key, override=None):
    g=[[' ']*W for _ in range(H)]
    def put(x,y,ch):
        if 0<=x<W and 0<=y<H: g[y][x]=ch
    actors={name:{j:list(v) for j,v in key[name].items()} for name in ('A','B')}
    if override: actors=override
    for name,rootch,headch in [('A','@','A'),('B','&','B')]:
        p=actors[name]
        for a,b in JOINT_LINKS:
            ga=line_glyph(p[a],p[b])
            for x,y in bres(p[a],p[b])[1:-1]:
                if g[y][x]==' ': put(x,y,ga)
        for j,(x,y) in p.items():
            put(x,y, rootch if j=='pelvis' else (headch if j=='head' else 'o'))
    for anchor in key.get('anchors',[]):
        x,y=anchor['at']; put(x,y,'*')
    if key.get('shared_center'):
        x,y=key['shared_center']; put(x,y,'X')
    if key['support_A']=='BOTH':
        for j in ('foot_l','foot_r'):
            x,y=actors['A'][j]; put(x,y+1,'=')
    if key['support_B']=='BOTH':
        for j in ('foot_l','foot_r'):
            x,y=actors['B'][j]; put(x,y+1,'=')
    if key['contact_state']!='NONE':
        for x in range(21,28): put(x,1,'>')
    lines=[''.join(r).rstrip() for r in g]
    return '\n'.join(lines)

def topology(k): return (k['contact_state'],k['support_A'],k['support_B'],k['root_owner'],k['custody'])

def connector(a,b,t=0.5):
    ov={}
    for actor in ('A','B'):
        ov[actor]={j:lerp(a[actor][j],b[actor][j],t) for j in a[actor]}
    return render_ascii(a,ov)

def contact_sheet(data):
    chunks=[]
    for k in data['keys']:
        header=f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | contact={k['contact_state']} | A_support={k['support_A']} | B_support={k['support_B']} | root={k['root_owner']}"
        chunks.append(header+'\n'+render_ascii(k))
    return '\n\n'.join(chunks)

def render_png(text: str, path: Path, label: str):
    im=Image.new('RGB',(640,360),'black'); d=ImageDraw.Draw(im); font=ImageFont.load_default(size=18)
    d.text((18,12),label,fill='white',font=font)
    d.multiline_text((18,42),text,fill='white',font=font,spacing=1)
    im.save(path)

def build_video(data):
    frames=[]
    keys=data['keys']
    semantic=[]
    for i,k in enumerate(keys):
        pose=render_ascii(k)
        for _ in range(HOLD[k['timing_class']]): semantic.append((k['key_id'],pose))
        if i+1<len(keys) and topology(k)==topology(keys[i+1]):
            semantic.append((k['key_id']+'~'+keys[i+1]['key_id'],connector(k,keys[i+1])))
    sequence=semantic*int(data['compile']['loop_repetitions'])
    with tempfile.TemporaryDirectory(prefix='ascii-kinesis-v2-') as td:
        td=Path(td)
        for n,(label,txt) in enumerate(sequence):
            p=td/f'frame-{n:04d}.png'; render_png(txt,p,label); frames.append(p)
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(data['compile']['fps']),'-i',str(td/'frame-%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','38','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT_MP4)]
        subprocess.run(cmd,check=True)
    return semantic

def html_escape(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def build_html(data, sheet, media_b64):
    pretty=json.dumps(data,indent=2,sort_keys=True)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Contact 001 — Scoped Synchronization Grapple</title>
<style>
:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1100px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:72ch;line-height:1.45}}
</style></head><body>
<h1>Scoped Synchronization Grapple</h1>
<p class="note">Copyright-safe abstract rig. Source art is evidence only and is not embedded. The performance principle is that contact phase-locks two local body clocks only at causal joins; it does not force continuous pose lockstep.</p>
<nav role="tablist" aria-label="Primary views">
<button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button>
<button type="button" role="tab" data-view="json" aria-selected="false">JSON</button>
<button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button>
</nav>
<section id="ascii" role="tabpanel"><pre>{html_escape(sheet)}</pre></section>
<section id="json" role="tabpanel" hidden><pre>{html_escape(pretty)}</pre></section>
<section id="video" role="tabpanel" hidden><video controls loop playsinline preload="metadata"><source src="data:video/mp4;base64,{media_b64}" type="video/mp4"></video><p class="note">MP4 compiled only from the abstract rig coordinates, generated ASCII frames, explicit holds, and topology-safe connectors recorded in JSON.</p></section>
<script>const tabs=[...document.querySelectorAll('button[data-view]')];const panels=[...document.querySelectorAll('section[role=tabpanel]')];for(const t of tabs)t.addEventListener('click',()=>{{for(const b of tabs)b.setAttribute('aria-selected',b===t?'true':'false');for(const p of panels)p.hidden=p.id!==t.dataset.view;}});</script>
</body></html>'''

def main():
    data=json.loads(MOTION.read_text())
    semantic=build_video(data)
    media=OUT_MP4.read_bytes(); sha=hashlib.sha256(media).hexdigest()
    data['compile']['media_sha256']=sha; data['compile']['media_bytes']=len(media); data['compile']['semantic_frames_per_loop']=len(semantic); data['compile']['video_frames_total']=len(semantic)*int(data['compile']['loop_repetitions'])
    sheet=contact_sheet(data); data['ascii_sheet_sha256']=hashlib.sha256(sheet.encode()).hexdigest()
    MOTION.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    OUT_HTML.write_text(build_html(data,sheet,base64.b64encode(media).decode('ascii')))
    print(json.dumps({'media_sha256':sha,'media_bytes':len(media),'semantic_frames_per_loop':len(semantic),'video_frames_total':data['compile']['video_frames_total'],'ascii_sheet_sha256':data['ascii_sheet_sha256']},sort_keys=True))
if __name__=='__main__': main()
