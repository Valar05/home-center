#!/usr/bin/env python3
from __future__ import annotations
import json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=json.loads((ROOT/'motion.json').read_text(encoding='utf-8'))
GW=MOTION['rig']['grid']['width']; GH=MOTION['rig']['grid']['height']
W=MOTION['compile']['width']; H=MOTION['compile']['height']; FPS=MOTION['compile']['fps']
HOLDS=MOTION['compile']['timing_frames']
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

def bres(a,b):
    x0,y0=a; x1,y1=b; pts=[]; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return pts

def put(g,x,y,ch):
    if 0<=x<GW and 0<=y<GH: g[y][x]=ch

def line(g,a,b,ch):
    for x,y in bres(tuple(a),tuple(b)): put(g,x,y,ch)

def interp(a,b,t): return [round(a[0]+(b[0]-a[0])*t), round(a[1]+(b[1]-a[1])*t)]

def topology(k): return (k['support_contact'],k['contact'])

def blend(a,b,t):
    out=dict(a)
    for key in ['root','head','rear_foot','front_foot','rear_hand','front_hand','shaft_butt','shaft_tip']:
        out[key]=interp(a[key],b[key],t)
    out['key_id']=f"{a['key_id']}~{b['key_id']}"
    out['name']='CONNECTIVE'
    out['wall_x']=a['wall_x']
    return out

def ascii_state(k, label=True):
    g=[[' ']*GW for _ in range(GH)]
    wx=k['wall_x']
    for y in range(3,17): put(g,wx,y,'#')
    root=k['root']; head=k['head']; rf=k['rear_foot']; ff=k['front_foot']; rh=k['rear_hand']; fh=k['front_hand']; butt=k['shaft_butt']; tip=k['shaft_tip']
    neck=[root[0], max(root[1]-3,0)]
    line(g,root,neck,'|'); line(g,neck,head,'|'); put(g,*head,'O')
    line(g,root,rf,'/'); line(g,root,ff,'\\')
    line(g,neck,rh,'/'); line(g,neck,fh,'\\')
    put(g,*rf,'*'); put(g,*ff,'*')
    line(g,butt,tip,'='); put(g,*rh,'+'); put(g,*fh,'+')
    put(g,*butt,'<')
    if k.get('contact')=='PINNED_TIP': put(g,*tip,'!')
    else: put(g,*tip,'>')
    put(g,*root,'@')
    rows=[''.join(r).rstrip() for r in g]
    if label:
        return f"{k['key_id']} {k['name']}\n" + '\n'.join(rows)
    return '\n'.join(rows)

def make_contact_sheet():
    chunks=[]
    for k in MOTION['keys']:
        meta=f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']} | causal_role={k['causal_role']}\nsupport={k['support_contact']} | contact={k['contact']} | root_note={k['motion_arc_root_note']}"
        chunks.append(ascii_state(k)+"\n"+meta)
    return '\n\n'.join(chunks)+'\n'

def render_frame(k, path):
    img=Image.new('RGB',(W,H),'black'); d=ImageDraw.Draw(img)
    font=ImageFont.truetype(FONT,11); small=ImageFont.truetype(FONT,9)
    title=f"STRIKES021 · {k['key_id']} · {k['name']}"
    d.text((10,7),title,font=small,fill='white')
    text=ascii_state(k,label=False)
    d.multiline_text((10,24),text,font=font,fill='white',spacing=0)
    d.text((10,H-18),'TIP PIN -> ROOT OVERRUN -> LEVER -> RELEASE -> COUNTERSWING -> DISPLACED SETTLE',font=small,fill='white')
    img.save(path)

def compile_frames():
    frames=[]; keys=MOTION['keys']
    for i,k in enumerate(keys):
        frames.extend([k]*HOLDS[k['timing_class']])
        if i < len(keys)-1 and k.get('bridge_after',0):
            nxt=keys[i+1]
            if topology(k)==topology(nxt):
                frames.append(blend(k,nxt,0.5))
    return frames

def build_video(out):
    frames=compile_frames()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,k in enumerate(frames): render_frame(k,td/f'{i:04d}.png')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(td/'%04d.png'),'-c:v','libx264','-crf','38','-preset','veryslow','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
    return len(frames)

def main():
    (ROOT/'contact-sheet.txt').write_text(make_contact_sheet(),encoding='utf-8')
    n=build_video(ROOT/'pinned-tip-lever-reversal-debt.mp4')
    print(json.dumps({'frames':n,'fps':FPS,'video':str(ROOT/'pinned-tip-lever-reversal-debt.mp4')},sort_keys=True))
if __name__=='__main__': main()
