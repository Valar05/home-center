#!/usr/bin/env python3
from pathlib import Path
import base64, hashlib, html, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
motion=json.loads((HERE/"motion.json").read_text(encoding="utf-8"))
manifest=json.loads((HERE/"manifest.json").read_text(encoding="utf-8"))

def render_video():
    frames_dir=HERE/".frames"
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir()
    candidates=[
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"),
    ]
    font_path=next((p for p in candidates if p.exists()),None)
    if font_path is None:
        raise SystemExit("monospace font unavailable")
    font=ImageFont.truetype(str(font_path),13)
    footer=ImageFont.truetype(str(font_path),9)
    counter=0
    for key in motion["keys"]:
        for _ in range(int(key["exposure_ticks"])):
            im=Image.new("RGB",(640,480),"white")
            d=ImageDraw.Draw(im)
            d.multiline_text((18,4),key["pose_rig"],fill="black",font=font,spacing=0)
            d.text((18,458),"fixed world datum 0+  |  abstract ASCII rig only",fill="black",font=footer)
            im.save(frames_dir/f"frame_{counter:04d}.png")
            counter += 1
    out=HERE/"scoped-gust-rephase.mp4"
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-framerate","24",
        "-i",str(frames_dir/"frame_%04d.png"),
        "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart",
        "-crf","26","-map_metadata","-1",str(out)
    ],check=True)
    return out,counter

def contact_sheet():
    out=[]
    for key in motion["keys"]:
        cs=key["channel_state"]
        out.append(
            f"{key['key_id']}  {key['causal_role']}  {key['timing_class']}/{key['exposure_ticks']}t  "
            f"ROOT=({cs['BODY_ROOT']['root_x']:02d},{cs['BODY_ROOT']['root_y']:02d})  "
            f"CANOPY={cs['CANOPY_CLOCK']['state']}  HAND={cs['HAND_SWAY']['state']}\n"
        )
        out.append(key["pose_rig"])
        out.append(key["motion_arc_root_note"]+"\n")
        out.append("-"*96+"\n")
    return "".join(out)

video,frame_count=render_video()
actual=hashlib.sha256(video.read_bytes()).hexdigest()
declared=motion["compile"]["media"]["sha256"]
if actual != declared:
    raise SystemExit(f"MEDIA_IDENTITY_MISMATCH declared={declared} actual={actual}")
if frame_count != int(motion["compile"]["media"]["frames"]):
    raise SystemExit("FRAME_COUNT_MISMATCH")
sheet=contact_sheet()
(HERE/"contact-sheet.txt").write_text(sheet,encoding="utf-8")
motion_text=(HERE/"motion.json").read_text(encoding="utf-8")
b64=base64.b64encode(video.read_bytes()).decode("ascii")
page=f"""<!doctype html>
<meta charset="utf-8">
<title>Timing017 — scoped gust rephase</title>
<style>
body{{font-family:system-ui;margin:0}}
nav{{display:flex;gap:.5rem;padding:.75rem;position:sticky;top:0;background:white}}
button{{padding:.5rem .8rem}}
section{{display:none;padding:1rem}}
section.active{{display:block}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}
video{{max-width:100%;height:auto}}
</style>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre>{html.escape(sheet)}</pre></section>
<section id="json"><pre>{html.escape(motion_text)}</pre></section>
<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section>
<script>
const ids=["ascii","json","video"];
for(const button of document.querySelectorAll("button[data-view]")) button.onclick=()=>{{
  for(const id of ids) document.getElementById(id).classList.toggle("active",id===button.dataset.view);
}};
</script>
"""
(HERE/manifest["spa_file"]).write_text(page,encoding="utf-8")
print(json.dumps({
    "schema":"ascii-kinesis.motion-dungeon-build",
    "ok":True,
    "media_sha256":actual,
    "frames":frame_count
},sort_keys=True))
