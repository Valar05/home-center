#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import base64, gzip, hashlib, json, math, subprocess, tempfile
from PIL import Image, ImageDraw
HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
W,H=58,23; FLOOR=21; TIMING={'ONES':1,'TWOS':2,'FOURS':4}

def lerp(a,b,t): return a+(b-a)*t

def qbez(a,b,bias,t):
    c=((a[0]+b[0])/2+bias[0],(a[1]+b[1])/2+bias[1]); u=1-t
    return (round(u*u*a[0]+2*u*t*c[0]+t*t*b[0]),round(u*u*a[1]+2*u*t*c[1]+t*t*b[1]))

def bridge(k,n,t):
    mode=k['bridge_to_next']['mode']; bias=k['bridge_to_next'].get('arc_bias',[0,0])
    # Causal boundary changes fail closed: decisive key owns the transition.
    if (k['support_contact'] != n['support_contact']) or mode.startswith('SNAP'):
        return json.loads(json.dumps(k))
    out=json.loads(json.dumps(k))
    out['pose_rig']={j:list(qbez(k['pose_rig'][j],n['pose_rig'][j],bias,t)) for j in k['pose_rig']}
    if k.get('object_position') is not None and n.get('object_position') is not None:
        ob=bias
        if k['support_contact']['object_custody']=='FREE': ob=[max(2,bias[0]),min(-2,bias[1]-2)]
        out['object_position']=list(qbez(k['object_position'],n['object_position'],ob,t))
    return out

def bres(g,p0,p1,ch=None):
    x0,y0=map(int,p0); x1,y1=map(int,p1); dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    if ch is None:
        if abs(x1-x0)>abs(y1-y0)*1.7: ch='-'
        elif abs(y1-y0)>abs(x1-x0)*1.7: ch='|'
        else: ch='\\' if (x1-x0)*(y1-y0)>0 else '/'
    while True:
        if 0<=x0<W and 0<=y0<H and g[y0][x0]==' ': g[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def put(g,p,ch):
    if p is None:return
    x,y=map(int,p)
    if 0<=x<W and 0<=y<H:g[y][x]=ch

def ascii_frame(k):
    g=[[' ']*W for _ in range(H)]
    for x in range(W):g[FLOOR][x]='_'
    p=k['pose_rig']; sl,sr,pel=p['shoulder_l'],p['shoulder_r'],p['pelvis']
    for a,b in [(sl,sr),(sl,pel),(sr,pel),(sl,p['hand_l']),(sr,p['hand_r']),(pel,p['knee_l']),(pel,p['knee_r']),(p['knee_l'],p['foot_l']),(p['knee_r'],p['foot_r'])]: bres(g,a,b)
    neck=((sl[0]+sr[0])//2,(sl[1]+sr[1])//2); bres(g,neck,p['head'],'|')
    put(g,p['head'],'@'); put(g,pel,'A')
    for j in ('shoulder_l','shoulder_r','hand_l','hand_r','knee_l','knee_r'): put(g,p[j],'+')
    put(g,p['foot_l'],'L');put(g,p['foot_r'],'R')
    obj=k.get('object_position'); cust=k['support_contact']['object_custody']
    if obj is not None:
        if cust=='ENVIRONMENT': bres(g,obj,(obj[0],FLOOR),'|')
        put(g,obj,'x' if cust=='A_HAND' else '*')
        if cust=='A_HAND': put(g,obj,'X')
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet(data):
    out=[]
    for k in data['keys']:
        sc=k['support_contact']; out += [f"{k['key_id']} {k['name']} | {k['timing_class']}/{k['timing_provenance']} | {sc['support_A']}:{sc['root_owner']} | {sc['object_custody']}",ascii_frame(k),'']
    return '\n'.join(out).rstrip()+'\n'

def sequence(data):
    frames=[]; scale=data['compile']['preview_time_scale']; ks=data['keys']
    for i,k in enumerate(ks):
        frames += [k]*(TIMING[k['timing_class']]*scale)
        if i<len(ks)-1:
            n=k['bridge_to_next'].get('frames',0)
            for j in range(1,n+1): frames.append(bridge(k,ks[i+1],j/(n+1)))
    return frames

def glyph(d,c,x,y,cw,ch):
    x0,y0=x+1,y+1;x1,y1=x+cw-2,y+ch-2;xm=(x0+x1)//2;ym=(y0+y1)//2
    kw=dict(fill='white',width=2)
    if c=='_':d.line((x0,y1,x1,y1),**kw)
    elif c=='-':d.line((x0,ym,x1,ym),**kw)
    elif c=='|':d.line((xm,y0,xm,y1),**kw)
    elif c=='/':d.line((x0,y1,x1,y0),**kw)
    elif c=='\\':d.line((x0,y0,x1,y1),**kw)
    elif c=='+':d.line((x0,ym,x1,ym),**kw);d.line((xm,y0,xm,y1),**kw)
    elif c in 'xX':d.line((x0,y0,x1,y1),**kw);d.line((x0,y1,x1,y0),**kw)
    elif c=='*':
        d.line((x0,ym,x1,ym),**kw);d.line((xm,y0,xm,y1),**kw);d.line((x0+1,y0+1,x1-1,y1-1),**kw);d.line((x0+1,y1-1,x1-1,y0+1),**kw)
    elif c=='@':d.ellipse((x0,y0,x1,y1),outline='white',width=2);d.ellipse((xm-1,ym-1,xm+1,ym+1),fill='white')
    elif c=='A':d.line((x0,y1,xm,y0),**kw);d.line((xm,y0,x1,y1),**kw);d.line((x0+2,ym,x1-2,ym),**kw)
    elif c=='L':d.line((x0,y0,x0,y1),**kw);d.line((x0,y1,x1,y1),**kw)
    elif c=='R':d.line((x0,y0,x0,y1),**kw);d.line((x0,y0,x1,y0),**kw);d.line((x0,ym,x1,ym),**kw);d.line((x1,y0,x1,ym),**kw);d.line((xm,ym,x1,y1),**kw)

def raster(k,path):
    text=ascii_frame(k); im=Image.new('RGB',(928,368),'black');d=ImageDraw.Draw(im);cw,ch=16,16
    for r,line in enumerate(text.splitlines()[:H]):
        for c,chv in enumerate(line[:W]):
            if chv!=' ':glyph(d,chv,c*cw,r*ch,cw,ch)
    im.save(path)

def render(data,tmp):
    seq=sequence(data); fd=tmp/'frames';fd.mkdir()
    for i,k in enumerate(seq):raster(k,fd/f'{i:04d}.png')
    mp4=tmp/'motion.mp4'
    cmd=['ffmpeg','-y','-loglevel','error','-framerate',str(data['compile']['fps']),'-i',str(fd/'%04d.png'),'-c:v','libx264','-preset','veryslow','-crf',str(data['compile']['crf']),'-vf',f"scale={data['compile']['output_width']}:{data['compile']['output_height']}:flags=neighbor",'-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1','-fflags','+bitexact','-flags:v','+bitexact',str(mp4)]
    subprocess.run(cmd,check=True)
    return mp4,seq

def page(data,sheet,raw):
    payload=json.dumps(data,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
    a=base64.b64encode(gzip.compress(sheet.encode(),compresslevel=9,mtime=0)).decode('ascii')
    j=base64.b64encode(gzip.compress(payload,compresslevel=9,mtime=0)).decode('ascii')
    v=base64.b64encode(raw).decode('ascii')
    vexpr='+'.join(repr(v[i:i+3000]) for i in range(0,len(v),3000))
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{data['experiment_id']}</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#080808;color:#eee;font-family:system-ui,sans-serif}}header{{padding:12px 16px;border-bottom:1px solid #444}}nav{{display:flex;gap:8px;padding:10px 16px;position:sticky;top:0;background:#080808}}button{{font:inherit;padding:8px 14px}}section{{display:none;padding:12px 16px}}section.active{{display:block}}pre{{margin:0;overflow:auto;white-space:pre;font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;tab-size:2;line-height:1.1}}video{{display:block;width:min(100%,900px);height:auto;background:#000;border:1px solid #444}}</style></head><body><header><strong>ASCII Kinesis V2 · CONTACT 008 · Asymmetric Custody Fork Repair</strong></header><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="ascii-pre"></pre></section><section id="json"><pre id="json-pre"></pre></section><section id="video"><video id="motion-video" controls autoplay muted loop playsinline></video></section><script>const A='{a}',J='{j}',V={vexpr};const bs=[...document.querySelectorAll('button[data-view]')],ss=[...document.querySelectorAll('section')];for(const b of bs)b.onclick=()=>{{for(const s of ss)s.classList.toggle('active',s.id===b.dataset.view)}};async function gunzip64(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip')));return await r.text()}};(async()=>{{document.getElementById('ascii-pre').textContent=await gunzip64(A);document.getElementById('json-pre').textContent=await gunzip64(J);document.getElementById('motion-video').src='data:video/mp4;base64,'+V}})();</script></body></html>'''

def main():
    data=json.loads(MOTION.read_text()); sheet=contact_sheet(data); (HERE/'contact-sheet.txt').write_text(sheet)
    with tempfile.TemporaryDirectory() as td:
        mp4,seq=render(data,Path(td)); raw=mp4.read_bytes(); (HERE/'chat-render.mp4').write_bytes(raw)
    data['compile']['video_frames_total']=len(seq); data['compile']['media_bytes']=len(raw); data['compile']['media_sha256']=hashlib.sha256(raw).hexdigest(); MOTION.write_text(json.dumps(data,sort_keys=True,separators=(',',':')))
    pg=page(data,sheet,raw); (HERE/'asymmetric-custody-fork-repair.motion.html').write_text(pg)
    print(json.dumps({'media_sha256':hashlib.sha256(raw).hexdigest(),'media_bytes':len(raw),'frames':len(seq),'motion_sha256':hashlib.sha256(MOTION.read_bytes()).hexdigest(),'sheet_sha256':hashlib.sha256((HERE/'contact-sheet.txt').read_bytes()).hexdigest(),'spa_sha256':hashlib.sha256(pg.encode()).hexdigest(),'spa_bytes':len(pg.encode())},sort_keys=True))
if __name__=='__main__':main()
