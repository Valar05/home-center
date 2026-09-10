#!/usr/bin/env python3
from pathlib import Path
import base64, gzip, hashlib, html, json, shutil, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
CONTACT = ROOT / "contact-sheet.txt"
MOTION = ROOT / "motion.json"
SPA = ROOT / "late-cue-causal-horizon-downstream-only.motion.html"
MP4 = ROOT / ".late-cue-causal-horizon-downstream-only.mp4"

WIDTH, HEIGHT = 560, 220
FPS = 24

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()

def load_blocks(text):
    blocks = text.rstrip("\n").split("\n------------------------------------------------------------------------------\n")
    out = {}
    for block in blocks:
        lines = block.splitlines()
        key = lines[0].split()[0]
        figure = []
        for line in lines[1:]:
            if line.startswith(" ROOT="):
                break
            figure.append(line)
        out[key] = figure
    return out

def render_ascii(lines):
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 17)
    # center-ish while keeping all ASCII visible
    y = 16
    for line in lines:
        draw.text((12, y), line, font=font, fill="black")
        y += 20
    return img

def main():
    contact_text = CONTACT.read_text(encoding="utf-8")
    motion = json.loads(MOTION.read_text(encoding="utf-8"))
    blocks = load_blocks(contact_text)
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        idx = 0
        for key in motion["keys"]:
            frame = render_ascii(blocks[key["key_id"]])
            for _ in range(int(key["exposure_ticks"])):
                frame.save(td / f"f{idx:04d}.png")
                idx += 1
        cmd = [
            "ffmpeg","-hide_banner","-loglevel","error","-y",
            "-framerate",str(FPS),"-i",str(td/"f%04d.png"),
            "-c:v","libx264","-pix_fmt","yuv420p","-crf","38",
            "-movflags","+faststart",
            "-map_metadata","-1",
            str(MP4)
        ]
        subprocess.run(cmd, check=True)
    raw = MP4.read_bytes()
    motion["compile"] = {
        "fps": FPS,
        "frame_count": sum(int(k["exposure_ticks"]) for k in motion["keys"]),
        "renderer": "Motion Dungeon ASCII-only deterministic decisive-key exposure renderer",
        "media": {
            "codec":"h264","pix_fmt":"yuv420p","width":WIDTH,"height":HEIGHT,
            "fps":FPS,"frames":sum(int(k["exposure_ticks"]) for k in motion["keys"]),
            "bytes":len(raw),"sha256":sha256_bytes(raw)
        }
    }
    motion["revision"]["actual_render_sha256"] = sha256_bytes(raw)
    MOTION.write_text(json.dumps(motion, ensure_ascii=False, sort_keys=True, separators=(",",":"))+"\n", encoding="utf-8")
    motion_text = MOTION.read_text(encoding="utf-8")
    c64 = base64.b64encode(gzip.compress(contact_text.encode("utf-8"), mtime=0)).decode()
    j64 = base64.b64encode(gzip.compress(motion_text.encode("utf-8"), mtime=0)).decode()
    v64 = base64.b64encode(raw).decode()
    page = f"""<!doctype html><meta charset="utf-8"><title>Timing036 — Late Cue Causal Horizon</title>
<style>body{{font-family:system-ui;margin:0;background:#111;color:#eee}}nav{{position:sticky;top:0;background:#181818;padding:.6rem;display:flex;gap:.5rem}}button{{font:inherit;padding:.5rem .8rem}}section{{display:none;padding:1rem}}section.on{{display:block}}pre{{white-space:pre;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;line-height:1.05}}video{{max-width:100%;height:auto}}</style>
<nav><button data-t="a">ASCII</button><button data-t="j">JSON</button><button data-t="v">VIDEO</button></nav>
<section id="a" class="on"><pre id="ap"></pre></section>
<section id="j"><pre id="jp"></pre></section>
<section id="v"><video id="vp" controls loop autoplay muted playsinline></video></section>
<script>
const C="{c64}",J="{j64}",V="{v64}";
async function ungz(s){{let b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));let t=await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip"))).text();return t}}
(async()=>{{ap.textContent=await ungz(C);jp.textContent=await ungz(J);vp.src="data:video/mp4;base64,"+V}})();
document.querySelectorAll("button").forEach(b=>b.onclick=()=>{{document.querySelectorAll("section").forEach(s=>s.classList.remove("on"));document.getElementById(b.dataset.t).classList.add("on")}})
</script>"""
    SPA.write_text(page, encoding="utf-8")

if __name__ == "__main__":
    main()
