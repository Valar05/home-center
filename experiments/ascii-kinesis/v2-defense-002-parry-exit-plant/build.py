#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
OUT_MP4 = HERE / "parry-exit-plant.mp4"
OUT_HTML = HERE / "parry-exit-plant.motion.html"
CONTACT_SHEET = HERE / "contact-sheet.txt"
W, H = 48, 18
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
    dx = abs(x1 - x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1 - y0); sy = 1 if y0 < y1 else -1
    err = dx + dy; pts = []
    while True:
        pts.append((x0, y0))
        if x0 == x1 and y0 == y1: break
        e2 = 2 * err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy
    return pts


def line_glyph(a, b):
    dx = b[0] - a[0]; dy = b[1] - a[1]
    if abs(dx) > abs(dy) * 2: return "-"
    if abs(dy) > abs(dx) * 2: return "|"
    return "\\" if dx * dy > 0 else "/"


def support_feet(s):
    if s in {"BOTH", "BOTH_OFFSET"}: return {"foot_l", "foot_r"}
    if s in {"REAR_ONLY", "REAR_DOMINANT"}: return {"foot_r"}
    return set()


def render_ascii(key, joints_override=None):
    grid = [[" "] * W for _ in range(H)]
    joints = joints_override or {j: list(v) for j, v in key["joints"].items()}
    def put(x, y, ch):
        if 0 <= x < W and 0 <= y < H: grid[y][x] = ch
    for a, b in JOINT_LINKS:
        glyph = line_glyph(joints[a], joints[b])
        for x, y in bres(joints[a], joints[b])[1:-1]:
            if 0 <= y < H and 0 <= x < W and grid[y][x] == " ": put(x, y, glyph)
    for j, (x, y) in joints.items():
        put(x, y, "@" if j == "pelvis" else ("O" if j == "head" else "o"))
    for foot in support_feet(key["support_contact"]):
        x, y = joints[foot]; put(x, y + 1, "=")
    if key["contact_state"] == "DEFLECT_CONTACT":
        for x in range(31, 39): put(x, 6, "<")
        hx, hy = joints["hand_r"]; put(hx + 1, hy, "X")
    if key["guard_state"] in {"READY", "BRACED", "CONTACT", "BOUND", "HALF_BOUND"}:
        hx, hy = joints["hand_r"]; put(hx, hy, "G")
    return "\n".join("".join(row).rstrip() for row in grid)


def topology(k):
    return (k["support_contact"], k["contact_state"], k["root_state"], k["guard_state"], k["readiness"])


def connector(a, b, t=0.5):
    joints = {j: lerp(a["joints"][j], b["joints"][j], t) for j in a["joints"]}
    return render_ascii(a, joints)


def contact_sheet(data):
    chunks = []
    for k in data["keys"]:
        header = (
            f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | "
            f"support={k['support_contact']} | contact={k['contact_state']} | root={k['root_state']} | "
            f"guard={k['guard_state']} | ready={k['readiness']}\n"
            f"role: {k['causal_role']}\nroot: {k['motion_arc_root_note']}"
        )
        chunks.append(header + "\n" + render_ascii(k))
    return "\n\n".join(chunks)


def render_png(text: str, path: Path, label: str):
    image = Image.new("RGB", (640, 360), "black")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=18)
    draw.text((18, 10), label, fill="white", font=font)
    draw.multiline_text((18, 38), text, fill="white", font=font, spacing=1)
    image.save(path)


def build_video(data):
    semantic = []
    keys = data["keys"]
    for index, key in enumerate(keys):
        pose = render_ascii(key)
        for _ in range(HOLD[key["timing_class"]]):
            semantic.append((key["key_id"], pose))
        if index + 1 < len(keys) and topology(key) == topology(keys[index + 1]):
            semantic.append((key["key_id"] + "~" + keys[index + 1]["key_id"], connector(key, keys[index + 1])))
    sequence = semantic * int(data["compile"]["loop_repetitions"])
    with tempfile.TemporaryDirectory(prefix="ascii-kinesis-defense-v2-") as tmp:
        tmp = Path(tmp)
        for n, (label, text) in enumerate(sequence):
            render_png(text, tmp / f"frame-{n:04d}.png", label)
        cmd = [
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-framerate", str(data["compile"]["fps"]),
            "-i", str(tmp / "frame-%04d.png"),
            "-c:v", "libx264", "-preset", "veryslow", "-crf", "35",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT_MP4)
        ]
        subprocess.run(cmd, check=True)
    return semantic


def html_escape(text):
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_html(data, sheet, media_b64):
    pretty = json.dumps(data, indent=2, sort_keys=True)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Defense 002 — Parry Exit-Plant</title>
<style>
:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1100px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:76ch;line-height:1.45}}
</style></head><body>
<h1>Parry Exit-Plant / Guarded Re-entry</h1>
<p class="note">Copyright-safe abstract defense rig. The source sheet is evidence only and is not embedded. Motion Dungeon compiles the authored ASCII keys and explicit timing; causal joins hard-cut instead of inventing support, contact, root, guard, or readiness state.</p>
<nav role="tablist" aria-label="Primary views">
<button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button>
<button type="button" role="tab" data-view="json" aria-selected="false">JSON</button>
<button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button>
</nav>
<section id="ascii" role="tabpanel"><pre>{html_escape(sheet)}</pre></section>
<section id="json" role="tabpanel" hidden><pre>{html_escape(pretty)}</pre></section>
<section id="video" role="tabpanel" hidden><video controls loop playsinline preload="metadata"><source src="data:video/mp4;base64,{media_b64}" type="video/mp4"></video><p class="note">Authoritative media identity is this embedded MP4. It is rendered only from the independently authored ASCII rig coordinates, literal ASCII frames, explicit holds, and topology-safe connectors in JSON.</p></section>
<script>const tabs=[...document.querySelectorAll('button[data-view]')];const panels=[...document.querySelectorAll('section[role=tabpanel]')];for(const t of tabs)t.addEventListener('click',()=>{{for(const b of tabs)b.setAttribute('aria-selected',b===t?'true':'false');for(const p of panels)p.hidden=p.id!==t.dataset.view;}});</script>
</body></html>'''


def main():
    data = json.loads(MOTION.read_text(encoding="utf-8"))
    semantic = build_video(data)
    media = OUT_MP4.read_bytes()
    media_sha = hashlib.sha256(media).hexdigest()
    data["compile"]["media_sha256"] = media_sha
    data["compile"]["media_bytes"] = len(media)
    data["compile"]["semantic_frames_per_loop"] = len(semantic)
    data["compile"]["video_frames_total"] = len(semantic) * int(data["compile"]["loop_repetitions"])
    sheet = contact_sheet(data)
    sheet_sha = hashlib.sha256(sheet.encode("utf-8")).hexdigest()
    data["ascii_sheet_sha256"] = sheet_sha
    MOTION.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    CONTACT_SHEET.write_text(sheet + "\n", encoding="utf-8")
    OUT_HTML.write_text(build_html(data, sheet, base64.b64encode(media).decode("ascii")), encoding="utf-8")
    print(json.dumps({
        "media_sha256": media_sha,
        "media_bytes": len(media),
        "semantic_frames_per_loop": len(semantic),
        "video_frames_total": data["compile"]["video_frames_total"],
        "ascii_sheet_sha256": sheet_sha
    }, sort_keys=True))


if __name__ == "__main__":
    main()
