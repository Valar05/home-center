#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
SLUG="inertial-join-sparse-rekey"
MOTION=HERE/"motion.json"; MP4=HERE/f"{SLUG}.mp4"; HTML=HERE/f"{SLUG}.motion.html"; MANIFEST=HERE/"manifest.json"; RECEIPT=HERE/"receipt.json"
HOLD={"ONES":1,"TWOS":2,"FOURS":4}; W,H=40,15
LINKS=[(0,1),(1,2),(1,3),(1,4),(0,5),(5,7),(0,6),(6,8)]
CHARS=["@","+","O","l","r","o","o","L","R"]

def sha(b): return hashlib.sha256(b).hexdigest()
def line(a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): return out
        e=2*err
        if e>=dy:err+=dy;x0+=sx
        if e<=dx:err+=dx;y0+=sy
def limb(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    return "-" if abs(dx)>2*abs(dy) else "|" if abs(dy)>2*abs(dx) else "\\" if dx*dy>0 else "/"
def frame(k,off=0):
    pts=[[x+off,y] for x,y in k["pose_rig"]["j"]];g=[[" "]*W for _ in range(H)]
    def put(x,y,c):
        if 0<=x<W and 0<=y<H:g[y][x]=c
    for a,b in LINKS:
        for x,y in line(pts[a],pts[b])[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ":put(x,y,limb(pts[a],pts[b]))
    for i,(x,y) in enumerate(pts):put(x,y,CHARS[i])
    for x in range(12+off,25+off):put(x,13,"=")
    put(11+off,13,"[");put(25+off,13,"]")
    return "\n".join("".join(r).rstrip() for r in g)

def sheet(data):
    out=["ASCII KINESIS V2 TIMING 003 — INERTIAL JOIN SPARSE REKEY",
         "SOURCE ART: NOT EMBEDDED. ABSTRACT RIG ONLY. SOURCE TIMING: NONE OBSERVED.",
         "PARENT TRANSFORM MAY MOVE INSIDE A HELD CHILD KEY; LOAD CHANGE EARNS LOCAL REKEY.",""]
    for k in data["keys"]:
        out += [f"[{k['key_id']}] {k['name']} | rig={k['pose_rig']['rig_id']} | support={k['support_contact']}",
                f"root/arc={k['motion_arc_root_note']}",
                f"timing={k['timing_class']} provenance={k['timing_provenance']} | role={k['causal_role']}",
                frame(k),""]
    out += ["AXES: temporal=LOCAL load state | parent=PLATFORM transform | variant/config≠time | effect=fail-closed",
            "ONES=1 display frame; TWOS=2; FOURS=4. At nominal 24fps ≈24/12/6 samples/s.",
            "1s/2s/4s means ONES/TWOS/FOURS, never seconds.",
            "STREET_FIGHTER/CAPCOM=nonuniform authored gameplay timing; INFERRED timing is not source-authentic."]
    return "\n".join(out)

def png(text,path,label):
    im=Image.new("RGB",(320,180),"black");dr=ImageDraw.Draw(im)
    try:f=ImageFont.truetype("DejaVuSansMono.ttf",8)
    except Exception:f=ImageFont.load_default()
    dr.text((5,4),label,fill="white",font=f);dr.multiline_text((5,17),text,fill="white",font=f,spacing=0);im.save(path)

def video(data):
    cyc=[]
    for k in data["keys"]:
        n=HOLD[k["timing_class"]]
        if len(k["parent_step"])!=n:raise ValueError(k["key_id"])
        for i,off in enumerate(k["parent_step"]):cyc.append((k,off,i))
    with tempfile.TemporaryDirectory(prefix="akv2-t003-") as td:
        td=Path(td)
        for i,(k,off,hi) in enumerate(cyc):
            png(frame(k,off),td/f"f{i:03d}.png",f"{k['key_id']} {k['name']} H{hi+1} PARENT+{off}")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(data["compile"]["fps"]),"-i",str(td/"f%03d.png"),"-map_metadata","-1","-c:v","libx264","-preset","veryslow","-crf","42","-pix_fmt","yuv420p","-movflags","+faststart",str(MP4)],check=True)
    return len(cyc)

def esc(s):return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
def page(data,ascii_text,b64):
    payload={k:data[k] for k in ["schema","experiment_id","rig","keys","clock_channels","axis_separation","timing_doctrine","source","compatibility","manifest"]}
    payload["media_sha256"]=data["compile"]["media_sha256"];payload["media_bytes"]=data["compile"]["media_bytes"]
    j=json.dumps(payload,separators=(",",":"),sort_keys=True)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Timing 003</title><style>:root{{color-scheme:dark}}body{{font-family:system-ui;margin:1rem}}nav{{display:flex;gap:.5rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0;white-space:pre;overflow:auto;line-height:1}}video{{max-width:100%}}</style></head><body><h1>Inertial Join Sparse Rekey</h1><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre>{esc(ascii_text)}</pre></section><section id="json" hidden><pre>{esc(j)}</pre></section><section id="video" hidden><video controls loop playsinline><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section><script>let b=[...document.querySelectorAll("button[data-view]")],s=[...document.querySelectorAll("section")];b.forEach(x=>x.onclick=()=>s.forEach(y=>y.hidden=y.id!==x.dataset.view));</script></body></html>'''

def main():
    data=json.loads(MOTION.read_text());n=video(data);media=MP4.read_bytes();h=sha(media);a=sheet(data);ah=sha(a.encode())
    data["ascii_sheet_sha256"]=ah;data["compile"].update(media_sha256=h,media_bytes=len(media),authored_hold_frames_per_cycle=n,semantic_frames_per_cycle=n,video_frames_total=n)
    data["manifest"]={"schema":"ascii-kinesis.swarm-manifest.v2","format_version":2,"status":"BUILT","primary_tabs":["ASCII","JSON","VIDEO"],"video_source":"abstract_ascii_rig_only","media_sha256":h,"media_bytes":len(media)}
    HTML.write_text(page(data,a,base64.b64encode(media).decode()))
    hooks=["KEEP","REJECT","EXAGGERATE","COMPRESS","RETIME","CHANGE SOURCE","PROMOTE","SPAWN VARIANT","FIX BLOCKER","RERUN"]
    man={"schema":"ascii-kinesis.swarm-manifest.v2","format_version":2,"experiment_id":data["experiment_id"],"lane":"timing","primary_tabs":["ASCII","JSON","VIDEO"],"ascii_literal_text":True,"ascii_surface":"pre","ligatures_disabled":True,"whitespace_preserved":True,"video_required":True,"video_source":"abstract_ascii_rig_only","video_packaging":f"embedded MP4 data URI in {SLUG}.motion.html","media_sha256":h,"media_bytes":len(media),"source_art_embedded":False,"backward_compatible":True,"motion_dungeon":{"authored_ascii_keys":len(data["keys"]),"explicit_holds":True,"deterministic_connective_motion":True,"connective_frames_per_cycle":0,"connector_semantics_fail_closed":True,"parent_transform_updates_are_not_child_keys":True,"ascii_only_frame_render":True,"fps":data["compile"]["fps"],"video_frames_total":n},"source":{"site":data["source"]["site"],"asset_id":data["source"]["asset_id"],"page_url":data["source"]["page_url"],"raw_sha256":data["source"]["sheet"]["raw_sha256"],"whole_sheet_inspected":True,"source_timing_available":False},"files":["build.py","manifest.json","motion.json","receipt.json",f"{SLUG}.motion.html"],"reconstruction":"python3 build.py","contract_test":"python3 tools/test_ascii_kinesis_swarm_contract_v2.py","correction_hooks":hooks}
    MANIFEST.write_text(json.dumps(man,indent=2,sort_keys=True)+"\n")
    rec={"schema":"ascii-kinesis.v2-receipt","experiment_id":data["experiment_id"],"status":"RENDERED_AWAITING_REPO_VERIFICATION","repo_path":f"experiments/ascii-kinesis/{data['experiment_id']}/","source":data["source"],"rights_note":data["source"]["rights_note"],"observation_inference_split":{"OBSERVED":data["source"]["observed"],"INFERRED":"All abstract rig geometry, semantic compression, parent-motion/load profile, causal roles, and ONES/TWOS/FOURS assignments.","UNKNOWN":data["source"]["unknown"]},"key_timings":[{"key_id":k["key_id"],"name":k["name"],"timing_class":k["timing_class"],"timing_provenance":k["timing_provenance"]} for k in data["keys"]],"media_sha256":h,"media_bytes":len(media),"ascii_sheet_sha256":ah,"skill_mutation":{"performed":False,"owner":"POSE LAB v1 — Street Fighter II Temporal Kinesis","owner_drive_id":"1fYe-mDSfesKCX75_kYX4dZ4wGlaOrt78PECuxIWGSFw","reason":"No new reusable rule earned; specimen exercises existing v1.6 parent-transform separation and v1.7 inertial-join/support-load doctrine."},"reconstruction":"python3 build.py","contract_test":"PENDING_EXTERNAL_RUN","repo_readback":"PENDING","correction_hooks":hooks}
    RECEIPT.write_text(json.dumps(rec,indent=2,sort_keys=True)+"\n")
    print(json.dumps({"media_sha256":h,"media_bytes":len(media),"ascii_sheet_sha256":ah,"frames":n,"html_bytes":HTML.stat().st_size},sort_keys=True))
if __name__=="__main__":main()
