#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/"motion.json"
CONTACT=HERE/"contact-sheet.txt"
SPA=HERE/"rate-regime-hysteresis.motion.html"
MP4=HERE/"rate-regime-hysteresis.mp4"
FRAMES=HERE/".timing019-frames"

def contact_text(motion):
    out=[]
    for k in motion["keys"]:
        out.append(f"{k['key_id']} {k['causal_role']} REQUEST={k['pace_request']} REGIME={k['rate_regime']} {k['timing_class']}/{k['exposure_ticks']}t PROVENANCE={k['timing_provenance']}\n")
        out.append(k["pose_rig"])
        out.append("-"*76+"\n")
    return "".join(out)

def render_video(motion):
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir()
    font_path=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    if not font_path.exists():
        raise SystemExit("DejaVuSansMono.ttf required for deterministic Motion Dungeon render")
    font=ImageFont.truetype(str(font_path),13)
    footer=ImageFont.truetype(str(font_path),10)
    n=0
    for k in motion["keys"]:
        for _ in range(int(k["exposure_ticks"])):
            im=Image.new("RGB",(720,300),"white")
            d=ImageDraw.Draw(im)
            d.multiline_text((14,8),k["pose_rig"],fill="black",font=font,spacing=0)
            d.text((12,278),f"Timing019 | {k['key_id']} | {k['causal_role']} | request={k['pace_request']} | regime={k['rate_regime']} | {k['timing_class']}",fill="black",font=footer)
            im.save(FRAMES/f"frame_{n:04d}.png")
            n+=1
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(FRAMES/"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","30","-map_metadata","-1",str(MP4)],check=True)
    return MP4.read_bytes()

def spa_text(contact, motion_raw, mp4):
    css="body{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}nav{display:flex;gap:.5rem;padding:.75rem;position:sticky;top:0;background:#111}button{padding:.6rem 1rem}section{display:none;padding:1rem}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto}"
    b64=base64.b64encode(mp4).decode("ascii")
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>Timing019 - Rate Regime Hysteresis</title><style>{css}</style></head>
<body>
<nav>
<button data-view="ascii" onclick="show('ascii')">ASCII</button>
<button data-view="json" onclick="show('json')">JSON</button>
<button data-view="video" onclick="show('video')">VIDEO</button>
</nav>
<section id="ascii" class="active"><pre>{html.escape(contact)}</pre></section>
<section id="json"><pre>{html.escape(motion_raw)}</pre></section>
<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section>
<script>
function show(id){{for(const s of document.querySelectorAll('section'))s.classList.remove('active');document.getElementById(id).classList.add('active');}}
</script>
</body></html>
'''

def main():
    raw=MOTION.read_text(encoding="utf-8")
    motion=json.loads(raw)
    contact=contact_text(motion)
    CONTACT.write_text(contact,encoding="utf-8")
    mp4=render_video(motion)
    expected=motion["compile"]["media"]["sha256"]
    got=hashlib.sha256(mp4).hexdigest()
    if got!=expected:
        raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={expected} got={got}")
    SPA.write_text(spa_text(contact,raw,mp4),encoding="utf-8")
    print(json.dumps({"experiment_id":motion["experiment_id"],"frames":motion["compile"]["media"]["frames"],"media_sha256":got,"ok":True},sort_keys=True))

if __name__=="__main__":
    main()
