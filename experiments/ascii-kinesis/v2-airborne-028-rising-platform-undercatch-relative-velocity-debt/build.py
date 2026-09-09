#!/usr/bin/env python3
from pathlib import Path
import json, math, subprocess, tempfile, shutil
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
motion=json.loads((HERE/"motion.json").read_text(encoding="utf-8"))
keys=motion["keys"]
W=motion["rig"]["grid"]["width"]; H=motion["rig"]["grid"]["height"]
OUT=HERE/"rising-platform-undercatch-relative-velocity-debt.mp4"
FPS=24
CELL_W=10; CELL_H=11; TOP=30
IMG_W=W*CELL_W; IMG_H=TOP+H*CELL_H
FONT=ImageFont.load_default(size=11)
SMALL=ImageFont.load_default(size=10)

def ease(t):
    return t*t*(3-2*t)

def interp(a,b,t):
    return a+(b-a)*ease(t)

def as_state(key):
    a=key["authoring"]
    return {
      "key_id":key["key_id"],"name":key["name"],"timing_class":key["timing_class"],
      "root":list(a["root"]),"platform":list(a["platform"]),
      "support":key["support_contact"]["support"],"contacts":list(key["support_contact"]["contacts"]),
      "a":{n:list(a[n]) for n in ["chest","head","le","lh","re","rh","lk","lf","rk","rf"]}
    }

def blend(sa,sb,t):
    out={"key_id":sa["key_id"]+"→"+sb["key_id"],"name":"CONNECTIVE","timing_class":"CONNECTIVE",
         "root":[round(interp(sa["root"][0],sb["root"][0],t)),round(interp(sa["root"][1],sb["root"][1],t))],
         "platform":[round(interp(sa["platform"][0],sb["platform"][0],t)),round(interp(sa["platform"][1],sb["platform"][1],t))],
         "support":sa["support"],"contacts":sa["contacts"],"a":{}}
    for n in sa["a"]:
        out["a"][n]=[round(interp(sa["a"][n][0],sb["a"][n][0],t)),round(interp(sa["a"][n][1],sb["a"][n][1],t))]
    return out

def line_chars(grid,x0,y0,x1,y1,ch):
    dx=x1-x0; dy=y1-y0; n=max(abs(dx),abs(dy))
    if n==0:
        if 0<=x0<W and 0<=y0<H: grid[y0][x0]=ch
        return
    for i in range(n+1):
        t=i/n; x=round(x0+dx*t); y=round(y0+dy*t)
        if 0<=x<W and 0<=y<H and grid[y][x]==" ": grid[y][x]=ch

def abspt(s,name):
    rx,ry=s["root"]; dx,dy=s["a"][name]; return rx+dx,ry+dy

def ascii_frame(s):
    grid=[[" "]*W for _ in range(H)]
    for x in range(0,18): grid[29][x]="_"
    grid[28][0]="L"
    px,py=s["platform"]; platform="[===========]"; sx=round(px-len(platform)//2)
    for i,ch in enumerate(platform):
        x=sx+i
        if 0<=x<W and 0<=py<H: grid[py][x]=ch
    if 0<=py+1<H:
        arrow="^>"
        for i,ch in enumerate(arrow):
            x=px+i
            if 0<=x<W: grid[py+1][x]=ch
    rootp=tuple(s["root"]); chest=abspt(s,"chest"); head=abspt(s,"head")
    le=abspt(s,"le"); lh=abspt(s,"lh"); re=abspt(s,"re"); rh=abspt(s,"rh")
    lk=abspt(s,"lk"); lf=abspt(s,"lf"); rk=abspt(s,"rk"); rf=abspt(s,"rf")
    line_chars(grid,*rootp,*chest,"|"); line_chars(grid,*chest,*head,"|")
    line_chars(grid,*chest,*le,"/"); line_chars(grid,*le,*lh,"/")
    line_chars(grid,*chest,*re,"\\"); line_chars(grid,*re,*rh,"\\")
    line_chars(grid,*rootp,*lk,"/"); line_chars(grid,*lk,*lf,"/")
    line_chars(grid,*rootp,*rk,"\\"); line_chars(grid,*rk,*rf,"\\")
    for (x,y),ch in [(rootp,"@"),(chest,"o"),(head,"O"),(le,"o"),(lh,"x"),(re,"o"),(rh,"x"),(lk,"o"),(lf,"="),(rk,"o"),(rf,"=")]:
        if 0<=x<W and 0<=y<H: grid[y][x]=ch
    for c in s["contacts"]:
        if c.startswith("right_") and "platform" in c:
            x,y=rf
        elif c.startswith("left_") and "platform" in c:
            x,y=lf
        elif c.startswith("right_") and "fixed" in c:
            x,y=rf
        elif c.startswith("left_") and "fixed" in c:
            x,y=lf
        else: continue
        yy=min(y+1,H-1)
        if 0<=x<W: grid[yy][x]="!"
    return "\n".join("".join(r) for r in grid)

states=[as_state(k) for k in keys]
hold={"ONES":1,"TWOS":2,"FOURS":4}
frames=[]
for idx,s in enumerate(states):
    frames += [(s, keys[idx]["key_id"])]*hold[keys[idx]["timing_class"]]
    if idx+1<len(states):
        nxt=states[idx+1]
        # three connective drawings; support/contact semantics remain the source key until target authored key.
        for j in range(1,4):
            frames.append((blend(s,nxt,j/4), s["key_id"]+"→"+nxt["key_id"]))

tmp=Path(tempfile.mkdtemp(prefix="air028_"))
try:
    for i,(s,label) in enumerate(frames):
        im=Image.new("RGB",(IMG_W,IMG_H),(250,250,250))
        d=ImageDraw.Draw(im)
        d.text((8,6),f"{motion['experiment_id']}  frame {i+1:03}/{len(frames):03}  {label}",fill=(0,0,0),font=SMALL)
        txt=ascii_frame(s)
        y=TOP
        for line in txt.splitlines():
            d.text((0,y),line,fill=(0,0,0),font=FONT)
            y+=CELL_H
        im.save(tmp/f"{i:04d}.png")
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(tmp/"%04d.png"),
        "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(OUT)
    ],check=True)
finally:
    shutil.rmtree(tmp)
print(OUT)
