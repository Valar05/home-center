#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,html,json,subprocess,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent
M=json.loads((R/'motion.json').read_text())
W,H=M['rig']['grid']['width'],M['rig']['grid']['height']; K=M['keys']; B=M['rig']['bones']; HOLD=M['motion_dungeon']['hold_frames_by_class']; TRANS=M['motion_dungeon']['transition_frames']; FPS=M['timing_policy']['nominal_fps']
J=['pelvis','chest','head','l_shoulder','l_elbow','l_hand','r_shoulder','r_elbow','r_hand','l_knee','l_foot','r_knee','r_foot','tool_butt','tool_tip']
def put(g,x,y,c):
 x,y=round(x),round(y)
 if 0<=x<W and 0<=y<H:g[y][x]=c
def line(g,a,b,c=None):
 x0,y0,x1,y1=map(round,(a[0],a[1],b[0],b[1]));dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
 if c is None:
  X,Y=x1-x0,y1-y0;c='-' if abs(X)>2*abs(Y) else ('|' if abs(Y)>2*abs(X) else ('\\' if X*Y>=0 else '/'))
 while 1:
  put(g,x0,y0,c)
  if x0==x1 and y0==y1:break
  z=2*e
  if z>=dy:e+=dy;x0+=sx
  if z<=dx:e+=dx;y0+=sy
def pose(p):
 g=[[' ']*W for _ in range(H)];j=p['joints']
 for x in range(10,35):put(g,x,18,'_')
 for a,b in B:line(g,j[a],j[b])
 line(g,j['tool_butt'],j['tool_tip'],'=')
 for n in J:
  x,y=j[n];c='O' if n=='head' else ('+' if n=='pelvis' else ('*' if n in {'l_hand','r_hand','l_foot','r_foot','tool_butt','tool_tip'} else 'o'));put(g,x,y,c)
 if p.get('key_id')=='K4':put(g,*j['tool_tip'],'!')
 put(g,2,2,'>')
 for f in ('l_foot','r_foot'):
  x,y=j[f];put(g,x,min(H-1,y+1),'^')
 return '\n'.join(''.join(r).rstrip() for r in g).rstrip()+'\n'
def hcat(bs):
 ls=[b.splitlines() for b in bs];ws=[max(map(len,x),default=0) for x in ls];h=max(map(len,ls));return '\n'.join('    '.join((x[y] if y<len(x) else '').ljust(w) for x,w in zip(ls,ws)).rstrip() for y in range(h))
cards=[f"[{p['key_id']} {p['name']} · {p['timing_class']} · {p['timing_provenance']}]\n{pose(p).rstrip()}" for p in K]
contact=('\n\n'+'='*118+'\n\n').join(hcat(cards[i:i+2]) for i in range(0,len(cards),2))+'\n'
def interp(a,b,t):return {'key_id':'T','joints':{n:[a['joints'][n][0]+(b['joints'][n][0]-a['joints'][n][0])*t,a['joints'][n][1]+(b['joints'][n][1]-a['joints'][n][1])*t] for n in J}}
seq=[]
for i,p in enumerate(K):
 seq += [p]*HOLD[p['timing_class']]
 if i<len(K)-1:
  seq += [interp(p,K[i+1],q/(TRANS[i]+1)) for q in range(1,TRANS[i]+1)]
seq*=2
D=R/'.frames';D.mkdir(exist_ok=True);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',10);cw=font.getbbox('M')[2];ch=12
for i,p in enumerate(seq):
 im=Image.new('L',(W*cw+16,H*ch+24),0);d=ImageDraw.Draw(im);y=7
 for s in pose(p).splitlines():d.text((8,y),s,font=font,fill=255);y+=ch
 im.convert('RGB').save(D/f'{i:04d}.png')
mp4=R/'axial-thrust-recovery-ascii.mp4'
subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(D/'%04d.png'),'-vf','scale=320:-2:flags=neighbor,format=yuv420p','-c:v','libx264','-preset','veryslow','-crf','45','-tune','animation','-movflags','+faststart',str(mp4)],check=True);shutil.rmtree(D)
vb=mp4.read_bytes();sha=hashlib.sha256(vb).hexdigest();man=json.loads((R/'manifest.json').read_text());man['media'].update(bytes=len(vb),sha256=sha);payload=dict(M);payload['manifest']=man;esc=lambda s:html.escape(s,quote=False);b64=base64.b64encode(vb).decode()
page=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>*{{box-sizing:border-box}}body{{margin:0;background:#050505;color:#eee;font-family:system-ui}}main{{max-width:1100px;margin:auto;padding:10px}}nav{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}button{{min-height:44px}}section{{display:none}}section.active{{display:block}}pre{{white-space:pre;overflow:auto;font:12px/1.08 "DejaVu Sans Mono","Liberation Mono",monospace;font-variant-ligatures:none;user-select:text;background:#000;padding:10px}}video{{max-width:100%}}</style></head><body><main><h1>V2 Strikes 001 — Axial Thrust / Tool-First Recovery</h1><nav><button data-view="ascii" aria-pressed="true">ASCII</button><button data-view="json" aria-pressed="false">JSON</button><button data-view="video" aria-pressed="false">VIDEO</button></nav><section data-panel="ascii" class="active"><pre>{esc(contact)}</pre></section><section data-panel="json"><pre>{esc(json.dumps(payload,indent=2))}</pre></section><section data-panel="video"><video controls autoplay muted loop playsinline src="data:video/mp4;base64,{b64}"></video></section></main><script>(()=>{{const b=[...document.querySelectorAll('[data-view]')],p=[...document.querySelectorAll('[data-panel]')];b.forEach(x=>x.onclick=()=>{{b.forEach(y=>y.setAttribute('aria-pressed',String(y===x)));p.forEach(y=>y.classList.toggle('active',y.dataset.panel===x.dataset.view))}})}})()</script></body></html>'''
(R/'axial-thrust-recovery.motion.html').write_text(page)
print(json.dumps({'video_sha256':sha,'video_bytes':len(vb),'frames':len(seq)}))
