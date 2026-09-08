#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/"motion.json"
CONTACT=HERE/"contact-sheet.txt"
MP4=HERE/"scoped-freeze-release-repair.motion.mp4"
HTML=HERE/"scoped-freeze-release-repair.motion.html"
HOLD={"ONES":1,"TWOS":2,"FOURS":4}
W,H=35,21
LINKS=[['root', 'chest'], ['chest', 'neck'], ['neck', 'head'], ['chest', 'left_shoulder'], ['left_shoulder', 'left_elbow'], ['left_elbow', 'left_hand'], ['chest', 'right_shoulder'], ['right_shoulder', 'right_elbow'], ['right_elbow', 'right_hand'], ['root', 'left_hip'], ['left_hip', 'left_knee'], ['left_knee', 'left_foot'], ['root', 'right_hip'], ['right_hip', 'right_knee'], ['right_knee', 'right_foot']]
HTML_TEMPLATE='<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>ASCII Kinesis V2 Timing 006 — Scoped Freeze / Release Repair</title>\n<style>:root{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}body{margin:0;padding:1rem;max-width:1180px}nav{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}button[data-view]{font:inherit;padding:.55rem .9rem}section[hidden]{display:none}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}video{max-width:100%;height:auto;border:1px solid #555}.note{max-width:82ch;line-height:1.45}</style>\n</head><body><h1>Scoped Freeze / Release — visible-performance repair</h1>\n<p class="note">Preserved negative fixture stays unchanged. This successor repairs the same Robot / Nuclear Throne evidence family with an independently authored ASCII biped: coil, scoped B freeze, A counter-sweep, release, overshoot, rebound, lag, and paid recovery. No source pixels.</p>\n<nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button></nav>\n<section id="ascii" role="tabpanel"><pre>__ASCII__</pre></section>\n<section id="json" role="tabpanel" hidden><pre>__JSON__</pre></section>\n<section id="video" role="tabpanel" hidden><video controls autoplay muted loop playsinline preload="metadata"><source src="data:video/mp4;base64,__VIDEO__" type="video/mp4"></video><p class="note">MP4 compiled solely from the abstract ASCII rig, explicit holds, and deterministic curved bridge instructions. Event boundaries hard-cut; no source art.</p></section>\n<script>const t=[...document.querySelectorAll(\'button[data-view]\')],p=[...document.querySelectorAll(\'section[role=tabpanel]\')];for(const x of t)x.addEventListener(\'click\',()=>{for(const b of t)b.setAttribute(\'aria-selected\',b===x?\'true\':\'false\');for(const y of p)y.hidden=y.id!==x.dataset.view;});</script>\n</body></html>'

def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def bres(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; e=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): break
        q=2*e
        if q>=dy: e+=dy; x0+=sx
        if q<=dx: e+=dx; y0+=sy
    return out

def glyph(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>abs(dy)*2:return "-"
    if abs(dy)>abs(dx)*2:return "|"
    return "\\" if dx*dy>0 else "/"

def render_ascii(joints,gate="OPEN"):
    j={n:tuple(v) for n,v in joints.items()}
    g=[[" "]*W for _ in range(H)]
    def put(x,y,ch):
        if 0<=x<W and 0<=y<H:g[y][x]=ch
    for a,b in LINKS:
        for x,y in bres(j[a],j[b])[1:-1]:
            if g[y][x]==" ": put(x,y,glyph(j[a],j[b]))
    marks={"root":"@","chest":"+","neck":":","head":"O","left_shoulder":"o","left_elbow":"o","left_hand":"A","right_shoulder":"o","right_elbow":"o","right_hand":"B","left_hip":"o","left_knee":"o","left_foot":"L","right_hip":"o","right_knee":"o","right_foot":"R"}
    for n,(x,y) in j.items(): put(x,y,marks[n])
    for x in range(8,27): put(x,19,"=")
    put(12,19,"^"); put(22,19,"^")
    put(j["head"][0],1,{"OPEN":"g","FREEZE_B":"F","RELEASE_B":"R"}[gate])
    if gate=="FREEZE_B":
        bx,by=j["right_hand"]; put(bx-1,by,"["); put(bx+1,by,"]")
    if gate=="RELEASE_B":
        bx,by=j["right_hand"]; put(bx-1,by,"<"); put(bx+1,by,">")
    return "\n".join("".join(r).rstrip() for r in g)

def ease(t,kind):
    if kind=="EASE_IN": return t*t
    if kind=="EASE_OUT": return 1-(1-t)*(1-t)
    if kind=="SMOOTHSTEP": return t*t*(3-2*t)
    return t

def qpoint(a,b,t,bias):
    cx=(a[0]+b[0])/2+bias[0]; cy=(a[1]+b[1])/2+bias[1]; u=1-t
    return [round(u*u*a[0]+2*u*t*cx+t*t*b[0]),round(u*u*a[1]+2*u*t*cy+t*t*b[1])]

def interp(a,b,t,bias):
    out={}
    for n,p in a.items():
        q=b[n]
        if "foot" in n:
            out[n]=list(p)
        else:
            mult=1.5 if "hand" in n else 1.0 if "elbow" in n else .4
            out[n]=qpoint(p,q,t,[bias[0]*mult,bias[1]*mult])
    return out

def event_key(k):
    return bool(k.get("event")) or k["pose_rig"]["gate_state"] in {"FREEZE_B","RELEASE_B"}

def seq_frames(m):
    seq=[]; ks=m["keys"]
    for i,k in enumerate(ks):
        txt=render_ascii(k["pose_rig"]["joints"],k["pose_rig"]["gate_state"])
        for _ in range(HOLD[k["timing_class"]]):
            seq.append((k["key_id"],"AUTHORED_HOLD",txt))
        nxt=ks[(i+1)%len(ks)]
        spec=k["bridge_to_next"]; n=int(spec.get("frames",0))
        if n and not event_key(k) and not event_key(nxt):
            for fi in range(1,n+1):
                t=ease(fi/(n+1),spec["easing"])
                jj=interp(k["pose_rig"]["joints"],nxt["pose_rig"]["joints"],t,spec["arc_bias"])
                seq.append((f"{k['key_id']}~{nxt['key_id']}:{fi}","CONNECTIVE_ARC",render_ascii(jj,k["pose_rig"]["gate_state"])))
    return seq

def contact_sheet(m):
    lines=[
        "ASCII KINESIS V2 TIMING 006 — SCOPED FREEZE / RELEASE REPAIR",
        f"revises: {m['revises']}",
        f"negative_fixture: {m['negative_fixture']}",
        "SOURCE ART: NONE | SOURCE TIMING OBSERVED: NONE | AUTHORED TIMING: INFERRED",
        "TIMING VOCABULARY: ONES=1 display frame | TWOS=2 | FOURS=4 | 1s/2s/4s are classes, never seconds",
        ""
    ]
    for k in m["keys"]:
        lines += [
            f"[{k['key_id']}] {k['name']}",
            f"pose/rig={k['pose_rig']['rig_id']} | support/contact={k['support_contact']}",
            f"root/motion-arc={k['motion_arc_root_note']}",
            f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']}",
            f"causal_role={k['causal_role']}",
            f"clocks BASE={k['clock_state']['BASE']} | A={k['clock_state']['SIGNAL_A']} | B={k['clock_state']['SIGNAL_B']} | GATE={k['clock_state']['GATE']}",
            render_ascii(k["pose_rig"]["joints"],k["pose_rig"]["gate_state"]),
            ""
        ]
    return "\n".join(lines).rstrip()+"\n"

def frame_png(txt,path):
    regular=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",10)
    header=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",9)
    im=Image.new("RGB",(400,250),"black")
    dr=ImageDraw.Draw(im)
    dr.text((8,6),"SCOPED FREEZE / RELEASE • ABSTRACT ASCII RIG",font=header,fill="white")
    dr.multiline_text((8,23),txt,font=regular,fill="white",spacing=0)
    im.save(path)

def main():
    m=json.loads(MOTION.read_text(encoding="utf-8"))
    sheet=contact_sheet(m)
    if sha256(sheet.encode()) != m["ascii_sheet_sha256"]:
        raise SystemExit("ASCII hash mismatch")
    CONTACT.write_text(sheet,encoding="utf-8")
    seq=seq_frames(m)
    all_frames=seq*int(m["compile"]["loop_repetitions"])
    if len(seq)!=m["compile"]["semantic_frames_per_loop"] or len(all_frames)!=m["compile"]["video_frames_total"]:
        raise SystemExit("frame-count mismatch")
    with tempfile.TemporaryDirectory(prefix="akv2timing006-") as td:
        td=Path(td)
        for n,(_,_,txt) in enumerate(all_frames):
            frame_png(txt,td/f"frame-{n:04d}.png")
        subprocess.run([
            "ffmpeg","-hide_banner","-loglevel","error","-y",
            "-framerate",str(m["compile"]["fps"]),"-i",str(td/"frame-%04d.png"),
            "-c:v","libx264","-preset","veryslow","-crf","31","-pix_fmt","yuv420p",
            "-movflags","+faststart",str(MP4)
        ],check=True)
    media=MP4.read_bytes()
    if sha256(media) != m["compile"]["media_sha256"]:
        raise SystemExit(f"media hash mismatch: {sha256(media)}")
    motion_text=MOTION.read_text(encoding="utf-8")
    page=HTML_TEMPLATE.replace("__ASCII__",html.escape(sheet)).replace("__JSON__",html.escape(motion_text)).replace("__VIDEO__",base64.b64encode(media).decode())
    HTML.write_text(page,encoding="utf-8")
    print(json.dumps({"ok":True,"media_sha256":sha256(media),"ascii_sha256":sha256(sheet.encode()),"frames":len(all_frames),"html_sha256":sha256(page.encode())},sort_keys=True))

if __name__=="__main__":
    main()
