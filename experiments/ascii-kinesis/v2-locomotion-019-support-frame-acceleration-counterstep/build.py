#!/usr/bin/env python3
from __future__ import annotations
import base64, json, math, subprocess, hashlib, gzip
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
MOTION = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
W, H = 640, 360
FPS = int(MOTION["timing"]["fps"])
FRAMES_DIR = HERE / "_frames"
MP4 = HERE / "_authoritative.mp4"
ASCII = HERE / "contact-sheet.txt"
SPA = HERE / "support-frame-acceleration-counterstep.motion.html"

def body_points(k):
    rx, ry = k["root"]
    a = math.radians(float(k["torso_lean_deg"]))
    chest = (rx + math.sin(a)*38, ry - math.cos(a)*38)
    neck = (chest[0] + math.sin(a)*8, chest[1] - math.cos(a)*8)
    head = (neck[0] + math.sin(a)*12 + float(k.get("head_lag_x",0)), neck[1] - math.cos(a)*12)
    left_sh = (chest[0]-11, chest[1]+2)
    right_sh = (chest[0]+11, chest[1]+2)
    lh = (chest[0]+k["left_hand_offset"][0], chest[1]+k["left_hand_offset"][1])
    rh = (chest[0]+k["right_hand_offset"][0], chest[1]+k["right_hand_offset"][1])
    lf = tuple(k["left_foot"]); rf = tuple(k["right_foot"])
    lk_mid = ((rx+lf[0])/2, (ry+lf[1])/2)
    rk_mid = ((rx+rf[0])/2, (ry+rf[1])/2)
    lk = (lk_mid[0] + (9 if lf[0] >= rx else -9), lk_mid[1]-4)
    rk = (rk_mid[0] + (9 if rf[0] >= rx else -9), rk_mid[1]-4)
    le = ((left_sh[0]+lh[0])/2-5, (left_sh[1]+lh[1])/2+5)
    re = ((right_sh[0]+rh[0])/2+5, (right_sh[1]+rh[1])/2+5)
    return {"root":(rx,ry),"chest":chest,"head":head,"left_sh":left_sh,"right_sh":right_sh,
            "left_hand":lh,"right_hand":rh,"left_elbow":le,"right_elbow":re,
            "left_knee":lk,"right_knee":rk,"left_foot":lf,"right_foot":rf}

def support_kind(k, side):
    s = str(k["support"].get(side.lower(),"")).upper()
    if "PROBE" in s or "TOUCH" in s:
        return "probe"
    if any(word in s for word in ("PLANTED","DOMINANT","SUPPORT","CATCH")):
        return "plant"
    return "free"

def draw_fixed_reference(d):
    y = int(MOTION["rig"]["platform"]["fixed_reference_y"])
    d.line((0,y,W,y), fill=(55,58,64), width=2)
    for x in range(18,W,32):
        d.line((x,y-5,x,y+5), fill=(88,92,100), width=2)

def draw_platform(d,k):
    x = int(k["platform_x"])
    p = MOTION["rig"]["platform"]
    y = int(p["top_y"]); w = int(p["width"]); t = int(p["thickness"])
    d.rectangle((x,y,x+w,y+t), fill=(94,103,116), outline=(174,183,194), width=2)
    for xx in range(x+18,x+w-10,34):
        d.line((xx,y+t+1,xx-8,y+t+9), fill=(72,77,86), width=2)

def draw_frame(k, outpath):
    im = Image.new("RGB",(W,H),(15,17,20))
    d = ImageDraw.Draw(im)
    draw_fixed_reference(d)
    draw_platform(d,k)
    p = body_points(k)
    body=(235,238,241); secondary=(187,194,203); rootc=(250,210,97)
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
            d.ellipse((fx-5,fy+4,fx+5,fy+14), fill=(120,210,150))
        elif kind=="probe":
            d.ellipse((fx-5,fy+4,fx+5,fy+14), outline=(226,169,91), width=2)
    bx=16; by=18; baseline=120; cur=int(k["relative_root_x"])
    d.line((bx,by,bx+120,by), fill=(74,79,88), width=2)
    d.line((bx+baseline//2,by-4,bx+baseline//2,by+4), fill=(115,121,132), width=2)
    d.ellipse((bx+cur//2-3,by-3,bx+cur//2+3,by+3), fill=rootc)
    d.text((16,30), k["key_id"], fill=(110,115,124))
    im.save(outpath, "PNG", optimize=False)

def grid_line(grid, x0,y0,x1,y1,ch):
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
    gx=round((x-10)/(620)*71)
    gy=round((y-82)/(250)*23)
    return int(gx),int(gy)

def ascii_pose(k):
    grid=[[" "]*72 for _ in range(24)]
    gy=to_grid((0,MOTION["rig"]["platform"]["fixed_reference_y"]))[1]
    if 0<=gy<24:
        for x in range(72):
            if x%5==0: grid[gy][x]="."
    p=MOTION["rig"]["platform"]; px=int(k["platform_x"]); py=int(p["top_y"])
    a=to_grid((px,py)); b=to_grid((px+int(p["width"]),py))
    grid_line(grid,*a,*b,"=")
    pnts=body_points(k)
    for a_name,b_name,ch in [
        ("root","chest","|"),("left_sh","left_elbow","/"),("left_elbow","left_hand","/"),
        ("right_sh","right_elbow","\\"),("right_elbow","right_hand","\\"),
        ("root","left_knee","/"),("left_knee","left_foot","/"),
        ("root","right_knee","\\"),("right_knee","right_foot","\\")]:
        aa=to_grid(pnts[a_name]); bb=to_grid(pnts[b_name]); grid_line(grid,*aa,*bb,ch)
    for nm,ch in [("head","O"),("chest","T"),("root","@"),("left_foot","_"),("right_foot","_"),
                  ("left_hand","o"),("right_hand","o")]:
        x,y=to_grid(pnts[nm])
        if 0<=y<24 and 0<=x<72: grid[y][x]=ch
    for side in ("left","right"):
        x,y=to_grid(pnts[f"{side}_foot"]); y=min(23,y+1)
        kind=support_kind(k,side)
        if kind=="plant": grid[y][x]="*"
        elif kind=="probe": grid[y][x]="+"
    return "\n".join("".join(r).rstrip() for r in grid)

def make_contact_sheet():
    out=[]
    out.append("ASCII KINESIS V2 · LOCOMOTION 019 · SUPPORT-FRAME ACCELERATION COUNTERSTEP")
    out.append("legend: @ root/COM · * support owner · + probe · = moving support frame · . fixed world ruler · O head")
    out.append("source evidence: Dr Robuttnik (Elevator) / Sunky's Schoolhouse / PC / asset 191044")
    out.append("source exact identity: 4480×360 RGBA PNG · 32,657 bytes · SHA-256 1304b1cacd772e783e9d000691ba22b39f254d7964b53a1e552e3c881facefca")
    out.append("source timing authority: UNKNOWN / NONE OBSERVED · authored cadence: INFERRED / STREET_FIGHTER-CAPCOM")
    out.append("thesis: acceleration can force corrective locomotion before support topology changes; load shift earns release, counterstep catch, long catch-up, overrun, short correction, displaced restack.")
    out.append("")
    for k in MOTION["keys"]:
        out.append(f'{k["key_id"]} {k["name"]} · {k["timing_class"]}/{k["hold_frames"]}f · {k["timing_provenance"]} · support={k["support"]["owner"]} · phase={k["phase"]} · rootΔ={k["root_spacing_px"]}px · platformΔ={k["platform_spacing_px"]}px · localRootX={k["relative_root_x"]}')
        out.append(ascii_pose(k))
        out.append(f'causal: {k["causal_role"]}')
        out.append("")
    return "\n".join(out).rstrip()+"\n"

def make_spa(ascii_text, motion_text, mp4_bytes):
    ab64=base64.b64encode(gzip.compress(ascii_text.encode("utf-8"),mtime=0)).decode("ascii")
    jb64=base64.b64encode(gzip.compress(motion_text.encode("utf-8"),mtime=0)).decode("ascii")
    vb64=base64.b64encode(mp4_bytes).decode("ascii")
    title="ASCII Kinesis V2 · Locomotion 019 · Support-Frame Acceleration Counterstep"
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
            draw_frame(k, FRAMES_DIR / f"frame-{idx:04d}.png")
            idx += 1
    if idx != int(MOTION["timing"]["total_frames"]):
        raise SystemExit(f"frame count mismatch {idx}")
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(FPS),"-i",str(FRAMES_DIR/"frame-%04d.png"),
         "-vf","scale=480:270:flags=area","-an","-c:v","libx264","-pix_fmt","yuv420p","-preset","veryslow","-crf","34",
         "-movflags","+faststart","-map_metadata","-1","-metadata","creation_time=1970-01-01T00:00:00Z",
         "-threads","1",str(MP4)]
    subprocess.run(cmd,check=True)
    ascii_text=make_contact_sheet()
    ASCII.write_text(ascii_text,encoding="utf-8")
    motion_text=(HERE/"motion.json").read_text(encoding="utf-8")
    mp4=MP4.read_bytes()
    SPA.write_text(make_spa(ascii_text,motion_text,mp4),encoding="utf-8")
    print(json.dumps({"frames":idx,"fps":FPS,"mp4_bytes":len(mp4),"mp4_sha256":hashlib.sha256(mp4).hexdigest(),
                      "ascii_bytes":len(ascii_text.encode("utf-8")),"ascii_sha256":hashlib.sha256(ascii_text.encode()).hexdigest(),
                      "motion_bytes":len(motion_text.encode("utf-8")),"motion_sha256":hashlib.sha256(motion_text.encode()).hexdigest(),
                      "spa_bytes":len(SPA.read_bytes()),"spa_sha256":hashlib.sha256(SPA.read_bytes()).hexdigest()},sort_keys=True))
if __name__=="__main__": main()
