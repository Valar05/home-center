#!/usr/bin/env python3
from pathlib import Path
import base64, gzip, hashlib, html, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
motion = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))

def render_video():
    frames = HERE / ".frames"
    if frames.exists():
        shutil.rmtree(frames)
    frames.mkdir()
    candidates = [
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"),
    ]
    font_path = next((p for p in candidates if p.exists()), None)
    if not font_path:
        raise SystemExit("monospace font unavailable")
    font = ImageFont.truetype(str(font_path), 10)
    footer = ImageFont.truetype(str(font_path), 8)
    n = 0
    for key in motion["keys"]:
        for _ in range(int(key["exposure_ticks"])):
            im = Image.new("RGB", (480, 250), "white")
            d = ImageDraw.Draw(im)
            d.multiline_text((8, 6), key["pose_rig"], fill="black", font=font, spacing=0)
            d.text(
                (8, 228),
                f"{key['key_id']} | {key['causal_role']} | {key['timing_class']} {key['exposure_ticks']}t",
                fill="black",
                font=footer,
            )
            d.text(
                (8, 238),
                "fixed world datum | abstract ASCII operator + station only",
                fill="black",
                font=footer,
            )
            im.save(frames / f"frame_{n:04d}.png")
            n += 1
    out = HERE / "priority-preempt-checkpoint-resume.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-framerate", "24",
            "-i", str(frames / "frame_%04d.png"),
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-crf", "30",
            "-map_metadata", "-1",
            str(out),
        ],
        check=True,
    )
    return out, n

def contact_sheet():
    out = []
    for key in motion["keys"]:
        out.append(
            f"{key['key_id']} {key['causal_role']} "
            f"{key['timing_class']}/{key['exposure_ticks']}t "
            f"AUTH={key['authority_state']} "
            f"CHECKPOINT={key['progress_checkpoint']} "
            f"SUPPORT={key['support_contact']}\n"
        )
        out.append(key["pose_rig"])
        out.append("-" * 96 + "\n")
    return "".join(out)

video, count = render_video()
actual = hashlib.sha256(video.read_bytes()).hexdigest()
declared = motion["compile"]["media"]["sha256"]
if actual != declared:
    raise SystemExit(f"MEDIA_IDENTITY_MISMATCH declared={declared} actual={actual}")
if count != int(motion["compile"]["media"]["frames"]):
    raise SystemExit("FRAME_COUNT_MISMATCH")

sheet = contact_sheet()
(HERE / "contact-sheet.txt").write_text(sheet, encoding="utf-8")
motion_raw = (HERE / "motion.json").read_bytes()
motion_gz = base64.b64encode(gzip.compress(motion_raw, mtime=0)).decode("ascii")
b64 = base64.b64encode(video.read_bytes()).decode("ascii")

page = f"""<!doctype html>
<meta charset="utf-8">
<title>Timing018 priority preempt checkpoint resume</title>
<style>
body{{font-family:system-ui;margin:0}}
nav{{display:flex;gap:.5rem;padding:.75rem;position:sticky;top:0;background:white}}
button{{padding:.5rem .8rem}}
section{{display:none;padding:1rem}}
section.active{{display:block}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}
video{{max-width:100%;height:auto}}
</style>
<nav>
<button data-view="ascii">ASCII</button>
<button data-view="json">JSON</button>
<button data-view="video">VIDEO</button>
</nav>
<section id="ascii" class="active"><pre id="ascii-pre"></pre></section>
<section id="json"><pre id="json-pre"></pre></section>
<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section>
<script>
(async()=>{{
const raw=Uint8Array.from(atob("{motion_gz}"),c=>c.charCodeAt(0));
const text=await new Response(new Blob([raw]).stream().pipeThrough(new DecompressionStream("gzip"))).text();
const motion=JSON.parse(text);
const line="-".repeat(96)+"\\n";
document.getElementById("ascii-pre").textContent=motion.keys.map(k=>`${{k.key_id}} ${{k.causal_role}} ${{k.timing_class}}/${{k.exposure_ticks}}t AUTH=${{k.authority_state}} CHECKPOINT=${{k.progress_checkpoint}} SUPPORT=${{k.support_contact}}\\n${{k.pose_rig}}${{line}}`).join("");
document.getElementById("json-pre").textContent=JSON.stringify(motion,null,2);
}})();
const ids=["ascii","json","video"];
for(const b of document.querySelectorAll("button[data-view]")) b.onclick=()=>{{
  for(const id of ids) document.getElementById(id).classList.toggle("active",id===b.dataset.view);
}};
</script>
"""
(HERE / "priority-preempt-checkpoint-resume.motion.html").write_text(page, encoding="utf-8")
print(json.dumps({
    "schema":"ascii-kinesis.motion-dungeon-build",
    "ok":True,
    "media_sha256":actual,
    "frames":count,
    "contact_sheet_sha256":hashlib.sha256(sheet.encode("utf-8")).hexdigest(),
    "spa_sha256":hashlib.sha256(page.encode("utf-8")).hexdigest(),
}, sort_keys=True))
