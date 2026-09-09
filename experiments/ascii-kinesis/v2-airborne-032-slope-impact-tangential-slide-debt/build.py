#!/usr/bin/env python3
from __future__ import annotations
import base64, json, math, subprocess, tempfile, hashlib, html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
CONTACT = HERE / "contact-sheet.txt"
SPA = HERE / "slope-impact-tangential-slide-debt.motion.html"
MP4 = HERE / "slope-impact-tangential-slide-debt.mp4"

W, H = 78, 29
POINTS = ["root","chest","head","l_elbow","l_hand","r_elbow","r_hand","l_knee","l_foot","r_knee","r_foot"]
EDGES = [
    ("root","chest"),("chest","head"),
    ("chest","l_elbow"),("l_elbow","l_hand"),
    ("chest","r_elbow"),("r_elbow","r_hand"),
    ("root","l_knee"),("l_knee","l_foot"),
    ("root","r_knee"),("r_knee","r_foot"),
]

def lerp(a,b,t): return a+(b-a)*t
def smooth(t): return t*t*(3.0-2.0*t)

def abs_points(k):
    rx, ry = k["root"]
    out = {"root": (rx,ry)}
    for name in POINTS[1:]:
        dx,dy = k[name]
        out[name]=(rx+dx,ry+dy)
    return out

def interp_key(a,b,t):
    s=smooth(t)
    aa=abs_points(a); bb=abs_points(b)
    out={}
    for name in POINTS:
        pa=aa[name]; pb=bb[name]
        out[name]=(lerp(pa[0],pb[0],s), lerp(pa[1],pb[1],s))
    out["l_contact"]=bool(a["l_contact"])
    out["r_contact"]=bool(a["r_contact"])
    return out

def key_pose(k):
    p=abs_points(k)
    p["l_contact"]=bool(k["l_contact"])
    p["r_contact"]=bool(k["r_contact"])
    return p

def put(grid,x,y,ch):
    x=int(round(x)); y=int(round(y))
    if 0<=x<W and 0<=y<H:
        grid[y][x]=ch

def line(grid,p0,p1):
    x0,y0=p0; x1,y1=p1
    dx=x1-x0; dy=y1-y0
    n=max(1,int(math.ceil(max(abs(dx),abs(dy))*2)))
    if abs(dx) > abs(dy)*1.6: ch="-"
    elif abs(dy) > abs(dx)*1.6: ch="|"
    else: ch="\\" if dx*dy>=0 else "/"
    for i in range(n+1):
        t=i/n
        put(grid,lerp(x0,x1,t),lerp(y0,y1,t),ch)

def slope_y(x): return 20.0 + 0.08*x

def render_grid(pose):
    g=[[" " for _ in range(W)] for _ in range(H)]
    for x in range(W):
        y=slope_y(x)
        put(g,x,y,"\\")
        if x%6==0:
            put(g,x,y+1,".")
    for a,b in EDGES:
        line(g,pose[a],pose[b])
    symbols={"root":"@","chest":"+","head":"O","l_elbow":"o","r_elbow":"o","l_hand":"x","r_hand":"x","l_knee":"o","r_knee":"o","l_foot":"=","r_foot":"="}
    for name,ch in symbols.items():
        put(g,*pose[name],ch)
    if pose.get("l_contact"): put(g,*pose["l_foot"],"*")
    if pose.get("r_contact"): put(g,*pose["r_foot"],"*")
    return ["".join(row).rstrip() for row in g]

def metadata_line(k):
    return (f'{k["key_id"]} {k["label"]} | timing={k["timing_class"]} | provenance={k["timing_provenance"]} | '
            f'support={k["support_contact"]} | role={k["causal_role"]}')

def make_contact(data):
    blocks=[]
    for k in data["keys"]:
        blocks.append(metadata_line(k))
        blocks.extend(render_grid(key_pose(k)))
        blocks.append("")
    text="\n".join(blocks).rstrip()+"\n"
    CONTACT.write_text(text,encoding="utf-8")
    return text

def frame_sequence(data):
    holds=data["compile"]["hold_frames"]
    bridges=data["compile"]["bridge_frames"]
    keys=data["keys"]
    seq=[]
    for i,k in enumerate(keys):
        pose=key_pose(k)
        seq += [pose] * int(holds[k["timing_class"]])
        if i < len(keys)-1:
            n=int(bridges[i])
            for j in range(1,n+1):
                seq.append(interp_key(k,keys[i+1],j/(n+1)))
    return seq

def font():
    candidates=[
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).is_file():
            return ImageFont.truetype(p,14)
    return ImageFont.load_default()

def render_png(lines, path):
    f=font()
    cell_w=9
    cell_h=15
    im=Image.new("RGB",(W*cell_w+24,H*cell_h+25),(7,7,7))
    d=ImageDraw.Draw(im)
    for y,line_text in enumerate(lines):
        d.text((12,10+y*cell_h),line_text,font=f,fill=(242,242,242),spacing=0)
    im.save(path)

def build_video(data):
    seq=frame_sequence(data)
    with tempfile.TemporaryDirectory(prefix="a032-") as td:
        td=Path(td)
        for i,pose in enumerate(seq):
            render_png(render_grid(pose), td/f"frame-{i:04d}.png")
        cmd=[
            "ffmpeg","-hide_banner","-loglevel","error","-y",
            "-framerate",str(data["compile"]["fps"]),
            "-i",str(td/"frame-%04d.png"),
            "-an","-c:v","libx264","-pix_fmt","yuv420p",
            "-preset","veryslow","-crf","28",
            "-x264-params","threads=1:lookahead_threads=1:sliced_threads=0",
            "-map_metadata","-1","-movflags","+faststart",
            str(MP4)
        ]
        subprocess.run(cmd,check=True)
    return len(seq)

def make_spa(data, ascii_text, mp4_bytes):
    pretty=json.dumps(data,separators=(",",":"),ensure_ascii=False)
    b64=base64.b64encode(mp4_bytes).decode("ascii")
    page=f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>ASCII Kinesis — Airborne032</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}}
nav{{display:flex;gap:8px;padding:12px;position:sticky;top:0;background:#111}}
button{{font:inherit;padding:8px 12px}}
section{{padding:14px}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.04}}
video{{max-width:100%;height:auto;background:#000}}
</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii"><pre>{html.escape(ascii_text)}</pre></section>
<section id="json" hidden><pre>{html.escape(pretty)}</pre></section>
<section id="video" hidden><video controls loop playsinline><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section>
<script>
const ids=["ascii","json","video"];
document.querySelectorAll("button[data-view]").forEach(b=>b.onclick=()=>{{
  ids.forEach(id=>document.getElementById(id).hidden=(id!==b.dataset.view));
}});
</script></body></html>'''
    SPA.write_text(page,encoding="utf-8")

def main():
    data=json.loads(MOTION.read_text(encoding="utf-8"))
    ascii_text=make_contact(data)
    frames=build_video(data)
    mp4=MP4.read_bytes()
    data["media"]["frames"]=frames
    data["media"]["bytes"]=len(mp4)
    data["media"]["sha256"]=hashlib.sha256(mp4).hexdigest()
    data["media"]["decode"]="PASS_FFMPEG_CURRENT_WORKER"
    MOTION.write_text(json.dumps(data,separators=(",",":"),ensure_ascii=False)+"\n",encoding="utf-8")
    make_spa(data,ascii_text,mp4)
    print(json.dumps({"frames":frames,"bytes":len(mp4),"sha256":data["media"]["sha256"]},sort_keys=True))

if __name__=="__main__":
    main()
