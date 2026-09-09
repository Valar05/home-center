#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
CONTACT = HERE / "contact-sheet.txt"
SPA = HERE / "brake-yaw-latency-fanout.motion.html"
MP4 = HERE / ".timing023-authoritative.mp4"
FRAMES = Path(tempfile.mkdtemp(prefix="timing023-frames-"))

def contact_text(motion):
    out = [
        "TIMING023 - BRAKE/YAW LATENCY FANOUT\n",
        "Primitive: ORDERED_CAUSAL_FANOUT_WITH_RESIDUAL_MOTION\n",
        "Pocket rule: BRAKE OWNS SPEED; YAW OWNS DIRECTION. LET SUPPORT PAY THEM IN ORDER.\n",
        "=" * 88 + "\n",
    ]
    for k in motion["keys"]:
        r, v = k["root_transform"], k["root_velocity"]
        out.append(
            f"{k['key_id']} {k['causal_role']} {k['timing_class']}/{k['exposure_ticks']}t "
            f"PROV={k['timing_provenance']} SUPPORT={k['support_contact']} "
            f"SPEED={v['speed_norm']:.2f} YAW={k['pelvis_yaw_deg']:+03d} "
            f"ROOT=({r['x']:.2f},{r['y']:.2f})\n"
        )
        out.append(k["pose_rig"])
        out.append("-" * 88 + "\n")
    return "".join(out)

def root_map(motion, active_id):
    pts = [(float(k["root_transform"]["x"]), float(k["root_transform"]["y"])) for k in motion["keys"]]
    xmin, xmax = min(x for x, _ in pts), max(x for x, _ in pts)
    ymin, ymax = min(y for _, y in pts), max(y for _, y in pts)
    grid = [[" "] * 30 for _ in range(12)]
    for i, (x, y) in enumerate(pts):
        gx = round((x - xmin) / (xmax - xmin or 1) * 27) + 1
        gy = 10 - round((y - ymin) / (ymax - ymin or 1) * 9)
        if 0 <= gx < 30 and 0 <= gy < 12:
            grid[gy][gx] = "@" if motion["keys"][i]["key_id"] == active_id else "+"
    grid[0][0:17] = list("ROOT PATH (XY)   ")
    return "\n".join("".join(row).rstrip() for row in grid)

def render_video(motion):
    FRAMES.mkdir(parents=True, exist_ok=True)
    font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    if not font_path.exists():
        raise SystemExit("DejaVuSansMono.ttf required")
    font = ImageFont.truetype(str(font_path), 12)
    footer = ImageFont.truetype(str(font_path), 8)
    body = ImageFont.truetype(str(font_path), 18)
    n = 0
    for k in motion["keys"]:
        for _ in range(int(k["exposure_ticks"])):
            im = Image.new("RGB", (480, 270), "white")
            d = ImageDraw.Draw(im)
            d.multiline_text((12, 10), k["pose_rig"].rstrip(), fill="black", font=body, spacing=1)
            d.multiline_text((250, 10), root_map(motion, k["key_id"]), fill="black", font=font, spacing=0)
            v = float(k["root_velocity"]["speed_norm"])
            gauge_n = max(0, min(20, round(v * 20)))
            gauge = "[" + "#" * gauge_n + "." * (20 - gauge_n) + "]"
            clocks = k["channel_state"]
            d.text((12, 185), f"SPEED {gauge} {v:.2f}", fill="black", font=font)
            d.text((12, 205), f"BRAKE {clocks['BRAKE_CLOCK']}   YAW {clocks['YAW_CLOCK']}", fill="black", font=footer)
            d.text((12, 220), f"SUPPORT {k['support_contact']}   YAW_DEG {k['pelvis_yaw_deg']:+03d}", fill="black", font=footer)
            d.line((8, 235, 472, 235), fill="black", width=1)
            d.text((10, 245), f"Timing023 | {k['key_id']} | {k['causal_role']} | {k['timing_class']} | AUTHORED KEYS ONLY", fill="black", font=footer)
            im.save(FRAMES / f"frame_{n:04d}.png")
            n += 1
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-framerate", "24", "-i", str(FRAMES / "frame_%04d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-crf", "40", "-map_metadata", "-1", str(MP4)
    ], check=True)
    return MP4.read_bytes()

def spa_text(contact, motion_raw, mp4):
    css = (
        "body{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}"
        "nav{display:flex;gap:.5rem;padding:.75rem;position:sticky;top:0;background:#111}"
        "button{padding:.6rem 1rem}section{display:none;padding:1rem}section.active{display:block}"
        "pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}"
        "video{max-width:100%;height:auto}"
    )
    video_b64 = base64.b64encode(mp4).decode("ascii")
    ascii_b64 = base64.b64encode(gzip.compress(contact.encode("ascii"), compresslevel=9, mtime=0)).decode("ascii")
    json_b64 = base64.b64encode(gzip.compress(motion_raw.encode("ascii"), compresslevel=9, mtime=0)).decode("ascii")
    return (
        '<!doctype html>\n<html><head><meta charset="utf-8"><title>Timing023 - Brake-Yaw Latency Fanout</title><style>' + css + '</style></head>\n<body>\n<nav>\n'
        '<button data-view="ascii" onclick="show(\'ascii\')">ASCII</button>\n'
        '<button data-view="json" onclick="show(\'json\')">JSON</button>\n'
        '<button data-view="video" onclick="show(\'video\')">VIDEO</button>\n</nav>\n'
        '<section id="ascii" class="active"><pre id="ascii-pre"></pre></section>\n'
        '<section id="json"><pre id="json-pre"></pre></section>\n'
        '<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,' + video_b64 + '"></video></section>\n<script>\n'
        "function show(id){for(const s of document.querySelectorAll('section'))s.classList.remove('active');document.getElementById(id).classList.add('active');}\n"
        "async function inflate64(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream('gzip');return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}\n"
        "Promise.all([inflate64('" + ascii_b64 + "'),inflate64('" + json_b64 + "')]).then(([a,j])=>{document.getElementById('ascii-pre').textContent=a;document.getElementById('json-pre').textContent=j;});\n"
        "</script></body></html>\n"
    )

def main():
    motion = json.loads(MOTION.read_text(encoding="ascii"))
    contact = contact_text(motion)
    CONTACT.write_text(contact, encoding="ascii")
    mp4 = render_video(motion)
    got = hashlib.sha256(mp4).hexdigest()
    motion["compile"]["media"].update({"sha256": got, "bytes": len(mp4)})
    motion["revision"]["actual_render_sha256"] = got
    raw = json.dumps(motion, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    MOTION.write_text(raw, encoding="ascii")
    SPA.write_text(spa_text(contact, raw, mp4), encoding="utf-8")
    shutil.rmtree(FRAMES, ignore_errors=True)
    print(json.dumps({"experiment_id": motion["experiment_id"], "frames": motion["compile"]["media"]["frames"], "media_sha256": got, "bytes": len(mp4), "ok": True}, sort_keys=True))

if __name__ == "__main__":
    main()
