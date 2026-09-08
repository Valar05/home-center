#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

H=Path(__file__).resolve().parent
M=H/'motion.json'
A=H/'contact-sheet.txt'
S=H/'floor-support-ladder-repair.motion.html'
W,HH=64,22

def J(k,m): return {n:tuple(xy) for n,xy in zip(m['rig']['joint_order'],k['pose_rig']['joint_xy'])}

def line(g,a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
    while 1:
        if 0<=x0<W and 0<=y0<HH and g[y0][x0]==' ':
            g[y0][x0]='|' if x0==x1 else ('-' if y0==y1 else ('\\' if (x1-x0)*(y1-y0)>0 else '/'))
        if x0==x1 and y0==y1: break
        e2=2*e
        if e2>=dy:e+=dy;x0+=sx
        if e2<=dx:e+=dx;y0+=sy

def support_names(s):
    q=set()
    if s=='BOTH_FEET': return {'foot_l','foot_r'}
    if s=='REAR_FOOT': return {'foot_r'}
    if 'FOOT_L' in s:q.add('foot_l')
    if 'FOOT_R' in s:q.add('foot_r')
    if 'HAND_L' in s or 'FOREARM_L' in s:q.add('hand_l')
    if 'HAND_R' in s or 'FOREARM_R' in s:q.add('hand_r')
    if 'KNEE_L' in s:q.add('knee_l')
    if 'KNEE_R' in s:q.add('knee_r')
    if 'HIP' in s:q.add('pelvis')
    return q

def topology(k):
    return (k.get('support_contact'),k.get('contact_state'),k.get('constraint_state'),k.get('root_state'))

def pose(k,m,meta=False):
    j=J(k,m);fy=m['rig']['floor_y'];g=[[' ']*W for _ in range(HH)]
    for x in range(4,60):g[fy][x]='_'
    for a,b in [('neck','pelvis'),('shoulder_l','shoulder_r'),('shoulder_l','elbow_l'),('elbow_l','hand_l'),('shoulder_r','elbow_r'),('elbow_r','hand_r'),('pelvis','knee_l'),('knee_l','foot_l'),('pelvis','knee_r'),('knee_r','foot_r')]:
        line(g,j[a],j[b])
    for n,c in {'head':'O','neck':'+','shoulder_l':'+','shoulder_r':'+','elbow_l':'+','elbow_r':'+','hand_l':'o','hand_r':'o','pelvis':'@','knee_l':'+','knee_r':'+','foot_l':'=','foot_r':'='}.items():
        x,y=j[n]
        if 0<=x<W and 0<=y<HH:g[y][x]=c
    if k.get('contact_state')=='IMPACT_FROM_RIGHT_LOW':
        for x in range(49,56):g[13][x]='<'
    s=k.get('support_contact','');q=[]
    if s=='BOTH_FEET':q=[('foot_l','L'),('foot_r','R')]
    elif s=='REAR_FOOT':q=[('foot_r','R')]
    else:
        if 'FOOT_L' in s:q.append(('foot_l','L'))
        if 'FOOT_R' in s:q.append(('foot_r','R'))
        if 'HAND_L' in s or 'FOREARM_L' in s:q.append(('hand_l','H'))
        if 'HAND_R' in s or 'FOREARM_R' in s:q.append(('hand_r','H'))
        if 'KNEE_L' in s:q.append(('knee_l','K'))
        if 'KNEE_R' in s:q.append(('knee_r','K'))
        if 'HIP' in s:q.append(('pelvis','P'))
    for n,c in q:
        x=j[n][0]
        if 0<=x<W and fy+1<HH:g[fy+1][x]=c
    b='\n'.join(''.join(r).rstrip() for r in g)
    if not meta:return b
    return f"{k['key_id']}  {k['name']}  [{k['timing_class']} | {k['timing_provenance']}]\n{b}\nsupport={s} root={k['root_state']} contact={k['contact_state']}\nrole={k['causal_role']}\narc={k['motion_arc_root_note']} debt={k['recovery_debt']:.2f}"

def interp(a,b,t,m,arc):
    if topology(a)!=topology(b):
        raise SystemExit(f"semantic bridge forbidden: {a['key_id']} -> {b['key_id']}")
    names=m['rig']['joint_order'];aj=J(a,m);bj=J(b,m);o={};pinned=support_names(a.get('support_contact',''))
    for n in names:
        p0,p1=aj[n],bj[n]
        lag=.13 if n in ('head','hand_r') else (.07 if n=='hand_l' else (-.08 if n in ('foot_l','foot_r') else 0))
        tt=max(0,min(1,t-lag));e=tt*tt*(3-2*tt);q=4*tt*(1-tt)
        sc=0 if n in pinned else (1 if n in ('pelvis','neck','head') else .55)
        o[n]=[round(p0[0]+(p1[0]-p0[0])*e+arc[0]*q*sc),round(p0[1]+(p1[1]-p0[1])*e+arc[1]*q*sc)]
    k={x:y for x,y in a.items() if x!='pose_rig'}
    k['pose_rig']={'joint_xy':[o[n] for n in names]}
    k['key_id']=a['key_id']+'→'+b['key_id']
    return k

def frames(m):
    out=[];lab=[];ks=m['keys']
    for i,k in enumerate(ks):
        for _ in range(k['hold_frames']):
            out.append(pose(k,m));lab.append(k['key_id'])
        if i<len(ks)-1:
            n=k['bridge']['frames'];arc=k['bridge']['root_arc']
            if n and topology(k)!=topology(ks[i+1]):
                raise SystemExit(f"bridge crosses semantic topology: {k['key_id']} -> {ks[i+1]['key_id']}")
            for s in range(1,n+1):
                x=interp(k,ks[i+1],s/(n+1),m,arc);out.append(pose(x,m));lab.append(x['key_id'])
    return out,lab

def sheet(m):
    return (
        'ASCII KINESIS V2 DEFENSE 011 — FLOOR SUPPORT LADDER REPAIR\n'
        'abstract rig only — source art never enters output\n'
        'performance law: floor contact is consequence; height is purchased by trustworthy support\n'
        'force line: RIGHT-LOW impact -> LEFT/DOWN collapse -> FLOOR overshoot -> HAND/KNEE post -> TRIPOD -> anchored HAND+FOOT push -> RIGHT/UP release -> displaced ready\n\n'
        + ('\n\n'+'-'*64+'\n\n').join(pose(k,m,True) for k in m['keys'])
    )

def video(m,p):
    fs,ls=frames(m);font=ImageFont.load_default(size=16);meta=ImageFont.load_default(size=14)
    with tempfile.TemporaryDirectory(prefix='d011-') as td:
        td=Path(td)
        for i,(t,l) in enumerate(zip(fs,ls)):
            im=Image.new('RGB',(640,360),(12,12,12));d=ImageDraw.Draw(im)
            d.text((12,8),l+'   DEFENSE 011',fill=(220,220,220),font=meta)
            d.multiline_text((14,34),t,fill=(245,245,245),font=font,spacing=1)
            im.save(td/f'{i:04d}.png')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(m['compile']['fps']),'-i',str(td/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart','-preset','veryslow','-crf','28',str(p)],check=True)
    return len(fs)

def spa(m,a,v):
    j=json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(',',':'))
    a64=base64.b64encode(gzip.compress(a.encode(),9)).decode()
    j64=base64.b64encode(gzip.compress(j.encode(),9)).decode()
    v64=base64.b64encode(v).decode()
    css='html,body{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}header{position:sticky;top:0;background:#171717;padding:12px;border-bottom:1px solid #444}nav{display:flex;gap:8px}button{font:inherit;padding:.55rem .85rem;background:#222;color:#eee;border:1px solid #666;border-radius:6px}button[aria-selected=true]{background:#eee;color:#111}main{padding:14px}.panel{display:none}.panel.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto;border:1px solid #555;background:#000}'
    return f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Defense 011 — Floor Support Ladder Repair</title><style>{css}</style></head><body><header><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section class="panel active" data-panel="ascii"><pre id="a"></pre></section><section class="panel" data-panel="json"><pre id="j"></pre></section><section class="panel" data-panel="video"><video id="v" controls loop playsinline preload="metadata"></video></section></main><script>const A={json.dumps(a64)};const J={json.dumps(j64)};const V={json.dumps(v64)};const B=[...document.querySelectorAll("button[data-view]")],P=[...document.querySelectorAll("[data-panel]")];B.forEach(b=>b.onclick=()=>{{B.forEach(x=>x.setAttribute("aria-selected",String(x===b)));P.forEach(p=>p.classList.toggle("active",p.dataset.panel===b.dataset.view))}});async function z(s){{let b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([z(A),z(J)]).then(([a,j])=>{{document.getElementById("a").textContent=a;document.getElementById("j").textContent=JSON.stringify(JSON.parse(j),null,2)}});document.getElementById("v").src="data:video/mp4;base64,"+V;</script></body></html>'

def main():
    m=json.loads(M.read_text())
    a=sheet(m);A.write_text(a)
    tmp=H/'.d011.tmp.mp4'
    try:
        n=video(m,tmp);v=tmp.read_bytes();h=hashlib.sha256(v).hexdigest()
        if h!=m['media']['sha256'] or n!=m['compile']['frames']:
            raise SystemExit('media identity mismatch')
        S.write_text(spa(m,a,v))
    finally:
        if tmp.exists():tmp.unlink()
    print(json.dumps({'frames':n,'media_sha256':h,'ascii_sha256':hashlib.sha256(a.encode()).hexdigest()},sort_keys=True))

if __name__=='__main__':main()
