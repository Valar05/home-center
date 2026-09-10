#!/usr/bin/env python3
"""Deterministic Motion Dungeon builder for Timing025.

Source pixels are never read. The MP4 is rendered solely from the persisted
abstract ASCII pose_rig strings plus authored exposure ticks in motion.json.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MOTION_PATH = ROOT / "motion.json"
CONTACT_PATH = ROOT / "contact-sheet.txt"
SLUG = "serial-consequence-wave-root-rebase"
SPA_PATH = ROOT / f"{SLUG}.motion.html"

WIDTH = 440
HEIGHT = 200
FPS = 24
FONT_PATH = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
FONT_SIZE = 9
SMALL_SIZE = 6

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def render_mp4(output_path: Path) -> bytes:
    motion = json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    frames_dir = Path(tempfile.mkdtemp(prefix="ascii-kinesis-timing025-"))
    try:
        font = ImageFont.truetype(str(FONT_PATH), FONT_SIZE)
        small = ImageFont.truetype(str(FONT_PATH), SMALL_SIZE)
        frame_no = 0
        for key in motion["keys"]:
            for _ in range(int(key["exposure_ticks"])):
                im = Image.new("RGB", (WIDTH, HEIGHT), "white")
                draw = ImageDraw.Draw(im)
                draw.multiline_text((6, 8), key["pose_rig"], fill="black", font=font, spacing=0)
                draw.line((4, 158, 436, 158), fill="black", width=1)
                footer = (
                    f"{key['key_id']}  {key['causal_role']}  {key['timing_class']}  "
                    f"SUPPORT={key['support_contact']}  V={key['root_velocity']:+.2f}  "
                    f"WAVE={key['consequence_stage']}"
                )
                draw.text((6, 164), footer, fill="black", font=small)
                draw.text((6, 181), "abstract ASCII rig only | source pixels: none", fill="black", font=small)
                im.save(frames_dir / f"frame_{frame_no:04d}.png")
                frame_no += 1
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
                "-i", str(frames_dir / "frame_%04d.png"),
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-preset", "medium", "-crf", "38", "-threads", "1",
                "-movflags", "+faststart", "-map_metadata", "-1",
                str(output_path),
            ],
            check=True,
        )
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)
    return output_path.read_bytes()

def build_spa(video_bytes: bytes) -> str:
    ascii_text = CONTACT_PATH.read_text(encoding="utf-8")
    json_text = MOTION_PATH.read_text(encoding="utf-8")
    media_uri = "data:video/mp4;base64," + base64.b64encode(video_bytes).decode("ascii")
    def esc(s: str) -> str:
        return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis Timing025 — Serial Consequence Wave / Deferred Root Rebase</title>
<style>
:root{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}}
body{{margin:0;padding:16px;background:#fff;color:#111}}
nav{{display:flex;gap:8px;margin-bottom:12px}}
button{{font:inherit;padding:8px 12px}}
section{{display:none}}
section.active{{display:block}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08;border:1px solid currentColor;padding:12px;max-height:72vh}}
video{{max-width:100%;height:auto;border:1px solid currentColor}}
.small{{font-size:12px}}
</style>
</head>
<body>
<h1>Timing025 — Serial Consequence Wave / Deferred Root Rebase</h1>
<p class="small">Motion Dungeon compile from abstract ASCII rig + authored timing only. Source pixels: none.</p>
<nav>
<button data-view="ascii">ASCII</button>
<button data-view="json">JSON</button>
<button data-view="video">VIDEO</button>
</nav>
<section id="ascii" class="active"><pre>{esc(ascii_text)}</pre></section>
<section id="json"><pre>{esc(json_text)}</pre></section>
<section id="video"><video controls loop muted playsinline src="{media_uri}"></video></section>
<script>
const buttons=[...document.querySelectorAll("button[data-view]")];
const sections=[...document.querySelectorAll("section")];
for(const b of buttons) b.addEventListener("click",()=>{{
  for(const s of sections) s.classList.toggle("active",s.id===b.dataset.view);
}});
</script>
</body>
</html>
"""

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default=str(ROOT / f"{SLUG}.mp4"))
    ap.add_argument("--emit-spa", action="store_true")
    args = ap.parse_args()
    out = Path(args.output)
    video = render_mp4(out)
    motion = json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    expected = motion["compile"]["media"]["sha256"]
    actual = sha256_bytes(video)
    if actual != expected:
        raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={expected} actual={actual}")
    if args.emit_spa:
        SPA_PATH.write_text(build_spa(video), encoding="utf-8")
    print(json.dumps({"bytes":len(video),"sha256":actual,"spa":str(SPA_PATH) if args.emit_spa else None},sort_keys=True))

if __name__ == "__main__":
    main()
