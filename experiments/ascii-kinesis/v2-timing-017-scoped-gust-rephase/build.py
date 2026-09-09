#!/usr/bin/env python3
from pathlib import Path
import base64, hashlib, html, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
motion=json.loads((HERE/"motion.json").read_text(encoding="utf-8"))
manifest=json.loads((HERE/"manifest.json").read_text(encoding="utf-8"))

def render_video():
    frames=HERE/".frames"
    if frames.exists(): shutil.rmtree(frames)
    frames.mkdir()
    candidates=[Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf")]
    font_path=next((p for p in candidates if p.exists()),None)
    if not font_path: raise SystemExit("monospace font unavailable")
    font=ImageFont.truetype(str(font_path),10)
    footer=ImageFont.truetype(str(font_path),8)
    n=0
    for key in motion["keys"]:
        root=key["root_transform"]
        for _ in range(int(key["exposure_ticks"])):
            im=Image.new("RGB",(360,280),"white")
            d=ImageDraw.Draw(im)
            d.multiline_text((18+int(root["x"])*3,5+int(root["y"])*4),key["pose_rig"],fill="black",font=font,spacing=0)
            d.line((8,260,352,260),fill="black",width=1)
            d.text((10,264),"0+ fixed world datum | abstract ASCII rig only",fill="black",font=footer)
            im.save(frames/f"frame_{n:04d}.png")
            n+=1
    out=HERE/"scoped-gust-rephase.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(frames/"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","30","-map_metadata","-1",str(out)],check=True)
    return out,n

def contact_sheet():
    out=[]
    for key in motion["keys"]:
        s=key["channel_state"]; r=key["root_transform"]
        out.append(f"{key['key_id']} {key['causal_role']} {key['timing_class']}/{key['exposure_ticks']}t ROOT=({r['x']:02d},{r['y']:02d}) CANOPY={s['CANOPY_CLOCK']['state']} HAND={s['HAND_SWAY']['state']}\n")
        out.append(key["pose_rig"])
        out.append("-"*72+"\n")
    return "".join(out)

video,count=render_video()
actual=hashlib.sha256(video.read_bytes()).hexdigest()
declared=motion["compile"]["media"]["sha256"]
if actual!=declared: raise SystemExit(f"MEDIA_IDENTITY_MISMATCH declared={declared} actual={actual}")
if count!=int(motion["compile"]["media"]["frames"]): raise SystemExit("FRAME_COUNT_MISMATCH")
sheet=contact_sheet()
(HERE/"contact-sheet.txt").write_text(sheet,encoding="utf-8")
motion_js=json.dumps(motion,separators=(",",":"),ensure_ascii=True)
b64=base64.b64encode(video.read_bytes()).decode("ascii")
page=f"""<!doctype html><meta charset="utf-8"><title>Timing017 scoped gust rephase</title>
<style>body{{font-family:system-ui;margin:0}}nav{{display:flex;gap:.5rem;padding:.75rem;position:sticky;top:0;background:white}}button{{padding:.5rem .8rem}}section{{display:none;padding:1rem}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}video{{max-width:100%;height:auto}}</style>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre id="ascii-pre"></pre></section><section id="json"><pre id="json-pre"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section>
<script>
const motion={motion_js};
const line="-".repeat(72)+"\\n";
document.getElementById("ascii-pre").textContent=motion.keys.map(k=>{{const s=k.channel_state,r=k.root_transform;return `${{k.key_id}} ${{k.causal_role}} ${{k.timing_class}}/${{k.exposure_ticks}}t ROOT=(${{String(r.x).padStart(2,"0")}},${{String(r.y).padStart(2,"0")}}) CANOPY=${{s.CANOPY_CLOCK.state}} HAND=${{s.HAND_SWAY.state}}\\n${{k.pose_rig}}${{line}}`;}}).join("");
document.getElementById("json-pre").textContent=JSON.stringify(motion,null,2);
const ids=["ascii","json","video"];for(const b of document.querySelectorAll("button[data-view]"))b.onclick=()=>{{for(const id of ids)document.getElementById(id).classList.toggle("active",id===b.dataset.view);}};
</script>"""
(HERE/manifest["spa_file"]).write_text(page,encoding="utf-8")
print(json.dumps({"schema":"ascii-kinesis.motion-dungeon-build","ok":True,"media_sha256":actual,"frames":count},sort_keys=True))
