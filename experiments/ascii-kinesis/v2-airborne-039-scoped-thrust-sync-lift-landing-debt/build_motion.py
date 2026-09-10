#!/usr/bin/env python3
import json, math, base64, hashlib, subprocess, tempfile, html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
CONTACT=HERE/'contact-sheet.txt'
SPA=HERE/'scoped-thrust-sync-lift-landing-debt.motion.html'
MP4=HERE/'_authoritative.mp4'
W,H,FPS=800,448,24
FONT_PATH='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
FONT=ImageFont.truetype(FONT_PATH,22)
SMALL=ImageFont.truetype(FONT_PATH,14)
TINY=ImageFont.truetype(FONT_PATH,11)
GROUND_Y=374

def pose_lines(pose,A,B,lean=0):
    fireA='///' if 'PULSE' in A else (' / ' if A=='PREP' else '   ')
    fireB=('\\'*3) if 'PULSE' in B else (' \\ ' if B=='PREP' else '   ')
    table={
      'coil':['      o      ','    _/|\\_    ','   [A]|[B]   ','     / \\     ','   _/   \\_   ','             ','   '+fireA+' '+fireB+'   '],
      'launch':['      o      ','     /|\\     ','   [A]|[B]   ','     / \\     ','    /   \\    ','             ','   '+fireA+' '+fireB+'   '],
      'air_leftpulse':['        o    ','      _/|\\   ','   [A] |[B]  ','      /  \\   ','     /    \\  ','             ','   '+fireA+' '+fireB+'   '],
      'air_rightpulse':['    o        ','   /|\\_      ','  [A]| [B]   ','   /  \\      ','  /    \\     ','             ','   '+fireA+' '+fireB+'   '],
      'apex':['      o      ','    --|--    ','   [A]|[B]   ','     / \\     ','    /   \\    ','             ','   '+fireA+' '+fireB+'   '],
      'air_coast':['      o      ','    --|--    ','   [A]|[B]   ','     / \\     ','    /   \\    ','             ','   '+fireA+' '+fireB+'   '],
      'sync':['      o      ','     /|\\     ','   [A]|[B]   ','     | |     ','     | |     ','             ','   '+fireA+' '+fireB+'   '],
      'sync_lift':['      o      ','    \\|/     ','   [A]|[B]   ','     | |     ','    /   \\    ','             ','   '+fireA+' '+fireB+'   '],
      'precontact':['       o     ','      /|\\    ','   [A] |[B]  ','      / \\    ','     /   \\__ ','            _','   '+fireA+' '+fireB+'   '],
      'right_catch':['        o    ','       /|\\   ','   [A]  |[B] ','       / \\   ','    __/   \\_ ','             ','   '+fireA+' '+fireB+'   '],
      'overshoot':['          o  ','        _/|\\ ','   [A]   |[B]','       _/ \\  ','    __/    \\_','             ','   '+fireA+' '+fireB+'   '],
      'both_catch':['        o    ','       /|\\   ','   [A]  |[B] ','      _/ \\_  ','   __/     \\_','             ','   '+fireA+' '+fireB+'   '],
      'compression':['       o     ','     _/|\\_   ','   [A] |[B]  ','    __/ \\__  ','  _/       \\_','             ','   '+fireA+' '+fireB+'   '],
      'rebound':['     o       ','    /|\\_     ','  [A]| [B]   ','    / \\      ',' __/   \\__   ','             ','   '+fireA+' '+fireB+'   '],
      'settle':['      o      ','     /|\\     ','   [A]|[B]   ','     / \\     ','  __/   \\__  ','             ','   '+fireA+' '+fireB+'   ']
    }
    return table.get(pose,table['settle'])

def world_to_px(root):
    return 70+root[0]*6.7, 74+root[1]*7.6

def quad(p0,p1,pc,t):
    u=1-t
    return (u*u*p0[0]+2*u*t*pc[0]+t*t*p1[0],
            u*u*p0[1]+2*u*t*pc[1]+t*t*p1[1])

def tool_char(angle):
    a=(angle%180+180)%180
    if 67.5<=a<=112.5: return '|'
    if 22.5<a<67.5: return '\\'
    if 112.5<a<157.5: return '/'
    return '-'

def draw_tool_pixels(d,px,py,tool):
    angle=float(tool['pivot_deg'])
    rad=math.radians(angle)
    pivot=(px+10,py-2)
    length=74
    tip=(pivot[0]+math.cos(rad)*length,pivot[1]+math.sin(rad)*length)
    ch=tool_char(angle)
    d.text((pivot[0]-6,pivot[1]-12),'+',font=FONT,fill='black')
    for t in (0.22,0.42,0.62,0.82):
        x=pivot[0]+(tip[0]-pivot[0])*t
        y=pivot[1]+(tip[1]-pivot[1])*t
        d.text((x-5,y-11),ch,font=FONT,fill='black')
    d.text((tip[0]-6,tip[1]-12),'@',font=FONT,fill='black')
    if tool['state'] in ('SYNC_PIVOT_DOWN','VERTICAL_THRUST_LOCK'):
        d.text((tip[0]-13,tip[1]+9),'^^',font=SMALL,fill='black')

def render_frame(root,key):
    im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im)
    d.line((28,GROUND_Y,W-28,GROUND_Y),fill='black',width=2)
    for x in range(34,W-30,36): d.text((x,GROUND_Y+4),'_',font=TINY,fill='black')
    px,py=world_to_px(root)
    lines=pose_lines(key['pose'],key['channels']['A'],key['channels']['B'],key.get('lean',0))
    for i,line in enumerate(lines):
        d.text((px-90,py-65+i*22),line,font=FONT,fill='black')
    draw_tool_pixels(d,px,py,key['tool_tip_pivot'])
    A=key['channels']['A']; B=key['channels']['B']
    if 'PULSE' in A: d.text((px-70,py+82),'//',font=FONT,fill='black')
    if 'PULSE' in B: d.text((px+34,py+82),'\\\\',font=FONT,fill='black')
    sc=key['support_contact']
    if 'RIGHT' in sc or sc=='BOTH_FEET_GROUND': d.text((px+27,GROUND_Y-14),'*',font=FONT,fill='black')
    if 'LEFT' in sc or sc=='BOTH_FEET_GROUND': d.text((px-48,GROUND_Y-14),'*',font=FONT,fill='black')
    d.text((20,14),'AIRBORNE039 :: SCOPED THRUST + TOOL-TIP PIVOT :: LIFT DEBT',font=SMALL,fill='black')
    d.text((20,35),f"{key['key_id']}  {key['label']}",font=SMALL,fill='black')
    d.text((20,H-55),f"support={sc}   A={A}   B={B}",font=TINY,fill='black')
    d.text((20,H-40),f"tool={key['tool_tip_pivot']['state']} pivot={key['tool_tip_pivot']['pivot_deg']}deg",font=TINY,fill='black')
    d.text((20,H-25),f"timing={key['timing_class']} / {key['timing_provenance']}   force={key['force']}",font=TINY,fill='black')
    return im

def compile_frames(m):
    frames=[]
    ks=m['keys']
    for i,k in enumerate(ks):
        for _ in range(k['hold_frames']): frames.append(render_frame(k['root'],k))
        if i+1<len(ks):
            n=k['bridge_frames']; nxt=ks[i+1]
            for j in range(1,n+1):
                t=j/(n+1); s=t*t*(3-2*t)
                frames.append(render_frame(quad(k['root'],nxt['root'],k['bridge_control'],s),k))
    return frames

def put(g,x,y,ch):
    if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=ch

def draw_tool_grid(g,rx,ry,tool):
    angle=float(tool['pivot_deg']); rad=math.radians(angle)
    px,py=rx+1,ry
    length=10
    tx=round(px+math.cos(rad)*length); ty=round(py+math.sin(rad)*length*0.55)
    ch=tool_char(angle)
    put(g,px,py,'+')
    for i in range(1,10):
        t=i/10
        x=round(px+(tx-px)*t); y=round(py+(ty-py)*t)
        put(g,x,y,ch)
    put(g,tx,ty,'@')
    if tool['state'] in ('SYNC_PIVOT_DOWN','VERTICAL_THRUST_LOCK'):
        put(g,tx-1,ty+1,'^'); put(g,tx,ty+1,'^')

def ascii_frame(k,w=104,h=42):
    g=[[' ']*w for _ in range(h)]; gy=38
    for x in range(w): g[gy][x]='_'
    rx=max(8,min(w-10,int(k['root'][0]))); ry=max(5,min(gy-8,int(k['root'][1]*0.78)))
    lines=pose_lines(k['pose'],k['channels']['A'],k['channels']['B'])
    for dy,line in enumerate(lines):
        yy=ry-3+dy; sx=rx-len(line)//2
        for dx,ch in enumerate(line):
            if ch!=' ': put(g,sx+dx,yy,ch)
    draw_tool_grid(g,rx,ry,k['tool_tip_pivot'])
    sc=k['support_contact']
    if sc=='BOTH_FEET_GROUND':
        put(g,rx-4,gy-1,'*'); put(g,rx+4,gy-1,'*')
    elif 'RIGHT' in sc: put(g,rx+4,gy-1,'*')
    return '\n'.join(''.join(r).rstrip() for r in g)

def make_contact(m):
    parts=[
      'ASCII KINESIS V2 - AIRBORNE039',
      'SCOPED_THRUST_SYNC_LIFT_LANDING_DEBT',
      'SOURCE EVIDENCE: TSR asset 97821 - Robot - Nuclear Throne - PC / Computer - Playable Characters',
      'SOURCE TIMING: UNKNOWN. ALL DECISIVE COMPILE TIMING BELOW: INFERRED / STREET_FIGHTER-CAPCOM.',
      'RIGHTS: source evidence only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/close imitation.',
      'CLOCK LAW: A period=5 ticks INFERRED; B period=7 ticks INFERRED; scoped sync restarts A+B only; BODY_ROOT/SUPPORT_CLOCK preserve phase.',
      'TOOL LAW: generic two-hand ASCII thrust-director boom is commission-authored, not source-derived; + = hand pivot, @ = tip; pivot timing INFERRED.',
      ''
    ]
    for k in m['keys']:
        parts += [
          '='*104,
          f"{k['key_id']} :: {k['label']}",
          f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']} | causal_role={k['causal_role']}",
          f"support_contact={k['support_contact']} | eligibility={k['contact_eligibility']}",
          f"root={k['root']} | channels={k['channels']} | force={k['force']}",
          f"tool_tip_pivot={k['tool_tip_pivot']}"
        ]
        if 'sync_scope' in k:
            parts.append(f"sync_scope={k['sync_scope']} | nonparticipants={k['nonparticipants']}")
        parts += [ascii_frame(k),'']
    return '\n'.join(parts).rstrip()+'\n'

def encode_mp4(frames,out):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,im in enumerate(frames): im.save(td/f'f{i:04d}.png',compress_level=9)
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(td/'f%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','encoder=ASCII-Kinesis-V2',str(out)]
        subprocess.run(cmd,check=True)

def make_spa(contact,m,mp4):
    b64=base64.b64encode(mp4).decode('ascii')
    mtxt=json.dumps(m,indent=2,ensure_ascii=False)+'\n'
    css="body{font-family:system-ui;margin:0;background:#fff;color:#111}nav{position:sticky;top:0;background:#fff;border-bottom:1px solid #999;padding:10px}button{font:inherit;margin-right:8px;padding:7px 14px}section{display:none;padding:14px}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:'liga' 0,'calt' 0;white-space:pre;overflow:auto;line-height:1.08;border:1px solid #999;padding:12px}video{max-width:100%;width:800px;background:#000}"
    js="document.querySelectorAll('button[data-view]').forEach(b=>b.onclick=()=>{document.querySelectorAll('section').forEach(s=>s.classList.remove('active'));document.getElementById(b.dataset.view).classList.add('active')})"
    return f'<!doctype html><html><head><meta charset="utf-8"><title>Airborne039</title><style>{css}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre>{html.escape(contact)}</pre></section><section id="json"><pre>{html.escape(mtxt)}</pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section><script>{js}</script></body></html>'

def main():
    m=json.loads(MOTION.read_text(encoding='utf-8'))
    contact=make_contact(m); CONTACT.write_text(contact,encoding='utf-8')
    frames=compile_frames(m); encode_mp4(frames,MP4)
    media=MP4.read_bytes()
    SPA.write_text(make_spa(contact,m,media),encoding='utf-8')
    print(json.dumps({'frames':len(frames),'bytes':len(media),'sha256':hashlib.sha256(media).hexdigest(),'contact_bytes':len(CONTACT.read_bytes()),'spa_bytes':len(SPA.read_bytes())},indent=2))
if __name__=='__main__': main()
