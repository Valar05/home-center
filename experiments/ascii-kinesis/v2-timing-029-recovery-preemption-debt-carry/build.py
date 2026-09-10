#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import base64, hashlib, html, json, re, shutil, subprocess, tempfile

HERE=Path(__file__).resolve().parent
CONTACT=HERE/"contact-sheet.txt"
MOTION=HERE/"motion.json"
VIDEO=HERE/".timing029-authoritative.mp4"
SPA=HERE/"recovery-preemption-debt-carry.motion.html"
W,H=560,260
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

motion=json.loads(MOTION.read_text(encoding="utf-8"))
contact=CONTACT.read_text(encoding="utf-8")
parts=contact.rstrip().split("\n"+"-"*72+"\n")
keys=motion["keys"]
assert len(parts)==len(keys)
font=ImageFont.truetype(FONT,13)
small=ImageFont.truetype(FONT,9)
frames=Path(tempfile.mkdtemp(prefix="timing029-frames-"))
n=0
try:
    for key,block in zip(keys,parts):
        for _ in range(int(key["exposure_ticks"])):
            im=Image.new("RGB",(W,H),"white")
            d=ImageDraw.Draw(im)
            d.multiline_text((8,7),block,fill="black",font=font,spacing=0)
            d.text((8,246),"Timing029 | abstract ASCII rig only | live recovery debt",fill="black",font=small)
            im.save(frames/f"frame_{n:04d}.png")
            n+=1
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(frames/"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","36","-map_metadata","-1",str(VIDEO)],check=True)
finally:
    shutil.rmtree(frames,ignore_errors=True)
raw=VIDEO.read_bytes()
expected=motion["compile"]["media"]
assert n==expected["frames"]
assert len(raw)==expected["bytes"]
assert hashlib.sha256(raw).hexdigest()==expected["sha256"]

b64=base64.b64encode(raw).decode("ascii")
a=html.escape(contact)
j=html.escape(MOTION.read_text(encoding="utf-8"))
page=f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis Timing029 — Recovery Preemption / State-Debt Carry</title>
<style>body{{font-family:system-ui,sans-serif;margin:0;background:#fff;color:#111}}nav{{display:flex;gap:.5rem;padding:.75rem;border-bottom:1px solid #999;position:sticky;top:0;background:#fff}}button{{font:inherit;padding:.45rem .8rem}}section{{display:none;padding:1rem}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0;white-space:pre;overflow:auto;line-height:1.08}}video{{max-width:100%;height:auto;border:1px solid #999}}small{{display:block;margin:.5rem 0}}</style></head>
<body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre>{a}</pre></section><section id="json"><pre>{j}</pre></section>
<section id="video"><small>Authoritative deterministic Motion Dungeon compile from abstract ASCII rig + authored INFERRED timing; no source pixels.</small><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section>
<script>const buttons=[...document.querySelectorAll("[data-view]")];buttons.forEach(b=>b.addEventListener("click",()=>{{document.querySelectorAll("section").forEach(s=>s.classList.remove("active"));document.getElementById(b.dataset.view).classList.add("active");}}));</script></body></html>"""
SPA.write_text(page,encoding="utf-8")
print(json.dumps({"schema":"timing029.build","frames":n,"bytes":len(raw),"sha256":expected["sha256"],"spa":SPA.name},sort_keys=True))
