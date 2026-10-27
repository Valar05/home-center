#!/usr/bin/env python3
"""Promptable segmentation smoke. No physical-landmark claims."""
import argparse, hashlib, json
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
from ultralytics import SAM
import torch
p=argparse.ArgumentParser()
p.add_argument("--image")
p.add_argument("--output",required=True)
p.add_argument("--model",default="sam2.1_t.pt")
p.add_argument("--device",default="cpu")
p.add_argument("--box",type=int,nargs=4)
a=p.parse_args()
out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
if a.image:
    source=Path(a.image);img=Image.open(source).convert("RGB")
else:
    source=out/"synthetic-source.png"
    img=Image.new("RGB",(640,480),"#eeeeee")
    ImageDraw.Draw(img).ellipse((140,115,485,365),fill="#667788",outline="#222222",width=9)
    img.save(source)
w,h=img.size
box=a.box or [100,75,535,410]
assert 0<=box[0]<box[2]<=w and 0<=box[1]<box[3]<=h,"Invalid box coordinates"
model=SAM(a.model)
results=model.predict(source=str(source),bboxes=box,device=a.device,verbose=False)
if len(results)!=1 or results[0].masks is None:
    raise RuntimeError("No predicted mask")
masks=results[0].masks.data.detach().cpu().numpy()
if masks.ndim!=3 or masks.shape[0]<1: raise RuntimeError("Empty masks")
mask=masks[0]
if mask.shape!=(h,w): raise RuntimeError(f"Mask shape {mask.shape} differs from image {(h,w)}")
binary=(mask>0.5).astype(np.uint8)*255
if not np.any(binary):raise RuntimeError("Zero foreground pixels")
Image.fromarray(binary).save(out/"mask.png")
overlay=img.convert("RGBA")
tint=Image.new("RGBA",(w,h),(255,75,10,0))
tint.putalpha(Image.fromarray((binary.astype(np.float32)*0.45).astype(np.uint8)))
overlay=Image.alpha_composite(overlay,tint)
ImageDraw.Draw(overlay).rectangle(box,outline="lime",width=2)
overlay.save(out/"overlay.png")
receipt={"ok":True,"scope":"promptable-mask-only","source":str(source),
"source_sha256":hashlib.sha256(source.read_bytes()).hexdigest(),"source_size":[w,h],
"prompt_box":box,"model":a.model,"device":a.device,"torch":torch.__version__,
"torch_cuda_available":torch.cuda.is_available(),"mask_pixels":int(np.count_nonzero(binary)),
"mask_sha256":hashlib.sha256((out/"mask.png").read_bytes()).hexdigest(),
"review":"UNVERIFIED: segmentation is not semantic landmark recognition"}
(out/"receipt.json").write_text(json.dumps(receipt,indent=2)+"\n",encoding="utf-8")
print(json.dumps(receipt,indent=2))
