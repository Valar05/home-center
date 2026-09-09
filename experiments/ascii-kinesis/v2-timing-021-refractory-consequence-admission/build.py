#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/"motion.json"
CONTACT=HERE/"contact-sheet.txt"
SPA=HERE/"refractory-consequence-admission.motion.html"
MP4=HERE/"refractory-consequence-admission.mp4"
FRAMES=Path(tempfile.mkdtemp(prefix="timing021-frames-"))
W,H=78,23

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

def pulse_x(k):
    state=k.get("event_state","NONE")
    if state=="PULSE_CONTACT": return 48
    if state=="PULSE_EXIT": return 55
    return None

def make_pose(k):
    c=[[" "]*W for _ in range(H)]
    for x in range(3,75): c[18][x]="_"
    p={name:tuple(xy) for name,xy in k["joints"].items()}
    for a,b,ch in [
        ("head","neck","|"),("neck","pelvis","|"),
        ("neck","l_shoulder","-"),("neck","r_shoulder","-"),
        ("l_shoulder","l_elbow","/"),("l_elbow","l_hand","/"),
        ("r_shoulder","r_elbow","\\"),
        ("r_elbow","r_hand","\\"),
        ("pelvis","l_knee","/"),("l_knee","l_foot","/"),
        ("pelvis","r_knee","\\"),
        ("r_knee","r_foot","\\")]:
        line(c,*p[a],*p[b],ch)
    owner=k.get("support_owner","")
    glyphs={"head":"O","neck":"o","pelvis":"@","l_shoulder":"o","r_shoulder":"o",
            "l_elbow":"o","r_elbow":"o","l_hand":"o","r_hand":"o","l_knee":"o","r_knee":"o",
            "l_foot":"*" if owner in ("LEFT","BOTH") else "+",
            "r_foot":"*" if owner in ("RIGHT","BOTH") else "+"}
    for name,ch in glyphs.items():
        x,y=p[name]
        if 0<=x<W and 0<=y<H: c[y][x]=ch
    px=pulse_x(k)
    if px is not None:
        for i,ch in enumerate(">>>"):
            x=px+i; y=8
            if 0<=x<W: c[y][x]=ch
        if k["causal_role"]=="EARLY_RETRIGGER_COALESCED":
            c[8][47]="x"
        elif "ADMITTED" in k["causal_role"]:
            c[8][47]="!"
    return "\n".join("".join(row).rstrip() for row in c).rstrip()+"\n"

def contact_text(motion):
    out=[]
    for k in motion["keys"]:
        out.append(f"{k['key_id']} {k['causal_role']} {k['timing_class']}/{k['exposure_ticks']}t PROVENANCE={k['timing_provenance']} REFRACTORY={k['refractory_state']} EVENT={k['event_disposition']} ROOT=({k['root_transform']['x']},{k['root_transform']['y']}) OWNER={k['support_owner']} SUPPORT={k['support_contact']}\n")
        out.append(make_pose(k)); out.append("-"*92+"\n")
    return "".join(out)

def render_video(motion):
    FRAMES.mkdir(exist_ok=True)
    fp=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    if not fp.exists(): raise SystemExit("DejaVuSansMono.ttf required")
    font=ImageFont.truetype(str(fp),13)
    footer=ImageFont.truetype(str(fp),10)
    n=0
    for k in motion["keys"]:
        pose=make_pose(k)
        for _ in range(int(k["exposure_ticks"])):
            im=Image.new("RGB",(780,360),"white")
            d=ImageDraw.Draw(im)
            d.multiline_text((12,8),pose,fill="black",font=font,spacing=0)
            d.text((12,336),f"Timing021 | {k['key_id']} | {k['causal_role']} | {k['timing_class']}",fill="black",font=footer)
            im.save(FRAMES/f"frame_{n:04d}.png"); n+=1
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(FRAMES/"frame_%04d.png"),
                    "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","30","-map_metadata","-1",str(MP4)],check=True)
    return MP4.read_bytes()

def spa_text(contact,motion_raw,mp4):
    css="body{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}nav{display:flex;gap:.5rem;padding:.75rem;position:sticky;top:0;background:#111}button{padding:.6rem 1rem}section{display:none;padding:1rem}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto}"
    video_b64=base64.b64encode(mp4).decode("ascii")
    ascii_b64=base64.b64encode(gzip.compress(contact.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    json_b64=base64.b64encode(gzip.compress(motion_raw.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    return '<!doctype html>\n<html><head><meta charset="utf-8"><title>Timing021 - Refractory Consequence Admission</title><style>'+css+'</style></head>\n<body>\n<nav>\n<button data-view="ascii" onclick="show(\'ascii\')">ASCII</button>\n<button data-view="json" onclick="show(\'json\')">JSON</button>\n<button data-view="video" onclick="show(\'video\')">VIDEO</button>\n</nav>\n<section id="ascii" class="active"><pre id="ascii-pre"></pre></section>\n<section id="json"><pre id="json-pre"></pre></section>\n<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+video_b64+'"></video></section>\n<script>\nfunction show(id){for(const s of document.querySelectorAll(\'section\'))s.classList.remove(\'active\');document.getElementById(id).classList.add(\'active\');}\nasync function inflate64(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream(\'gzip\');return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}\nPromise.all([inflate64(\''+ascii_b64+'\'),inflate64(\''+json_b64+'\')]).then(([a,j])=>{document.getElementById(\'ascii-pre\').textContent=a;document.getElementById(\'json-pre\').textContent=j;});\n</script></body></html>\n'

def main():
    raw=MOTION.read_text(encoding="utf-8")
    motion=json.loads(raw)
    contact=contact_text(motion)
    CONTACT.write_text(contact,encoding="utf-8")
    mp4=render_video(motion)
    got=hashlib.sha256(mp4).hexdigest()
    expected=motion["compile"]["media"]["sha256"]
    if got!=expected: raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={expected} got={got}")
    SPA.write_text(spa_text(contact,raw,mp4),encoding="utf-8")
    print(json.dumps({"experiment_id":motion["experiment_id"],"frames":motion["compile"]["media"]["frames"],"media_sha256":got,"ok":True},sort_keys=True))

if __name__=="__main__":
    main()
