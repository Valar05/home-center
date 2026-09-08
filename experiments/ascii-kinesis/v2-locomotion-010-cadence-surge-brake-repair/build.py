#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
M = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
MAN = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
W = int(M["rig"]["grid"]["width"])
H = int(M["rig"]["grid"]["height"])
G = int(M["rig"]["grid"]["ground_y"])
ORDER = list(M["rig"]["joint_order"])
BONES = [tuple(x) for x in M["rig"]["bones"]]
HOLD = {"ONES": 1, "TWOS": 2, "FOURS": 4}

def joints(key):
    pts = key["pose_rig"]["points"]
    if len(pts) != len(ORDER):
        raise SystemExit(f"{key['key_id']}: joint count mismatch")
    return {name: pts[i] for i, name in enumerate(ORDER)}

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

def ascii_frame(j, support):
    g = [[" "] * W for _ in range(H)]
    for x in range(W):
        g[G][x] = "-"
    for a, b in BONES:
        pa, pb = j[a], j[b]
        for x, y in line_points(pa, pb)[1:-1]:
            if 0 <= x < W and 0 <= y < H and g[y][x] == " ":
                dx = pb[0] - pa[0]
                dy = pb[1] - pa[1]
                g[y][x] = "/" if dx * dy < 0 else ("\\" if dx * dy > 0 else ("-" if dy == 0 else "|"))
    for name, (x, y) in j.items():
        if 0 <= x < W and 0 <= y < H:
            g[y][x] = "O" if name == "head" else ("@" if name == "pelvis" else ("+" if name == "chest" else ("o" if "elbow" in name or "knee" in name else "*")))
    for side, node in [("L_FOOT", "l_foot"), ("R_FOOT", "r_foot")]:
        x, y = j[node]
        if side + "_PROBE" in support:
            g[y][x] = "?"
        elif side in support:
            g[y][x] = "!"
    return "\n".join("".join(row).rstrip() for row in g)

def compile_frames():
    if M.get("connectors"):
        raise SystemExit("Locomotion010 fails closed: generated connectors are forbidden; every transition geometry frame must be authored")
    frames = []
    for key in M["keys"]:
        timing = key["timing_class"]
        if timing not in HOLD:
            raise SystemExit(f"{key['key_id']}: unsupported timing {timing}")
        frame = (joints(key), key["support_contact"], key["key_id"], key["name"])
        frames.extend([frame] * HOLD[timing])
    last = M["keys"][-1]
    frame = (joints(last), last["support_contact"], last["key_id"], last["name"])
    frames.extend([frame] * int(M["motion_dungeon"]["compile"]["endpoint_hold_frames"]))
    return frames

def contact_sheet():
    lines = [
        "ASCII KINESIS V2 LOCOMOTION 010 — CADENCE SURGE / BRAKE REPAIR",
        "Legend: ! trusted support   ? probe-only contact   @ pelvis/root   + chest   - ground",
        "Timing: ONES/TWOS/FOURS are PoseLab cadence classes; every decisive key here is INFERRED.",
        "Phase law: cadence changes root spacing and holds without resetting L/R support order.",
        "Source boundary: independent abstract ASCII only; no source pixels/palette/layout/contours/choreography are embedded.",
        "",
    ]
    for key in M["keys"]:
        bridge = "  BRIDGE" if key.get("authored_bridge_key") else ""
        lines.extend([
            f"{key['key_id']} {key['name']}  [{key['timing_class']} / {key['timing_provenance']}]  SUPPORT={key['support_contact']}  PHASE={key['cadence_phase']}{bridge}",
            "ROOT: " + key["motion_arc_root_note"],
            "ROLE: " + key["causal_role"],
            "ATTITUDE: " + key.get("attitude", "—"),
            "",
            ascii_frame(joints(key), key["support_contact"]),
            "",
            "",
        ])
    return "\n".join(lines).rstrip() + "\n"

def render_mp4(frames, out):
    frame_dir = HERE / ".motion_frames"
    shutil.rmtree(frame_dir, ignore_errors=True)
    frame_dir.mkdir()
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
    font = ImageFont.truetype(font_path, 10)
    small = ImageFont.truetype(font_path, 8)
    for idx, (j, support, kid, name) in enumerate(frames):
        im = Image.new("RGB", (960, 480), (10, 10, 12))
        d = ImageDraw.Draw(im)
        d.text((16, 10), "ASCII KINESIS · LOCOMOTION 010 · CADENCE SURGE / BRAKE REPAIR", font=small, fill=(180, 180, 180))
        d.text((16, 28), f"{kid} {name} SUPPORT={support}", font=small, fill=(235, 235, 230))
        d.multiline_text((16, 50), ascii_frame(j, support), font=font, fill=(245, 245, 238), spacing=0)
        d.text((16, 445), "! trusted foot   ? probe only   @ pelvis/root   + chest   - ground", font=small, fill=(160, 160, 160))
        d.text((850, 445), f"{idx + 1:03d}/{len(frames):03d}", font=small, fill=(130, 130, 130))
        im.save(frame_dir / f"frame_{idx:04d}.png", compress_level=9)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", "24",
        "-i", str(frame_dir / "frame_%04d.png"),
        "-c:v", "libx264", "-preset", "veryslow", "-crf", str(M["motion_dungeon"]["compile"]["crf"]),
        "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        "-map_metadata", "-1", "-metadata", "comment=ASCII Kinesis abstract rig only",
        str(out),
    ], check=True)
    shutil.rmtree(frame_dir)

def make_spa(sheet, media):
    motion_text = (HERE / "motion.json").read_text(encoding="utf-8")
    b64 = base64.b64encode(media).decode("ascii")
    title = M["title"]
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;color-scheme:dark;background:#0b0b0d;color:#f2f2ed}}
*{{box-sizing:border-box}}
body{{margin:0;padding:16px;max-width:1280px;margin-inline:auto}}
nav{{display:flex;gap:8px;position:sticky;top:0;background:#0b0b0df2;padding:8px 0}}
button{{font:inherit;padding:10px 16px;border:1px solid #555;background:#16161a;color:inherit;border-radius:8px}}
button[aria-selected="true"]{{border-color:#ddd;background:#29292f}}
.panel{{display:none}}
.panel.active{{display:block}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08;tab-size:2}}
video{{width:100%;max-height:75vh;background:#000}}
</style>
</head>
<body>
<h1>{html.escape(title)}</h1>
<nav aria-label="Primary views">
<button data-view="ascii" aria-selected="true">ASCII</button>
<button data-view="json" aria-selected="false">JSON</button>
<button data-view="video" aria-selected="false">VIDEO</button>
</nav>
<section id="panel-ascii" class="panel active"><pre>{html.escape(sheet)}</pre></section>
<section id="panel-json" class="panel"><pre>{html.escape(motion_text)}</pre></section>
<section id="panel-video" class="panel"><video controls playsinline preload="metadata" src="data:video/mp4;base64,{b64}"></video></section>
<script>
const buttons=[...document.querySelectorAll('button[data-view]')];
for(const button of buttons) button.addEventListener('click',()=>{{
  for(const q of buttons) q.setAttribute('aria-selected',String(q===button));
  for(const panel of document.querySelectorAll('.panel')) panel.classList.remove('active');
  document.getElementById('panel-'+button.dataset.view).classList.add('active');
}});
</script>
</body>
</html>
'''

def main():
    sheet = contact_sheet()
    (HERE / "contact_sheet.txt").write_text(sheet, encoding="utf-8")
    frames = compile_frames()
    expected = int(M["motion_dungeon"]["compile"]["frame_count"])
    if len(frames) != expected:
        raise SystemExit(f"frame count {len(frames)} != {expected}")
    media_path = HERE / "_reconstructed.mp4"
    render_mp4(frames, media_path)
    media = media_path.read_bytes()
    sha = hashlib.sha256(media).hexdigest()
    if sha != M["motion_dungeon"]["compile"]["media_sha256"]:
        raise SystemExit(f"media sha mismatch {sha}")
    if len(media) != int(M["motion_dungeon"]["compile"]["media_bytes"]):
        raise SystemExit(f"media byte count mismatch {len(media)}")
    (HERE / MAN["spa_file"]).write_text(make_spa(sheet, media), encoding="utf-8")
    media_path.unlink()
    print(json.dumps({"ok": True, "frames": len(frames), "media_sha256": sha, "media_bytes": len(media), "spa": MAN["spa_file"]}, sort_keys=True))

if __name__ == "__main__":
    main()
