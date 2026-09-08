#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

P=Path(__file__).resolve().parent
M=P/"motion.json"; HTML=P/"guard-support-fork-repair.motion.html"; MP4=P/"guard-support-fork-repair.mp4"
MANIFEST=P/"manifest.json"; RECEIPT=P/"receipt.md"
W,H=56,22; HOLD={"ONES":1,"TWOS":2,"FOURS":4}
LINKS=[("head","neck"),("neck","shoulder_l"),("neck","shoulder_r"),("shoulder_l","elbow_l"),("elbow_l","hand_l"),("shoulder_r","elbow_r"),("elbow_r","hand_r"),("neck","pelvis"),("pelvis","knee_l"),("pelvis","knee_r"),("knee_l","foot_l"),("knee_r","foot_r")]

def bres(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): return out
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy

def limb(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>2*abs(dy): return "-"
    if abs(dy)>2*abs(dx): return "|"
    return "\\" if dx*dy>0 else "/"

def support_feet(state):
    if state in {"BOTH_REAR_BIASED","BOTH"}: return {"foot_l","foot_r"}
    if state=="REAR_ONLY": return {"foot_l"}
    if state=="FRONT_ONLY": return {"foot_r"}
    return set()

def pose_text(k,coords=None):
    j=coords or k["joints"]; g=[[" "]*W for _ in range(H)]
    def put(x,y,c):
        if 0<=x<W and 0<=y<H: g[y][x]=c
    for a,b in LINKS:
        for x,y in bres(j[a],j[b])[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ": put(x,y,limb(j[a],j[b]))
    for n,(x,y) in j.items(): put(x,y,"@" if n=="pelvis" else ("O" if n=="head" else "o"))
    for n in support_feet(k["support_contact"]):
        x,y=j[n]; put(x,min(H-1,y+1),"=")
    if k["support_contact"]=="BOTH_REAR_BIASED":
        x,y=j["foot_l"]; put(x,max(0,y-1),"^")
    if k["guard_authority"] in {"OWNED","CARRIED","RECOVERING"}:
        x,y=j["hand_r"]; put(min(W-1,x+1),y,"]")
    if k["contact_state"]=="IMPACT_RIGHT":
        x,y=j["hand_r"]; put(min(W-1,x+2),y,"X")
        for q in range(x+4,min(W,x+11)): put(q,y,"<")
    if k["recoil_debt"]>=0.45:
        x,y=j["pelvis"]
        for q in range(1,4): put(max(0,x-q),min(H-1,y+1),"~")
    return "\n".join("".join(r).rstrip() for r in g)

def qbez(a,b,t,off):
    e=t*t*(3-2*t); bulge=4*t*(1-t)
    return [round(a[0]+(b[0]-a[0])*e+off[0]*bulge),round(a[1]+(b[1]-a[1])*e+off[1]*bulge)]

def interp(a,b,t,arc):
    return {n:qbez(a["joints"][n],b["joints"][n],t,arc.get(n,[0,0])) for n in a["joints"]}

def frame_sequence(d):
    out=[]
    for i,k in enumerate(d["keys"]):
        for _ in range(HOLD[k["timing_class"]]): out.append({"label":k["key_id"],"name":k["name"],"semantic":k,"coords":k["joints"],"decisive":True})
        if i+1<len(d["keys"]):
            b=d["keys"][i+1]; c=k.get("connective_to_next",{}); n=int(c.get("frames",0)); arc=c.get("arc",{})
            for q in range(1,n+1):
                t=q/(n+1); out.append({"label":f"{k['key_id']}~{b['key_id']}","name":f"{k['name']} -> {b['name']}","semantic":k,"coords":interp(k,b,t,arc),"decisive":False})
    return out

def contact_sheet(d):
    rows=[]
    for k in d["keys"]:
        rows += [f"[{k['key_id']}] {k['name']} | {k['timing_class']} | {k['timing_provenance']}",
                 f"support={k['support_contact']} root={k['root_state']} contact={k['contact_state']} guard={k['guard_authority']} debt={k['recoil_debt']:.2f}",
                 pose_text(k),""]
    return "\n".join(rows).rstrip()+"\n"

def font(size):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf","/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"]:
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def render_frame(f,path):
    sem=f["semantic"]; im=Image.new("RGB",(480,270),"black"); dr=ImageDraw.Draw(im); f11=font(8); f13=font(10)
    header=f"{f['label']}  {sem['support_contact']}  debt={sem['recoil_debt']:.2f}"
    dr.text((6,4),header,fill="white",font=f11); dr.multiline_text((6,18),pose_text(sem,f["coords"]),fill="white",font=f13,spacing=0); im.save(path)

def probe(mp4):
    raw=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration","-of","json",str(mp4)],check=True,capture_output=True,text=True).stdout
    q=json.loads(raw); s=q["streams"][0]
    return {"tool":"ffprobe","codec":s["codec_name"],"width":int(s["width"]),"height":int(s["height"]),"fps":s["r_frame_rate"],"frames":int(s["nb_frames"]),"duration_seconds":float(q["format"]["duration"])}

def compile_video(d):
    seq=frame_sequence(d)
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,f in enumerate(seq): render_frame(f,td/f"f{i:04d}.png")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(d["compile"]["fps"]),"-i",str(td/"f%04d.png"),"-c:v","libx264","-preset","veryslow","-crf","40","-pix_fmt","yuv420p","-movflags","+faststart",str(MP4)],check=True)
    return seq

def manifest(d,sheet,media,pr):
    return {"schema":"ascii-kinesis.swarm-manifest.v2","format_version":2,"experiment_id":d["experiment_id"],"lane":"defense","revision":d["revision"],"principle":d["principle"],"primary_tabs":["ASCII","JSON","VIDEO"],"ascii_literal_text":True,"ascii_surface":"real preformatted DOM text","ligatures_disabled":True,"whitespace_preserved":True,"video_required":True,"video_source":"abstract_ascii_rig_only","source_art_embedded":False,"backward_compatible":True,"compatibility":d["compatibility"],"files":["build.py","manifest.json","motion.json","receipt.md","guard-support-fork-repair.motion.html"],"reconstruction":"python3 build.py","video_packaging":"authoritative MP4 bytes embedded as data URI in SPA","tracked_media_sidecar":False,"media_sha256":hashlib.sha256(media).hexdigest(),"media_bytes":len(media),"media_decode_preflight":pr,"ascii_sheet_sha256":hashlib.sha256(sheet.encode()).hexdigest(),"motion_dungeon":{"authored_ascii_keys":len(d["keys"]),"explicit_holds":True,"deterministic_connective_motion":True,"connector_semantics_fail_closed":True,"authored_non_linear_arcs":True,"ascii_only_frame_render":True,"fps":d["compile"]["fps"],"video_frames_total":pr["frames"]},"source":d["source"],"rights":d["rights"],"evidence":d["evidence"],"timing_provenance_required":True,"quality_gates":d["quality_gates"],"validation":d["validation"],"correction_hooks":d["correction_hooks"],"receipt_status":"QUALITY_GATES_PASS / REPO_READBACK_REQUIRED"}

def spa(d,sheet,media,man):
    order=d["rig_schema"]["joints"]; payload={"schema":"ascii-kinesis.motion-spa-json.v2","experiment_id":d["experiment_id"],"revision":d["revision"],"source":d["source"],"rights":d["rights"],"compatibility":d["compatibility"],"rig":d["rig_schema"],"timing_policy":d["timing_policy"],"keys":[{"key_id":k["key_id"],"name":k["name"],"joints":[k["joints"][n] for n in order],"support_contact":k["support_contact"],"root_state":k["root_state"],"contact_state":k["contact_state"],"guard_authority":k["guard_authority"],"recoil_debt":k["recoil_debt"],"timing_class":k["timing_class"],"timing_provenance":k["timing_provenance"],"causal_role":k["causal_role"],"motion_arc_root_note":k["motion_arc_root_note"]} for k in d["keys"]],"provenance":d["evidence"],"compile":{"method":d["compile"]["motion_dungeon_method"],"fps":d["compile"]["fps"],"media_sha256":man["media_sha256"],"media_bytes":man["media_bytes"],"media_decode_preflight":man["media_decode_preflight"],"ascii_sheet_sha256":man["ascii_sheet_sha256"]},"manifest_receipt":{"schema":man["schema"],"files":man["files"],"primary_tabs":man["primary_tabs"],"receipt_status":man["receipt_status"],"quality":{"tango":man["quality_gates"]["tango"]["status"],"noodle_queen":man["quality_gates"]["noodle_queen"]["status"]},"validation":man["validation"]},"correction_hooks":d["correction_hooks"]}
    j=json.dumps(payload,separators=(",",":"),sort_keys=True); b64=base64.b64encode(media).decode(); a64=base64.b64encode(gzip.compress(sheet.encode(),compresslevel=9,mtime=0)).decode(); j64=base64.b64encode(gzip.compress(j.encode(),compresslevel=9,mtime=0)).decode()
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Defense 007</title><style>:root{{color-scheme:dark;background:#0d0e0f;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1200px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#0d0e0f;padding:.5rem 0}}button{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1}}video{{display:block;max-width:100%;height:auto}}</style></head><body><h1>Guard / Support Authority Fork - Performance Repair</h1><nav role="tablist"><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre></pre></section><section id="json" hidden><pre></pre></section><section id="video" hidden><video controls playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section><script>const B=[...document.querySelectorAll("[data-view]")],S=[...document.querySelectorAll("section")];B.forEach(b=>b.onclick=()=>S.forEach(s=>s.hidden=s.id!==b.dataset.view));async function U(x){{const a=Uint8Array.from(atob(x),c=>c.charCodeAt(0));return new Response(new Blob([a]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([U("{a64}"),U("{j64}")]).then(([a,j])=>{{document.querySelector("#ascii pre").textContent=a;document.querySelector("#json pre").textContent=j}});</script></body></html>'''

def receipt(d,man):
    timing="\n".join(f"- {k['key_id']} {k['name']} - {k['timing_class']} - {k['timing_provenance']}" for k in d["keys"]); q=d["quality_gates"]
    return f'''# ASCII Kinesis V2 Defense 007 - repair receipt

Status: QUALITY_GATES_PASS / REPO_READBACK_REQUIRED

Revises `{d['revision']['revises']}`; negative fixture `{d['revision']['negative_fixture']}`; predecessor preserved; source change false.

Source: TSR Cammy / Super Street Fighter II SNES asset 5553 - {d['source']['url']} - inherited predecessor whole-sheet evidence family; no fresh source or concept. No Drew work and no source pixels/palette/contours/layout/tracing/choreography/redistribution/close imitation.

OBSERVED: inherited predecessor whole-sheet evidence only; no source-authentic timing measured.
INFERRED: all authored defensive performance, root/support mechanics, recoil/settle arcs, and every timing class.
UNKNOWN: source chronology/exposure/hit-stop/hitbox/support-foot/root path.

{timing}

MP4 SHA-256 `{man['media_sha256']}`; {man['media_bytes']} bytes; H.264 {man['media_decode_preflight']['width']}x{man['media_decode_preflight']['height']}; {man['media_decode_preflight']['frames']} frames; {man['media_decode_preflight']['duration_seconds']:.6f}s.
ASCII SHA-256 `{man['ascii_sheet_sha256']}`.

Tango: {q['tango']['status']}; iterations recorded in motion.json and manifest.
Noodle Queen: {q['noodle_queen']['status']} - TASTE {q['noodle_queen']['taste']['status']} / FUNCTION {q['noodle_queen']['function']['status']} / CONTEMPT {q['noodle_queen']['contempt']['status']}.

Contract candidate: `{d['validation'].get('candidate_status','UNKNOWN')}`; repository regression: `{d['validation'].get('repository_status','UNKNOWN')}`; exact boundary preserved in validation record.

Correction hooks: KEEP / REJECT / EXAGGERATE / COMPRESS / RETIME / CHANGE SOURCE / PROMOTE / SPAWN VARIANT / FIX BLOCKER / RERUN
'''

def main():
    d=json.loads(M.read_text()); seq=compile_video(d); media=MP4.read_bytes(); pr=probe(MP4); sheet=contact_sheet(d); man=manifest(d,sheet,media,pr)
    d["compile"].update({"media_sha256":man["media_sha256"],"media_bytes":man["media_bytes"],"media_decode_preflight":pr,"video_frames_total":pr["frames"],"semantic_frames_total":len(seq),"ascii_sheet_sha256":man["ascii_sheet_sha256"]})
    M.write_text(json.dumps(d,separators=(",",":"),sort_keys=True)+"\n"); man=manifest(d,sheet,media,pr); MANIFEST.write_text(json.dumps(man,separators=(",",":"),sort_keys=True)+"\n"); RECEIPT.write_text(receipt(d,man)); HTML.write_text(spa(d,sheet,media,man))
    print(json.dumps({"media_sha256":man["media_sha256"],"media_bytes":len(media),"frames":pr["frames"],"duration":pr["duration_seconds"],"ascii_sheet_sha256":man["ascii_sheet_sha256"],"html_bytes":HTML.stat().st_size},sort_keys=True))
if __name__=="__main__": main()
