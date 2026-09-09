#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, html, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION_PATH = HERE / "motion.json"
CONTACT_PATH = HERE / "contact_sheet.txt"
MP4_PATH = HERE / "motion.mp4"
SPA_PATH = HERE / "throw-release-force-chain-repair.motion.html"

COLS, ROWS = 64, 24
CELL_W, CELL_H = 12, 18
WIDTH, HEIGHT = COLS * CELL_W, ROWS * CELL_H
FPS = 24
GROUND_Y = 21

def font():
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).is_file():
            return ImageFont.truetype(p, 16)
    return ImageFont.load_default()

FONT = font()

def blank_grid():
    g = [[" " for _ in range(COLS)] for _ in range(ROWS)]
    for x in range(COLS):
        g[GROUND_Y][x] = "_"
    return g

def put(g, x, y, ch):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < COLS and 0 <= y < ROWS:
        g[y][x] = ch

def line_char(x0,y0,x1,y1):
    dx, dy = x1-x0, y1-y0
    if abs(dx) >= abs(dy)*2: return "-"
    if abs(dy) >= abs(dx)*2: return "|"
    return "\\" if dx*dy >= 0 else "/"

def draw_line(g, a, b):
    x0,y0 = [int(round(v)) for v in a]
    x1,y1 = [int(round(v)) for v in b]
    dx, dy = abs(x1-x0), -abs(y1-y0)
    sx, sy = (1 if x0<x1 else -1), (1 if y0<y1 else -1)
    err = dx+dy
    ch = line_char(x0,y0,x1,y1)
    while True:
        put(g,x0,y0,ch)
        if x0==x1 and y0==y1: break
        e2 = 2*err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy

def render_pose(joints):
    g = blank_grid()
    segments = [
        ("head","neck"),
        ("neck","root"),
        ("neck","throw_shoulder"),("throw_shoulder","throw_elbow"),("throw_elbow","throw_hand"),
        ("neck","off_shoulder"),("off_shoulder","off_elbow"),("off_elbow","off_hand"),
        ("root","rear_knee"),("rear_knee","rear_foot"),
        ("root","front_knee"),("front_knee","front_foot"),
    ]
    for a,b in segments:
        draw_line(g,joints[a],joints[b])
    put(g,*joints["head"],"O")
    put(g,*joints["neck"],"+")
    put(g,*joints["root"],"@")
    for n in ("throw_shoulder","throw_elbow","off_shoulder","off_elbow","rear_knee","front_knee"):
        put(g,*joints[n],"+")
    put(g,*joints["throw_hand"],"T")
    put(g,*joints["off_hand"],"*")
    put(g,*joints["rear_foot"],"A")
    put(g,*joints["front_foot"],"B")
    bx,by=joints["ball"]
    if 0 <= bx < COLS and 0 <= by < ROWS:
        put(g,bx,by,"o")
    return "\n".join("".join(r).rstrip() for r in g)

def interp(a,b,t):
    u = t*t*(3.0-2.0*t)
    out={}
    for n,p in a.items():
        q=b[n]
        x=p[0]+(q[0]-p[0])*u
        y=p[1]+(q[1]-p[1])*u
        if n in {"throw_hand","throw_elbow","ball"}:
            y -= math.sin(math.pi*u)*0.55
        if n in {"off_hand","off_elbow"}:
            y += math.sin(math.pi*u)*0.25
        out[n]=[x,y]
    return out

def compile_frames(motion):
    frames=[]
    keys=motion["keys"]
    for i,k in enumerate(keys):
        joints=k["pose_rig"]["joints"]
        for _ in range(int(k["compile_hold_frames"])):
            frames.append((k["key_id"], k["support_contact"], k["object_custody"], joints))
        travel=int(k.get("travel_to_next_frames",0))
        if i+1 < len(keys):
            nxt=keys[i+1]
            if travel and (k["support_contact"] != nxt["support_contact"] or k["object_custody"] != nxt["object_custody"] or k.get("causal_boundary_to_next")):
                raise SystemExit(f"semantic connector forbidden: {k['key_id']}->{nxt['key_id']}")
            for j in range(1,travel+1):
                t=j/(travel+1.0)
                frames.append((f"{k['key_id']}~{nxt['key_id']}", k["support_contact"], k["object_custody"], interp(joints,nxt["pose_rig"]["joints"],t)))
    return frames

def render_image(ascii_frame):
    img=Image.new("RGB",(WIDTH,HEIGHT),(10,10,12))
    d=ImageDraw.Draw(img)
    for y,row in enumerate(ascii_frame.splitlines()):
        d.text((0,y*CELL_H),row,font=FONT,fill=(238,238,232))
    return img

def write_video(frames):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,(_,_,_,joints) in enumerate(frames):
            render_image(render_pose(joints)).save(td/f"{i:04d}.png")
        cmd=["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(td/"%04d.png"),
             "-c:v","libx264","-preset","veryslow","-crf","20","-pix_fmt","yuv420p",
             "-movflags","+faststart",str(MP4_PATH)]
        subprocess.run(cmd,check=True)

def contact_sheet(motion):
    parts=[
        motion["title"],
        f"{motion['experiment_id']} | abstract ASCII rig + object channel only | source pixels/audio absent",
        "Legend: O head | @ COM/root | T throwing hand | * off hand | A rear-foot channel | B front-foot channel | o object",
        "Source timestamps below are OBSERVED slow-motion presentation anchors only. All acting/support/custody/release/compile timing is INFERRED.",
        ""
    ]
    for k in motion["keys"]:
        src=k.get("source_anchor")
        src_text=f"{src['time_s']:.3f}s OBSERVED — {src['meaning']}" if src else "—"
        parts += [
            f"{k['key_id']} {k['causal_role']} | {k['timing_class']} / {k['timing_provenance']}",
            f"source_anchor {src_text}",
            f"support {k['support_contact']} | custody {k['object_custody']}",
            f"root/arc {k['motion_arc_root_note']}",
            f"acting {k['acting_note']}",
            "",
            render_pose(k["pose_rig"]["joints"]),
            "",
            ""
        ]
    return "\n".join(parts).rstrip()+"\n"

def build_spa(motion, contact, mp4_bytes):
    motion_text=json.dumps(motion,ensure_ascii=False,separators=(",",":"))+"\\n"
    asc=base64.b64encode(gzip.compress(contact.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    jsn=base64.b64encode(gzip.compress(motion_text.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    video_b64=base64.b64encode(mp4_bytes).decode("ascii")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis · VideoMotion011</title>
<style>
:root{{color-scheme:dark;background:#0a0a0c;color:#eee;font-family:system-ui,sans-serif}}
body{{margin:0;padding:16px}} nav{{display:flex;gap:8px;position:sticky;top:0;background:#0a0a0c;padding:8px 0}}
section[hidden]{{display:none}} button{{font:inherit;padding:8px 14px}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #555;padding:12px}}
video{{max-width:100%;height:auto;background:#000;border:1px solid #555}}
</style>
</head><body>
<h1>Throw repair · rear-load → pelvis lead → release fork → displaced recovery debt</h1>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii"><pre id="ascii-pre"></pre></section>
<section id="json" hidden><pre id="json-pre"></pre></section>
<section id="video" hidden><video controls loop muted playsinline src="data:video/mp4;base64,{video_b64}"></video></section>
<script>
const A="{asc}",J="{jsn}";
async function gunzip(b){{const u=Uint8Array.from(atob(b),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([u]).stream().pipeThrough(ds)).text()}}
(async()=>{{document.querySelector("#ascii-pre").textContent=await gunzip(A);document.querySelector("#json-pre").textContent=await gunzip(J)}})();
const B=[...document.querySelectorAll("button[data-view]")];function show(id){{for(const b of B)b.setAttribute("aria-pressed",String(b.dataset.view===id));for(const s of document.querySelectorAll("section[id]"))s.hidden=s.id!==id}}for(const b of B)b.onclick=()=>show(b.dataset.view);show("ascii");
</script></body></html>
"""

def main():
    motion=json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    frames=compile_frames(motion)
    if len(frames) != int(motion["timing"]["total_frames"]):
        raise SystemExit(f"frame count mismatch {len(frames)} != {motion['timing']['total_frames']}")
    contact=contact_sheet(motion)
    CONTACT_PATH.write_text(contact,encoding="utf-8")
    write_video(frames)
    mp4=MP4_PATH.read_bytes()
    expected=motion.get("media",{}).get("sha256")
    if expected and hashlib.sha256(mp4).hexdigest()!=expected:
        raise SystemExit("media sha mismatch")
    SPA_PATH.write_text(build_spa(motion,contact,mp4),encoding="utf-8")
    print(json.dumps({
        "frames":len(frames),
        "mp4_sha256":hashlib.sha256(mp4).hexdigest(),
        "mp4_bytes":len(mp4),
        "contact_sha256":hashlib.sha256(contact.encode()).hexdigest(),
        "spa_sha256":hashlib.sha256(SPA_PATH.read_bytes()).hexdigest()
    },sort_keys=True))

if __name__=="__main__":
    main()
