#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/"motion.json"; MANIFEST=HERE/"manifest.json"; SHEET=HERE/"contact_sheet.txt"
OUT_MP4=HERE/"embodied-root-arc-repair.mp4"; OUT_HTML=HERE/"embodied-root-arc-repair.motion.html"
W,H=72,30
HOLD={"ONES":1,"TWOS":2,"FOURS":4}
LINKS=[("head","neck"),("neck","shoulder_l"),("neck","shoulder_r"),
("shoulder_l","elbow_l"),("elbow_l","hand_l"),("shoulder_r","elbow_r"),("elbow_r","hand_r"),
("neck","pelvis"),("pelvis","knee_l"),("knee_l","foot_l"),("pelvis","knee_r"),("knee_r","foot_r")]

def bres(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return out

def glyph(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>abs(dy)*2:return "-"
    if abs(dy)>abs(dx)*2:return "|"
    return "\\" if dx*dy>0 else "/"

def render_ascii(key, joints=None):
    p={k:list(v) for k,v in (joints or key["pose_rig"]).items()}
    g=[[" "]*W for _ in range(H)]
    def put(x,y,c):
        if 0<=x<W and 0<=y<H:g[y][x]=c
    for a,b in LINKS:
        ch=glyph(p[a],p[b])
        for x,y in bres(p[a],p[b])[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ":g[y][x]=ch
    for name,(x,y) in p.items():
        put(x,y,"O" if name=="head" else ("@" if name=="pelvis" else "o"))
    hx,hy=p["head"]; put(hx+2,hy,">")
    if key["support_contact"]=="GROUND_BOTH":
        for f in ("foot_l","foot_r"):
            x,y=p[f]; put(x,min(H-1,y+1),"=")
    elif key["support_contact"]=="GROUND_REAR_DOMINANT":
        x,y=p["foot_l"]; put(x,min(H-1,y+1),"#")
        x,y=p["foot_r"]; put(x,min(H-1,y+1),"=")
    elif key["support_contact"]=="GROUND_REAR_ONLY":
        x,y=p["foot_r"]; put(x,min(H-1,y+1),"=")
    elif key["support_contact"]=="GROUND_LEAD_ONLY":
        x,y=p["foot_l"]; put(x,min(H-1,y+1),"=")
    for x in range(W): g[28][x]="_"
    px,py=p["pelvis"]
    marker={"LOAD":"v","DRIVE":"/","LAUNCH":"^","RISE":"^","APEX":"~","DESCENT_BEGIN":"\\","DESCENT":"v",
            "PRECONTACT":"v","CONTACT":"!","COMPRESSION":"v","REBOUND":"^","SETTLE":".","READY":"."}.get(key["vertical_phase"],".")
    put(max(0,px-4),py,marker)
    return "\n".join("".join(r).rstrip() for r in g)

def topology(k): return (k["support_contact"],k["contact_state"],k["force_owner"])
def smoothstep(t): return t*t*(3-2*t)
def interp_pose(a,b,t,bow=(0,0)):
    # Explicit quadratic connector: control point is authored midpoint + per-segment bow.
    # This prevents straight-line tweening while staying inside adjacent authored semantics.
    s=smoothstep(t)
    out={}
    for j in a:
        ax,ay=a[j]; bx,by=b[j]
        cx=(ax+bx)/2+bow[0]; cy=(ay+by)/2+bow[1]
        x=(1-s)*(1-s)*ax + 2*(1-s)*s*cx + s*s*bx
        y=(1-s)*(1-s)*ay + 2*(1-s)*s*cy + s*s*by
        out[j]=[round(x),round(y)]
    return out

def frame_sequence(data):
    keys=data["keys"]; seq=[]
    for i,k in enumerate(keys):
        txt=render_ascii(k)
        for _ in range(HOLD[k["timing_class"]]): seq.append((k["key_id"],txt))
        if i+1<len(keys) and topology(k)==topology(keys[i+1]):
            seg=k["key_id"]+">"+keys[i+1]["key_id"]
            bow=tuple(data["compile"].get("connector_bows",{}).get(seg,[0,0]))
            for t in (0.32,0.74):
                seq.append((k["key_id"]+"~"+keys[i+1]["key_id"],render_ascii(k,interp_pose(k["pose_rig"],keys[i+1]["pose_rig"],t,bow))))
    return seq

def contact_sheet(data):
    out=[]
    for k in data["keys"]:
        out.append(f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | support={k['support_contact']} | contact={k['contact_state']} | phase={k['vertical_phase']} | force={k['force_owner']}\nROOT: {k['motion_arc_root_note']}\n{render_ascii(k)}")
    return "\n\n".join(out)+"\n"

def font_pair():
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf","/system/fonts/NotoSansMono-Regular.ttf","DejaVuSansMono.ttf"):
        try:return ImageFont.truetype(p,18),ImageFont.truetype(p,14)
        except OSError:pass
    f=ImageFont.load_default(); return f,f

def draw_frame(text,path,label):
    im=Image.new("RGB",(864,486),"black"); d=ImageDraw.Draw(im); font,small=font_pair()
    d.text((18,12),"ASCII KINESIS — EMBODIED ROOT ARC REPAIR",fill="white",font=small)
    d.text((18,34),label,fill="white",font=small)
    d.multiline_text((18,58),text,fill="white",font=font,spacing=0)
    im.save(path)

def build_video(data):
    one=frame_sequence(data); seq=one*int(data["compile"]["loop_repetitions"])
    with tempfile.TemporaryDirectory(prefix="ak-airborne010-") as td:
        td=Path(td)
        for i,(label,txt) in enumerate(seq):draw_frame(txt,td/f"frame-{i:04d}.png",label)
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(data["compile"]["fps"]),
                        "-i",str(td/"frame-%04d.png"),"-c:v","libx264","-preset","veryslow","-crf","31",
                        "-pix_fmt","yuv420p","-movflags","+faststart",str(OUT_MP4)],check=True)
    return one,seq

def html_page(data,sheet,b64):
    pretty=json.dumps(data,indent=2,sort_keys=True)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Airborne 010 — Embodied Root Arc Repair</title>
<style>
:root{{color-scheme:dark;background:#0d0d0d;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1180px}}
nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#0d0d0d;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}
section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.02}}
video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:82ch;line-height:1.45}}
</style></head><body>
<h1>Embodied Root Arc Repair</h1>
<p class="note">Successor repair of <code>v2-airborne-001-air-task-rides-root-arc</code>. Same source/evidence family and same core principle; performance rebuilt for asymmetric load, support-truth launch, nonuniform ballistic spacing, landing consequence, rebound, lag, and recovery debt. No source art is embedded.</p>
<nav role="tablist" aria-label="Primary views">
<button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button>
<button type="button" role="tab" data-view="json" aria-selected="false">JSON</button>
<button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button>
</nav>
<section id="ascii" role="tabpanel"><pre>{html.escape(sheet)}</pre></section>
<section id="json" role="tabpanel" hidden><pre>{html.escape(pretty)}</pre></section>
<section id="video" role="tabpanel" hidden><video controls playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section>
<script>const ts=[...document.querySelectorAll('button[data-view]')],ps=[...document.querySelectorAll('section[role=tabpanel]')];for(const t of ts)t.addEventListener('click',()=>{{for(const b of ts)b.setAttribute('aria-selected',b===t?'true':'false');for(const p of ps)p.hidden=p.id!==t.dataset.view;}});</script>
</body></html>'''

def build():
    data=json.loads(MOTION.read_text())
    sheet=contact_sheet(data); SHEET.write_text(sheet)
    one,seq=build_video(data)
    media=OUT_MP4.read_bytes(); msh=hashlib.sha256(media).hexdigest(); ash=hashlib.sha256(sheet.encode()).hexdigest()
    data["ascii_sheet_sha256"]=ash
    data["compile"].update({"media_sha256":msh,"media_bytes":len(media),"semantic_frames_per_loop":len(one),"video_frames_total":len(seq)})
    MOTION.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    OUT_HTML.write_text(html_page(data,sheet,base64.b64encode(media).decode()))
    manifest={
      "schema":"ascii-kinesis.swarm-manifest.v2","format_version":2,"experiment_id":data["experiment_id"],"lane":"airborne",
      "revises":data["revises"],"negative_fixture":data["negative_fixture"],"predecessor_status":data["predecessor_status"],
      "primary_tabs":["ASCII","JSON","VIDEO"],"ascii_literal_text":True,"ascii_surface":"real preformatted DOM text","ligatures_disabled":True,"whitespace_preserved":True,
      "video_required":True,"video_source":"abstract_ascii_rig_only","video_packaging":"embedded MP4 data URI in embodied-root-arc-repair.motion.html",
      "media_sha256":msh,"media_bytes":len(media),"ascii_sheet_sha256":ash,"source_art_embedded":False,"backward_compatible":True,
      "source":data["source"],"source_rights":data["source_rights"],
      "motion_dungeon":{"authored_ascii_keys":len(data["keys"]),"explicit_holds":True,"deterministic_connective_motion":True,
                        "connector_semantics_fail_closed":True,"ascii_only_frame_render":True,"fps":data["compile"]["fps"],
                        "semantic_frames_per_loop":len(one),"loop_repetitions":data["compile"]["loop_repetitions"],"video_frames_total":len(seq)},
      "review":data["review"],
      "files":["build.py","contact_sheet.txt","manifest.json","motion.json","receipt.md","embodied-root-arc-repair.motion.html","embodied-root-arc-repair.mp4"],
      "reconstruction":"python3 build.py","correction_hooks":data["correction_hooks"]
    }
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"media_sha256":msh,"media_bytes":len(media),"ascii_sha256":ash,"semantic_frames_per_loop":len(one),"video_frames_total":len(seq)},sort_keys=True))

if __name__=="__main__":build()
