#!/usr/bin/env python3
# Deterministically rebuild Defense 011 from persisted abstract motion data.
# No source sprite pixels, palette, contours, layout, audio, or frames are read.
from __future__ import annotations
import base64, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
ASCII_OUT = HERE / "contact-sheet.txt"
SPA_OUT = HERE / "floor-support-ladder-repair.motion.html"
W, H = 64, 22

def key_joints(key, motion):
    names = motion["rig"]["joint_order"]
    return {name: tuple(xy) for name, xy in zip(names, key["pose_rig"]["joint_xy"])}

def draw_line(grid, a, b):
    x0,y0=a; x1,y1=b
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        if 0 <= x0 < W and 0 <= y0 < H and grid[y0][x0] == " ":
            if x0 == x1: c="|"
            elif y0 == y1: c="-"
            else: c="\\" if (x1-x0)*(y1-y0)>0 else "/"
            grid[y0][x0]=c
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def pose_ascii(key, motion, include_meta=False):
    j=key_joints(key,motion)
    floor_y=int(motion["rig"]["floor_y"])
    g=[[" "]*W for _ in range(H)]
    for x in range(4,60): g[floor_y][x]="_"
    for a,b in [("neck","pelvis"),("shoulder_l","shoulder_r"),("shoulder_l","elbow_l"),("elbow_l","hand_l"),("shoulder_r","elbow_r"),("elbow_r","hand_r"),("pelvis","knee_l"),("knee_l","foot_l"),("pelvis","knee_r"),("knee_r","foot_r")]:
        draw_line(g,j[a],j[b])
    marks={"head":"O","neck":"+","shoulder_l":"+","shoulder_r":"+","elbow_l":"+","elbow_r":"+","hand_l":"o","hand_r":"o","pelvis":"@","knee_l":"+","knee_r":"+","foot_l":"=","foot_r":"="}
    for nm,ch in marks.items():
        x,y=j[nm]
        if 0<=x<W and 0<=y<H: g[y][x]=ch
    if key.get("contact_state")=="IMPACT_FROM_RIGHT_LOW":
        for x in range(49,56): g[13][x]="<"
    supports=key.get("support_contact","")
    anchors=[]
    if supports=="BOTH_FEET": anchors=[("foot_l","L"),("foot_r","R")]
    elif supports=="REAR_FOOT": anchors=[("foot_r","R")]
    else:
        if "FOOT_L" in supports: anchors.append(("foot_l","L"))
        if "FOOT_R" in supports: anchors.append(("foot_r","R"))
    if "HAND_L" in supports or "FOREARM_L" in supports: anchors.append(("hand_l","H"))
    if "HAND_R" in supports: anchors.append(("hand_r","H"))
    if "KNEE_L" in supports: anchors.append(("knee_l","K"))
    if "KNEE_R" in supports: anchors.append(("knee_r","K"))
    if "HIP" in supports: anchors.append(("pelvis","P"))
    for nm,ch in anchors:
        x=j[nm][0]
        if 0<=x<W and floor_y+1<H: g[floor_y+1][x]=ch
    body="\n".join("".join(row).rstrip() for row in g)
    if include_meta:
        return (f"{key['key_id']}  {key['name']}  [{key['timing_class']} | {key['timing_provenance']}]\n" + body + f"\nsupport={key['support_contact']} root={key['root_state']} contact={key['contact_state']}" + f"\nrole={key['causal_role']}" + f"\narc={key['motion_arc_root_note']} debt={key['recovery_debt']:.2f}")
    return body

def interpolate(a,b,t,motion,arc):
    names=motion["rig"]["joint_order"]
    aj=key_joints(a,motion); bj=key_joints(b,motion)
    out={}
    for nm in names:
        p0=aj[nm]; p1=bj[nm]
        lag = 0.13 if nm in ("head","hand_r") else (0.07 if nm=="hand_l" else (-0.08 if nm in ("foot_l","foot_r") else 0.0))
        tt=max(0.0,min(1.0,t-lag)); e=tt*tt*(3.0-2.0*tt); q=4.0*tt*(1.0-tt)
        scale=1.0 if nm in ("pelvis","neck","head") else 0.55
        x=p0[0]+(p1[0]-p0[0])*e+arc[0]*q*scale
        y=p0[1]+(p1[1]-p0[1])*e+arc[1]*q*scale
        out[nm]=[int(round(x)),int(round(y))]
    k={kk:vv for kk,vv in a.items() if kk!="pose_rig"}
    k["pose_rig"]={"joint_xy":[out[nm] for nm in names]}
    k["key_id"]=f"{a['key_id']}→{b['key_id']}"; k["name"]=f"{a['name']}→{b['name']}"
    return k

def compile_frames(motion):
    frames=[]; labels=[]; keys=motion["keys"]
    for i,k in enumerate(keys):
        for _ in range(int(k["hold_frames"])):
            frames.append(pose_ascii(k,motion)); labels.append(k["key_id"])
        if i < len(keys)-1:
            n=int(k.get("bridge",{}).get("frames",0)); arc=tuple(k.get("bridge",{}).get("root_arc",[0,0]))
            for s in range(1,n+1):
                ik=interpolate(k,keys[i+1],s/(n+1),motion,arc)
                frames.append(pose_ascii(ik,motion)); labels.append(ik["key_id"])
    return frames,labels

def make_ascii_sheet(motion):
    title=("ASCII KINESIS V2 DEFENSE 011 — FLOOR SUPPORT LADDER REPAIR\n" "abstract rig only — source art never enters output\n" "performance law: floor contact is consequence; height is purchased by trustworthy support\n" "force line: RIGHT-LOW impact -> LEFT/DOWN collapse -> FLOOR overshoot -> RIGHT/UP recovery -> displaced ready\n\n")
    return title + ("\n\n"+"-"*64+"\n\n").join(pose_ascii(k,motion,True) for k in motion["keys"])

def render_mp4(motion,target):
    frames,labels=compile_frames(motion); font=ImageFont.load_default(size=16); meta=ImageFont.load_default(size=14)
    with tempfile.TemporaryDirectory(prefix="ascii-kinesis-d011-") as td:
        td=Path(td)
        for i,(txt,label) in enumerate(zip(frames,labels)):
            im=Image.new("RGB",(640,360),(12,12,12)); d=ImageDraw.Draw(im)
            d.text((12,8),f"{label}   DEFENSE 011",fill=(220,220,220),font=meta)
            d.multiline_text((14,34),txt,fill=(245,245,245),font=font,spacing=1); im.save(td/f"{i:04d}.png")
        subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(motion["compile"]["fps"]),"-i",str(td/"%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-preset","veryslow","-crf","28",str(target)],check=True)
    return len(frames)

def make_spa(motion,ascii_sheet,media):
    payload=json.dumps(motion,ensure_ascii=False,sort_keys=True,separators=(",",":")); v64=base64.b64encode(media).decode("ascii")
    css='''html,body{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}header{position:sticky;top:0;background:#171717;padding:12px;border-bottom:1px solid #444}nav{display:flex;gap:8px}button{font:inherit;padding:.55rem .85rem;background:#222;color:#eee;border:1px solid #666;border-radius:6px}button[aria-selected=true]{background:#eee;color:#111}main{padding:14px}.panel{display:none}.panel.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto;border:1px solid #555;background:#000}'''
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Defense 011 — Floor Support Ladder Repair</title><style>{css}</style></head><body><header><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section class="panel active" data-panel="ascii"><pre>{html.escape(ascii_sheet)}</pre></section><section class="panel" data-panel="json"><pre>{html.escape(payload)}</pre></section><section class="panel" data-panel="video"><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{v64}"></video></section></main><script>const buttons=[...document.querySelectorAll('button[data-view]')];const panels=[...document.querySelectorAll('[data-panel]')];buttons.forEach(b=>b.addEventListener('click',()=>{{buttons.forEach(x=>x.setAttribute('aria-selected',String(x===b)));panels.forEach(p=>p.classList.toggle('active',p.dataset.panel===b.dataset.view));}}));</script></body></html>'''

def main():
    motion=json.loads(MOTION.read_text(encoding="utf-8")); sheet=make_ascii_sheet(motion); ASCII_OUT.write_text(sheet,encoding="utf-8"); tmp=HERE/".d011.tmp.mp4"
    try:
        count=render_mp4(motion,tmp); media=tmp.read_bytes(); got=hashlib.sha256(media).hexdigest(); expected=motion["media"]["sha256"]
        if expected not in ("__PENDING__",got): raise SystemExit(f"media hash mismatch {got} != {expected}")
        if motion["compile"].get("frames") not in (None,count): raise SystemExit(f"frame mismatch {count} != {motion['compile']['frames']}")
        SPA_OUT.write_text(make_spa(motion,sheet,media),encoding="utf-8")
    finally:
        if tmp.exists(): tmp.unlink()
    print(json.dumps({"experiment_id":motion["experiment_id"],"frames":count,"ascii_sha256":hashlib.sha256(sheet.encode()).hexdigest(),"media_sha256":got,"media_bytes":len(media),"spa":SPA_OUT.name},sort_keys=True))

if __name__=="__main__": main()
