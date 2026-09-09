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
W = int(MOTION["rig"]["grid"]["width"])
H = int(MOTION["rig"]["grid"]["height"])
GROUND = 21
FPS = int(MOTION["compile"]["fps"])
HOLD = {"ONES": 1, "TWOS": 2, "FOURS": 4}
HOLD_SCALE = int(MOTION["compile"].get("render_hold_scale", 2))
FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

POINT_FIELDS = [
    "root", "chest", "head",
    "l_elbow", "l_hand", "r_elbow", "r_hand",
    "l_knee", "l_foot", "r_knee", "r_foot",
]

def put(grid, x, y, ch):
    x = int(round(x)); y = int(round(y))
    if 0 <= x < W and 0 <= y < H:
        grid[y][x] = ch

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

def abs_pt(state, field):
    root = state["root"]
    if field == "root":
        return tuple(root)
    p = state[field]
    return (root[0] + p[0], root[1] + p[1])

def pose_to_grid(state):
    g = [[" "] * W for _ in range(H)]
    for x in range(1, W - 1):
        g[GROUND][x] = "_"

    hip = abs_pt(state, "root")
    chest = abs_pt(state, "chest")
    head = abs_pt(state, "head")
    le = abs_pt(state, "l_elbow"); lh = abs_pt(state, "l_hand")
    re = abs_pt(state, "r_elbow"); rh = abs_pt(state, "r_hand")
    lk = abs_pt(state, "l_knee"); lf = abs_pt(state, "l_foot")
    rk = abs_pt(state, "r_knee"); rf = abs_pt(state, "r_foot")

    line(g, *hip, *chest, "|")
    line(g, *chest, *le, "/")
    line(g, *le, *lh, "-")
    line(g, *chest, *re, "\\")
    line(g, *re, *rh, "-")
    line(g, *hip, *lk, "/")
    line(g, *lk, *lf, "/")
    line(g, *hip, *rk, "\\")
    line(g, *rk, *rf, "\\")

    put(g, *hip, "@"); put(g, *chest, "+"); put(g, *head, "O")
    put(g, *le, "o"); put(g, *lh, "x"); put(g, *re, "o"); put(g, *rh, "x")
    put(g, *lk, "o"); put(g, *rk, "o")
    put(g, *lf, "="); put(g, *rf, "=")

    if state.get("l_contact"):
        put(g, lf[0], min(GROUND - 1, lf[1]), "!")
    if state.get("r_contact"):
        put(g, rf[0], min(GROUND - 1, rf[1]), "!")
    return "\n".join("".join(row).rstrip() for row in g).rstrip()

def interp(a, b, t):
    # Smooth geometry only. Semantic support/contact stays with the source
    # until the authored destination key is reached.
    s = t * t * (3.0 - 2.0 * t)
    out = {}
    for field in POINT_FIELDS:
        av = a[field]; bv = b[field]
        out[field] = [av[0] + (bv[0] - av[0]) * s,
                      av[1] + (bv[1] - av[1]) * s]
    out["l_contact"] = bool(a.get("l_contact", False))
    out["r_contact"] = bool(a.get("r_contact", False))
    return out

keys = []
for key in MOTION["keys"]:
    state = dict(key["authoring"])
    state["l_contact"] = bool(state.get("l_contact", False))
    state["r_contact"] = bool(state.get("r_contact", False))
    keys.append(state)

# Literal selectable contact sheet.
panels = []
for key, state in zip(MOTION["keys"], keys):
    pose = pose_to_grid(state).splitlines()
    pose += [""] * (H - len(pose))
    header = f'{key["key_id"]} {key["label"]} [{key["timing_class"]}/{key["timing_provenance"]}]'
    footer = f'{key["support_contact"]} | {key["causal_role"]}'
    panel = [header] + [ln.ljust(W) for ln in pose[:H]] + [footer]
    panels.append(panel)

sheet_rows = []
for i in range(0, len(panels), 2):
    batch = panels[i:i+2]
    if len(batch) == 1:
        batch.append([""] * (H + 2))
    for r in range(H + 2):
        sheet_rows.append("   |   ".join(p[r].ljust(W + 42) for p in batch))
    sheet_rows.append("")
sheet = "\n".join(sheet_rows).rstrip() + "\n"
(ROOT / "contact-sheet.txt").write_text(sheet, encoding="utf-8")

# Motion Dungeon compile.
frames = []
for i, (key, state) in enumerate(zip(MOTION["keys"], keys)):
    for _ in range(HOLD[key["timing_class"]] * HOLD_SCALE):
        frames.append(pose_to_grid(state))
    if i < len(keys) - 1:
        # More bridge exposure only where root is traveling fastest.
        bridge_n = 2 if i in {0,1,4,5,6,7,9,10} else 1
        for j in range(1, bridge_n + 1):
            t = j / (bridge_n + 1)
            frames.append(pose_to_grid(interp(state, keys[i+1], t)))

frames_dir = ROOT / ".frames"
if frames_dir.exists():
    shutil.rmtree(frames_dir)
frames_dir.mkdir()

imgw, imgh = 512, 288
font = ImageFont.truetype(FONT_PATH, 13)
for idx, txt in enumerate(frames):
    img = Image.new("RGB", (imgw, imgh), (10, 10, 10))
    draw = ImageDraw.Draw(img)
    draw.multiline_text((8, 4), txt, font=font, fill=(240, 240, 240), spacing=-1)
    img.save(frames_dir / f"{idx:04d}.png", compress_level=9)

mp4 = ROOT / "counterspin-hook-catch-recovery.mp4"
subprocess.run([
    "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
    "-framerate", str(FPS), "-i", str(frames_dir / "%04d.png"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "29",
    "-threads", "1", "-movflags", "+faststart", str(mp4)
], check=True)
shutil.rmtree(frames_dir)

media = mp4.read_bytes()
sha = hashlib.sha256(media).hexdigest()
expected = MOTION.get("media", {}).get("sha256") or ""
if expected and sha != expected:
    raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={expected} got={sha}")

print(json.dumps({
    "ok": True,
    "frames": len(frames),
    "bytes": len(media),
    "media_sha256": sha,
    "contact_sheet_sha256": hashlib.sha256((ROOT / "contact-sheet.txt").read_bytes()).hexdigest()
}, sort_keys=True))
