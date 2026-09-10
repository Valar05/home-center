#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/"motion.json"
CONTACT=HERE/"contact-sheet.txt"
SPA=HERE/"noncommutative-recovery-order.motion.html"
FPS=24
SIZE=(720,300)
GRID_W,GRID_H=58,17

def put(c,x,y,ch,force=False):
    if 0<=x<GRID_W and 0<=y<GRID_H and (force or c[y][x]==" "):
        c[y][x]=ch

def line(c,x0,y0,x1,y1,ch):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        put(c,x0,y0,ch)
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def pose_art(k):
    s=k["rig_state"]; c=[[" "]*GRID_W for _ in range(GRID_H)]
    for y in range(1,15): put(c,1,y,"|",True); put(c,56,y,"|",True)
    for x in range(1,57): put(c,x,14,"_",True)
    sx0,sy0,sx1,sy1=s["shaft"]
    tch="=" if sy0==sy1 else ("/" if (sy1-sy0)*(sx1-sx0)<0 else "\\")
    line(c,sx0,sy0,sx1,sy1,tch)
    if s.get("contact_wall"): put(c,55,sy1,"X",True)
    rx,ry=s["root"]; lean=s["lean"]; hx=rx+lean
    head=(hx,4); neck=(rx+lean//2,6); pelvis=(rx,10)
    ls=(neck[0]-3,7); rs=(neck[0]+3,7)
    h1=tuple(s["hands"][0]); h2=tuple(s["hands"][1])
    lk=(rx-2,12); rk=(rx+3,12); lf=(rx-5,14); rf=(rx+5,14)
    for a,b,ch in [(head,neck,"|"),(neck,pelvis,"|"),(neck,ls,"-"),(neck,rs,"-"),
                   (ls,h1,"/"),(rs,h2,"\\"),(pelvis,lk,"/"),(lk,lf,"/"),
                   (pelvis,rk,"\\"),(rk,rf,"\\")]:
        line(c,*a,*b,ch)
    for p,ch in [(head,"O"),(neck,"o"),(pelvis,"@"),(h1,"o"),(h2,"o")]: put(c,*p,ch,True)
    put(c,rx,9,"*",True)
    support=s["support"]
    put(c,*lf,"X" if support in ("REAR","BOTH") else "+",True)
    put(c,*rf,"X" if support in ("FRONT","BOTH") else "+",True)
    return "\n".join("".join(row).rstrip() for row in c).rstrip()+"\n"

def contact_text(m):
    out=[]
    for k in m["keys"]:
        out.append(f"{k['key_id']} {k['causal_role']} {k['timing_class']}/{k['exposure_ticks']}t PROV={k['timing_provenance']} SUPPORT={k['support_contact']} ROT={k['rotation_state']} CLR={k['clearance_state']}\n")
        out.append(pose_art(k)); out.append("-"*72+"\n")
    return "".join(out)

def render_mp4(m,out_path):
    d=Path(tempfile.mkdtemp(prefix="ascii-kinesis-t026-"))
    try:
        fp=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
        if not fp.exists(): fp=Path("/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf")
        font=ImageFont.truetype(str(fp),13); footer=ImageFont.truetype(str(fp),10); idx=0
        for k in m["keys"]:
            rig=pose_art(k)
            for _ in range(int(k["exposure_ticks"])):
                im=Image.new("RGB",SIZE,"white"); dr=ImageDraw.Draw(im)
                dr.multiline_text((12,8),rig,fill="black",font=font,spacing=0)
                dr.text((12,SIZE[1]-18),f"Timing026 | {k['key_id']} | {k['causal_role']} | {k['timing_class']} | {k['rotation_state']}",fill="black",font=footer)
                im.save(d/f"frame_{idx:04d}.png"); idx+=1
        subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(d/"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","30","-map_metadata","-1",str(out_path)],check=True)
        return idx
    finally:
        shutil.rmtree(d,ignore_errors=True)

def build_spa(m,contact,video):
    compact=json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(",",":"))
    v64=base64.b64encode(video).decode("ascii")
    css="body{font-family:system-ui,sans-serif;margin:0;background:#fff;color:#111}nav{position:sticky;top:0;background:#fff;border-bottom:1px solid #111;padding:8px}button{font:inherit;margin-right:8px;padding:6px 12px}section{display:none;padding:12px}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08}video{max-width:100%;height:auto;border:1px solid #111}"
    js="const bs=[...document.querySelectorAll('[data-view]')],ss=[...document.querySelectorAll('section')];function show(v){ss.forEach(s=>s.classList.toggle('active',s.id===v));}bs.forEach(b=>b.onclick=()=>show(b.dataset.view));show('ascii');"
    return f'<!doctype html><meta charset="utf-8"><title>Timing026 — Noncommutative Recovery Order</title><style>{css}</style><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre>{html.escape(contact)}</pre></section><section id="json"><pre>{html.escape(compact)}</pre></section><section id="video"><video controls loop playsinline src="data:video/mp4;base64,{v64}"></video></section><script>{js}</script>'

def main():
    m=json.loads(MOTION.read_text(encoding="utf-8")); contact=contact_text(m)
    if CONTACT.exists() and CONTACT.read_text(encoding="utf-8")!=contact: raise SystemExit("contact-sheet.txt drifted from motion.json")
    CONTACT.write_text(contact,encoding="utf-8")
    mp4=HERE/".timing026-authoritative.mp4"; count=render_mp4(m,mp4); b=mp4.read_bytes(); sha=hashlib.sha256(b).hexdigest()
    declared=m.get("compile",{}).get("media",{}).get("sha256")
    if declared and declared!=sha: raise SystemExit(f"media identity mismatch declared={declared} actual={sha}")
    if m.get("compile",{}).get("frame_count") not in (None,count): raise SystemExit("frame_count mismatch")
    SPA.write_text(build_spa(m,contact,b),encoding="utf-8")
    print(json.dumps({"frames":count,"bytes":len(b),"sha256":sha,"spa":SPA.name},sort_keys=True))
if __name__=="__main__": main()
