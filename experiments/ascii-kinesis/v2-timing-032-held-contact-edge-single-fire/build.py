#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import base64, hashlib, html, json, re, shutil, subprocess, tempfile

ROOT = Path(__file__).resolve().parent
CONTACT = ROOT / "contact-sheet.txt"
MOTION = ROOT / "motion.json"
SPA = ROOT / "held-contact-edge-single-fire.motion.html"
MP4 = ROOT / ".held-contact-edge-single-fire.mp4"

contact = CONTACT.read_text(encoding="utf-8")
motion = json.loads(MOTION.read_text(encoding="utf-8"))
blocks = [b.strip("\n") for b in contact.split("----------------------------------------------------------------------------\n") if b.strip()]
by_id = {b.split()[0]: b for b in blocks}

font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
font = ImageFont.truetype(str(font_path), 15)
small = ImageFont.truetype(str(font_path), 11)
W, H = 720, 320
tmp = Path(tempfile.mkdtemp(prefix="ascii-kinesis-t032-"))
try:
    frame = 0
    for key in motion["keys"]:
        block = by_id[key["key_id"]]
        for _ in range(int(key["exposure_ticks"])):
            im = Image.new("RGB", (W,H), "white")
            d = ImageDraw.Draw(im)
            d.multiline_text((14,12), block, fill="black", font=font, spacing=1)
            d.text((14,298), "Timing032 | EDGE fires once; HIGH contact may persist | abstract ASCII only", fill="black", font=small)
            im.save(tmp / f"frame_{frame:04d}.png")
            frame += 1
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-framerate","24",
        "-i",str(tmp/"frame_%04d.png"),
        "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",
        "-crf","39","-map_metadata","-1",str(MP4)
    ], check=True)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

raw = MP4.read_bytes()
motion["compile"] = {
    "renderer":"Motion Dungeon ASCII-only deterministic key-exposure renderer",
    "fps":24,
    "frame_count":sum(int(k["exposure_ticks"]) for k in motion["keys"]),
    "media":{
        "codec":"h264","pix_fmt":"yuv420p","width":W,"height":H,"fps":24,
        "frames":sum(int(k["exposure_ticks"]) for k in motion["keys"]),
        "bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()
    }
}
MOTION.write_text(json.dumps(motion, ensure_ascii=False, sort_keys=True, separators=(",",":"))+"\n", encoding="utf-8")
motion_text = MOTION.read_text(encoding="utf-8")
payload = base64.b64encode(raw).decode("ascii")
page = f"""<!doctype html>
<meta charset="utf-8">
<title>Timing032 — Held Contact / Edge Single Fire</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;padding:1rem}}
nav{{display:flex;gap:.5rem;margin-bottom:1rem}}
button{{font:inherit;padding:.5rem .75rem}}
section{{display:none}} section.active{{display:block}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;border:1px solid currentColor;padding:.75rem;line-height:1.08}}
video{{max-width:100%;height:auto;border:1px solid currentColor}}
</style>
<nav>
<button data-view="ascii">ASCII</button>
<button data-view="json">JSON</button>
<button data-view="video">VIDEO</button>
</nav>
<section id="ascii" class="active"><pre>{html.escape(contact, quote=False)}</pre></section>
<section id="json"><pre>{html.escape(motion_text, quote=False)}</pre></section>
<section id="video"><video controls loop muted playsinline src="data:video/mp4;base64,{payload}"></video></section>
<script>
const sections=[...document.querySelectorAll("section")];
document.querySelectorAll("button[data-view]").forEach(b=>b.onclick=()=>{{
  sections.forEach(s=>s.classList.toggle("active",s.id===b.dataset.view));
}});
</script>
"""
SPA.write_text(page, encoding="utf-8")
print(json.dumps(motion["compile"], sort_keys=True))
