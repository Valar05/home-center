#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import base64,gzip,hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;M=R/'motion.json';A=R/'contact-sheet.txt';B=R/'.motion-build';V=B/'motion.mp4';S=R/'friction-cone-stick-slip-support-gate.motion.html'
CANVAS=(560,330);HOLD={'ONES':1,'TWOS':2,'FOURS':4}
def font(n):
 p=Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
 if not p.is_file(): raise SystemExit('MISSING_REQUIRED_FONT')
 return ImageFont.truetype(str(p),n)
def line(g,a,b,ch=None):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy;pts=[]
 while True:
  pts.append((x0,y0))
  if (x0,y0)==(x1,y1): break
  e2=2*e
  if e2>=dy:e+=dy;x0+=sx
  if e2<=dx:e+=dx;y0+=sy
 for i,(x,y) in enumerate(pts[1:-1],1):
  if 0<=y<len(g) and 0<=x<len(g[0]) and g[y][x]==' ':
   if ch:g[y][x]=ch
   else:
    px,py=pts[i-1];nx,ny=pts[i+1];ddx=nx-px;ddy=ny-py
    g[y][x]='-' if abs(ddx)>=2*abs(ddy) else ('|' if abs(ddy)>=2*abs(ddx) else ('\\' if ddx*ddy>0 else '/'))
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
 if 'REAR' in sc or 'BOTH' in sc: g[rear[1]][rear[0]]='!'
 if 'FRONT' in sc or 'BOTH' in sc: g[front[1]][front[0]]='!'
 return '\n'.join(''.join(r).rstrip() for r in g)
def sheet(m):
 o=['ASCII KINESIS V2 CONTACT025 — FRICTION-CONE STICK/SLIP SUPPORT GATE','Legend: O head | @ root | x COM | o zero/open hand | * closed loaded contact | | wall | < normal force | ^ tangent support | v sliding patch | ! ground support','Primitive: contact topology can remain CLOSED while tangential authority changes STICK -> SLIDE -> RESTICK. Custody stays NONE.','Release law: unload tangential force, then normal force, preserve one zero-load touch, then open a real gap. Source art never enters this rig.','']
 for k in m['keys']:
  o += [f"{k['key_id']}  {k['name']}  [{k['timing_class']}/{k['timing_provenance']}]",f"REL={k['relationship_state']}  CONTACT={k['contact_state']}  N={k['normal_load']:.2f}  T={k['tangent_load']:.2f}",f"SUPPORT={k['support_contact']}  FORCE_OWNER={k['force_owner']}  CUSTODY=NONE",f"CAUSE: {k['root_com_note']}",art(k,m),'']
 return '\n'.join(o).rstrip()+'\n'
def frame(k,m,fonts):
 im=Image.new('RGB',CANVAS,(9,10,13));d=ImageDraw.Draw(im)
 d.text((8,5),'CONTACT025 | FRICTION-CONE STICK/SLIP SUPPORT GATE',font=fonts[0],fill=(242,242,242));d.text((8,18),f"{k['key_id']}  {k['name']}",font=fonts[0],fill=(242,242,242));y=34
 for ln in art(k,m).splitlines():d.text((8,y),ln,font=fonts[1],fill=(238,238,238));y+=10
 d.text((8,266),f"contact={k['contact_state']}  N={k['normal_load']:.2f}  T={k['tangent_load']:.2f}",font=fonts[2],fill=(220,220,220));d.text((8,280),f"rel={k['relationship_state']}  support={k['support_contact']}",font=fonts[2],fill=(220,220,220));d.text((8,294),'CLOSED topology can lose static tangential authority without release',font=fonts[2],fill=(220,220,220));d.text((8,308),'stick -> impending slip -> slide -> displaced restick -> unload -> release',font=fonts[2],fill=(220,220,220));return im
def gz(s):return base64.b64encode(gzip.compress(s.encode(),compresslevel=9,mtime=0)).decode()
def spa(a,j,v):
 return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Contact025 Friction-Cone Stick/Slip Support Gate</title><style>body{margin:0;background:#101116;color:#eee;font-family:system-ui}nav{padding:10px;background:#191b22;position:sticky;top:0}button{margin-right:8px;padding:8px 14px}section{display:none;padding:16px}section.active{display:block}pre{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;border:1px solid #555}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+base64.b64encode(v).decode()+'"></video></section><script>const A="'+gz(a)+'",J="'+gz(j)+'";async function z(s){let u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}Promise.all([z(A),z(J)]).then(x=>{a.textContent=x[0];j.textContent=x[1]});for(const b of document.querySelectorAll("button"))b.onclick=()=>{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view)}</script></body></html>'
def main():
 m=json.loads(M.read_text());A.write_text(sheet(m));shutil.rmtree(B,ignore_errors=True);(B/'f').mkdir(parents=True);fonts=(font(9),font(10),font(8));n=0
 for k in m['keys']:
  for _ in range(HOLD[k['timing_class']]):frame(k,m,fonts).save(B/'f'/f'{n:04d}.png');n+=1
 subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(B/'f'/'%04d.png'),'-map_metadata','-1','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-crf','40','-movflags','+faststart','-fflags','+bitexact','-flags:v','+bitexact',str(V)],check=True)
 v=V.read_bytes();h=hashlib.sha256(v).hexdigest();e=m['compile'].get('media_sha256')
 if e and h!=e:raise SystemExit(f'MEDIA_IDENTITY_MISMATCH {e} != {h}')
 S.write_text(spa(A.read_text(),M.read_text(),v));print(json.dumps({'ok':True,'frames':n,'media_sha256':h,'media_bytes':len(v)},sort_keys=True))
if __name__=='__main__':main()
