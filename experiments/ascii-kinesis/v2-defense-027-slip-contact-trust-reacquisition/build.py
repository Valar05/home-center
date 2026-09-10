#!/usr/bin/env python3
from pathlib import Path
import json, math, base64, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MOTION = json.loads((ROOT/"motion.json").read_text(encoding="utf-8"))
COLS=MOTION["canvas"]["cols"]; ROWS=MOTION["canvas"]["rows"]; FLOOR=MOTION["canvas"]["floor_y"]
FPS=MOTION["canvas"]["fps"]; W=MOTION["canvas"]["width_px"]; H=MOTION["canvas"]["height_px"]

def line(grid,a,b,ch=None):
    x0,y0=a; x1,y1=b
    dx=abs(x1-x0); dy=-abs(y1-y0)
    sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        if 0<=x0<COLS and 0<=y0<ROWS:
            if ch is not None: c=ch
            elif abs(x1-a[0]) > abs(y1-a[1])*2: c='-'
            elif abs(y1-a[1]) > abs(x1-a[0])*2: c='|'
            else: c='\\' if (x1-a[0])*(y1-a[1])>0 else '/'
            if grid[y0][x0]==' ': grid[y0][x0]=c
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def pose_ascii(k):
    g=[[' ']*COLS for _ in range(ROWS)]
    for x in range(COLS): g[FLOOR][x]='_'
    p=k["pose_rig"]
    head=tuple(p["head"]); root=tuple(p["root"])
    shL,shR=map(tuple,p["shoulders"]); hL,hR=map(tuple,p["hands"])
    eL,eR=map(tuple,p["elbows"]); knL,knR=map(tuple,p["knees"]); fL,fR=map(tuple,p["feet"])
    neck=((shL[0]+shR[0])//2,(shL[1]+shR[1])//2)
    for a,b in [(neck,root),(shL,shR),(shL,eL),(eL,hL),(shR,eR),(eR,hR),(root,knL),(knL,fL),(root,knR),(knR,fR)]:
        line(g,a,b)
    for (x,y),c in [(head,'o'),(root,'@'),(shL,'+'),(shR,'+'),(eL,'*'),(eR,'*'),(hL,'['),(hR,']')]:
        if 0<=x<COLS and 0<=y<ROWS:g[y][x]=c
    fs=k["support_contact"]
    for foot,state in [(fL,fs["left"]),(fR,fs["right"])]:
        x,y=foot
        c='x' if state=="trusted" else ('?' if state=="touch_low" else '.')
        if 0<=x<COLS and 0<=y<ROWS:g[y][x]=c
    t=k["threat"]
    y=t["y"]
    if t["state"]=="CONTACT":
        for x in range(t["x0"], min(t["x1"],COLS-1)+1):
            g[y][x]='<' if x%2==0 else '='
    elif t["state"]=="APPROACH":
        for x in range(t["x0"], min(t["x1"],COLS-1)+1):
            g[y][x]='<' if x%3 else '-'
    else:
        for x in range(t["x0"], min(t["x1"],COLS-1)+1):
            g[y][x]='<' if x%4==0 else ' '
    note=k["motion_arc_root_note"]
    if any(w in note.lower() for w in ["root continues left","outruns","overrun","momentum"]):
        rx,ry=root
        for x in range(max(0,rx-7),rx):
            if g[ry][x]==' ': g[ry][x]='~'
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet():
    parts=[]
    parts.append("ASCII KINESIS V2 — DEFENSE027\nSLIP CONTACT / TRUST REACQUISITION\n")
    parts.append("Legend: o head | @ root/pelvis | x trusted support | ? touching but untrusted | . airborne | <=incoming threat | ~=root momentum\n")
    for k in MOTION["keys"]:
        parts.append(f'\n[{k["key_id"]}] {k["label"]}  timing={k["timing_class"]} provenance={k["timing_provenance"]}\n')
        parts.append(pose_ascii(k)+"\n")
        sc=k["support_contact"]
        parts.append(f'support L={sc["left"]} R={sc["right"]} owner={sc["support_owner"]}; contact={k["guard_contact"]["active"]}; role={k["causal_role"]}\n')
        parts.append(f'root/arc: {k["motion_arc_root_note"]}\n')
    return ''.join(parts)

def interpolate(a,b,t):
    if isinstance(a,list) and len(a)==2 and all(isinstance(v,(int,float)) for v in a):
        return [round(a[0]+(b[0]-a[0])*t),round(a[1]+(b[1]-a[1])*t)]
    if isinstance(a,list) and a and isinstance(a[0],list):
        return [interpolate(x,y,t) for x,y in zip(a,b)]
    return a

def geom_bridge(a,b,t):
    k=json.loads(json.dumps(a))
    k["pose_rig"]={name:interpolate(a["pose_rig"][name],b["pose_rig"][name],t) for name in a["pose_rig"]}
    return k

def compile_frames():
    out=[]
    ks=MOTION["keys"]
    for i,k in enumerate(ks):
        out += [k]*int(k["exposure_frames"])
        if i<len(ks)-1:
            n=int(k.get("bridge_frames_to_next",0))
            for j in range(1,n+1):
                out.append(geom_bridge(k,ks[i+1],j/(n+1)))
    return out

def render_pngs(frames,outdir):
    outdir.mkdir(exist_ok=True)
    font_paths=["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf","/usr/share/fonts/dejavu/DejaVuSansMono.ttf"]
    fp=next((p for p in font_paths if Path(p).exists()),None)
    font=ImageFont.truetype(fp,17) if fp else ImageFont.load_default()
    small=ImageFont.truetype(fp,13) if fp else ImageFont.load_default()
    for idx,k in enumerate(frames):
        img=Image.new("RGB",(W,H),"black")
        d=ImageDraw.Draw(img)
        art=pose_ascii(k)
        d.text((18,48),art,font=font,fill="white",spacing=0)
        d.text((18,10),f'{k["key_id"]}  {k["label"]}',font=small,fill="white")
        d.text((18,H-30),f'support={k["support_contact"]["support_owner"]}  threat={k["threat"]["state"]}  timing={k["timing_class"]}',font=small,fill="white")
        img.save(outdir/f"frame-{idx:04d}.png")

def encode_video(frame_dir,out):
    subprocess.run(["ffmpeg","-y","-v","error","-framerate",str(FPS),"-i",str(frame_dir/"frame-%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-preset","medium","-crf","24","-threads","1","-g","48","-bf","0","-movflags","+faststart","-map_metadata","-1",str(out)],check=True)

def spa(ascii_text,motion_text,video_bytes):
    b64=base64.b64encode(video_bytes).decode("ascii")
    import html
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>ASCII Kinesis Defense027</title>
<style>
body{{margin:0;background:#0a0a0a;color:#eee;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}}
nav{{position:sticky;top:0;background:#151515;padding:12px;border-bottom:1px solid #444}}
button{{font:inherit;margin-right:8px;padding:8px 12px}}
section{{display:none;padding:16px}} section.active{{display:block}}
pre{{white-space:pre;overflow:auto;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;line-height:1.05}}
video{{width:min(100%,800px);background:#000}}
</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre>{html.escape(ascii_text)}</pre></section>
<section id="json"><pre>{html.escape(motion_text)}</pre></section>
<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section>
<script>
const sections=[...document.querySelectorAll("section")];
for(const b of document.querySelectorAll("button[data-view]")) b.onclick=()=>{{
  for(const s of sections)s.classList.toggle("active",s.id===b.dataset.view);
}};
</script></body></html>"""

ascii_text=contact_sheet()
(ROOT/"contact-sheet.txt").write_text(ascii_text,encoding="utf-8")
frames=compile_frames()
frame_dir=ROOT/"_frames"
if frame_dir.exists(): shutil.rmtree(frame_dir)
render_pngs(frames,frame_dir)
video=ROOT/"slip-contact-trust-reacquisition.mp4"
encode_video(frame_dir,video)
motion_text=(ROOT/"motion.json").read_text(encoding="utf-8")
(ROOT/"slip-contact-trust-reacquisition.motion.html").write_text(spa(ascii_text,motion_text,video.read_bytes()),encoding="utf-8")
print(json.dumps({"frames":len(frames),"video_bytes":video.stat().st_size},sort_keys=True))
