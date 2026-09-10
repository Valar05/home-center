#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import base64,gzip,hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent;M=R/"motion.json";A=R/"contact-sheet.txt";B=R/".motion-build";V=B/"motion.mp4";S=R/"unilateral-hook-contact-force-sign-gate.motion.html"
HOLD={"ONES":1,"TWOS":2,"FOURS":4};CANVAS=(560,330)
BONES=[("head","neck"),("neck","shoulder_l"),("neck","shoulder_r"),("shoulder_l","elbow_l"),("elbow_l","hand_l"),("shoulder_r","elbow_r"),("elbow_r","hand_r"),("neck","pelvis"),("pelvis","knee_l"),("knee_l","foot_l"),("pelvis","knee_r"),("knee_r","foot_r")]
def font(n):
 p=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
 if not p.is_file():raise SystemExit("MISSING_REQUIRED_FONT")
 return ImageFont.truetype(str(p),n)
def bres(a,b):
 x0,y0=a;x1,y1=b;o=[];dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
 while 1:
  o.append((x0,y0))
  if (x0,y0)==(x1,y1):return o
  e2=2*e
  if e2>=dy:e+=dy;x0+=sx
  if e2<=dx:e+=dx;y0+=sy
def pose(k,floor):
 q=k["pose_rig"];px,py=q["pelvis"];lean=q["lean"];c=q["compact"];am=q["arm_mode"];lm=q["leg_mode"]
 neck=(px+round(lean*.55),py-(5-c));head=(px+round(lean*.8),neck[1]-2);sl=(neck[0]-2,neck[1]+1);sr=(neck[0]+2,neck[1]+1)
 if am in ("reach","grip"):er=(sr[0]+3,sr[1]+1);hr=(er[0]+3,er[1]);el=(sl[0]+1,sl[1]+2);hl=(el[0]+4,el[1])
 elif am in ("pull","pull_soft"):er=(sr[0]+4,sr[1]+1);hr=(er[0]+3,er[1]-1);el=(sl[0]+2,sl[1]+2);hl=(el[0]+4,el[1]-1)
 elif am=="lift":er=(sr[0]+3,sr[1]-1);hr=(er[0]+3,er[1]-2);el=(sl[0]+2,sl[1]);hl=(el[0]+4,el[1]-2)
 elif am=="recover":er=(sr[0]+2,sr[1]-2);hr=(er[0]+3,er[1]-2);el=(sl[0]+2,sl[1]);hl=(el[0]+3,el[1]-2)
 elif am=="lag":er=(sr[0]+1,sr[1]+2);hr=(er[0]+3,er[1]+1);el=(sl[0]-1,sl[1]+2);hl=(el[0]+3,el[1]+1)
 elif am in ("carry_low","carry"):er=(sr[0]+2,sr[1]+2);hr=(er[0]+3,er[1]+2);el=(sl[0]+1,sl[1]+3);hl=(el[0]+3,el[1]+1)
 else:er=(sr[0]+2,sr[1]+2);hr=(er[0]+3,er[1]+1);el=(sl[0]+1,sl[1]+2);hl=(el[0]+3,el[1]+1)
 if lm=="step":kl=(px-2,py+2);fl=(px-4,floor);kr=(px+3,py+2);fr=(px+6,floor)
 elif lm=="front":kl=(px-1,py+2);fl=(px-3,floor);kr=(px+3,py+2);fr=(px+6,floor)
 elif lm=="rear":kl=(px-3,py+2);fl=(px-6,floor);kr=(px+2,py+2);fr=(px+4,floor)
 elif lm=="rear_deep":kl=(px-4,py+1);fl=(px-7,floor);kr=(px+2,py+2);fr=(px+5,floor)
 else:kl=(px-2,py+2);fl=(px-4,floor);kr=(px+2,py+2);fr=(px+4,floor)
 return {"head":head,"neck":neck,"shoulder_l":sl,"shoulder_r":sr,"elbow_l":el,"hand_l":hl,"elbow_r":er,"hand_r":hr,"pelvis":(px,py),"knee_l":kl,"foot_l":fl,"knee_r":kr,"foot_r":fr}
def lchar(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 return "-" if abs(dx)>=2*abs(dy) else ("|" if abs(dy)>=2*abs(dx) else ("\\" if dx*dy>0 else "/"))
def hook_cells(k,head):
 hx,hy=head;mode=k["hook_mode"]
 if mode in ("CLOSED","SEATED"):return [(48,11,")"),(49,11,"_"),(49,12,"X"),(49,13,"J")]
 if mode=="EDGE_TOUCH":return [(49,10,")"),(50,10,"_"),(50,11,"X"),(49,11,"J")]
 return [(hx,hy,")"),(hx-1,hy,"_"),(hx,hy+1,"J")]
def art(k,m,override_pose=None,override_head=None):
 W=m["rig"]["grid"]["width"];H=m["rig"]["grid"]["height"];fy=m["rig"]["grid"]["floor_y"];g=[[" "]*W for _ in range(H)]
 p=override_pose or pose(k,fy);head=override_head or tuple(k["tool_head"]);hand=p["hand_r"]
 for x in range(2,W-2):g[fy][x]="_"
 for y in range(7,24):
  if g[y][50]==" ":g[y][50]="#"
 g[12][50]="@"
 for a,b in BONES:
  for x,y in bres(p[a],p[b])[1:-1]:
   if 0<=x<W and 0<=y<H and g[y][x]==" ":g[y][x]=lchar(p[a],p[b])
 for n,(x,y) in p.items():
  if 0<=x<W and 0<=y<H:g[y][x]="O" if n=="head" else ("+" if n=="pelvis" else "o")
 px,py=p["pelvis"]
 if 0<=py-1<H and g[py-1][px]==" ":g[py-1][px]="x"
 ch="=" if k["constraint_load"]>0 else "-"
 for x,y in bres(hand,head)[1:-1]:
  if 0<=x<W and 0<=y<H and g[y][x]==" ":g[y][x]=ch
 if k["constraint_load"]>0:
  y=max(2,min(H-2,head[1]-2))
  for i,ch2 in enumerate("<<<"):
   x=head[0]-7+i
   if 0<=x<W and g[y][x]==" ":g[y][x]=ch2
 for x,y,ch2 in hook_cells(k,head):
  if 0<=x<W and 0<=y<H:g[y][x]=ch2
 sc=k["support_contact"]
 if "REAR" in sc:
  x,y=p["foot_l"];g[y][x]="!"
 elif "FRONT" in sc:
  x,y=p["foot_r"];g[y][x]="!"
 elif "BOTH" in sc:
  for n in ("foot_l","foot_r"):
   x,y=p[n];g[y][x]="!"
 return "\n".join("".join(r).rstrip() for r in g)
def sheet(m):
 o=["ASCII KINESIS V2 CONTACT023 — UNILATERAL HOOK CONTACT FORCE-SIGN GATE",
 "Legend: # fixed post | @ fixed peg | J/) generic hook | X closed contact | - unloaded shaft | = loaded shaft | + root | x COM | ! owning ground support",
 "Topology truth: CLOSED hook contact may carry ZERO load; force exists only while motion/load seats the hook into its blocking face. Environment custody is NONE.",
 "Independent abstract ASCII rig only; no source art.",""]
 for k in m["keys"]:
  o += [f'{k["key_id"]}  {k["name"]}  [{k["timing_class"]}/{k["timing_provenance"]}]',
        f'CONTACT={k["contact_state"]}  REL={k["relationship_state"]}  SUPPORT={k["support_contact"]}  ENV_CUSTODY={k["environment_custody"]}',
        f'HOOK={k["hook_mode"]}  LOAD={k["constraint_load"]:.2f}  INTENT={k["relative_intent"]}  FORCE_AXIS={k["force_axis"]}',
        f'CAUSE: {k["root_com_note"]}',art(k,m),""]
 return "\n".join(o).rstrip()+"\n"
def ease(t):return t*t*(3-2*t)
def bridge(a,b,m):
 e=ease(.58);fy=m["rig"]["grid"]["floor_y"];pa=pose(a,fy);pb=pose(b,fy);p={}
 for n in pa:p[n]=(round(pa[n][0]+(pb[n][0]-pa[n][0])*e),round(pa[n][1]+(pb[n][1]-pa[n][1])*e))
 ha=tuple(a["tool_head"]);hb=tuple(b["tool_head"]);h=(round(ha[0]+(hb[0]-ha[0])*e),round(ha[1]+(hb[1]-ha[1])*e))
 k=dict(a);k["name"]=a["name"]+" -> "+b["name"]
 if a["contact_state"]==b["contact_state"] and a["relationship_state"]==b["relationship_state"]:k["constraint_load"]=a["constraint_load"]+(b["constraint_load"]-a["constraint_load"])*e
 return k,p,h
def frame(k,m,fonts,p=None,h=None):
 im=Image.new("RGB",CANVAS,(10,10,12));d=ImageDraw.Draw(im);d.text((8,5),"CONTACT023 | UNILATERAL HOOK CONTACT FORCE-SIGN GATE",font=fonts[0],fill=(235,235,235));d.text((8,17),f'{k["key_id"]}  {k["name"]}',font=fonts[0],fill=(235,235,235));y=30
 for ln in art(k,m,p,h).splitlines():d.text((8,y),ln,font=fonts[1],fill=(242,242,242));y+=9
 d.text((8,301),f'contact={k["contact_state"]} load={k["constraint_load"]:.2f} support={k["support_contact"]}',font=fonts[2],fill=(220,220,220))
 d.text((8,313),"closed contact != force != custody | unload -> unseat -> release",font=fonts[2],fill=(220,220,220));return im
def gz(s):return base64.b64encode(gzip.compress(s.encode(),compresslevel=9,mtime=0)).decode()
def spa(a,j,v):
 return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Contact023 Unilateral Hook Contact Force-Sign Gate</title><style>body{margin:0;background:#111;color:#eee;font-family:system-ui}nav{padding:10px;background:#191919}button{margin-right:8px;padding:8px 14px}section{display:none;padding:16px}section.active{display:block}pre{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;border:1px solid #555}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+base64.b64encode(v).decode()+'"></video></section><script>const A="'+gz(a)+'",J="'+gz(j)+'";async function z(s){let u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}Promise.all([z(A),z(J)]).then(x=>{a.textContent=x[0];j.textContent=x[1]});for(const b of document.querySelectorAll("button"))b.onclick=()=>{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view)}</script></body></html>'
def main():
 m=json.loads(M.read_text());A.write_text(sheet(m));shutil.rmtree(B,ignore_errors=True);(B/"f").mkdir(parents=True);fonts=(font(8),font(9),font(7));n=0
 for i,k in enumerate(m["keys"]):
  for _ in range(HOLD[k["timing_class"]]):frame(k,m,fonts).save(B/"f"/f"{n:04}.png");n+=1
  if i+1<len(m["keys"]):q,p,h=bridge(k,m["keys"][i+1],m);frame(q,m,fonts,p,h).save(B/"f"/f"{n:04}.png");n+=1
 subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(B/"f"/"%04d.png"),"-map_metadata","-1","-c:v","libx264","-threads","1","-pix_fmt","yuv420p","-crf","42","-movflags","+faststart","-fflags","+bitexact","-flags:v","+bitexact",str(V)],check=True)
 v=V.read_bytes();h=hashlib.sha256(v).hexdigest();e=m["compile"].get("media_sha256")
 if e and h!=e:raise SystemExit(f"MEDIA_IDENTITY_MISMATCH {e} != {h}")
 S.write_text(spa(A.read_text(),M.read_text(),v));print(json.dumps({"ok":True,"frames":n,"media_sha256":h,"media_bytes":len(v)},sort_keys=True))
if __name__=="__main__":main()
