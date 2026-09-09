#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

H=Path(__file__).resolve().parent
M=H/'motion.json'
A=H/'contact-sheet.txt'
S=H/'shield-knee-post-torque-recovery.motion.html'
V=H/'shield-knee-post-torque-recovery.mp4'
W,HH=72,24

def J(k,m):
    return {n:tuple(xy) for n,xy in zip(m['rig']['joint_order'],k['pose_rig']['joint_xy'])}

def line(g,a,b,ch=None):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<HH and g[y0][x0]==' ':
            if ch:g[y0][x0]=ch
            else:g[y0][x0]='|' if x0==x1 else ('-' if y0==y1 else ('\\' if (x1-x0)*(y1-y0)>0 else '/'))
        if x0==x1 and y0==y1:break
        e2=2*e
        if e2>=dy:e+=dy;x0+=sx
        if e2<=dx:e+=dx;y0+=sy

def support_names(s):
    if s in {'BOTH_FEET','BOTH_NEW_BIASED'}:return {'foot_l','foot_r'}
    if s=='REAR_FOOT':return {'foot_r'}
    if s=='REAR_FOOT_PLUS_KNEE':return {'foot_r','knee_l'}
    if s=='NEW_LEAD_FOOT':return {'foot_l'}
    return set()

def topology(k):
    return (k.get('support_contact'),k.get('contact_state'))

def pose(k,m,meta=False):
    j=J(k,m);fy=m['rig']['floor_y'];g=[[' ']*W for _ in range(HH)]
    for x in range(2,W-2):g[fy][x]='_'
    for a,b in m['rig']['links']:line(g,j[a],j[b])
    glyph={'head':'O','neck':'+','shoulder_l':'+','shoulder_r':'+','elbow_l':'+','elbow_r':'+',
           'hand_l':'G','hand_r':'o','pelvis':'@','knee_l':'+','knee_r':'+','foot_l':'=','foot_r':'='}
    for n,c in glyph.items():
        x,y=j[n]
        if 0<=x<W and 0<=y<HH:g[y][x]=c
    state=k.get('contact_state')
    if state=='PRECONTACT_LEFT':
        for x in range(3,16,2):
            if 0<=8<HH and g[8][x]==' ':g[8][x]='>'
    elif state=='IMPACT_LEFT':
        hx,hy=j['hand_l']
        for x in range(3,max(3,hx-1)):
            if 0<=hy<HH and g[hy][x]==' ':g[hy][x]='>'
        if hx-1>=0:g[hy][hx-1]='X'
    marks=[]
    s=k.get('support_contact','')
    if s=='BOTH_FEET':marks=[('foot_l','L'),('foot_r','R')]
    elif s=='REAR_FOOT':marks=[('foot_r','R')]
    elif s=='REAR_FOOT_PLUS_KNEE':marks=[('foot_r','R'),('knee_l','K')]
    elif s=='NEW_LEAD_FOOT':marks=[('foot_l','N')]
    elif s=='BOTH_NEW_BIASED':marks=[('foot_l','N'),('foot_r','r')]
    for n,c in marks:
        x,y=j[n]
        yy=min(HH-1,fy+1) if (n.startswith('foot') or n=='knee_l') else max(0,min(HH-1,y-1))
        if 0<=x<W:g[yy][x]=c
    body='\n'.join(''.join(r).rstrip() for r in g)
    if not meta:return body
    return (f"{k['key_id']}  {k['name']}  [{k['timing_class']} | {k['timing_provenance']}]\n"
            f"{body}\n"
            f"support={s} contact={state} root={k['root_state']} guard={k['guard_state']}\n"
            f"role={k['causal_role']}\narc={k['motion_arc_root_note']} debt={k['recovery_debt']:.2f}")

def interp(a,b,t,m,arc):
    if topology(a)!=topology(b):raise SystemExit(f"semantic bridge forbidden: {a['key_id']} -> {b['key_id']}")
    names=m['rig']['joint_order'];aj=J(a,m);bj=J(b,m);out={};pinned=support_names(a.get('support_contact',''))
    if a.get('contact_state')=='IMPACT_LEFT':pinned.add('hand_l')
    for n in names:
        p0,p1=aj[n],bj[n]
        lag=.15 if n=='hand_r' else (.10 if n in ('head','hand_l') and n not in pinned else 0)
        tt=max(0,min(1,t-lag));e=tt*tt*(3-2*tt);q=4*tt*(1-tt)
        scale=0 if n in pinned else (1 if n in ('pelvis','neck','head','hand_l','hand_r') else .55)
        out[n]=[round(p0[0]+(p1[0]-p0[0])*e+arc[0]*q*scale),
                round(p0[1]+(p1[1]-p0[1])*e+arc[1]*q*scale)]
    k={x:y for x,y in a.items() if x!='pose_rig'}
    k['pose_rig']={'joint_xy':[out[n] for n in names]}
    k['key_id']=a['key_id']+'→'+b['key_id'];k['name']='BRIDGE'
    return k

def frames(m):
    out=[];labs=[];ks=m['keys']
    for i,k in enumerate(ks):
        for _ in range(k['hold_frames']):out.append(pose(k,m));labs.append(k['key_id'])
        if i<len(ks)-1:
            n=k['bridge']['frames'];arc=k['bridge']['root_arc']
            if n and topology(k)!=topology(ks[i+1]):raise SystemExit(f"bridge crosses semantic topology: {k['key_id']} -> {ks[i+1]['key_id']}")
            for s in range(1,n+1):
                z=interp(k,ks[i+1],s/(n+1),m,arc);out.append(pose(z,m));labs.append(z['key_id'])
    return out,labs

def sheet(m):
    return (
      'ASCII KINESIS V2 DEFENSE 016 — GUARD COLUMN / KNEE-POST TORQUE RECOVERY\n'
      'abstract generic ASCII rig only — TSR Cress Albane asset 11953 is whole-sheet campaign evidence only; no source pixels, contours, costume, layout, or choreography enter output\n'
      'performance law: offset ready -> guard column brace -> precontact still point -> fixed-endpoint impact -> pinned body shear -> rear-support break -> contact-release fold -> knee seek -> real knee+rear-foot low tripod -> low torque spill -> knee release corkscrew -> around preplant -> new-foot catch -> catch overshoot -> second-foot reacquire -> late guard reopen -> secondary settle -> displaced ready debt\n'
      'novelty: body knee becomes temporary floor support while the guard remains an upper-body constraint; no tool-floor kickstand, rear-anchor cross-body exit, backdash, wall share, or BASE/TASK phase-slip grammar\n'
      'legend: G=abstract guard hand; X=impact; >=incoming left-side force; L/R=initial supports; K=knee floor post; N=new lead support; floor=_\n\n'
      + ('\n\n'+'-'*72+'\n\n').join(pose(k,m,True) for k in m['keys'])
    )

def video(m,p):
    fs,labs=frames(m);font=ImageFont.load_default(size=16);meta=ImageFont.load_default(size=14)
    with tempfile.TemporaryDirectory(prefix='d016-') as td:
        td=Path(td)
        for i,(txt,lab) in enumerate(zip(fs,labs)):
            im=Image.new('RGB',(800,450),(12,12,12));d=ImageDraw.Draw(im)
            d.text((14,8),f"{lab}   DEFENSE 016   GUARD COLUMN / KNEE-POST TORQUE RECOVERY",fill=(220,220,220),font=meta)
            d.multiline_text((16,42),txt,fill=(246,246,246),font=font,spacing=1)
            d.text((14,420),'LEFT threat >>> | G=guard | K=knee floor-post | abstract ASCII rig only',fill=(180,180,180),font=meta)
            im.save(td/f'{i:04d}.png')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(m['compile']['fps']),'-i',str(td/'%04d.png'),
                        '-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart','-preset','veryslow','-crf','28',str(p)],check=True)
    return len(fs)

def probe(p):
    q=json.loads(subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
        'stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration','-of','json',str(p)],
        check=True,capture_output=True,text=True).stdout)
    s=q['streams'][0]
    subprocess.run(['ffmpeg','-v','error','-i',str(p),'-f','null','-'],check=True)
    return {'tool':'ffprobe+ffmpeg_full_decode','codec':s['codec_name'],'width':int(s['width']),'height':int(s['height']),
            'fps':s['r_frame_rate'],'frames':int(s['nb_frames']),'duration_seconds':float(q['format']['duration'])}

def spa(m,a,v):
    a64=base64.b64encode(gzip.compress(a.encode('utf-8'),9)).decode()
    j64=base64.b64encode(gzip.compress(M.read_bytes(),9)).decode()
    v64=base64.b64encode(v).decode()
    css='html,body{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}header{position:sticky;top:0;background:#171717;padding:12px;border-bottom:1px solid #444}nav{display:flex;gap:8px}button{font:inherit;padding:.55rem .85rem;background:#222;color:#eee;border:1px solid #666;border-radius:6px}button[aria-selected=true]{background:#eee;color:#111}main{padding:14px}.panel{display:none}.panel.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto;border:1px solid #555;background:#000}'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Defense 016 — Guard Column / Knee-Post Torque Recovery</title><style>{css}</style></head><body><header><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section class="panel active" data-panel="ascii"><pre id="a"></pre></section><section class="panel" data-panel="json"><pre id="j"></pre></section><section class="panel" data-panel="video"><video id="v" controls playsinline preload="metadata"></video></section></main><script>async function z(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([z({json.dumps(a64)}),z({json.dumps(j64)})]).then(([a,j])=>{{document.getElementById("a").textContent=a;document.getElementById("j").textContent=JSON.stringify(JSON.parse(j),null,2)}});document.getElementById("v").src="data:video/mp4;base64,"+{json.dumps(v64)};const B=[...document.querySelectorAll("button[data-view]")],P=[...document.querySelectorAll("[data-panel]")];B.forEach(b=>b.onclick=()=>{{B.forEach(x=>x.setAttribute("aria-selected",String(x===b)));P.forEach(p=>p.classList.toggle("active",p.dataset.panel===b.dataset.view))}});</script></body></html>'''

def main():
    m=json.loads(M.read_text(encoding='utf-8'))
    a=sheet(m);A.write_text(a,encoding='utf-8')
    n=video(m,V);v=V.read_bytes();sha=hashlib.sha256(v).hexdigest();pr=probe(V)
    if m['media']['sha256'] not in {'PENDING',sha}:raise SystemExit(f"media identity mismatch: declared {m['media']['sha256']} built {sha}")
    if m['media']['frames'] not in {0,n}:raise SystemExit(f"frame identity mismatch: declared {m['media']['frames']} built {n}")
    if m['media']['bytes'] not in {0,len(v)}:raise SystemExit(f"byte identity mismatch: declared {m['media']['bytes']} built {len(v)}")
    S.write_text(spa(m,a,v),encoding='utf-8')
    print(json.dumps({'ascii_sha256':hashlib.sha256(a.encode()).hexdigest(),'media_sha256':sha,'media_bytes':len(v),'frames':n,'probe':pr},sort_keys=True))
if __name__=='__main__':main()
