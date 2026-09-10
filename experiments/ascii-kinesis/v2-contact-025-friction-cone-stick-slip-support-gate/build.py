#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import base64,gzip,hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;M=R/'motion.json';A=R/'contact-sheet.txt';B=R/'.motion-build';V=B/'motion.mp4';S=R/'friction-cone-stick-slip-support-gate.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
def font(n):
 p=Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
 if not p.is_file(): raise SystemExit('MISSING_REQUIRED_FONT')
 return ImageFont.truetype(str(p),n)
def line(g,a,b,ch=None,overwrite=False):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy;pts=[]
 while True:
  pts.append((x0,y0))
  if (x0,y0)==(x1,y1): break
  e2=2*e
  if e2>=dy:e+=dy;x0+=sx
  if e2<=dx:e+=dx;y0+=sy
 for i,(x,y) in enumerate(pts[1:-1],1):
  if 0<=y<len(g) and 0<=x<len(g[0]) and (overwrite or g[y][x]==' '):
   if ch:g[y][x]=ch
   else:
    px,py=pts[i-1];nx,ny=pts[i+1];ddx=nx-px;ddy=ny-py
    g[y][x]='-' if abs(ddx)>=2*abs(ddy) else ('|' if abs(ddy)>=2*abs(ddx) else ('\\' if ddx*ddy>0 else '/'))
def force_inset(g,k):
 x0,y0=72,10
 label='FORCE'
 for i,c in enumerate(label):
  if x0-10+i<len(g[0]):g[2][x0-10+i]=c
 line(g,(x0,y0),(x0-10,y0-5),':',True);line(g,(x0,y0),(x0-10,y0+5),':',True)
 if 0<=y0<len(g) and 0<=x0<len(g[0]):g[y0][x0]='*' if k['contact_state']!='OPEN' else 'o'
 cone=k.get('cone_status','NONE')
 if cone in ('NONE','ZERO'): return
 N=max(.01,float(k.get('normal_load',0.0)));T=float(k.get('tangent_load',0.0));D=float(k.get('demand_tangent',T))
 dy=max(-5,min(5,-round(5*T/max(.01,N*.78))));yr=y0+dy
 line(g,(x0,y0),(x0-9,yr),'=',True)
 if 0<=yr<len(g):g[yr][x0-10]='R'
 ddy=max(-8,min(8,-round(5*D/max(.01,N*.78))));yd=y0+ddy
 if 0<=yd<len(g):g[yd][x0-11]='D'
 tag={'INSIDE':'I','BOUNDARY':'B','OUTSIDE_CLAMPED':'X','CENTER':'C'}.get(cone,'?')
 if 0<=17<len(g):g[17][x0-2]=tag
def art(k,m):
 W=m['rig']['grid']['width'];H=m['rig']['grid']['height'];fy=m['rig']['grid']['floor_y'];wx=m['rig']['grid']['wall_x'];g=[[' ']*W for _ in range(H)]
 for x in range(1,W-1):g[fy][x]='_'
 for y in range(1,fy):g[y][wx]='|'
 rx,ry=k['root'];lean=k['lean'];compact=k['compact'];neck=(rx+round(lean*.45),ry-(5-compact));head=(neck[0]+round(lean*.35),neck[1]-2);sh=(neck[0],neck[1]+1)
 rear=(rx-5,fy);front=(rx+5,fy);line(g,head,neck,'|');line(g,neck,(rx,ry),'|');line(g,(rx,ry),rear);line(g,(rx,ry),front)
 hand=tuple(k['hand']);free=tuple(k['free_hand']);el=(sh[0]+5,sh[1]+(1 if hand[1]>sh[1] else -1));line(g,sh,el);line(g,el,hand);ef=(sh[0]-4,sh[1]-1);line(g,sh,ef);line(g,ef,free)
 for x,y,c in [(head[0],head[1],'O'),(rx,ry,'@'),(rx+round(lean*.25),ry-2,'x'),(free[0],free[1],'o')]:
  if 0<=x<W and 0<=y<H:g[y][x]=c
 state=k['contact_state'];hx,hy=hand
 if state=='OPEN':
  if 0<=hx<W and 0<=hy<H:g[hy][hx]='o'
 else:
  g[hy][wx]='o' if state=='TOUCH_ZERO' else '*'
  if k['normal_load']>0:
   n=max(1,min(5,round(k['normal_load']*5)))
   for i in range(1,n+1):
    if wx-i>=0 and g[hy][wx-i]==' ':g[hy][wx-i]='<'
  if k['tangent_load']>0:
   n=max(1,min(5,round(k['tangent_load']*5)))
   for i in range(1,n+1):
    yy=hy-i
    if yy>=0 and g[yy][wx]=='|':g[yy][wx]='^'
  if state=='SLIDE':
   for yy in range(max(1,hy-2),min(fy,hy+3)):
    if yy!=hy and g[yy][wx]=='|':g[yy][wx]='v'
 sc=k['support_contact']
 if 'REAR' in sc or 'BOTH' in sc:g[rear[1]][rear[0]]='!'
 if 'FRONT' in sc or 'BOTH' in sc:g[front[1]][front[0]]='!'
 force_inset(g,k)
 return '\n'.join(''.join(r).rstrip() for r in g)
def sheet(m):
 o=['ASCII KINESIS V2 CONTACT025 — FRICTION-CONE DIRECTIONAL ADMISSIBILITY GATE','Legend: O head | @ root | x COM | o zero/open hand | * closed contact | ! support | : cone boundary | R reaction | D demand | X outside','Primitive: closed contact only carries static tangential support while the demanded force direction remains inside the visible friction cone.','Novelty vs Contact016: force-DIRECTION admissibility is the decisive variable. Patch stays fixed through INSIDE→BOUNDARY; OUTSIDE appears before slide; re-entry precedes restick.','Release: tangential unload → normal unload → zero-load touch → real gap. Source art never enters this rig.','']
 for k in m['keys']:
  full=[r.ljust(m['rig']['grid']['width']) for r in art(k,m).splitlines()]
  crop=[]
  for y in range(8,18):
   r=full[y] if y<len(full) else ' '*m['rig']['grid']['width'];crop.append(r[14:51]+'   '+r[60:77])
  o += [f"{k['key_id']} {k['name']} [{k['timing_class']}/{k['timing_provenance']}]",f"REL={k['relationship_state']} CONTACT={k['contact_state']} CONE={k['cone_status']} N={k['normal_load']:.2f} T={k['tangent_load']:.2f} DEMAND={k['demand_tangent']:.2f}",f"ROOT={k['root']} HAND={k['hand']} SUPPORT={k['support_contact']} FORCE={k['force_owner']} CUSTODY=NONE",*crop,'']
 return '\n'.join(o).rstrip()+'\n'
def frame(k,m,fonts):
 im=Image.new('RGB',tuple(m['compile']['canvas']),(9,10,13));d=ImageDraw.Draw(im)
 d.text((8,5),'CONTACT025 | FRICTION-CONE DIRECTIONAL ADMISSIBILITY',font=fonts[0],fill=(242,242,242));d.text((8,18),f"{k['key_id']}  {k['name']}",font=fonts[0],fill=(242,242,242));y=34
 for ln in art(k,m).splitlines():d.text((8,y),ln,font=fonts[1],fill=(238,238,238));y+=10
 d.text((8,276),f"contact={k['contact_state']}  cone={k['cone_status']}  N={k['normal_load']:.2f}  actual-T={k['tangent_load']:.2f}  demand-T={k['demand_tangent']:.2f}",font=fonts[2],fill=(220,220,220));d.text((8,291),f"rel={k['relationship_state']}  support={k['support_contact']}",font=fonts[2],fill=(220,220,220));d.text((8,306),'fixed patch: force direction sweeps INSIDE -> BOUNDARY -> OUTSIDE/CLAMP -> SLIDE',font=fonts[2],fill=(220,220,220));d.text((8,321),'re-enter cone -> displaced restick -> T unload -> N unload -> release -> overshoot',font=fonts[2],fill=(220,220,220));return im
def gz(s):return base64.b64encode(gzip.compress(s.encode(),compresslevel=9,mtime=0)).decode()
def spa(a,j,v):
 return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Contact025 Friction-Cone Directional Admissibility</title><style>body{margin:0;background:#101116;color:#eee;font-family:system-ui}nav{padding:10px;background:#191b22;position:sticky;top:0}button{margin-right:8px;padding:8px 14px}section{display:none;padding:16px}section.active{display:block}pre{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;border:1px solid #555}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+base64.b64encode(v).decode()+'"></video></section><script>const A="'+gz(a)+'",J="'+gz(j)+'";async function z(s){let u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}Promise.all([z(A),z(J)]).then(x=>{a.textContent=x[0];j.textContent=x[1]});for(const b of document.querySelectorAll("button"))b.onclick=()=>{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view)}</script></body></html>'
def main():
 m=json.loads(M.read_text());A.write_text(sheet(m));shutil.rmtree(B,ignore_errors=True);(B/'f').mkdir(parents=True);fonts=(font(9),font(10),font(8));n=0
 for k in m['keys']:
  for _ in range(HOLD[k['timing_class']]):frame(k,m,fonts).save(B/'f'/f'{n:04d}.png');n+=1
 subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(B/'f'/'%04d.png'),'-map_metadata','-1','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-crf','40','-movflags','+faststart','-fflags','+bitexact','-flags:v','+bitexact',str(V)],check=True)
 v=V.read_bytes();h=hashlib.sha256(v).hexdigest();e=m['compile'].get('media_sha256')
 if e and h!=e:raise SystemExit(f'MEDIA_IDENTITY_MISMATCH {e} != {h}')
 if not e:
  m['compile']['media_sha256']=h;m['compile']['media_bytes']=len(v);m['compile']['actual_decode']='PASS_CURRENT_WORKER_ACTUAL_RENDER';M.write_text(json.dumps(m,separators=(',',':'),ensure_ascii=False)+'\n');A.write_text(sheet(m))
 S.write_text(spa(A.read_text(),M.read_text(),v));print(json.dumps({'ok':True,'frames':n,'media_sha256':h,'media_bytes':len(v)},sort_keys=True))
if __name__=='__main__':main()
