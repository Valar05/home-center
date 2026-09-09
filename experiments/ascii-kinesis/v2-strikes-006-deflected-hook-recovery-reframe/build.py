#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOTION = ROOT / "motion.json"
ASCII = ROOT / "contact_sheet.txt"
SPA = ROOT / "deflected-hook-recovery-reframe.motion.html"
MP4 = ROOT / "deflected-hook-recovery-reframe.mp4"
FPS = 24
OUT_W, OUT_H = 960, 480
CELL_W, CELL_H = 12, 18
OX, OY = 44, 24
FONT = {
" ":["00000"]*7,
".":["00000","00000","00000","00000","00000","00100","00100"],
"-":["00000","00000","00000","11111","00000","00000","00000"],
"|":["00100","00100","00100","00100","00100","00100","00100"],
"/":["00001","00010","00100","01000","10000","00000","00000"],
"\\":["10000","01000","00100","00010","00001","00000","00000"],
"=":["00000","00000","11111","00000","11111","00000","00000"],
"O":["01110","10001","10001","10001","10001","10001","01110"],
"o":["00000","00000","01110","10001","10001","10001","01110"],
"+":["00000","00100","00100","11111","00100","00100","00000"],
"_":["00000","00000","00000","00000","00000","00000","11111"],
">":["10000","01000","00100","00010","00100","01000","10000"],
"<":["00001","00010","00100","01000","00100","00010","00001"],
"X":["10001","01010","00100","00100","01010","10001","00000"],
"*":["00100","10101","01110","11111","01110","10101","00100"],
}

def curve_t(t,name):
    if name=="ease_in": return t*t
    if name=="ease_out": return 1-(1-t)*(1-t)
    if name=="ease_in_out": return 3*t*t-2*t*t*t
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

def draw_segment(g,a,b,ch,overwrite=False):
    H=len(g); W=len(g[0])
    for x,y in bresenham(a,b):
        if 0<=x<W and 0<=y<H and (overwrite or g[y][x]==" "):
            g[y][x]=ch

def ascii_frame(m,joints,contact_state="CLEAR"):
    W,H=m["rig"]["grid"]["width"],m["rig"]["grid"]["height"]
    g=[[" "]*W for _ in range(H)]
    for x in range(W): g[21][x]="."
    # Fixed abstract opponent/deflector line is context, never source art.
    draw_segment(g,joints["deflect_top"],joints["deflect_bottom"],"/",True)
    # Body first.
    for a,b in m["rig"]["bones"]:
        draw_segment(g,joints[a],joints[b],line_char(joints[a],joints[b]),False)
    # Tool: butt -> rear hand -> front hand -> head.
    draw_segment(g,joints["tool_butt"],joints["rear_hand"],"-",True)
    draw_segment(g,joints["rear_hand"],joints["front_hand"],"-",True)
    draw_segment(g,joints["front_hand"],joints["tool_head"],"=",True)
    for name,sym in {
      "head":"O","pelvis":"+","rear_hand":"o","front_hand":"o",
      "rear_foot":"_","front_foot":"_","tool_head":">","tool_butt":"<",
    }.items():
        x,y=map(lambda v:int(round(v)),joints[name])
        if 0<=x<W and 0<=y<H: g[y][x]=sym
    if contact_state=="BIND":
        x,y=map(lambda v:int(round(v)),joints["bind_point"])
        if 0<=x<W and 0<=y<H: g[y][x]="X"
    return ["".join(r) for r in g]

def contact_sheet(m):
    parts=[
      "ASCII KINESIS V2 STRIKES 006 — DEFLECTED HOOK RECOVERY REFRAME",
      "FRESH POST-DEBT CONCEPT | STRIKES003/004/005 CLOSED HEALTHY",
      "SOURCE: TSR asset 215612 — Grim Reaper — Sword Master — NES",
      "SOURCE SHA-256: 86a8011900b0e37ed030b949d9a690519b57c85afe18ddcb1e2504723283e52c",
      "RIGHTS: whole-sheet evidence only; independent abstract ASCII rig; NO SOURCE PIXELS.",
      "OBSERVED SOURCE TIMING: NONE | EVERY DECISIVE KEY TIMING BELOW: INFERRED / STREET_FIGHTER-CAPCOM",
      "PRINCIPLE: DEFLECTION REWRITES THE RECOVERY AXIS.",
      "POCKET RULE: WHEN CONTACT ROTATES THE TOOL, RECOVER FROM THE NEW AXIS — DO NOT REVERSE THE ATTACK.",
      "LEGEND: O head | + pelvis | o hands | _ feet | <====> abstract hooked long tool | / opponent deflector | X bound contact",
      "",
    ]
    for k in m["keys"]:
        parts += [
          f'{k["key_id"]} {k["name"]} | {k["timing_class"]}/{k["timing_provenance"]} | {k["support_contact"]} | contact={k["contact_state"]}',
          f'ROLE: {k["causal_role"]}',
          f'ROOT/ARC: {k["motion_arc_root_note"]}',
        ]
        parts += ascii_frame(m,k["joints"],k["contact_state"])
        parts += [""]
    return "\n".join(parts).rstrip()+"\n"

def compile_frames(m):
    hold=m["motion_dungeon"]["hold_frames_by_class"]; ks=m["keys"]; ts=m["transitions"]
    frames=[]; provenance=[]
    for i,k in enumerate(ks):
        for n in range(hold[k["timing_class"]]):
            frames.append((k["joints"],k["contact_state"]))
            provenance.append({"kind":"HOLD","key_id":k["key_id"],"hold_index":n})
        if i<len(ks)-1:
            t=ts[i]; count=int(t["connective_frames"])
            for n in range(1,count+1):
                joints=mix(k["joints"],ks[i+1]["joints"],n/(count+1),t["curve"])
                state=k["contact_state"] if k["contact_state"]==ks[i+1]["contact_state"] else "CLEAR"
                frames.append((joints,state))
                provenance.append({"kind":"CONNECTIVE","from":k["key_id"],"to":ks[i+1]["key_id"],"index":n,"semantic_rule":t["semantic_rule"]})
    return frames,provenance

def put_rect(buf,x0,y0,x1,y1,v=244):
    x0=max(0,x0);y0=max(0,y0);x1=min(OUT_W,x1);y1=min(OUT_H,y1)
    for y in range(y0,y1):
        idx=(y*OUT_W+x0)*3
        for _ in range(x0,x1):
            buf[idx]=v;buf[idx+1]=v;buf[idx+2]=v;idx+=3

def raster(lines):
    buf=bytearray(OUT_W*OUT_H*3); sx=sy=2
    for gy,line in enumerate(lines):
        for gx,ch in enumerate(line):
            pat=FONT.get(ch,FONT[" "]); px=OX+gx*CELL_W; py=OY+gy*CELL_H
            for yy,row in enumerate(pat):
                for xx,b in enumerate(row):
                    if b=="1": put_rect(buf,px+xx*sx,py+yy*sy,px+(xx+1)*sx,py+(yy+1)*sy)
    return bytes(buf)

def encode_mp4(m,frames):
    cmd=["ffmpeg","-y","-loglevel","error","-f","rawvideo","-pixel_format","rgb24","-video_size",f"{OUT_W}x{OUT_H}","-framerate",str(FPS),"-i","-","-an","-c:v","libx264","-preset","veryslow","-crf","25","-pix_fmt","yuv420p","-movflags","+faststart",str(MP4)]
    p=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for joints,state in frames: p.stdin.write(raster(ascii_frame(m,joints,state)))
    finally:
        p.stdin.close()
    rc=p.wait()
    if rc: raise SystemExit(rc)

def build_spa(m,contact,video):
    video_chunks=json.dumps(base64.b64encode(video).decode("ascii"))
    ascii_chunks=json.dumps(base64.b64encode(gzip.compress(contact.encode(),compresslevel=9,mtime=0)).decode("ascii"))
    json_chunks=json.dumps(base64.b64encode(gzip.compress(json.dumps(m,separators=(",",":"),ensure_ascii=False).encode(),compresslevel=9,mtime=0)).decode("ascii"))
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Strikes 006 — Deflected Hook Recovery Reframe</title>
<style>:root{{color-scheme:dark;background:#080808;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0}}main{{max-width:1240px;margin:auto;padding:10px}}nav{{position:sticky;top:0;display:grid;grid-template-columns:repeat(3,1fr);gap:8px;background:#080808;padding:8px 0}}button{{min-height:44px;font:inherit}}section{{display:none}}section.active{{display:block}}pre{{white-space:pre;overflow:auto;font:12px/1.08 ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;user-select:text;background:#000;padding:10px}}video{{display:block;width:min(100%,960px);height:auto;background:#000}}</style></head><body><main>
<h1>V2 Strikes 006 — Deflected Hook Recovery Reframe</h1><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section data-panel="ascii" class="active"><pre id="asciiText">loading…</pre></section><section data-panel="json"><pre id="jsonText">loading…</pre></section><section data-panel="video"><video id="player" controls autoplay muted loop playsinline></video></section></main>
<script>const V={video_chunks};const A={ascii_chunks};const J={json_chunks};async function gunzip64(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}}document.getElementById("player").src="data:video/mp4;base64,"+V;Promise.all([gunzip64(A),gunzip64(J)]).then(([a,j])=>{{document.getElementById("asciiText").textContent=a;document.getElementById("jsonText").textContent=JSON.stringify(JSON.parse(j),null,2);}});const b=[...document.querySelectorAll('[data-view]')],p=[...document.querySelectorAll('[data-panel]')];b.forEach(x=>x.onclick=()=>p.forEach(y=>y.classList.toggle('active',y.dataset.panel===x.dataset.view)));</script></body></html>'''

def main():
    m=json.loads(MOTION.read_text())
    contact=contact_sheet(m); ASCII.write_text(contact)
    frames,_=compile_frames(m)
    encode_mp4(m,frames)
    vb=MP4.read_bytes(); sha=hashlib.sha256(vb).hexdigest()
    # First build can populate metadata, subsequent builds enforce it.
    if m["media"].get("frame_count") is not None and len(frames)!=m["media"]["frame_count"]: raise SystemExit("frame count mismatch")
    if m["media"].get("sha256") is not None and sha!=m["media"]["sha256"]: raise SystemExit(f"media sha mismatch {sha} != {m['media']['sha256']}")
    if m["media"].get("bytes") is not None and len(vb)!=m["media"]["bytes"]: raise SystemExit("media bytes mismatch")
    SPA.write_text(build_spa(m,contact,vb))
    print(json.dumps({"frames":len(frames),"media_sha256":sha,"bytes":len(vb),"spa":SPA.name,"ascii_bytes":len(contact.encode())},sort_keys=True))
if __name__=="__main__": main()
