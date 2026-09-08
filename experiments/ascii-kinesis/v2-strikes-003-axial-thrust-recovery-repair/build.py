#!/usr/bin/env python3
from __future__ import annotations
import json, math, subprocess, hashlib, base64, gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOTION = ROOT / "motion.json"
SPA = ROOT / "axial-thrust-recovery-repair.motion.html"
MP4 = ROOT / "axial-thrust-recovery-repair.mp4"
W, H = 44, 18
FPS = 24
OUT_W, OUT_H = 1280, 720
CELL_W, CELL_H = 22, 36
OX, OY = 42, 28

FONT = {
" ": ["00000"]*7,
".": ["00000","00000","00000","00000","00000","00100","00100"],
":": ["00000","00100","00100","00000","00100","00100","00000"],
"-": ["00000","00000","00000","11111","00000","00000","00000"],
"|": ["00100","00100","00100","00100","00100","00100","00100"],
"/": ["00001","00010","00100","01000","10000","00000","00000"],
"\\":["10000","01000","00100","00010","00001","00000","00000"],
"=": ["00000","00000","11111","00000","11111","00000","00000"],
"O": ["01110","10001","10001","10001","10001","10001","01110"],
"o": ["00000","00000","01110","10001","10001","10001","01110"],
"+": ["00000","00100","00100","11111","00100","00100","00000"],
"_": ["00000","00000","00000","00000","00000","00000","11111"],
"[": ["01110","01000","01000","01000","01000","01000","01110"],
"]": ["01110","00010","00010","00010","00010","00010","01110"],
">": ["10000","01000","00100","00010","00100","01000","10000"],
"!": ["00100","00100","00100","00100","00100","00000","00100"],
}

BONES = [
("pelvis","chest"),("chest","head"),
("chest","rear_shoulder"),("rear_shoulder","rear_elbow"),("rear_elbow","rear_hand"),
("chest","front_shoulder"),("front_shoulder","front_elbow"),("front_elbow","front_hand"),
("pelvis","rear_knee"),("rear_knee","rear_foot"),
("pelvis","front_knee"),("front_knee","front_foot"),
]

def curve_t(t, name):
    if name == "ease_in": return t*t
    if name == "ease_out": return 1.0-(1.0-t)*(1.0-t)
    if name == "ease_in_out": return 3*t*t-2*t*t*t
    return t

def mix(a,b,t,curve):
    u=curve_t(t,curve)
    return {j:[a[j][0]*(1-u)+b[j][0]*u,a[j][1]*(1-u)+b[j][1]*u] for j in a}

def bresenham(p0,p1):
    x0,y0=map(lambda v:int(round(v)),p0); x1,y1=map(lambda v:int(round(v)),p1)
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    out=[]
    while True:
        out.append((x0,y0))
        if x0==x1 and y0==y1: return out
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def line_char(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>=2*abs(dy): return "-"
    if abs(dy)>=2*abs(dx): return "|"
    return "\\" if dx*dy>0 else "/"

def ascii_frame(j):
    g=[[" "]*W for _ in range(H)]
    for x in range(W): g[16][x]="."
    for y in range(4,14): g[y][40]=":"
    for a,b in BONES:
        c=line_char(j[a],j[b])
        for x,y in bresenham(j[a],j[b]):
            if 0<=x<W and 0<=y<H and g[y][x]==" ": g[y][x]=c
    for x,y in bresenham(j["tool_butt"],j["tool_tip"]):
        if 0<=x<W and 0<=y<H: g[y][x]="="
    for name,sym in {
        "head":"O","pelvis":"+","rear_hand":"o","front_hand":"o",
        "rear_foot":"_","front_foot":"_","tool_butt":"[","tool_tip":">",
    }.items():
        x,y=map(lambda v:int(round(v)),j[name])
        if 0<=x<W and 0<=y<H: g[y][x]=sym
    tx,ty=map(lambda v:int(round(v)),j["tool_tip"])
    if tx>=40 and 0<=ty<H: g[ty][40]="!"
    return ["".join(row) for row in g]

def compile_frames(m):
    hold={"ONES":1,"TWOS":2,"FOURS":4}
    ks=m["keys"]; ts=m["transitions"]
    frames=[]
    provenance=[]
    for i,k in enumerate(ks):
        for n in range(hold[k["timing_class"]]):
            frames.append(k["joints"]); provenance.append({"kind":"HOLD","key_id":k["key_id"],"hold_index":n})
        if i < len(ks)-1:
            t=ts[i]; count=int(t["connective_frames"])
            for n in range(1,count+1):
                frames.append(mix(k["joints"],ks[i+1]["joints"],n/(count+1),t["curve"]))
                provenance.append({"kind":"CONNECTIVE","from":k["key_id"],"to":ks[i+1]["key_id"],"index":n})
    return frames, provenance

def put_rect(buf,x0,y0,x1,y1,v=238):
    x0=max(0,x0);y0=max(0,y0);x1=min(OUT_W,x1);y1=min(OUT_H,y1)
    for y in range(y0,y1):
        row=(y*OUT_W+x0)*3
        for x in range(x0,x1):
            buf[row]=v;buf[row+1]=v;buf[row+2]=v;row+=3

def raster(lines):
    buf=bytearray(OUT_W*OUT_H*3)
    for gy,line in enumerate(lines):
        for gx,ch in enumerate(line):
            pat=FONT.get(ch,FONT[" "])
            px=OX+gx*CELL_W; py=OY+gy*CELL_H
            sx=max(1,CELL_W//7); sy=max(1,CELL_H//9)
            for yy,row in enumerate(pat):
                for xx,b in enumerate(row):
                    if b=="1":
                        put_rect(buf,px+xx*sx,py+yy*sy,px+(xx+1)*sx,py+(yy+1)*sy)
    return bytes(buf)

def encode_mp4(frames):
    cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pixel_format","rgb24",
         "-video_size",f"{OUT_W}x{OUT_H}","-framerate",str(FPS),"-i","-",
         "-an","-c:v","libx264","-preset","veryslow","-crf","28","-pix_fmt","yuv420p",
         "-movflags","+faststart",str(MP4)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for j in frames:
            p.stdin.write(raster(ascii_frame(j)))
    finally:
        p.stdin.close()
    rc=p.wait()
    if rc: raise SystemExit(rc)

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def build_spa(m, contact):
    b64=base64.b64encode(MP4.read_bytes()).decode("ascii")
    ascii_gz=base64.b64encode(gzip.compress(contact.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    json_gz=base64.b64encode(gzip.compress(json.dumps(m,separators=(",",":"),ensure_ascii=False).encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Strikes 003 — Axial Thrust Recovery Repair</title><style>:root{{color-scheme:dark;background:#090909;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0}}nav{{position:sticky;top:0;display:flex;gap:.5rem;padding:.65rem;background:#111;border-bottom:1px solid #444}}button{{font:inherit;padding:.55rem .85rem;background:#181818;color:#eee;border:1px solid #555;border-radius:.4rem}}section{{display:none;padding:1rem}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.12;font-size:12px}}video{{display:block;max-width:100%;height:auto;background:#000}}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="asciiText">loading…</pre></section><section id="json"><pre id="jsonText">loading…</pre></section><section id="video"><video controls loop playsinline src="data:video/mp4;base64,{b64}"></video></section><script>const ASCII_GZ="{ascii_gz}";const JSON_GZ="{json_gz}";async function gunzip64(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}}Promise.all([gunzip64(ASCII_GZ),gunzip64(JSON_GZ)]).then(([a,j])=>{{document.getElementById("asciiText").textContent=a;document.getElementById("jsonText").textContent=JSON.stringify(JSON.parse(j),null,2);}});const tabs=["ascii","json","video"];document.querySelectorAll("button[data-view]").forEach(b=>b.onclick=()=>tabs.forEach(id=>document.getElementById(id).classList.toggle("active",id===b.dataset.view)));</script></body></html>"""

def main():
    m=json.loads(MOTION.read_text(encoding="utf-8"))
    contact=(ROOT/"contact_sheet.txt").read_text(encoding="utf-8")
    frames, provenance=compile_frames(m)
    if len(frames)!=m["media"]["frame_count"]: raise SystemExit(f"frame count mismatch {len(frames)}")
    encode_mp4(frames)
    actual=sha256(MP4)
    print(json.dumps({"frames":len(frames),"media_sha256":actual,"bytes":MP4.stat().st_size},sort_keys=True))
    SPA.write_text(build_spa(m,contact),encoding="utf-8")

if __name__=="__main__":
    main()
