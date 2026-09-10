#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import base64, gzip, hashlib, json, shutil, subprocess

ROOT=Path(__file__).resolve().parent
MOTION_PATH=ROOT/"motion.json"
ASCII_PATH=ROOT/"contact-sheet.txt"
BUILD=ROOT/".motion-build"
VIDEO=BUILD/"motion.mp4"
SPA=ROOT/"load-share-transfer-no-topology-change.motion.html"
W,H=64,23
CANVAS=(560,300)
TIMING_FRAMES={"ONES":1,"TWOS":2,"FOURS":4}
BONES=[("head","neck"),("neck","shoulder_l"),("neck","shoulder_r"),
("shoulder_l","elbow_l"),("elbow_l","hand_l"),("shoulder_r","elbow_r"),("elbow_r","hand_r"),
("neck","pelvis"),("pelvis","knee_l"),("knee_l","foot_l"),("pelvis","knee_r"),("knee_r","foot_r")]

def bres(p0,p1):
    x0,y0=p0;x1,y1=p1;pts=[];dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy;x0+=sx
        if e2<=dx: err+=dx;y0+=sy
    return pts

def linechar(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if abs(dx)>=2*abs(dy): return "-"
    if abs(dy)>=2*abs(dx): return "|"
    return "\\" if dx*dy>0 else "/"

def load_marks(v):
    if v<=0: return ""
    if v<.25: return "^"
    if v<.6: return "^^"
    if v<.8: return "^^^"
    return "^^^^"

def render_ascii(key):
    g=[[" "]*W for _ in range(H)]
    y=key["platform_y"]; aa,bb=key["platform_span"]
    for x in range(max(0,aa),min(W,bb+1)): g[y][x]="="
    pts=key["pose"]
    for a1,b1 in BONES:
        p0=tuple(pts[a1]);p1=tuple(pts[b1]);ch=linechar(p0,p1)
        for x1,y1 in bres(p0,p1)[1:-1]:
            if 0<=x1<W and 0<=y1<H and g[y1][x1]==" ": g[y1][x1]=ch
    for n,p in pts.items():
        x1,y1=p;c="O" if n=="head" else ("+" if n=="pelvis" else "o")
        if 0<=x1<W and 0<=y1<H:g[y1][x1]=c
    for x1,y1 in key.get("contact_markers",[]):
        if 0<=x1<W and 0<=y1<H:g[y1][x1]="*"
    cx,cy=key["com"]
    if 0<=cx<W and 0<=cy<H and g[cy][cx]==" ":g[cy][cx]="x"
    if key["contact_markers"]:
        left_x=key["contact_markers"][0][0];right_x=key["contact_markers"][-1][0]
        lm=load_marks(key["load_share"]["left"]);rm=load_marks(key["load_share"]["right"])
        for i,ch in enumerate(lm):
            x=left_x-((len(lm)-1)//2)+i
            if 0<=x<W and y+1<H:g[y+1][x]=ch
        for i,ch in enumerate(rm):
            x=right_x-((len(rm)-1)//2)+i
            if 0<=x<W and y+1<H:g[y+1][x]=ch
    cue={"RIGHT_ONSET":">>","RIGHT_MAX":">>>>","REVERSAL_JOIN":"<><>","LEFT_MAX":"<<<<","DECAY":"<<","NEAR_ZERO":".","ZERO":"","NONE":""}.get(key["base_accel"],"")
    if cue:
        for i,ch in enumerate(cue):
            if i<W:g[21][i]=ch
    return "\n".join("".join(r).rstrip() for r in g)

def font(size):
    p=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    if not p.is_file():raise SystemExit("MISSING_REQUIRED_FONT: DejaVuSansMono.ttf")
    return ImageFont.truetype(str(p),size)

def b64gzip(text):
    return base64.b64encode(gzip.compress(text.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")

def make_spa(ascii_text,motion_text,video_bytes):
    a=b64gzip(ascii_text);j=b64gzip(motion_text);v=base64.b64encode(video_bytes).decode("ascii")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Contact020 - Load Share Transfer Without Topology Change</title>
<style>
body{{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}}nav{{position:sticky;top:0;padding:10px;background:#191919;border-bottom:1px solid #555}}
button{{margin-right:8px;padding:8px 14px}}section{{display:none;padding:16px}}section.active{{display:block}}
pre{{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}
video{{max-width:100%;height:auto;border:1px solid #555}}
</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre id="ascii-out"></pre></section>
<section id="json"><pre id="json-out"></pre></section>
<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{v}"></video></section>
<script>
const A="{a}",J="{j}";
async function inflate(s){{const u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([u]).stream().pipeThrough(ds)).text();}}
Promise.all([inflate(A),inflate(J)]).then(([a,j])=>{{document.getElementById("ascii-out").textContent=a;document.getElementById("json-out").textContent=j;}});
const buttons=[...document.querySelectorAll("button[data-view]")];
for(const b of buttons)b.onclick=()=>{{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view);}};
</script></body></html>'''

def main():
    motion=json.loads(MOTION_PATH.read_text(encoding="utf-8"));ascii_text=ASCII_PATH.read_text(encoding="utf-8")
    if BUILD.exists():shutil.rmtree(BUILD)
    BUILD.mkdir();fd=BUILD/"frames";fd.mkdir()
    f9=font(9);f8=font(8);idx=0
    for key in motion["keys"]:
        art=render_ascii(key)
        for _ in range(TIMING_FRAMES[key["timing_class"]]):
            im=Image.new("RGB",CANVAS,(12,12,12));d=ImageDraw.Draw(im)
            d.text((8,6),"CONTACT020 | LOAD-SHARE TRANSFER / TOPOLOGY CONSTANT",font=f8,fill=(230,230,230))
            d.text((8,18),f'{key["key_id"]} {key["name"]} [{key["timing_class"]}]',font=f8,fill=(230,230,230))
            yy=31
            for ln in art.splitlines():
                d.text((8,yy),ln,font=f9,fill=(240,240,240));yy+=9
            ls=key["load_share"]
            d.text((8,272),f'contact={key["contact_state"]} load L/R={ls["left"]:.2f}/{ls["right"]:.2f} custody=NONE',font=f8,fill=(220,220,220))
            im.save(fd/f"{idx:04d}.png");idx+=1
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(fd/"%04d.png"),
                    "-map_metadata","-1","-c:v","libx264","-threads","1","-pix_fmt","yuv420p","-crf","42",
                    "-movflags","+faststart","-fflags","+bitexact","-flags:v","+bitexact",str(VIDEO)],check=True)
    video=VIDEO.read_bytes();got=hashlib.sha256(video).hexdigest()
    expected=motion["compile"].get("media_sha256")
    if expected and got!=expected:raise SystemExit(f"MEDIA_IDENTITY_MISMATCH: expected {expected} got {got}")
    SPA.write_text(make_spa(ascii_text,MOTION_PATH.read_text(encoding="utf-8"),video),encoding="utf-8")
    print(json.dumps({"ok":True,"frames":idx,"media_sha256":got,"media_bytes":len(video),"spa":SPA.name},sort_keys=True))
if __name__=="__main__":main()
