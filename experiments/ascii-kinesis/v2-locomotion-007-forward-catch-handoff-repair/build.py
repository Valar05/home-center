#!/usr/bin/env python3
"""Reconstruct the canonical Locomotion 007 repair from motion.json only.

No source sprites are read or required. Authored ASCII keys are semantic authority.
Only explicitly declared same-support connectors are permitted; support/contact changes
hard-cut at authored decisive keys. Requires Pillow and ffmpeg.
"""
from pathlib import Path
import base64
import hashlib
import html
import json
import shutil
import subprocess

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
M = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
FPS = int(M["motion_dungeon"]["compile"]["fps"])
GRID_W = int(M["rig"]["grid"]["width"])
GRID_H = int(M["rig"]["grid"]["height"])
GROUND = int(M["rig"]["grid"]["ground_y"])
BONES = [tuple(x) for x in M["rig"]["bones"]]
HOLD = {"ONES": 1, "TWOS": 2, "FOURS": 4}
CONN = {(c["from"], c["to"]): c for c in M["connectors"]}
KEYS = M["keys"]


def line_points(a, b):
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    pts = []
    while True:
        pts.append((x0, y0))
        if (x0, y0) == (x1, y1):
            return pts
        e = 2 * err
        if e >= dy:
            err += dy
            x0 += sx
        if e <= dx:
            err += dx
            y0 += sy


def art(joints, support):
    grid = [[" "] * GRID_W for _ in range(GRID_H)]
    for x in range(GRID_W):
        grid[GROUND][x] = "-"
    for a, b in BONES:
        pa = joints[a]
        pb = joints[b]
        for x, y in line_points(pa, pb)[1:-1]:
            if 0 <= x < GRID_W and 0 <= y < GRID_H and grid[y][x] == " ":
                prod = (pb[0] - pa[0]) * (pb[1] - pa[1])
                grid[y][x] = "/" if prod < 0 else ("\\" if prod > 0 else ("-" if pb[1] == pa[1] else "|"))
    for name, (x, y) in joints.items():
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            grid[y][x] = "O" if name == "head" else ("@" if name == "pelvis" else ("*" if name in ("l_hand", "r_hand", "l_foot", "r_foot") else "o"))
    if support.startswith("LEFT_"):
        x, y = joints["l_foot"]
        grid[y][x] = "!"
    elif support == "RIGHT_FOOT_PROBE_CONTACT":
        x, y = joints["r_foot"]
        grid[y][x] = "?"
    elif support.startswith("RIGHT_"):
        x, y = joints["r_foot"]
        grid[y][x] = "!"
    return "\n".join("".join(row).rstrip() for row in grid)


def bridge(a, b, t, bend):
    s = t * t * (3 - 2 * t)
    out = {}
    for name, pa in a.items():
        pb = b[name]
        x = pa[0] + (pb[0] - pa[0]) * s
        y = pa[1] + (pb[1] - pa[1]) * s
        amp = 4 * s * (1 - s) * bend
        if name in ("head", "chest"):
            y += amp * 0.35
        elif name in ("l_hand", "r_hand"):
            y += amp * (0.8 if name == "l_hand" else -0.6)
        elif name in ("l_knee", "r_knee"):
            y += amp * 0.25
        elif name == "pelvis":
            y += amp * 0.20
        out[name] = [round(x), round(y)]
    return out


def contact_sheet():
    out = []
    for k in KEYS:
        out.extend([
            f"{k['key_id']} {k['name']}  [{k['timing_class']} / {k['timing_provenance']}]  SUPPORT={k['support_contact']}",
            "ROOT: " + k["motion_arc_root_note"],
            "ROLE: " + k["causal_role"],
            "",
        ])
        out.extend(art(k["joints"], k["support_contact"]).splitlines())
        out.extend(["", ""])
    return "\n".join(out).rstrip() + "\n"


frames = []
for i, k in enumerate(KEYS):
    frames += [(k["joints"], k["support_contact"], k["key_id"], k["name"])] * HOLD[k["timing_class"]]
    if i < len(KEYS) - 1:
        nxt = KEYS[i + 1]
        conn = CONN.get((k["key_id"], nxt["key_id"]))
        if conn:
            if k["support_contact"] != nxt["support_contact"]:
                raise SystemExit(f"CONNECTOR_CROSSES_SUPPORT_CHANGE {k['key_id']}->{nxt['key_id']}")
            for q in range(1, int(conn["frames"]) + 1):
                frames.append((
                    bridge(k["joints"], nxt["joints"], q / (int(conn["frames"]) + 1), int(conn["bend"])),
                    k["support_contact"],
                    k["key_id"] + "→" + nxt["key_id"],
                    "AUTHORED_CONNECTOR",
                ))

frames += [(KEYS[-1]["joints"], KEYS[-1]["support_contact"], KEYS[-1]["key_id"], KEYS[-1]["name"])] * int(M["motion_dungeon"]["compile"]["endpoint_hold_frames"])
expected_frames = int(M["motion_dungeon"]["compile"]["frame_count"])
if len(frames) != expected_frames:
    raise SystemExit(f"FRAME_COUNT_MISMATCH {len(frames)} != {expected_frames}")

tmp = HERE / "_rebuild_frames"
shutil.rmtree(tmp, ignore_errors=True)
tmp.mkdir()

font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
if not font_path.is_file():
    raise SystemExit("REQUIRED_FONT_MISSING /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
font = ImageFont.truetype(str(font_path), 10)
small = ImageFont.truetype(str(font_path), 8)

for idx, (joints, support, kid, name) in enumerate(frames):
    im = Image.new("RGB", (640, 360), (15, 15, 16))
    d = ImageDraw.Draw(im)
    d.text((18, 10), "ASCII KINESIS · LOCOMOTION 007 · FORWARD CATCH HANDOFF REPAIR", font=small, fill=(180, 180, 180))
    d.text((18, 24), f"{kid}  {name}  SUPPORT={support}", font=small, fill=(235, 235, 235))
    d.multiline_text((18, 44), art(joints, support), font=font, fill=(245, 245, 240), spacing=0)
    d.text((18, 332), "! trusted support   ? probe only   @ pelvis/root   * extremity", font=small, fill=(170, 170, 170))
    d.text((500, 332), f"frame {idx + 1:03d}/{len(frames):03d}", font=small, fill=(130, 130, 130))
    im.save(tmp / f"frame_{idx:04d}.png", compress_level=9)

mp4 = HERE / "motion.mp4"
subprocess.run([
    "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
    "-i", str(tmp / "frame_%04d.png"), "-c:v", "libx264", "-preset", "veryslow",
    "-crf", str(M["motion_dungeon"]["compile"]["crf"]), "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", "-metadata", "comment=ASCII Kinesis abstract rig only",
    str(mp4),
], check=True)
subprocess.run(["ffmpeg", "-v", "error", "-i", str(mp4), "-f", "null", "-"], check=True)

media_sha = hashlib.sha256(mp4.read_bytes()).hexdigest()
expected_sha = M["motion_dungeon"]["compile"]["media_sha256"]
if media_sha != expected_sha:
    raise SystemExit(f"MEDIA_HASH_MISMATCH {media_sha} != {expected_sha}")
if len(mp4.read_bytes()) != int(M["motion_dungeon"]["compile"]["media_bytes"]):
    raise SystemExit("MEDIA_BYTE_COUNT_MISMATCH")

ct = contact_sheet()
(HERE / "contact_sheet.txt").write_text(ct, encoding="utf-8")
motion_pretty = json.dumps(M, ensure_ascii=False, indent=2)
b64 = base64.b64encode(mp4.read_bytes()).decode("ascii")
page = f"""<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Locomotion 007 — Forward Catch Handoff Repair</title>
<style>
:root{{color-scheme:dark}}
body{{margin:0;background:#0f0f10;color:#f2f2ee;font:16px/1.35 ui-sans-serif,system-ui,sans-serif}}
header{{padding:1rem 1.25rem;border-bottom:1px solid #333}}
nav{{display:flex;gap:.5rem;padding:.75rem 1rem;position:sticky;top:0;background:#0f0f10}}
button{{background:#19191b;color:#eee;border:1px solid #444;padding:.65rem 1rem;border-radius:.35rem}}
button[aria-selected="true"]{{background:#eee;color:#111}}
main{{padding:0 1rem 1rem}}
section[hidden]{{display:none}}
pre{{font-family:"DejaVu Sans Mono","Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2;background:#121214;border:1px solid #2d2d30;padding:1rem;max-height:78vh}}
video{{display:block;width:min(100%,1280px);height:auto;background:#000;border:1px solid #333}}
.note{{max-width:88ch;color:#aaa}}
</style>
</head>
<body>
<header><strong>ASCII Kinesis V2 Locomotion 007 — Forward Catch Handoff Repair</strong><div class="note">Canonical active repair successor for Locomotion 001. Source art is evidence-only and is not embedded. One-shot recovery exits with unresolved travel debt rather than looping to idle.</div></header>
<nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav>
<main>
<section id="ascii"><pre id="ascii-text">{html.escape(ct)}</pre></section>
<section id="json" hidden><pre id="json-text">{html.escape(motion_pretty)}</pre></section>
<section id="video" hidden><video id="motion-video" controls autoplay muted playsinline src="data:video/mp4;base64,{b64}"></video><p class="note">H.264/yuv420p 640×360 @ 24 fps · 39 frames · abstract ASCII rig only · SHA-256 {media_sha}</p></section>
</main>
<script>
const buttons=[...document.querySelectorAll('button[data-view]')];
const sections={{ascii:document.getElementById('ascii'),json:document.getElementById('json'),video:document.getElementById('video')}};
for(const b of buttons) b.addEventListener('click',()=>{{
  for(const x of buttons) x.setAttribute('aria-selected',String(x===b));
  for(const [name,section] of Object.entries(sections)) section.hidden=name!==b.dataset.view;
}});
</script>
</body>
</html>
"""
(HERE / "forward-catch-handoff-repair.motion.html").write_text(page, encoding="utf-8")
print(json.dumps({
    "frame_count": len(frames),
    "media_sha256": media_sha,
    "media_bytes": len(mp4.read_bytes()),
    "contact_sheet_sha256": hashlib.sha256(ct.encode("utf-8")).hexdigest(),
    "spa_sha256": hashlib.sha256(page.encode("utf-8")).hexdigest(),
}, sort_keys=True))
