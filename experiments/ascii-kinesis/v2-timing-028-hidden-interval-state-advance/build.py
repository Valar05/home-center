#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=json.loads((ROOT/"motion.json").read_text(encoding="utf-8"))
CONTACT=(ROOT/"contact-sheet.txt").read_text(encoding="utf-8")
OUT_MP4=ROOT/".hidden-interval-state-advance.mp4"
OUT_HTML=ROOT/"hidden-interval-state-advance.motion.html"
FONT=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
if not FONT.is_file():
    raise SystemExit("Motion Dungeon deterministic font missing: DejaVuSansMono.ttf")

SEP="------------------------------------------------------------------------------"
POSE={}
for part in CONTACT.split(SEP):
    block=part.strip("\n")
    if not block.strip():
        continue
    kid=block.splitlines()[0].split()[0]
    POSE[kid]=block.rstrip()

for key in MOTION["keys"]:
    kid=key["key_id"]
    rig=POSE[kid]
    expect=key["pose_rig"]["ascii_sha256"]
    got=hashlib.sha256(rig.encode("utf-8")).hexdigest()
    if got!=expect:
        raise SystemExit(f"{kid} ASCII key integrity mismatch: {got} != {expect}")

frames=Path(tempfile.mkdtemp(prefix="timing028-frames-"))
try:
    font=ImageFont.truetype(str(FONT),12)
    footer=ImageFont.truetype(str(FONT),9)
    n=0
    for key in MOTION["keys"]:
        rig=POSE[key["key_id"]]
        for _ in range(int(key["exposure_ticks"])):
            im=Image.new("RGB",(720,320),"white")
            d=ImageDraw.Draw(im)
            d.multiline_text((10,5),rig,font=font,fill="black",spacing=0)
            d.line((10,289,710,289),fill="black",width=1)
            d.text((10,296),f"Timing028 | {key['key_id']} {key['causal_role']} | {key['timing_class']} | BODY CLOCK CONTINUES | task phase {key['task_phase_unwrapped']}",font=footer,fill="black")
            im.save(frames/f"frame_{n:04d}.png")
            n+=1
    if n!=int(MOTION["compile"]["frame_count"]):
        raise SystemExit(f"frame count mismatch: {n}")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(MOTION["compile"]["fps"]),"-i",str(frames/"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","30","-map_metadata","-1",str(OUT_MP4)],check=True)
finally:
    shutil.rmtree(frames,ignore_errors=True)

raw=OUT_MP4.read_bytes()
sha=hashlib.sha256(raw).hexdigest()
decl=MOTION["compile"]["media"]
if sha!=decl["sha256"] or len(raw)!=int(decl["bytes"]):
    raise SystemExit(f"media identity mismatch: {sha}/{len(raw)} expected {decl['sha256']}/{decl['bytes']}")

motion_text=(ROOT/"motion.json").read_text(encoding="utf-8")
v64=base64.b64encode(raw).decode("ascii")
esc=lambda s: html.escape(s,quote=False)
page='<!doctype html><meta charset="utf-8"><title>Timing028 — Hidden Interval State Advance</title>' \
     '<style>body{font:14px system-ui;margin:16px}nav{display:flex;gap:8px}section{display:none}' \
     'section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;' \
     'font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08}video{max-width:100%;height:auto}</style>' \
     '<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>' \
     '<section id="ascii" class="active"><pre>'+esc(CONTACT)+'</pre></section>' \
     '<section id="json"><pre>'+esc(motion_text)+'</pre></section>' \
     '<section id="video"><video controls loop muted playsinline src="data:video/mp4;base64,'+v64+'"></video></section>' \
     '<script>const s=[...document.querySelectorAll("section")];document.querySelectorAll("button[data-view]").forEach(b=>b.onclick=()=>s.forEach(x=>x.classList.toggle("active",x.id===b.dataset.view)));</script>'
OUT_HTML.write_text(page,encoding="utf-8")
print(json.dumps({"ok":True,"frames":n,"media_sha256":sha,"media_bytes":len(raw),"spa":OUT_HTML.name},sort_keys=True))
