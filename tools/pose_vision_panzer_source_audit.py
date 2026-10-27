#!/usr/bin/env python3
"""Read-only audit of authoritative Panzer sprites: native alpha components, source hashes.
This script does NOT identify physical landmarks or alter/source-copy artwork.
"""
import hashlib,json,sys
from pathlib import Path
from PIL import Image,ImageDraw
import numpy as np
import cv2

root=Path("G:/My Drive/Panzer-PoseLab-20261024")
dest=Path.home()/"workspace"/"pose-vision-sam21"/"evidence"/"panzer-source-audit-20261026"
dest.mkdir(parents=True,exist_ok=True)
allrows=[]
for filename in ("hulls.png","turrets.png","barrels.png"):
    src=root/filename
    if not src.is_file():
        raise FileNotFoundError(f"Missing canonical sprite: {src}")
    original=src.read_bytes()
    with Image.open(src) as opened:
        rgba=opened.convert("RGBA")
        mode=opened.mode
    pixels=np.array(rgba)
    alpha=pixels[:,:,3]
    visible=np.uint8(alpha>0)
    count,labels,stats,centers=cv2.connectedComponentsWithStats(visible,connectivity=8)
    blobs=[]
    for idx in range(1,count):
        x,y,w,h,area=[int(z) for z in stats[idx]]
        if area < 16:continue
        blobs.append({"bbox_xywh":[x,y,w,h],"alpha_pixels":area})
    blobs.sort(key=lambda z:z["alpha_pixels"],reverse=True)
    record={"file":filename,"source":str(src),"source_sha256":hashlib.sha256(original).hexdigest(),
        "dimensions":list(rgba.size),"original_mode":mode,"alpha_nonzero_pixels":int(visible.sum()),
        "components_total_over_15_pixels":len(blobs),"largest_components":blobs[:50],
        "notes":"Alpha components are NOT semantic sprite cells or mechanical landmarks."}
    allrows.append(record)
    # Informational rectangle map only; original resolution is maintained.
    overview=rgba.convert("RGB")
    paint=ImageDraw.Draw(overview)
    for index,b in enumerate(blobs[:30]):
        x,y,w,h=b["bbox_xywh"]
        paint.rectangle([x,y,x+w-1,y+h-1],outline=(255,0,255),width=3)
        paint.text((x,y),str(index),fill=(255,255,0))
    overview.save(dest/(filename.replace(".png","-components.png")))
report={"stage":"original-pixels-readonly","result":"PASS","entries":allrows,"limits":
"Component boxes are candidate regions only; do not infer physical features, sheet cells, pivots, barrel proximal faces or mount coordinates."}
(dest/"source-inventory.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
print(json.dumps(report,indent=2))
print("SOURCE_AUDIT_PASS="+str(dest))
