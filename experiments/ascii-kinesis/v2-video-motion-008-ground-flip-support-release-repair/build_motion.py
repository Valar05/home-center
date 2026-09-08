#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
P=Path(__file__).resolve().parent; M=json.loads((P/'motion.json').read_text()); K=M['keys']
FPS=M['timing']['compile_fps']; C,R=48,20; G=18; CW,CH=11,19; PX=PY=22; W=C*CW+2*PX; H=((R+3)*CH+2*PY+1)//2*2
ORDER=['head','neck','root','le','lh','re','rh','lk','lf','rk','rf']; BONES=[('head','neck'),('neck','root'),('neck','le'),('le','lh'),('neck','re'),('re','rh'),('root','lk'),('lk','lf'),('root','rk'),('rk','rf')]
def phase(s): return 'air' if s.startswith('AIRBORNE') else ('prep' if ('LAST_SUPPORT' in s or 'PEEL' in s) else 'ground')
def sm(t): return t*t*(3-2*t)
def ij(a,b,t,n,p):
 q=sm(t); x=a[0]+(b[0]-a[0])*q; y=a[1]+(b[1]-a[1])*q
 if n in {'lh','rh'}: y-=math.sin(math.pi*t)*(0.8 if p in {'air','prep'} else 0.4)
 elif n in {'lf','rf'} and p=='air': y-=math.sin(math.pi*t)*0.7
 return [round(x),round(y)]
def glyph(dx,dy): return '-' if abs(dx)>=abs(dy)*2 else ('|' if abs(dy)>=abs(dx)*2 else ('\\' if dx*dy>=0 else '/'))
def line(g,a,b):
 x0,y0=a;x1,y1=b;dx=x1-x0;dy=y1-y0;n=max(abs(dx),abs(dy),1);ch=glyph(dx,dy)
 for i in range(1,n):
  x=round(x0+dx*i/n);y=round(y0+dy*i/n)
  if 0<=x<C and 0<=y<R and g[y][x]==' ': g[y][x]=ch
def ascii_pose(j,s):
 g=[[' ']*C for _ in range(R)]
 for x in range(C): g[G][x]='_'
 for x in range(22,41,4): g[G][x]='.'
 for a,b in BONES: line(g,j[a],j[b])
 for n,ch in {'head':'O','neck':'+','root':'@','le':'+','lh':'*','re':'+','rh':'*','lk':'+','lf':'L','rk':'+','rf':'R'}.items():
  x,y=j[n]
  if 0<=x<C and 0<=y<R:g[y][x]=ch
 if 'LEFT' in s or 'BOTH' in s:g[G][max(0,min(C-1,j['lf'][0]))]='L'
 if 'RIGHT' in s or 'BOTH' in s:g[G][max(0,min(C-1,j['rf'][0]))]='R'
 return '\n'.join(''.join(r).rstrip() for r in g)
def frames():
 out=[]; n=0
 for i,k in enumerate(K):
  j=k['pose_rig']['joints']
  for _ in range(k['compile_hold_frames']):out.append((n,k['causal_role'],k['support'],j));n+=1
  if i+1<len(K):
   z=K[i+1]; tr=k['travel_to_next_frames']
   for q in range(1,tr+1):
    if k['causal_boundary_to_next'] or z['causal_boundary_to_next'] or k['support']!=z['support']: jj=z['pose_rig']['joints'];s=z['support'];role=z['causal_role']
    else:
     t=q/(tr+1);p=phase(k['support']);jj={a:ij(j[a],z['pose_rig']['joints'][a],t,a,p) for a in ORDER};s=k['support'];role=k['causal_role']+' > '+z['causal_role']
    out.append((n,role,s,jj));n+=1
 return out
def render(out):
 fs=frames(); fp=next((x for x in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'] if Path(x).exists()),None);font=ImageFont.truetype(fp,16) if fp else ImageFont.load_default()
 with tempfile.TemporaryDirectory() as td:
  d=Path(td)
  for no,role,s,j in fs:
   text=f'{no:03d}  {role[:34]:34}  {s[:28]}\n'+'-'*C+'\n'+ascii_pose(j,s);im=Image.new('RGB',(W,H),(8,8,8));ImageDraw.Draw(im).multiline_text((PX,PY),text,font=font,fill=(238,238,238),spacing=2);im.save(d/f'{no:04d}.png')
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(d/'%04d.png'),'-an','-c:v','libx264','-pix_fmt','yuv420p','-profile:v','baseline','-level','3.0','-crf','28','-preset','veryslow','-movflags','+faststart',str(out)],check=True)
 subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True)
 b=Path(out).read_bytes();print(json.dumps({'frames':len(fs),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()}))
if __name__=='__main__':render(P/'motion.mp4')
