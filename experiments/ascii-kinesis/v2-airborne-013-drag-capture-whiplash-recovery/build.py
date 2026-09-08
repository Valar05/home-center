#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
MANIFEST=HERE/'manifest.json'
CONTACT=HERE/'contact-sheet.txt'
MP4=HERE/'drag-capture-whiplash-recovery.mp4'
SPA=HERE/'drag-capture-whiplash-recovery.motion.html'
W,H,GROUND_Y=72,27,23
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
JOINTS=['head','neck','shoulder_l','shoulder_r','elbow_l','elbow_r','hand_l','hand_r','pelvis','knee_l','knee_r','foot_l','foot_r']
LINKS=[('head','neck'),('neck','shoulder_l'),('neck','shoulder_r'),('shoulder_l','elbow_l'),('elbow_l','hand_l'),('shoulder_r','elbow_r'),('elbow_r','hand_r'),('neck','pelvis'),('pelvis','knee_l'),('knee_l','foot_l'),('pelvis','knee_r'),('knee_r','foot_r')]

def pose(obj):
    return dict(zip(JOINTS,obj['pose']))

def bres(a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): break
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
    def put(x,y,c,overwrite=False):
        if 0<=x<W and 0<=y<H and (overwrite or g[y][x]==' '): g[y][x]=c
    for x in range(W): g[GROUND_Y][x]='_'
    dp=obj.get('drag_pose')
    if dp and obj.get('drag_surface_state')!='STOWED':
        surf=dp['surface']
        for a,b in zip(surf,surf[1:]):
            for x,y in bres(a,b): put(x,y,'~',True)
        for start,end in ((surf[0],dp['tether_l']),(surf[-1],dp['tether_r'])):
            c=glyph(start,end)
            for x,y in bres(start,end)[1:]: put(x,y,c,True)
    for a,b in LINKS:
        c=glyph(p[a],p[b])
        for x,y in bres(p[a],p[b])[1:-1]: put(x,y,c)
    for name,(x,y) in p.items(): put(x,y,'O' if name=='head' else ('@' if name=='pelvis' else 'o'),True)
    hx,hy=p['head'];put(hx+2,hy,'>',True)
    sc=obj['support_contact']
    if sc in ('GROUND_BOTH','GROUND_LEFT','GROUND_LEFT_DOMINANT'):
        x,y=p['foot_l'];put(x,min(H-1,y+1),'=',True)
    if sc in ('GROUND_BOTH','GROUND_RIGHT','GROUND_RIGHT_DOMINANT'):
        x,y=p['foot_r'];put(x,min(H-1,y+1),'=',True)
    if label:
        px,py=p['pelvis'];ph=obj['vertical_phase']
        m={'READY':'+','LOAD':'<','LAUNCH':'^','RISE':'^','APEX':'~','DESCENT_BEGIN':'v','DESCENT':'v','PRECONTACT':'?','CONTACT':'!','LAND_COMPRESSION':'#','REBOUND':'^','SETTLE':'.','RECOVERY':':','RETURN':'+'}.get(ph,'*')
        put(max(0,px-4),py,m,True)
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet(d):
    chunks=['ASCII KINESIS V2 AIRBORNE 013 — DRAG-CAPTURE WHIPLASH RECOVERY','COPYABLE CONTACT SHEET — ABSTRACT RIG ONLY — NO SOURCE PIXELS','Legend: O head | @ pelvis/root | o joints | > facing | ~ drag surface | = grounded support','']
    for k in d['keys']:
        chunks.append(f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | support={k['support_contact']} | contact={k['contact_state']} | drag={k['drag_surface_state']} | phase={k['vertical_phase']}\n"+render_ascii(k))
    chunks.append('--- AUTHORED BRIDGES ---')
    for b in d['bridge_keys']:
        chunks.append(f"{b['bridge_id']} {b['from_key']} -> {b['to_key']} | {b['timing_class']} {b['timing_provenance']} | geometry-only; semantic state unchanged")
    return '\n\n'.join(chunks)

def sequence(d):
    bm={(b['from_key'],b['to_key']):b for b in d['bridge_keys']};out=[];ks=d['keys']
    for i,k in enumerate(ks):
        out += [(k['key_id'],render_ascii(k),'decisive')]*HOLD[k['timing_class']]
        if i+1<len(ks):
            n=ks[i+1];b=bm.get((k['key_id'],n['key_id']))
            if b:
                if (k['support_contact'],k['contact_state'],k['drag_surface_state'])!=(n['support_contact'],n['contact_state'],n['drag_surface_state']):
                    raise RuntimeError('bridge crosses semantic state')
                out += [(b['bridge_id'],render_ascii(b,False),'bridge')]*HOLD[b['timing_class']]
    return out

def font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'):
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def frame(text,path,label):
    im=Image.new('RGB',(640,360),'black');d=ImageDraw.Draw(im)
    d.text((10,7),'ASCII KINESIS V2 — AIRBORNE 013 — DRAG CAPTURE WHIPLASH RECOVERY',font=font(10),fill='white')
    d.text((10,22),label,font=font(10),fill='white')
    d.multiline_text((7,38),text,font=font(11),fill='white',spacing=0)
    im.save(path)

def make_video(d):
    seq=sequence(d)
    with tempfile.TemporaryDirectory(prefix='air013-') as td:
        td=Path(td)
        for i,(lab,txt,kind) in enumerate(seq): frame(txt,td/f'f-{i:04d}.png',f'{i:03d} {lab} [{kind}]')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),'-i',str(td/'f-%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','36','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
    return seq

def html_page(d,sheet,media):
    pretty=json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False)
    def pack(text): return base64.b64encode(gzip.compress(text.encode(),9,mtime=0)).decode()
    def parts(text,n=3600): return '[\n'+',\n'.join(json.dumps(text[i:i+n]) for i in range(0,len(text),n))+'\n]'
    V=parts(base64.b64encode(media).decode());A=parts(pack(sheet));J=parts(pack(pretty))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Airborne 013 — Drag-Capture Whiplash Recovery</title><style>:root{{color-scheme:dark;background:#0d0d0d;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1200px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#0d0d0d;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:84ch;line-height:1.45}}</style></head><body><h1>Drag-Capture Whiplash Recovery</h1><p class="note">Repair successor of v2-airborne-004-drag-capture-descent. Same Green Army Man / Toy Story Genesis whole-sheet evidence family; no source pixels. Authored performance: asymmetric coil, one support break, gravity-earned descent, drag capture jerk, pendulum damping, release drop, staggered landing catch, crush, overshoot, rebound, secondary lag, recovery debt.</p><nav role="tablist"><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="ascii-pre"></pre></section><section id="json" hidden><pre id="json-pre"></pre></section><section id="video" hidden><video id="motion-video" controls loop playsinline></video></section><script>const V={V},A={A},J={J};const video=document.getElementById("motion-video");video.src="data:video/mp4;base64,"+V.join("");async function gun(parts){{const u=Uint8Array.from(atob(parts.join("")),c=>c.charCodeAt(0));return new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([gun(A),gun(J)]).then(([a,j])=>{{document.getElementById("ascii-pre").textContent=a;document.getElementById("json-pre").textContent=j}});const tabs=[...document.querySelectorAll('button[data-view]')],panels=[...document.querySelectorAll('section')];for(const t of tabs)t.onclick=()=>{{for(const p of panels)p.hidden=p.id!==t.dataset.view}};</script></body></html>'''

def main():
    d=json.loads(MOTION.read_text())
    seq=make_video(d);media=MP4.read_bytes();sha=hashlib.sha256(media).hexdigest();sheet=contact_sheet(d);sheet_sha=hashlib.sha256(sheet.encode()).hexdigest()
    if d['compile'].get('media_sha256') and d['compile']['media_sha256']!=sha:
        raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={d['compile']['media_sha256']} actual={sha}")
    d['compile'].update(media_sha256=sha,media_bytes=len(media),semantic_frames_per_loop=len(seq),video_frames_total=len(seq),video_file=MP4.name,video_dimensions=[640,360],codec='H.264',pixel_format='yuv420p',duration_seconds=len(seq)/d['compile']['fps'],decode_verified=True)
    d['ascii_sheet_sha256']=sheet_sha
    MOTION.write_text(json.dumps(d,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n')
    CONTACT.write_text(sheet)
    m=json.loads(MANIFEST.read_text())
    if m.get('media_sha256') and m['media_sha256']!=sha:
        raise SystemExit(f"MANIFEST_MEDIA_IDENTITY_MISMATCH expected={m['media_sha256']} actual={sha}")
    m.update(media_sha256=sha,media_bytes=len(media),ascii_sheet_sha256=sheet_sha)
    m['motion_dungeon'].update(semantic_frames_per_loop=len(seq),video_frames_total=len(seq))
    MANIFEST.write_text(json.dumps(m,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n')
    SPA.write_text(html_page(d,sheet,media))
    print(json.dumps({'media_sha256':sha,'media_bytes':len(media),'frames':len(seq),'ascii_sha256':sheet_sha},sort_keys=True))
if __name__=='__main__': main()
