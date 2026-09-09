#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
M=json.loads((HERE/"motion.json").read_text(encoding="utf-8"))
MAN=json.loads((HERE/"manifest.json").read_text(encoding="utf-8"))
W=int(M["rig"]["grid"]["width"]); H=int(M["rig"]["grid"]["height"])
HIGH=int(M["rig"]["grid"]["high_step_y"]); LOW=int(M["rig"]["grid"]["low_step_y"]); EDGE=int(M["rig"]["grid"]["step_edge_x"])
ORDER=list(M["rig"]["joint_order"]); BONES=[tuple(x) for x in M["rig"]["bones"]]
HOLD={"ONES":1,"TWOS":2,"FOURS":4}

def joints(k):
    pts=k["points"]
    if len(pts)!=len(ORDER): raise SystemExit(f"{k['key_id']}: joint count mismatch")
    return {n:pts[i] for i,n in enumerate(ORDER)}

def line_points(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): return out
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy

def ascii_frame(j,support):
    g=[[" "]*W for _ in range(H)]
    for x in range(EDGE): g[HIGH][x]="_"
    for y in range(HIGH,LOW+1): g[y][EDGE]="|"
    for x in range(EDGE,W): g[LOW][x]="_"
    for a,b in BONES:
        pa,pb=j[a],j[b]; dx=pb[0]-pa[0]; dy=pb[1]-pa[1]
        c="/" if dx*dy<0 else ("\\" if dx*dy>0 else ("-" if dy==0 else "|"))
        for x,y in line_points(pa,pb)[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ": g[y][x]=c
    for n,(x,y) in j.items():
        if 0<=x<W and 0<=y<H:
            g[y][x]="O" if n=="head" else ("@" if n=="pelvis" else ("+" if n=="chest" else ("o" if "elbow" in n or "knee" in n else "*")))
    for side,node in [("L_FOOT","l_foot"),("R_FOOT","r_foot")]:
        x,y=j[node]
        if side+"_PROBE" in support: g[y][x]="?"
        elif side in support: g[y][x]="!"
    return "\n".join("".join(r).rstrip() for r in g)

def contact_sheet():
    lines=[
      "ASCII KINESIS V2 LOCOMOTION 011 — SUPPORT-HEIGHT CATCH / DROP REPAIR",
      "Legend: ! trusted support   ? probe-only contact   @ pelvis/root   + chest   _ support surface   | riser",
      "Timing: ONES/TWOS/FOURS are PoseLab cadence classes; every decisive key is INFERRED.",
      "Causal law: lower support must become trustworthy before pelvis/root height may fall.",
      "Source boundary: independent abstract ASCII only; no Bullwinkle source pixels/palette/layout/contours/choreography embedded.",""]
    for k in M["keys"]:
        lines += [
          f"{k['key_id']} {k['name']}  [{k['timing_class']} / {k['timing_provenance']}]  SUPPORT={k['support_contact']}  ROOT_OWNER={k['root_owner']}"+("  BRIDGE" if k.get("authored_bridge_key") else ""),
          "ROOT: "+k["motion_arc_root_note"],
          "ROLE: "+k["causal_role"],
          "ATTITUDE: "+k["attitude"],"",
          ascii_frame(joints(k),k["support_contact"]),"",""]
    return "\n".join(lines).rstrip()+"\n"

def compile_frames():
    if M.get("connectors"): raise SystemExit("Locomotion011 fails closed: generated connectors are forbidden")
    frames=[]
    for k in M["keys"]:
        if k["timing_class"] not in HOLD: raise SystemExit(f"{k['key_id']}: unsupported timing")
        item=(joints(k),k["support_contact"],k["root_owner"],k["key_id"],k["name"])
        frames.extend([item]*HOLD[k["timing_class"]])
    frames.extend([frames[-1]]*int(M["motion_dungeon"]["compile"]["endpoint_hold_frames"]))
    return frames

def render_mp4(frames,out):
    fd=HERE/".motion_frames"; shutil.rmtree(fd,ignore_errors=True); fd.mkdir()
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",10)
    small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",8)
    for idx,(j,s,root,kid,name) in enumerate(frames):
        im=Image.new("RGB",(960,520),(10,10,12)); d=ImageDraw.Draw(im)
        d.text((12,8),"ASCII KINESIS · LOCO 011 · SUPPORT-HEIGHT CATCH / DROP REPAIR",font=small,fill=(180,180,180))
        d.text((12,22),f"{kid} {name}  SUPPORT={s}  ROOT={root}",font=small,fill=(235,235,230))
        d.multiline_text((12,40),ascii_frame(j,s),font=font,fill=(245,245,238),spacing=0)
        d.text((12,495),f"{idx+1:03d}/{len(frames):03d}",font=small,fill=(130,130,130))
        im.save(fd/f"f_{idx:04d}.png",compress_level=9)
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(fd/"f_%04d.png"),
                    "-c:v","libx264","-preset","veryslow","-crf",str(M["motion_dungeon"]["compile"]["crf"]),
                    "-pix_fmt","yuv420p","-movflags","+faststart","-map_metadata","-1",
                    "-metadata","comment=ASCII Kinesis abstract rig only",str(out)],check=True)
    shutil.rmtree(fd)

def make_spa(media,sheet):
    title=html.escape(M["title"])
    b64=base64.b64encode(media).decode("ascii")
    motion=html.escape(json.dumps(M,ensure_ascii=False,indent=2))
    ascii_text=html.escape(sheet)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>
:root{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;color-scheme:dark;background:#0b0b0d;color:#f2f2ed}}*{{box-sizing:border-box}}body{{margin:0;padding:16px;max-width:1320px;margin-inline:auto}}nav{{display:flex;gap:8px;position:sticky;top:0;background:#0b0b0df2;padding:8px 0;z-index:2}}button{{font:inherit;padding:10px 16px;border:1px solid #555;background:#16161a;color:inherit;border-radius:8px}}button[aria-selected="true"]{{border-color:#ddd;background:#29292f}}.panel{{display:none}}.panel.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08;tab-size:2}}video{{width:100%;max-height:78vh;background:#000}}
</style></head><body><h1>{title}</h1><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav><section id="panel-ascii" class="panel active"><pre>{ascii_text}</pre></section><section id="panel-json" class="panel"><pre>{motion}</pre></section><section id="panel-video" class="panel"><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{b64}"></video></section><script>const bs=[...document.querySelectorAll("button[data-view]")];for(const b of bs)b.addEventListener("click",()=>{{for(const q of bs)q.setAttribute("aria-selected",String(q===b));for(const p of document.querySelectorAll(".panel"))p.classList.remove("active");document.getElementById("panel-"+b.dataset.view).classList.add("active")}});</script></body></html>'''

def main():
    sheet=contact_sheet()
    sheet_sha=hashlib.sha256(sheet.encode("utf-8")).hexdigest()
    if sheet_sha!=M["ascii_sheet_sha256"]: raise SystemExit(f"contact sheet identity mismatch {sheet_sha}")
    (HERE/MAN["contact_sheet_file"]).write_text(sheet,encoding="utf-8")
    frames=compile_frames()
    if len(frames)!=int(M["motion_dungeon"]["compile"]["frame_count"]): raise SystemExit("frame count mismatch")
    out=HERE/"_reconstructed.mp4"; render_mp4(frames,out); media=out.read_bytes()
    sha=hashlib.sha256(media).hexdigest()
    if sha!=M["motion_dungeon"]["compile"]["media_sha256"] or len(media)!=int(M["motion_dungeon"]["compile"]["media_bytes"]):
        raise SystemExit(f"media identity mismatch {sha} {len(media)}")
    subprocess.run(["ffmpeg","-v","error","-i",str(out),"-f","null","-"],check=True)
    (HERE/MAN["spa_file"]).write_text(make_spa(media,sheet),encoding="utf-8")
    out.unlink()
    print(json.dumps({"ok":True,"frames":len(frames),"media_sha256":sha,"media_bytes":len(media),"spa":MAN["spa_file"]},sort_keys=True))
if __name__=="__main__": main()
