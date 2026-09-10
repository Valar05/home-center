#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from copy import deepcopy
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MOTION = json.loads((ROOT / "motion.json").read_text(encoding="utf-8"))
GRID = MOTION["rig"]["grid"]
GW, GH = GRID["width"], GRID["height"]
GROUND_Y, WALL_X, TARGET_X = GRID["ground_y"], GRID["rear_wall_x"], GRID["target_x"]
W, H, FPS = MOTION["compile"]["width"], MOTION["compile"]["height"], MOTION["compile"]["fps"]
TIMING = MOTION["compile"]["timing_frames"]
OVERRIDES = MOTION["compile"].get("hold_overrides", {})
VIDEO_NAME = "rear-clearance-gates-commit-step-debt.mp4"
SPA_NAME = "rear-clearance-gates-commit-step-debt.motion.html"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

POINT_FIELDS = ["root","head","rear_hand","front_hand","rear_knee","front_knee",
                "rear_foot","front_foot","rear_end","front_end"]

def put(g, x, y, ch):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < GW and 0 <= y < GH:
        g[y][x] = ch

def bres(a, b):
    x0,y0 = map(lambda v:int(round(v)), a); x1,y1 = map(lambda v:int(round(v)), b)
    pts=[]; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err += dy; x0 += sx
        if e2<=dx: err += dx; y0 += sy
    return pts

def line(g, a, b, ch):
    for x,y in bres(a,b):
        put(g,x,y,ch)

def foot_symbol(state):
    return {"ACTIVE":"*","LIGHT":".","AIR":"^"}.get(state, "?")

def ascii_pose(k, label=False):
    g = [[" "]*GW for _ in range(GH)]
    for y in range(2, GROUND_Y+1):
        put(g, WALL_X, y, "#")
    for x in range(5, GW-3):
        put(g, x, GROUND_Y, "_")
    for y in range(7, GROUND_Y+1):
        put(g, TARGET_X, y, "|")

    p = k["pose_rig"]
    root, head = p["root"], p["head"]
    shoulder = [round((root[0]+head[0])/2), max(head[1]+3, root[1]-3)]
    line(g, root, shoulder, "|"); line(g, shoulder, head, "|"); put(g,*head,"O")
    line(g, shoulder, p["rear_hand"], "/"); line(g, shoulder, p["front_hand"], "\\")
    line(g, root, p["rear_knee"], "/"); line(g, p["rear_knee"], p["rear_foot"], "/")
    line(g, root, p["front_knee"], "\\"); line(g, p["front_knee"], p["front_foot"], "\\")
    put(g,*p["rear_knee"],"o"); put(g,*p["front_knee"],"o")
    put(g,*p["rear_foot"], foot_symbol(k["rear_foot_state"]))
    put(g,*p["front_foot"], foot_symbol(k["front_foot_state"]))
    put(g,*root,"@")

    line(g, p["rear_end"], p["rear_hand"], "=")
    line(g, p["rear_hand"], p["front_hand"], "=")
    line(g, p["front_hand"], p["front_end"], "=")
    put(g,*p["rear_end"],"B")
    put(g,*p["rear_hand"],"+")
    put(g,*p["front_hand"],"+")
    if k["contact"] in {"TARGET","TARGET_HOLD"}:
        put(g,*p["front_end"],"X")
    else:
        put(g,*p["front_end"],"T")
    rows = ["".join(r).rstrip() for r in g]
    body = "\n".join(rows)
    if label:
        return f"{k['key_id']} {k['name']}\n{body}"
    return body

def make_contact_sheet():
    header = (
        "ASCII KINESIS V2 STRIKES025 — REAR CLEARANCE GATES COMMIT STEP DEBT\n"
        "Pocket rule: THE STRIKE OWES A STEP BEFORE IT OWES A THRUST. IF THE BUTT HAS NO REAR ROOM, ROOT SUPPORT MUST MOVE FIRST.\n"
        "Legend: # rear obstruction | | target | B staff butt | T staff tip | X target contact | + hands | O head | @ root | o knee | * active support | . light | ^ air | _ ground\n"
        "Source: STRIKES PASS 005 — VERIFIED | Home Center evidence 1BW6UzsUckanhIqsAIcO6mWhc7FNCHGCX7A5tsdfO1EU | TSR asset 23976 | Donatello — TMNT Tournament Fighters — SNES.\n"
        "Source roles: POSE_REFERENCE + CONTACT_REFERENCE. Timing authority=false. Source timing=UNKNOWN.\n"
        "OBSERVED: complete static long-weapon fighter sheet; long staff extension and front/rear tool volume; commissioned lifecycle explicitly proposes a rear-occluded partial-cover follow-up testing root movement before coil.\n"
        "INFERRED: this entire authored pose order, root/support clearance gate, contact, hit-stop implication, recoil, overshoot, lag, recovery and all timing. Direction=STREET_FIGHTER/CAPCOM.\n"
        "Rights firewall: independent abstract ASCII biped + line-segment staff only. No source pixels, palette, costume/contours, sheet layout, tracing, source choreography/audio, redistribution or close imitation.\n\n"
    )
    chunks=[]
    for k in MOTION["keys"]:
        chunks.append(
            ascii_pose(k, True) + "\n" +
            f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']} | causal_role={k['causal_role']}\n" +
            f"support={k['support_contact']} | contact={k['contact']} | rear_foot={k['rear_foot_state']} | front_foot={k['front_foot_state']}\n" +
            f"root_note={k['motion_arc_root_note']}\nclearance_note={k['clearance_note']}"
        )
    return header + "\n\n".join(chunks) + "\n"

def smoothstep(t):
    return t*t*(3-2*t)

def interp_key(a, b, t):
    u = smoothstep(t)
    out = deepcopy(a if t < 0.5 else b)
    out["key_id"] = f"{a['key_id']}→{b['key_id']}"
    out["name"] = "CONNECTIVE"
    out["pose_rig"] = {}
    for field in POINT_FIELDS:
        av, bv = a["pose_rig"][field], b["pose_rig"][field]
        out["pose_rig"][field] = [av[0] + (bv[0]-av[0])*u, av[1] + (bv[1]-av[1])*u]
    return out

def compile_frames():
    keys=MOTION["keys"]; frames=[]
    for i,k in enumerate(keys):
        n = int(OVERRIDES.get(k["key_id"], TIMING[k["timing_class"]]))
        frames.extend([deepcopy(k) for _ in range(n)])
        if i+1 < len(keys):
            frames.append(interp_key(k, keys[i+1], 0.5))
    return frames

def render_frame(k, path):
    img=Image.new("RGB",(W,H),"black"); d=ImageDraw.Draw(img)
    font=ImageFont.truetype(FONT,10); small=ImageFont.truetype(FONT,9)
    d.text((10,6), f"STRIKES025 | {k['key_id']} | {k['name']}", font=small, fill="white")
    d.multiline_text((10,20), ascii_pose(k,False), font=font, fill="white", spacing=0)
    d.text((10,H-62), f"SUPPORT {k['support_contact']} | CONTACT {k['contact']}", font=small, fill="white")
    d.text((10,H-49), "CLOCK: DENIED COIL → CLEARING STEP → LEGAL COIL → AXIS → PRECONTACT → CONTACT → BODY CHECK → AXIAL WITHDRAW", font=small, fill="white")
    d.text((10,H-36), "DEBT: support purchases rear volume before commitment; long-tool overshoot/hand lag must settle into a displaced ready", font=small, fill="white")
    d.text((10,H-23), "SOURCE ART ABSENT | authored geometry/timing/causality INFERRED | source timing UNKNOWN", font=small, fill="white")
    img.save(path)

def build_video(out):
    frames=compile_frames()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,k in enumerate(frames):
            render_frame(k, td/f"{i:04d}.png")
        subprocess.run([
            "ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(td/"%04d.png"),
            "-c:v","libx264","-crf","32","-preset","veryslow","-pix_fmt","yuv420p","-movflags","+faststart",str(out)
        ], check=True)
    return len(frames)

def make_spa(ascii_text, motion_text, video_bytes):
    a64=base64.b64encode(gzip.compress(ascii_text.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    j64=base64.b64encode(gzip.compress(motion_text.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    v64=base64.b64encode(video_bytes).decode("ascii")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Strikes025 — Rear Clearance Gates Commit Step Debt</title>
<style>body{{margin:0;background:#0b0c0f;color:#f3f3f3;font-family:ui-monospace,Menlo,Consolas,monospace}}nav{{position:sticky;top:0;background:#15171d;padding:10px;display:flex;gap:8px}}button{{font:inherit;padding:8px 14px}}main{{padding:12px}}section{{display:none}}section.active{{display:block}}pre{{white-space:pre;overflow:auto;font-variant-ligatures:none;line-height:1}}video{{max-width:100%;height:auto;background:black}}</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><main>
<section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls loop playsinline src="data:video/mp4;base64,{v64}"></video></section>
</main><script>
const ss=[...document.querySelectorAll("section")];for(const b of document.querySelectorAll("button[data-view]"))b.onclick=()=>{{ss.forEach(s=>s.classList.toggle("active",s.id===b.dataset.view));}};
async function gunzip(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip")));return r.text();}}
Promise.all([gunzip("{a64}"),gunzip("{j64}")]).then(([a,j])=>{{document.getElementById("a").textContent=a;document.getElementById("j").textContent=j;}});
</script></body></html>'''

def main():
    contact=make_contact_sheet()
    (ROOT/"contact-sheet.txt").write_text(contact,encoding="utf-8")
    video=ROOT/VIDEO_NAME
    n=build_video(video)
    motion_text=(ROOT/"motion.json").read_text(encoding="utf-8")
    spa=ROOT/SPA_NAME
    spa.write_text(make_spa(contact,motion_text,video.read_bytes()),encoding="utf-8")
    print(json.dumps({
        "frames":n,"fps":FPS,"video":str(video),"spa":str(spa),
        "video_bytes":video.stat().st_size,
        "video_sha256":hashlib.sha256(video.read_bytes()).hexdigest()
    },sort_keys=True))
if __name__=="__main__":
    main()
