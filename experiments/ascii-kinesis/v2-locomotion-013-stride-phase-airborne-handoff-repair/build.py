#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, subprocess, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
M=json.loads((HERE/"motion.json").read_text(encoding="utf-8"))
W,H=M["rig"]["canvas"]; G=M["rig"]["ground_y"]
BONES=[tuple(x) for x in M["rig"]["bones"]]
HOLD=M["timing_policy"]["hold_frames"]
CONNECT={(c["from"],c["to"]):c for c in M["connectors"]}

def line_points(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; pts=[]
    while True:
        pts.append((x0,y0))
        if (x0,y0)==(x1,y1): return pts
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy

def art(joints,support):
    g=[[" "]*W for _ in range(H)]
    for x in range(W): g[G][x]="="
    for a,b in BONES:
        pa,pb=joints[a],joints[b]
        for x,y in line_points(pa,pb)[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ":
                dx=pb[0]-pa[0]; dy=pb[1]-pa[1]
                g[y][x]="-" if dy==0 else ("|" if dx==0 else ("\\" if dx*dy>0 else "/"))
    for name,(x,y) in joints.items():
        if 0<=x<W and 0<=y<H:
            g[y][x]="O" if name=="head" else ("+" if name=="chest" else ("@" if name=="pelvis" else ("o" if ("elbow" in name or "knee" in name) else "*")))
    parts=set(support.split("+"))
    for state,node in (("LEFT_SUPPORT","l_foot"),("RIGHT_SUPPORT","r_foot")):
        if state in parts:
            x,y=joints[node]; g[y][x]="!"
    for state,node in (("LEFT_PROBE","l_foot"),("RIGHT_PROBE","r_foot")):
        if state in parts:
            x,y=joints[node]; g[y][x]="?"
    return "\n".join("".join(r).rstrip() for r in g)

def smoothstep(t): return t*t*(3-2*t)
def bridge(a,b,t,bend):
    s=smoothstep(t); out={}
    for n,pa in a.items():
        pb=b[n]; x=pa[0]+(pb[0]-pa[0])*s; y=pa[1]+(pb[1]-pa[1])*s
        amp=4*s*(1-s)*bend
        if n=="pelvis": y+=amp*.25
        elif n in ("head","chest"): y+=amp*.15
        elif n in ("l_hand","r_hand"): y+=amp*(.45 if n=="l_hand" else -.35)
        elif n in ("l_foot","r_foot"): y+=amp*(-.25 if n=="l_foot" else .25)
        out[n]=[round(x),round(y)]
    return out

keys=M["keys"]; frames=[]
for i,k in enumerate(keys):
    frames += [(k["joints"],k["support_contact"],k["key_id"],k["name"])]*int(HOLD[k["timing_class"]])
    if i<len(keys)-1:
        n=keys[i+1]; c=CONNECT.get((k["key_id"],n["key_id"]))
        if c:
            if k["support_contact"] != n["support_contact"]:
                raise SystemExit("connector attempted semantic support transition")
            for q in range(1,int(c["frames"])+1):
                frames.append((bridge(k["joints"],n["joints"],q/(int(c["frames"])+1),float(c["bend"])),k["support_contact"],k["key_id"]+"->"+n["key_id"],"AUTHORED_BRIDGE"))
frames += [(keys[-1]["joints"],keys[-1]["support_contact"],keys[-1]["key_id"],keys[-1]["name"])]*int(M["motion_dungeon"]["compile"]["endpoint_hold_frames"])

font_path="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
font=ImageFont.truetype(font_path,10); small=ImageFont.truetype(font_path,8)
tmp=HERE/".motion-dungeon-tmp"; shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir()
for idx,(j,s,kid,name) in enumerate(frames):
    im=Image.new("RGB",(960,520),(12,12,13)); d=ImageDraw.Draw(im)
    d.text((14,10),"ASCII KINESIS · LOCOMOTION 013 · STRIDE-PHASE AIRBORNE HANDOFF REPAIR",font=small,fill=(190,190,190))
    d.text((14,24),f"{kid}  {name}  SUPPORT={s}",font=small,fill=(238,238,235))
    d.multiline_text((14,44),art(j,s),font=font,fill=(247,247,241),spacing=0)
    d.text((14,486),"! trusted support   ? probe   @ pelvis/root   + chest   = ground",font=small,fill=(160,160,160))
    d.text((850,486),f"{idx+1:03d}/{len(frames):03d}",font=small,fill=(140,140,140))
    im.save(tmp/f"frame_{idx:04d}.png",compress_level=9)

mp4=HERE/"stride-phase-airborne-handoff-repair.mp4"
subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(tmp/"frame_%04d.png"),"-c:v","libx264","-preset","veryslow","-crf","20","-pix_fmt","yuv420p","-movflags","+faststart","-metadata","comment=ASCII Kinesis abstract rig only",str(mp4)],check=True)
subprocess.run(["ffmpeg","-v","error","-i",str(mp4),"-f","null","-"],check=True)
blob=mp4.read_bytes()
if hashlib.sha256(blob).hexdigest()!=M["motion_dungeon"]["compile"]["media_sha256"]:
    raise SystemExit("media identity mismatch")

sheet=(HERE/"contact-sheet.txt").read_text(encoding="utf-8")
motion=(HERE/"motion.json").read_text(encoding="utf-8").rstrip("\n")
b64=base64.b64encode(blob).decode("ascii")
page=f"""<!doctype html><meta charset="utf-8"><title>{html.escape(M['title'])}</title>
<style>body{{background:#0d0d0f;color:#eee;font-family:ui-monospace,monospace}}pre{{font-variant-ligatures:none;white-space:pre;overflow:auto}}section{{display:none}}section.active{{display:block}}</style>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre>{html.escape(sheet)}</pre></section><section id="json"><pre>{html.escape(motion)}</pre></section>
<section id="video"><video controls loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section>
<script>for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>{{for(const s of document.querySelectorAll('section'))s.classList.remove('active');document.getElementById(b.dataset.view).classList.add('active')}};</script>"""
(HERE/"stride-phase-airborne-handoff-repair.motion.html").write_text(page,encoding="utf-8")
print(json.dumps({"frames":len(frames),"media_sha256":hashlib.sha256(blob).hexdigest(),"media_bytes":len(blob)},sort_keys=True))
