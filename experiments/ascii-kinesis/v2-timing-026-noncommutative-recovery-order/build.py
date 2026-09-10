#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
CONTACT = HERE / "contact-sheet.txt"
SPA = HERE / "noncommutative-recovery-order.motion.html"
FPS = 24
SIZE = (720, 300)

def contact_text(motion):
    out=[]
    for k in motion["keys"]:
        out.append(
            f"{k['key_id']} {k['causal_role']} {k['timing_class']}/{k['exposure_ticks']}t "
            f"PROV={k['timing_provenance']} SUPPORT={k['support_contact']} "
            f"ROT={k['rotation_state']} CLR={k['clearance_state']}\n"
        )
        out.append(k["pose_rig"])
        out.append("-"*72+"\n")
    return "".join(out)

def render_mp4(motion, out_path):
    frames_dir = Path(tempfile.mkdtemp(prefix="ascii-kinesis-t026-"))
    try:
        font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
        if not font_path.exists():
            font_path = Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf")
        font = ImageFont.truetype(str(font_path), 13)
        footer = ImageFont.truetype(str(font_path), 10)
        idx=0
        for k in motion["keys"]:
            for _ in range(int(k["exposure_ticks"])):
                im=Image.new("RGB",SIZE,"white")
                d=ImageDraw.Draw(im)
                d.multiline_text((12,8),k["pose_rig"],fill="black",font=font,spacing=0)
                d.text(
                    (12,SIZE[1]-18),
                    f"Timing026 | {k['key_id']} | {k['causal_role']} | {k['timing_class']} | {k['rotation_state']}",
                    fill="black",font=footer
                )
                im.save(frames_dir/f"frame_{idx:04d}.png")
                idx += 1
        subprocess.run([
            "ffmpeg","-y","-loglevel","error","-framerate",str(FPS),
            "-i",str(frames_dir/"frame_%04d.png"),
            "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",
            "-crf","30","-map_metadata","-1",str(out_path)
        ],check=True)
        return idx
    finally:
        shutil.rmtree(frames_dir, ignore_errors=True)

def build_spa(motion, contact, video_bytes):
    compact = json.dumps(motion, ensure_ascii=False, sort_keys=True, separators=(",",":"))
    video_b64 = base64.b64encode(video_bytes).decode("ascii")
    css = """body{font-family:system-ui,sans-serif;margin:0;background:#fff;color:#111}
nav{position:sticky;top:0;background:#fff;border-bottom:1px solid #111;padding:8px}
button{font:inherit;margin-right:8px;padding:6px 12px}
section{display:none;padding:12px}section.active{display:block}
pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08}
video{max-width:100%;height:auto;border:1px solid #111}"""
    js = """const bs=[...document.querySelectorAll('[data-view]')],ss=[...document.querySelectorAll('section')];
function show(v){ss.forEach(s=>s.classList.toggle('active',s.id===v));}
bs.forEach(b=>b.onclick=()=>show(b.dataset.view));show('ascii');"""
    return f"""<!doctype html><meta charset="utf-8"><title>Timing026 — Noncommutative Recovery Order</title>
<style>{css}</style>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii"><pre>{html.escape(contact)}</pre></section>
<section id="json"><pre>{html.escape(compact)}</pre></section>
<section id="video"><video controls loop playsinline src="data:video/mp4;base64,{video_b64}"></video></section>
<script>{js}</script>"""

def main():
    motion=json.loads(MOTION.read_text(encoding="utf-8"))
    expected_contact=contact_text(motion)
    if CONTACT.exists() and CONTACT.read_text(encoding="utf-8") != expected_contact:
        raise SystemExit("contact-sheet.txt drifted from motion.json")
    CONTACT.write_text(expected_contact,encoding="utf-8")
    temp=HERE/".timing026-authoritative.mp4"
    count=render_mp4(motion,temp)
    b=temp.read_bytes()
    sha=hashlib.sha256(b).hexdigest()
    declared=motion.get("compile",{}).get("media",{}).get("sha256")
    if declared and declared != sha:
        raise SystemExit(f"media identity mismatch declared={declared} actual={sha}")
    if motion.get("compile",{}).get("frame_count") not in (None,count):
        raise SystemExit("frame_count mismatch")
    SPA.write_text(build_spa(motion,expected_contact,b),encoding="utf-8")
    print(json.dumps({"frames":count,"bytes":len(b),"sha256":sha,"spa":SPA.name},sort_keys=True))

if __name__=="__main__":
    main()
