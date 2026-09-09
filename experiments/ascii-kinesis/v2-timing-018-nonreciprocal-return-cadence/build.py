#!/usr/bin/env python3
"""Deterministically rebuild Timing018 from persisted structured ASCII rig + timing only."""
from pathlib import Path
import json,hashlib,subprocess,shutil
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent; M=json.loads((ROOT/"motion.json").read_text()); W,H,FY,WX,WB=64,18,15,52,8
def line(c,x0,y0,x1,y1,ch):
 d=abs(x1-x0); e=-abs(y1-y0); sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1; er=d+e
 while True:
  if 0<=x0<W and 0<=y0<H and c[y0][x0]==" ": c[y0][x0]=ch
  if x0==x1 and y0==y1: break
  q=2*er
  if q>=e: er+=e; x0+=sx
  if q<=d: er+=d; y0+=sy
def pose(k):
 a=M["rig"]["rig_states"][k["key_id"]]; rx,ry,hx,hy,sx,sy,lx,ly,rxh,ryh,lfx,lfy,rfx,rfy,tx,ty,hook=a
 c=[[" "]*W for _ in range(H)]
 for x in range(1,W-1): c[FY][x]="_"
 for y in range(WB+1): c[y][WX]="#"
 for x in range(WX,W-1): c[WB][x]="#"
 c[10][50]="X" if k["causal_role"]=="CONTACT_SPIKE" else "x"
 line(c,rx,ry,lfx,lfy,"/"); line(c,rx,ry,rfx,rfy,"\\"); line(c,rx,ry,sx,sy,"|"); line(c,sx,sy,hx,hy,"|"); c[hy][hx]="O"; c[ry][rx]="^"
 line(c,sx,sy,lx,ly,"/"); line(c,sx,sy,rxh,ryh,"\\"); c[ly][lx]="o"; c[ryh][rxh]="o"
 line(c,rxh,ryh,tx,ty,"=" if abs(tx-rxh)>=abs(ty-ryh) else "|"); c[ty][tx]=hook
 return "\n".join("".join(r).rstrip() for r in c).rstrip()+"\n"
parts=[]
for k in M["keys"]: parts += [f'{k["key_id"]} {k["causal_role"]} {k["timing_class"]}/{k["exposure_ticks"]}t {k["timing_provenance"]}\n',f'support={k["support_contact"]} | {k["motion_arc_root_note"]}\n',pose(k),"-"*72+"\n"]
font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",12); fd=ROOT/".motion-frames"
if fd.exists(): shutil.rmtree(fd)
fd.mkdir(); n=0
for k in M["keys"]:
 for _ in range(int(k["exposure_ticks"])):
  im=Image.new("RGB",(620,260),"white"); ImageDraw.Draw(im).multiline_text((12,8),pose(k),font=font,fill="black",spacing=0); im.save(fd/f"f_{n:04d}.png"); n+=1
out=ROOT/"nonreciprocal-return-cadence.mp4"
subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(fd/"f_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-crf","27","-movflags","+faststart","-map_metadata","-1",str(out)],check=True)
print(json.dumps({"frames":n,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"bytes":out.stat().st_size},sort_keys=True))
