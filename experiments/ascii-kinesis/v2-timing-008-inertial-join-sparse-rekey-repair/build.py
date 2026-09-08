#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

D=Path(__file__).resolve().parent
M=D/'motion.json'; C=D/'contact-sheet.txt'
V=D/'inertial-join-sparse-rekey-repair.motion.mp4'
H=D/'inertial-join-sparse-rekey-repair.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
GW,GH=48,22
PLATFORM_Y=19
JOINTS=["root","chest","head","left_shoulder","left_elbow","left_hand","right_shoulder","right_elbow","right_hand","left_hip","left_knee","left_foot","right_hip","right_knee","right_foot"]
LINKS=[('root','chest'),('chest','head'),('chest','left_shoulder'),('left_shoulder','left_elbow'),('left_elbow','left_hand'),('chest','right_shoulder'),('right_shoulder','right_elbow'),('right_elbow','right_hand'),('root','left_hip'),('left_hip','left_knee'),('left_knee','left_foot'),('root','right_hip'),('right_hip','right_knee'),('right_knee','right_foot')]
MARK={'root':'@','chest':'+','head':'O','left_shoulder':'o','left_elbow':'o','left_hand':'a','right_shoulder':'o','right_elbow':'o','right_hand':'b','left_hip':'o','left_knee':'o','left_foot':'L','right_hip':'o','right_knee':'o','right_foot':'R'}

def sha(b): return hashlib.sha256(b).hexdigest()
def bline(a,b):
    x,y=a;X,Y=b;dx=abs(X-x);sx=1 if x<X else -1;dy=-abs(Y-y);sy=1 if y<Y else -1;e=dx+dy;o=[]
    while True:
        o.append((x,y))
        if (x,y)==(X,Y): return o
        q=2*e
        if q>=dy:e+=dy;x+=sx
        if q<=dx:e+=dx;y+=sy
def glyph(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if abs(dx)>2*abs(dy): return '-'
    if abs(dy)>2*abs(dx): return '|'
    return '\\' if dx*dy>0 else '/'
def pose(m,k): return {n:list(k['pose_rig']['coords'][i]) for i,n in enumerate(m['rig_schema']['joint_order'])}
def ease(t,name):
    if name=='EASE_IN': return t*t
    if name=='EASE_OUT': return 1-(1-t)*(1-t)
    if name=='SMOOTHSTEP': return t*t*(3-2*t)
    return t
def quad(p,q,t,bias,mag):
    cx=(p[0]+q[0])/2+bias[0]*mag;cy=(p[1]+q[1])/2+bias[1]*mag;u=1-t
    return [round(u*u*p[0]+2*u*t*cx+t*t*q[0]),round(u*u*p[1]+2*u*t*cy+t*t*q[1])]
def interp(a,b,t,bias):
    out={}
    for n,p in a.items():
        mag=2.5 if ('hand' in n or 'head' in n) else 1.6 if ('elbow' in n or 'knee' in n) else .9
        out[n]=quad(p,b[n],t,bias,mag)
    return out

def art(joints,parent_x=0,pressure='='):
    j={n:tuple(v) for n,v in joints.items()}; g=[[' ']*GW for _ in range(GH)]
    def put(x,y,c):
        if 0<=x<GW and 0<=y<GH:g[y][x]=c
    for a,b in LINKS:
        for x,y in bline(j[a],j[b])[1:-1]:
            if 0<=x<GW and 0<=y<GH and g[y][x]==' ':put(x,y,glyph(j[a],j[b]))
    for n,(x,y) in j.items():put(x,y,MARK[n])
    for x in range(13,34):put(x,PLATFORM_Y,pressure)
    put(12,PLATFORM_Y,'[');put(34,PLATFORM_Y,']')
    ticker=13+(parent_x%21); put(ticker,PLATFORM_Y,'#')
    put(2,1,'P');put(3,1,'>')
    for i,c in enumerate(f'{parent_x:02d}'):put(5+i,1,c)
    return '\n'.join(''.join(r).rstrip() for r in g)

def timeline(m):
    frames=[]
    for i,k in enumerate(m['keys']):
        p=pose(m,k)
        for h in range(HOLD[k['timing_class']]): frames.append({'j':p,'key':k,'sub':f'HOLD {h+1}/{HOLD[k["timing_class"]]}','bridge':False})
        if i==len(m['keys'])-1: continue
        nxt=m['keys'][i+1]; spec=k['bridge_to_next']; q=int(spec['frames'])
        if q and k['support_contact'].split(';')[0]!=nxt['support_contact'].split(';')[0]: raise SystemExit('bridge crosses support topology')
        for z in range(1,q+1):
            t=ease(z/(q+1),spec['easing']); j=interp(p,pose(m,nxt),t,spec['arc_bias'])
            frames.append({'j':j,'key':k,'sub':f'BRIDGE {z}/{q} -> {nxt["key_id"]}','bridge':True})
    n=len(frames); increments=[]
    for i in range(n):
        if i<6: inc=3
        elif i<10: inc=max(1,3-(i-5)//2)
        elif i<17: inc=1
        elif i<21: inc=0
        elif i<25: inc=1
        else: inc=2
        increments.append(inc)
    x=0
    for f,inc in zip(frames,increments):
        f['parent_x']=x;f['parent_inc']=inc;x+=inc
    return frames

def panel(f):
    k=f['key']; pressure='!' if 'SHOCK' in k['name'] else ':' if 'CATCH' in k['name'] or 'BRACE' in k['name'] else '='
    hdr=f"{k['key_id']} {k['name']} | {k['timing_class']} {k['timing_provenance']} | {f['sub']} | PLATFORM x={f['parent_x']} dx={f['parent_inc']}"
    return hdr+'\n'+art(f['j'],f['parent_x'],pressure)

def sheet(m):
    o=[
      'ASCII KINESIS V2 TIMING 008 - INERTIAL JOIN SPARSE REKEY REPAIR',
      f"revises: {m['revises']}",f"negative_fixture: {m['negative_fixture']}",
      'SOURCE ART: NONE | WHOLE-SHEET EVIDENCE FAMILY INHERITED | SOURCE TIMING: NONE OBSERVED',
      'TIMING: STREET_FIGHTER/CAPCOM | ONES=1 frame | TWOS=2 | FOURS=4 | 1s/2s/4s ARE CLASSES, NEVER SECONDS',
      'CLOCKS: PLATFORM_CLOCK parent transform is independent; RIDER_CLOCK rekeys only for semantic/load change.',
      'GLYPHS: O head, @ root/COM, L/R feet, # parent-clock ticker; ! shock platform, : loaded catch/brace.', ''
    ]
    for k in m['keys']:
        o += [f"[{k['key_id']}] {k['name']}",f"pose/rig={k['pose_rig']['rig_id']} | support/contact={k['support_contact']}",f"root/motion-arc={k['motion_arc_root_note']}",f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']}",f"causal_role={k['causal_role']}",f"clocks PLATFORM={k['clock_state']['PLATFORM_CLOCK']} | RIDER={k['clock_state']['RIDER_CLOCK']}",art(pose(m,k),0,'!' if 'SHOCK' in k['name'] else ':' if 'CATCH' in k['name'] or 'BRACE' in k['name'] else '='),'']
    o += ['VISIBLE PHRASE: CARRY -> COIL -> SHOCK -> CATCH -> LOADED HOLD -> OVERSHOOT -> LAG -> RECOVERY DEBT -> AFTER-DEBT CRUISE',
          'No source pixels. No traced choreography. Connective frames are deterministic same-support arcs and cannot invent semantics.']
    return '\n'.join(o).rstrip()+'\n'
def get_font(size=12):
    for fp in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'):
        try:return ImageFont.truetype(fp,size)
        except Exception:pass
    return ImageFont.load_default()
def render_png(txt,path):
    im=Image.new('RGB',(320,180),'black');d=ImageDraw.Draw(im);d.multiline_text((12,10),txt,font=get_font(7),fill='white',spacing=1);im.save(path)
def spa(m,s,v):
    vid=base64.b64encode(v).decode('ascii');pack=lambda x:base64.b64encode(gzip.compress(x.encode(),mtime=0)).decode('ascii')
    mj=json.dumps(m,separators=(',',':'),ensure_ascii=False)
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Timing 008 Repair</title><style>:root{color-scheme:dark;background:#101010;color:#eee}body{margin:1rem;font-family:system-ui}nav{display:flex;gap:.5rem}section[hidden]{display:none}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0;white-space:pre;overflow:auto;line-height:1.08}video{max-width:100%;height:auto}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="a"></pre></section><section id="json" hidden><pre id="j"></pre></section><section id="video" hidden><video controls autoplay muted loop playsinline><source src="data:video/mp4;base64,__V__" type="video/mp4"></video></section><script>const P={a:"__A__",j:"__J__"};async function u(x){const b=Uint8Array.from(atob(x),c=>c.charCodeAt(0)),d=new DecompressionStream("gzip");return new TextDecoder().decode(await new Response(new Blob([b]).stream().pipeThrough(d)).arrayBuffer())}(async()=>{a.textContent=await u(P.a);j.textContent=await u(P.j)})();const B=[...document.querySelectorAll("button[data-view]")],S=[...document.querySelectorAll("section")];B.forEach(b=>b.onclick=()=>S.forEach(s=>s.hidden=s.id!==b.dataset.view));</script></body></html>'''
    return page.replace('__V__',vid).replace('__A__',pack(s)).replace('__J__',pack(mj))
def main():
    m=json.loads(M.read_text());s=sheet(m);C.write_text(s)
    frames=timeline(m)
    with tempfile.TemporaryDirectory(prefix='akv2-t008-') as td:
        td=Path(td)
        for i,f in enumerate(frames):render_png(panel(f),td/f'f{i:03d}.png')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(m['compile']['fps']),'-i',str(td/'f%03d.png'),'-an','-c:v','libx264','-preset','veryslow','-crf','40','-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1',str(V)],check=True)
    v=V.read_bytes();m['compile'].update(video_frames_total=len(frames),media_sha256=sha(v),media_bytes=len(v),ascii_sheet_sha256=sha(s.encode()))
    M.write_text(json.dumps(m,separators=(',',':'),ensure_ascii=False)+'\n')
    H.write_text(spa(m,s,v))
    print(json.dumps({'media_sha256':sha(v),'media_bytes':len(v),'video_frames':len(frames),'ascii_sha256':sha(s.encode()),'html_sha256':sha(H.read_bytes())},sort_keys=True))
if __name__=='__main__':main()
