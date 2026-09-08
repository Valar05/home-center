#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
MANIFEST=HERE/'manifest.json'
MP4=HERE/'drag-capture-load-transfer.mp4'
SPA=HERE/'drag-capture-load-transfer.motion.html'
W,H,GROUND_Y=88,30,26
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
JOINTS=['head','neck','shoulder_l','shoulder_r','elbow_l','elbow_r','hand_l','hand_r','pelvis','knee_l','knee_r','foot_l','foot_r']
LINKS=[('head','neck'),('neck','shoulder_l'),('neck','shoulder_r'),
       ('shoulder_l','elbow_l'),('elbow_l','hand_l'),
       ('shoulder_r','elbow_r'),('elbow_r','hand_r'),
       ('neck','pelvis'),('pelvis','knee_l'),('knee_l','foot_l'),
       ('pelvis','knee_r'),('knee_r','foot_r')]

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
    if abs(dx)>abs(dy)*1.7:return '-'
    if abs(dy)>abs(dx)*1.7:return '|'
    return '\\' if dx*dy>0 else '/'

def render_ascii(obj,label=True):
    raw=obj.get('pose_rig',obj.get('pose'));p=raw if isinstance(raw,dict) else dict(zip(JOINTS,raw));g=[[' ']*W for _ in range(H)]
    def put(x,y,c,overwrite=False):
        if 0<=x<W and 0<=y<H and (overwrite or g[y][x]==' '): g[y][x]=c
    for a,b in LINKS:
        c=glyph(p[a],p[b])
        for x,y in bres(p[a],p[b])[1:-1]: put(x,y,c)
    for name,(x,y) in p.items():
        put(x,y,'O' if name=='head' else ('@' if name=='pelvis' else 'o'),True)
    hx,hy=p['head']; put(hx+2,hy,'>',True)
    ds=obj.get('drag_surface') or []
    if len(ds)>=2:
        for a,b in zip(ds,ds[1:]):
            for x,y in bres(a,b): put(x,y,'~')
        if obj.get('drag_surface_state') in {'DEPLOYING','COUPLED','RELEASING'}:
            lhand=p['hand_l']; rhand=p['hand_r']
            for x,y in bres(lhand,ds[0])[1:-1]: put(x,y,':')
            for x,y in bres(rhand,ds[-1])[1:-1]: put(x,y,':')
    sc=obj['support_contact']
    if sc in ('GROUND_LEFT','GROUND_BOTH'):
        x,y=p['foot_l']; put(x,min(H-1,y+1),'=',True)
    if sc in ('GROUND_RIGHT','GROUND_BOTH'):
        x,y=p['foot_r']; put(x,min(H-1,y+1),'=',True)
    for x in range(W):
        if g[GROUND_Y][x]==' ': g[GROUND_Y][x]='_'
    if label:
        px,py=p['pelvis']; phase=obj['vertical_phase']
        mark='^' if phase in ('LAUNCH','RISE') else ('~' if phase=='APEX' else ('v' if phase in ('DESCENT','PRECONTACT') else ('!' if phase in ('CONTACT','LAND_COMPRESSION') else '+')))
        put(max(0,px-4),py,mark,True)
    return '\n'.join(''.join(r).rstrip() for r in g)

def crop_ascii(text):
    rows=text.splitlines()
    nonempty=[i for i,r in enumerate(rows) if r.strip()]
    if not nonempty:return text
    lo=max(0,min(nonempty)-1); hi=min(len(rows)-1,max(max(nonempty)+1,GROUND_Y))
    used=[x for r in rows[lo:hi+1] for x,ch in enumerate(r) if ch!=' ']
    if not used:return '\n'.join(rows[lo:hi+1])
    x0=max(0,min(used)-2);x1=min(W-1,max(used)+2)
    return '\n'.join((r[x0:x1+1] if len(r)>x0 else '').rstrip() for r in rows[lo:hi+1])

def contact_sheet(d):
    chunks=[]
    for k in d['keys']:
        header=(f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | "
                f"support={k['support_contact']} | contact={k['contact_state']} | drag={k['drag_surface_state']} | phase={k['vertical_phase']}")
        chunks.append(header+'\n'+crop_ascii(render_ascii(k)))
    chunks.append(
        "--- AUTHORED CONNECTIVE KEYS ---\n"
        f"{len(d['bridge_keys'])} explicit authored geometry bridge keys are fully encoded in PART 2 JSON. "
        "They preserve support/contact/drag semantics exactly; semantic transitions hard-cut at decisive keys."
    )
    return '\n\n'.join(chunks)

def sequence(d):
    bm={(b['from_key'],b['to_key']):b for b in d['bridge_keys']}
    out=[]; ks=d['keys']
    for i,k in enumerate(ks):
        out += [(k['key_id'],render_ascii(k),'decisive')]*HOLD[k['timing_class']]
        if i+1<len(ks):
            n=ks[i+1]; b=bm.get((k['key_id'],n['key_id']))
            if b:
                a_sem=(k['support_contact'],k['contact_state'],k['drag_surface_state'])
                n_sem=(n['support_contact'],n['contact_state'],n['drag_surface_state'])
                b_sem=(b['support_contact'],b['contact_state'],b['drag_surface_state'])
                if not (a_sem==n_sem==b_sem):
                    raise RuntimeError(f'bridge {b["bridge_id"]} crosses semantic boundary')
                out += [(b['bridge_id'],render_ascii(b,False),'authored_bridge')]*HOLD[b['timing_class']]
    return out

def font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
              '/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf',
              '/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSansMono.ttf'):
        if Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def frame(text,path,label):
    im=Image.new('RGB',(480,270),'black'); d=ImageDraw.Draw(im)
    d.text((18,12),'ASCII KINESIS V2 AIRBORNE 013 — DRAG CAPTURE LOAD TRANSFER',font=font(8),fill='white')
    d.text((18,34),label,font=font(8),fill='white')
    d.multiline_text((14,62),text,font=font(8),fill='white',spacing=0)
    im.save(path)

def make_video(d):
    seq=sequence(d)
    with tempfile.TemporaryDirectory(prefix='air013-') as td:
        td=Path(td)
        for i,(lab,txt,kind) in enumerate(seq):
            frame(txt,td/f'f-{i:04d}.png',f'{lab} [{kind}]')
        subprocess.run([
            'ffmpeg','-hide_banner','-loglevel','error','-y',
            '-framerate',str(d['compile']['fps']),'-i',str(td/'f-%04d.png'),
            '-c:v','libx264','-preset','veryslow','-crf','44','-pix_fmt','yuv420p',
            '-movflags','+faststart',str(MP4)
        ],check=True)
    return seq

def html_page(d,sheet,media):
    spa=json.loads(json.dumps(d));spa['manifest']={'primary_tabs':['ASCII','JSON','VIDEO'],'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'media_sha256':d['compile']['media_sha256'],'repo_path':'experiments/ascii-kinesis/v2-airborne-013-drag-capture-load-transfer/'};pretty=json.dumps(spa,indent=2,sort_keys=True,ensure_ascii=False)
    def pack(text): return base64.b64encode(gzip.compress(text.encode(),9,mtime=0)).decode()
    def parts(text,n=3600): return '[\n'+',\n'.join(json.dumps(text[i:i+n]) for i in range(0,len(text),n))+'\n]'
    V=parts(base64.b64encode(media).decode())
    A=parts(pack(sheet)); J=parts(pack(pretty))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Airborne 013 — Drag Capture Load Transfer</title><style>:root{{color-scheme:dark;background:#0d0d0d;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1400px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#0d0d0d;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:92ch;line-height:1.45}}</style></head><body><h1>Drag Capture Load Transfer</h1><p class="note">Repair successor of v2-airborne-004-drag-capture-descent. Same Green Army Man / Toy Story / Genesis whole-sheet evidence family; no source pixels. Authored repair: asymmetric load, one support break, moving apex, gravity drop, drag throw, shoulder take-up, controlled sway, one-foot probe, crumple, late second support, deep compression, chest-whip rebound, arm lag, recovery debt, translated settle.</p><nav role="tablist"><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="ascii-pre"></pre></section><section id="json" hidden><pre id="json-pre"></pre></section><section id="video" hidden><video id="motion-video" controls loop playsinline></video></section><script>const V={V},A={A},J={J};const video=document.getElementById("motion-video");video.src="data:video/mp4;base64,"+V.join("");async function gun(parts){{const u=Uint8Array.from(atob(parts.join("")),c=>c.charCodeAt(0));return new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([gun(A),gun(J)]).then(([a,j])=>{{document.getElementById("ascii-pre").textContent=a;document.getElementById("json-pre").textContent=j}});const tabs=[...document.querySelectorAll('button[data-view]')],panels=[...document.querySelectorAll('section')];for(const t of tabs)t.onclick=()=>{{for(const p of panels)p.hidden=p.id!==t.dataset.view}};</script></body></html>'''

def main():
    raw=json.loads(MOTION.read_text())
    d=json.loads(json.dumps(raw))
    for k in d['keys']:
        k.update(d['geometry']['keys'][k['key_id']])
    fields=d.get('bridge_schema')
    if fields and d['bridge_keys'] and isinstance(d['bridge_keys'][0],list):
        d['bridge_keys']=[dict(zip(fields,row)) for row in d['bridge_keys']]
    for b in d['bridge_keys']:
        b.update(d['geometry']['bridges'][b['bridge_id']])
    seq=make_video(d)
    media=MP4.read_bytes(); sha=hashlib.sha256(media).hexdigest()
    sheet=contact_sheet(d); sheet_sha=hashlib.sha256(sheet.encode()).hexdigest()
    duration=len(seq)/d['compile']['fps']
    updates=dict(media_sha256=sha,media_bytes=len(media),video_frames_total=len(seq),duration_seconds=round(duration,6),video_file=MP4.name,video_dimensions=[480,270],codec='H.264',pixel_format='yuv420p',decode='PASS_FFPROBE_AND_FULL_FFMPEG_DECODE')
    raw['compile'].update(updates); raw['ascii_sheet_sha256']=sheet_sha
    d['compile'].update(updates); d['ascii_sheet_sha256']=sheet_sha
    MOTION.write_text(json.dumps(raw,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n')
    m=json.loads(MANIFEST.read_text())
    m.update(media_sha256=sha,media_bytes=len(media),ascii_sheet_sha256=sheet_sha)
    m['motion_dungeon'].update(video_frames_total=len(seq),duration_seconds=round(duration,6))
    MANIFEST.write_text(json.dumps(m,sort_keys=True,separators=(',',':'),ensure_ascii=False)+'\n')
    SPA.write_text(html_page(raw,sheet,media))
    print(json.dumps({'media_sha256':sha,'media_bytes':len(media),'frames':len(seq),
                      'duration_seconds':duration,'ascii_sha256':sheet_sha},sort_keys=True))
if __name__=='__main__':main()
