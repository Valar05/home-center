#!/usr/bin/env python3
"""Deterministically rebuild Timing018 from the persisted abstract ASCII rig + timing only."""
from pathlib import Path
import json, hashlib, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parent
motion=json.loads((ROOT/"motion.json").read_text(encoding="utf-8"))
font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",12)
frames=ROOT/".motion-frames"
if frames.exists(): shutil.rmtree(frames)
frames.mkdir()
n=0
for key in motion["keys"]:
    for _ in range(int(key["exposure_ticks"])):
        im=Image.new("RGB",(620,260),"white"); d=ImageDraw.Draw(im)
        d.multiline_text((12,8),key["pose_rig"],font=font,fill="black",spacing=0)
        im.save(frames/f"f_{n:04d}.png"); n+=1
out=ROOT/"nonreciprocal-return-cadence.mp4"
subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(frames/"f_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-crf","27","-movflags","+faststart","-map_metadata","-1",str(out)],check=True)
print(json.dumps({"frames":n,"sha256":hashlib.sha256(out.read_bytes()).hexdigest(),"bytes":out.stat().st_size},sort_keys=True))
