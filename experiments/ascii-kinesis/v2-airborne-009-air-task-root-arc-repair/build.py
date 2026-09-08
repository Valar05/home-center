#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION_PATH = HERE / "motion.json"
SPA_PATH = HERE / "air-task-root-arc-repair.motion.html"
GROUND_Y = 24
W_CH, H_CH = 72, 28
CLASS_FRAMES = {"ONES": 1, "TWOS": 2, "FOURS": 4}
CONNECTIONS = [
    ("head","neck"), ("shoulder_l","shoulder_r"), ("neck","pelvis"),
    ("shoulder_l","elbow_l"), ("elbow_l","hand_l"),
    ("shoulder_r","elbow_r"), ("elbow_r","hand_r"),
    ("pelvis","knee_l"), ("knee_l","foot_l"),
    ("pelvis","knee_r"), ("knee_r","foot_r"),
]

def linechar(a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    if abs(dx)>abs(dy)*1.5: return "-"
    if abs(dy)>abs(dx)*1.5: return "|"
    return "\\" if dx*dy>0 else "/"

def bresenham(a,b):
    x0,y0=a; x1,y1=b; pts=[]
    dx=abs(x1-x0); dy=-abs(y1-y0)
    sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1
    err=dx+dy; x,y=x0,y0
    while True:
        pts.append((x,y))
        if x==x1 and y==y1: return pts
        e2=2*err
        if e2>=dy: err+=dy; x+=sx
        if e2<=dx: err+=dx; y+=sy

def grid_text(pose,support,label,timing,phase):
    g=[[" "]*W_CH for _ in range(H_CH)]
    for x in range(W_CH): g[GROUND_Y][x]="_"
    for a,b in CONNECTIONS:
        ch=linechar(pose[a],pose[b])
        for x,y in bresenham(pose[a],pose[b])[1:-1]:
            if 0<=x<W_CH and 0<=y<H_CH: g[y][x]=ch
    supported=set()
    if support=="GROUND_BOTH": supported={"foot_l","foot_r"}
    elif support=="GROUND_REAR": supported={"foot_l"}
    elif support=="GROUND_FRONT": supported={"foot_r"}
    glyph={k:"o" for k in pose}
    glyph.update({"head":"O","pelvis":"@","hand_l":"*","hand_r":"*","foot_l":"+","foot_r":"+"})
    for j,(x,y) in pose.items():
        if 0<=x<W_CH and 0<=y<H_CH: g[y][x]="=" if j in supported else glyph[j]
    hx,hy=pose["head"]
    if hx+2<W_CH and 0<=hy<H_CH: g[hy][hx+2]=">"
    px,py=pose["pelvis"]
    v={"LOAD":"v","LOAD_RELEASE":"^","LAUNCH":"^","RISE":"^","RISE_TO_APEX":"^","APEX":"~",
       "DESCENT_BEGIN":"v","DESCENT":"v","PRECONTACT":"v","CONTACT":"!","COMPRESSION":"v",
       "REBOUND":"^","SETTLE":".","STABLE":".","READY":"."}.get(phase,".")
    if px>=2: g[py][px-2]=v
    top=f"{label}  {timing}  {phase}"
    for i,ch in enumerate(top[:W_CH]): g[0][i]=ch
    return "\n".join("".join(r).rstrip() for r in g)

def local_panel(item,w=24,h=16):
    p=item["pose_rig"]; px,py=p["pelvis"]
    mp={j:[x-px+w//2,y-py+8] for j,(x,y) in p.items()}
    g=[[" "]*w for _ in range(h)]
    gy=GROUND_Y-py+8
    if 0<=gy<h:
        for x in range(w): g[gy][x]="_"
    for a,b in CONNECTIONS:
        ch=linechar(mp[a],mp[b])
        for x,y in bresenham(mp[a],mp[b])[1:-1]:
            if 0<=x<w and 0<=y<h: g[y][x]=ch
    supported=set()
    if item["support_contact"]=="GROUND_BOTH": supported={"foot_l","foot_r"}
    elif item["support_contact"]=="GROUND_REAR": supported={"foot_l"}
    elif item["support_contact"]=="GROUND_FRONT": supported={"foot_r"}
    glyph={k:"o" for k in mp}
    glyph.update({"head":"O","pelvis":"@","hand_l":"*","hand_r":"*","foot_l":"+","foot_r":"+"})
    for j,(x,y) in mp.items():
        if 0<=x<w and 0<=y<h: g[y][x]="=" if j in supported else glyph[j]
    hx,hy=mp["head"]
    if 0<=hy<h and hx+2<w: g[hy][hx+2]=">"
    return ["".join(r) for r in g]

def contact_sheet(motion):
    panels=[]
    for item in motion["keys"]:
        hdr1=f'{item["key_id"]} {item["timing_class"]} {item["key_kind"].replace("authored_","")}'
        hdr2=f'{item["name"]} root={tuple(item["pose_rig"]["pelvis"])}'
        hdr3=f'{item["support_contact"]} / {item["vertical_phase"]}'
        panels.append([hdr1[:24].ljust(24),hdr2[:24].ljust(24),hdr3[:24].ljust(24)]+local_panel(item))
    lines=[
        "ASCII KINESIS V2 AIRBORNE 009 -- AIR TASK RIDES ROOT ARC / EMBODIED REPAIR",
        "revises: experiments/ascii-kinesis/v2-airborne-001-air-task-rides-root-arc/",
        "negative_fixture: experiments/ascii-kinesis/v2-airborne-001-air-task-rides-root-arc/",
        "timing: all authored keys INFERRED / STREET_FIGHTER-CAPCOM; 1s/2s/4s = ONES/TWOS/FOURS",
        "",
    ]
    for row in range((len(panels)+2)//3):
        group=panels[row*3:(row+1)*3]
        for i in range(max(map(len,group))):
            lines.append("  ".join((p[i] if i<len(p) else " "*24) for p in group).rstrip())
        lines.append("")
    return "\n".join(lines).rstrip()+"\n"

def smoothstep(t): return t*t*(3-2*t)

def interp_pose(a,b,u):
    delays={"pelvis":0.0,"neck":0.0,"head":0.05,"shoulder_l":0.08,"shoulder_r":0.04,
            "elbow_l":0.13,"elbow_r":0.09,"hand_l":0.20,"hand_r":0.16,
            "knee_l":0.10,"knee_r":0.06,"foot_l":0.16,"foot_r":0.12}
    out={}
    for j in a:
        d=delays.get(j,0.0)
        q=max(0.0,min(1.0,(u-d)/(1-d))); q=smoothstep(q)
        out[j]=[round(a[j][0]+(b[j][0]-a[j][0])*q), round(a[j][1]+(b[j][1]-a[j][1])*q)]
    return out

def semantic_frames(motion):
    scale=int(motion["compile"]["preview_time_scale"]); keys=motion["keys"]; out=[]
    for i,k in enumerate(keys):
        for _ in range(CLASS_FRAMES[k["timing_class"]]*scale):
            out.append((k["pose_rig"],k["support_contact"],k["contact_state"],k["key_id"],k["timing_class"],k["vertical_phase"]))
        if i+1<len(keys):
            n=keys[i+1]
            same=(k["support_contact"]==n["support_contact"] and k["contact_state"]==n["contact_state"] and k["force_owner"]==n["force_owner"])
            if same:
                out.append((interp_pose(k["pose_rig"],n["pose_rig"],0.58),k["support_contact"],k["contact_state"],f'{k["key_id"]}->{n["key_id"]}',"CONNECT","bridge"))
    return out

def resolve_font():
    candidates=[
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/dejavu/DejaVuSansMono.ttf"),
    ]
    for p in candidates:
        if p.is_file(): return str(p)
    raise SystemExit("DejaVuSansMono.ttf not available; canonical builder fails closed")

def render_mp4(motion,tmp):
    frames=semantic_frames(motion)
    font=ImageFont.truetype(resolve_font(),18)
    frame_dir=tmp/"frames"; frame_dir.mkdir()
    for idx,(pose,support,contact,kid,timing,phase) in enumerate(frames):
        text=grid_text(pose,support,kid,timing,phase)
        im=Image.new("RGB",(960,540),"black"); d=ImageDraw.Draw(im)
        d.multiline_text((18,6),text,font=font,fill="white",spacing=0)
        im.save(frame_dir/f"f{idx:04d}.png")
    mp4=tmp/"motion.mp4"
    subprocess.run(["ffmpeg","-y","-hide_banner","-loglevel","error","-framerate",str(motion["compile"]["fps"]),
                    "-i",str(frame_dir/"f%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",str(mp4)],check=True)
    return mp4.read_bytes()

def make_html(ascii_text,motion,video_bytes):
    motion_text=json.dumps(motion,indent=2,ensure_ascii=False)
    video64=base64.b64encode(video_bytes).decode("ascii")
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(motion["title"])}</title>
<style>
:root{{color-scheme:dark}}body{{margin:0;background:#090909;color:#eee;font-family:system-ui,sans-serif}}
header,nav{{padding:12px 16px}}nav{{display:flex;gap:8px;position:sticky;top:0;background:#090909}}
button{{padding:10px 16px}}section{{display:none;padding:0 16px 24px}}section.active{{display:block}}
pre{{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}
video{{width:min(100%,960px);height:auto;background:#000}}.note{{max-width:72ch}}
</style></head><body>
<header><h1>{html.escape(motion["title"])}</h1><div class="note">Successor repair of the preserved negative fixture. Source art is not embedded.</div></header>
<nav>
<button data-view="ascii">ASCII</button>
<button data-view="json">JSON</button>
<button data-view="video">VIDEO</button>
</nav>
<section id="ascii" class="active"><pre>{html.escape(ascii_text)}</pre></section>
<section id="json"><pre>{html.escape(motion_text)}</pre></section>
<section id="video"><video controls loop muted playsinline preload="metadata" src="data:video/mp4;base64,{video64}"></video></section>
<script>
const buttons=[...document.querySelectorAll("button[data-view]")];
const sections=[...document.querySelectorAll("section")];
function show(id){{sections.forEach(s=>s.classList.toggle("active",s.id===id));}}
buttons.forEach(b=>b.addEventListener("click",()=>show(b.dataset.view)));
</script></body></html>"""

def main():
    motion=json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    ascii_text=contact_sheet(motion)
    actual_ascii=hashlib.sha256(ascii_text.encode()).hexdigest()
    if actual_ascii!=motion["ascii_sheet_sha256"]:
        raise SystemExit(f"ASCII hash mismatch: {actual_ascii}")
    with tempfile.TemporaryDirectory() as td:
        media=render_mp4(motion,Path(td))
    actual_media=hashlib.sha256(media).hexdigest()
    if actual_media!=motion["compile"]["media_sha256"]:
        raise SystemExit(f"media hash mismatch: {actual_media}")
    SPA_PATH.write_text(make_html(ascii_text,motion,media),encoding="utf-8")
    print(json.dumps({"spa":SPA_PATH.name,"ascii_sha256":actual_ascii,"media_sha256":actual_media,
                      "media_bytes":len(media),"video_frames_total":motion["compile"]["video_frames_total"]},sort_keys=True))
if __name__=="__main__": main()
