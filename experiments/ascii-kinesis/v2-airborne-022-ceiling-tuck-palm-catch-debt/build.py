#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=json.loads((ROOT/"motion.json").read_text(encoding="utf-8"))
W=int(MOTION["rig"]["grid"]["width"]); H=int(MOTION["rig"]["grid"]["height"])
GROUND=23; FPS=int(MOTION["compile"]["fps"])
HOLD={"ONES":1,"TWOS":2,"FOURS":4}
HOLD_SCALE=int(MOTION["compile"].get("render_hold_scale",2))
BRIDGES=list(MOTION["compile"].get("bridge_plan",[]))
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
POINTS=["root","chest","head","l_elbow","l_hand","r_elbow","r_hand","l_knee","l_foot","r_knee","r_foot"]
CEIL_Y=4; CEIL_X0=22; CEIL_X1=39

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
    for x in range(CEIL_X0,CEIL_X1+1): g[CEIL_Y][x]="-"
    p={f:abspt(s,f) for f in POINTS}
    for a,b,ch in ((p["root"],p["chest"],"|"),(p["chest"],p["l_elbow"],"/"),(p["l_elbow"],p["l_hand"],"-"),
                   (p["chest"],p["r_elbow"],"\\"),(p["r_elbow"],p["r_hand"],"-"),
                   (p["root"],p["l_knee"],"/"),(p["l_knee"],p["l_foot"],"/"),
                   (p["root"],p["r_knee"],"\\"),(p["r_knee"],p["r_foot"],"\\")):
        line(g,*a,*b,ch)
    for q,ch in ((p["root"],"@"),(p["chest"],"+"),(p["head"],"O"),(p["l_elbow"],"o"),(p["l_hand"],"x"),
                 (p["r_elbow"],"o"),(p["r_hand"],"x"),(p["l_knee"],"o"),(p["r_knee"],"o"),
                 (p["l_foot"],"="),(p["r_foot"],"=")):
        put(g,*q,ch)
    if s.get("l_contact"): put(g,p["l_foot"][0],min(GROUND-1,p["l_foot"][1]),"!")
    if s.get("r_contact"): put(g,p["r_foot"][0],min(GROUND-1,p["r_foot"][1]),"!")
    if s.get("l_hand_contact"): put(g,p["l_hand"][0],min(GROUND-1,p["l_hand"][1]),"!")
    if s.get("r_hand_contact"): put(g,p["r_hand"][0],min(GROUND-1,p["r_hand"][1]),"!")
    return g

def text_pose(s):
    return "\n".join("".join(row).rstrip() for row in grid(s)).rstrip()

def compact_sheet(keys,states):
    out=["AIRBORNE022 — CEILING TUCK / PALM-CATCH DEBT",
         "source art not reproduced; generic ASCII rig; all decisive timing INFERRED / STREET_FIGHTER-CAPCOM",""]
    for key,s in zip(keys,states):
        cx=int(round(s["root"][0])); x0=max(0,min(W-34,cx-17)); x1=x0+34
        g=grid(s)
        out.extend([f'{key["key_id"]} {key["label"]} [{key["timing_class"]}/{key["timing_provenance"]}]',
                    f'root=({s["root"][0]:.1f},{s["root"][1]:.1f}) support={key["support_contact"]} crop_x={x0}:{x1-1}',
                    "+"+"-"*34+"+"])
        out.extend("|"+"".join(g[y][x0:x1])+"|" for y in range(2,24))
        out.extend(["+"+"-"*34+"+","role: "+key["causal_role"],""])
    return "\n".join(out).rstrip()+"\n"

def interp(a,b,t):
    s=t*t*(3-2*t); out={}
    for f in POINTS:
        av=a[f]; bv=b[f]
        out[f]=[av[0]+(bv[0]-av[0])*s,av[1]+(bv[1]-av[1])*s]
    for flag in ("l_contact","r_contact","l_hand_contact","r_hand_contact"):
        out[flag]=bool(a.get(flag,False))
    return out

states=[dict(key["authoring"]) for key in MOTION["keys"]]
(ROOT/"contact-sheet.txt").write_text(compact_sheet(MOTION["keys"],states),encoding="utf-8")

frames=[]
for i,(key,s) in enumerate(zip(MOTION["keys"],states)):
    frames += [text_pose(s)]*(HOLD[key["timing_class"]]*HOLD_SCALE)
    if i<len(states)-1:
        n=BRIDGES[i] if i<len(BRIDGES) else 1
        for j in range(1,n+1):
            frames.append(text_pose(interp(s,states[i+1],j/(n+1))))

fd=ROOT/".frames"
if fd.exists(): shutil.rmtree(fd)
fd.mkdir()
font=ImageFont.truetype(FONT,10)
for i,txt in enumerate(frames):
    img=Image.new("RGB",(520,286),(10,10,10))
    d=ImageDraw.Draw(img)
    d.multiline_text((8,4),txt,font=font,fill=(240,240,240),spacing=-1)
    img.save(fd/f"{i:04d}.png",compress_level=9)

mp4=ROOT/MOTION["media"]["filename"]
subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-framerate",str(FPS),"-i",str(fd/"%04d.png"),
                "-c:v","libx264","-pix_fmt","yuv420p","-preset","medium","-crf","32","-threads","1",
                "-movflags","+faststart",str(mp4)],check=True)
subprocess.run(["ffmpeg","-v","error","-i",str(mp4),"-f","null","-"],check=True)
media=mp4.read_bytes(); sha=hashlib.sha256(media).hexdigest()
expected=MOTION["media"]["sha256"]
if expected not in {"PENDING",sha}:
    raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={expected} got={sha}")
if MOTION["media"].get("bytes") not in {None,len(media)}:
    raise SystemExit("MEDIA_IDENTITY_MISMATCH bytes")
if MOTION["media"].get("frames") not in {None,len(frames)}:
    raise SystemExit("MEDIA_IDENTITY_MISMATCH frames")
print(json.dumps({"ok":True,"frames":len(frames),"bytes":len(media),"media_sha256":sha,
                  "contact_sheet_sha256":hashlib.sha256((ROOT/"contact-sheet.txt").read_bytes()).hexdigest()},sort_keys=True))
