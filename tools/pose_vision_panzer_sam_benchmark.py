#!/usr/bin/env python3
"""SAM2.1 candidate segmentation vs original alpha, no semantic landmark claims."""
import hashlib,json
from pathlib import Path
import cv2,numpy as np
from PIL import Image,ImageDraw
from ultralytics import SAM
ROOT=Path("G:/My Drive/Panzer-PoseLab-20261024")
OUT=Path.home()/"workspace"/"pose-vision-sam21"/"evidence"/"panzer-sam-probe-20261026"
AUDIT=OUT.parent/"panzer-source-audit-20261026"/"source-inventory.json"
OUT.mkdir(parents=True,exist_ok=True)
report=json.loads(AUDIT.read_text(encoding="utf-8"))
weights=Path.home()/"sam2.1_t.pt"
assert weights.is_file() and weights.stat().st_size > 70_000_000, "Known verified model weights missing; never redownload into inaccessible worker cwd"
model=SAM(str(weights))
summary=[]
for record in report["entries"]:
    name=record["file"]
    source=ROOT/name
    sha=hashlib.sha256(source.read_bytes()).hexdigest()
    assert sha==record["source_sha256"],f"Source changed since audit: {name}"
    img=Image.open(source).convert("RGBA")
    source_alpha=np.asarray(img.getchannel("A"))
    # Deliberately benchmark ONLY the largest alpha component. This is not sprite identification.
    x,y,w,h=record["largest_components"][0]["bbox_xywh"]
    pad=32
    left=max(0,x-pad);top=max(0,y-pad)
    right=min(img.width,x+w+pad);bottom=min(img.height,y+h+pad)
    crop=img.crop((left,top,right,bottom))
    background=Image.new("RGBA",crop.size,(245,245,245,255))
    background.alpha_composite(crop)
    rgb=background.convert("RGB")
    box=[x-left,y-top,x-left+w,y-top+h]
    target=OUT/name.replace(".png","")
    target.mkdir(exist_ok=True)
    rgb.save(target/"input-crop.png")
    pred=model.predict(source=str(target/"input-crop.png"),bboxes=box,device="cpu",verbose=False)
    if not pred or pred[0].masks is None:raise RuntimeError("No SAM mask: "+name)
    mask=pred[0].masks.data[0].cpu().numpy()
    if mask.shape!=(crop.height,crop.width):raise RuntimeError("Mask size disagreement: "+name)
    candidate=mask>0.5
    exact=source_alpha[top:bottom,left:right]>0
    original_mask=np.uint8(exact)*255
    Image.fromarray(original_mask).save(target/"original-alpha.png")
    Image.fromarray(np.uint8(candidate)*255).save(target/"sam-mask.png")
    comparison=np.zeros((crop.height,crop.width,3),dtype=np.uint8)
    comparison[exact & candidate]=(50,200,70)
    comparison[exact & ~candidate]=(255,80,80)
    comparison[~exact & candidate]=(65,130,255)
    Image.fromarray(comparison).save(target/"mask-disagreement.png")
    overlay=rgb.copy();drawer=ImageDraw.Draw(overlay)
    drawer.rectangle(box,outline="#FFCC00",width=3)
    overlay.save(target/"prompt-crop.png")
    intersection=int(np.logical_and(exact,candidate).sum())
    union=int(np.logical_or(exact,candidate).sum())
    row={"source":name,"source_sha256":sha,"source_dimensions":list(img.size),
         "source_component_bbox_xywh":[x,y,w,h],"crop_rect_xyxy":[left,top,right,bottom],
         "crop_prompt_bbox_xyxy":box,"alpha_pixels":int(exact.sum()),
         "sam_pixels":int(candidate.sum()),"overlap_pixels":intersection,
         "alpha_iou":round(intersection/union,4) if union else None,
         "mask_sha256":hashlib.sha256((target/"sam-mask.png").read_bytes()).hexdigest(),
         "limits":"Alpha overlap measures silhouette segmentation only, not mounting-face recognition. No pose mutations."}
    summary.append(row)
    print("SAM_REAL_SOURCE_PASS="+name+" IOU_ALPHA="+str(row["alpha_iou"]),flush=True)
payload={"stage":"real-source-promptable-segmentation","model":"sam2.1_t.pt","device":"cpu",
         "source_audit":str(AUDIT),"results":summary,
         "semantic_landmark_acceptance":"NOT TESTED",
         "user_review":"REQUIRED"}
(OUT/"receipt.json").write_text(json.dumps(payload,indent=2)+"\n",encoding="utf-8")
print("SAM_SOURCE_BENCHMARK_PASS="+str(OUT),flush=True)
