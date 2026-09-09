#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, subprocess, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
CONTACT = (HERE / "contact-sheet.txt").read_text(encoding="utf-8")
SLUG = "figure-eight-curvature-sign-reversal"
FPS = int(MOTION["motion_dungeon"]["compile"]["fps"])
HOLDS = MOTION["motion_dungeon"]["compile"]["timing_hold_frames"]
BONES = [tuple(v) for v in MOTION["rig"]["bones"]]

def line_points(a, b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): return out
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy

def rig_ascii(key):
    j={n:tuple(v) for n,v in key["pose_rig"].items()}
    xs=[p[0] for p in j.values()]; ys=[p[1] for p in j.values()]
    minx,maxx=min(xs)-3,max(xs)+3; miny,maxy=min(ys)-3,max(ys)+3
    w=max(22,maxx-minx+1); h=max(16,maxy-miny+1)
    g=[[" "]*w for _ in range(h)]
    def q(p): return p[0]-minx,p[1]-miny
    for a,b in BONES:
        pa,pb=q(j[a]),q(j[b])
        for x,y in line_points(pa,pb)[1:-1]:
            if 0<=x<w and 0<=y<h and g[y][x]==" ":
                dx=pb[0]-pa[0]; dy=pb[1]-pa[1]
                g[y][x]="/" if dx*dy<0 else ("\\" if dx*dy>0 else ("-" if dy==0 else "|"))
    for name,p in j.items():
        x,y=q(p)
        g[y][x]="O" if name=="head" else ("@" if name=="pelvis" else ("+" if name=="chest" else ("o" if "elbow" in name or "knee" in name else "*")))
    support=key["support_contact"]
    for side,node in [("L","l_foot"),("R","r_foot")]:
        x,y=q(j[node])
        if key["contact_state"]=="PRECONTACT" and ((key["name"].endswith("_TO_L") and side=="L") or (key["name"].endswith("_TO_R") and side=="R")):
            g[y][x]="?"
        elif support==side:
            g[y][x]="!"
        else:
            g[y][x]="~"
    return "\n".join("".join(r).rstrip() for r in g)

def compile_frames():
    out=[]
    for key in MOTION["keys"]:
        art=rig_ascii(key)
        for _ in range(int(HOLDS[key["timing_class"]])):
            out.append((key,art))
    return out

def render_mp4(path: Path):
    frames=compile_frames()
    tmp=HERE/".motion-frames"; shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir()
    mono="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    font=ImageFont.truetype(mono,16); small=ImageFont.truetype(mono,10)
    for i,(key,art) in enumerate(frames):
        im=Image.new("RGB",(960,520),(10,10,11)); d=ImageDraw.Draw(im)
        d.text((16,10),"ASCII KINESIS · LOCOMOTION 014 · FIGURE-EIGHT CURVATURE SIGN REVERSAL",font=small,fill=(190,190,190))
        d.text((16,28),f'{key["key_id"]} {key["name"]}  support={key["support_contact"]}  contact={key["contact_state"]}',font=small,fill=(238,238,235))
        d.multiline_text((34,62),art,font=font,fill=(246,246,240),spacing=1)
        mech=key["mechanics"]
        d.text((16,485),f'root={mech["root_xy"]} heading={mech["heading_deg"]}° curvature={mech["curvature"]} bank={mech["bank_units"]}  |  no source pixels',font=small,fill=(160,160,160))
        im.save(tmp/f"f_{i:04d}.png",compress_level=9)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(tmp/"f_%04d.png"),
                    "-c:v","libx264","-preset","veryslow","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",str(path)],check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(path),"-f","null","-"],check=True)

def build_spa(mp4_path: Path):
    motion_text=(HERE/"motion.json").read_text(encoding="utf-8")
    video=base64.b64encode(mp4_path.read_bytes()).decode("ascii")
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(MOTION["title"])}</title><style>
body{{font-family:system-ui,sans-serif;margin:0;padding:16px}}nav{{display:flex;gap:8px;position:sticky;top:0;background:Canvas;padding:8px 0}}
section{{display:none}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}
video{{max-width:100%;height:auto;background:#000}}</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre>{html.escape(CONTACT)}</pre></section><section id="json"><pre>{html.escape(motion_text)}</pre></section>
<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{video}"></video></section>
<script>const bs=[...document.querySelectorAll("[data-view]")];for(const b of bs)b.onclick=()=>{{for(const s of document.querySelectorAll("section"))s.classList.remove("active");document.getElementById(b.dataset.view).classList.add("active")}};</script>
</body></html>'''
    (HERE/f"{SLUG}.motion.html").write_text(page,encoding="utf-8")

if __name__=="__main__":
    mp4=HERE/f"{SLUG}.motion.mp4"
    render_mp4(mp4)
    build_spa(mp4)
