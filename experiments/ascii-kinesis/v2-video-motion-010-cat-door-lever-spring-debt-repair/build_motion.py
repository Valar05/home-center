#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
W, H, GROUND_Y = 64, 22, 19
CELL_W, CELL_H = 8, 12

def line_points(p0, p1):
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    n = max(abs(dx), abs(dy), 1)
    return [(round(x0 + dx * (i / n)), round(y0 + dy * (i / n))) for i in range(n + 1)]

def segchar(p0, p1):
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    if abs(dx) > abs(dy) * 1.8:
        return "-"
    if abs(dy) > abs(dx) * 1.8:
        return "|"
    return "\\" if dx * dy > 0 else "/"

def state_from_key(key):
    rig = key["pose_rig"]
    return {
        "j": rig["joints"],
        "door": rig["door"],
        "curve": rig.get("connector_curve_xy_chars", [0, 0]),
        "boundary": bool(key.get("causal_boundary_to_next", False)),
        "hold": int(key["compile_hold_frames"]),
        "travel": int(key.get("travel_to_next_frames", 0)),
        "key_id": key["key_id"],
    }

def render_ascii(state):
    grid = [[" "] * W for _ in range(H)]
    for x in range(W):
        grid[GROUND_Y][x] = "_"

    j = state["j"]
    hx = int(state["door"]["hinge_x"])
    ex = int(state["door"]["edge_x"])
    for y in range(3, GROUND_Y):
        if 0 <= hx < W:
            grid[y][hx] = "|" if hx == ex else ":"
        if 0 <= ex < W:
            grid[y][ex] = "D" if y in (3, GROUND_Y - 1) else "|"
    if ex != hx:
        lo, hi = sorted((hx, ex))
        for x in range(lo + 1, hi):
            if 0 <= x < W:
                grid[3][x] = "="
                grid[GROUND_Y - 1][x] = "="

    ht = j["handle_tip"]
    start = (ex, int(state["door"]["handle_y"]))
    ch = segchar(start, ht)
    for x, y in line_points(start, ht):
        if 0 <= x < W and 0 <= y < H:
            grid[y][x] = ch
    if 0 <= ht[0] < W and 0 <= ht[1] < H:
        grid[ht[1]][ht[0]] = "H"

    bones = [
        ("root", "shoulder"),
        ("shoulder", "head"),
        ("shoulder", "fore_elbow"),
        ("fore_elbow", "front_paw"),
        ("root", "hind_knee"),
        ("hind_knee", "rear_paw"),
        ("root", "tail_mid"),
        ("tail_mid", "tail_tip"),
    ]
    for a, b in bones:
        p0, p1 = j[a], j[b]
        ch = "~" if ("tail" in a or "tail" in b) else segchar(p0, p1)
        for x, y in line_points(p0, p1):
            if 0 <= x < W and 0 <= y < H and grid[y][x] == " ":
                grid[y][x] = ch

    glyphs = {
        "head": "O",
        "shoulder": "o",
        "root": "@",
        "fore_elbow": "+",
        "hind_knee": "+",
        "front_paw": "*",
        "rear_paw": "*",
        "tail_mid": "~",
        "tail_tip": "~",
    }
    for name, glyph in glyphs.items():
        x, y = j[name]
        if 0 <= x < W and 0 <= y < H:
            grid[y][x] = glyph

    return "\n".join("".join(row).rstrip() for row in grid)

def interpolate(a, b, t):
    s = t * t * (3.0 - 2.0 * t)
    bulge = 4.0 * s * (1.0 - s)
    cx, cy = a.get("curve", [0, 0])
    out = {"j": {}, "door": {}, "curve": a.get("curve", [0, 0]), "boundary": False, "hold": 1, "travel": 0}
    for name in a["j"]:
        ax, ay = a["j"][name]
        bx, by = b["j"][name]
        x = ax * (1.0 - s) + bx * s
        y = ay * (1.0 - s) + by * s
        if name != "handle_tip":
            x += cx * bulge
            y += cy * bulge
        out["j"][name] = [round(x), round(y)]
    for name in a["door"]:
        out["door"][name] = round(a["door"][name] * (1.0 - s) + b["door"][name] * s)
    return out

def build_ascii_frames(motion):
    states = [state_from_key(key) for key in motion["keys"]]
    frames = []
    for i, state in enumerate(states):
        rendered = render_ascii(state)
        frames.extend([rendered] * state["hold"])
        if i == len(states) - 1:
            continue
        nxt = states[i + 1]
        if state["boundary"]:
            frames.extend([rendered] * state["travel"])
        else:
            for step in range(1, state["travel"] + 1):
                frames.append(render_ascii(interpolate(state, nxt, step / (state["travel"] + 1))))
    return frames

def draw_glyph(draw, x, y, ch):
    x0, y0 = x * CELL_W, y * CELL_H
    white = "white"
    if ch == "_":
        draw.line((x0, y0 + 10, x0 + 7, y0 + 10), fill=white)
    elif ch == "-":
        draw.line((x0, y0 + 6, x0 + 7, y0 + 6), fill=white)
    elif ch == "=":
        draw.line((x0, y0 + 5, x0 + 7, y0 + 5), fill=white)
        draw.line((x0, y0 + 7, x0 + 7, y0 + 7), fill=white)
    elif ch == "|":
        draw.line((x0 + 4, y0 + 1, x0 + 4, y0 + 10), fill=white)
    elif ch == ":":
        draw.point((x0 + 4, y0 + 3), fill=white)
        draw.point((x0 + 4, y0 + 8), fill=white)
    elif ch == "/":
        draw.line((x0 + 1, y0 + 10, x0 + 6, y0 + 1), fill=white)
    elif ch == "\\":
        draw.line((x0 + 1, y0 + 1, x0 + 6, y0 + 10), fill=white)
    elif ch == "~":
        draw.line((x0, y0 + 7, x0 + 2, y0 + 5), fill=white)
        draw.line((x0 + 2, y0 + 5, x0 + 5, y0 + 8), fill=white)
        draw.line((x0 + 5, y0 + 8, x0 + 7, y0 + 6), fill=white)
    elif ch == "O":
        draw.ellipse((x0 + 1, y0 + 2, x0 + 6, y0 + 9), outline=white)
    elif ch == "o":
        draw.ellipse((x0 + 2, y0 + 3, x0 + 5, y0 + 7), outline=white)
    elif ch == "@":
        draw.ellipse((x0 + 1, y0 + 2, x0 + 6, y0 + 9), outline=white)
        draw.point((x0 + 4, y0 + 6), fill=white)
    elif ch == "+":
        draw.line((x0 + 4, y0 + 2, x0 + 4, y0 + 9), fill=white)
        draw.line((x0 + 1, y0 + 6, x0 + 7, y0 + 6), fill=white)
    elif ch == "*":
        draw.line((x0 + 1, y0 + 2, x0 + 6, y0 + 9), fill=white)
        draw.line((x0 + 6, y0 + 2, x0 + 1, y0 + 9), fill=white)
        draw.line((x0 + 1, y0 + 6, x0 + 6, y0 + 6), fill=white)
    elif ch == "D":
        draw.line((x0 + 1, y0 + 1, x0 + 1, y0 + 10), fill=white)
        draw.arc((x0 - 1, y0 + 1, x0 + 7, y0 + 10), -90, 90, fill=white)
    elif ch == "H":
        draw.line((x0 + 1, y0 + 2, x0 + 1, y0 + 9), fill=white)
        draw.line((x0 + 6, y0 + 2, x0 + 6, y0 + 9), fill=white)
        draw.line((x0 + 1, y0 + 6, x0 + 6, y0 + 6), fill=white)

def render_png_frames(frames, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    for idx, frame in enumerate(frames):
        image = Image.new("RGB", (W * CELL_W, H * CELL_H), "black")
        draw = ImageDraw.Draw(image)
        lines = frame.splitlines() + [""] * H
        for y, line in enumerate(lines[:H]):
            for x, ch in enumerate(line[:W]):
                if ch != " ":
                    draw_glyph(draw, x, y, ch)
        image.save(out_dir / f"{idx:04d}.png")

def encode_mp4(frames_dir, mp4_path, fps):
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-framerate", str(fps),
            "-i", str(frames_dir / "%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-crf", "28",
            "-movflags", "+faststart",
            str(mp4_path),
        ],
        check=True,
    )

def build_spa(contact_sheet, motion_text, mp4_bytes):
    payload = base64.b64encode(mp4_bytes).decode("ascii")
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis · Cat Door Lever Spring Debt Repair</title>
<style>
:root{{color-scheme:dark;background:#090909;color:#f4f4f4;font-family:system-ui,sans-serif}}
body{{margin:0;padding:16px}}
nav{{display:flex;gap:8px;position:sticky;top:0;background:#090909;padding:8px 0}}
button{{font:inherit;padding:9px 14px}}
section{{display:none}} section.active{{display:block}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #555;padding:12px}}
video{{max-width:100%;height:auto;background:#000;border:1px solid #555}}
</style>
<nav>
<button data-view="ascii">ASCII</button>
<button data-view="json">JSON</button>
<button data-view="video">VIDEO</button>
</nav>
<section id="ascii" class="active"><pre>{html.escape(contact_sheet)}</pre></section>
<section id="json"><pre>{html.escape(motion_text)}</pre></section>
<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{payload}"></video></section>
<script>
const buttons=[...document.querySelectorAll("[data-view]")];
for(const b of buttons)b.onclick=()=>{{
  for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view);
}};
</script>
</html>
"""

def main():
    motion_path = HERE / "motion.json"
    contact_path = HERE / "contact_sheet.txt"
    motion_text = motion_path.read_text(encoding="utf-8")
    motion = json.loads(motion_text)
    contact_sheet = contact_path.read_text(encoding="utf-8")
    frames = build_ascii_frames(motion)
    tmp = HERE / ".motion-frames"
    if tmp.exists():
        shutil.rmtree(tmp)
    render_png_frames(frames, tmp)
    mp4 = HERE / "motion.mp4"
    encode_mp4(tmp, mp4, motion["timing"]["compile_fps"])
    media = mp4.read_bytes()
    sha = hashlib.sha256(media).hexdigest()
    if sha != motion["media"]["sha256"] or len(media) != motion["media"]["bytes"]:
        raise SystemExit(f"media identity mismatch: {sha} / {len(media)}")
    spa = build_spa(contact_sheet, motion_text, media)
    (HERE / "cat-door-lever-spring-debt-repair.motion.html").write_text(spa, encoding="utf-8")
    shutil.rmtree(tmp)
    print(json.dumps({"frames": len(frames), "media_sha256": sha, "bytes": len(media)}, sort_keys=True))

if __name__ == "__main__":
    main()
