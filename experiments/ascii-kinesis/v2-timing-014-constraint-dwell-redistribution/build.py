#!/usr/bin/env python3
from __future__ import annotations

import base64
import hashlib
import html
import json
import shutil
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
MOTION = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
W = int(MOTION["rig"]["grid"]["columns"])
H = int(MOTION["rig"]["grid"]["rows"])
GROUND_Y = int(MOTION["rig"]["ground_y"])
WALL_X = int(MOTION["rig"]["constraint_wall_x"])
JOINT_KEYS = list(MOTION["rig"]["joints"])
OUT_W, OUT_H = map(int, MOTION["motion_dungeon"]["render_size"])
FPS = int(MOTION["motion_dungeon"]["fps"])
CELL_W, CELL_H = 8, 8
SCALE = 1

GLYPHS = {
    " ": ["00000"] * 7,
    "-": ["00000","00000","00000","11111","00000","00000","00000"],
    "|": ["00100","00100","00100","00100","00100","00100","00100"],
    "/": ["00001","00010","00100","01000","10000","00000","00000"],
    "\\": ["10000","01000","00100","00010","00001","00000","00000"],
    "+": ["00100","00100","11111","00100","00100","00000","00000"],
    "O": ["01110","10001","10001","10001","10001","10001","01110"],
    "@": ["01110","10001","10111","10101","10111","10000","01111"],
    "*": ["00100","10101","01110","11111","01110","10101","00100"],
    "_": ["00000","00000","00000","00000","00000","00000","11111"],
    "=": ["00000","00000","11111","00000","11111","00000","00000"],
    "#": ["01010","11111","01010","11111","01010","00000","00000"],
}

def line_cells(a, b):
    x0, y0 = a
    x1, y1 = b
    dx = abs(x1 - x0)
    sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0)
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    out = []
    while True:
        out.append((x0, y0))
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy
    return out

def seg_char(a, b):
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    if abs(dx) >= 2 * abs(dy):
        return "-"
    if abs(dy) >= 2 * abs(dx):
        return "|"
    return "\\" if dx * dy > 0 else "/"

def render_pose(pose):
    g = [[" "] * W for _ in range(H)]
    for x in range(W):
        g[GROUND_Y][x] = "="
    for y in range(2, GROUND_Y + 1):
        g[y][WALL_X] = "#"
    segs = [
        ("root","chest"), ("ls","le"), ("le","lh"), ("rs","re"), ("re","rh"),
        ("root","lk"), ("lk","lf"), ("root","rk"), ("rk","rf"),
    ]
    for akey, bkey in segs:
        a = tuple(round(v) for v in pose[akey])
        b = tuple(round(v) for v in pose[bkey])
        ch = seg_char(a, b)
        for x, y in line_cells(a, b)[1:-1]:
            if 0 <= x < W and 0 <= y < H and g[y][x] == " ":
                g[y][x] = ch
    marks = [
        ("head","O"), ("root","@"), ("chest","+"), ("ls","+"), ("rs","+"),
        ("le","+"), ("re","+"), ("lk","+"), ("rk","+"), ("lh","*"), ("rh","*"),
        ("lf","_"), ("rf","_"),
    ]
    for key, ch in marks:
        x, y = (round(v) for v in pose[key])
        if 0 <= x < W and 0 <= y < H:
            g[y][x] = ch
    return "\n".join("".join(row) for row in g)

def contact_sheet():
    lines = [
        "TIMING014 - CONSTRAINT DWELL REDISTRIBUTION",
        "WHEN A DEGREE OF FREEDOM CLOSES, MOVE TEMPORAL WEIGHT INTO DEFORMATION.",
        "",
        "KEY LEDGER",
    ]
    keys = MOTION["keys"]
    for key in keys:
        sc = key["support_contact"]
        lines.append(
            f'{key["key_id"]}  {key["causal_role"]:<20}  class={key["timing_class"]:<6}  '
            f'hold={key["exposure_ticks"]:<2}  provenance={key["timing_provenance"]}  '
            f'support={sc["support"]}  contact={sc["contact"]}'
        )
    lines += ["", "CONTACT SHEET", ""]
    panels = [(f'{k["key_id"]} {k["causal_role"]}', render_pose(k["pose_rig"])) for k in keys]
    for row in range(0, len(panels), 2):
        pair = panels[row:row+2]
        headers = [name[:W].ljust(W) for name, _ in pair]
        if len(pair) == 1:
            headers.append(" " * W)
        lines.append("  ".join(headers))
        bodies = [body.splitlines() for _, body in pair]
        if len(pair) == 1:
            bodies.append([" " * W] * H)
        for i in range(H):
            lines.append("  ".join(bodies[j][i] for j in range(2)))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"

def ease(t, curve):
    if curve == "ease_in":
        return t * t
    if curve == "ease_out":
        return 1 - (1 - t) * (1 - t)
    if curve == "smooth":
        return t * t * (3 - 2 * t)
    if curve == "snap":
        return t ** 0.55
    if curve == "compress":
        return 1 - (1 - t) ** 2.4
    if curve == "peel":
        return t * t * (3 - 2 * t)
    return t

def compile_ascii_frames():
    keys = MOTION["keys"]
    frames = []
    for i, key in enumerate(keys):
        if i:
            prev = keys[i - 1]
            n = int(key["transition_frames"])
            for j in range(1, n + 1):
                t = j / (n + 1)
                tt = ease(t, key["bridge_curve"])
                pose = {}
                for name in JOINT_KEYS:
                    a = prev["pose_rig"][name]
                    b = key["pose_rig"][name]
                    pose[name] = [a[0] + (b[0] - a[0]) * tt, a[1] + (b[1] - a[1]) * tt]
                frames.append(render_pose(pose))
        for _ in range(int(key["exposure_ticks"])):
            frames.append(render_pose(key["pose_rig"]))
    return frames

def raster_ascii(text):
    img = bytearray(OUT_W * OUT_H)
    xoff = (OUT_W - W * CELL_W) // 2
    yoff = (OUT_H - H * CELL_H) // 2
    rows = text.splitlines()
    for gy, row in enumerate(rows):
        for gx, ch in enumerate(row):
            pat = GLYPHS.get(ch, GLYPHS[" "])
            ox = xoff + gx * CELL_W + (CELL_W - 5 * SCALE) // 2
            oy = yoff + gy * CELL_H + (CELL_H - 7 * SCALE) // 2
            for py, bits in enumerate(pat):
                for px, bit in enumerate(bits):
                    if bit != "1":
                        continue
                    for sy in range(SCALE):
                        for sx in range(SCALE):
                            x = ox + px * SCALE + sx
                            y = oy + py * SCALE + sy
                            if 0 <= x < OUT_W and 0 <= y < OUT_H:
                                img[y * OUT_W + x] = 255
    return bytes(img)

def render_mp4(frames):
    frame_dir = HERE / ".motion-frames"
    if frame_dir.exists():
        shutil.rmtree(frame_dir)
    frame_dir.mkdir()
    for idx, text in enumerate(frames):
        p = frame_dir / f"{idx:04d}.pgm"
        p.write_bytes(f"P5\n{OUT_W} {OUT_H}\n255\n".encode("ascii") + raster_ascii(text))
    out = HERE / "constraint-dwell-redistribution.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS),
        "-i", str(frame_dir / "%04d.pgm"), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", "-crf", "42", str(out)
    ], check=True)
    shutil.rmtree(frame_dir)
    return out

def build_spa(ascii_text, mp4_path):
    data = base64.b64encode(mp4_path.read_bytes()).decode("ascii")
    motion_text = json.dumps(MOTION, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    css = """
    :root{color-scheme:dark;background:#080808;color:#f3f3f3;font-family:system-ui,sans-serif}
    body{margin:0;padding:1rem;max-width:100vw;overflow-x:hidden}
    nav{display:flex;gap:.5rem;position:sticky;top:0;background:#080808;padding:.5rem 0}
    button{font:inherit;padding:.55rem .9rem}
    section{display:none}
    section.active{display:block}
    pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
        font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08}
    video{max-width:100%;height:auto;border:1px solid currentColor}
    """
    script = """
    const tabs=[...document.querySelectorAll('[data-view]')];
    const panels=[...document.querySelectorAll('main section')];
    function show(v){panels.forEach(p=>p.classList.toggle('active',p.id===v));}
    tabs.forEach(b=>b.addEventListener('click',()=>show(b.dataset.view)));
    show('ascii');
    """
    page = (
        "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" "
        "content=\"width=device-width,initial-scale=1\"><title>Timing014 Constraint Dwell Redistribution</title>"
        f"<style>{css}</style></head><body>"
        "<nav><button data-view=\"ascii\">ASCII</button><button data-view=\"json\">JSON</button>"
        "<button data-view=\"video\">VIDEO</button></nav><main>"
        f"<section id=\"ascii\"><pre>{html.escape(ascii_text)}</pre></section>"
        f"<section id=\"json\"><pre>{html.escape(motion_text)}</pre></section>"
        f"<section id=\"video\"><video controls loop muted playsinline src=\"data:video/mp4;base64,{data}\"></video></section>"
        f"</main><script>{script}</script></body></html>"
    )
    out = HERE / "constraint-dwell-redistribution.motion.html"
    out.write_text(page, encoding="utf-8")
    return out

def main():
    ascii_text = contact_sheet()
    (HERE / "contact-sheet.txt").write_text(ascii_text, encoding="ascii")
    frames = compile_ascii_frames()
    if len(frames) != int(MOTION["motion_dungeon"]["frame_count"]):
        raise SystemExit(f"frame count mismatch: {len(frames)}")
    mp4 = render_mp4(frames)
    actual = hashlib.sha256(mp4.read_bytes()).hexdigest()
    expected = MOTION["media"]["sha256"]
    if actual != expected:
        raise SystemExit(f"media sha mismatch: expected {expected}, got {actual}")
    build_spa(ascii_text, mp4)
    print(json.dumps({"frames": len(frames), "media_sha256": actual, "ok": True}, sort_keys=True))

if __name__ == "__main__":
    main()
