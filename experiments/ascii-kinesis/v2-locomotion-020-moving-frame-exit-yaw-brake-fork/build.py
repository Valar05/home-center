#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
MOTION = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
W, H = map(int, MOTION["rig"]["viewport"])
FPS = int(MOTION["timing"]["fps"])
FRAMES_DIR = HERE / "_frames"
MP4 = HERE / "_authoritative.mp4"
ASCII = HERE / "contact-sheet.txt"
SPA = HERE / "moving-frame-exit-yaw-brake-fork.motion.html"

def body_points(k):
    rx, ry = map(float, k["root"])
    lean = math.radians(float(k["torso_lean_deg"]))
    yaw = math.radians(float(k["yaw_deg"]))
    chest = (rx + math.sin(lean)*40.0, ry - math.cos(lean)*40.0)
    neck = (chest[0] + math.sin(lean)*8.0, chest[1] - math.cos(lean)*8.0)
    head = (neck[0] + math.sin(lean)*12.0 + float(k.get("head_lag_x", 0)),
            neck[1] - math.cos(lean)*12.0)
    span = 13.0 * max(0.42, abs(math.cos(yaw)))
    depth = 5.0 * math.sin(yaw)
    left_sh = (chest[0]-span, chest[1]-depth)
    right_sh = (chest[0]+span, chest[1]+depth)
    lh = (chest[0]+float(k["left_hand_offset"][0]), chest[1]+float(k["left_hand_offset"][1]))
    rh = (chest[0]+float(k["right_hand_offset"][0]), chest[1]+float(k["right_hand_offset"][1]))
    lf = tuple(map(float, k["left_foot"]))
    rf = tuple(map(float, k["right_foot"]))
    lk_mid = ((rx+lf[0])/2.0, (ry+lf[1])/2.0)
    rk_mid = ((rx+rf[0])/2.0, (ry+rf[1])/2.0)
    lk = (lk_mid[0] + (9 if lf[0] >= rx else -9), lk_mid[1]-5)
    rk = (rk_mid[0] + (9 if rf[0] >= rx else -9), rk_mid[1]-5)
    le = ((left_sh[0]+lh[0])/2.0-5, (left_sh[1]+lh[1])/2.0+5)
    re = ((right_sh[0]+rh[0])/2.0+5, (right_sh[1]+rh[1])/2.0+5)
    return {
        "root":(rx,ry),"chest":chest,"head":head,
        "left_sh":left_sh,"right_sh":right_sh,
        "left_hand":lh,"right_hand":rh,
        "left_elbow":le,"right_elbow":re,
        "left_knee":lk,"right_knee":rk,
        "left_foot":lf,"right_foot":rf
    }

def support_kind(k, side):
    s = str(k["support"].get(side.lower(), "")).upper()
    if "PROBE" in s:
        return "probe"
    if any(x in s for x in ("PLANTED", "SUPPORT", "CATCH")):
        return "plant"
    return "free"

def quadratic_bezier(p0,p1,p2,t):
    u=1-t
    return (u*u*p0[0]+2*u*t*p1[0]+t*t*p2[0],
            u*u*p0[1]+2*u*t*p1[1]+t*t*p2[1])

def draw_environment(d, frame_index):
    rig=MOTION["rig"]
    y=int(rig["fixed_floor_reference_y"])
    mf=rig["moving_frame"]; x0=int(mf["x0"]); x1=int(mf["x1"])
    d.rectangle((x0,y,x1,y+15), fill=(64,69,77), outline=(130,137,148), width=2)
    phase=(frame_index*7)%28
    for x in range(x0-28+phase,x1,28):
        d.line((x,y+4,x+10,y+4), fill=(176,183,193), width=2)
        d.line((x+10,y+4,x+5,y), fill=(176,183,193), width=2)
        d.line((x+10,y+4,x+5,y+8), fill=(176,183,193), width=2)
    d.line((x1,y,W,y), fill=(58,62,69), width=2)
    lane=rig["turn_lane"]
    p0=tuple(lane["entry"]); p1=tuple(lane["control"]); p2=tuple(lane["exit"])
    prev=p0
    for i in range(1,31):
        t=i/30
        cur=quadratic_bezier(p0,p1,p2,t)
        d.line((prev[0],prev[1]+10,cur[0],cur[1]+10), fill=(50,54,61), width=2)
        prev=cur
    for x in range(x1+18,W,34):
        d.line((x,y-4,x,y+4), fill=(78,83,91), width=1)

def draw_frame(k, frame_index, outpath):
    im=Image.new("RGB",(W,H),(14,16,19))
    d=ImageDraw.Draw(im)
    draw_environment(d, frame_index)
    p=body_points(k)
    body=(235,238,242); secondary=(185,193,202); rootc=(247,207,92)
    d.line([p["root"],p["left_knee"],p["left_foot"]], fill=body, width=5)
    d.line([p["root"],p["right_knee"],p["right_foot"]], fill=body, width=5)
    d.line([p["root"],p["chest"]], fill=body, width=7)
    d.line([p["left_sh"],p["left_elbow"],p["left_hand"]], fill=secondary, width=4)
    d.line([p["right_sh"],p["right_elbow"],p["right_hand"]], fill=secondary, width=4)
    hx,hy=p["head"]; d.ellipse((hx-10,hy-10,hx+10,hy+10), outline=body, width=4)
    rx,ry=p["root"]; d.polygon([(rx,ry-6),(rx+6,ry),(rx,ry+6),(rx-6,ry)], outline=rootc)
    for side in ("left","right"):
        fx,fy=p[f"{side}_foot"]
        d.line((fx-9,fy,fx+9,fy), fill=body, width=4)
        kind=support_kind(k,side)
        if kind=="plant":
            d.ellipse((fx-5,fy+4,fx+5,fy+13), fill=(111,199,142))
        elif kind=="probe":
            d.ellipse((fx-5,fy+4,fx+5,fy+13), outline=(225,169,88), width=2)
    d.text((14,14), k["key_id"], fill=(92,98,108))
    im.save(outpath,"PNG",optimize=False)

def grid_line(grid,x0,y0,x1,y1,ch):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        if 0<=y0<len(grid) and 0<=x0<len(grid[0]): grid[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def to_grid(pt):
    x,y=pt
    return int(round((x-8)/430*71)), int(round((y-82)/178*23))

def ascii_pose(k):
    grid=[[" "]*72 for _ in range(24)]
    y=MOTION["rig"]["fixed_floor_reference_y"]
    gy=to_grid((0,y))[1]
    if 0<=gy<24:
        for x in range(72): grid[gy][x]="." if x%4 else ":"
    mf=MOTION["rig"]["moving_frame"]
    a=to_grid((mf["x0"],mf["top_y"])); b=to_grid((mf["x1"],mf["top_y"]))
    grid_line(grid,*a,*b,"=")
    lane=MOTION["rig"]["turn_lane"]
    p0=tuple(lane["entry"]); p1=tuple(lane["control"]); p2=tuple(lane["exit"])
    last=to_grid(p0)
    for i in range(1,18):
        cur=to_grid(quadratic_bezier(p0,p1,p2,i/17))
        grid_line(grid,*last,*cur,".")
        last=cur
    p=body_points(k)
    for a_name,b_name,ch in [
        ("root","chest","|"),
        ("left_sh","left_elbow","/"),("left_elbow","left_hand","/"),
        ("right_sh","right_elbow","\\"),("right_elbow","right_hand","\\"),
        ("root","left_knee","/"),("left_knee","left_foot","/"),
        ("root","right_knee","\\"),("right_knee","right_foot","\\")]:
        grid_line(grid,*to_grid(p[a_name]),*to_grid(p[b_name]),ch)
    for nm,ch in [("head","O"),("chest","T"),("root","@"),
                  ("left_foot","_"),("right_foot","_"),
                  ("left_hand","o"),("right_hand","o")]:
        x,y=to_grid(p[nm])
        if 0<=y<24 and 0<=x<72: grid[y][x]=ch
    for side in ("left","right"):
        x,y=to_grid(p[f"{side}_foot"]); y=min(23,y+1)
        kind=support_kind(k,side)
        if 0<=x<72:
            if kind=="plant": grid[y][x]="*"
            elif kind=="probe": grid[y][x]="+"
    return "\n".join("".join(r).rstrip() for r in grid)

def make_contact_sheet():
    out=[
        "ASCII KINESIS V2 · LOCOMOTION 020 · MOVING-FRAME EXIT / YAW-BRAKE FORK",
        "legend: @ root/COM · * support owner · + probe · = old moving frame · . fixed turn lane · O head",
        "source evidence: Mowgli / The Jungle Book / Sega Genesis / asset 28829 / Home Center artifact 1BA2z9DYof9hEfdqYdt5SzUmMnkPe_uWpVpLfMXsB-vc",
        "source observations: whole sheet shows upright, low, airborne, hand-supported, and recovery families; static sheet gives support contrasts, not chronology.",
        "source timing authority: UNKNOWN / Animated GIFs (0) · authored cadence: INFERRED / STREET_FIGHTER-CAPCOM",
        "rights firewall: generic abstract rig only; no source pixels, palette, costume, contours, layout, tracing, choreography, audio, redistribution, or close imitation.",
        "thesis: exit a moving support frame onto fixed ground, spend inherited translation first, then earn a separate yaw catch; braking and heading change are distinct causal joins.",
        ""
    ]
    for k in MOTION["keys"]:
        out.append(
            f'{k["key_id"]} {k["name"]} · {k["timing_class"]}/{k["hold_frames"]}f · '
            f'{k["timing_provenance"]} · support={k["support"]["owner"]} · '
            f'phase={k["phase"]} · rootΔ={k["root_spacing_px"]}px · pathΔ={k["frame_spacing_px"]}px'
        )
        out.append(ascii_pose(k))
        out.append(f'causal: {k["causal_role"]}')
        out.append("")
    return "\n".join(out).rstrip()+"\n"

def make_spa(ascii_text,motion_text,mp4_bytes):
    ab64=base64.b64encode(gzip.compress(ascii_text.encode("utf-8"),mtime=0)).decode("ascii")
    jb64=base64.b64encode(gzip.compress(motion_text.encode("utf-8"),mtime=0)).decode("ascii")
    vb64=base64.b64encode(mp4_bytes).decode("ascii")
    title="ASCII Kinesis V2 · Locomotion 020 · Moving-Frame Exit / Yaw-Brake Fork"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><style>
:root{{color-scheme:dark}}body{{margin:0;background:#0f1114;color:#edf0f3;font-family:system-ui,sans-serif}}header{{padding:14px 18px;border-bottom:1px solid #343943}}
nav{{display:flex;gap:8px}}button{{font:inherit;padding:7px 12px;background:#1a1e24;color:inherit;border:1px solid #4a515d;border-radius:6px}}
button[aria-selected="true"]{{background:#303641}}main{{padding:14px 18px}}section[hidden]{{display:none}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #343943;padding:12px;max-height:78vh}}
video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #343943}}</style></head><body>
<header><h1>{title}</h1><nav><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header>
<main><section id="ascii"><pre id="ascii-pre">loading exact persisted ASCII…</pre></section><section id="json" hidden><pre id="json-pre">loading exact persisted JSON…</pre></section>
<section id="video" hidden><video controls loop muted playsinline src="data:video/mp4;base64,{vb64}"></video></section></main>
<script>
const A="{ab64}",J="{jb64}";
async function gunzip64(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}}
Promise.all([gunzip64(A),gunzip64(J)]).then(([a,j])=>{{document.getElementById("ascii-pre").textContent=a;document.getElementById("json-pre").textContent=j;}});
const buttons=[...document.querySelectorAll('button[data-view]')];for(const b of buttons)b.addEventListener('click',()=>{{for(const q of buttons)q.setAttribute('aria-selected',q===b?'true':'false');for(const x of document.querySelectorAll('main section'))x.hidden=x.id!==b.dataset.view;}});
</script></body></html>
'''

def main():
    FRAMES_DIR.mkdir(exist_ok=True)
    for p in FRAMES_DIR.glob("*.png"): p.unlink()
    idx=0
    for k in MOTION["keys"]:
        for _ in range(int(k["hold_frames"])):
            draw_frame(k,idx,FRAMES_DIR/f"frame-{idx:04d}.png")
            idx+=1
    if idx != int(MOTION["timing"]["total_frames"]):
        raise SystemExit(f"frame count mismatch {idx}")
    cmd=[
        "ffmpeg","-hide_banner","-loglevel","error","-y",
        "-framerate",str(FPS),"-i",str(FRAMES_DIR/"frame-%04d.png"),
        "-vf","scale=480:270:flags=area","-an","-c:v","libx264","-pix_fmt","yuv420p",
        "-preset","veryslow","-crf","34","-movflags","+faststart",
        "-map_metadata","-1","-metadata","creation_time=1970-01-01T00:00:00Z",
        "-threads","1",str(MP4)
    ]
    subprocess.run(cmd,check=True)
    ascii_text=make_contact_sheet()
    ASCII.write_text(ascii_text,encoding="utf-8")
    motion_text=(HERE/"motion.json").read_text(encoding="utf-8")
    mp4=MP4.read_bytes()
    SPA.write_text(make_spa(ascii_text,motion_text,mp4),encoding="utf-8")
    print(json.dumps({
        "frames":idx,"fps":FPS,"mp4_bytes":len(mp4),
        "mp4_sha256":hashlib.sha256(mp4).hexdigest(),
        "ascii_bytes":len(ascii_text.encode("utf-8")),
        "ascii_sha256":hashlib.sha256(ascii_text.encode("utf-8")).hexdigest(),
        "motion_bytes":len(motion_text.encode("utf-8")),
        "motion_sha256":hashlib.sha256(motion_text.encode("utf-8")).hexdigest(),
        "spa_bytes":SPA.stat().st_size,
        "spa_sha256":hashlib.sha256(SPA.read_bytes()).hexdigest()
    },indent=2))

if __name__=="__main__":
    main()
