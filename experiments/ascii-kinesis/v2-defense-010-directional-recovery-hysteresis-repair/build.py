#!/usr/bin/env python3
"""Deterministically rebuild Defense 010 from persisted abstract motion data.

No source sprite pixels, palette, contours, layout, or audio are read.
The only animation inputs are motion.json ASCII joint geometry, explicit timing,
and authored connective arc facts.
"""
from __future__ import annotations
import base64, hashlib, html, json, math, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
ASCII_OUT = HERE / "contact-sheet.txt"
SPA_OUT = HERE / "directional-recovery-hysteresis-repair.motion.html"
W, H = 64, 22

def key_joints(key, motion=None):
    names = (motion or {}).get("rig",{}).get("joint_order") if motion else None
    if names is None:
        names = ["head","neck","shoulder_l","shoulder_r","elbow_l","elbow_r","hand_l","hand_r","pelvis","knee_l","knee_r","foot_l","foot_r"]
    return {name: tuple(xy) for name,xy in zip(names,key["pose_rig"]["joint_xy"])}

def line_chars(grid, a, b):
    x0,y0 = a; x1,y1 = b
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        if 0 <= x0 < W and 0 <= y0 < H and grid[y0][x0] == " ":
            if x0 == x1: c="|"
            elif y0 == y1: c="-"
            else: c="\\" if (x1-x0)*(y1-y0)>0 else "/"
            grid[y0][x0]=c
        if x0 == x1 and y0 == y1: break
        e2=2*err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy

def pose_ascii(key, include_meta=False):
    j=key_joints(key)
    floor_y=19
    g=[[" "]*W for _ in range(H)]
    for x in range(5,59): g[floor_y][x]="_"
    for a,b in [
        ("neck","pelvis"),("shoulder_l","shoulder_r"),
        ("shoulder_l","elbow_l"),("elbow_l","hand_l"),
        ("shoulder_r","elbow_r"),("elbow_r","hand_r"),
        ("pelvis","knee_l"),("knee_l","foot_l"),
        ("pelvis","knee_r"),("knee_r","foot_r"),
    ]:
        line_chars(g,j[a],j[b])
    marks={"head":"O","neck":"+","shoulder_l":"+","shoulder_r":"+",
           "elbow_l":"+","elbow_r":"+","hand_l":"o","hand_r":"o",
           "pelvis":"@","knee_l":"+","knee_r":"+","foot_l":"=","foot_r":"="}
    for nm,ch in marks.items():
        x,y=j[nm]
        if 0 <= x < W and 0 <= y < H: g[y][x]=ch
    if key.get("contact_state") == "IMPACT_LEFT":
        for x in range(7,15): g[8][x]=">"
    sup=key.get("support_contact","")
    if "LEFT" in sup and "NONE" not in sup:
        x=j["foot_l"][0]
        if floor_y+1 < H and 0 <= x < W: g[floor_y+1][x]="L"
    if "RIGHT" in sup and "NONE" not in sup and "HAND" not in sup:
        x=j["foot_r"][0]
        if floor_y+1 < H and 0 <= x < W: g[floor_y+1][x]="R"
    if "HAND_R" in sup:
        x=j["hand_r"][0]
        if floor_y+1 < H and 0 <= x < W: g[floor_y+1][x]="H"
    body="\n".join("".join(r).rstrip() for r in g)
    if include_meta:
        return (
            f"{key['key_id']}  {key['name']}  [{key['timing_class']} | {key['timing_provenance']}]\n"
            + body
            + f"\nsupport={key['support_contact']} root={key['root_state']} debt={key['recovery_debt']:.2f}"
        )
    return body

def interpolate(a,b,t,arc):
    joint_names=["head","neck","shoulder_l","shoulder_r","elbow_l","elbow_r","hand_l","hand_r","pelvis","knee_l","knee_r","foot_l","foot_r"]
    aj=key_joints(a); bj=key_joints(b)
    joints={}
    for nm in joint_names:
        p0=aj[nm]; p1=bj[nm]
        lag=0.12 if nm in ("head","hand_r") else (-0.07 if nm in ("foot_l","foot_r") else 0.0)
        tt=max(0.0,min(1.0,t-lag))
        e=tt*tt*(3.0-2.0*tt)
        x=p0[0]+(p1[0]-p0[0])*e
        y=p0[1]+(p1[1]-p0[1])*e
        q=4.0*tt*(1.0-tt)
        scale=1.0 if nm in ("pelvis","neck","head") else 0.55
        x += arc[0]*q*scale
        y += arc[1]*q*scale
        joints[nm]=[int(round(x)),int(round(y))]
    out={k:v for k,v in a.items() if k != "pose_rig"}
    out["pose_rig"]={"joint_xy":[joints[nm] for nm in joint_names]}
    out["key_id"]=f"{a['key_id']}→{b['key_id']}"
    out["name"]=f"{a['name']}→{b['name']}"
    return out

def compile_frames(motion):
    keys=motion["keys"]
    frames=[]; labels=[]
    for i,k in enumerate(keys):
        for _ in range(int(k["hold_frames"])):
            frames.append(pose_ascii(k)); labels.append(k["key_id"])
        if i < len(keys)-1:
            n=int(k["bridge"]["frames"])
            arc=tuple(k["bridge"]["root_arc"])
            for s in range(1,n+1):
                ik=interpolate(k,keys[i+1],s/(n+1),arc)
                frames.append(pose_ascii(ik)); labels.append(ik["key_id"])
    return frames,labels

def make_ascii_sheet(motion):
    blocks=[pose_ascii(k,True) for k in motion["keys"]]
    return (
        "ASCII KINESIS V2 DEFENSE 010 — DIRECTIONAL RECOVERY HYSTERESIS REPAIR\n"
        "abstract rig only — source art never enters output\n"
        "force memory: LEFT→RIGHT impact / counter-travel left / displaced READY with residual debt\n\n"
        + ("\n\n"+"-"*64+"\n\n").join(blocks)
    )

def render_mp4(motion, target):
    frames,labels=compile_frames(motion)
    font=ImageFont.load_default(size=16)
    meta=ImageFont.load_default(size=14)
    with tempfile.TemporaryDirectory(prefix="ascii-kinesis-d010-") as td:
        td=Path(td)
        for i,(text,label) in enumerate(zip(frames,labels)):
            img=Image.new("RGB",(640,360),(12,12,12))
            d=ImageDraw.Draw(img)
            d.text((12,8),label,fill=(220,220,220),font=meta)
            d.multiline_text((14,34),text,fill=(245,245,245),font=font,spacing=1)
            img.save(td/f"{i:04d}.png")
        subprocess.run([
            "ffmpeg","-y","-loglevel","error","-framerate","24",
            "-i",str(td/"%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p",
            "-movflags","+faststart","-preset","veryslow","-crf","28",str(target)
        ],check=True)
    return len(frames)

def make_spa(motion, ascii_sheet, mp4_bytes):
    json_text=json.dumps(motion,indent=2,ensure_ascii=False,sort_keys=True)
    video64=base64.b64encode(mp4_bytes).decode("ascii")
    css=r"""
html,body{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}
header{position:sticky;top:0;background:#171717;padding:12px;border-bottom:1px solid #444}
nav{display:flex;gap:8px}
button{font:inherit;padding:.55rem .85rem;background:#222;color:#eee;border:1px solid #666;border-radius:6px}
button[aria-selected=true]{background:#eee;color:#111}
main{padding:14px}.panel{display:none}.panel.active{display:block}
pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;
font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1.05}
video{max-width:100%;height:auto;border:1px solid #555;background:#000}
"""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis Defense 010</title><style>{css}</style></head>
<body><header><nav aria-label="Primary views">
<button data-view="ascii" aria-selected="true">ASCII</button>
<button data-view="json" aria-selected="false">JSON</button>
<button data-view="video" aria-selected="false">VIDEO</button>
</nav></header><main>
<section class="panel active" data-panel="ascii"><pre>{html.escape(ascii_sheet)}</pre></section>
<section class="panel" data-panel="json"><pre>{html.escape(json_text)}</pre></section>
<section class="panel" data-panel="video"><video controls loop playsinline preload="metadata"
src="data:video/mp4;base64,{video64}"></video></section>
</main><script>
const buttons=[...document.querySelectorAll('button[data-view]')];
const panels=[...document.querySelectorAll('[data-panel]')];
buttons.forEach(b=>b.addEventListener('click',()=>{{
 buttons.forEach(x=>x.setAttribute('aria-selected',String(x===b)));
 panels.forEach(p=>p.classList.toggle('active',p.dataset.panel===b.dataset.view));
}}));
</script></body></html>"""

def main():
    motion=json.loads(MOTION.read_text(encoding="utf-8"))
    ascii_sheet=make_ascii_sheet(motion)
    ASCII_OUT.write_text(ascii_sheet,encoding="utf-8")
    got_ascii=hashlib.sha256(ascii_sheet.encode()).hexdigest()
    tmp=HERE/".directional-recovery-hysteresis-repair.motion.tmp.mp4"
    try:
        count=render_mp4(motion,tmp)
        media=tmp.read_bytes()
        got=hashlib.sha256(media).hexdigest()
        expected=motion["media"]["sha256"]
        if got != expected:
            raise SystemExit(f"media hash mismatch: {got} != {expected}")
        if count != motion["compile"]["frames"]:
            raise SystemExit(f"frame count mismatch: {count}")
        SPA_OUT.write_text(make_spa(motion,ascii_sheet,media),encoding="utf-8")
    finally:
        if tmp.exists(): tmp.unlink()
    print(json.dumps({"experiment_id":motion["experiment_id"],"ascii_sha256":got_ascii,
                      "media_sha256":got,"frames":count,"spa":SPA_OUT.name},sort_keys=True))

if __name__ == "__main__":
    main()
