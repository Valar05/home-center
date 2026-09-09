#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/"motion.json"
CONTACT=HERE/"contact-sheet.txt"
SPA=HERE/"rate-regime-hysteresis.motion.html"
MP4=HERE/"rate-regime-hysteresis.mp4"
FRAMES=Path(tempfile.mkdtemp(prefix="timing019-frames-"))
W,H,GROUND_Y=72,19,16
JOINT_ORDER=["head","neck","pelvis","l_shoulder","r_shoulder","l_elbow","r_elbow","l_hand","r_hand","l_knee","r_knee","l_foot","r_foot"]

def line(c,x0,y0,x1,y1,ch):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<H and c[y0][x0]==" ": c[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def make_pose(demand,joints,support):
    c=[[" "]*W for _ in range(H)]
    c[0][:24]=list(f"PACE INPUT {demand}/7".ljust(24))
    for i,level in enumerate(range(7,0,-1),start=2):
        label=f"{level}|"; c[i][0]=label[0]; c[i][1]=label[1]
        if level==6:
            for x in range(3,10): c[i][x]="="
            for j,ch in enumerate(" ENTER6"):
                if 10+j<W: c[i][10+j]=ch
        elif level==3:
            for x in range(3,10): c[i][x]="-"
            for j,ch in enumerate(" EXIT3"):
                if 10+j<W: c[i][10+j]=ch
        if level==demand: c[i][8]=">"
    for x in range(16,W): c[GROUND_Y][x]="_"
    for x in range(18,W,5): c[17][x]="+"
    for j,ch in enumerate("WORLD DATUM"): c[18][16+j]=ch
    p={name:(joints[i*2],joints[i*2+1]) for i,name in enumerate(JOINT_ORDER)} if isinstance(joints,list) else {k:tuple(v) for k,v in joints.items()}
    for a,b,ch in [
        ("head","neck","|"),("neck","pelvis","|"),
        ("neck","l_shoulder","-"),("neck","r_shoulder","-"),
        ("l_shoulder","l_elbow","/"),("l_elbow","l_hand","/"),
        ("r_shoulder","r_elbow","\\"),("r_elbow","r_hand","\\"),
        ("pelvis","l_knee","/"),("l_knee","l_foot","/"),
        ("pelvis","r_knee","\\"),("r_knee","r_foot","\\")]:
        line(c,*p[a],*p[b],ch)
    glyphs={"head":"O","neck":"o","pelvis":"@","l_shoulder":"o","r_shoulder":"o",
            "l_elbow":"o","r_elbow":"o","l_hand":"o","r_hand":"o","l_knee":"o","r_knee":"o",
            "l_foot":"*" if "LEFT" in support or "BOTH" in support else "+",
            "r_foot":"*" if "RIGHT" in support or "BOTH" in support else "+"}
    for k,ch in glyphs.items():
        x,y=p[k]
        if 0<=x<W and 0<=y<H: c[y][x]=ch
    return "\n".join("".join(row).rstrip() for row in c).rstrip()+"\n"

def contact_text(motion):
    out=[]
    for k in motion["keys"]:
        out.append(f"{k['key_id']} {k['causal_role']} REQUEST={k['pace_request']} REGIME={k['rate_regime']} {k['timing_class']}/{k['exposure_ticks']}t PROVENANCE={k['timing_provenance']}\n")
        out.append(make_pose(k["pace_request"],k["joints"],k["support_contact"]))
        out.append("-"*76+"\n")
    return "".join(out)

def render_video(motion):
    FRAMES.mkdir(exist_ok=True)
    fp=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    if not fp.exists(): raise SystemExit("DejaVuSansMono.ttf required")
    font=ImageFont.truetype(str(fp),9); footer=ImageFont.truetype(str(fp),7)
    n=0
    for k in motion["keys"]:
        pose=make_pose(k["pace_request"],k["joints"],k["support_contact"])
        for _ in range(int(k["exposure_ticks"])):
            im=Image.new("RGB",(480,220),"white"); d=ImageDraw.Draw(im)
            d.multiline_text((9,5),pose,fill="black",font=font,spacing=0)
            d.text((8,208),f"Timing019 | {k['key_id']} | {k['causal_role']} | request={k['pace_request']} | regime={k['rate_regime']} | {k['timing_class']}",fill="black",font=footer)
            im.save(FRAMES/f"frame_{n:04d}.png"); n+=1
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(FRAMES/"frame_%04d.png"),
                    "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","31","-map_metadata","-1",str(MP4)],check=True)
    return MP4.read_bytes()

def spa_text(contact,motion_raw,mp4):
    css="body{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}nav{display:flex;gap:.5rem;padding:.75rem;position:sticky;top:0;background:#111}button{padding:.6rem 1rem}section{display:none;padding:1rem}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto}"
    b64=base64.b64encode(mp4).decode("ascii")
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><title>Timing019 - Rate Regime Hysteresis</title><style>{css}</style></head>
<body>
<nav>
<button data-view="ascii" onclick="show('ascii')">ASCII</button>
<button data-view="json" onclick="show('json')">JSON</button>
<button data-view="video" onclick="show('video')">VIDEO</button>
</nav>
<section id="ascii" class="active"><pre>{html.escape(contact)}</pre></section>
<section id="json"><pre>{html.escape(motion_raw)}</pre></section>
<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section>
<script>function show(id){{for(const s of document.querySelectorAll('section'))s.classList.remove('active');document.getElementById(id).classList.add('active');}}</script>
</body></html>
'''

def main():
    raw=MOTION.read_text(encoding="utf-8"); motion=json.loads(raw)
    contact=contact_text(motion); CONTACT.write_text(contact,encoding="utf-8")
    mp4=render_video(motion); got=hashlib.sha256(mp4).hexdigest()
    expected=motion["compile"]["media"]["sha256"]
    if got!=expected: raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={expected} got={got}")
    SPA.write_text(spa_text(contact,raw,mp4),encoding="utf-8")
    print(json.dumps({"experiment_id":motion["experiment_id"],"frames":motion["compile"]["media"]["frames"],"media_sha256":got,"ok":True},sort_keys=True))

if __name__=="__main__": main()
