#!/usr/bin/env python3
from __future__ import annotations
import json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=json.loads((ROOT/'motion.json').read_text(encoding='utf-8'))
W,H=MOTION['rig']['grid']
FPS=int(MOTION['compile_fps'])
HOLD={'ONES':1,'TWOS':2,'FOURS':4}

# deterministic character grid renderer; only abstract ASCII glyphs are drawn.
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

def body_grid(root,joints,tag,contact=False):
    pts={k:tuple(v) for k,v in joints.items()}; root=tuple(root)
    g={}
    def put(p,ch):
        x,y=p
        if 0<=x<W and 0<=y<H:g[(x,y)]=ch
    put(pts['head'],'O'); put(root,'@'); put(pts['shoulder'],'o')
    for p,ch in [(pts['lhand'],'h'),(pts['rhand'],'h'),(pts['lfoot'],'^'),(pts['rfoot'],'^')]:put(p,ch)
    segs=[(pts['head'],pts['shoulder'],'|'),(pts['shoulder'],root,'|'),(pts['shoulder'],pts['lhand'],'/'),(pts['shoulder'],pts['rhand'],'\\'),(root,pts['lfoot'],'/'),(root,pts['rfoot'],'\\')]
    for a,b,ch in segs:
        for p in line_points(a,b)[1:-1]: put(p,ch)
    # label near head, minimal
    put((pts['head'][0]-1,max(0,pts['head'][1]-1)),tag)
    return g

def render_ascii(state):
    grid=[[' ']*W for _ in range(H)]
    # ground
    for x in range(W):grid[28][x]='_'
    for tag in ('A','B'):
        g=body_grid(state['root_'+tag],state['joints_'+tag],tag,state.get('contact')!='NONE')
        for (x,y),ch in g.items():grid[y][x]=ch
    if 'TRANSIENT' in state.get('contact',''):
        # mark only authored inter-body contact; ground support/contact must never draw a phantom body-body marker
        ax,ay=state['joints_A']['rhand']; bx,by=state['joints_B']['lhand']
        cx=round((ax+bx)/2); cy=round((ay+by)/2)
        if 0<=cx<W and 0<=cy<H:grid[cy][cx]='*'
    return '\n'.join(''.join(r).rstrip() for r in grid).rstrip()+'\n'

def lerp(a,b,t): return a+(b-a)*t

def interp(k0,k1,t):
    out={'contact':'NONE'}
    for tag in ('A','B'):
        out['root_'+tag]=[round(lerp(k0['root_'+tag][i],k1['root_'+tag][i],t)) for i in range(2)]
        out['joints_'+tag]={}
        for n in k0['joints_'+tag]:
            out['joints_'+tag][n]=[round(lerp(k0['joints_'+tag][n][i],k1['joints_'+tag][n][i],t)) for i in range(2)]
    return out

def compile_states():
    keys=MOTION['keys']; trans={(x['from'],x['to']):x['frames'] for x in MOTION['transitions']}
    frames=[]
    for i,k in enumerate(keys):
        for _ in range(HOLD[k['timing_class']]): frames.append(k)
        if i+1<len(keys):
            n=trans[(k['key_id'],keys[i+1]['key_id'])]
            for j in range(1,n+1):
                t=j/(n+1)
                frames.append(interp(k,keys[i+1],t))
    return frames

def font():
    paths=['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf']
    for p in paths:
        if Path(p).exists(): return ImageFont.truetype(p,12)
    return ImageFont.load_default()

def make_contact_sheet(path):
    return '\n\n'.join(f"{k['key_id']} — {k['label']} — {k['timing_class']} — {k['timing_provenance']}\n{render_ascii(k)}SUPPORT A={k['support_contact']['A']} | B={k['support_contact']['B']} | CONTACT={k['contact']}\nROOT: {k['root_note']}" for k in MOTION['keys'])+'\n'

def render_mp4(path):
    frames=compile_states(); fnt=font(); cw,ch=7,13; pad=10
    width=W*cw+pad*2; height=H*ch+pad*2
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for idx,s in enumerate(frames):
            im=Image.new('RGB',(width,height),'black'); d=ImageDraw.Draw(im)
            txt=render_ascii(s)
            d.multiline_text((pad,pad),txt,font=fnt,fill='white',spacing=0)
            im.save(td/f'{idx:04d}.png')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(td/'%04d.png'),'-c:v','libx264','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',str(path)],check=True)
    return len(frames)

if __name__=='__main__':
    (ROOT/'contact-sheet.txt').write_text(make_contact_sheet(ROOT/'contact-sheet.txt'),encoding='utf-8')
    n=render_mp4(ROOT/'opposed-flight-glance-split-landing-debt.mp4')
    print(json.dumps({'frames':n,'fps':FPS},sort_keys=True))
