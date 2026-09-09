#!/usr/bin/env python3
from __future__ import annotations
import base64, html, json, subprocess, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
SLUG = "figure-eight-curvature-sign-reversal"
FPS = int(MOTION["motion_dungeon"]["compile"]["fps"])
HOLDS = MOTION["motion_dungeon"]["compile"]["timing_hold_frames"]
BONES = [tuple(v) for v in MOTION["rig"]["bones"]]
WORLD_W = int(MOTION["rig"]["world_grid"]["width"])
WORLD_H = int(MOTION["rig"]["world_grid"]["height"])
CROSS = tuple(MOTION["rig"]["world_grid"]["crossover_xy"])

def line_points(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): return out
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy

def draw_rig(g,key,offset=(0,0)):
    j={n:tuple(v) for n,v in key["pose_rig"].items()}
    ox,oy=offset
    def q(p): return (p[0]-ox,p[1]-oy)
    h=len(g); w=len(g[0]) if h else 0
    for a,b in BONES:
        pa,pb=q(j[a]),q(j[b])
        for x,y in line_points(pa,pb)[1:-1]:
            if 0<=x<w and 0<=y<h and g[y][x]==" ":
                dx=pb[0]-pa[0]; dy=pb[1]-pa[1]
                g[y][x]="/" if dx*dy<0 else ("\\" if dx*dy>0 else ("-" if dy==0 else "|"))
    for name,p in j.items():
        x,y=q(p)
        if 0<=x<w and 0<=y<h:
            g[y][x]="O" if name=="head" else ("@" if name=="pelvis" else ("+" if name=="chest" else ("o" if "elbow" in name or "knee" in name else "*")))
    probe=key.get("probe_foot")
    support=key["support_contact"]
    for side,node in [("L","l_foot"),("R","r_foot")]:
        x,y=q(j[node])
        if 0<=x<w and 0<=y<h:
            if key["contact_state"]=="PRECONTACT" and probe==side:
                g[y][x]="?"
            elif support==side:
                g[y][x]="!"
            else:
                g[y][x]="~"

def local_ascii(key):
    j={n:tuple(v) for n,v in key["pose_rig"].items()}
    xs=[p[0] for p in j.values()]; ys=[p[1] for p in j.values()]
    minx,maxx=min(xs)-3,max(xs)+3; miny,maxy=min(ys)-3,max(ys)+3
    w=max(22,maxx-minx+1); h=max(16,maxy-miny+1)
    g=[[" "]*w for _ in range(h)]
    draw_rig(g,key,(minx,miny))
    return "\n".join("".join(r).rstrip() for r in g)

def world_ascii(key):
    g=[[" "]*WORLD_W for _ in range(WORLD_H)]
    for x in range(WORLD_W):
        g[0][x]="-"; g[WORLD_H-1][x]="-"
    for y in range(WORLD_H):
        g[y][0]="|"; g[y][WORLD_W-1]="|"
    if 0<CROSS[0]<WORLD_W-1 and 0<CROSS[1]<WORLD_H-1:
        g[CROSS[1]][CROSS[0]]="x"
    draw_rig(g,key,(0,0))
    return "\n".join("".join(r).rstrip() for r in g)

def root_map():
    g=[[" "]*WORLD_W for _ in range(WORLD_H)]
    for x in range(WORLD_W):
        g[0][x]="-"; g[WORLD_H-1][x]="-"
    for y in range(WORLD_H):
        g[y][0]="|"; g[y][WORLD_W-1]="|"
    cx,cy=CROSS; g[cy][cx]="x"
    pts=[]
    for key in MOTION["keys"]:
        x,y=[int(round(v)) for v in key["mechanics"]["root_xy"]]
        pts.append((x,y))
        if 0<x<WORLD_W-1 and 0<y<WORLD_H-1: g[y][x]="o"
    for a,b in zip(pts,pts[1:]):
        for x,y in line_points(a,b)[1:-1]:
            if 0<x<WORLD_W-1 and 0<y<WORLD_H-1 and g[y][x]==" ": g[y][x]="."
    if pts:
        sx,sy=pts[0]; ex,ey=pts[-1]; g[sy][sx]="S"; g[ey][ex]="E"
    return "\n".join("".join(r).rstrip() for r in g)

def make_contact_sheet():
    lines=[
        "ASCII KINESIS V2 LOCOMOTION 014 — FIGURE-EIGHT CURVATURE SIGN REVERSAL",
        "Legend: ! trusted support   ? precontact probe   ~ free foot   @ pelvis/root   + chest   O head   x crossover",
        "Timing: ONES/TWOS/FOURS are display-frame exposure classes; every decisive timing here is INFERRED / STREET_FIGHTER-CAPCOM.",
        "",
        "ROOT TRAVEL MAP — fixed world address; dots audit authored root travel and do not reproduce source choreography:",
        root_map(),""
    ]
    for key in MOTION["keys"]:
        m=key["mechanics"]
        lines += [
            f'{key["key_id"]} {key["name"]}  [{key["timing_class"]} / {key["timing_provenance"]}]  SUPPORT={key["support_contact"]}  CONTACT={key["contact_state"]}',
            f'ROOT={m["root_xy"]}  HEADING={m["heading_deg"]:+.1f}deg  CURVATURE={m["curvature"]:+.2f}  BANK={m["bank_units"]:+.2f}  SPACING={m["spacing_from_prev"]}',
            f'ROLE: {key["causal_role"]}', local_ascii(key), ""
        ]
    return "\n".join(lines).rstrip()+"\n"

def compile_frames():
    out=[]
    for key in MOTION["keys"]:
        art=world_ascii(key)
        for _ in range(int(HOLDS[key["timing_class"]])):
            out.append((key,art))
    return out

def render_mp4(path: Path):
    frames=compile_frames()
    tmp=HERE/".motion-frames"; shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir()
    mono="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    font=ImageFont.truetype(mono,10); small=ImageFont.truetype(mono,10)
    for i,(key,art) in enumerate(frames):
        im=Image.new("RGB",(960,520),(10,10,11)); d=ImageDraw.Draw(im)
        d.text((16,8),"ASCII KINESIS · LOCOMOTION 014 · FIGURE-EIGHT CURVATURE SIGN REVERSAL",font=small,fill=(190,190,190))
        d.text((16,24),f'{key["key_id"]} {key["name"]}   support={key["support_contact"]}   {key["contact_state"]}',font=small,fill=(238,238,235))
        d.multiline_text((18,42),art,font=font,fill=(246,246,240),spacing=0)
        mech=key["mechanics"]
        d.text((16,501),f'heading={mech["heading_deg"]:+.1f}°  curvature={mech["curvature"]:+.2f}  bank={mech["bank_units"]:+.2f}  frame {i+1:02d}/{len(frames)} · abstract ASCII only',font=small,fill=(160,160,160))
        im.save(tmp/f"f_{i:04d}.png",compress_level=9)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(tmp/"f_%04d.png"),
                    "-c:v","libx264","-preset","veryslow","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart",
                    "-metadata","comment=ASCII Kinesis abstract rig only",str(path)],check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(path),"-f","null","-"],check=True)

def build_spa(mp4_path: Path):
    contact=(HERE/"contact-sheet.txt").read_text(encoding="utf-8")
    motion_text=(HERE/"motion.json").read_text(encoding="utf-8")
    video=base64.b64encode(mp4_path.read_bytes()).decode("ascii")
    page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
body{{font-family:system-ui,sans-serif;margin:0;padding:16px}}nav{{display:flex;gap:8px;position:sticky;top:0;background:Canvas;padding:8px 0}}
section{{display:none}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}
video{{max-width:100%;height:auto;background:#000}}</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre>{ascii}</pre></section><section id="json"><pre>{json}</pre></section>
<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{video}"></video></section>
<script>const bs=[...document.querySelectorAll("[data-view]")];for(const b of bs)b.onclick=()=>{{for(const s of document.querySelectorAll("section"))s.classList.remove("active");document.getElementById(b.dataset.view).classList.add("active")}};</script>
</body></html>'''.format(title=html.escape(MOTION["title"]),ascii=html.escape(contact),json=html.escape(motion_text),video=video)
    (HERE/f"{SLUG}.motion.html").write_text(page,encoding="utf-8")

if __name__=="__main__":
    (HERE/"contact-sheet.txt").write_text(make_contact_sheet(),encoding="utf-8")
    mp4=HERE/f"{SLUG}.motion.mp4"
    render_mp4(mp4)
    build_spa(mp4)
