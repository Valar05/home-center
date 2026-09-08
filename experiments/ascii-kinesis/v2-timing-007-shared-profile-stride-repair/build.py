#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D=Path(__file__).resolve().parent
M=D/'motion.json'
C=D/'contact-sheet.txt'
V=D/'shared-profile-stride-repair.motion.mp4'
H=D/'shared-profile-stride-repair.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
GW,GH=41,21
GROUND=19
LINKS=[
 ('root','chest'),('chest','head'),
 ('chest','left_shoulder'),('left_shoulder','left_elbow'),('left_elbow','left_hand'),
 ('chest','right_shoulder'),('right_shoulder','right_elbow'),('right_elbow','right_hand'),
 ('root','left_hip'),('left_hip','left_knee'),('left_knee','left_foot'),
 ('root','right_hip'),('right_hip','right_knee'),('right_knee','right_foot')
]
MARK={
 'root':'@','chest':'+','head':'O',
 'left_shoulder':'o','left_elbow':'o','left_hand':'a',
 'right_shoulder':'o','right_elbow':'o','right_hand':'b',
 'left_hip':'o','left_knee':'o','left_foot':'L',
 'right_hip':'o','right_knee':'o','right_foot':'R'
}

def sha(b): return hashlib.sha256(b).hexdigest()

def bline(a,b):
    x,y=a; X,Y=b; dx=abs(X-x); sx=1 if x<X else -1; dy=-abs(Y-y); sy=1 if y<Y else -1; e=dx+dy; out=[]
    while True:
        out.append((x,y))
        if (x,y)==(X,Y): return out
        q=2*e
        if q>=dy: e+=dy; x+=sx
        if q<=dx: e+=dx; y+=sy

def glyph(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>2*abs(dy): return '-'
    if abs(dy)>2*abs(dx): return '|'
    return '\\' if dx*dy>0 else '/'

def pose(m,k):
    return {n:list(k['pose_rig']['coords'][i]) for i,n in enumerate(m['rig_schema']['joint_order'])}

def mirror(j):
    return {n:[(GW-1)-p[0],p[1]] for n,p in j.items()}

def art(joints,orientation='RIGHT'):
    j={n:tuple(v) for n,v in joints.items()}
    g=[[' ']*GW for _ in range(GH)]
    def put(x,y,c):
        if 0<=x<GW and 0<=y<GH: g[y][x]=c
    for a,b in LINKS:
        for x,y in bline(j[a],j[b])[1:-1]:
            if 0<=x<GW and 0<=y<GH and g[y][x]==' ':
                put(x,y,glyph(j[a],j[b]))
    for n,(x,y) in j.items(): put(x,y,MARK[n])
    for x in range(1,GW-1): put(x,GROUND,'=')
    put(1,1,'>' if orientation=='RIGHT' else '<')
    return '\n'.join(''.join(r).rstrip() for r in g)

def ease(t,k):
    if k=='EASE_IN': return t*t
    if k=='EASE_OUT': return 1-(1-t)**2
    if k=='SMOOTHSTEP': return t*t*(3-2*t)
    return t

def interp(a,b,t,bias):
    out={}
    for n,p in a.items():
        q=b[n]
        mag=2.2 if 'hand' in n or 'foot' in n else 1.3 if 'elbow' in n or 'knee' in n else .7
        cx=(p[0]+q[0])/2+bias[0]*mag
        cy=(p[1]+q[1])/2+bias[1]*mag
        u=1-t
        out[n]=[
            round(u*u*p[0]+2*u*t*cx+t*t*q[0]),
            round(u*u*p[1]+2*u*t*cy+t*t*q[1])
        ]
    return out

def panel(frame_j,key,sub='KEY'):
    right=art(frame_j,'RIGHT').splitlines()
    left=art(mirror(frame_j),'LEFT').splitlines()
    while len(right)<GH: right.append('')
    while len(left)<GH: left.append('')
    hdr=f"SHARED GAIT CLOCK  {key['key_id']} {key['name']}  {key['timing_class']} / {key['timing_provenance']}  [{sub}]"
    axis="FACING RIGHT - PRESENTATION ONLY".ljust(GW)+"   "+"FACING LEFT - SAME TEMPORAL KEY"
    body='\n'.join(right[i].ljust(GW)+"   "+left[i] for i in range(GH))
    return hdr+"\n"+axis+"\n"+body

def semantic_frames(m):
    out=[]
    ks=m['keys']
    for i,k in enumerate(ks):
        p=pose(m,k)
        for h in range(HOLD[k['timing_class']]):
            out.append(panel(p,k,f"HOLD {h+1}/{HOLD[k['timing_class']]}"))
        if i==len(ks)-1:
            continue
        n=ks[i+1]
        s=k['bridge_to_next']; q=int(s.get('frames',0))
        same_support=(k['support_contact']==n['support_contact'])
        if q and not same_support:
            raise SystemExit(f"bridge crosses support topology: {k['key_id']} -> {n['key_id']}")
        for z in range(1,q+1):
            t=ease(z/(q+1),s['easing'])
            j=interp(p,pose(m,n),t,s['arc_bias'])
            out.append(panel(j,k,f"BRIDGE {z}/{q} -> {n['key_id']}"))
    return out

def sheet(m):
    o=[
      'ASCII KINESIS V2 TIMING 007 - SHARED PROFILE STRIDE REPAIR',
      f"revises: {m['revises']}",
      f"negative_fixture: {m['negative_fixture']}",
      'SOURCE ART: NONE | SOURCE PREVIEW TIMING: OBSERVED EVIDENCE ONLY | AUTHORED DECISIVE-KEY TIMING: INFERRED',
      'POLICY: STREET_FIGHTER/CAPCOM | ONES=1 display frame | TWOS=2 | FOURS=4 | 1s/2s/4s are classes, never seconds',
      'VARIANT RULE: FACING_RIGHT + FACING_LEFT are simultaneous presentation transforms of ONE shared temporal key list.',
      ''
    ]
    for k in m['keys']:
        p=pose(m,k)
        o += [
          f"[{k['key_id']}] {k['name']}",
          f"pose/rig={k['pose_rig']['rig_id']} | support/contact={k['support_contact']}",
          f"root/motion-arc={k['motion_arc_root_note']}",
          f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']}",
          f"causal_role={k['causal_role']}",
          f"clocks GAIT={k['clock_state']['GAIT_CLOCK']} | ORIENTATION={k['clock_state']['ORIENTATION_VARIANT']}",
          'FACING_RIGHT (presentation only)',
          art(p,'RIGHT'),
          'FACING_LEFT (same temporal key, mirrored presentation only)',
          art(mirror(p),'LEFT'),
          ''
        ]
    return '\n'.join(o).rstrip()+'\n'

def get_font(size=10):
    for fp in (
      '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',
      '/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'
    ):
        try: return ImageFont.truetype(fp,size)
        except Exception: pass
    return ImageFont.load_default()

def render_png(txt,path):
    font=get_font(10)
    im=Image.new('RGB',(960,540),'black')
    d=ImageDraw.Draw(im)
    d.multiline_text((14,12),txt,font=font,fill='white',spacing=1)
    im.save(path)

def spa(m,s,v):
    vid=base64.b64encode(v).decode('ascii')
    pack=lambda x:base64.b64encode(gzip.compress(x.encode('utf-8'),mtime=0)).decode('ascii')
    mj=json.dumps(m,separators=(',',':'),ensure_ascii=False)
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Timing 007 Repair</title><style>:root{color-scheme:dark;background:#101010;color:#eee}body{margin:1rem;font-family:system-ui}nav{display:flex;gap:.5rem}section[hidden]{display:none}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto}video{max-width:100%;height:auto}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="a"></pre></section><section id="json" hidden><pre id="j"></pre></section><section id="video" hidden><video controls autoplay muted playsinline><source src="data:video/mp4;base64,__V__" type="video/mp4"></video></section><script>const P={a:"__A__",j:"__J__"};async function u(x){const b=Uint8Array.from(atob(x),c=>c.charCodeAt(0)),d=new DecompressionStream("gzip");return new TextDecoder().decode(await new Response(new Blob([b]).stream().pipeThrough(d)).arrayBuffer())}(async()=>{a.textContent=await u(P.a);j.textContent=await u(P.j)})();const B=[...document.querySelectorAll("button[data-view]")],S=[...document.querySelectorAll("section")];B.forEach(b=>b.onclick=()=>S.forEach(s=>s.hidden=s.id!==b.dataset.view));</script></body></html>'''
    return page.replace('__V__',vid).replace('__A__',pack(s)).replace('__J__',pack(mj))

def main():
    m=json.loads(M.read_text(encoding='utf-8'))
    s=sheet(m); C.write_text(s,encoding='utf-8')
    sem=semantic_frames(m)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,x in enumerate(sem): render_png(x,td/f'f{i:03d}.png')
        subprocess.run([
          'ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(m['compile']['fps']),
          '-i',str(td/'f%03d.png'),'-an','-c:v','libx264','-preset','veryslow','-crf','30',
          '-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1',str(V)
        ],check=True)
    v=V.read_bytes()
    m['compile']['video_frames_total']=len(sem)
    m['compile']['media_sha256']=sha(v)
    m['compile']['media_bytes']=len(v)
    m['compile']['ascii_sheet_sha256']=sha(s.encode('utf-8'))
    M.write_text(json.dumps(m,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
    H.write_text(spa(m,s,v),encoding='utf-8')
    print(json.dumps({'ok':True,'media_sha256':sha(v),'media_bytes':len(v),'video_frames':len(sem),
                      'html_sha256':sha(H.read_bytes()),'ascii_sha256':sha(s.encode('utf-8'))},sort_keys=True))

if __name__=='__main__':
    main()
