#!/usr/bin/env python3
from __future__ import annotations
import json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=json.loads((ROOT/'motion.json').read_text(encoding='utf-8'))
W,H=MOTION['rig']['grid']
FPS=int(MOTION['compile_fps'])
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
ENV=MOTION['rig']['environment']

def line_points(a,b):
    x0,y0=a; x1,y1=b
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return out

def render_ascii(state):
    grid=[[' ']*W for _ in range(H)]
    fy=int(ENV['floor_y']); wxs=[int(x) for x in ENV['aperture_wall_xs']]; ot,ob=ENV['opening_rows']
    for x in range(W): grid[fy][x]='_'
    for y in range(fy):
        if y<ot or y>ob:
            for wx in wxs: grid[y][wx]='#'
    pts={k:tuple(v) for k,v in state['joints'].items()}; root=tuple(state['root'])
    def put(p,ch):
        x,y=p
        if 0<=x<W and 0<=y<H: grid[y][x]=ch
    put(pts['head'],'O'); put(pts['shoulder'],'o'); put(root,'@')
    for p,ch in [(pts['lhand'],'h'),(pts['rhand'],'h'),(pts['lfoot'],'^'),(pts['rfoot'],'^')]: put(p,ch)
    for a,b,ch in [
        (pts['head'],pts['shoulder'],'|'),(pts['shoulder'],root,'|'),
        (pts['shoulder'],pts['lhand'],'/'),(pts['shoulder'],pts['rhand'],'\\'),
        (root,pts['lfoot'],'/'),(root,pts['rfoot'],'\\')]:
        for p in line_points(a,b)[1:-1]: put(p,ch)
    return '\n'.join(''.join(r).rstrip() for r in grid).rstrip()+'\n'

def lerp(a,b,t): return a+(b-a)*t

def interp(k0,k1,t):
    return {'root':[round(lerp(k0['root'][i],k1['root'][i],t)) for i in range(2)],
            'joints':{n:[round(lerp(k0['joints'][n][i],k1['joints'][n][i],t)) for i in range(2)] for n in k0['joints']},
            'support_contact':k0['support_contact'],'obstacle_contact':k0['obstacle_contact']}

def compile_states():
    keys=MOTION['keys']
    trans={(x['from'],x['to']):x['frames'] for x in MOTION['transitions']}
    frames=[]
    for i,k in enumerate(keys):
        for _ in range(HOLD[k['timing_class']]): frames.append(k)
        if i+1<len(keys):
            nxt=keys[i+1]; n=trans[(k['key_id'],nxt['key_id'])]
            if n and (k['support_contact']!=nxt['support_contact'] or k['obstacle_contact']!=nxt['obstacle_contact']):
                raise RuntimeError(f"generic transition crosses causal topology {k['key_id']}->{nxt['key_id']}")
            for j in range(1,n+1): frames.append(interp(k,nxt,j/(n+1)))
    return frames

def font():
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf']:
        if Path(p).exists(): return ImageFont.truetype(p,12)
    return ImageFont.load_default()

def contact_sheet():
    blocks=[
        f"ASCII KINESIS V2 AIRBORNE031 — APERTURE FOLD / DELAYED LANDING OPEN\n"
        f"ENVIRONMENT: floor y={ENV['floor_y']} | wall x={ENV['aperture_wall_xs']} | opening rows={ENV['opening_rows']}\n"
        "Each decisive key below is a literal crop of the same global ASCII rig; x/y windows are stated explicitly.\n"
    ]
    for k in MOTION['keys']:
        full=render_ascii(k).splitlines()
        rx,ry=k['root']; x0=max(0,rx-13); x1=min(W-1,rx+13); y0=max(0,ry-8); y1=min(H-1,ry+8)
        crop='\n'.join((full[y] if y < len(full) else '')[x0:x1+1].rstrip() for y in range(y0,y1+1)).rstrip()+'\n'
        blocks.append(f"{k['key_id']} — {k['label']} — {k['timing_class']} — {k['timing_provenance']} | WINDOW x={x0}..{x1} y={y0}..{y1}\n"
                      f"{crop}"
                      f"SUPPORT={k['support_contact']} ({k['support_detail']}) | APERTURE_CONTACT={k['obstacle_contact']}\n"
                      f"ROOT: {k['root_note']}\n"
                      f"ROLE: {k['causal_role']}")
    return '\n\n'.join(blocks)+'\n'

def render_mp4(path):
    frames=compile_states(); fnt=font(); cw,ch=7,13; pad=10
    width=W*cw+pad*2; height=H*ch+pad*2
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for idx,s in enumerate(frames):
            im=Image.new('RGB',(width,height),'black')
            d=ImageDraw.Draw(im)
            d.multiline_text((pad,pad),render_ascii(s),font=fnt,fill='white',spacing=0)
            im.save(td/f'{idx:04d}.png')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),
                        '-i',str(td/'%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','34',
                        '-pix_fmt','yuv420p','-movflags','+faststart',str(path)],check=True)
    return len(frames),width,height

if __name__=='__main__':
    (ROOT/'contact-sheet.txt').write_text(contact_sheet(),encoding='utf-8')
    n,w,h=render_mp4(ROOT/'aperture-fold-delayed-landing-open.mp4')
    print(json.dumps({'frames':n,'fps':FPS,'width':w,'height':h},sort_keys=True))
