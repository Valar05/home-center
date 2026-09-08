#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MOTION=ROOT/'motion.json'
CONTACT=ROOT/'contact_sheet.txt'
MP4=ROOT/'contact-pin-disengage-causality-repair.mp4'
SPA=ROOT/'contact-pin-disengage-causality-repair.motion.html'
FPS=24; OUT_W=720; OUT_H=400; CELL_W=13; CELL_H=18; OX=18; OY=18
FONT={
' ':['00000']*7,'.':['00000','00000','00000','00000','00000','00100','00100'],':':['00000','00100','00100','00000','00100','00100','00000'],'-':['00000','00000','00000','11111','00000','00000','00000'],'|':['00100']*7,'/':['00001','00010','00100','01000','10000','00000','00000'],'\\':['10000','01000','00100','00010','00001','00000','00000'],'=':['00000','00000','11111','00000','11111','00000','00000'],'O':['01110','10001','10001','10001','10001','10001','01110'],'o':['00000','00000','01110','10001','10001','10001','01110'],'+':['00000','00100','00100','11111','00100','00100','00000'],'_':['00000','00000','00000','00000','00000','00000','11111'],'[':['01110','01000','01000','01000','01000','01000','01110'],']':['01110','00010','00010','00010','00010','00010','01110'],'>':['10000','01000','00100','00010','00100','01000','10000'],'!':['00100','00100','00100','00100','00100','00000','00100'],'^':['00100','01010','10001','00000','00000','00000','00000']}

def curve(t,name):
 if name=='ease_in': return t*t
 if name=='ease_out': return 1-(1-t)*(1-t)
 if name=='ease_in_out': return 3*t*t-2*t*t*t
 return t

def mix(a,b,t,kind):
 u=curve(t,kind); return {j:[a[j][0]*(1-u)+b[j][0]*u,a[j][1]*(1-u)+b[j][1]*u] for j in a}

def bres(a,b):
 x0,y0=map(lambda v:int(round(v)),a);x1,y1=map(lambda v:int(round(v)),b);dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy;out=[]
 while 1:
  out.append((x0,y0))
  if x0==x1 and y0==y1:return out
  q=2*e
  if q>=dy:e+=dy;x0+=sx
  if q<=dx:e+=dx;y0+=sy

def line_char(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 return '-' if abs(dx)>=2*abs(dy) else ('|' if abs(dy)>=2*abs(dx) else ('\\' if dx*dy>0 else '/'))

def frame(m,j,contact=False):
 W,H=m['rig']['grid']['width'],m['rig']['grid']['height'];g=[[' ']*W for _ in range(H)]
 for x in range(W):g[18][x]='.'
 plane=m['rig']['impact_plane']['x']
 for y in range(5,16):g[y][plane]=':'
 for a,b in m['rig']['bones']:
  c=line_char(j[a],j[b])
  for x,y in bres(j[a],j[b]):
   if 0<=x<W and 0<=y<H and g[y][x]==' ':g[y][x]=c
 for x,y in bres(j['tool_butt'],j['tool_tip']):
  if 0<=x<W and 0<=y<H:g[y][x]='='
 syms={'head':'O','pelvis':'+','rear_hand':'o','front_hand':'o','rear_foot':'_','front_foot':'_','tool_butt':'[','tool_tip':'>'}
 for n,c in syms.items():
  x,y=map(lambda v:int(round(v)),j[n])
  if 0<=x<W and 0<=y<H:g[y][x]=c
 if contact:
  tx,ty=map(lambda v:int(round(v)),j['tool_tip'])
  if tx==plane and 0<=ty<H:g[ty][plane]='!'
 return [''.join(r) for r in g]

def compile_frames(m):
 hold={'ONES':1,'TWOS':2,'FOURS':4};ks=m['keys'];ts=m['transitions'];frames=[]
 for i,k in enumerate(ks):
  for _ in range(hold[k['timing_class']]): frames.append((k['joints'],k.get('contact_state')=='PINNED'))
  if i<len(ks)-1:
   t=ts[i];n=int(t['connective_frames'])
   for q in range(1,n+1):
    pinned=k.get('contact_state')=='PINNED' and ks[i+1].get('contact_state')=='PINNED'
    frames.append((mix(k['joints'],ks[i+1]['joints'],q/(n+1),t['curve']),pinned))
 return frames

def put(buf,x0,y0,x1,y1,v=242):
 x0=max(0,x0);y0=max(0,y0);x1=min(OUT_W,x1);y1=min(OUT_H,y1)
 for y in range(y0,y1):
  i=(y*OUT_W+x0)*3
  for _ in range(x0,x1):buf[i]=v;buf[i+1]=v;buf[i+2]=v;i+=3

def raster(lines):
 buf=bytearray(OUT_W*OUT_H*3)
 for gy,line in enumerate(lines):
  for gx,ch in enumerate(line):
   pat=FONT.get(ch,FONT[' ']);px=OX+gx*CELL_W;py=OY+gy*CELL_H;sx=max(1,CELL_W//7);sy=max(1,CELL_H//9)
   for yy,row in enumerate(pat):
    for xx,b in enumerate(row):
     if b=='1':put(buf,px+xx*sx,py+yy*sy,px+(xx+1)*sx,py+(yy+1)*sy)
 return bytes(buf)

def encode(m,frames):
 p=subprocess.Popen(['ffmpeg','-y','-loglevel','error','-f','rawvideo','-pixel_format','rgb24','-video_size',f'{OUT_W}x{OUT_H}','-framerate',str(FPS),'-i','-','-an','-c:v','libx264','-preset','veryslow','-crf','26','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],stdin=subprocess.PIPE)
 try:
  for j,c in frames:p.stdin.write(raster(frame(m,j,c)))
 finally:p.stdin.close()
 if p.wait():raise SystemExit('ffmpeg encode failed')

def build_spa(m,contact,video):
 esc=lambda s:html.escape(s,quote=False);b64=base64.b64encode(video).decode('ascii')
 j=esc(json.dumps(m,indent=2,ensure_ascii=False))
 return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Strikes 004 — Contact Pin / Disengage Causality Repair</title><style>:root{{color-scheme:dark;background:#080808;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0}}main{{max-width:1120px;margin:auto;padding:10px}}nav{{position:sticky;top:0;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;background:#080808;padding:8px 0}}button{{min-height:44px;font:inherit}}section{{display:none}}section.active{{display:block}}pre{{white-space:pre;overflow:auto;font:12px/1.08 ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;user-select:text;background:#000;padding:10px}}video{{display:block;width:min(100%,720px);height:auto;background:#000}}</style></head><body><main><h1>V2 Strikes 004 — Contact Pin / Disengage Causality Repair</h1><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section data-panel="ascii" class="active"><pre>{esc(contact)}</pre></section><section data-panel="json"><pre>{j}</pre></section><section data-panel="video"><video controls autoplay muted loop playsinline src="data:video/mp4;base64,{b64}"></video></section></main><script>(()=>{{const b=[...document.querySelectorAll('[data-view]')],p=[...document.querySelectorAll('[data-panel]')];b.forEach(x=>x.onclick=()=>p.forEach(y=>y.classList.toggle('active',y.dataset.panel===x.dataset.view)))}})()</script></body></html>'''

def main():
 m=json.loads(MOTION.read_text(encoding='utf-8'));contact=CONTACT.read_text(encoding='utf-8');frames=compile_frames(m)
 if len(frames)!=m['media']['frame_count']:raise SystemExit(f"frame count mismatch {len(frames)}")
 encode(m,frames);video=MP4.read_bytes();sha=hashlib.sha256(video).hexdigest()
 if m['media'].get('sha256') and sha!=m['media']['sha256']:raise SystemExit('media sha mismatch')
 if m['media'].get('bytes') and len(video)!=m['media']['bytes']:raise SystemExit('media byte mismatch')
 SPA.write_text(build_spa(m,contact,video),encoding='utf-8')
 print(json.dumps({'frames':len(frames),'media_sha256':sha,'bytes':len(video),'spa':SPA.name},sort_keys=True))
if __name__=='__main__':main()
