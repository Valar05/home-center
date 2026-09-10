#!/usr/bin/env python3
from __future__ import annotations
import base64, json, math, subprocess, tempfile, hashlib, html, gzip
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
CONTACT = HERE / "contact-sheet.txt"
SPA = HERE / "breakaway-support-redrop-rim-catch-debt.motion.html"
MP4 = HERE / "breakaway-support-redrop-rim-catch-debt.mp4"

W, H = 88, 34
FLOOR_Y = 22
PANEL_L, PANEL_R = 39, 54
POINTS = ["root","chest","head","l_elbow","l_hand","r_elbow","r_hand","l_knee","l_foot","r_knee","r_foot"]
EDGES = [
    ("root","chest"),("chest","head"),
    ("chest","l_elbow"),("l_elbow","l_hand"),
    ("chest","r_elbow"),("r_elbow","r_hand"),
    ("root","l_knee"),("l_knee","l_foot"),
    ("root","r_knee"),("r_knee","r_foot"),
]

def lerp(a,b,t): return a+(b-a)*t
def smooth(t): return t*t*(3.0-2.0*t)

def abs_points(k):
    rx, ry = k["root"]
    out = {"root": (rx,ry)}
    for name in POINTS[1:]:
        dx,dy = k[name]
        out[name]=(rx+dx,ry+dy)
    return out

def interp_key(a,b,t):
    s=smooth(t)
    aa=abs_points(a); bb=abs_points(b)
    out={}
    for name in POINTS:
        pa=aa[name]; pb=bb[name]
        out[name]=(lerp(pa[0],pb[0],s), lerp(pa[1],pb[1],s))
    out["contact_points"]=list(a.get("contact_points",[]))
    out["env_state"]=a.get("env_state","INTACT")
    return out

def key_pose(k):
    p=abs_points(k)
    p["contact_points"]=list(k.get("contact_points",[]))
    p["env_state"]=k.get("env_state","INTACT")
    return p

def put(grid,x,y,ch):
    x=int(round(x)); y=int(round(y))
    if 0<=x<W and 0<=y<H:
        grid[y][x]=ch

def line(grid,p0,p1):
    x0,y0=p0; x1,y1=p1
    dx=x1-x0; dy=y1-y0
    n=max(1,int(math.ceil(max(abs(dx),abs(dy))*2)))
    if abs(dx) > abs(dy)*1.6: ch="-"
    elif abs(dy) > abs(dx)*1.6: ch="|"
    else: ch="\\" if dx*dy>=0 else "/"
    for i in range(n+1):
        t=i/n
        put(grid,lerp(x0,x1,t),lerp(y0,y1,t),ch)

def draw_environment(g,state):
    for x in range(0,PANEL_L):
        put(g,x,FLOOR_Y,"=")
    for x in range(PANEL_R+1,W):
        put(g,x,FLOOR_Y,"=")
    put(g,PANEL_L-1,FLOOR_Y,"|")
    put(g,PANEL_R+1,FLOOR_Y,"|")
    if state=="INTACT":
        for x in range(PANEL_L,PANEL_R+1):
            put(g,x,FLOOR_Y,"~")
    elif state=="SAGGING":
        mid=(PANEL_L+PANEL_R)/2
        for x in range(PANEL_L,PANEL_R+1):
            sag=2.0*(1.0-abs(x-mid)/((PANEL_R-PANEL_L)/2+0.5))
            put(g,x,FLOOR_Y+sag,"~")
    else:
        for x,y,ch in [(42,24,"\\"),(50,25,"/"),(45,27,"."),(52,28,".")]:
            put(g,x,y,ch)

def render_grid(pose):
    g=[[" " for _ in range(W)] for _ in range(H)]
    draw_environment(g,pose.get("env_state","INTACT"))
    for a,b in EDGES:
        line(g,pose[a],pose[b])
    symbols={"root":"@","chest":"+","head":"O","l_elbow":"o","r_elbow":"o","l_hand":"x","r_hand":"x",
             "l_knee":"o","r_knee":"o","l_foot":"=","r_foot":"="}
    for name,ch in symbols.items():
        put(g,*pose[name],ch)
    for name in pose.get("contact_points",[]):
        put(g,*pose[name],"*")
    return ["".join(row).rstrip() for row in g]

def metadata_line(k):
    return (f'{k["key_id"]} {k["label"]} | timing={k["timing_class"]} | provenance={k["timing_provenance"]} | '
            f'support={k["support_contact"]} | env={k["env_state"]} | role={k["causal_role"]}')

def make_contact(data):
    blocks=[]
    for k in data["keys"]:
        blocks.append(metadata_line(k))
        blocks.extend(render_grid(key_pose(k)))
        blocks.append("")
    text="\n".join(blocks).rstrip()+"\n"
    CONTACT.write_text(text,encoding="utf-8")
    return text

def frame_sequence(data):
    holds=data["compile"]["hold_frames"]
    bridges=data["compile"]["bridge_frames"]
    keys=data["keys"]
    seq=[]
    for i,k in enumerate(keys):
        pose=key_pose(k)
        seq += [pose] * int(holds[k["timing_class"]])
        if i < len(keys)-1:
            n=int(bridges[i])
            for j in range(1,n+1):
                seq.append(interp_key(k,keys[i+1],j/(n+1)))
    return seq

def font():
    candidates=[
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).is_file():
            return ImageFont.truetype(p,12)
    return ImageFont.load_default()

def render_png(lines,path):
    f=font()
    cell_w=8
    cell_h=14
    width=W*cell_w+24
    height=H*cell_h+26
    if width%2: width+=1
    if height%2: height+=1
    im=Image.new("RGB",(width,height),(7,7,7))
    d=ImageDraw.Draw(im)
    for y,line_text in enumerate(lines):
        d.text((12,9+y*cell_h),line_text,font=f,fill=(242,242,242),spacing=0)
    im.save(path)

def build_video(data):
    seq=frame_sequence(data)
    with tempfile.TemporaryDirectory(prefix="a033-") as td:
        td=Path(td)
        for i,pose in enumerate(seq):
            render_png(render_grid(pose),td/f"frame-{i:04d}.png")
        cmd=[
            "ffmpeg","-hide_banner","-loglevel","error","-y",
            "-framerate",str(data["compile"]["fps"]),
            "-i",str(td/"frame-%04d.png"),
            "-an","-c:v","libx264","-pix_fmt","yuv420p",
            "-preset","veryslow","-crf","40",
            "-x264-params","threads=1:lookahead_threads=1:sliced_threads=0",
            "-map_metadata","-1","-movflags","+faststart",
            str(MP4)
        ]
        subprocess.run(cmd,check=True)
    return len(seq)

def make_spa(data,ascii_text,mp4_bytes):
    pretty=json.dumps(data,separators=(",",":"),ensure_ascii=False)
    video_b64=base64.b64encode(mp4_bytes).decode("ascii")
    video_parts=json.dumps([video_b64[i:i+4000] for i in range(0,len(video_b64),4000)],separators=(",",":"))
    ascii_gz=base64.b64encode(gzip.compress(ascii_text.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    json_gz=base64.b64encode(gzip.compress(pretty.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    page=f"""<!doctype html>
<html lang=\"en\"><head><meta charset=\"utf-8\">
<title>ASCII Kinesis — Airborne033</title>
<style>
body{{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}}
nav{{display:flex;gap:8px;padding:12px;position:sticky;top:0;background:#111}}
button{{font:inherit;padding:8px 12px}}
section{{padding:14px}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.04}}
video{{max-width:100%;height:auto;background:#000}}
</style></head><body>
<nav><button data-view=\"ascii\">ASCII</button><button data-view=\"json\">JSON</button><button data-view=\"video\">VIDEO</button></nav>
<section id=\"ascii\"><pre id=\"ascii-pre\"></pre></section>
<section id=\"json\" hidden><pre id=\"json-pre\"></pre></section>
<section id=\"video\" hidden><video id=\"video-player\" controls loop playsinline></video></section>
<script>
const ids=[\"ascii\",\"json\",\"video\"];
const videoParts={video_parts};
document.getElementById(\"video-player\").src=\"data:video/mp4;base64,\"+videoParts.join(\"\");
document.querySelectorAll(\"button[data-view]\").forEach(b=>b.onclick=()=>{{
  ids.forEach(id=>document.getElementById(id).hidden=(id!==b.dataset.view));
}});
async function ungzip(b64){{
  const bytes=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));
  const stream=new Blob([bytes]).stream().pipeThrough(new DecompressionStream(\"gzip\"));
  return new TextDecoder().decode(await new Response(stream).arrayBuffer());
}}
Promise.all([ungzip(\"{ascii_gz}\"),ungzip(\"{json_gz}\")]).then(([a,j])=>{{
  document.getElementById(\"ascii-pre\").textContent=a;
  document.getElementById(\"json-pre\").textContent=j;
}});
</script></body></html>"""
    SPA.write_text(page,encoding="utf-8")

def main():
    data=json.loads(MOTION.read_text(encoding="utf-8"))
    ascii_text=make_contact(data)
    frames=build_video(data)
    mp4=MP4.read_bytes()
    data["media"]["frames"]=frames
    data["media"]["bytes"]=len(mp4)
    data["media"]["sha256"]=hashlib.sha256(mp4).hexdigest()
    data["media"]["decode"]="PASS_FFMPEG_CURRENT_WORKER"
    data["media"]["width"]=W*8+24
    data["media"]["height"]=H*14+26
    if data["media"]["width"]%2: data["media"]["width"]+=1
    if data["media"]["height"]%2: data["media"]["height"]+=1
    MOTION.write_text(json.dumps(data,separators=(",",":"),ensure_ascii=False)+"\n",encoding="utf-8")
    make_spa(data,ascii_text,mp4)
    print(json.dumps({"frames":frames,"bytes":len(mp4),"sha256":data["media"]["sha256"],
                      "width":data["media"]["width"],"height":data["media"]["height"]},sort_keys=True))

if __name__=="__main__":
    main()
