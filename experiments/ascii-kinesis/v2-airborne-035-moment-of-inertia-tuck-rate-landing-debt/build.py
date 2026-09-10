#!/usr/bin/env python3
from __future__ import annotations
import base64, io, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
CONTACT=HERE/'contact-sheet.txt'
VIDEO=HERE/'airborne-tool-radius-rate-landing-debt.mp4'
SPA=HERE/'airborne-tool-radius-rate-landing-debt.motion.html'
W,H=768,432
FPS=24
GROUND_Y=352
GRID_X0,GRID_Y0=42,38
SX,SY=10,12
FONT_PATH='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
FONT=ImageFont.truetype(FONT_PATH, 20)
SMALL=ImageFont.truetype(FONT_PATH, 14)

TIMING_HOLD={'ONES':1,'TWOS':2,'FOURS':4}

def pt(root, r, deg):
    a=math.radians(deg)
    return (root[0]+r*math.sin(a), root[1]-r*math.cos(a))

def limb_points(k):
    root=tuple(k['root'])
    ba=k['body_angle']
    chest=pt(root,3.1,ba)
    neck=pt(root,5.0,ba)
    head=pt(root,6.1,ba)
    shL=pt(chest,1.7,ba-90); shR=pt(chest,1.7,ba+90)
    hipL=pt(root,1.3,ba-90); hipR=pt(root,1.3,ba+90)
    eL=pt(shL,2.5,ba+k['arm_l']); eR=pt(shR,2.5,ba+k['arm_r'])
    hL=pt(eL,2.2,ba+k['fore_l']); hR=pt(eR,2.2,ba+k['fore_r'])
    kneeL=pt(hipL,3.2,ba+k['leg_l']); kneeR=pt(hipR,3.2,ba+k['leg_r'])
    footL=pt(kneeL,3.0,ba+k['shin_l']); footR=pt(kneeR,3.0,ba+k['shin_r'])
    grip=((hL[0]+hR[0])/2.0,(hL[1]+hR[1])/2.0)
    ta=k['tool_angle']
    tail=pt(grip,1.7,ta+180); headT=pt(grip,3.8,ta)
    return dict(root=root,chest=chest,neck=neck,head=head,shL=shL,shR=shR,eL=eL,eR=eR,hL=hL,hR=hR,hipL=hipL,hipR=hipR,kneeL=kneeL,kneeR=kneeR,footL=footL,footR=footR,tool_tail=tail,tool_head=headT,tool_center=grip,tool_grip=grip)

def interp(a,b,t): return a+(b-a)*t

def ease(t, kind):
    if kind=='snap': return t*t*(3-2*t)
    if kind=='ease_in': return t*t
    if kind=='ease_out': return 1-(1-t)*(1-t)
    if kind=='hold_then_go': return 0 if t<0.25 else (t-0.25)/0.75
    return t

def interpolate_key(a,b,t):
    t=ease(t,b.get('incoming_ease','smooth'))
    out={}
    numeric=['body_angle','arm_l','arm_r','fore_l','fore_r','leg_l','leg_r','shin_l','shin_r','tool_angle']
    out['root']=[interp(a['root'][0],b['root'][0],t),interp(a['root'][1],b['root'][1],t)]
    for f in numeric: out[f]=interp(a[f],b[f],t)
    out['support_contact']=a['support_contact'] if t<1 else b['support_contact']
    out['contact']=a['contact'] if t<1 else b['contact']
    out['key_id']=f"{a['key_id']}->{b['key_id']}"
    out['name']=b['name']
    return out

def grid_to_px(p): return (GRID_X0+p[0]*SX, GRID_Y0+p[1]*SY)

def draw_seg(draw,p1,p2,ch='/',width=2):
    a=grid_to_px(p1); b=grid_to_px(p2)
    draw.line([a,b],fill=(232,232,232),width=width)

def draw_pose(draw,k, label=''):
    p=limb_points(k)
    draw_seg(draw,p['root'],p['chest'],'|',3); draw_seg(draw,p['chest'],p['neck'],'|',3)
    draw_seg(draw,p['shL'],p['eL'],3); draw_seg(draw,p['eL'],p['hL'],3)
    draw_seg(draw,p['shR'],p['eR'],3); draw_seg(draw,p['eR'],p['hR'],3)
    draw_seg(draw,p['hipL'],p['kneeL'],3); draw_seg(draw,p['kneeL'],p['footL'],3)
    draw_seg(draw,p['hipR'],p['kneeR'],3); draw_seg(draw,p['kneeR'],p['footR'],3)
    draw_seg(draw,p['hL'],p['tool_grip'],2); draw_seg(draw,p['hR'],p['tool_grip'],2)
    draw_seg(draw,p['tool_tail'],p['tool_head'],4)
    th=grid_to_px(p['tool_head']); tt=grid_to_px(p['tool_tail'])
    draw.text((th[0]-12,th[1]-12),'[@]',font=FONT,fill=(240,240,240))
    draw.text((tt[0]-6,tt[1]-10),'=',font=FONT,fill=(220,220,220))
    hp=grid_to_px(p['head']); rp=grid_to_px(p['root'])
    draw.text((hp[0]-7,hp[1]-11),'O',font=FONT,fill=(255,255,255))
    draw.text((rp[0]-7,rp[1]-10),'P',font=FONT,fill=(255,255,255))
    for nm in ('hL','hR'):
        q=grid_to_px(p[nm]); draw.text((q[0]-5,q[1]-8),'o',font=SMALL,fill=(220,220,220))
    for nm in ('footL','footR'):
        q=grid_to_px(p[nm]); draw.text((q[0]-5,q[1]-8),'!',font=SMALL,fill=(235,235,235))
    draw.line([(35,GROUND_Y),(735,GROUND_Y)],fill=(115,115,115),width=2)
    if k.get('support_contact','NONE')!='NONE':
        for nm in ('footL','footR'):
            if (('LEFT' in k['support_contact'] and nm=='footL') or ('RIGHT' in k['support_contact'] and nm=='footR') or k['support_contact'] in ('BOTH','BOTH_WIDE')):
                q=grid_to_px(p[nm]); draw.line([(q[0]-12,GROUND_Y-1),(q[0]+12,GROUND_Y-1)],fill=(245,245,245),width=3)
    draw.text((24,12), label, font=SMALL, fill=(210,210,210))

def render_frame(k,label):
    im=Image.new('RGB',(W,H),(8,8,10)); d=ImageDraw.Draw(im)
    d.arc((80,65,650,330),190,350,fill=(38,38,44),width=1)
    draw_pose(d,k,label)
    return im

def ascii_frame(k,cols=64,rows=24):
    p=limb_points(k)
    canvas=[[' ']*cols for _ in range(rows)]
    def put(x,y,ch):
        x=int(round(x)); y=int(round(y))
        if 0<=x<cols and 0<=y<rows: canvas[y][x]=ch
    def seg(a,b,ch):
        x1,y1=a; x2,y2=b; n=max(1,int(max(abs(x2-x1),abs(y2-y1))*2))
        for i in range(n+1):
            t=i/n; x=x1+(x2-x1)*t; y=y1+(y2-y1)*t; put(x,y,ch)
    xoff=-4; yoff=0
    def q(v): return (v[0]+xoff,v[1]+yoff)
    seg(q(p['root']),q(p['chest']),'|'); seg(q(p['chest']),q(p['neck']),'|')
    seg(q(p['shL']),q(p['eL']),'/'); seg(q(p['eL']),q(p['hL']),'/')
    seg(q(p['shR']),q(p['eR']),'\\'); seg(q(p['eR']),q(p['hR']),'\\')
    seg(q(p['hipL']),q(p['kneeL']),'/'); seg(q(p['kneeL']),q(p['footL']),'/')
    seg(q(p['hipR']),q(p['kneeR']),'\\'); seg(q(p['kneeR']),q(p['footR']),'\\')
    seg(q(p['hL']),q(p['tool_grip']),'o'); seg(q(p['hR']),q(p['tool_grip']),'o'); seg(q(p['tool_tail']),q(p['tool_head']),'=')
    for nm,ch in [('head','O'),('root','P'),('hL','o'),('hR','o'),('footL','!'),('footR','!')]: put(*(q(p[nm])),ch)
    th=q(p['tool_head']); put(th[0],th[1],'@')
    gy=rows-2
    for x in range(cols): canvas[gy][x]='_'
    lines=[''.join(r).rstrip() for r in canvas]
    return '\n'.join(line.ljust(cols) for line in lines)

def build_contact(m):
    chunks=[]
    chunks.append('ASCII KINESIS V2 — AIRBORNE035 — MOMENT-OF-INERTIA TUCK/RATE LANDING DEBT')
    chunks.append('Legend: O=head P=pelvis o=hand !=foot @=weighted tool head ==rigid shaft _=ground  Facing/rightward travel =>')
    chunks.append('Source art is NOT present. Every drawing below is an independent abstract ASCII rig key.')
    for k in m['keys']:
        chunks += ['', f"{k['key_id']}  {k['name']}  timing={k['timing_class']}  provenance={k['timing_provenance']}", f"support={k['support_contact']}  contact={k['contact']}  root={k['motion_arc_root_note']}", f"causal_role={k['causal_role']}", ascii_frame(k)]
    chunks += ['', 'POCKET RULE: radius changes may change rotation RATE while external support/contact remains NONE; they do not mint a new root impulse.', 'LANDING DEBT: right-toe catch -> unilateral crush -> delayed left-foot catch -> tool/torso overshoot -> displaced settle.']
    return '\n'.join(chunks)+'\n'

def encode_video(frames):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,im in enumerate(frames): im.save(td/f'f{i:04d}.png',compress_level=9)
        cmd=['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(td/'f%04d.png'),'-an','-c:v','libx264','-preset','veryslow','-crf','35','-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1','-fflags','+bitexact','-flags:v','+bitexact',str(VIDEO)]
        subprocess.run(cmd,check=True)

def build_video(m):
    keys=m['keys']; frames=[]
    for i,k in enumerate(keys):
        hold=TIMING_HOLD[k['timing_class']]
        for h in range(hold): frames.append(render_frame(k,f"{k['key_id']}  {k['name']}  hold {h+1}/{hold}"))
        if i < len(keys)-1:
            b=keys[i+1]; n=k['transition_frames']
            for j in range(1,n+1):
                t=j/(n+1)
                frames.append(render_frame(interpolate_key(k,b,t),f"{k['key_id']} -> {b['key_id']}  connective {j}/{n}"))
    encode_video(frames)
    return len(frames)

def make_spa(m,contact):
    import gzip
    media=VIDEO.read_bytes(); b64=base64.b64encode(media).decode("ascii")
    js=json.dumps(m,indent=2,ensure_ascii=False)
    a64=base64.b64encode(gzip.compress(contact.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    j64=base64.b64encode(gzip.compress(js.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    head=("<!doctype html><html><head><meta charset=\"utf-8\"><title>"+m["experiment_id"]+"</title><style>" "body{background:#09090b;color:#eee;font-family:system-ui;margin:0}nav{position:sticky;top:0;background:#111;padding:10px}" "button{margin-right:8px;padding:8px 14px}section{display:none;padding:16px}section.active{display:block}" "pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.02}" "video{max-width:100%;background:#000}</style></head><body>")
    nav=("<nav><button data-view=\"ascii\">ASCII</button><button data-view=\"json\">JSON</button><button data-view=\"video\">VIDEO</button></nav>" "<section id=\"ascii\" class=\"active\"><pre>loading exact persisted ASCII...</pre></section>" "<section id=\"json\"><pre>loading exact persisted JSON...</pre></section>" "<section id=\"video\"><video controls autoplay loop muted playsinline><source src=\"data:video/mp4;base64,"+b64+"\" type=\"video/mp4\"></video></section>")
    script=("<script>const PAYLOAD={ascii:'"+a64+"',json:'"+j64+"'};" "async function gunzip64(s){const raw=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream('gzip');return new TextDecoder().decode(await new Response(new Blob([raw]).stream().pipeThrough(ds)).arrayBuffer())}" "Promise.all([gunzip64(PAYLOAD.ascii),gunzip64(PAYLOAD.json)]).then(([a,j])=>{document.querySelector('#ascii pre').textContent=a;document.querySelector('#json pre').textContent=j});" "for(const b of document.querySelectorAll('button[data-view]'))b.onclick=()=>{for(const s of document.querySelectorAll('section'))s.classList.remove('active');document.getElementById(b.dataset.view).classList.add('active')};</script></body></html>")
    return head+nav+script

def main():
    m=json.loads(MOTION.read_text())
    contact=build_contact(m); CONTACT.write_text(contact)
    n=build_video(m); m['compile']['frames']=n
    import hashlib
    media=VIDEO.read_bytes(); m['media'].update({'frames':n,'bytes':len(media),'sha256':hashlib.sha256(media).hexdigest()})
    MOTION.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
    contact=build_contact(m); CONTACT.write_text(contact)
    SPA.write_text(make_spa(m,contact))
    print(json.dumps({'frames':n,'bytes':len(media),'sha256':hashlib.sha256(media).hexdigest()}))
if __name__=='__main__': main()
