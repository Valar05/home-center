#!/usr/bin/env python3
from pathlib import Path
import re, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
CONTACT = ROOT / "contact-sheet.txt"
OUT = ROOT / ".root-reversal-secondary-lag-propagation.mp4"
FPS = 24
W, H = 720, 300

def font():
    for p in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    ):
        if Path(p).exists():
            return ImageFont.truetype(p, 20)
    return ImageFont.load_default()

def blocks():
    text = CONTACT.read_text(encoding="utf-8")
    parts = re.split(r"\n-{78}\n", text.strip())
    result = []
    for part in parts:
        lines = part.splitlines()
        header = lines[0]
        m = re.search(r"/(\d+)t", header)
        if not m:
            raise SystemExit(f"missing exposure ticks in {header!r}")
        ticks = int(m.group(1))
        art = []
        for ln in lines[1:]:
            if ln.startswith(" STATE="):
                break
            art.append(ln.rstrip())
        result.append((header, art, ticks))
    return result

def main():
    tmp = ROOT / ".timing037-frames"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir()
    f = font()
    frame_index = 0
    for header, art, ticks in blocks():
        canvas = Image.new("RGB", (W, H), "black")
        d = ImageDraw.Draw(canvas)
        d.text((18, 14), header.split(" | ")[0], font=f, fill="white")
        y = 54
        for ln in art:
            d.text((18, y), ln, font=f, fill="white")
            y += 23
        for _ in range(ticks):
            canvas.save(tmp / f"{frame_index:04d}.png")
            frame_index += 1
    subprocess.run([
        "ffmpeg","-y","-loglevel","error",
        "-framerate",str(FPS),"-i",str(tmp/"%04d.png"),
        "-c:v","libx264","-preset","veryslow","-crf","38",
        "-pix_fmt","yuv420p","-movflags","+faststart",
        str(OUT)
    ], check=True)
    shutil.rmtree(tmp)

if __name__ == "__main__":
    main()
