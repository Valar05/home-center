#!/usr/bin/env python3
from pathlib import Path
import json, math, subprocess, hashlib, base64, html, shutil, gzip
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
CONTACT = HERE / "contact_sheet.txt"
SPA = HERE / "axial-thrust-recovery-reset-repair.motion.html"
MP4 = HERE / "_authoritative.mp4"
FRAMES = HERE / "_frames"
W,H = 800,360
FPS = 24

def font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def lerp(a,b,t): return a+(b-a)*t
def interp_joints(a,b,t):
    return {k:[lerp(a[k][0],b[k][0],t),lerp(a[k][1],b[k][1],t)] for k in a}

def compile_frames(m):
    out=[]
    keys=m["keys"]
    trans=m["motion_dungeon"]["transition_frames"]
    for i,k in enumerate(keys):
        for _ in range(int(k["hold_frames"])):
            out.append((k["joints"], k["key_id"], k["name"], k["support_contact"], 0.0))
        if i < len(keys)-1:
            n=int(trans[i])
            for q in range(1,n+1):
                t=q/(n+1)
                out.append((interp_joints(k["joints"],keys[i+1]["joints"],t),
                            f"{k['key_id']}→{keys[i+1]['key_id']}", "CONNECTIVE_GEOMETRY",
                            "SEMANTICS_CHANGE_ONLY_AT_KEYS", t))
    return out

def xy(p,grid):
    gx,gy=p
    left,top=55,50
    right,bottom=745,315
    return (left + gx/(grid["width"]-1)*(right-left),
            top + gy/(grid["height"]-1)*(bottom-top))

def draw_frame(m, joints, kid, name, support, idx, total):
    img=Image.new("RGB",(W,H),(15,16,19))
    d=ImageDraw.Draw(img)
    f12,f16,f22 = font(12),font(16),font(22)
    grid=m["rig"]["grid"]
    d.text((18,12),"ASCII KINESIS V2 STRIKES 028",font=f16,fill=(230,230,230))
    d.text((18,32),f"{kid}  {name}",font=f12,fill=(190,190,190))
    d.text((545,16),f"{idx+1:02d}/{total:02d}",font=f12,fill=(160,160,160))
    d.text((18,335),support,font=f12,fill=(165,165,165))
    gy=xy([0,28],grid)[1]
    d.line((45,gy,755,gy),fill=(55,58,64),width=2)
    ix=xy([m["rig"]["impact_plane"]["x"],0],grid)[0]
    d.line((ix,65,ix,300),fill=(85,87,92),width=2)
    d.text((ix-30,302),"IMPACT",font=f12,fill=(105,105,110))
    for a,b in m["rig"]["bones"]:
        pa=xy(joints[a],grid); pb=xy(joints[b],grid)
        d.line((*pa,*pb),fill=(220,220,220),width=5)
    pa=xy(joints["tool_butt"],grid); pb=xy(joints["tool_tip"],grid)
    d.line((*pa,*pb),fill=(245,245,245),width=7)
    for namej in ["pelvis","chest","rear_shoulder","rear_elbow","rear_hand","front_shoulder","front_elbow","front_hand","rear_knee","rear_foot","front_knee","front_foot"]:
        x,y=xy(joints[namej],grid)
        r=5 if "foot" not in namej else 6
        d.ellipse((x-r,y-r,x+r,y+r),fill=(210,210,210))
    x,y=xy(joints["head"],grid); d.ellipse((x-9,y-9,x+9,y+9),outline=(240,240,240),width=4)
    x,y=xy(joints["pelvis"],grid); d.rectangle((x-6,y-6,x+6,y+6),fill=(240,240,240))
    x,y=pa; d.rectangle((x-6,y-6,x+6,y+6),outline=(235,235,235),width=2)
    x,y=pb; d.polygon([(x+9,y),(x-6,y-6),(x-6,y+6)],fill=(245,245,245))
    if kid=="K8":
        d.line((ix-10,y-10,ix+10,y+10),fill=(255,255,255),width=3)
        d.line((ix-10,y+10,ix+10,y-10),fill=(255,255,255),width=3)
        d.text((ix-52,73),"CONTACT PIN",font=f12,fill=(230,230,230))
    return img

def make_spa(m, ascii_text, mp4):
    vb64=base64.b64encode(mp4).decode("ascii")
    motion_text=json.dumps(m,separators=(",",":"),ensure_ascii=False)
    ab64=base64.b64encode(gzip.compress(ascii_text.encode("utf-8"),9)).decode("ascii")
    jb64=base64.b64encode(gzip.compress(motion_text.encode("utf-8"),9)).decode("ascii")
    page=f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis Strikes 028 — Axial Thrust Recovery Reset Repair</title>
<style>:root{{color-scheme:dark}}body{{margin:0;background:#0f1013;color:#eee;font-family:system-ui}}nav{{position:sticky;top:0;padding:12px;background:#181a1f;border-bottom:1px solid #333}}button{{padding:8px 14px;margin-right:8px}}section{{display:none;padding:16px}}section.on{{display:block}}pre{{white-space:pre;overflow:auto;font:12px/1.12 monospace;font-variant-ligatures:none}}video{{display:block;max-width:100%;height:auto;background:#000}}</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="on"><pre id="asciiText"></pre></section><section id="json"><pre id="jsonText"></pre></section><section id="video"><video controls playsinline src="data:video/mp4;base64,{vb64}"></video></section>
<script>const A="{ab64}",J="{jb64}";async function gun(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).text()}};(async()=>{{asciiText.textContent=await gun(A);jsonText.textContent=await gun(J)}})();for(const b of document.querySelectorAll('button[data-view]'))b.onclick=()=>{{for(const s of document.querySelectorAll('section'))s.classList.remove('on');document.getElementById(b.dataset.view).classList.add('on')}};</script></body></html>"""
    return page

def main():
    m=json.loads(MOTION.read_text(encoding="utf-8"))
    ascii_text=CONTACT.read_text(encoding="utf-8")
    frames=compile_frames(m)
    if FRAMES.exists():
        shutil.rmtree(FRAMES)
    FRAMES.mkdir()
    for i,(j,kid,name,support,t) in enumerate(frames):
        draw_frame(m,j,kid,name,support,i,len(frames)).save(FRAMES/f"f{i:04d}.png")
    cmd=["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(FRAMES/"f%04d.png"),
         "-c:v","libx264","-pix_fmt","yuv420p","-preset","veryslow","-crf","42","-movflags","+faststart",str(MP4)]
    subprocess.run(cmd,check=True)
    raw=MP4.read_bytes()
    m["media"]={"codec":"h264/yuv420p","width":W,"height":H,"fps":FPS,"frame_count":len(frames),
                "bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),
                "video_required":True,"video_source":"abstract_ascii_rig_only","embedded_in_spa":True}
    MOTION.write_text(json.dumps(m,separators=(",",":"),ensure_ascii=False)+"\n",encoding="utf-8")
    SPA.write_text(make_spa(m,ascii_text,raw),encoding="utf-8")
    print(json.dumps(m["media"],sort_keys=True))
if __name__=="__main__":
    main()
