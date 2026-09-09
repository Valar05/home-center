#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=json.loads((ROOT/"motion.json").read_text(encoding="utf-8"))
W=int(MOTION["rig"]["grid"]["width"]); H=int(MOTION["rig"]["grid"]["height"])
GROUND=26; FPS=int(MOTION["compile"]["fps"])
HOLD={"ONES":1,"TWOS":2,"FOURS":4}
HOLD_SCALE=int(MOTION["compile"].get("render_hold_scale",2))
BRIDGES=list(MOTION["compile"]["bridge_plan"])
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
POINTS=["root","chest","head","l_elbow","l_hand","r_elbow","r_hand","l_knee","l_foot","r_knee","r_foot"]

def put(g,x,y,ch,overwrite=True):
    x=int(round(x)); y=int(round(y))
    if 0<=x<W and 0<=y<H and (overwrite or g[y][x]==" "): g[y][x]=ch

def line(g,x0,y0,x1,y1,ch,overwrite=False):
    x0,y0,x1,y1=map(lambda v:int(round(v)),(x0,y0,x1,y1))
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<H and (overwrite or g[y0][x0]==" "): g[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def abspt(s,f):
    if f=="root": return tuple(s["root"])
    r=s["root"]; q=s[f]
    return (r[0]+q[0],r[1]+q[1])

def grid(s):
    g=[[" "]*W for _ in range(H)]
    for x in range(1,W-1): g[GROUND][x]="_"
    p={f:abspt(s,f) for f in POINTS}
    line(g,*s["tool_a"],*s["tool_b"],"=",False)
    put(g,*s["tool_a"],"^",True); put(g,*s["tool_b"],"^",True)
    for a,b,ch in (
        (p["root"],p["chest"],"|"),
        (p["chest"],p["l_elbow"],"/"),(p["l_elbow"],p["l_hand"],"-"),
        (p["chest"],p["r_elbow"],"\\"),(p["r_elbow"],p["r_hand"],"-"),
        (p["root"],p["l_knee"],"/"),(p["l_knee"],p["l_foot"],"/"),
        (p["root"],p["r_knee"],"\\"),(p["r_knee"],p["r_foot"],"\\")
    ): line(g,*a,*b,ch)
    for q,ch in (
        (p["root"],"@"),(p["chest"],"+"),(p["head"],"O"),
        (p["l_elbow"],"o"),(p["l_hand"],"x"),(p["r_elbow"],"o"),(p["r_hand"],"x"),
        (p["l_knee"],"o"),(p["l_foot"],"="),(p["r_knee"],"o"),(p["r_foot"],"=")
    ): put(g,*q,ch,True)
    if s.get("l_contact"): put(g,*p["l_foot"],"!",True)
    if s.get("r_contact"): put(g,*p["r_foot"],"!",True)
    if s.get("tool_contact"): put(g,*s["tool_b"],"!",True)
    return g

def text_pose(s):
    return "\n".join("".join(row).rstrip() for row in grid(s)).rstrip()

def interp(a,b,t):
    u=t*t*(3-2*t); out={}
    for f in POINTS:
        av=a[f]; bv=b[f]
        out[f]=[av[0]+(bv[0]-av[0])*u,av[1]+(bv[1]-av[1])*u]
    for f in ("tool_a","tool_b"):
        av=a[f]; bv=b[f]
        out[f]=[av[0]+(bv[0]-av[0])*u,av[1]+(bv[1]-av[1])*u]
    for flag in ("l_contact","r_contact","tool_contact"):
        out[flag]=bool(a.get(flag,False))
    return out

states=[dict(k["authoring"]) for k in MOTION["keys"]]
contact_path=ROOT/"contact-sheet.txt"
if not contact_path.is_file():
    raise SystemExit("CONTACT_SHEET_MISSING: tracked literal ASCII sidecar is required")

frames=[]; meta=[]
for i,(key,s) in enumerate(zip(MOTION["keys"],states)):
    for _ in range(HOLD[key["timing_class"]]*HOLD_SCALE):
        frames.append(text_pose(s)); meta.append((key["key_id"],"hold"))
    if i<len(states)-1:
        n=BRIDGES[i]
        for j in range(1,n+1):
            frames.append(text_pose(interp(s,states[i+1],j/(n+1)))); meta.append((f'{key["key_id"]}->{MOTION["keys"][i+1]["key_id"]}',"bridge"))

fd=ROOT/".frames"
if fd.exists(): shutil.rmtree(fd)
fd.mkdir()
font=ImageFont.truetype(FONT,9)
for i,txt in enumerate(frames):
    img=Image.new("RGB",(560,300),(8,8,8)); d=ImageDraw.Draw(img)
    d.multiline_text((8,4),txt,font=font,fill=(238,238,238),spacing=-1)
    d.text((8,278),f"{i:03d} {meta[i][0]}",font=font,fill=(180,180,180))
    img.save(fd/f"{i:04d}.png",compress_level=9)

mp4=ROOT/MOTION["media"]["filename"]
subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-framerate",str(FPS),"-i",str(fd/"%04d.png"),
                "-c:v","libx264","-pix_fmt","yuv420p","-preset","medium","-crf","39","-threads","1","-movflags","+faststart",str(mp4)],check=True)
subprocess.run(["ffmpeg","-v","error","-i",str(mp4),"-f","null","-"],check=True)
media=mp4.read_bytes()
sha=hashlib.sha256(media).hexdigest()
if sha != MOTION["media"]["sha256"]:
    raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={MOTION['media']['sha256']} got={sha}")
if len(media) != int(MOTION["media"]["bytes"]):
    raise SystemExit(f"MEDIA_IDENTITY_MISMATCH bytes expected={MOTION['media']['bytes']} got={len(media)}")
if len(frames) != int(MOTION["media"]["frames"]):
    raise SystemExit(f"MEDIA_IDENTITY_MISMATCH frames expected={MOTION['media']['frames']} got={len(frames)}")
print(json.dumps({"ok":True,"frames":len(frames),"bytes":len(media),"media_sha256":sha,
                  "contact_sheet_sha256":hashlib.sha256(contact_path.read_bytes()).hexdigest()},sort_keys=True))
