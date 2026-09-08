#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D=Path(__file__).resolve().parent
M=D/'motion.json'
C=D/'contact-sheet.txt'
V=D/'clock-rendezvous-reacquire-repair.motion.mp4'
H=D/'clock-rendezvous-reacquire-repair.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
GW,GH=52,22
W,HPIX=800,450
GROUND=20
MARK={'root':'@','chest':'+','head':'O','left_shoulder':'o','left_elbow':'o','left_hand':'a',
      'right_shoulder':'o','right_elbow':'o','right_hand':'b','left_hip':'o','left_knee':'o',
      'left_foot':'L','right_hip':'o','right_knee':'o','right_foot':'R'}

def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()

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

def resolved(m,k):
    names=m['rig_schema']['joint_order']
    j={n:list(k['pose_rig']['coords'][i]) for i,n in enumerate(names)}
    j['object_token']=list(k['pose_rig']['object_token'])
    return j

def ease(t,name):
    if name=='EASE_IN': return t*t
    if name=='EASE_OUT': return 1-(1-t)*(1-t)
    if name=='SMOOTHSTEP': return t*t*(3-2*t)
    return t

def quad(p,q,t,bias,mag):
    cx=(p[0]+q[0])/2+bias[0]*mag
    cy=(p[1]+q[1])/2+bias[1]*mag
    u=1-t
    return [round(u*u*p[0]+2*u*t*cx+t*t*q[0]), round(u*u*p[1]+2*u*t*cy+t*t*q[1])]

def interpolate(a,b,t,bias,obj_bias):
    out={}
    for n,p in a.items():
        q=b[n]
        if n=='object_token':
            out[n]=quad(p,q,t,obj_bias,2.4)
        else:
            mag=2.1 if ('hand' in n or 'head' in n) else 1.6 if ('elbow' in n or 'knee' in n) else 1.0
            out[n]=quad(p,q,t,bias,mag)
    return out

def art(m,state,key):
    links=[tuple(x) for x in m['rig_schema']['links']]
    g=[[' ']*GW for _ in range(GH)]
    def put(x,y,c):
        if 0<=x<GW and 0<=y<GH: g[y][x]=c
    j={n:tuple(state[n]) for n in m['rig_schema']['joint_order']}
    for a,b in links:
        for x,y in bline(j[a],j[b])[1:-1]:
            if 0<=x<GW and 0<=y<GH and g[y][x]==' ': put(x,y,glyph(j[a],j[b]))
    for n,(x,y) in j.items(): put(x,y,MARK[n])
    ox,oy=state['object_token']; put(ox,oy,'*')
    for x in range(4,48):
        if g[GROUND][x]==' ': put(x,GROUND,'_')
    put(42,6,'|'); put(42,7,'|'); put(42,8,'|')
    return '\n'.join(''.join(r).rstrip() for r in g)

def timeline(m):
    frames=[]
    keys=m['keys']
    for i,k in enumerate(keys):
        p=resolved(m,k)
        h=HOLD[k['timing_class']]
        for n in range(h):
            frames.append({'state':p,'key':k,'kind':'HOLD','detail':f'{n+1}/{h}'})
        if i==len(keys)-1: continue
        nxt=keys[i+1]; spec=k['bridge_to_next']; q=int(spec['frames'])
        if q:
            if k['support_topology'] != nxt['support_topology']:
                raise SystemExit(f"bridge crosses support topology: {k['key_id']}->{nxt['key_id']}")
            if k['contact_topology'] != nxt['contact_topology']:
                raise SystemExit(f"bridge crosses contact topology: {k['key_id']}->{nxt['key_id']}")
            a=p; b=resolved(m,nxt)
            for z in range(1,q+1):
                t=ease(z/(q+1),spec['easing'])
                frames.append({'state':interpolate(a,b,t,spec['arc_bias'],spec['object_arc_bias']),
                               'key':k,'kind':'ARC','detail':f'{z}/{q}->{nxt["key_id"]}'})
    return frames

def key_block(m,k):
    state=resolved(m,k)
    lines=[
      f"[{k['key_id']}] {k['name']}",
      f"pose/rig={k['pose_rig']['rig_id']} | changed_channels={k['changed_channels']}",
      f"support/contact={k['support_contact']} | support_topology={k['support_topology']} | contact_topology={k['contact_topology']}",
      f"root/motion-arc={k['motion_arc_root_note']}",
      f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']} | policy=STREET_FIGHTER/CAPCOM",
      f"causal_role={k['causal_role']}",
      f"clocks BODY={k['clock_state']['BODY_CLOCK']} | OBJECT={k['clock_state']['OBJECT_CLOCK']}",
    ]
    if 'causal_join' in k:
        j=k['causal_join']
        lines.append(f"causal_join={j.get('join_id',j.get('event_id'))} | sync_scope={','.join(j['sync_scope'])} | relation={j['relationship_change']}")
    lines += [art(m,state,k),'']
    return lines

def sheet(m):
    out=[
      'ASCII KINESIS V2 TIMING 009 - CLOCK RENDEZVOUS / REACQUIRE REPAIR',
      f"revises: {m['revises']}",
      f"negative_fixture: {m['negative_fixture']}",
      'SOURCE ART: NONE | TSR ASSET 3116 EVIDENCE FAMILY INHERITED | SOURCE TIMING: NONE OBSERVED',
      'TIMING: STREET_FIGHTER/CAPCOM | ONES=1 display frame | TWOS=2 | FOURS=4 | 1s/2s/4s ARE CLASSES, NEVER SECONDS',
      'CLOCKS: BODY_CLOCK and OBJECT_CLOCK diverge after release; K08 is the only rendezvous/catch sync join.',
      'GLYPHS: O head, @ COM/root, L/R feet, a/b hands, * detached generic phase token, | abstract phase gate.',
      'VISIBLE PHRASE: OFFSET READY -> ASYM COIL -> RELEASE -> ACCELERATE -> BRAKE -> BODY HOLD/OBJECT TURN -> RENDEZVOUS COIL -> PRE-CATCH -> CONTACT -> ABSORB -> OVERSHOOT -> RECOVERY DEBT -> NEW READY',
      ''
    ]
    for k in m['keys']: out.extend(key_block(m,k))
    out += [
      'RIGHTS FIREWALL: no source pixels, palette, contours, layout, tracing, choreography, redistribution, or close imitation.',
      'CONNECTIVE MOTION: deterministic authored arcs only; support/contact changes snap at decisive keys and cannot be invented by interpolation.',
    ]
    return '\n'.join(out).rstrip()+'\n'

def frame_text(m,f,idx,total):
    k=f['key']
    return '\n'.join([
      f"ASCII KINESIS TIMING 009  frame {idx+1:02d}/{total:02d}",
      f"{k['key_id']} {k['name']} | {k['timing_class']} {k['timing_provenance']} | {f['kind']} {f['detail']}",
      f"BODY={k['clock_state']['BODY_CLOCK']} | OBJECT={k['clock_state']['OBJECT_CLOCK']} | changed={k['changed_channels']}",
      f"support={k['support_topology']} | contact={k['contact_topology']}",
      '',
      art(m,f['state'],k)
    ])

def get_font(size=14):
    for fp in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'):
        try: return ImageFont.truetype(fp,size)
        except Exception: pass
    return ImageFont.load_default()

def render_png(text,path):
    im=Image.new('RGB',(W,HPIX),'black')
    d=ImageDraw.Draw(im)
    d.multiline_text((18,14),text,font=get_font(14),fill='white',spacing=2)
    im.save(path)

def spa(m,s,v):
    vid=base64.b64encode(v).decode('ascii')
    js=json.dumps(m,indent=2,ensure_ascii=False)
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Timing 009 Repair</title><style>:root{color-scheme:dark;background:#0f0f0f;color:#eee}body{margin:1rem;font-family:system-ui}nav{display:flex;gap:.5rem;position:sticky;top:0;background:#0f0f0f;padding:.4rem 0}section[hidden]{display:none}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0;white-space:pre;overflow:auto;line-height:1.08}video{max-width:100%;height:auto}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre>__ASCII__</pre></section><section id="json" hidden><pre>__JSON__</pre></section><section id="video" hidden><video controls autoplay muted loop playsinline><source src="data:video/mp4;base64,__VIDEO__" type="video/mp4"></video></section><script>const B=[...document.querySelectorAll("button[data-view]")],S=[...document.querySelectorAll("section")];B.forEach(b=>b.onclick=()=>S.forEach(s=>s.hidden=s.id!==b.dataset.view));</script></body></html>'''
    return page.replace('__ASCII__',html.escape(s)).replace('__JSON__',html.escape(js)).replace('__VIDEO__',vid)

def main():
    m=json.loads(M.read_text(encoding='utf-8'))
    s=sheet(m); C.write_text(s,encoding='utf-8')
    frames=timeline(m)
    with tempfile.TemporaryDirectory(prefix='akv2-t009-') as td:
        td=Path(td)
        for i,f in enumerate(frames): render_png(frame_text(m,f,i,len(frames)),td/f'f{i:03d}.png')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(m['compile']['fps']),
                        '-i',str(td/'f%03d.png'),'-an','-c:v','libx264','-preset','veryslow','-crf','30',
                        '-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1',str(V)],check=True)
    v=V.read_bytes()
    m['compile'].update(video_frames_total=len(frames),media_sha256=sha(v),media_bytes=len(v),ascii_sheet_sha256=sha(s.encode()))
    M.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    H.write_text(spa(m,s,v),encoding='utf-8')
    print(json.dumps({'video_frames_total':len(frames),'media_sha256':sha(v),'media_bytes':len(v),
                      'ascii_sheet_sha256':sha(s.encode()),'html_sha256':sha(H.read_bytes())},sort_keys=True))
if __name__=='__main__': main()
