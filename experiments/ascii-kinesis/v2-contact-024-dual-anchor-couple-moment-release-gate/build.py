#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import base64,gzip,hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;M=R/"motion.json";A=R/"contact-sheet.txt";B=R/".motion-build";V=B/"motion.mp4";S=R/"dual-anchor-couple-moment-release-gate.motion.html"
CANVAS=(600,340);HOLD={"ONES":1,"TWOS":2,"FOURS":4}
def font(n):
 p=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
 if not p.is_file():raise SystemExit("MISSING_REQUIRED_FONT")
 return ImageFont.truetype(str(p),n)
def line(g,a,b,ch=None):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
 pts=[]
 while True:
  pts.append((x0,y0))
  if (x0,y0)==(x1,y1):break
  e2=2*e
  if e2>=dy:e+=dy;x0+=sx
  if e2<=dx:e+=dx;y0+=sy
 for i,(x,y) in enumerate(pts[1:-1],1):
  if 0<=y<len(g) and 0<=x<len(g[0]) and g[y][x]==" ":
   if ch:g[y][x]=ch
   else:
    px,py=pts[i-1];nx,ny=pts[i+1];ddx=nx-px;ddy=ny-py
    g[y][x]="-" if abs(ddx)>=2*abs(ddy) else ("|" if abs(ddy)>=2*abs(ddx) else ("\\" if ddx*ddy>0 else "/"))
def body(g,root,lean,side,compact,floor,contact_xs,contact_ys):
 rx,ry=root; neck=(rx+round(lean*.55),ry-(5-compact)); head=(rx+lean,neck[1]-2); sh=(neck[0],neck[1]+1)
 line(g,head,neck,"|");line(g,neck,(rx,ry),"|")
 if side=="A":
  rear=(rx-5,floor);front=(rx+5,floor)
 else:
  rear=(rx+5,floor);front=(rx-5,floor)
 line(g,(rx,ry),rear);line(g,(rx,ry),front)
 ux,lx=contact_xs;uy,ly=contact_ys
 if side=="A":
  e1=(sh[0]+4,sh[1]-1); e2=(sh[0]+3,sh[1]+3)
 else:
  e1=(sh[0]-4,sh[1]-1); e2=(sh[0]-3,sh[1]+3)
 line(g,sh,e1);line(g,e1,(ux,uy));line(g,sh,e2);line(g,e2,(lx,ly))
 for x,y,c in [(head[0],head[1],"O"),(rx,ry,"@"),(rx+round(lean*.35),ry-2,"x"),(ux,uy,"o"),(lx,ly,"o")]:
  if 0<=y<len(g) and 0<=x<len(g[0]):g[y][x]=c
 return {"rear":rear,"front":front,"upper":(ux,uy),"lower":(lx,ly),"root":(rx,ry),"head":head}
def link(g,a,b,state,load,row):
 ax,ay=a;bx,by=b
 if state=="OPEN": return
 g[ay][ax]="*";g[by][bx]="*"
 ch="=" if state.startswith("LOADED") else "-"
 for x in range(ax+1,bx):
  if g[row][x]==" ":g[row][x]=ch
 if state.startswith("LOADED"):
  arrows=">>>>" if load>0 else "<<<<"
  start=(ax+bx)//2-len(arrows)//2
  yy=max(1,row-1 if load>0 else row+1)
  for i,c in enumerate(arrows):
   if 0<=start+i<len(g[0]) and g[yy][start+i]==" ":g[yy][start+i]=c
def art(k,m):
 W=m["rig"]["grid"]["width"];H=m["rig"]["grid"]["height"];fy=m["rig"]["grid"]["floor_y"];g=[[" "]*W for _ in range(H)]
 for x in range(1,W-1):g[fy][x]="_"
 cx=W//2
 arx=k["a_root"][0];brx=k["b_root"][0]
 au=(cx-4,6) if k["upper_state"]!="OPEN" else (arx+7,6)
 bu=(cx+4,6) if k["upper_state"]!="OPEN" else (brx-7,6)
 al=(cx-4,10) if k["lower_state"]!="OPEN" else (arx+6,10)
 bl=(cx+4,10) if k["lower_state"]!="OPEN" else (brx-6,10)
 A=body(g,tuple(k["a_root"]),k["a_lean"],"A",k["compact"],fy,(au[0],al[0]),(au[1],al[1]))
 B=body(g,tuple(k["b_root"]),k["b_lean"],"B",k["compact"],fy,(bu[0],bl[0]),(bu[1],bl[1]))
 link(g,A["upper"],B["upper"],k["upper_state"],k["upper_load"],6)
 link(g,A["lower"],B["lower"],k["lower_state"],k["lower_load"],10)
 sc=k["support_contact"]
 for label,pt in [("A_REAR",A["rear"]),("A_FRONT",A["front"]),("B_REAR",B["rear"]),("B_FRONT",B["front"])]:
  if label in sc or "BOTH" in sc:
   x,y=pt
   if 0<=x<W:g[y][x]="!"
 if k["relationship_state"] not in ("SEPARATE","ELIGIBLE","SEPARATE_DISPLACED","SEPARATED_RELEASE"):
  g[8][cx]="R"
 return "\n".join("".join(r).rstrip() for r in g)
def sheet(m):
 o=["ASCII KINESIS V2 CONTACT024 — DUAL-ANCHOR COUPLE MOMENT RELEASE GATE",
 "Legend: A/B abstract bodies | O head | @ root | x COM | o hand | * closed contact | - zero-load contact | = loaded contact | R relationship center | ! ground support | >/< force sign",
 "Primitive: two separated closed anchors can carry equal-opposed forces with near-zero resultant translation but a visible couple moment. Custody stays NONE.",
 "Release law: unload an anchor to zero while still touching, then open that anchor. Upper releases before lower. Source art never enters the rig.",""]
 for k in m["keys"]:
  o += [f'{k["key_id"]}  {k["name"]}  [{k["timing_class"]}/{k["timing_provenance"]}]',
        f'REL={k["relationship_state"]}  UPPER={k["upper_state"]}:{k["upper_load"]:+.2f}  LOWER={k["lower_state"]}:{k["lower_load"]:+.2f}',
        f'SUPPORT={k["support_contact"]}  FORCE_OWNER={k["force_owner"]}  CUSTODY=NONE',
        f'CAUSE: {k["root_com_note"]}',art(k,m),""]
 return "\n".join(o).rstrip()+"\n"
def frame(k,m,fonts):
 im=Image.new("RGB",CANVAS,(9,10,13));d=ImageDraw.Draw(im)
 d.text((8,5),"CONTACT024 | DUAL-ANCHOR COUPLE MOMENT RELEASE GATE",font=fonts[0],fill=(242,242,242))
 d.text((8,18),f'{k["key_id"]}  {k["name"]}',font=fonts[0],fill=(242,242,242));y=33
 for ln in art(k,m).splitlines():d.text((8,y),ln,font=fonts[1],fill=(238,238,238));y+=10
 d.text((8,278),f'upper={k["upper_state"]}:{k["upper_load"]:+.2f}  lower={k["lower_state"]}:{k["lower_load"]:+.2f}',font=fonts[2],fill=(220,220,220))
 d.text((8,292),f'rel={k["relationship_state"]}  support={k["support_contact"]}',font=fonts[2],fill=(220,220,220))
 d.text((8,306),"dual contact != custody | force couple -> unload -> release -> unequal overshoot",font=fonts[2],fill=(220,220,220));return im
def gz(s):return base64.b64encode(gzip.compress(s.encode(),compresslevel=9,mtime=0)).decode()
def spa(a,j,v):
 return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Contact024 Dual-Anchor Couple Moment Release Gate</title><style>body{margin:0;background:#101116;color:#eee;font-family:system-ui}nav{padding:10px;background:#191b22;position:sticky;top:0}button{margin-right:8px;padding:8px 14px}section{display:none;padding:16px}section.active{display:block}pre{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;border:1px solid #555}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+base64.b64encode(v).decode()+'"></video></section><script>const A="'+gz(a)+'",J="'+gz(j)+'";async function z(s){let u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}Promise.all([z(A),z(J)]).then(x=>{a.textContent=x[0];j.textContent=x[1]});for(const b of document.querySelectorAll("button"))b.onclick=()=>{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view)}</script></body></html>'
def main():
 m=json.loads(M.read_text());A.write_text(sheet(m));shutil.rmtree(B,ignore_errors=True);(B/"f").mkdir(parents=True);fonts=(font(9),font(10),font(8));n=0
 for k in m["keys"]:
  for _ in range(HOLD[k["timing_class"]]):frame(k,m,fonts).save(B/"f"/f"{n:04d}.png");n+=1
 subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(B/"f"/"%04d.png"),"-map_metadata","-1","-c:v","libx264","-threads","1","-pix_fmt","yuv420p","-crf","40","-movflags","+faststart","-fflags","+bitexact","-flags:v","+bitexact",str(V)],check=True)
 v=V.read_bytes();h=hashlib.sha256(v).hexdigest();e=m["compile"].get("media_sha256")
 if e and h!=e:raise SystemExit(f"MEDIA_IDENTITY_MISMATCH {e} != {h}")
 S.write_text(spa(A.read_text(),M.read_text(),v));print(json.dumps({"ok":True,"frames":n,"media_sha256":h,"media_bytes":len(v)},sort_keys=True))
if __name__=="__main__":main()
