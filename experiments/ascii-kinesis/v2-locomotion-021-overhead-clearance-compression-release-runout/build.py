#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, json, math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
MOTION = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
W,H = map(int,MOTION["rig"]["viewport"])
FPS = int(MOTION["timing"]["fps"])
FRAMES = HERE / "_frames"
MP4 = HERE / "_authoritative.mp4"
ASCII = HERE / "contact-sheet.txt"
SPA = HERE / "overhead-clearance-compression-release-runout.motion.html"

def body_points(k):
    rx,ry=map(float,k["root"])
    lean=math.radians(float(k["torso_lean_deg"]))
    comp=float(k.get("compression",0))
    torso_len=40.0-comp*0.42
    chest=(rx+math.sin(lean)*torso_len, ry-math.cos(lean)*torso_len)
    neck=(chest[0]+math.sin(lean)*7.0, chest[1]-math.cos(lean)*7.0)
    head=(neck[0]+math.sin(lean)*10.0, neck[1]-math.cos(lean)*10.0+float(k.get("head_lag_y",0)))
    span=12.0
    ls=(chest[0]-span,chest[1]); rs=(chest[0]+span,chest[1])
    lh=(chest[0]+float(k["left_hand_offset"][0]),chest[1]+float(k["left_hand_offset"][1]))
    rh=(chest[0]+float(k["right_hand_offset"][0]),chest[1]+float(k["right_hand_offset"][1]))
    lf=tuple(map(float,k["left_foot"])); rf=tuple(map(float,k["right_foot"]))
    lk=((rx+lf[0])/2.0 + (8 if lf[0]>=rx else -8), (ry+lf[1])/2.0-4-comp*0.08)
    rk=((rx+rf[0])/2.0 + (8 if rf[0]>=rx else -8), (ry+rf[1])/2.0-4-comp*0.08)
    le=((ls[0]+lh[0])/2.0-4,(ls[1]+lh[1])/2.0+4)
    re=((rs[0]+rh[0])/2.0+4,(rs[1]+rh[1])/2.0+4)
    return {"root":(rx,ry),"chest":chest,"head":head,"left_sh":ls,"right_sh":rs,
            "left_hand":lh,"right_hand":rh,"left_elbow":le,"right_elbow":re,
            "left_foot":lf,"right_foot":rf,"left_knee":lk,"right_knee":rk}

def support_kind(k,side):
    s=str(k["support"].get(side,"")).upper()
    if "PROBE" in s: return "probe"
    if "PLANTED" in s or "LIGHT_FIXED" in s or s=="LIGHT": return "plant" if "PLANTED" in s else "light"
    return "free"

def draw_env(d):
    floor=int(MOTION["rig"]["fixed_floor_reference_y"])
    z=MOTION["rig"]["clearance_zone"]
    d.line((0,floor,W,floor),fill=(78,84,92),width=3)
    x0,x1,u=int(z["x0"]),int(z["x1"]),int(z["underside_y"])
    d.rectangle((x0,0,x1,u),fill=(38,42,48),outline=(112,120,132),width=2)
    for x in range(x0+7,x1,18):
        d.line((x,u-7,x+7,u),fill=(84,91,101),width=2)

def draw_frame(k,idx,path):
    im=Image.new("RGB",(W,H),(13,15,18)); d=ImageDraw.Draw(im); draw_env(d); p=body_points(k)
    body=(235,239,244); secondary=(184,193,203); rootc=(247,207,92)
    d.line([p["root"],p["left_knee"],p["left_foot"]],fill=body,width=5)
    d.line([p["root"],p["right_knee"],p["right_foot"]],fill=body,width=5)
    d.line([p["root"],p["chest"]],fill=body,width=7)
    d.line([p["left_sh"],p["left_elbow"],p["left_hand"]],fill=secondary,width=4)
    d.line([p["right_sh"],p["right_elbow"],p["right_hand"]],fill=secondary,width=4)
    hx,hy=p["head"]; d.ellipse((hx-9,hy-9,hx+9,hy+9),outline=body,width=4)
    rx,ry=p["root"]; d.polygon([(rx,ry-6),(rx+6,ry),(rx,ry+6),(rx-6,ry)],outline=rootc)
    for side in ("left","right"):
        fx,fy=p[f"{side}_foot"]; d.line((fx-8,fy,fx+8,fy),fill=body,width=4)
        kind=support_kind(k,side)
        if kind=="plant": d.ellipse((fx-5,fy+4,fx+5,fy+13),fill=(111,199,142))
        elif kind=="probe": d.ellipse((fx-5,fy+4,fx+5,fy+13),outline=(225,169,88),width=2)
    d.text((12,12),f'{k["key_id"]}  {k["name"]}',fill=(104,112,123))
    im.save(path,"PNG",optimize=False)

def grid_line(g,x0,y0,x1,y1,ch):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        if 0<=y0<len(g) and 0<=x0<len(g[0]): g[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def to_grid(pt):
    x,y=pt; return int(round((x-5)/430*71)), int(round((y-72)/188*23))

def ascii_pose(k):
    g=[[" "]*72 for _ in range(24)]
    floor=MOTION["rig"]["fixed_floor_reference_y"]; gy=to_grid((0,floor))[1]
    if 0<=gy<24:
        for x in range(72): g[gy][x]="." if x%4 else ":"
    z=MOTION["rig"]["clearance_zone"]
    a=to_grid((z["x0"],z["underside_y"])); b=to_grid((z["x1"],z["underside_y"]))
    grid_line(g,*a,*b,"#")
    p=body_points(k)
    for an,bn,ch in [("root","chest","|"),("left_sh","left_elbow","/"),("left_elbow","left_hand","/"),("right_sh","right_elbow","\\"),("right_elbow","right_hand","\\"),("root","left_knee","/"),("left_knee","left_foot","/"),("root","right_knee","\\"),("right_knee","right_foot","\\")]:
        grid_line(g,*to_grid(p[an]),*to_grid(p[bn]),ch)
    for nm,ch in [("head","O"),("chest","T"),("root","@"),("left_foot","_"),("right_foot","_"),("left_hand","o"),("right_hand","o")]:
        x,y=to_grid(p[nm]);
        if 0<=y<24 and 0<=x<72:g[y][x]=ch
    for side in ("left","right"):
        x,y=to_grid(p[f"{side}_foot"]); y=min(23,y+1); kind=support_kind(k,side)
        if 0<=x<72:
            if kind=="plant":g[y][x]="*"
            elif kind=="probe":g[y][x]="+"
    return "\n".join("".join(r).rstrip() for r in g)

def make_contact_sheet():
    out=[
      "ASCII KINESIS V2 · LOCOMOTION 021 · OVERHEAD CLEARANCE COMPRESSION / RELEASE RUNOUT",
      "legend: @ root/COM · * support owner · + probe · # overhead clearance underside · . fixed ground · O head",
      "source evidence: Samus Aran (Power Suit) / Metroid: Zero Mission / GBA / TSR asset 106418 / Home Center artifact 1H3ceHukijHxTRnsCuxsG1-ylAd-MQ5kmNM5z4Kon77U",
      "OBSERVED: commissioned static whole-sheet evidence separates repeated body organizations from detached component/configuration banks; it supplies pose-family evidence, not this choreography.",
      "UNKNOWN: source chronology/exposure/gameplay cadence; source page Animations (0). Authored cadence below is INFERRED / STREET_FIGHTER-CAPCOM.",
      "rights firewall: generic abstract rig only; no source pixels, palette, costume, contours, layout, tracing, choreography, audio, redistribution, or close imitation.",
      "thesis: compress root/COM before a low overhead constraint while fixed-ground travel continues; release only after exit, then pay surviving forward debt with one long free catch and shorter displaced corrections.",""]
    for k in MOTION["keys"]:
        out.append(f'{k["key_id"]} {k["name"]} · {k["timing_class"]}/{k["hold_frames"]}f · {k["timing_provenance"]} · support={k["support"]["owner"]} · phase={k["phase"]} · rootΔ={k["root_spacing_px"]}px')
        out.append(ascii_pose(k)); out.append(f'causal: {k["causal_role"]}'); out.append("")
    return "\n".join(out).rstrip()+"\n"

def make_spa(ascii_text,motion_text,mp4_bytes):
    ab64=base64.b64encode(gzip.compress(ascii_text.encode(),mtime=0)).decode(); jb64=base64.b64encode(gzip.compress(motion_text.encode(),mtime=0)).decode(); vb64=base64.b64encode(mp4_bytes).decode()
    title="ASCII Kinesis V2 · Locomotion 021 · Overhead Clearance Compression / Release Runout"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>:root{{color-scheme:dark}}body{{margin:0;background:#0f1114;color:#edf0f3;font-family:system-ui,sans-serif}}header{{padding:14px 18px;border-bottom:1px solid #343943}}nav{{display:flex;gap:8px}}button{{font:inherit;padding:7px 12px;background:#1a1e24;color:inherit;border:1px solid #4a515d;border-radius:6px}}button[aria-selected="true"]{{background:#303641}}main{{padding:14px 18px}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #343943;padding:12px;max-height:78vh}}video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #343943}}</style></head><body><header><h1>{title}</h1><nav><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section id="ascii"><pre id="ascii-pre">loading exact persisted ASCII…</pre></section><section id="json" hidden><pre id="json-pre">loading exact persisted JSON…</pre></section><section id="video" hidden><video controls loop muted playsinline src="data:video/mp4;base64,{vb64}"></video></section></main><script>const A="{ab64}",J="{jb64}";async function gunzip64(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}}Promise.all([gunzip64(A),gunzip64(J)]).then(([a,j])=>{{document.getElementById("ascii-pre").textContent=a;document.getElementById("json-pre").textContent=j;}});const buttons=[...document.querySelectorAll('button[data-view]')];for(const b of buttons)b.addEventListener('click',()=>{{for(const q of buttons)q.setAttribute('aria-selected',q===b?'true':'false');for(const x of document.querySelectorAll('main section'))x.hidden=x.id!==b.dataset.view;}});</script></body></html>'''

def main():
    FRAMES.mkdir(exist_ok=True)
    for p in FRAMES.glob("*.png"):p.unlink()
    idx=0
    for k in MOTION["keys"]:
        for _ in range(int(k["hold_frames"])):
            draw_frame(k,idx,FRAMES/f"frame-{idx:04d}.png"); idx+=1
    assert idx==MOTION["timing"]["total_frames"]
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(FPS),"-i",str(FRAMES/"frame-%04d.png"),"-vf","scale=480:270:flags=neighbor","-c:v","libx264","-preset","veryslow","-crf","28","-pix_fmt","yuv420p","-movflags","+faststart","-metadata","creation_time=1970-01-01T00:00:00Z",str(MP4)]
    subprocess.run(cmd,check=True)
    ascii_text=make_contact_sheet(); ASCII.write_text(ascii_text,encoding="utf-8")
    motion_text=(HERE/"motion.json").read_text(encoding="utf-8")
    SPA.write_text(make_spa(ascii_text,motion_text,MP4.read_bytes()),encoding="utf-8")

if __name__=="__main__":main()
