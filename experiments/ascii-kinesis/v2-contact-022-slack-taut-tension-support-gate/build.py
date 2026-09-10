#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import base64,gzip,hashlib,json,math,shutil,subprocess
R=Path(__file__).resolve().parent;M=R/"motion.json";A=R/"contact-sheet.txt";B=R/".motion-build";V=B/"motion.mp4";S=R/"slack-taut-tension-support-gate.motion.html"
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
 if am=="trail_left":el=(sl[0]-3,sl[1]+1);hl=(el[0]-2,el[1]+1);er=(sr[0]+2,sr[1]+2);hr=(er[0]+2,er[1]+1)
 elif am=="counter_right":el=(sl[0]-2,sl[1]+2);hl=(el[0]-1,el[1]+2);er=(sr[0]+3,sr[1]-1);hr=(er[0]+2,er[1]-1)
 elif am=="wide":el=(sl[0]-3,sl[1]);hl=(el[0]-3,el[1]-1);er=(sr[0]+3,sr[1]);hr=(er[0]+3,er[1]+1)
 elif am=="brace":el=(sl[0]-2,sl[1]+2);hl=(px-3,py-1);er=(sr[0]+2,sr[1]+2);hr=(px+3,py-1)
 else:el=(sl[0]-2,sl[1]+2);hl=(el[0],el[1]+2);er=(sr[0]+2,sr[1]+2);hr=(er[0],er[1]+2)
 if lm=="air_split":kl=(px-3,py+2);fl=(px-6,py+3);kr=(px+2,py+3);fr=(px+5,py+4)
 elif lm=="trail":kl=(px-3,py+2);fl=(px-5,py+4);kr=(px+2,py+2);fr=(px+4,py+1)
 elif lm=="probe":kl=(px-2,py+2);fl=(px-3,py+4);kr=(px+2,py+2);fr=(px+4,py+4)
 elif lm=="catch":kl=(px-2,py+2);fl=(px-4,floor);kr=(px+2,py+2);fr=(px+4,py+3)
 elif lm=="dual":kl=(px-2,py+2);fl=(px-4,floor);kr=(px+2,py+2);fr=(px+4,floor)
 else:kl=(px-2,py+3);fl=(px-3,py+5);kr=(px+2,py+3);fr=(px+3,py+5)
 return {"head":head,"neck":neck,"shoulder_l":sl,"shoulder_r":sr,"elbow_l":el,"hand_l":hl,"elbow_r":er,"hand_r":hr,"pelvis":(px,py),"knee_l":kl,"foot_l":fl,"knee_r":kr,"foot_r":fr}
def lchar(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 return "-" if abs(dx)>=2*abs(dy) else ("|" if abs(dy)>=2*abs(dx) else ("\\" if dx*dy>0 else "/"))
def tether(a,p,state):
 if state=="TAUT":return bres(a,p)
 ax,ay=a;px,py=p;n=max(abs(px-ax),abs(py-ay),8);s=3 if state=="SLACK" else 1;o=[]
 for i in range(n+1):
  t=i/n;q=(round(ax+(px-ax)*t),round(ay+(py-ay)*t+4*s*t*(1-t)))
  if not o or q!=o[-1]:o.append(q)
 return o
def art(k,m,override_pose=None):
 W=m["rig"]["grid"]["width"];H=m["rig"]["grid"]["height"];fy=m["rig"]["grid"]["floor_y"];g=[[" "]*W for _ in range(H)];ax,ay=k["anchor"];g[ay][ax]="@";p=override_pose or pose(k,fy);pel=p["pelvis"];ch="=" if k["tension_load"]>0 else (":" if k["tether_state"]=="TAUT" else "~")
 for x,y in tether((ax,ay),pel,k["tether_state"])[1:-1]:
  if 0<=x<W and 0<=y<H and g[y][x]==" ":g[y][x]=ch
 for x in range(2,W-2):g[fy][x]="_"
 for a,b in BONES:
  for x,y in bres(p[a],p[b])[1:-1]:
   if 0<=x<W and 0<=y<H and g[y][x]==" ":g[y][x]=lchar(p[a],p[b])
 for n,(x,y) in p.items():
  if 0<=x<W and 0<=y<H:g[y][x]="O" if n=="head" else ("+" if n=="pelvis" else "o")
 px,py=pel
 if 0<=py-1<H and g[py-1][px]==" ":g[py-1][px]="x"
 if "GROUND_LEFT" in k["support_contact"] or "GROUND_BOTH" in k["support_contact"]:x,y=p["foot_l"];g[y][x]="!"
 if "GROUND_RIGHT" in k["support_contact"] or "GROUND_BOTH" in k["support_contact"]:x,y=p["foot_r"];g[y][x]="!"
 return "\n".join("".join(r).rstrip() for r in g)
def sheet(m):
 o=["ASCII KINESIS V2 CONTACT022 — SLACK / TAUT TENSION SUPPORT GATE","Legend: @ fixed anchor | ~ slack | : taut zero-load | = taut loaded | + harness/root | x COM | ! ground support","Independent abstract ASCII rig only; no source art.",""]
 for k in m["keys"]:o += [f'{k["key_id"]}  {k["name"]}  [{k["timing_class"]}/{k["timing_provenance"]}]',f'ATTACHMENT={k["contact_state"]}  REL={k["relationship_state"]}  SUPPORT={k["support_contact"]}  CUSTODY={k["custody"]}',f'TETHER={k["tether_state"]}  TENSION={k["tension_load"]:.2f}  LENGTH={k["length_at_key"]:.3f}/{k["max_length"]:.3f}  FORCE_AXIS={k["force_axis"]}',f'CAUSE: {k["root_com_note"]}',art(k,m),""]
 return "\n".join(o).rstrip()+"\n"
def ease(t):return t*t*(3-2*t)
def bridge(a,b,m):
 e=ease(.55);fy=m["rig"]["grid"]["floor_y"];pa=pose(a,fy);pb=pose(b,fy);aa=a["anchor"];L=a["max_length"];p0=pa["pelvis"];p1=pb["pelvis"]
 if a["tether_state"]=="TAUT" and b["tether_state"]=="TAUT":
  x0=math.atan2(p0[1]-aa[1],p0[0]-aa[0]);x1=math.atan2(p1[1]-aa[1],p1[0]-aa[0]);d=(x1-x0+math.pi)%(2*math.pi)-math.pi;ang=x0+d*e;pc=(aa[0]+L*math.cos(ang),aa[1]+L*math.sin(ang))
 else:pc=(p0[0]+(p1[0]-p0[0])*e,p0[1]+(p1[1]-p0[1])*e)
 q={}
 for n in pa:
  if n=="pelvis":q[n]=(round(pc[0]),round(pc[1]));continue
  ao=(pa[n][0]-p0[0],pa[n][1]-p0[1]);bo=(pb[n][0]-p1[0],pb[n][1]-p1[1]);q[n]=(round(pc[0]+ao[0]+(bo[0]-ao[0])*e),round(pc[1]+ao[1]+(bo[1]-ao[1])*e))
 k=dict(a);k["name"]=a["name"]+" -> "+b["name"]
 if a["tether_state"]=="TAUT" and b["tether_state"]=="TAUT":k["tension_load"]=a["tension_load"]+(b["tension_load"]-a["tension_load"])*e
 return k,q
def frame(k,m,fonts,p=None):
 im=Image.new("RGB",CANVAS,(10,10,12));d=ImageDraw.Draw(im);d.text((8,5),"CONTACT022 | SLACK->TAUT TENSION SUPPORT GATE",font=fonts[0],fill=(235,235,235));d.text((8,17),f'{k["key_id"]}  {k["name"]}',font=fonts[0],fill=(235,235,235));y=30
 for ln in art(k,m,p).splitlines():d.text((8,y),ln,font=fonts[1],fill=(242,242,242));y+=9
 d.text((8,298),f'attachment=ATTACHED  tether={k["tether_state"]}  tension={k["tension_load"]:.2f}  support={k["support_contact"]}',font=fonts[2],fill=(220,220,220));d.text((8,310),"force can turn ON/OFF without attachment topology changing",font=fonts[2],fill=(220,220,220));return im
def gz(s):return base64.b64encode(gzip.compress(s.encode(),compresslevel=9,mtime=0)).decode()
def spa(a,j,v):
 return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Contact022 Slack-Taut Tension Support Gate</title><style>body{{margin:0;background:#111;color:#eee;font-family:system-ui}}nav{{padding:10px;background:#191919}}button{{margin-right:8px;padding:8px 14px}}section{{display:none;padding:16px}}section.active{{display:block}}pre{{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}video{{max-width:100%;border:1px solid #555}}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{base64.b64encode(v).decode()}"></video></section><script>const A="{gz(a)}",J="{gz(j)}";async function z(s){{let u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([z(A),z(J)]).then(x=>{{a.textContent=x[0];j.textContent=x[1]}});for(const b of document.querySelectorAll("button"))b.onclick=()=>{{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view[0])}}</script></body></html>'''
def main():
 m=json.loads(M.read_text());A.write_text(sheet(m));shutil.rmtree(B,ignore_errors=True);(B/"f").mkdir(parents=True);fonts=(font(8),font(9),font(7));n=0
 for i,k in enumerate(m["keys"]):
  for _ in range(HOLD[k["timing_class"]]):frame(k,m,fonts).save(B/"f"/f"{n:04}.png");n+=1
  if i+1<len(m["keys"]):q,p=bridge(k,m["keys"][i+1],m);frame(q,m,fonts,p).save(B/"f"/f"{n:04}.png");n+=1
 subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(B/"f"/"%04d.png"),"-map_metadata","-1","-c:v","libx264","-threads","1","-pix_fmt","yuv420p","-crf","38","-movflags","+faststart","-fflags","+bitexact","-flags:v","+bitexact",str(V)],check=True)
 v=V.read_bytes();h=hashlib.sha256(v).hexdigest();e=m["compile"].get("media_sha256")
 if e and h!=e:raise SystemExit(f"MEDIA_IDENTITY_MISMATCH {e} != {h}")
 S.write_text(spa(A.read_text(),M.read_text(),v));print(json.dumps({"ok":True,"frames":n,"media_sha256":h,"media_bytes":len(v)},sort_keys=True))
if __name__=="__main__":main()
