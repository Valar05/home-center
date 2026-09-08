#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MOTION = json.loads((ROOT / "motion.json").read_text(encoding="utf-8"))
W, H = MOTION["rig"]["grid"]["width"], MOTION["rig"]["grid"]["height"]
GROUND = 20
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
FPS = int(MOTION["compile"]["fps"])
HOLD = {"ONES": 1, "TWOS": 2, "FOURS": 4}
NUM_FIELDS = ["x", "y", "pitch", "torso", "arm_angle", "hip_dx"]

def line(grid, x0, y0, x1, y1, ch="*"):
    x0, y0, x1, y1 = map(int, [round(x0), round(y0), round(x1), round(y1)])
    dx = abs(x1 - x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0); sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        if 0 <= x0 < W and 0 <= y0 < H and grid[y0][x0] == " ":
            grid[y0][x0] = ch
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy

def put(grid, x, y, ch):
    x = int(round(x)); y = int(round(y))
    if 0 <= x < W and 0 <= y < H:
        grid[y][x] = ch

def rot(pt, angle_deg, origin):
    a = math.radians(angle_deg)
    x, y = pt; ox, oy = origin
    dx = x - ox; dy = y - oy
    return (ox + dx * math.cos(a) - dy * math.sin(a),
            oy + dx * math.sin(a) + dy * math.cos(a))

def pose_to_grid(s):
    g = [[" "] * W for _ in range(H)]
    for x in range(2, W - 2):
        g[GROUND][x] = "_"
    cx, cy, ang = s["x"], s["y"], s["pitch"]
    left = rot((cx - 5, cy + 2), ang, (cx, cy))
    right = rot((cx + 5, cy + 2), ang, (cx, cy))
    line(g, *left, *right, "=")
    dl = rot((cx - 5, cy), ang, (cx, cy))
    dr = rot((cx + 5, cy), ang, (cx, cy))
    line(g, *dl, *dr, "-")
    wl = rot((cx - 4, cy + 3), ang, (cx, cy))
    wr = rot((cx + 4, cy + 3), ang, (cx, cy))
    put(g, *wl, "o"); put(g, *wr, "o")

    hip = rot((cx + s.get("hip_dx", -1), cy - 2 + s.get("hip_dy", 0)), ang, (cx, cy))
    torso_ang = s["torso"]
    shoulder = (hip[0] + 3 * math.cos(math.radians(torso_ang - 90)),
                hip[1] + 3 * math.sin(math.radians(torso_ang - 90)))
    head = (shoulder[0] + 1.6 * math.cos(math.radians(torso_ang - 90)),
            shoulder[1] + 1.6 * math.sin(math.radians(torso_ang - 90)))
    put(g, *hip, "@"); put(g, *shoulder, "+"); put(g, *head, "O")
    line(g, *hip, *shoulder, "|")

    peg_rear = rot((cx - 3, cy + 1), ang, (cx, cy))
    peg_front = rot((cx + 2, cy + 1), ang, (cx, cy))
    knee1 = (hip[0] - 2 + s.get("rear_knee_dx", 0), hip[1] + 2 + s.get("rear_knee_dy", 0))
    knee2 = (hip[0] + 2 + s.get("front_knee_dx", 0), hip[1] + 2 + s.get("front_knee_dy", 0))
    line(g, *hip, *knee1, "/"); line(g, *knee1, *peg_rear, "/")
    line(g, *hip, *knee2, "\\"); line(g, *knee2, *peg_front, "\\")

    hand1 = rot((cx + 3, cy - 1), ang, (cx, cy))
    elbow1 = ((shoulder[0] + hand1[0]) / 2 + 1, (shoulder[1] + hand1[1]) / 2)
    line(g, *shoulder, *elbow1, "-"); line(g, *elbow1, *hand1, "-"); put(g, *hand1, "x")
    aa = math.radians(s.get("arm_angle", -140))
    hand2 = (shoulder[0] + 4 * math.cos(aa), shoulder[1] + 4 * math.sin(aa))
    elbow2 = ((shoulder[0] + hand2[0]) / 2 - 0.5, (shoulder[1] + hand2[1]) / 2)
    line(g, *shoulder, *elbow2, "~"); line(g, *elbow2, *hand2, "~"); put(g, *hand2, "x")

    if s.get("rear_contact"):
        put(g, wl[0], GROUND - 1, "!")
    if s.get("front_contact"):
        put(g, wr[0], GROUND - 1, "!")
    return "\n".join("".join(r).rstrip() for r in g).rstrip()

def interp(a, b, t):
    s = t * t * (3 - 2 * t)
    out = {}
    for f in NUM_FIELDS:
        out[f] = a.get(f, 0) + (b.get(f, 0) - a.get(f, 0)) * s
    for f in ["rear_knee_dx", "front_knee_dx", "rear_knee_dy", "front_knee_dy"]:
        out[f] = a.get(f, 0) + (b.get(f, 0) - a.get(f, 0)) * s
    for f in ["rear_contact", "front_contact"]:
        out[f] = b.get(f, False) if t >= 1 else a.get(f, False)
    return out

keys = []
for key in MOTION["keys"]:
    state = dict(key["authoring"])
    state.update({
        "key_id": key["key_id"],
        "label": key.get("label", key["key_id"]),
        "timing_class": key["timing_class"],
        "timing_provenance": key["timing_provenance"],
    })
    keys.append(state)

# Reconstruct literal contact sheet from authored poses.
panels = []
for key, state in zip(MOTION["keys"], keys):
    pose = pose_to_grid(state).splitlines()
    pose += [""] * (H - len(pose))
    header = f'{key["key_id"]} {key["label"]} [{key["timing_class"]}/{key["timing_provenance"]}]'
    panels.append([header] + [ln.ljust(W) for ln in pose[:H]])

rows = []
for i in range(0, len(panels), 2):
    batch = panels[i:i+2]
    for r in range(H + 1):
        rows.append("   |   ".join(p[r].ljust(W + 24) for p in batch))
    rows.append("")
sheet = "\n".join(rows).rstrip() + "\n"
(ROOT / "contact-sheet.txt").write_text(sheet, encoding="utf-8")

# Motion Dungeon: decisive authored states + explicit holds + deterministic bridge geometry.
frames = []
for i, (key, state) in enumerate(zip(MOTION["keys"], keys)):
    for _ in range(HOLD[key["timing_class"]] * 2):
        frames.append(pose_to_grid(state))
    if i < len(keys) - 1:
        a, b = state, keys[i + 1]
        n = 3 if i in {0, 2, 5, 6, 7} else 2
        for j in range(1, n + 1):
            t = j / (n + 1)
            bridge = interp(a, b, t)
            if i in {1, 2, 3, 4}:
                bridge["y"] -= math.sin(math.pi * t) * (0.7 if i < 3 else -0.25)
            frames.append(pose_to_grid(bridge))

frames_dir = ROOT / ".frames"
if frames_dir.exists():
    shutil.rmtree(frames_dir)
frames_dir.mkdir()
font = ImageFont.truetype(FONT_PATH, 18)
imgw, imgh = W * 11 + 20, H * 21 + 20
for idx, txt in enumerate(frames):
    img = Image.new("RGB", (imgw, imgh), (12, 12, 12))
    draw = ImageDraw.Draw(img)
    draw.multiline_text((10, 8), txt, font=font, fill=(238, 238, 238), spacing=0)
    img.save(frames_dir / f"{idx:04d}.png", compress_level=9)

full_mp4 = ROOT / "._air018_full.mp4"
mp4 = ROOT / "rider-chassis-counterpitch-landing-debt.mp4"
subprocess.run([
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-framerate", str(FPS), "-i", str(frames_dir / "%04d.png"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "30",
    "-threads", "1", "-movflags", "+faststart", str(full_mp4)
], check=True)
subprocess.run([
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-i", str(full_mp4), "-vf", "scale=362:262:flags=lanczos",
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "30",
    "-threads", "1", "-movflags", "+faststart", str(mp4)
], check=True)
full_mp4.unlink()
shutil.rmtree(frames_dir)

sha = hashlib.sha256(mp4.read_bytes()).hexdigest()
expected = MOTION["media"]["sha256"]
if sha != expected:
    raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={expected} got={sha}")
print(json.dumps({
    "ok": True,
    "frames": len(frames),
    "media_sha256": sha,
    "contact_sheet_sha256": hashlib.sha256((ROOT / "contact-sheet.txt").read_bytes()).hexdigest()
}, sort_keys=True))
