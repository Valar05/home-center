#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, math, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((HERE / "manifest.json").read_text(encoding="utf-8"))
ASCII_TEXT = (HERE / "contact-sheet.txt").read_text(encoding="utf-8")
W, H = MOTION["abstract_rig"]["grid"]
FPS = int(MOTION["compile"]["fps"])
IMG_W, IMG_H = map(int, MOTION["compile"]["frame_size"])
KEYS = MOTION["keys"]
ENTRY = MOTION["experiment_id"]
SLUG = ENTRY.removeprefix("v2-contact-030-")

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
]
FONT_PATH = next((p for p in FONT_CANDIDATES if Path(p).exists()), None)
if not FONT_PATH:
    raise SystemExit("build requires a system monospace TrueType font")
FONT = ImageFont.truetype(FONT_PATH, 15)
FOOTER_FONT = ImageFont.truetype(FONT_PATH, 10)

def bres(grid, x0, y0, x1, y1, ch):
    x0, y0, x1, y1 = map(lambda v: int(round(v)), (x0, y0, x1, y1))
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

def draw_body(grid, label, body):
    rx, ry = body["root"]
    hx = rx + body["head_offset"][0]; hy = ry + body["head_offset"][1]
    so = body.get("shoulder_offset", [0, -4])
    shoulder = (rx + so[0], ry + so[1])
    torso_ch = "|" if abs(so[0]) < 1 else ("/" if so[0] < 0 else "\\")
    bres(grid, rx, ry, shoulder[0], shoulder[1], torso_ch)
    for fx, fy in body["feet"]:
        bres(grid, rx, ry, fx, fy, "/" if fx < rx else "\\")
        if 0 <= round(fx) < W and 0 <= round(fy) < H:
            grid[round(fy)][round(fx)] = "^"
    for mx, my in body["hands"]:
        bres(grid, shoulder[0], shoulder[1], mx, my, "/" if mx < shoulder[0] else "\\")
        if 0 <= round(mx) < W and 0 <= round(my) < H:
            grid[round(my)][round(mx)] = "h"
    if 0 <= round(rx) < W and 0 <= round(ry) < H:
        grid[round(ry)][round(rx)] = "@"
    if 0 <= round(hx) < W and 0 <= round(hy) < H:
        grid[round(hy)][round(hx)] = "O"
    lx = int(round(hx - 2 if label == "A" else hx + 2))
    if 0 <= lx < W and 0 <= round(hy) < H:
        grid[round(hy)][lx] = label

def render_grid(state):
    grid = [[" "] * W for _ in range(H)]
    for x in range(4, W - 4):
        if x % 2 == 0:
            grid[23][x] = "."
    draw_body(grid, "A", state["A"])
    draw_body(grid, "B", state["B"])
    rel = state.get("relationship_frame", {})
    rstate = rel.get("state")
    if rstate in ("LATENT", "LOCKED"):
        x, y = map(lambda v: int(round(v)), rel["pos"])
        if 0 <= x < W and 0 <= y < H:
            grid[y][x] = "R" if rstate == "LOCKED" else "r"
        if rstate == "LOCKED":
            if x - 1 >= 0: grid[y][x - 1] = "*"
            if x + 1 < W: grid[y][x + 1] = "*"
    elif rstate == "RETIRED":
        x, y = map(lambda v: int(round(v)), rel["pos"])
        for i, c in enumerate("R//"):
            if 0 <= x + i < W and 0 <= y < H:
                grid[y][x + i] = c
    hdr = f"{state['key_id']} {state['name']}  {state['authority']}  CONTACT={state['contact_state']}"
    for i, c in enumerate(hdr[:W-2], 1):
        grid[1][i] = c
    force = state.get("force", "")
    if force:
        txt = f"FORCE {force}"
        for i, c in enumerate(txt[:W-4], 2):
            grid[3][i] = c
    sup = f"A_SUPPORT={state['A']['support']}   B_SUPPORT={state['B']['support']}"
    for i, c in enumerate(sup[:W-2], 1):
        grid[24][i] = c
    return "\n".join("".join(row).rstrip() for row in grid)

def ease(t):
    return t * t * (3 - 2 * t)

def arc(t, amp):
    return amp * 4 * t * (1 - t)

def interp_point(p0, p1, t, y_arc=0):
    u = ease(t)
    return [p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u - arc(t, y_arc)]

def interp_body(b0, b1, t, amp=0):
    return {
        "root": interp_point(b0["root"], b1["root"], t, amp),
        "feet": [interp_point(a, b, t, amp * 0.15) for a, b in zip(b0["feet"], b1["feet"])],
        "hands": [interp_point(a, b, t, amp * 0.55) for a, b in zip(b0["hands"], b1["hands"])],
        "head_offset": interp_point(b0["head_offset"], b1["head_offset"], t, 0),
        "shoulder_offset": interp_point(b0.get("shoulder_offset", [0,-4]), b1.get("shoulder_offset", [0,-4]), t, 0),
        "support": b0["support"] if t < 0.72 else b1["support"],
    }

def compile_ascii_frames():
    frames = []
    for i, key in enumerate(KEYS):
        frames.extend([render_grid(key)] * int(key["hold_frames"]))
        if i == len(KEYS) - 1:
            continue
        nxt = KEYS[i+1]
        n = int(key.get("connective_frames_to_next", 0))
        ampA = float(key.get("connective_arc_amp_A", 0))
        ampB = float(key.get("connective_arc_amp_B", 0))
        for j in range(1, n + 1):
            t = j / (n + 1)
            state = {
                "key_id": f"{key['key_id']}~{nxt['key_id']}",
                "name": "CONNECTIVE_ARC",
                "authority": key["authority"],
                "contact_state": key["contact_state"],
                "relationship_frame": key["relationship_frame"],
                "force": key.get("force", ""),
                "A": interp_body(key["A"], nxt["A"], t, ampA),
                "B": interp_body(key["B"], nxt["B"], t, ampB),
            }
            frames.append(render_grid(state))
    return frames

def render_pngs(frames, out_dir):
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)
    for idx, text in enumerate(frames):
        im = Image.new("RGB", (IMG_W, IMG_H), (8, 10, 12))
        d = ImageDraw.Draw(im)
        d.multiline_text((16, 12), text, font=FONT, fill=(235, 238, 230), spacing=2)
        d.text((16, 376), f"{ENTRY}  frame {idx+1:02d}/{len(frames)}",
               font=FOOTER_FONT, fill=(130, 135, 132))
        im.save(out_dir / f"frame-{idx:03d}.png")

def build_video(frames_dir, out_mp4):
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
        "-i", str(frames_dir / "frame-%03d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "25",
        "-preset", "veryfast", "-movflags", "+faststart", str(out_mp4)
    ], check=True)

def build_spa(mp4_bytes):
    motion_text = (HERE / "motion.json").read_text(encoding="utf-8")
    video64 = base64.b64encode(mp4_bytes).decode("ascii")
    css = """
    :root{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;background:#0b0d0f;color:#eef1ec}
    body{margin:0;padding:16px}nav{display:flex;gap:8px;position:sticky;top:0;background:#0b0d0f;padding-bottom:12px}
    button{font:inherit;padding:8px 12px;background:#171b20;color:#eef1ec;border:1px solid #58606a}
    [data-panel]{display:none}[data-panel].active{display:block}
    pre{font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.2;border:1px solid #343a40;padding:12px;background:#07090b}
    video{max-width:100%;height:auto;border:1px solid #343a40;background:#000}
    """
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>{html.escape(ENTRY)}</title><style>{css}</style></head>
<body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section data-panel="ascii" class="active"><pre>{html.escape(ASCII_TEXT)}</pre></section>
<section data-panel="json"><pre>{html.escape(motion_text)}</pre></section>
<section data-panel="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{video64}"></video></section>
<script>
const buttons=[...document.querySelectorAll('[data-view]')],panels=[...document.querySelectorAll('[data-panel]')];
buttons.forEach(b=>b.onclick=()=>{{panels.forEach(p=>p.classList.toggle('active',p.dataset.panel===b.dataset.view));}});
</script></body></html>"""

def main():
    work = HERE / ".motion-build"
    frames_dir = work / "frames"
    work.mkdir(exist_ok=True)
    frames = compile_ascii_frames()
    expected_frames = int(MOTION["compile"]["frame_count"])
    if len(frames) != expected_frames:
        raise SystemExit(f"frame count mismatch {len(frames)} != {expected_frames}")
    render_pngs(frames, frames_dir)
    mp4 = work / "motion.mp4"
    build_video(frames_dir, mp4)
    media = mp4.read_bytes()
    sha = hashlib.sha256(media).hexdigest()
    expected = MANIFEST["media_sha256"]
    if sha != expected:
        raise SystemExit(f"media identity mismatch {sha} != {expected}")
    spa = build_spa(media)
    (HERE / f"{SLUG}.motion.html").write_text(spa, encoding="utf-8")
    print(json.dumps({"ok": True, "frames": len(frames), "bytes": len(media), "sha256": sha}, sort_keys=True))

if __name__ == "__main__":
    main()
