#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=json.loads((ROOT/"motion.json").read_text(encoding="utf-8"))
W=int(MOTION["rig"]["grid"]["width"]); H=int(MOTION["rig"]["grid"]["height"])
GROUND=21; FPS=int(MOTION["compile"]["fps"])
HOLD={"ONES":1,"TWOS":2,"FOURS":4}
HOLD_SCALE=int(MOTION["compile"].get("render_hold_scale",2))
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
POINTS=["root","chest","head","l_elbow","l_hand","r_elbow","r_hand","l_knee","l_foot","r_knee","r_foot"]

def put(g,x,y,ch):
    x=int(round(x)); y=int(round(y))
    if 0<=x<W and 0<=y<H: g[y][x]=ch

def line(g,x0,y0,x1,y1,ch):
    x0,y0,x1,y1=map(lambda v:int(round(v)),(x0,y0,x1,y1))
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<H and g[y0][x0]==" ": g[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def abspt(s,f):
    r=s["root"]
    return tuple(r) if f=="root" else (r[0]+s[f][0],r[1]+s[f][1])

def grid(s):
    g=[[" "]*W for _ in range(H)]
    for x in range(1,W-1): g[GROUND][x]="_"
    hip=abspt(s,"root"); chest=abspt(s,"chest"); head=abspt(s,"head")
    le=abspt(s,"l_elbow"); lh=abspt(s,"l_hand"); re=abspt(s,"r_elbow"); rh=abspt(s,"r_hand")
    lk=abspt(s,"l_knee"); lf=abspt(s,"l_foot"); rk=abspt(s,"r_knee"); rf=abspt(s,"r_foot")
    for a,b,ch in ((hip,chest,"|"),(chest,le,"/"),(le,lh,"-"),(chest,re,"\\"),(re,rh,"-"),
                   (hip,lk,"/"),(lk,lf,"/"),(hip,rk,"\\"),(rk,rf,"\\")):
        line(g,*a,*b,ch)
    for p,ch in ((hip,"@"),(chest,"+"),(head,"O"),(le,"o"),(lh,"x"),(re,"o"),(rh,"x"),
                 (lk,"o"),(rk,"o"),(lf,"="),(rf,"=")):
        put(g,*p,ch)
    if s.get("l_contact"): put(g,lf[0],min(GROUND-1,lf[1]),"!")
    if s.get("r_contact"): put(g,rf[0],min(GROUND-1,rf[1]),"!")
    return g

def text_pose(s):
    return "\n".join("".join(row).rstrip() for row in grid(s)).rstrip()

def compact_sheet(keys,states):
    out=[]
    for key,s in zip(keys,states):
        cx=int(round(s["root"][0])); x0=max(0,min(W-28,cx-14)); x1=x0+28
        g=grid(s)
        out.append(f'{key["key_id"]} {key["label"]} [{key["timing_class"]}/{key["timing_provenance"]}]')
        out.append(f'root=({s["root"][0]:.1f},{s["root"][1]:.1f}) support={key["support_contact"]} crop_x={x0}:{x1-1}')
        out.append("+"+"-"*28+"+")
        for y in range(4,22): out.append("|"+"".join(g[y][x0:x1])+"|")
        out.append("+"+"-"*28+"+")
        out.append("role: "+key["causal_role"])
        out.append("")
    return "\n".join(out).rstrip()+"\n"

def interp(a,b,t):
    s=t*t*(3-2*t); out={}
    for f in POINTS:
        av=a[f]; bv=b[f]
        out[f]=[av[0]+(bv[0]-av[0])*s,av[1]+(bv[1]-av[1])*s]
    out["l_contact"]=bool(a.get("l_contact",False))
    out["r_contact"]=bool(a.get("r_contact",False))
    return out

states=[]
for key in MOTION["keys"]:
    s=dict(key["authoring"])
    s["l_contact"]=bool(s.get("l_contact",False)); s["r_contact"]=bool(s.get("r_contact",False))
    states.append(s)

(ROOT/"contact-sheet.txt").write_text(compact_sheet(MOTION["keys"],states),encoding="utf-8")

frames=[]
for i,(key,s) in enumerate(zip(MOTION["keys"],states)):
    frames += [text_pose(s)]*(HOLD[key["timing_class"]]*HOLD_SCALE)
    if i<len(states)-1:
        n=2 if i in {0,1,4,5,6,7,9,10} else 1
        for j in range(1,n+1): frames.append(text_pose(interp(s,states[i+1],j/(n+1)))

fd=ROOT/".frames"
if fd.exists(): shutil.rmtree(fd)
fd.mkdir()
font=ImageFont.truetype(FONT,13)
for i,txt in enumerate(frames):
    img=Image.new("RGB",(512,288),(10,10,10))
    d=ImageDraw.Draw(img); d.multiline_text((8,4),txt,font=font,fill=(240,240,240),spacing=-1)
    img.save(fd/f"{i:04d}.png",compress_level=9)

mp4=ROOT/"counterspin-hook-catch-recovery.mp4"
subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-framerate",str(FPS),"-i",str(fd/"%04d.png"),
                "-c:v","libx264","-pix_fmt","yuv420p","-preset","medium","-crf","29","-threads","1",
                "-movflags","+faststart",str(mp4)],check=True)
shutil.rmtree(fd)
media=mp4.read_bytes(); sha=hashlib.sha256(media).hexdigest()
expected=MOTION["media"]["sha256"]
if sha!=expected: raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={expected} got={sha}")
print(json.dumps({"ok":True,"frames":len(frames),"bytes":len(media),"media_sha256":sha,
                  "contact_sheet_sha256":hashlib.sha256((ROOT/"contact-sheet.txt").read_bytes()).hexdigest()},sort_keys=True))
