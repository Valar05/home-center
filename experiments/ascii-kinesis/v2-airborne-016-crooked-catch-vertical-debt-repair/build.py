#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
H=Path(__file__).resolve().parent; M=H/"motion.json"; SPA=H/"crooked-catch-vertical-debt-repair.motion.html"
W,HH,G=72,27,23
HOLDS={"ONES":1,"TWOS":2,"FOURS":4}
J=["head","neck","shoulder_l","shoulder_r","elbow_l","elbow_r","hand_l","hand_r","pelvis","knee_l","knee_r","foot_l","foot_r"]
L=[("head","neck"),("neck","shoulder_l"),("neck","shoulder_r"),("shoulder_l","elbow_l"),("elbow_l","hand_l"),("shoulder_r","elbow_r"),("elbow_r","hand_r"),("neck","pelvis"),("pelvis","knee_l"),("knee_l","foot_l"),("pelvis","knee_r"),("knee_r","foot_r")]
def pm(o): return dict(zip(J,([int(n) for n in q.split(",")] for q in o["pose_rig"].split(";"))))
def line(a,b):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy;r=[]
 while 1:
  r.append((x0,y0))
  if (x0,y0)==(x1,y1): return r
  e2=2*e
  if e2>=dy:e+=dy;x0+=sx
  if e2<=dx:e+=dx;y0+=sy
def glyph(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 return "-" if abs(dx)>abs(dy)*1.8 else ("|" if abs(dy)>abs(dx)*1.8 else ("\\" if dx*dy>0 else "/"))
def render(o,label=True):
 p=pm(o);g=[[" "]*W for _ in range(HH)]
 def put(x,y,c,ow=False):
  if 0<=x<W and 0<=y<HH and (ow or g[y][x]==" "):g[y][x]=c
 for x in range(W):g[G][x]="_"
 for a,b in L:
  for x,y in line(p[a],p[b])[1:-1]:put(x,y,glyph(p[a],p[b]))
 for n,(x,y) in p.items():put(x,y,"O" if n=="head" else ("@" if n=="pelvis" else "o"),True)
 x,y=p["head"];put(min(W-1,x+2),y,">",True)
 s=o["support_contact"]
 if s in ("GROUND_BOTH","GROUND_LEFT","GROUND_LEFT_DOMINANT"):x,y=p["foot_l"];put(x,min(HH-1,y+1),"=",True)
 if s in ("GROUND_BOTH","GROUND_RIGHT","GROUND_RIGHT_DOMINANT"):x,y=p["foot_r"];put(x,min(HH-1,y+1),"=",True)
 if label:
  x,y=p["pelvis"];m={"READY":"+","LOAD":"<","LAUNCH":"^","ASCEND":"^","APEX":"~","DESCEND":"v","PRECONTACT":"?","CONTACT":"!","LAND_COMPRESSION":"#","REBOUND":"^","OVERSHOOT":">","SETTLE":".","REENTRY":"+"}.get(o["vertical_phase"],"*");put(max(0,x-4),y,m,True)
 return "\n".join("".join(r).rstrip() for r in g)
def sheet(d):
 out=["ASCII KINESIS V2 AIRBORNE 016 — CROOKED-CATCH VERTICAL DEBT REPAIR","COPYABLE CONTACT SHEET — ABSTRACT ASCII RIG ONLY — NO SOURCE PIXELS","Legend: O head | @ pelvis/root | o joints | > facing-right | = owned ground support","Principle: LANDING PAYS VERTICAL DEBT BEFORE GROUND SPEED RE-ENTERS.",""]
 for k in d["keys"]:out.append(f'[{k["key_id"]}] {k["name"]} | {k["timing_class"]} {k["timing_provenance"]} | support={k["support_contact"]} | contact={k["contact_state"]} | phase={k["vertical_phase"]} | role={k["causal_role"]} | root={k["motion_arc_root_note"]}\n'+render(k))
 out.append("--- AUTHORED BRIDGE KEYS (GEOMETRY ONLY; DECISIVE KEYS REMAIN SEMANTIC AUTHORITY) ---")
 for b in d["bridge_keys"]:out.append(f'{b["bridge_id"]} {b["from_key"]} -> {b["to_key"]} | {b["timing_class"]} {b["timing_provenance"]} | {b["purpose"]}\n'+render(b,False))
 return "\n\n".join(out)
def seq(d):
 bm={(b["from_key"],b["to_key"]):b for b in d["bridge_keys"]};out=[];ks=d["keys"]
 for i,k in enumerate(ks):
  out += [render(k)]*HOLDS[k["timing_class"]]
  if i+1<len(ks):
   n=ks[i+1];b=bm.get((k["key_id"],n["key_id"]))
   if b:
    if (k["support_contact"],k["contact_state"])!=(n["support_contact"],n["contact_state"]):raise SystemExit("BRIDGE_SEMANTIC_CROSS")
    out += [render(b,False)]*HOLDS[b["timing_class"]]
 return out
def font(sz):
 for f in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf","/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"):
  if Path(f).exists():return ImageFont.truetype(f,sz)
 return ImageFont.load_default()
def media(d,dst):
 fs=seq(d);f=font(5)
 with tempfile.TemporaryDirectory(prefix="air016-") as td:
  td=Path(td)
  for i,t in enumerate(fs):
   im=Image.new("RGB",(320,180),"black");ImageDraw.Draw(im).multiline_text((4,5),t,font=f,fill="white",spacing=0);im.save(td/f"f-{i:04d}.png")
  subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(d["compile"]["fps"]),"-i",str(td/"f-%04d.png"),"-c:v","libx264","-preset","veryslow","-crf",str(d["compile"]["encoder_crf"]),"-pix_fmt","yuv420p","-movflags","+faststart",str(dst)],check=True)
 return fs
def html(d,s,m):
 jt=json.dumps(d,separators=(",",":"),sort_keys=True,ensure_ascii=False)
 pack=lambda x:base64.b64encode(gzip.compress(x.encode(),9,mtime=0)).decode()
 A,B,V=pack(s),pack(jt),base64.b64encode(m).decode()
 return f'''<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Crooked-Catch Vertical Debt Repair</title><style>:root{{color-scheme:dark}}body{{margin:0;background:#111;color:#eee;font-family:system-ui}}nav{{display:flex;gap:8px;padding:10px;position:sticky;top:0;background:#181818}}section{{padding:12px}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}video{{width:640px;max-width:100%;background:#000}}</style><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="a"></pre></section><section id="json" hidden><pre id="j"></pre></section><section id="video" hidden><video id="v" controls loop playsinline></video></section><script>const A="{A}",B="{B}",V="{V}";async function z(x){{let u=Uint8Array.from(atob(x),c=>c.charCodeAt());return new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([z(A),z(B)]).then(([x,y])=>{{a.textContent=x;j.textContent=y}});v.src="data:video/mp4;base64,"+V;for(const b of document.querySelectorAll("button[data-view]"))b.onclick=()=>{{for(const s of document.querySelectorAll("section"))s.hidden=s.id!==b.dataset.view}};</script>'''
def main():
 d=json.loads(M.read_text());s=sheet(d)
 if hashlib.sha256(s.encode()).hexdigest()!=d["ascii_sheet_sha256"]:raise SystemExit("ASCII_IDENTITY_MISMATCH")
 with tempfile.TemporaryDirectory() as td:
  p=Path(td)/d["compile"]["video_file"];fs=media(d,p);m=p.read_bytes()
 if hashlib.sha256(m).hexdigest()!=d["compile"]["media_sha256"] or len(m)!=d["compile"]["media_bytes"] or len(fs)!=d["compile"]["video_frames_total"]:raise SystemExit("MEDIA_IDENTITY_MISMATCH")
 SPA.write_text(html(d,s,m));print(json.dumps({"ascii_sha256":d["ascii_sheet_sha256"],"media_sha256":d["compile"]["media_sha256"],"media_bytes":len(m),"frames":len(fs),"spa":SPA.name},sort_keys=True))
if __name__=="__main__":main()
