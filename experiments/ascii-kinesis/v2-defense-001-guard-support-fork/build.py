#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
MANIFEST = HERE / "manifest.json"
OUT_MP4 = HERE / "guard-support-fork.mp4"
OUT_HTML = HERE / "guard-support-fork.motion.html"
OUT_ASCII = HERE / "contact-sheet.txt"
W, H = 48, 20
HOLD = {"ONES": 1, "TWOS": 2, "FOURS": 4}
JOINT_LINKS = [
    ("head", "shoulder_l"), ("head", "shoulder_r"),
    ("shoulder_l", "shoulder_r"), ("shoulder_l", "hand_l"),
    ("shoulder_r", "hand_r"), ("shoulder_l", "pelvis"),
    ("shoulder_r", "pelvis"), ("pelvis", "knee_l"),
    ("pelvis", "knee_r"), ("knee_l", "foot_l"), ("knee_r", "foot_r")
]

def lerp(a, b, t):
    return [round(a[0] + (b[0] - a[0]) * t), round(a[1] + (b[1] - a[1]) * t)]

def bres(a, b):
    x0, y0 = a; x1, y1 = b
    dx = abs(x1-x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1-y0); sy = 1 if y0 < y1 else -1
    err = dx + dy; out = []
    while True:
        out.append((x0, y0))
        if x0 == x1 and y0 == y1: break
        e2 = 2 * err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy
    return out

def line_glyph(a, b):
    dx = b[0] - a[0]; dy = b[1] - a[1]
    if abs(dx) > abs(dy) * 2: return "-"
    if abs(dy) > abs(dx) * 2: return "|"
    return "\\" if dx * dy > 0 else "/"

def support_feet(state):
    return {"BOTH": ("foot_l", "foot_r"), "REAR_ONLY": ("foot_l",), "FRONT_ONLY": ("foot_r",), "NONE": ()}[state]

def render_ascii(key, pose_override=None):
    g = [[" "] * W for _ in range(H)]
    pose = {j: list(v) for j, v in (pose_override or key["pose_rig"]).items()}
    def put(x, y, ch):
        if 0 <= x < W and 0 <= y < H: g[y][x] = ch
    for a, b in JOINT_LINKS:
        glyph = line_glyph(pose[a], pose[b])
        for x, y in bres(pose[a], pose[b])[1:-1]:
            if g[y][x] == " ": put(x, y, glyph)
    for j, (x, y) in pose.items():
        put(x, y, "@" if j == "pelvis" else ("O" if j == "head" else "o"))
    for foot in support_feet(key["support_contact"]):
        x, y = pose[foot]; put(x, y + 1, "=")
    if key.get("incoming"):
        for x in range(34, 43): put(x, 8, "<")
    if key.get("contact_marker"):
        x, y = key["contact_marker"]; put(x, y, "!")
    return "\n".join("".join(row).rstrip() for row in g)

def topology(key):
    return (key["support_contact"], key["contact_state"], key["root_state"])

def connector(a, b):
    pose = {j: lerp(a["pose_rig"][j], b["pose_rig"][j], 0.5) for j in a["pose_rig"]}
    return render_ascii(a, pose)

def contact_sheet(data):
    blocks = []
    for k in data["keys"]:
        hdr = (f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | "
               f"support={k['support_contact']} | contact={k['contact_state']} | root={k['root_state']}")
        blocks.append(hdr + "\n" + render_ascii(k))
    return "\n\n".join(blocks) + "\n"

def render_png(text, path, label):
    im = Image.new("RGB", (640, 360), "black")
    draw = ImageDraw.Draw(im)
    font = ImageFont.load_default(size=18)
    draw.text((18, 12), label, fill="white", font=font)
    draw.multiline_text((18, 42), text, fill="white", font=font, spacing=1)
    im.save(path)

def build_video(data):
    semantic = []
    keys = data["keys"]
    for i, k in enumerate(keys):
        pose = render_ascii(k)
        semantic.extend([(k["key_id"], pose)] * HOLD[k["timing_class"]])
        if i + 1 < len(keys) and topology(k) == topology(keys[i+1]):
            semantic.append((k["key_id"] + "~" + keys[i+1]["key_id"], connector(k, keys[i+1])))
    seq = semantic * int(data["compile"]["loop_repetitions"])
    with tempfile.TemporaryDirectory(prefix="ascii-kinesis-defense-v2-") as td:
        td = Path(td)
        for n, (label, text) in enumerate(seq):
            render_png(text, td / f"frame-{n:04d}.png", label)
        cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
               "-framerate", str(data["compile"]["fps"]), "-i", str(td / "frame-%04d.png"),
               "-c:v", "libx264", "-preset", "veryslow", "-crf", "38",
               "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-metadata", "creation_time=1970-01-01T00:00:00Z",
               str(OUT_MP4)]
        subprocess.run(cmd, check=True)
    return semantic

def build_html(data, sheet, media_b64):
    pretty = json.dumps(data, indent=2, sort_keys=True)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Defense 001 — Guard / Support Authority Fork</title>
<style>
:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1100px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:76ch;line-height:1.45}}
</style></head><body>
<h1>Guard / Support Authority Fork</h1>
<p class="note">Copyright-safe abstract defensive rig. The source sheet is evidence only and is not embedded. The specimen tests one transferable rule: guard recoil remains a defense while support still owns the root; the hit reaction begins when support authority breaks, and recovery begins at the first trustworthy plant.</p>
<nav role="tablist" aria-label="Primary views">
<button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button>
<button type="button" role="tab" data-view="json" aria-selected="false">JSON</button>
<button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button>
</nav>
<section id="ascii" role="tabpanel"><pre>{html.escape(sheet)}</pre></section>
<section id="json" role="tabpanel" hidden><pre>{html.escape(pretty)}</pre></section>
<section id="video" role="tabpanel" hidden><video controls loop playsinline preload="metadata"><source src="data:video/mp4;base64,{media_b64}" type="video/mp4"></video><p class="note">MP4 compiled only from the abstract rig coordinates, explicit ONES/TWOS/FOURS holds, generated ASCII frames, and topology-safe connectors recorded in JSON. No source art enters the media.</p></section>
<script>const tabs=[...document.querySelectorAll('button[data-view]')];const panels=[...document.querySelectorAll('section[role=tabpanel]')];for(const t of tabs)t.addEventListener('click',()=>{{for(const b of tabs)b.setAttribute('aria-selected',b===t?'true':'false');for(const p of panels)p.hidden=p.id!==t.dataset.view;}});</script>
</body></html>'''

def main():
    data = json.loads(MOTION.read_text(encoding="utf-8"))
    semantic = build_video(data)
    media = OUT_MP4.read_bytes()
    sha = hashlib.sha256(media).hexdigest()
    data["compile"]["media_sha256"] = sha
    data["compile"]["media_bytes"] = len(media)
    data["compile"]["semantic_frames_per_loop"] = len(semantic)
    data["compile"]["video_frames_total"] = len(semantic) * int(data["compile"]["loop_repetitions"])
    sheet = contact_sheet(data)
    data["ascii_sheet_sha256"] = hashlib.sha256(sheet.encode("utf-8")).hexdigest()
    MOTION.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    OUT_ASCII.write_text(sheet, encoding="utf-8")
    OUT_HTML.write_text(build_html(data, sheet, base64.b64encode(media).decode("ascii")), encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    manifest["media_sha256"] = sha
    manifest["media_bytes"] = len(media)
    manifest["ascii_sheet_sha256"] = data["ascii_sheet_sha256"]
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"media_sha256": sha, "media_bytes": len(media), "semantic_frames_per_loop": len(semantic), "video_frames_total": data["compile"]["video_frames_total"], "ascii_sheet_sha256": data["ascii_sheet_sha256"]}, sort_keys=True))

if __name__ == "__main__":
    main()
