#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent
M=json.loads((HERE/"motion.json").read_text(encoding="utf-8"))
W,H=M["rig"]["canvas"]; G=M["rig"]["ground_y"]; BONES=[tuple(x) for x in M["rig"]["bones"]]; HOLD=M["timing_policy"]["hold_frames"]; CONNECT={(c["from"],c["to"]):c for c in M["connectors"]}
def lp(a,b):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;p=[]
 while True:
  p.append((x0,y0))
  if (x0,y0)==(x1,y1): return p
  e=2*err
  if e>=dy: err+=dy;x0+=sx
  if e<=dx: err+=dx;y0+=sy
def art(j,s):
 g=[[" "]*W for _ in range(H)]
 for x in range(W): g[G][x]="="
 for a,b in BONES:
  pa,pb=j[a],j[b]
  for x,y in lp(pa,pb)[1:-1]:
   if 0<=x<W and 0<=y<H and g[y][x]==" ":
    dx=pb[0]-pa[0];dy=pb[1]-pa[1];g[y][x]="-" if dy==0 else ("|" if dx==0 else ("\\" if dx*dy>0 else "/"))
 for n,(x,y) in j.items():
  if 0<=x<W and 0<=y<H:g[y][x]="O" if n=="head" else ("+" if n=="chest" else ("@" if n=="pelvis" else ("o" if ("elbow" in n or "knee" in n) else "*")))
 parts=set(s.split("+"))
 for st,n in (("LEFT_SUPPORT","l_foot"),("RIGHT_SUPPORT","r_foot")):
  if st in parts:x,y=j[n];g[y][x]="!"
 for st,n in (("LEFT_PROBE","l_foot"),("RIGHT_PROBE","r_foot")):
  if st in parts:x,y=j[n];g[y][x]="?"
 return "\n".join("".join(r).rstrip() for r in g)
def bridge(a,b,t,bend):
 s=t*t*(3-2*t);o={}
 for n,pa in a.items():
  pb=b[n];x=pa[0]+(pb[0]-pa[0])*s;y=pa[1]+(pb[1]-pa[1])*s;amp=4*s*(1-s)*bend
  if n=="pelvis":y+=amp*.25
  elif n in ("head","chest"):y+=amp*.15
  elif n in ("l_hand","r_hand"):y+=amp*(.45 if n=="l_hand" else -.35)
  elif n in ("l_foot","r_foot"):y+=amp*(-.25 if n=="l_foot" else .25)
  o[n]=[round(x),round(y)]
 return o
keys=M["keys"];frames=[]
for i,k in enumerate(keys):
 frames += [(k["joints"],k["support_contact"],k["key_id"],k["name"])]*int(HOLD[k["timing_class"]])
 if i<len(keys)-1:
  n=keys[i+1];c=CONNECT.get((k["key_id"],n["key_id"]))
  if c:
   if k["support_contact"]!=n["support_contact"]:raise SystemExit("connector semantic support transition")
   for q in range(1,int(c["frames"])+1):frames.append((bridge(k["joints"],n["joints"],q/(int(c["frames"])+1),float(c["bend"])),k["support_contact"],k["key_id"]+"->"+n["key_id"],"AUTHORED_BRIDGE"))
frames += [(keys[-1]["joints"],keys[-1]["support_contact"],keys[-1]["key_id"],keys[-1]["name"])]*int(M["motion_dungeon"]["compile"]["endpoint_hold_frames"])
tmp=HERE/".motion-dungeon-tmp";shutil.rmtree(tmp,ignore_errors=True);tmp.mkdir();font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",5);small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",5)
for i,(j,s,kid,name) in enumerate(frames):
 im=Image.new("RGB",(480,260),(12,12,13));d=ImageDraw.Draw(im);d.text((6,4),"ASCII KINESIS · LOCOMOTION 013",font=small,fill=(190,190,190));d.text((6,12),f"{kid} {name} {s}",font=small,fill=(238,238,235));d.multiline_text((6,22),art(j,s),font=font,fill=(247,247,241),spacing=0);d.text((6,244),f"{i+1:03d}/{len(frames):03d}",font=small,fill=(140,140,140));im.save(tmp/f"f_{i:04d}.png",compress_level=9)
mp4=HERE/"stride-phase-airborne-handoff-repair.mp4";subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(tmp/"f_%04d.png"),"-c:v","libx264","-preset","veryslow","-crf","36","-pix_fmt","yuv420p","-movflags","+faststart","-metadata","comment=ASCII Kinesis abstract rig only",str(mp4)],check=True);subprocess.run(["ffmpeg","-v","error","-i",str(mp4),"-f","null","-"],check=True)
blob=mp4.read_bytes();C=M["motion_dungeon"]["compile"]
if len(frames)!=C["frames"] or len(blob)!=C["media_bytes"] or hashlib.sha256(blob).hexdigest()!=C["media_sha256"]:raise SystemExit("authoritative media identity mismatch")
print(json.dumps({"frames":len(frames),"media_bytes":len(blob),"media_sha256":hashlib.sha256(blob).hexdigest()},sort_keys=True))
