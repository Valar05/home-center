#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, html, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOTION = ROOT / "motion.json"
CONTACT = ROOT / "contact_sheet.txt"
SPA = ROOT / "contact-pin-disengage-causality-repair.motion.html"
MP4 = ROOT / "contact-pin-disengage-causality-repair.mp4"
FPS = 24
OUT_W, OUT_H = 720, 400
CELL_W, CELL_H = 12, 17
OX, OY = 32, 18

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
">": ["10000","01000","00100","00010","00100","01000","10000"],
"!": ["00100","00100","00100","00100","00100","00000","00100"],
}

def curve_t(t, name):
    if name == "ease_in": return t*t
    if name == "ease_out": return 1.0-(1.0-t)*(1.0-t)
    if name == "ease_in_out": return 3*t*t-2*t*t*t
    return t

def bresenham(p0,p1):
    x0,y0=map(lambda v:int(round(v)),p0); x1,y1=map(lambda v:int(round(v)),p1)
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy; out=[]
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

def mix(a,b,t,curve):
    u=curve_t(t,curve)
    return {j:[a[j][0]*(1-u)+b[j][0]*u,a[j][1]*(1-u)+b[j][1]*u] for j in a}

def ascii_frame(m, joints, contact_state="CLEAR"):
    W,H=m["rig"]["grid"]["width"],m["rig"]["grid"]["height"]
    impact_x=m["rig"]["impact_plane"]["x"]
    g=[[" "]*W for _ in range(H)]
    for x in range(W): g[18][x]="."
    for y in range(4,16): g[y][impact_x]=":"
    for a,b in m["rig"]["bones"]:
        c=line_char(joints[a],joints[b])
        for x,y in bresenham(joints[a],joints[b]):
            if 0<=x<W and 0<=y<H and g[y][x]==" ": g[y][x]=c
    for x,y in bresenham(joints["tool_butt"],joints["tool_tip"]):
        if 0<=x<W and 0<=y<H: g[y][x]="="
    for name,sym in {
        "head":"O","pelvis":"+","rear_hand":"o","front_hand":"o",
        "rear_foot":"_","front_foot":"_","tool_butt":"[","tool_tip":">",
    }.items():
        x,y=map(lambda v:int(round(v)),joints[name])
        if 0<=x<W and 0<=y<H: g[y][x]=sym
    if contact_state=="PINNED":
        x,y=map(lambda v:int(round(v)),joints["tool_tip"])
        if 0<=x<W and 0<=y<H: g[y][x]="!"
    return ["".join(row) for row in g]

def compile_frames(m):
    hold=m["motion_dungeon"]["hold_frames_by_class"]
    ks=m["keys"]; ts=m["transitions"]
    frames=[]; provenance=[]
    for i,k in enumerate(ks):
        for n in range(hold[k["timing_class"]]):
            frames.append((k["joints"],k["contact_state"]))
            provenance.append({"kind":"HOLD","key_id":k["key_id"],"hold_index":n})
        if i < len(ks)-1:
            t=ts[i]; count=int(t["connective_frames"])
            for n in range(1,count+1):
                joints=mix(k["joints"],ks[i+1]["joints"],n/(count+1),t["curve"])
                state=k["contact_state"] if k["contact_state"]==ks[i+1]["contact_state"] else "CLEAR"
                frames.append((joints,state))
                provenance.append({"kind":"CONNECTIVE","from":k["key_id"],"to":ks[i+1]["key_id"],"index":n})
    return frames,provenance

def put_rect(buf,x0,y0,x1,y1,v=242):
    x0=max(0,x0); y0=max(0,y0); x1=min(OUT_W,x1); y1=min(OUT_H,y1)
    for y in range(y0,y1):
        idx=(y*OUT_W+x0)*3
        for _ in range(x0,x1):
            buf[idx]=v; buf[idx+1]=v; buf[idx+2]=v; idx+=3

def raster(lines):
    buf=bytearray(OUT_W*OUT_H*3)
    sx,sy=2,2
    for gy,line in enumerate(lines):
        for gx,ch in enumerate(line):
            pat=FONT.get(ch,FONT[" "])
            px=OX+gx*CELL_W; py=OY+gy*CELL_H
            for yy,row in enumerate(pat):
                for xx,b in enumerate(row):
                    if b=="1":
                        put_rect(buf,px+xx*sx,py+yy*sy,px+(xx+1)*sx,py+(yy+1)*sy)
    return bytes(buf)

def encode_mp4(m, frames):
    cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pixel_format","rgb24",
         "-video_size",f"{OUT_W}x{OUT_H}","-framerate",str(FPS),"-i","-","-an",
         "-c:v","libx264","-preset","veryslow","-crf","26","-pix_fmt","yuv420p",
         "-movflags","+faststart",str(MP4)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for joints,state in frames:
            p.stdin.write(raster(ascii_frame(m,joints,state)))
    finally:
        p.stdin.close()
    rc=p.wait()
    if rc: raise SystemExit(rc)

def chunks(s,n=1800):
 return [s[i:i+n] for i in range(0,len(s),n)]

def build_spa(m,contact,video):
 video_chunks=json.dumps(chunks(base64.b64encode(video).decode('ascii')),separators=(',',':'))
 ascii_chunks=json.dumps(chunks(base64.b64encode(gzip.compress(contact.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')),separators=(',',':'))
 json_chunks=json.dumps(chunks(base64.b64encode(gzip.compress(json.dumps(m,separators=(',',':'),ensure_ascii=False).encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')),separators=(',',':'))
 return f'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Strikes 004 — Contact Pin / Disengage Causality Repair</title>
<style>:root{{color-scheme:dark;background:#080808;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0}}main{{max-width:1120px;margin:auto;padding:10px}}nav{{position:sticky;top:0;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;background:#080808;padding:8px 0}}button{{min-height:44px;font:inherit}}section{{display:none}}section.active{{display:block}}pre{{white-space:pre;overflow:auto;font:12px/1.08 ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;user-select:text;background:#000;padding:10px}}video{{display:block;width:min(100%,720px);height:auto;background:#000}}</style></head><body><main>
<h1>V2 Strikes 004 — Contact Pin / Disengage Causality Repair</h1>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section data-panel="ascii" class="active"><pre id="asciiText">loading…</pre></section>
<section data-panel="json"><pre id="jsonText">loading…</pre></section>
<section data-panel="video"><video id="player" controls autoplay muted loop playsinline></video></section></main>
<script>
const V={video_chunks}.join("");
const A={ascii_chunks}.join("");
const J={json_chunks}.join("");
async function gunzip64(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}}
document.getElementById("player").src="data:video/mp4;base64,"+V;
Promise.all([gunzip64(A),gunzip64(J)]).then(([a,j])=>{{document.getElementById("asciiText").textContent=a;document.getElementById("jsonText").textContent=JSON.stringify(JSON.parse(j),null,2);}});
const b=[...document.querySelectorAll('[data-view]')],p=[...document.querySelectorAll('[data-panel]')];b.forEach(x=>x.onclick=()=>p.forEach(y=>y.classList.toggle('active',y.dataset.panel===x.dataset.view)));
</script></body></html>'''

def main():
    m=json.loads(MOTION.read_text(encoding="utf-8"))
    contact=CONTACT.read_text(encoding="utf-8")
    frames, provenance=compile_frames(m)
    if len(frames)!=m["media"]["frame_count"]:
        raise SystemExit(f"frame count mismatch {len(frames)} != {m['media']['frame_count']}")
    encode_mp4(m,frames)
    vb=MP4.read_bytes()
    sha=hashlib.sha256(vb).hexdigest()
    expected=m["media"].get("sha256")
    if expected is not None and expected != sha:
        raise SystemExit(f"media sha mismatch {sha} != {expected}")
    expected_bytes=m["media"].get("bytes")
    if expected_bytes is not None and expected_bytes != len(vb):
        raise SystemExit(f"media bytes mismatch {len(vb)} != {expected_bytes}")
    SPA.write_text(build_spa(m,contact,vb),encoding="utf-8")
    print(json.dumps({"frames":len(frames),"media_sha256":sha,"bytes":len(vb),"spa":SPA.name},sort_keys=True))

if __name__=="__main__":
    main()
