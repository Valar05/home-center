#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION_PATH = HERE / "motion.json"
MANIFEST_PATH = HERE / "manifest.json"
OUT_MP4 = HERE / "air-task-rides-root-arc.mp4"
OUT_HTML = HERE / "air-task-rides-root-arc.motion.html"
W, H = 64, 24
HOLD = {"ONES":1, "TWOS":2, "FOURS":4}
LINKS = [
    ("head","neck"),("neck","shoulder_l"),("neck","shoulder_r"),
    ("shoulder_l","elbow_l"),("elbow_l","hand_l"),
    ("shoulder_r","elbow_r"),("elbow_r","hand_r"),
    ("neck","pelvis"),("pelvis","knee_l"),("knee_l","foot_l"),
    ("pelvis","knee_r"),("knee_r","foot_r")
]

def lerp(a,b,t):
    return [round(a[0]+(b[0]-a[0])*t), round(a[1]+(b[1]-a[1])*t)]

def bres(a,b):
    x0,y0=a; x1,y1=b
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return out

def glyph(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx) > abs(dy)*2: return "-"
    if abs(dy) > abs(dx)*2: return "|"
    return "\\" if dx*dy>0 else "/"

def render_ascii(key, joints_override=None, label_vector=True):
    grid=[[" "]*W for _ in range(H)]
    def put(x,y,ch):
        if 0<=x<W and 0<=y<H: grid[y][x]=ch
    p={k:list(v) for k,v in (joints_override or key["pose_rig"]).items()}
    for a,b in LINKS:
        ch=glyph(p[a],p[b])
        for x,y in bres(p[a],p[b])[1:-1]:
            if grid[y][x]==" ": put(x,y,ch)
    for name,(x,y) in p.items():
        put(x,y,"O" if name=="head" else ("@" if name=="pelvis" else "o"))
    hx,hy=p["head"]; put(hx+2,hy,">")
    if key["support_contact"]=="GROUND_BOTH":
        for foot in ("foot_l","foot_r"):
            fx,fy=p[foot]; put(fx, min(H-1,fy+1), "=")
    for x in range(W):
        if grid[22][x]==" ": grid[22][x]="_"
    if label_vector:
        px,py=p["pelvis"]
        phase=key["vertical_phase"]
        marker="^" if phase in {"LAUNCH","RISE"} else ("~" if phase=="APEX" else ("v" if phase in {"DESCENT_BEGIN","DESCENT","PRECONTACT"} else "+"))
        put(max(0,px-5),py,marker)
    return "\n".join("".join(r).rstrip() for r in grid)

def topology(k):
    return (k["support_contact"], k["contact_state"])

def connector(a,b):
    # Geometry only. Semantic labels/topology remain those of a, and a connector
    # is emitted only when support/contact topology is identical.
    p={j:lerp(a["pose_rig"][j], b["pose_rig"][j], 0.5) for j in a["pose_rig"]}
    return render_ascii(a,p,label_vector=False)

def contact_sheet(data):
    chunks=[]
    for k in data["keys"]:
        header=(f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | "
                f"support={k['support_contact']} | contact={k['contact_state']} | phase={k['vertical_phase']} | force={k['force_owner']}")
        chunks.append(header+"\n"+render_ascii(k))
    return "\n\n".join(chunks)

def sequence_for_loop(data):
    seq=[]
    keys=data["keys"]
    for i,k in enumerate(keys):
        txt=render_ascii(k)
        for _ in range(HOLD[k["timing_class"]]):
            seq.append((k["key_id"],txt))
        if i+1<len(keys) and topology(k)==topology(keys[i+1]):
            seq.append((k["key_id"]+"~"+keys[i+1]["key_id"],connector(k,keys[i+1])))
    return seq

def draw_frame(text,path,label):
    im=Image.new("RGB",(960,540),"black")
    d=ImageDraw.Draw(im)
    try:
        font=ImageFont.truetype("DejaVuSansMono.ttf",20)
        small=ImageFont.truetype("DejaVuSansMono.ttf",16)
    except OSError:
        font=ImageFont.load_default(); small=font
    d.text((20,14),"ASCII KINESIS V2 — AIR TASK RIDES ROOT ARC",fill="white",font=small)
    d.text((20,38),label,fill="white",font=small)
    d.multiline_text((20,72),text,fill="white",font=font,spacing=0)
    im.save(path)

def build_video(data):
    loop=sequence_for_loop(data)
    seq=loop*int(data["compile"]["loop_repetitions"])
    with tempfile.TemporaryDirectory(prefix="ascii-kinesis-airborne-") as td:
        td=Path(td)
        for n,(label,text) in enumerate(seq):
            draw_frame(text,td/f"frame-{n:04d}.png",label)
        cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(data["compile"]["fps"]),
             "-i",str(td/"frame-%04d.png"),"-c:v","libx264","-preset","veryslow","-crf","35","-pix_fmt","yuv420p","-movflags","+faststart",str(OUT_MP4)]
        subprocess.run(cmd,check=True)
    return loop,seq

def build_html(data,sheet,media_b64):
    pretty=json.dumps(data,indent=2,sort_keys=True)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Airborne 001 — Air Task Rides the Root Arc</title>
<style>
:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1180px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:78ch;line-height:1.45}}
</style></head><body>
<h1>Air Task Rides the Root Arc</h1>
<p class="note">Copyright-safe generic ASCII rig. Source art is evidence only and is not embedded. The transferable principle: an airborne local task change rides one authored ballistic root arc instead of manufacturing a second vertical impulse.</p>
<nav role="tablist" aria-label="Primary views">
<button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button>
<button type="button" role="tab" data-view="json" aria-selected="false">JSON</button>
<button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button>
</nav>
<section id="ascii" role="tabpanel"><pre>{html.escape(sheet)}</pre></section>
<section id="json" role="tabpanel" hidden><pre>{html.escape(pretty)}</pre></section>
<section id="video" role="tabpanel" hidden><video controls loop playsinline preload="metadata"><source src="data:video/mp4;base64,{media_b64}" type="video/mp4"></video><p class="note">MP4 compiled solely from the abstract joint data, generated ASCII frames, explicit ONES/TWOS/FOURS holds, and topology-safe connective frames recorded in JSON.</p></section>
<script>const tabs=[...document.querySelectorAll('button[data-view]')];const panels=[...document.querySelectorAll('section[role=tabpanel]')];for(const t of tabs)t.addEventListener('click',()=>{{for(const b of tabs)b.setAttribute('aria-selected',b===t?'true':'false');for(const p of panels)p.hidden=p.id!==t.dataset.view;}});</script>
</body></html>'''

def build_manifest(data,media_sha,media_bytes,loop_len,total_frames,sheet_sha):
    return {
      "schema":"ascii-kinesis.swarm-manifest.v2","format_version":2,
      "experiment_id":data["experiment_id"],"lane":"airborne",
      "primary_tabs":["ASCII","JSON","VIDEO"],
      "ascii_literal_text":True,"ascii_surface":"real preformatted DOM text","ligatures_disabled":True,"whitespace_preserved":True,
      "video_required":True,"video_source":"abstract_ascii_rig_only","video_packaging":"embedded MP4 data URI in air-task-rides-root-arc.motion.html",
      "media_sha256":media_sha,"media_bytes":media_bytes,"ascii_sheet_sha256":sheet_sha,
      "source_art_embedded":False,"backward_compatible":True,
      "motion_dungeon":{"authored_ascii_keys":len(data["keys"]),"explicit_holds":True,"deterministic_connective_motion":True,"connector_semantics_fail_closed":True,"ascii_only_frame_render":True,"fps":data["compile"]["fps"],"semantic_frames_per_loop":loop_len,"loop_repetitions":data["compile"]["loop_repetitions"],"video_frames_total":total_frames},
      "source":{"site":"The Spriters Resource","asset_id":501,"page_url":data["source"]["page_url"],"raw_sha256":data["source"]["raw_sha256"],"raw_bytes":data["source"]["raw_bytes"],"raw_dimensions":data["source"]["raw_dimensions"],"whole_sheet_inspected":True,"source_timing_available":False},
      "files":["build.py","manifest.json","motion.json","receipt.md","air-task-rides-root-arc.motion.html","air-task-rides-root-arc.mp4"],
      "reconstruction":"python3 build.py",
      "correction_hooks":data["correction_hooks"]
    }

def main():
    data=json.loads(MOTION_PATH.read_text())
    loop,seq=build_video(data)
    media=OUT_MP4.read_bytes(); media_sha=hashlib.sha256(media).hexdigest()
    data["compile"]["media_sha256"]=media_sha
    data["compile"]["media_bytes"]=len(media)
    data["compile"]["semantic_frames_per_loop"]=len(loop)
    data["compile"]["video_frames_total"]=len(seq)
    sheet=contact_sheet(data); sheet_sha=hashlib.sha256(sheet.encode()).hexdigest()
    data["ascii_sheet_sha256"]=sheet_sha
    MOTION_PATH.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
    OUT_HTML.write_text(build_html(data,sheet,base64.b64encode(media).decode("ascii")))
    manifest=build_manifest(data,media_sha,len(media),len(loop),len(seq),sheet_sha)
    MANIFEST_PATH.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"media_sha256":media_sha,"media_bytes":len(media),"semantic_frames_per_loop":len(loop),"video_frames_total":len(seq),"ascii_sheet_sha256":sheet_sha},sort_keys=True))

if __name__=="__main__": main()
