#!/usr/bin/env python3
"""Deterministic Motion Dungeon builder for V2 CONTACT 007 repair.
Reads motion.json; source sprite pixels are never read or rendered.
"""
from __future__ import annotations
import base64, hashlib, json, math, os, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
W,H=78,24
FLOOR=21
TIMING={'ONES':1,'TWOS':2,'FOURS':4}

def lerp(a,b,t): return a+(b-a)*t

def qbez(a,b,bias,t):
    c=((a[0]+b[0])/2+bias[0],(a[1]+b[1])/2+bias[1]); u=1-t
    return (u*u*a[0]+2*u*t*c[0]+t*t*b[0], u*u*a[1]+2*u*t*c[1]+t*t*b[1])

def interp_pose(pa,pb,t,bias=(0,0)):
    return {j:tuple(round(v) for v in qbez(pa[j],pb[j],bias,t)) for j in pa}

def bridge_state(k,nk,t):
    mode=k.get('bridge_to_next',{}).get('mode','LOCAL_ARC')
    ba=tuple(k.get('bridge_to_next',{}).get('arc_bias_A',[0,0])); bb=tuple(k.get('bridge_to_next',{}).get('arc_bias_B',[0,0]))
    st=json.loads(json.dumps(k))
    if mode=='LOCKED_POLAR':
        ca=k['shared_center']; cb=nk['shared_center']; c=(lerp(ca[0],cb[0],t),lerp(ca[1],cb[1],t))
        theta=math.radians(k['bridge_to_next'].get('rotation_degrees',0))*t
        for who in ('A','B'):
            out={}
            for j,p in k[who].items():
                rx,ry=p[0]-ca[0],p[1]-ca[1]; drx,dry=nk[who][j][0]-cb[0],nk[who][j][1]-cb[1]
                rrx,rry=lerp(rx,drx,t),lerp(ry,dry,t)
                out[j]=(round(rrx*math.cos(theta)-rry*math.sin(theta)+c[0]),round(rrx*math.sin(theta)+rry*math.cos(theta)+c[1]))
            st[who]=out
        st['shared_center']=[round(c[0]),round(c[1])]
        for idx,a in enumerate(k['anchors']):
            na=nk['anchors'][idx]
            ax,ay=round(lerp(a['at'][0],na['at'][0],t)),round(lerp(a['at'][1],na['at'][1],t))
            st['anchors'][idx]['at']=[ax,ay]
            for endpoint in (a['a'],a['b']):
                who,j=endpoint.split('.'); st[who][j]=(ax,ay)
    else:
        if mode=='FREE_SPLIT': ba=(-3,3); bb=(4,4)
        elif mode=='BALLISTIC_TO_GROUND': ba=(3,1); bb=(3,5)
        elif mode=='PRECONTACT_ARC': ba=(2,-2); bb=(-1,0)
        elif mode=='ONE_ANCHOR_PIVOT': ba=(0,1); bb=(2,-1)
        elif mode=='TRANSFER_PREP': ba=(2,-2); bb=(2,-3)
        elif mode=='LOCKED_TO_RELEASE': ba=(1,1); bb=(3,2)
        elif mode=='DEBT_SETTLE': ba=(-2,1); bb=(0,0)
        st['A']=interp_pose(k['A'],nk['A'],t,ba); st['B']=interp_pose(k['B'],nk['B'],t,bb)
        if k.get('shared_center') and nk.get('shared_center'):
            st['shared_center']=[round(lerp(k['shared_center'][0],nk['shared_center'][0],t)),round(lerp(k['shared_center'][1],nk['shared_center'][1],t))]
        for a in st.get('anchors',[]):
            who,j=a['a'].split('.'); a['at']=list(st[who][j]); other,oj=a['b'].split('.'); st[other][oj]=tuple(a['at'])
    return st

def bres(grid,p0,p1,ch=None):
    x0,y0=p0; x1,y1=p1; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    if ch is None:
        if abs(x1-x0)>abs(y1-y0)*1.7: ch='-'
        elif abs(y1-y0)>abs(x1-x0)*1.7: ch='|'
        else: ch='\\' if (x1-x0)*(y1-y0)>0 else '/'
    while True:
        if 0<=x0<W and 0<=y0<H and grid[y0][x0]==' ': grid[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def put(grid,p,ch):
    x,y=p
    if 0<=x<W and 0<=y<H: grid[y][x]=ch

def body(grid,p,tag):
    sl,sr,pel=p['shoulder_l'],p['shoulder_r'],p['pelvis']
    for a,b in [(sl,sr),(sl,pel),(sr,pel),(sl,p['hand_l']),(sr,p['hand_r']),(pel,p['knee_l']),(pel,p['knee_r']),(p['knee_l'],p['foot_l']),(p['knee_r'],p['foot_r'])]: bres(grid,a,b)
    neck=((sl[0]+sr[0])//2,(sl[1]+sr[1])//2); bres(grid,neck,p['head'],'|')
    put(grid,p['head'],'@' if tag=='A' else 'o'); put(grid,pel,tag)
    for j in ('shoulder_l','shoulder_r','hand_l','hand_r','knee_l','knee_r'): put(grid,p[j],'+')
    put(grid,p['foot_l'],'L' if tag=='A' else 'l'); put(grid,p['foot_r'],'R' if tag=='A' else 'r')

def ascii_frame(st,label=True):
    g=[[' ']*W for _ in range(H)]
    for x in range(W): g[FLOOR][x]='_'
    body(g,st['A'],'A'); body(g,st['B'],'B')
    for a in st.get('anchors',[]): put(g,tuple(a['at']),'x')
    if st.get('shared_center'):
        cx,cy=st['shared_center']; put(g,(cx,cy),'X')
        if st.get('contact_state')=='TWO_ANCHORS': put(g,(cx-1,cy),'>'); put(g,(cx+1,cy),'<')
    if label:
        s=f"{st['key_id']} {st['name']} | {st['timing_class']} {st['timing_provenance']} | CONTACT={st['contact_state']} CUSTODY={st['custody']} A={st['support_A']} B={st['support_B']}"
        for i,ch in enumerate(s[:W]): g[0][i]=ch
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet(keys):
    out=[]
    for k in keys:
        out += ['='*W,f"{k['key_id']}  {k['name']}  | {k['timing_class']} / {k['timing_provenance']}",f"ROLE: {k['causal_role']}",f"STATE: contact={k['contact_state']} custody={k['custody']} support_A={k['support_A']} support_B={k['support_B']} root={k['root_owner']}",f"ARC: {k['motion_arc_root_note']}",ascii_frame(k,False)]
    return '\n'.join(out)+'\n'

def sequence(data):
    keys=data['keys']; scale=data['compile']['preview_time_scale']; frames=[]
    for i,k in enumerate(keys):
        frames += [k]*(TIMING[k['timing_class']]*scale)
        if i<len(keys)-1:
            n=k.get('bridge_to_next',{}).get('frames',0)
            for j in range(1,n+1):
                st=bridge_state(k,keys[i+1],j/(n+1)); st['key_id']=k['key_id']+'~'+keys[i+1]['key_id']; st['name']='CONNECTIVE_'+k.get('bridge_to_next',{}).get('mode','ARC'); frames.append(st)
    return frames

def choose_font():
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf']:
        if os.path.exists(p): return ImageFont.truetype(p,14)
    return ImageFont.load_default()

def raster(text,path):
    im=Image.new('RGB',(960,360),'black'); d=ImageDraw.Draw(im); d.multiline_text((14,12),text,font=choose_font(),fill='white',spacing=1); im.save(path)

def render_mp4(data,tmp):
    frames=sequence(data); fd=tmp/'frames'; fd.mkdir()
    for i,st in enumerate(frames): raster(ascii_frame(st),fd/f'{i:04d}.png')
    mp4=tmp/'motion.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(data['compile']['fps']),'-i',str(fd/'%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',str(mp4)],check=True)
    return mp4,len(frames)

def html(data,sheet,video_bytes):
    payload=json.dumps(data,indent=2,ensure_ascii=False)
    b64=base64.b64encode(video_bytes).decode('ascii')
    import html as H
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{data['experiment_id']}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#080808;color:#eee;font-family:system-ui,sans-serif}}header{{padding:12px 16px;border-bottom:1px solid #444}}nav{{display:flex;gap:8px;padding:10px 16px;position:sticky;top:0;background:#080808}}button{{font:inherit;padding:8px 14px}}section{{display:none;padding:12px 16px}}section.active{{display:block}}pre{{margin:0;overflow:auto;white-space:pre;font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;tab-size:2;line-height:1.15}}video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #444}}
</style></head><body><header><strong>ASCII Kinesis V2 · CONTACT 007 · scoped sync grapple repair</strong></header><nav>
<button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre>{H.escape(sheet)}</pre></section><section id="json"><pre>{H.escape(payload)}</pre></section><section id="video"><video controls autoplay muted loop playsinline src="data:video/mp4;base64,{b64}"></video></section>
<script>const bs=[...document.querySelectorAll('button[data-view]')];const ss=[...document.querySelectorAll('section')];for(const b of bs)b.onclick=()=>{{for(const s of ss)s.classList.toggle('active',s.id===b.dataset.view)}};</script></body></html>'''

def main():
    data=json.loads(MOTION.read_text())
    sheet=contact_sheet(data['keys']); (HERE/'contact-sheet.txt').write_text(sheet)
    with tempfile.TemporaryDirectory() as td:
        mp4,n=render_mp4(data,Path(td)); raw=mp4.read_bytes()
    sha=hashlib.sha256(raw).hexdigest(); expected=data['compile'].get('media_sha256')
    if expected and sha!=expected: raise SystemExit(f'media hash mismatch: {sha} != {expected}')
    if n!=data['compile']['video_frames_total']: raise SystemExit(f'frame count mismatch: {n}')
    page=html(data,sheet,raw); (HERE/'scoped-sync-grapple-repair.motion.html').write_text(page)
    print(json.dumps({'media_sha256':sha,'media_bytes':len(raw),'video_frames_total':n,'spa_bytes':len(page.encode())},sort_keys=True))
if __name__=='__main__': main()
