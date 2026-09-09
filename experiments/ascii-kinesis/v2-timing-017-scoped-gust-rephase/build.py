#!/usr/bin/env python3
from pathlib import Path
import base64, hashlib, html, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
motion=json.loads((HERE/"motion.json").read_text(encoding="utf-8"))
manifest=json.loads((HERE/"manifest.json").read_text(encoding="utf-8"))

def render_video():
    frames_dir=HERE/".frames"
    if frames_dir.exists(): shutil.rmtree(frames_dir)
    frames_dir.mkdir()
    font_candidates=[
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
        Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"),
    ]
    font_path=next((p for p in font_candidates if p.exists()),None)
    if font_path is None: raise SystemExit("monospace font unavailable")
    font=ImageFont.truetype(str(font_path),16)
    counter=0
    for k in motion["keys"]:
        for _ in range(int(k["exposure_ticks"])):
            im=Image.new("RGB",(640,560),"white")
            d=ImageDraw.Draw(im)
            d.text((18,12),f"{k['key_id']}  {k['causal_role']}  {k['timing_class']}",fill="black",font=font)
            d.multiline_text((130,50),k["pose_rig"],fill="black",font=font,spacing=1)
            cs=k["channel_state"]
            d.text((18,530),f"ROOT y={cs['BODY_ROOT']['root_y']:02d} | HAND {cs['HAND_SWAY']['state']} | CANOPY {cs['CANOPY_CLOCK']['state']}",fill="black",font=font)
            im.save(frames_dir/f"frame_{counter:04d}.png")
            counter+=1
    out=HERE/"scoped-gust-rephase.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(frames_dir/"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","18",str(out)],check=True)
    return out

def contact_sheet():
    parts=[]
    for k in motion["keys"]:
        cs=k["channel_state"]
        parts += [
            f"{k['key_id']}  {k['causal_role']}  {k['timing_class']}/{k['exposure_ticks']}t  CANOPY={cs['CANOPY_CLOCK']['state']}  HAND={cs['HAND_SWAY']['state']}\n",
            k["pose_rig"],
            f"ROOT_Y={cs['BODY_ROOT']['root_y']:02d}  {k['motion_arc_root_note'].split('; ',1)[-1]}\n",
            "-"*79+"\n",
        ]
    return "".join(parts)

video=render_video()
declared=motion["compile"]["media"]["sha256"]
actual=hashlib.sha256(video.read_bytes()).hexdigest()
if actual != declared:
    raise SystemExit(f"MEDIA_IDENTITY_MISMATCH declared={declared} actual={actual}")
sheet=contact_sheet()
(HERE/"contact-sheet.txt").write_text(sheet,encoding="utf-8")
b64=base64.b64encode(video.read_bytes()).decode("ascii")
motion_text=(HERE/"motion.json").read_text(encoding="utf-8")
page=f"""<!doctype html><meta charset="utf-8"><title>Timing017 scoped gust rephase</title>
<style>
body{{font-family:system-ui;margin:0}}nav{{display:flex;gap:.5rem;padding:.75rem;position:sticky;top:0;background:white}}
button{{padding:.5rem .8rem}}section{{display:none;padding:1rem}}section.active{{display:block}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}
video{{max-width:100%;height:auto}}
</style>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre>{html.escape(sheet)}</pre></section>
<section id="json"><pre>{html.escape(motion_text)}</pre></section>
<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section>
<script>
const ids=["ascii","json","video"];
for(const b of document.querySelectorAll("button[data-view]")) b.onclick=()=>{{
 for(const id of ids) document.getElementById(id).classList.toggle("active",id===b.dataset.view);
}};
</script>"""
(HERE/manifest["spa_file"]).write_text(page,encoding="utf-8")
print(json.dumps({"schema":"ascii-kinesis.motion-dungeon-build","ok":True,"media_sha256":actual,"frames":sum(int(k["exposure_ticks"]) for k in motion["keys"])}))
