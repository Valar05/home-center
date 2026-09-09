#!/usr/bin/env python3
from __future__ import annotations
import base64, json, math, subprocess, hashlib, html
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
MOTION = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
W, H = 640, 360
FPS = int(MOTION["timing"]["fps"])
FRAMES_DIR = HERE / "_frames"
MP4 = HERE / "_authoritative.mp4"
ASCII = HERE / "contact-sheet.txt"
SPA = HERE / "riser-catch-momentum-redirect.motion.html"

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
    if any(word in s for word in ("PLANTED","DOMINANT","SUPPORT","CATCH","SETTLE")):
        return "plant"
    return "free"

def draw_terrain(d):
    terr = MOTION["rig"]["terrain"]
    pts = []
    x = terr[0]["x0"]; y = terr[0]["y"]
    pts.append((x,y))
    for i,t in enumerate(terr):
        if i == 0:
            pts.append((t["x1"], t["y"]))
        else:
            px = t["x0"]; py_prev = terr[i-1]["y"]
            pts.append((px, py_prev)); pts.append((px, t["y"])); pts.append((t["x1"], t["y"]))
    d.line(pts, fill=(108,112,120), width=4)
    for t in terr:
        d.line((t["x0"],t["y"]+4,t["x1"],t["y"]+4), fill=(55,58,64), width=1)

def draw_frame(k, outpath):
    im = Image.new("RGB",(W,H),(15,17,20))
    d = ImageDraw.Draw(im)
    draw_terrain(d)
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
    d.text((16,16), k["key_id"], fill=(110,115,124))
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
    gx=round((x-20)/(600)*63)
    gy=round((y-90)/(230)*23)
    return int(gx),int(gy)

def ascii_pose(k):
    grid=[[" "]*64 for _ in range(24)]
    terr=MOTION["rig"]["terrain"]
    for t in terr:
        x0,y0=to_grid((t["x0"],t["y"])); x1,y1=to_grid((t["x1"],t["y"]))
        grid_line(grid,x0,y0,x1,y1,"#")
    for i in range(1,len(terr)):
        x=terr[i]["x0"]; ya=terr[i-1]["y"]; yb=terr[i]["y"]
        a=to_grid((x,ya)); b=to_grid((x,yb)); grid_line(grid,*a,*b,"#")
    p=body_points(k)
    for a,b,ch in [
        ("root","chest","|"),("left_sh","left_elbow","/"),("left_elbow","left_hand","/"),
        ("right_sh","right_elbow","\\"),("right_elbow","right_hand","\\"),
        ("root","left_knee","/"),("left_knee","left_foot","/"),
        ("root","right_knee","\\"),("right_knee","right_foot","\\")]:
        aa=to_grid(p[a]); bb=to_grid(p[b]); grid_line(grid,*aa,*bb,ch)
    for nm,ch in [("head","O"),("chest","T"),("root","@"),("left_foot","_"),("right_foot","_"),
                  ("left_hand","o"),("right_hand","o")]:
        x,y=to_grid(p[nm])
        if 0<=y<24 and 0<=x<64: grid[y][x]=ch
    for side in ("left","right"):
        x,y=to_grid(p[f"{side}_foot"]); y=min(23,y+1)
        kind=support_kind(k,side)
        if kind=="plant": grid[y][x]="*"
        elif kind=="probe": grid[y][x]="+"
    return "\n".join("".join(r).rstrip() for r in grid)

def make_contact_sheet():
    out=[]
    out.append("ASCII KINESIS V2 · LOCOMOTION 018 · RISER CATCH MOMENTUM REDIRECT")
    out.append("legend: @ root/COM · * support owner · + probe · # terrain · O head")
    out.append("source evidence: Bullwinkle / NES / asset 81106 · timing authority UNKNOWN · authored timing INFERRED / STREET_FIGHTER-CAPCOM")
    out.append("")
    for k in MOTION["keys"]:
        out.append(f'{k["key_id"]} {k["name"]} · {k["timing_class"]}/{k["hold_frames"]}f · INFERRED · support={k["support"]["owner"]} · phase={k["phase"]}')
        out.append(ascii_pose(k))
        out.append(f'causal: {k["causal_role"]}')
        out.append("")
    return "\n".join(out).rstrip()+"\n"

def make_spa(ascii_text, motion_text, mp4_bytes):
    a=html.escape(ascii_text); j=html.escape(motion_text); b64=base64.b64encode(mp4_bytes).decode("ascii")
    title="ASCII Kinesis V2 · Locomotion 018 · Riser Catch Momentum Redirect"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{color-scheme:dark}}body{{margin:0;background:#0f1114;color:#edf0f3;font-family:system-ui,sans-serif}}
header{{padding:14px 18px;border-bottom:1px solid #343943}}h1{{font-size:18px;margin:0 0 10px}}
nav{{display:flex;gap:8px}}button{{font:inherit;padding:7px 12px;background:#1a1e24;color:inherit;border:1px solid #4a515d;border-radius:6px}}
button[aria-selected="true"]{{background:#303641}}main{{padding:14px 18px}}section[hidden]{{display:none}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #343943;padding:12px;max-height:78vh}}
video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #343943}}
.meta{{font-family:ui-monospace,monospace;font-size:12px;margin:0 0 10px;color:#b7bec8}}
</style></head><body>
<header><h1>{title}</h1><nav>
<button data-view="ascii" aria-selected="true">ASCII</button>
<button data-view="json" aria-selected="false">JSON</button>
<button data-view="video" aria-selected="false">VIDEO</button>
</nav></header><main>
<section id="ascii"><pre>{a}</pre></section>
<section id="json" hidden><pre>{j}</pre></section>
<section id="video" hidden><p class="meta">authoritative embedded H.264/yuv420p · abstract ASCII rig only</p>
<video controls loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section>
</main><script>
const buttons=[...document.querySelectorAll('button[data-view]')];
for(const b of buttons)b.addEventListener('click',()=>{{for(const q of buttons)q.setAttribute('aria-selected',q===b?'true':'false');for(const s of document.querySelectorAll('main section'))s.hidden=s.id!==b.dataset.view;}});
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
         "-an","-c:v","libx264","-pix_fmt","yuv420p","-preset","veryslow","-crf","28",
         "-movflags","+faststart","-map_metadata","-1","-metadata","creation_time=1970-01-01T00:00:00Z",
         "-threads","1",str(MP4)]
    subprocess.run(cmd,check=True)
    ascii_text=make_contact_sheet()
    ASCII.write_text(ascii_text,encoding="utf-8")
    motion_text=(HERE/"motion.json").read_text(encoding="utf-8")
    mp4=MP4.read_bytes()
    SPA.write_text(make_spa(ascii_text,motion_text,mp4),encoding="utf-8")
    print(json.dumps({"frames":idx,"fps":FPS,"mp4_bytes":len(mp4),"mp4_sha256":hashlib.sha256(mp4).hexdigest(),
                      "ascii_sha256":hashlib.sha256(ascii_text.encode()).hexdigest(),
                      "motion_sha256":hashlib.sha256(motion_text.encode()).hexdigest(),
                      "spa_sha256":hashlib.sha256(SPA.read_bytes()).hexdigest()},sort_keys=True))
if __name__=="__main__": main()
