#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D=Path(__file__).resolve().parent
M=D/'motion.json'
C=D/'contact-sheet.txt'
V=D/'scoped-freeze-release-repair.motion.mp4'
H=D/'scoped-freeze-release-repair.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
GW,GH=39,21
LINKS=[('root','chest'),('chest','neck'),('neck','head'),
       ('chest','left_shoulder'),('left_shoulder','left_elbow'),('left_elbow','left_hand'),
       ('chest','right_shoulder'),('right_shoulder','right_elbow'),('right_elbow','right_hand'),
       ('root','left_hip'),('left_hip','left_knee'),('left_knee','left_foot'),
       ('root','right_hip'),('right_hip','right_knee'),('right_knee','right_foot')]
MARK={'root':'@','chest':'+','neck':':','head':'O',
      'left_shoulder':'o','left_elbow':'o','left_hand':'A',
      'right_shoulder':'o','right_elbow':'o','right_hand':'B',
      'left_hip':'o','left_knee':'o','left_foot':'L',
      'right_hip':'o','right_knee':'o','right_foot':'R'}

def sha(b): return hashlib.sha256(b).hexdigest()

def line(a,b):
    x,y=a; X,Y=b; dx=abs(X-x); sx=1 if x<X else -1; dy=-abs(Y-y); sy=1 if y<Y else -1; e=dx+dy; out=[]
    while True:
        out.append((x,y))
        if (x,y)==(X,Y): return out
        q=2*e
        if q>=dy: e+=dy; x+=sx
        if q<=dx: e+=dx; y+=sy

def glyph(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    return '-' if abs(dx)>2*abs(dy) else '|' if abs(dy)>2*abs(dx) else ('\\\\' if dx*dy>0 else '/')

def art(joints,gate='OPEN'):
    j={n:tuple(v) for n,v in joints.items()}; g=[[' ']*GW for _ in range(GH)]
    def put(x,y,c):
        if 0<=x<GW and 0<=y<GH: g[y][x]=c
    for a,b in LINKS:
        for x,y in line(j[a],j[b])[1:-1]:
            if 0<=x<GW and 0<=y<GH and g[y][x]==' ': put(x,y,glyph(j[a],j[b]))
    for n,(x,y) in j.items(): put(x,y,MARK[n])
    for x in range(8,31): put(x,19,'=')
    put(12,19,'^'); put(26,19,'^')
    put(j['head'][0],1,{'OPEN':'g','FREEZE_B':'F','RELEASE_B':'R'}[gate])
    bx,by=j['right_hand']
    if gate=='FREEZE_B': put(bx-1,by,'['); put(bx+1,by,']')
    if gate=='RELEASE_B': put(bx-1,by,'<'); put(bx+1,by,'>')
    return '\n'.join(''.join(r).rstrip() for r in g)

def ease(t,k):
    if k=='EASE_IN': return t*t
    if k=='EASE_OUT': return 1-(1-t)**2
    if k=='SMOOTHSTEP': return t*t*(3-2*t)
    return t

def interp(a,b,t,bias):
    out={}
    for n,p in a.items():
        if 'foot' in n:
            out[n]=p
            continue
        q=b[n]; mag=1.7 if 'hand' in n else 1.0 if 'elbow' in n else .5
        cx=(p[0]+q[0])/2+bias[0]*mag; cy=(p[1]+q[1])/2+bias[1]*mag; u=1-t
        out[n]=[round(u*u*p[0]+2*u*t*cx+t*t*q[0]),round(u*u*p[1]+2*u*t*cy+t*t*q[1])]
    return out

def pose(m,k):
    return {n:k['pose_rig']['coords'][i] for i,n in enumerate(m['rig_schema']['joint_order'])}

def semantic_frames(m):
    out=[]; ks=m['keys']
    for i,k in enumerate(ks):
        out += [art(pose(m,k),k['pose_rig']['gate_state'])]*HOLD[k['timing_class']]
        n=ks[(i+1)%len(ks)]; s=k['bridge_to_next']; q=int(s.get('frames',0))
        event_boundary=bool(n.get('event')) or k['pose_rig']['gate_state']!=n['pose_rig']['gate_state']
        if q and not event_boundary:
            for z in range(1,q+1):
                t=ease(z/(q+1),s['easing'])
                j=interp(pose(m,k),pose(m,n),t,s['arc_bias'])
                out.append(art(j,k['pose_rig']['gate_state']))
    return out

def sheet(m):
    o=[
      'ASCII KINESIS V2 TIMING 006 — SCOPED FREEZE / RELEASE REPAIR',
      f"revises: {m['revises']}",
      f"negative_fixture: {m['negative_fixture']}",
      'SOURCE ART: NONE | SOURCE TIMING OBSERVED: NONE | AUTHORED TIMING: INFERRED',
      'POLICY: STREET_FIGHTER/CAPCOM | ONES=1 display frame | TWOS=2 | FOURS=4 | 1s/2s/4s are classes, never seconds',
      ''
    ]
    for k in m['keys']:
        o += [
          f"[{k['key_id']}] {k['name']}",
          f"pose/rig={k['pose_rig']['rig_id']} | support/contact={k['support_contact']}",
          f"root/motion-arc={k['motion_arc_root_note']}",
          f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']}",
          f"causal_role={k['causal_role']}",
          f"clocks BASE={k['clock_state']['BASE']} | A={k['clock_state']['SIGNAL_A']} | B={k['clock_state']['SIGNAL_B']} | GATE={k['clock_state']['GATE']}",
          art(pose(m,k),k['pose_rig']['gate_state']),
          ''
        ]
    return '\n'.join(o).rstrip()+'\n'

def render_png(txt,path):
    try: font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',13)
    except Exception: font=ImageFont.load_default()
    im=Image.new('RGB',(640,360),'black'); d=ImageDraw.Draw(im)
    d.text((14,8),'SCOPED FREEZE / RELEASE — PHASE DEBT',font=font,fill='white')
    d.multiline_text((150,34),txt,font=font,fill='white',spacing=0)
    im.save(path)

def spa(m,s,v):
    vid=base64.b64encode(v).decode('ascii')
    pack=lambda x:base64.b64encode(gzip.compress(x.encode('utf-8'),mtime=0)).decode('ascii')
    mj=json.dumps(m,separators=(',',':'),ensure_ascii=False)
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Timing 006 Repair</title><style>:root{color-scheme:dark;background:#101010;color:#eee}body{margin:1rem;font-family:system-ui}nav{display:flex;gap:.5rem}section[hidden]{display:none}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto}video{max-width:100%;height:auto}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="a"></pre></section><section id="json" hidden><pre id="j"></pre></section><section id="video" hidden><video controls autoplay muted loop playsinline><source src="data:video/mp4;base64,__V__" type="video/mp4"></video></section><script>const P={a:"__A__",j:"__J__"};async function u(x){const b=Uint8Array.from(atob(x),c=>c.charCodeAt(0)),d=new DecompressionStream("gzip");return new TextDecoder().decode(await new Response(new Blob([b]).stream().pipeThrough(d)).arrayBuffer())}(async()=>{a.textContent=await u(P.a);j.textContent=await u(P.j)})();const B=[...document.querySelectorAll("button[data-view]")],S=[...document.querySelectorAll("section")];B.forEach(b=>b.onclick=()=>S.forEach(s=>s.hidden=s.id!==b.dataset.view));</script></body></html>'''
    return page.replace('__V__',vid).replace('__A__',pack(s)).replace('__J__',pack(mj))

def main():
    m=json.loads(M.read_text(encoding='utf-8'))
    s=sheet(m); C.write_text(s,encoding='utf-8')
    sem=semantic_frames(m)
    if len(sem)!=int(m['compile']['semantic_frames_per_loop']): raise SystemExit(f"semantic-frame-count mismatch {len(sem)}")
    if len(sem)!=int(m['compile']['video_frames_total']): raise SystemExit(f"video-frame-count mismatch {len(sem)}")
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,x in enumerate(sem): render_png(x,td/f'f{i:03d}.png')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(m['compile']['fps']),'-i',str(td/'f%03d.png'),'-an','-c:v','libx264','-preset','veryslow','-crf','32','-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1',str(V)],check=True)
    v=V.read_bytes(); mh=sha(v); ah=sha(s.encode('utf-8'))
    m['compile']['media_sha256']=mh; m['compile']['media_bytes']=len(v); m['compile']['ascii_sheet_sha256']=ah
    M.write_text(json.dumps(m,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
    H.write_text(spa(m,s,v),encoding='utf-8')
    print(json.dumps({'ok':True,'media_sha256':mh,'media_bytes':len(v),'html_sha256':sha(H.read_bytes()),'ascii_sha256':ah,'semantic_frames':len(sem),'video_frames':len(sem)},sort_keys=True))

if __name__=='__main__':
    main()
