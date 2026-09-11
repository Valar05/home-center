#!/usr/bin/env python3
import json, math, base64, hashlib, subprocess, tempfile, html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
CONTACT=HERE/'contact-sheet.txt'
SPA=HERE/'control-phase-seize-landing-brace-debt.motion.html'
MP4=HERE/'_authoritative.mp4'
DELIVERY=HERE/'_delivery.mp4'
W,H,FPS=800,448,24
FONT_PATH='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
FONT=ImageFont.truetype(FONT_PATH,21)
SMALL=ImageFont.truetype(FONT_PATH,14)
TINY=ImageFont.truetype(FONT_PATH,11)
GROUND_Y=374

def world_to_px(root):
    return 65+float(root[0])*7.35, 90+float(root[1])*7.2

def segment_char(dx,dy):
    if abs(dx)<2: return '|'
    if abs(dy)<2: return '-'
    return '\\' if dx*dy>0 else '/'

def draw_char_segment(d,a,b,font=FONT,fill='black',steps=None):
    ax,ay=a; bx,by=b
    dist=math.hypot(bx-ax,by-ay)
    n=steps or max(2,int(dist/13))
    ch=segment_char(bx-ax,by-ay)
    for i in range(1,n):
        t=i/n
        x=ax+(bx-ax)*t; y=ay+(by-ay)*t
        d.text((x-6,y-11),ch,font=font,fill=fill)

def pose_geometry(root,key):
    px,py=world_to_px(root)
    pose=key['pose']; lean=float(key.get('lean',0))*3.5
    head=(px+lean,py-43)
    neck=(px+lean*0.7,py-26)
    pelvis=(px,py)
    shoulderL=(neck[0]-13,neck[1]+5); shoulderR=(neck[0]+13,neck[1]+5)
    kneeL=(px-14,py+19); kneeR=(px+15,py+17)
    footL=(px-26,py+42); footR=(px+29,py+42)
    handL=(px-33+lean,py-5); handR=(px+34+lean,py-2)

    if pose=='load':
        handL=(px-37,py-1); handR=(px+29,py-10)
        kneeL=(px-18,py+19); kneeR=(px+12,py+20)
        footL=(px-37,GROUND_Y); footR=(px+31,GROUND_Y)
    elif pose=='launch':
        handL=(px-28,py-18); handR=(px+35,py-23)
        kneeL=(px-8,py+20); kneeR=(px+18,py+16)
    elif pose=='ascent':
        handL=(px-37,py-25); handR=(px+23,py-8)
        kneeL=(px-19,py+14); kneeR=(px+15,py+22)
    elif pose=='apex':
        handL=(px-40,py-20); handR=(px+40,py-18)
        kneeL=(px-12,py+23); kneeR=(px+13,py+22)
    elif pose=='descent_a':
        handL=(px-31,py-1); handR=(px+36,py-19)
        kneeL=(px-19,py+18); kneeR=(px+11,py+24)
    elif pose=='descent_b':
        handL=(px-37,py-22); handR=(px+29,py-2)
        kneeL=(px-10,py+25); kneeR=(px+20,py+17)
    elif pose=='descent_c':
        handL=(px-25,py-30); handR=(px+40,py-9)
        kneeL=(px-17,py+15); kneeR=(px+17,py+23)
    elif pose=='seize':
        handL=(px-16,py-31); handR=(px+31,py+1)
        kneeL=(px-20,py+17); kneeR=(px+18,py+21)
    elif pose=='brace':
        handL=(px-20,py+4); handR=(px+24,py+6)
        kneeL=(px-15,py+25); kneeR=(px+18,py+24)
        footL=(px-27,py+44); footR=(px+31,py+43)
    elif pose=='precontact':
        handL=(px-22,py+8); handR=(px+22,py+5)
        kneeL=(px-16,py+20); kneeR=(px+18,py+18)
        footL=(px-27,GROUND_Y-13); footR=(px+31,GROUND_Y-4)
    elif pose=='right_catch':
        handL=(px-16,py+8); handR=(px+30,py+2)
        kneeL=(px-18,py+14); kneeR=(px+18,py+8)
        footL=(px-31,GROUND_Y-11); footR=(px+32,GROUND_Y)
    elif pose=='crush':
        head=(px+lean,py-35); neck=(px+lean*0.7,py-19)
        shoulderL=(neck[0]-13,neck[1]+5); shoulderR=(neck[0]+13,neck[1]+5)
        handL=(px-8,py+9); handR=(px+36,py+8)
        kneeL=(px-17,py+8); kneeR=(px+14,py+6)
        footL=(px-32,GROUND_Y-8); footR=(px+31,GROUND_Y)
    elif pose=='both_catch':
        handL=(px-8,py+4); handR=(px+32,py+4)
        kneeL=(px-17,py+8); kneeR=(px+15,py+8)
        footL=(px-32,GROUND_Y); footR=(px+31,GROUND_Y)
    elif pose=='rebound':
        head=(px+lean,py-47); neck=(px+lean*0.7,py-29)
        shoulderL=(neck[0]-13,neck[1]+5); shoulderR=(neck[0]+13,neck[1]+5)
        handL=(px-37,py-12); handR=(px+18,py-22)
        kneeL=(px-17,py+15); kneeR=(px+15,py+14)
        footL=(px-34,GROUND_Y); footR=(px+31,GROUND_Y)
    elif pose=='settle':
        handL=(px-23,py-4); handR=(px+29,py-7)
        kneeL=(px-18,py+12); kneeR=(px+15,py+13)
        footL=(px-34,GROUND_Y); footR=(px+31,GROUND_Y)
    elif pose=='final':
        handL=(px-24,py-8); handR=(px+25,py-8)
        kneeL=(px-17,py+12); kneeR=(px+16,py+12)
        footL=(px-34,GROUND_Y); footR=(px+32,GROUND_Y)

    return dict(px=px,py=py,head=head,neck=neck,pelvis=pelvis,shoulderL=shoulderL,shoulderR=shoulderR,
                handL=handL,handR=handR,kneeL=kneeL,kneeR=kneeR,footL=footL,footR=footR)

def controller_tip(g,key):
    angle=float(key['local_control']['pivot_deg'])
    rad=math.radians(angle)
    pivot=(g['neck'][0]-11,g['neck'][1]+13)
    length=78
    tip=(pivot[0]+math.cos(rad)*length,pivot[1]+math.sin(rad)*length)
    return pivot,tip

def render_frame(root,key):
    im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im)
    d.line((28,GROUND_Y,W-28,GROUND_Y),fill='black',width=2)
    for x in range(34,W-30,34): d.text((x,GROUND_Y+3),'_',font=TINY,fill='black')
    g=pose_geometry(root,key)
    d.text((g['head'][0]-6,g['head'][1]-12),'o',font=FONT,fill='black')
    d.text((g['neck'][0]-6,g['neck'][1]-12),'|',font=FONT,fill='black')
    d.text((g['pelvis'][0]-6,g['pelvis'][1]-12),'+',font=FONT,fill='black')
    for a,b in [(g['shoulderL'],g['handL']),(g['shoulderR'],g['handR']),
                (g['neck'],g['pelvis']),(g['pelvis'],g['kneeL']),(g['kneeL'],g['footL']),
                (g['pelvis'],g['kneeR']),(g['kneeR'],g['footR'])]:
        draw_char_segment(d,a,b)
    for pt,ch in [(g['handL'],'x'),(g['handR'],'x'),(g['footL'],'_'),(g['footR'],'_')]:
        d.text((pt[0]-6,pt[1]-12),ch,font=FONT,fill='black')

    pivot,tip=controller_tip(g,key)
    d.text((pivot[0]-6,pivot[1]-12),'+',font=FONT,fill='black')
    draw_char_segment(d,pivot,tip)
    d.text((tip[0]-6,tip[1]-12),'@',font=FONT,fill='black')
    phase=key['local_control']['phase']
    if phase in ('A','B','C'):
        d.text((tip[0]+8,tip[1]-12),phase,font=SMALL,fill='black')
    elif phase=='C*':
        d.text((tip[0]+8,tip[1]-12),'!',font=SMALL,fill='black')

    sc=key['support_contact']
    if sc=='BOTH_FEET_GROUND':
        d.text((g['footL'][0]-8,GROUND_Y-18),'*',font=FONT,fill='black')
        d.text((g['footR'][0]-8,GROUND_Y-18),'*',font=FONT,fill='black')
    elif 'RIGHT' in sc:
        d.text((g['footR'][0]-8,GROUND_Y-18),'*',font=FONT,fill='black')

    d.text((20,14),'AIRBORNE040 :: LOCAL CONTROL PHASE SEIZE -> LANDING BRACE DEBT',font=SMALL,fill='black')
    d.text((20,35),f"{key['key_id']}  {key['label']}",font=SMALL,fill='black')
    d.text((20,H-54),f"support={sc}   local={key['local_control']['state']} phase={phase}",font=TINY,fill='black')
    d.text((20,H-39),f"root=({root[0]:.1f},{root[1]:.1f})  force={key['force']}",font=TINY,fill='black')
    d.text((20,H-24),f"timing={key['timing_class']} / {key['timing_provenance']}   clock={key['local_control']['clock']}",font=TINY,fill='black')
    return im

def quad(p0,p1,pc,t):
    u=1-t
    return (u*u*p0[0]+2*u*t*pc[0]+t*t*p1[0],
            u*u*p0[1]+2*u*t*pc[1]+t*t*p1[1])

def compile_frames(m):
    frames=[]; ks=m['keys']
    for i,k in enumerate(ks):
        for _ in range(k['hold_frames']): frames.append(render_frame(k['root'],k))
        if i+1<len(ks):
            n=k['bridge_frames']; nxt=ks[i+1]
            for j in range(1,n+1):
                t=j/(n+1)
                s=t*t*(3-2*t)
                frames.append(render_frame(quad(k['root'],nxt['root'],k['bridge_control'],s),k))
    return frames

def put(g,x,y,ch):
    if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=ch

def grid_segment(g,a,b):
    ax,ay=a; bx,by=b; n=max(2,int(max(abs(bx-ax),abs(by-ay))*1.5))
    ch=segment_char(bx-ax,by-ay)
    for i in range(1,n):
        t=i/n; put(g,round(ax+(bx-ax)*t),round(ay+(by-ay)*t),ch)

def ascii_frame(k,w=104,h=42):
    g=[[' ']*w for _ in range(h)]; gy=38
    for x in range(w): g[gy][x]='_'
    rx=max(12,min(w-12,int(k['root'][0]))); ry=max(5,min(gy-7,int(k['root'][1]*0.78)))
    head=(rx,ry-5); neck=(rx,ry-3); pelvis=(rx,ry)
    pose=k['pose']
    handL=(rx-5,ry-1); handR=(rx+5,ry-1); kneeL=(rx-2,ry+2); kneeR=(rx+2,ry+2)
    footL=(rx-4,ry+5); footR=(rx+4,ry+5)
    if pose in ('load','settle','final'): footL=(rx-5,gy-1); footR=(rx+5,gy-1)
    if pose=='precontact': footL=(rx-4,gy-3); footR=(rx+4,gy-2)
    if pose in ('right_catch','crush'): footL=(rx-5,gy-2); footR=(rx+5,gy-1)
    if pose in ('both_catch','rebound'): footL=(rx-5,gy-1); footR=(rx+5,gy-1)
    if pose=='ascent': handL=(rx-5,ry-3); handR=(rx+4,ry-1)
    if pose=='apex': handL=(rx-6,ry-2); handR=(rx+6,ry-2)
    if pose=='descent_a': handL=(rx-5,ry); handR=(rx+5,ry-2)
    if pose=='descent_b': handL=(rx-5,ry-2); handR=(rx+5,ry)
    if pose=='descent_c': handL=(rx-4,ry-3); handR=(rx+6,ry-1)
    if pose=='seize': handL=(rx-2,ry-4); handR=(rx+5,ry)
    if pose=='brace': handL=(rx-3,ry+1); handR=(rx+3,ry+1)
    put(g,*head,'o'); put(g,*neck,'|'); put(g,*pelvis,'+')
    for a,b in [(neck,pelvis),((rx-1,ry-3),handL),((rx+1,ry-3),handR),(pelvis,kneeL),(kneeL,footL),(pelvis,kneeR),(kneeR,footR)]:
        grid_segment(g,a,b)
    put(g,*handL,'x'); put(g,*handR,'x'); put(g,*footL,'_'); put(g,*footR,'_')
    angle=math.radians(float(k['local_control']['pivot_deg']))
    piv=(rx-1,ry-2); tip=(round(piv[0]+math.cos(angle)*10),round(piv[1]+math.sin(angle)*5.5))
    put(g,*piv,'+'); grid_segment(g,piv,tip); put(g,*tip,'@')
    ph=k['local_control']['phase']; put(g,min(w-1,tip[0]+1),tip[1], '!' if ph=='C*' else (ph if ph in 'ABC' else 'N'))
    sc=k['support_contact']
    if sc=='BOTH_FEET_GROUND':
        put(g,footL[0],gy-1,'*'); put(g,footR[0],gy-1,'*')
    elif 'RIGHT' in sc: put(g,footR[0],gy-1,'*')
    return '\n'.join(''.join(r).rstrip() for r in g)

def make_contact(m):
    parts=[
      'ASCII KINESIS V2 - AIRBORNE040',
      'LOCAL_CONTROL_PHASE_SEIZE_LANDING_BRACE_DEBT',
      'SOURCE EVIDENCE: TSR asset 52290 - Dixie Kong - Donkey Kong Country 3 - SNES - commissioned evidence 1FVCu-OOy4fvhMpNUMJtiF7yobfKqcfJ3OXWELI6rHkw',
      'SOURCE TIMING: UNKNOWN. ALL DECISIVE COMPILE TIMING BELOW: INFERRED / STREET_FIGHTER-CAPCOM.',
      'RIGHTS: source evidence only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/close imitation.',
      'CONTROL LAW: generic hinged vane cycles A -> B -> C locally while BODY_ROOT/SUPPORT_CLOCK continue independently.',
      'SEIZE LAW: local control is arrested off-neutral at C* before contact; root descent continues; C* becomes landing-brace authority instead of resetting.',
      'LANDING LAW: separated precontact -> unilateral right catch -> impact overshoot -> delayed left support -> counterswing -> displaced final rest.',
      ''
    ]
    for k in m['keys']:
        parts += [
          '='*104,
          f"{k['key_id']} :: {k['label']}",
          f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']} | causal_role={k['causal_role']}",
          f"support_contact={k['support_contact']} | eligibility={k['contact_eligibility']}",
          f"root={k['root']} | force={k['force']}",
          f"local_control={k['local_control']}",
          f"clock_ownership={k['clock_ownership']}",
          ascii_frame(k),''
        ]
    return '\n'.join(parts).rstrip()+'\n'

def encode_mp4(frames,out,w=W,h=H,crf=28):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,im in enumerate(frames):
            if im.size!=(w,h): im=im.resize((w,h),Image.Resampling.LANCZOS)
            im.save(td/f'f{i:04d}.png',compress_level=9)
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(td/'f%04d.png'),
             '-c:v','libx264','-preset','veryslow','-crf',str(crf),'-pix_fmt','yuv420p','-movflags','+faststart',
             '-metadata','encoder=ASCII-Kinesis-V2',str(out)]
        subprocess.run(cmd,check=True)

def make_spa(contact,m,delivery_bytes):
    b64=base64.b64encode(delivery_bytes).decode('ascii')
    mtxt=json.dumps(m,indent=2,ensure_ascii=False)+'\n'
    css="body{font-family:system-ui;margin:0;background:#fff;color:#111}nav{position:sticky;top:0;background:#fff;border-bottom:1px solid #999;padding:10px}button{font:inherit;margin-right:8px;padding:7px 14px}section{display:none;padding:14px}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:'liga' 0,'calt' 0;white-space:pre;overflow:auto;line-height:1.08;border:1px solid #999;padding:12px}video{max-width:100%;width:640px;background:#000}"
    js="document.querySelectorAll('button[data-view]').forEach(b=>b.onclick=()=>{document.querySelectorAll('section').forEach(s=>s.classList.remove('active'));document.getElementById(b.dataset.view).classList.add('active')})"
    return f'<!doctype html><html><head><meta charset="utf-8"><title>Airborne040</title><style>{css}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre>{html.escape(contact)}</pre></section><section id="json"><pre>{html.escape(mtxt)}</pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section><script>{js}</script></body></html>'

def main():
    m=json.loads(MOTION.read_text(encoding='utf-8'))
    contact=make_contact(m); CONTACT.write_text(contact,encoding='utf-8')
    frames=compile_frames(m)
    encode_mp4(frames,MP4,W,H,28)
    delivery_frames=[im.resize((640,358),Image.Resampling.LANCZOS) for im in frames]
    encode_mp4(delivery_frames,DELIVERY,640,358,30)
    media=MP4.read_bytes(); delivery=DELIVERY.read_bytes()
    SPA.write_text(make_spa(contact,m,delivery),encoding='utf-8')
    print(json.dumps({
      'frames':len(frames),
      'authoritative_bytes':len(media),'authoritative_sha256':hashlib.sha256(media).hexdigest(),
      'delivery_bytes':len(delivery),'delivery_sha256':hashlib.sha256(delivery).hexdigest(),
      'contact_bytes':len(CONTACT.read_bytes()),'spa_bytes':len(SPA.read_bytes())
    },indent=2))
if __name__=='__main__': main()
