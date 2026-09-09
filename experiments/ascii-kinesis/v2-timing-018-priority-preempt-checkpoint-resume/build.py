#!/usr/bin/env python3
from pathlib import Path
import base64, gzip, hashlib, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
motion = json.loads((HERE / "motion.json").read_text(encoding="utf-8"))
W, H = motion["rig"]["grid"]
ORDER = motion["rig"]["joint_order"]

def line_points(x0, y0, x1, y1):
    pts = []
    dx, sx = abs(x1-x0), 1 if x0 < x1 else -1
    dy, sy = -abs(y1-y0), 1 if y0 < y1 else -1
    err, x, y = dx+dy, x0, y0
    while True:
        pts.append((x,y))
        if x == x1 and y == y1: break
        e2 = 2*err
        if e2 >= dy: err += dy; x += sx
        if e2 <= dx: err += dx; y += sy
    return pts

def draw_line(g, a, b):
    x0,y0=a; x1,y1=b
    c = "|" if x0==x1 else "-" if y0==y1 else ("\\" if (x1-x0)*(y1-y0)>0 else "/")
    for x,y in line_points(x0,y0,x1,y1)[1:-1]:
        if 0 <= x < W and 0 <= y < H and g[y][x] == " ": g[y][x] = c

def scene(key):
    g = [[" "]*W for _ in range(H)]
    for x in range(W): g[motion["rig"]["ground_y"]][x] = "_"
    wx = motion["rig"]["wall_x"]
    for y in range(2,15):
        if 0 <= wx < W: g[y][wx] = "|"
    for x,y,ch in [(wx-1,2,"+"),(wx+1,2,"+"),(wx-1,14,"+"),(wx+1,14,"+")]:
        if 0 <= x < W and 0 <= y < H: g[y][x]=ch
    for x in (wx-1,wx+1):
        for y in range(3,14):
            if 0 <= x < W and g[y][x]==" ": g[y][x]="|"
    pivot=tuple(motion["rig"]["lever_pivot"]); tip=tuple(key["station_handle_tip"])
    draw_line(g,pivot,tip)
    g[pivot[1]][pivot[0]]="@"; g[tip[1]][tip[0]]="o"
    vals=key["joints"]; j={name:(vals[i*2],vals[i*2+1]) for i,name in enumerate(ORDER)}
    links=[("neck","pelvis"),("l_shoulder","l_elbow"),("l_elbow","l_hand"),("r_shoulder","r_elbow"),("r_elbow","r_hand"),
           ("pelvis","l_knee"),("l_knee","l_foot"),("pelvis","r_knee"),("r_knee","r_foot"),("l_shoulder","r_shoulder")]
    for a,b in links: draw_line(g,j[a],j[b])
    for name,ch in [("head","O"),("neck","+"),("pelvis","#"),("l_hand","*"),("r_hand","*"),("l_foot","/"),("r_foot","\\")]:
        x,y=j[name]; g[y][x]=ch
    for name in ("l_shoulder","r_shoulder","l_elbow","r_elbow","l_knee","r_knee"):
        x,y=j[name]; g[y][x]="+"
    if key.get("interrupt_aux"):
        hx,hy=j["head"]
        for i,ch in enumerate("<<<"):
            x=max(0,hx-8+i); y=hy+2
            if 0<=x<W and 0<=y<H: g[y][x]=ch
        x,y=hx-4,hy+1
        if 0<=x<W and 0<=y<H: g[y][x]="!"
    return "\n".join("".join(row).rstrip() for row in g).rstrip()+"\n"

def contact_sheet():
    out=[]
    for k in motion["keys"]:
        out.append(f"{k['key_id']} {k['causal_role']} {k['timing_class']}/{k['exposure_ticks']}t AUTH={k['authority_state']} CHECKPOINT={k['progress_checkpoint']} SUPPORT={k['support_contact']}\n")
        out.append(scene(k))
        out.append("-"*96+"\n")
    return "".join(out)

def render_video():
    frames=HERE/".frames"
    if frames.exists(): shutil.rmtree(frames)
    frames.mkdir()
    candidates=[Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf")]
    fp=next((p for p in candidates if p.exists()),None)
    if not fp: raise SystemExit("monospace font unavailable")
    font=ImageFont.truetype(str(fp),8); footer=ImageFont.truetype(str(fp),7)
    n=0
    for k in motion["keys"]:
        rig=scene(k)
        for _ in range(int(k["exposure_ticks"])):
            im=Image.new("RGB",(320,180),"white"); d=ImageDraw.Draw(im)
            d.multiline_text((6,4),rig,fill="black",font=font,spacing=0)
            im.save(frames/f"frame_{n:04d}.png"); n+=1
    out=HERE/"priority-preempt-checkpoint-resume.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(frames/"frame_%04d.png"),
                    "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","35","-map_metadata","-1",str(out)],check=True)
    return out,n

video,count=render_video()
actual=hashlib.sha256(video.read_bytes()).hexdigest()
declared=motion["compile"]["media"]["sha256"]
if actual != declared: raise SystemExit(f"MEDIA_IDENTITY_MISMATCH declared={declared} actual={actual}")
if count != int(motion["compile"]["media"]["frames"]): raise SystemExit("FRAME_COUNT_MISMATCH")
sheet=contact_sheet()
(HERE/"contact-sheet.txt").write_text(sheet,encoding="utf-8")
motion_raw=(HERE/"motion.json").read_bytes()
motion_gz=base64.b64encode(gzip.compress(motion_raw,mtime=0)).decode("ascii")
sheet_gz=base64.b64encode(gzip.compress(sheet.encode("utf-8"),mtime=0)).decode("ascii")
b64=base64.b64encode(video.read_bytes()).decode("ascii")
page=f"""<!doctype html><meta charset="utf-8"><title>Timing018 priority preempt checkpoint resume</title><style>body{{font-family:system-ui;margin:0}}nav{{display:flex;gap:.5rem;padding:.75rem}}section{{display:none;padding:1rem}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto}}video{{max-width:100%}}</style><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section><script>async function u(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}};(async()=>{{a.textContent=await u("{sheet_gz}");j.textContent=JSON.stringify(JSON.parse(await u("{motion_gz}")),null,2)}})();for(const b of document.querySelectorAll("button"))b.onclick=()=>{{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view)}};</script>"""
(HERE/"priority-preempt-checkpoint-resume.motion.html").write_text(page,encoding="utf-8")
print(json.dumps({"schema":"ascii-kinesis.motion-dungeon-build","ok":True,"media_sha256":actual,"frames":count,
                  "contact_sheet_sha256":hashlib.sha256(sheet.encode()).hexdigest(),"spa_sha256":hashlib.sha256(page.encode()).hexdigest()},sort_keys=True))
