#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, math, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOTION_PATH = ROOT / "motion.json"
CONTACT_PATH = ROOT / "contact_sheet.txt"
SPA_PATH = ROOT / "shove-it-dual-clock-recapture-repair.motion.html"
TEMP_MP4 = ROOT / ".motion-build.mp4"
W, H = 54, 22
FPS = 24
GROUND_Y = 20
CELL_W, CELL_H = 8, 10
VIDEO_W, VIDEO_H = W * CELL_W, H * CELL_H
FONT = {
    'O':["01110","10001","10011","10101","11001","10001","01110"],
    '@':["01110","10001","10111","10101","10111","10000","01111"],
    'o':["00000","01110","01010","01110","00000","00000","00000"],
    '|':["00100","00100","00100","00100","00100","00100","00100"],
    '-':["00000","00000","00000","11111","00000","00000","00000"],
    '_':["00000","00000","00000","00000","00000","00000","11111"],
    '/':["00001","00010","00100","01000","10000","00000","00000"],
    '\\':["10000","01000","00100","00010","00001","00000","00000"],
    '=':["00000","11111","00000","11111","00000","00000","00000"],
    '+':["00000","00100","00100","11111","00100","00100","00000"],
    '#':["01010","11111","01010","11111","01010","00000","00000"],
    'A':["01110","10001","10001","11111","10001","10001","10001"],
    'B':["11110","10001","10001","11110","10001","10001","11110"],
    ' ':["00000"]*7,
}
JOINT_MARKERS = {
    "head":"O","neck":"o","root":"@",
    "left_shoulder":"o","left_elbow":"o","left_hand":"+",
    "right_shoulder":"o","right_elbow":"o","right_hand":"+",
    "left_knee":"o","left_foot":"+","right_knee":"o","right_foot":"+",
}
EDGES = [
    ("head","neck"),("neck","root"),
    ("neck","left_shoulder"),("left_shoulder","left_elbow"),("left_elbow","left_hand"),
    ("neck","right_shoulder"),("right_shoulder","right_elbow"),("right_elbow","right_hand"),
    ("root","left_knee"),("left_knee","left_foot"),
    ("root","right_knee"),("right_knee","right_foot"),
]

def sha256_bytes(data: bytes)->str:
    return hashlib.sha256(data).hexdigest()

def line(grid, a, b, glyph=None):
    x0,y0 = map(int,a); x1,y1 = map(int,b)
    dx=abs(x1-x0); dy=-abs(y1-y0)
    sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<H and grid[y0][x0]==' ':
            if glyph:
                ch=glyph
            elif x0==x1:
                ch='|'
            elif y0==y1:
                ch='-'
            else:
                ch='\\' if (x1-x0)*(y1-y0)>0 else '/'
            grid[y0][x0]=ch
        if x0==x1 and y0==y1:
            break
        e2=2*err
        if e2>=dy:
            err+=dy; x0+=sx
        if e2<=dx:
            err+=dx; y0+=sy

def pose_grid(key):
    g=[[' ']*W for _ in range(H)]
    for x in range(W):
        g[GROUND_Y][x]='_'
    j=key["joints"]
    for a,b in EDGES:
        line(g,j[a],j[b])
    board=key["board"]
    cx,cy=map(int,board["center"]); half=int(board["half_length"]); yaw=float(board["yaw_deg"]) % 360.0
    projected=max(1,int(round(half*abs(math.cos(math.radians(yaw))))))
    ax=max(0,cx-projected); bx=min(W-1,cx+projected)
    if ax==bx:
        ax=max(0,cx-1); bx=min(W-1,cx+1)
    line(g,(ax,cy),(bx,cy),'=')
    if 0<=cy<H and 0<=cx<W:
        g[cy][cx]='#'
    left_marker,right_marker=('A','B') if math.cos(math.radians(yaw))>=0 else ('B','A')
    if 0<=cy<H and 0<=ax<W: g[cy][ax]=left_marker
    if 0<=cy<H and 0<=bx<W: g[cy][bx]=right_marker
    for name,marker in JOINT_MARKERS.items():
        x,y=map(int,j[name])
        if 0<=x<W and 0<=y<H:
            g[y][x]=marker
    return [''.join(r) for r in g]

def contact_sheet(motion):
    out=[
        motion["title"],
        motion["experiment_id"]+" | abstract ASCII rig only | source pixels/audio absent",
        "Observed source presentation evidence is provenance only; every decisive compile timing and acting key below is INFERRED.",
        ""
    ]
    for k in motion["keys"]:
        out += [
            f'{k["key_id"]} {k["causal_role"]} | {k["timing_class"]}/{k["timing_provenance"]}',
            f'SUPPORT: {k["support_contact"]}',
            f'BODY CLOCK: {k["body_clock"]}',
            f'BOARD CLOCK: {k["board_clock"]}',
            *pose_grid(k),
            f'ROOT/ARC: {k["root_arc_note"]}',
            ""
        ]
    return "\n".join(out).rstrip()+"\n"

def deep_copy(v):
    return json.loads(json.dumps(v))

def quad(v0,v1,arc,t):
    return v0+(v1-v0)*t + 4.0*t*(1.0-t)*arc

def same_semantics(a,b):
    return a["semantic_group"]==b["semantic_group"] and not a.get("causal_boundary_to_next",False)

def interpolate(a,b,t):
    if not same_semantics(a,b):
        return deep_copy(a)
    out=deep_copy(a)
    arc=a.get("transition_arc",[0,0])
    for name,p in a["joints"].items():
        q=b["joints"][name]
        out["joints"][name]=[
            int(round(quad(p[0],q[0],arc[0],t))),
            int(round(quad(p[1],q[1],arc[1],t)))
        ]
    p=a["board"]["center"]; q=b["board"]["center"]
    out["board"]["center"]=[
        int(round(quad(p[0],q[0],arc[0]*0.5,t))),
        int(round(quad(p[1],q[1],arc[1]*0.5,t)))
    ]
    aa=a["board"]["yaw_deg"]; bb=b["board"]["yaw_deg"]
    out["board"]["yaw_deg"]=aa+(bb-aa)*(t*t*(3-2*t))
    return out

def compile_frames(keys):
    frames=[]
    for i,k in enumerate(keys):
        for _ in range(int(k["hold_frames"])):
            frames.append(pose_grid(k))
        if i==len(keys)-1:
            continue
        nxt=keys[i+1]
        travel=int(k.get("travel_frames_to_next",0))
        if travel<=0:
            continue
        if not same_semantics(k,nxt):
            for _ in range(travel):
                frames.append(pose_grid(k))
            continue
        for s in range(1,travel+1):
            t=s/(travel+1)
            frames.append(pose_grid(interpolate(k,nxt,t)))
    return frames

def ppm_bytes(lines):
    width,height=VIDEO_W,VIDEO_H
    pix=bytearray([246,246,246])*(width*height)
    def setpx(x,y,v=20):
        if 0<=x<width and 0<=y<height:
            idx=(y*width+x)*3
            pix[idx:idx+3]=bytes((v,v,v))
    for gy,row in enumerate(lines):
        for gx,ch in enumerate(row):
            glyph=FONT.get(ch,FONT[' '])
            ox=gx*CELL_W+1; oy=gy*CELL_H+1
            for yy,bits in enumerate(glyph):
                for xx,bit in enumerate(bits):
                    if bit=='1':
                        setpx(ox+xx,oy+yy)
    return f"P6\n{width} {height}\n255\n".encode()+bytes(pix)

def render_mp4(frames,out_path):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,frame in enumerate(frames):
            (td/f"{i:04d}.ppm").write_bytes(ppm_bytes(frame))
        subprocess.run([
            "ffmpeg","-y","-loglevel","error",
            "-framerate",str(FPS),"-i",str(td/"%04d.ppm"),
            "-an","-c:v","libx264","-pix_fmt","yuv420p",
            "-profile:v","baseline","-level","3.0",
            "-movflags","+faststart","-map_metadata","-1",
            str(out_path)
        ],check=True)

def make_spa(contact,motion,media):
    payload=base64.b64encode(media).decode("ascii")
    motion_text=json.dumps(motion,indent=2,sort_keys=True)
    title=html.escape(motion["title"])
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
:root{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;background:#f5f5f2;color:#151515}}
*{{box-sizing:border-box}} body{{margin:0;min-height:100vh}} header{{padding:1rem;border-bottom:1px solid #aaa}}
h1{{font-size:1rem;margin:.1rem 0 .35rem}} .sub{{font-size:.8rem;max-width:86ch}}
nav{{display:flex;gap:.4rem;padding:.6rem 1rem;border-bottom:1px solid #aaa;position:sticky;top:0;background:#f5f5f2;z-index:2}}
button{{font:inherit;padding:.45rem .8rem}} main{{padding:1rem}} section[hidden]{{display:none}}
pre{{font:12px/1.08 ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2}}
video{{display:block;width:min(100%,864px);height:auto;background:#fff;border:1px solid #999}}
.note{{font-size:.78rem;max-width:86ch;line-height:1.4}}
</style></head><body>
<header><h1>{title}</h1><div class="sub">Video Motion 009 repair · Wikimedia Commons Shove it.webm / TheContreOfficial / CC BY 3.0 · source pixels/audio excluded from output</div></header>
<nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav>
<main>
<section id="ascii"><pre>{html.escape(contact)}</pre></section>
<section id="json" hidden><pre>{html.escape(motion_text)}</pre></section>
<section id="video" hidden><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{payload}"></video><p class="note">Motion Dungeon output: abstract ASCII rig + structured inferred timing only. No source video frames, pixels, audio, tracing, face, costume, or source layout are embedded.</p></section>
</main>
<script>
const buttons=[...document.querySelectorAll('button[data-view]')], sections=[...document.querySelectorAll('main>section')];
buttons.forEach(b=>b.addEventListener('click',()=>{{buttons.forEach(x=>x.setAttribute('aria-selected',String(x===b)));sections.forEach(s=>s.hidden=s.id!==b.dataset.view;}}));
</script></body></html>'''

def main():
    motion=json.loads(MOTION_PATH.read_text())
    contact=contact_sheet(motion)
    CONTACT_PATH.write_text(contact)
    frames=compile_frames(motion["keys"])
    render_mp4(frames,TEMP_MP4)
    subprocess.run(["ffmpeg","-v","error","-i",str(TEMP_MP4),"-f","null","-"],check=True)
    media=TEMP_MP4.read_bytes()
    motion["timing"]["total_frames"]=len(frames)
    motion["timing"]["duration_s"]=len(frames)/FPS
    motion["media"]={
        "authoritative":"embedded_mp4_in_spa",
        "tracked_mp4":False,
        "sha256":sha256_bytes(media),
        "bytes":len(media),
        "codec":"H.264",
        "pixel_format":"yuv420p",
        "width":VIDEO_W,
        "height":VIDEO_H,
        "fps":FPS,
        "frame_count":len(frames),
        "duration_s":len(frames)/FPS,
        "source":"abstract_ascii_rig_only",
        "decode_verified":True
    }
    MOTION_PATH.write_text(json.dumps(motion,indent=2,sort_keys=True)+"\n")
    spa=make_spa(contact,motion,media)
    SPA_PATH.write_text(spa)
    print(json.dumps({
        "frames":len(frames),"duration_s":len(frames)/FPS,
        "media_sha256":sha256_bytes(media),"media_bytes":len(media),
        "spa_bytes":len(spa.encode()),"contact_bytes":len(contact.encode())
    },sort_keys=True))

if __name__=="__main__":
    main()
