#!/usr/bin/env python3
"""Deterministic Motion Dungeon builder for ASCII Kinesis V2 Video Motion 001.

Input authority: motion.json only. Source footage is never read, decoded, or embedded.
The builder renders an abstract ASCII rig to RGB frames, compiles H.264 MP4,
and emits a self-contained three-tab SPA with the MP4 embedded as a data URI.
"""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOTION_PATH = ROOT / "motion.json"
CONTACT_PATH = ROOT / "contact_sheet.txt"
MP4_PATH = ROOT / "motion.mp4"
HTML_PATH = ROOT / "black-pirate-compression-release.motion.html"

FONT = {
    " ": ["00000"] * 7,
    "O": ["01110","10001","10001","10001","10001","10001","01110"],
    "A": ["01110","10001","10001","11111","10001","10001","10001"],
    "B": ["11110","10001","10001","11110","10001","10001","11110"],
    "@": ["01110","10001","10111","10101","10111","10000","01111"],
    "|": ["00100","00100","00100","00100","00100","00100","00100"],
    "/": ["00001","00010","00010","00100","01000","01000","10000"],
    "\\": ["10000","01000","01000","00100","00010","00010","00001"],
    "=": ["00000","00000","11111","00000","11111","00000","00000"],
    "-": ["00000","00000","00000","11111","00000","00000","00000"],
    "_": ["00000","00000","00000","00000","00000","00000","11111"],
    "?": ["01110","10001","00010","00100","00100","00000","00100"],
    "X": ["10001","01010","00100","00100","00100","01010","10001"],
    "<": ["00010","00100","01000","10000","01000","00100","00010"],
    ">": ["01000","00100","00010","00001","00010","00100","01000"],
}

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def clamp(v: int, lo: int, hi: int) -> int:
    return lo if v < lo else hi if v > hi else v

def put(grid: list[list[str]], x: int, y: int, ch: str) -> None:
    if 0 <= y < len(grid) and 0 <= x < len(grid[0]):
        existing = grid[y][x]
        if existing != " " and ch not in {"_", "="} and existing != ch:
            grid[y][x] = "X"
        elif existing == " " or ch not in {"_", "="}:
            grid[y][x] = ch

def line(grid: list[list[str]], x0: int, y0: int, x1: int, y1: int, horiz: str = "=", diag_fwd: str = "/", diag_back: str = "\\") -> None:
    dx = x1 - x0
    dy = y1 - y0
    steps = max(abs(dx), abs(dy), 1)
    for i in range(steps + 1):
        t = i / steps
        x = round(x0 + dx * t)
        y = round(y0 + dy * t)
        if abs(dx) >= abs(dy) * 2:
            ch = horiz
        elif dx * dy < 0:
            ch = diag_fwd
        else:
            ch = diag_back
        put(grid, x, y, ch)

def interp_point(a: list[int], b: list[int], t: float) -> tuple[int, int]:
    return (round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t))

def render_semantic_frame(motion: dict, key: dict, next_key: dict | None, t: float) -> list[str]:
    """Render geometry between authored keys while retaining prior-key semantics."""
    cols, rows = motion["motion_dungeon"]["render_grid"]
    grid = [[" " for _ in range(cols)] for _ in range(rows)]
    ground_y = rows - 3
    for x in range(cols):
        put(grid, x, ground_y, "_")
    if next_key is None:
        next_key = key
        t = 0.0
    actors = []
    for label, field in (("A", "actor_a"), ("B", "actor_b")):
        root = interp_point(key[field]["root"], next_key[field]["root"], t)
        head = interp_point(key[field]["head"], next_key[field]["head"], t)
        actors.append((label, root, head))
    if key.get("prop_relation") == "bridged_unresolved":
        a_head = actors[0][2]
        b_head = actors[1][2]
        line(grid, a_head[0] + 2, a_head[1] + 1, b_head[0] - 2, b_head[1] + 1, horiz="=")
    for label, root, head in actors:
        hx, hy = head
        rx, ry = root
        put(grid, hx, hy, "O")
        put(grid, hx + 1, hy, label)
        line(grid, hx, hy + 1, rx, ry - 1, horiz="|", diag_fwd="/", diag_back="\\")
        put(grid, rx, ry, "@")
        arm_y = min(hy + 2, ry - 1)
        put(grid, hx - 1, arm_y, "/")
        put(grid, hx + 1, arm_y, "\\")
        put(grid, rx - 1, ry + 1, "/")
        put(grid, rx + 1, ry + 1, "?")
        put(grid, rx - 2, ry + 2, "/")
        put(grid, rx + 2, ry + 2, "?")
    bx, by = actors[1][1]
    if key["key_id"] in {"K1", "K2", "K3", "K4", "K5"}:
        for off in range(2, 6):
            put(grid, bx + off, by, "<")
    if key["key_id"] == "K6":
        bhx, bhy = actors[1][2]
        for off in range(2, 8):
            put(grid, bhx + off, bhy + 1, "-")
        put(grid, bhx + 8, bhy + 1, ">")
    return ["".join(row) for row in grid]

def bitmap_rgb(lines: list[str], cell_w: int, cell_h: int, scale: int) -> bytes:
    rows = len(lines)
    cols = len(lines[0]) if rows else 0
    width = cols * cell_w * scale
    height = rows * cell_h * scale
    out = bytearray(width * height * 3)
    for y in range(height):
        base = y * width * 3
        for x in range(width):
            p = base + x * 3
            out[p:p+3] = b"\x08\x08\x08"
    for gy, row in enumerate(lines):
        for gx, ch in enumerate(row):
            pattern = FONT.get(ch, FONT["?"])
            for py, bits in enumerate(pattern):
                for px, bit in enumerate(bits):
                    if bit != "1":
                        continue
                    ox = (gx * cell_w + px) * scale
                    oy = (gy * cell_h + py) * scale
                    for sy in range(scale):
                        y = oy + sy
                        if y >= height:
                            continue
                        for sx in range(scale):
                            x = ox + sx
                            if x >= width:
                                continue
                            p = (y * width + x) * 3
                            out[p:p+3] = b"\xf2\xf2\xf2"
    return bytes(out)

def compile_frames(motion: dict) -> list[bytes]:
    fps = int(motion["timing"]["compile_fps"])
    keys = motion["keys"]
    start_t = float(keys[0]["source_time_s"])
    target_frames = [round((float(k["source_time_s"]) - start_t) * fps) for k in keys]
    frame_specs: list[tuple[dict, dict | None, float]] = []
    for i, key in enumerate(keys[:-1]):
        nxt = keys[i + 1]
        span = max(1, target_frames[i + 1] - target_frames[i])
        hold = clamp(int(key.get("compile_hold_frames", 1)), 1, span)
        if key.get("causal_boundary_to_next"):
            hold = span
        for _ in range(hold):
            frame_specs.append((key, nxt, 0.0))
        remaining = span - hold
        for j in range(remaining):
            t = (j + 1) / (remaining + 1)
            frame_specs.append((key, nxt, t))
    final_key = keys[-1]
    for _ in range(int(motion["motion_dungeon"].get("final_hold_frames", 12))):
        frame_specs.append((final_key, None, 0.0))
    cell_w, cell_h = motion["motion_dungeon"]["cell_pixels"]
    scale = int(motion["motion_dungeon"]["scale"])
    return [bitmap_rgb(render_semantic_frame(motion, key, nxt, t), cell_w, cell_h, scale) for key, nxt, t in frame_specs]

def compile_mp4(motion: dict, frames: list[bytes]) -> tuple[bytes, str]:
    cols, rows = motion["motion_dungeon"]["render_grid"]
    cell_w, cell_h = motion["motion_dungeon"]["cell_pixels"]
    scale = int(motion["motion_dungeon"]["scale"])
    width = cols * cell_w * scale
    height = rows * cell_h * scale
    fps = int(motion["timing"]["compile_fps"])
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s:v", f"{width}x{height}", "-r", str(fps), "-i", "-",
        "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-threads", "1",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-map_metadata", "-1",
        "-metadata", "creation_time=1970-01-01T00:00:00Z", str(MP4_PATH),
    ]
    proc = subprocess.run(cmd, input=b"".join(frames), stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.stderr.decode("utf-8", "replace"))
    data = MP4_PATH.read_bytes()
    ffmpeg_version = subprocess.check_output(["ffmpeg", "-version"], text=True).splitlines()[0]
    return data, ffmpeg_version

def html_escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def build_html(motion: dict, manifest: dict, contact: str, mp4: bytes) -> str:
    audit = json.dumps({"motion": motion, "manifest": manifest}, indent=2, ensure_ascii=False)
    b64 = base64.b64encode(mp4).decode("ascii")
    return f'''<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 · Video Motion 001</title>
<style>
:root{{color-scheme:dark;background:#0a0a0a;color:#f2f2f2;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}}*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;background:#0a0a0a;color:#f2f2f2}}header{{position:sticky;top:0;background:#111;border-bottom:1px solid #444;padding:.75rem;z-index:2}}nav{{display:flex;gap:.5rem}}button{{font:inherit;padding:.6rem .9rem;background:#1c1c1c;color:#eee;border:1px solid #555;border-radius:.35rem;cursor:pointer}}button[aria-selected="true"]{{background:#eee;color:#111}}main{{padding:1rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;tab-size:2;overflow:auto;line-height:1.15;margin:0;padding:1rem;border:1px solid #333;background:#0d0d0d;max-width:100%}}video{{display:block;width:min(100%,960px);height:auto;border:1px solid #333;background:#000}}.small{{max-width:70rem;margin:0 0 1rem 0;line-height:1.5}}
</style></head><body>
<header><nav aria-label="Primary views"><button type="button" data-view="ascii" aria-selected="true">ASCII</button><button type="button" data-view="json" aria-selected="false">JSON</button><button type="button" data-view="video" aria-selected="false">VIDEO</button></nav></header>
<main><section id="view-ascii"><p class="small">Literal selectable/copyable contact sheet. No source pixels are present.</p><pre id="ascii-sheet">{html_escape(contact)}</pre></section><section id="view-json" hidden><p class="small">Motion, provenance, rights, compatibility, manifest, and media identity.</p><pre id="json-audit">{html_escape(audit)}</pre></section><section id="view-video" hidden><p class="small">Motion Dungeon MP4 rendered solely from the abstract ASCII rig and structured timing.</p><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{b64}"></video></section></main>
<script>const buttons=[...document.querySelectorAll('nav button')];const sections={{ascii:document.getElementById('view-ascii'),json:document.getElementById('view-json'),video:document.getElementById('view-video')}};for(const b of buttons){{b.addEventListener('click',()=>{{for(const x of buttons)x.setAttribute('aria-selected',String(x===b));for(const [name,s] of Object.entries(sections))s.hidden=name!==b.dataset.view;}})}}</script></body></html>'''

def main() -> None:
    motion = json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    contact = CONTACT_PATH.read_text(encoding="utf-8")
    frames = compile_frames(motion)
    mp4, ffmpeg_version = compile_mp4(motion, frames)
    media_hash = sha256_bytes(mp4)
    motion["media"]["sha256"] = media_hash
    motion["media"]["bytes"] = len(mp4)
    motion["media"]["frame_count"] = len(frames)
    motion["media"]["compile_fps"] = int(motion["timing"]["compile_fps"])
    motion["media"]["ffmpeg_version"] = ffmpeg_version
    motion["status"] = "RENDERED_PENDING_REPO_VERIFICATION"
    MOTION_PATH.write_text(json.dumps(motion, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    manifest = {
        "schema": "ascii-kinesis.v2-manifest", "format_version": 2, "entry": motion["experiment_id"], "lane": "video-motion",
        "primary_tabs": ["ASCII", "JSON", "VIDEO"], "ascii_literal_text": True, "video_required": True,
        "video_source": "abstract_ascii_rig_only", "source_art_embedded": False, "backward_compatible": True, "offline_spa": True,
        "source": {"title": motion["source"]["title"], "url": motion["source"]["page_url"], "rights_status": motion["source"]["rights_status"], "source_sha1": motion["source"]["source_sha1"], "selected_segment_s": motion["source"]["selected_segment_s"]},
        "media": {"mime": "video/mp4", "sha256": media_hash, "bytes": len(mp4), "frame_count": len(frames), "embedded_in_spa": True, "source_pixels_used": False},
        "builder": {"path": "build_motion.py", "method": "Motion Dungeon", "input": "motion.json + contact_sheet.txt", "source_video_dependency": False, "ffmpeg_version": ffmpeg_version},
        "files": ["contact_sheet.txt", "motion.json", "build_motion.py", "manifest.json", "receipt.json", "black-pirate-compression-release.motion.html"],
        "compatibility": {"v1_untouched": True, "v2_three_tab_read_path": True, "network_required": False},
        "correction_hooks": motion["correction_hooks"], "status": "RENDERED_PENDING_REPO_VERIFICATION"
    }
    (ROOT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    html = build_html(motion, manifest, contact, mp4)
    HTML_PATH.write_text(html, encoding="utf-8")
    receipt = {
        "schema": "ascii-kinesis.v2-receipt", "entry": motion["experiment_id"], "source": motion["source"], "rights_status": motion["source"]["rights_status"],
        "observed_key_times_s": {k["key_id"]: k["source_time_s"] for k in motion["keys"]}, "inferred": ["connective geometry", "compile hold allocation"],
        "media_sha256": media_hash, "media_bytes": len(mp4), "media_frame_count": len(frames), "media_source": "abstract_ascii_rig_only",
        "repo_path": f"experiments/ascii-kinesis/{motion['experiment_id']}/", "repo_readback_verified": False, "contract_test_exact_readback": False,
        "status": "RENDERED_PENDING_REPO_VERIFICATION", "correction_hooks": motion["correction_hooks"]
    }
    (ROOT / "receipt.json").write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"entry": motion["experiment_id"], "frames": len(frames), "mp4_bytes": len(mp4), "mp4_sha256": media_hash, "html_bytes": len(html.encode("utf-8")), "ffmpeg": ffmpeg_version}, sort_keys=True))

if __name__ == "__main__":
    main()
