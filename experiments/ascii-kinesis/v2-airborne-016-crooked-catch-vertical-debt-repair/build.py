#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
SPA=HERE/'crooked-catch-vertical-debt-repair.motion.html'
W,H,GROUND_Y=72,27,23
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
JOINTS=['head','neck','shoulder_l','shoulder_r','elbow_l','elbow_r','hand_l','hand_r','pelvis','knee_l','knee_r','foot_l','foot_r']
LINKS=[('head','neck'),('neck','shoulder_l'),('neck','shoulder_r'),('shoulder_l','elbow_l'),('elbow_l','hand_l'),('shoulder_r','elbow_r'),('elbow_r','hand_r'),('neck','pelvis'),('pelvis','knee_l'),('knee_l','foot_l'),('pelvis','knee_r'),('knee_r','foot_r')]

def pmap(obj):
    return dict(zip(JOINTS, [[int(n) for n in pair.split(',')] for pair in obj['pose_rig'].split(';')]))

def bres(a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): return out
        e2=2*err
        if e2>=dy: err+=dy;x0+=sx
        if e2<=dx: err+=dx;y0+=sy

def glyph(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if abs(dx)>abs(dy)*1.8:return '-'
    if abs(dy)>abs(dx)*1.8:return '|'
    return '\\' if dx*dy>0 else '/'

def render_ascii(obj,label=True):
    p=pmap(obj);g=[[' ']*W for _ in range(H)]
    def put(x,y,c,overwrite=False):
        if 0<=x<W and 0<=y<H and (overwrite or g[y][x]==' '):g[y][x]=c
    for x in range(W):g[GROUND_Y][x]='_'
    for a,b in LINKS:
        c=glyph(p[a],p[b])
        for x,y in bres(p[a],p[b])[1:-1]:put(x,y,c)
    for name,(x,y) in p.items():put(x,y,'O' if name=='head' else ('@' if name=='pelvis' else 'o'),True)
    hx,hy=p['head'];put(min(W-1,hx+2),hy,'>',True)
    sup=obj['support_contact']
    if sup in ('GROUND_BOTH','GROUND_LEFT','GROUND_LEFT_DOMINANT'):
        x,y=p['foot_l'];put(x,min(H-1,y+1),'=',True)
    if sup in ('GROUND_BOTH','GROUND_RIGHT','GROUND_RIGHT_DOMINANT'):
        x,y=p['foot_r'];put(x,min(H-1,y+1),'=',True)
    if label:
        px,py=p['pelvis']
        mark={'READY':'+','LOAD':'<','LAUNCH':'^','ASCEND':'^','APEX':'~','DESCEND':'v','PRECONTACT':'?','CONTACT':'!','LAND_COMPRESSION':'#','REBOUND':'^','OVERSHOOT':'>','SETTLE':'.','REENTRY':'+'}.get(obj['vertical_phase'],'*')
        put(max(0,px-4),py,mark,True)
    return '\n'.join(''.join(row).rstrip() for row in g)

def contact_sheet(data):
    out=[
        "ASCII KINESIS V2 AIRBORNE 016 — CROOKED-CATCH VERTICAL DEBT REPAIR",
        "COPYABLE CONTACT SHEET — ABSTRACT ASCII RIG ONLY — NO SOURCE PIXELS",
        "Legend: O head | @ pelvis/root | o joints | > facing-right | = owned ground support",
        "Principle: LANDING PAYS VERTICAL DEBT BEFORE GROUND SPEED RE-ENTERS.",
        ""
    ]
    for k in data['keys']:
        out.append(
            f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | support={k['support_contact']} | "
            f"contact={k['contact_state']} | phase={k['vertical_phase']} | role={k['causal_role']} | root={k['motion_arc_root_note']}\n"
            + render_ascii(k)
        )
    out.append("--- AUTHORED BRIDGE KEYS (GEOMETRY ONLY; DECISIVE KEYS REMAIN SEMANTIC AUTHORITY) ---")
    for b in data['bridge_keys']:
        out.append(f"{b['bridge_id']} {b['from_key']} -> {b['to_key']} | {b['timing_class']} {b['timing_provenance']} | {b['purpose']}\n"+render_ascii(b,False))
    return '\n\n'.join(out)

def sequence(data):
    bm={(b['from_key'],b['to_key']):b for b in data['bridge_keys']};out=[];ks=data['keys']
    for i,k in enumerate(ks):
        out += [render_ascii(k)]*HOLD[k['timing_class']]
        if i+1<len(ks):
            n=ks[i+1];b=bm.get((k['key_id'],n['key_id']))
            if b:
                if (k['support_contact'],k['contact_state'])!=(n['support_contact'],n['contact_state']):
                    raise RuntimeError('authored bridge crosses semantic state')
                out += [render_ascii(b,False)]*HOLD[b['timing_class']]
    return out

def mono_font(size=11):
    for c in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'):
        if Path(c).exists():return ImageFont.truetype(c,size)
    return ImageFont.load_default()

def make_media(data,dst):
    frames=sequence(data);font=mono_font(11)
    with tempfile.TemporaryDirectory(prefix='air016-') as td:
        td=Path(td)
        for i,text in enumerate(frames):
            im=Image.new('RGB',(640,360),'black');dr=ImageDraw.Draw(im)
            dr.multiline_text((7,8),text,font=font,fill='white',spacing=0)
            im.save(td/f'f-{i:04d}.png')
        subprocess.run([
            'ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(data['compile']['fps']),
            '-i',str(td/'f-%04d.png'),'-c:v','libx264','-preset','veryslow','-crf',
            str(data['compile']['encoder_crf']),'-pix_fmt','yuv420p','-movflags','+faststart',str(dst)
        ],check=True)
    return frames

def make_html(data,sheet,media):
    jt=json.dumps(data,separators=(',',':'),sort_keys=True,ensure_ascii=False)
    def pack(t):return base64.b64encode(gzip.compress(t.encode(),9,mtime=0)).decode()
    A,J,V=pack(sheet),pack(jt),base64.b64encode(media).decode()
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Crooked-Catch Vertical Debt Repair</title><style>:root{{color-scheme:dark}}body{{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}}nav{{position:sticky;top:0;display:flex;gap:8px;padding:10px;background:#181818;border-bottom:1px solid #444;z-index:1}}button{{font:inherit;padding:8px 12px}}section{{padding:12px}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1.05}}video{{display:block;max-width:100%;width:640px;height:auto;background:#000}}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="a"></pre></section><section id="json" hidden><pre id="j"></pre></section><section id="video" hidden><video id="v" controls loop playsinline></video></section><script>const A="{A}",J="{J}",V="{V}";async function gz(x){{const u=Uint8Array.from(atob(x),c=>c.charCodeAt());return new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([gz(A),gz(J)]).then(([aa,jj])=>{{a.textContent=aa;j.textContent=jj}});v.src="data:video/mp4;base64,"+V;for(const b of document.querySelectorAll("button[data-view]"))b.onclick=()=>{{for(const s of document.querySelectorAll("section"))s.hidden=s.id!==b.dataset.view}};</script></body></html>'''

def main():
    data=json.loads(MOTION.read_text(encoding='utf-8'))
    sheet=contact_sheet(data);asha=hashlib.sha256(sheet.encode()).hexdigest()
    if asha!=data['ascii_sheet_sha256']:
        raise SystemExit(f'ASCII_IDENTITY_MISMATCH expected={data["ascii_sheet_sha256"]} actual={asha}')
    with tempfile.TemporaryDirectory(prefix='air016-media-') as td:
        mp=Path(td)/data['compile']['video_file'];frames=make_media(data,mp);media=mp.read_bytes()
    msha=hashlib.sha256(media).hexdigest()
    if msha!=data['compile']['media_sha256']:
        raise SystemExit(f'MEDIA_IDENTITY_MISMATCH expected={data["compile"]["media_sha256"]} actual={msha}')
    if len(media)!=data['compile']['media_bytes'] or len(frames)!=data['compile']['video_frames_total']:
        raise SystemExit('MEDIA_FACT_MISMATCH')
    SPA.write_text(make_html(data,sheet,media),encoding='utf-8')
    print(json.dumps({'ascii_sha256':asha,'media_sha256':msha,'media_bytes':len(media),'frames':len(frames),'spa':SPA.name},sort_keys=True))
if __name__=='__main__':main()
