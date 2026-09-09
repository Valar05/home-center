#!/usr/bin/env python3
"""Motion Dungeon builder for ASCII Kinesis V2 Strikes010.

Authority: motion.json decisive ASCII rig keys + inferred timing.
No source pixels, palette, contours, frames, audio, or character art are read.
"""
from __future__ import annotations
import hashlib, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MOTION = json.loads((ROOT / "motion.json").read_text(encoding="utf-8"))
FPS = int(MOTION["timing_policy"]["display_fps"])
WIDTH, HEIGHT = 880, 440
GRID_W, GRID_H = MOTION["rig"]["grid"]
TARGET = tuple(MOTION["keys"][0]["pose_rig"]["target_contact"])
POINT_FIELDS = [
    "root","chest","head","left_foot","right_foot","left_hand","right_hand",
    "tool_butt","tool_tip"
]

def bresenham(a, b):
    x0,y0=a; x1,y1=b
    pts=[]; dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: return pts
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def line_char(a,b,staff=False):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>=2*abs(dy): return "=" if staff else "-"
    if abs(dy)>=2*abs(dx): return "|"
    return "\\" if dx*dy>0 else "/"

def derive(p):
    root=tuple(p["root"]); chest=tuple(p["chest"])
    ls=(chest[0]-2,chest[1]); rs=(chest[0]+2,chest[1])
    lhp=(root[0]-2,root[1]+1); rhp=(root[0]+2,root[1]+1)
    def mid(a,b,bias=(0,0)):
        return ((a[0]+b[0])//2+bias[0],(a[1]+b[1])//2+bias[1])
    return {
        "ls":ls,"rs":rs,"lhp":lhp,"rhp":rhp,
        "le":mid(ls,tuple(p["left_hand"]),(-1,0)),
        "re":mid(rs,tuple(p["right_hand"]),(1,0)),
        "lk":mid(lhp,tuple(p["left_foot"]),(-1,0)),
        "rk":mid(rhp,tuple(p["right_foot"]),(1,0)),
    }

def ascii_from_pose(p, tool_contact):
    g=[[" "]*GRID_W for _ in range(GRID_H)]
    for x in range(3,GRID_W-3): g[22][x]="_"
    tx,ty=TARGET; g[ty-1][tx]="T"; g[ty][tx]="|"; g[ty+1][tx]="|"
    d=derive(p)
    pts={**{k:tuple(v) for k,v in p.items() if isinstance(v,list) and len(v)==2},**d}
    def seg(a,b,staff=False):
        ch=line_char(a,b,staff)
        for x,y in bresenham(a,b):
            if 0<=x<GRID_W and 0<=y<GRID_H and g[y][x]==" ": g[y][x]=ch
    seg(pts["root"],pts["chest"]); seg(pts["chest"],pts["head"])
    seg(pts["ls"],pts["le"]); seg(pts["le"],pts["left_hand"])
    seg(pts["rs"],pts["re"]); seg(pts["re"],pts["right_hand"])
    seg(pts["root"],pts["lhp"]); seg(pts["lhp"],pts["lk"]); seg(pts["lk"],pts["left_foot"])
    seg(pts["root"],pts["rhp"]); seg(pts["rhp"],pts["rk"]); seg(pts["rk"],pts["right_foot"])
    seg(pts["tool_butt"],pts["tool_tip"],True)
    for name,ch in [
        ("head","o"),("chest","+"),("root","@"),("ls","+"),("rs","+"),("le","o"),("re","o"),
        ("left_hand","*"),("right_hand","*"),("lk","o"),("rk","o"),("left_foot","/"),("right_foot","\\")
    ]:
        x,y=pts[name]
        if 0<=x<GRID_W and 0<=y<GRID_H: g[y][x]=ch
    for name,ch in [("tool_butt","<"),("tool_tip",">")]:
        x,y=pts[name]
        if 0<=x<GRID_W and 0<=y<GRID_H: g[y][x]=ch
    if tool_contact=="MID_SHAFT_PIN": g[ty][tx]="X"
    return "\n".join("".join(row).rstrip() for row in g)

def interp(a,b,t,arc=0):
    u=t*t*(3-2*t)
    return [round(a[0]+(b[0]-a[0])*u), round(a[1]+(b[1]-a[1])*u + arc*math.sin(math.pi*t))]

def compile_ascii_frames():
    keys=MOTION["keys"]; bridges=MOTION["bridges"]; out=[]
    for i,k in enumerate(keys):
        out += [k["ascii"]]*int(k["compile_hold_frames"])
        if i==len(keys)-1: continue
        n=keys[i+1]; br=bridges[i]
        for q in range(int(br["frames"])):
            t=(q+1)/(int(br["frames"])+1)
            pose={}
            for fld,val in k["pose_rig"].items():
                if fld=="target_contact": pose[fld]=val; continue
                if isinstance(val,list) and len(val)==2:
                    arc=int(br["root_arc_offset_y"]) if fld in {"root","chest","head"} else 0
                    pose[fld]=interp(val,n["pose_rig"][fld],t,arc)
            out.append(ascii_from_pose(pose,k["tool_contact"]))
    return out

def font():
    try: return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",14)
    except OSError: return ImageFont.load_default()

def render_mp4(path):
    frames=compile_ascii_frames(); fnt=font()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for idx,txt in enumerate(frames):
            im=Image.new("RGB",(WIDTH,HEIGHT),"black"); d=ImageDraw.Draw(im)
            d.multiline_text((18,34),txt,font=fnt,fill="white",spacing=1)
            d.text((18,12),f"ASCII KINESIS V2 STRIKES010  frame {idx+1:02d}/{len(frames):02d}",font=fnt,fill="white")
            im.save(td/f"f{idx:04d}.png")
        subprocess.run([
            "ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(td/"f%04d.png"),
            "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(path)
        ],check=True)
    return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__=="__main__":
    out=ROOT/"midshaft-contact-repivot-debt.mp4"
    print(json.dumps({"media_sha256":render_mp4(out),"path":str(out)},sort_keys=True))
