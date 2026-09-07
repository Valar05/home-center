#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
SLUG="clock-rendezvous-reacquire"
MOTION=HERE/"motion.json"
MP4=HERE/f"{SLUG}.mp4"
HTML=HERE/f"{SLUG}.motion.html"
MANIFEST=HERE/"manifest.json"
RECEIPT=HERE/"receipt.json"
W,H=40,15
LINKS=[(0,1),(1,2),(1,3),(1,4),(0,5),(5,7),(0,6),(6,8)]
CHARS=["@","+","O","l","r","o","o","L","R"]

def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()

def line(a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): return out
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy

def limb(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    return "-" if abs(dx)>2*abs(dy) else "|" if abs(dy)>2*abs(dx) else "\\" if dx*dy>0 else "/"

def body_frame(key, object_xy=None):
    pts=key["pose_rig"]["j"]
    g=[[" "]*W for _ in range(H)]
    def put(x,y,c):
        if 0<=x<W and 0<=y<H: g[y][x]=c
    for a,b in LINKS:
        for x,y in line(pts[a],pts[b])[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ": put(x,y,limb(pts[a],pts[b]))
    for i,(x,y) in enumerate(pts): put(x,y,CHARS[i])
    for x in range(14,27): put(x,13,"=")
    put(13,13,"[");put(27,13,"]")
    if object_xy is not None: put(object_xy[0],object_xy[1],"*")
    return "\n".join("".join(row).rstrip() for row in g)

def object_panel(key):
    x,y=key["pose_rig"]["ctrl"][0]
    g=[[" "]*W for _ in range(H)]
    g[4][26]="+"
    g[y][x]="*"
    for xx,yy in [(28,4),(32,3),(35,6),(30,5),(26,4)]:
        if g[yy][xx]==" ": g[yy][xx]="."
    return "\n".join("".join(row).rstrip() for row in g)

def sheet(data):
    out=[
      "ASCII KINESIS V2 TIMING 004 — CLOCK RENDEZVOUS / REACQUIRE",
      "SOURCE ART: NOT EMBEDDED. ABSTRACT RIG ONLY. SOURCE TIMING: NONE OBSERVED.",
      "TEMPORAL AXIS IS SEPARATE FROM CONFIGURATION AND DETACHED-OBJECT AXES.",""
    ]
    for key in data["keys"]:
        out += [
          f"[{key['key_id']}] {key['name']} | clock={key['clock_channel']} | rig={key['pose_rig']['rig_id']}",
          f"support/contact={key['support_contact']}",
          f"root/arc={key['motion_arc_root_note']}",
          f"timing={key['timing_class']} provenance={key['timing_provenance']} | role={key['causal_role']}",
          body_frame(key) if key["clock_channel"]=="BODY_CLOCK" else object_panel(key),""
        ]
    out += [
      "COMPOSITE DISPLAY SCHEDULE (authored; all timing INFERRED):",
      "frames 00-03  B00 + CONFIG TOOL_DOCKED",
      "frames 04-07  B01 + CONFIG TOOL_DOCKED",
      "frame  08     B02 + O01   RELEASE_FORK",
      "frames 09-10  B03 + O02",
      "frames 11-12  B04 + O03",
      "frames 13-14  B04 + O04   (BODY KEY REUSED; no body rekey)",
      "frame  15     B05 + O05   REACQUIRE_RENDEZVOUS",
      "frames 16-19  B06 + CONFIG TOOL_DOCKED","",
      "AXES: temporal=BODY/OBJECT causal states | config=tool attached/absent | effect=separate unless causally joined.",
      "ONES=1 display frame; TWOS=2; FOURS=4. At nominal 24fps ≈24/12/6 samples/s.",
      "1s/2s/4s means ONES/TWOS/FOURS, never seconds.",
      "STREET_FIGHTER/CAPCOM=nonuniform authored gameplay timing; INFERRED timing is not source-authentic.",
      "RULE EXERCISED: CLOCKS MAY FORK, RUN INDEPENDENTLY, AND REJOIN ONLY AT AN AUTHORED CAUSAL CONTACT."
    ]
    return "\n".join(out)

def png(text,path,label):
    im=Image.new("RGB",(320,180),"black"); dr=ImageDraw.Draw(im)
    try: font=ImageFont.truetype("DejaVuSansMono.ttf",8)
    except Exception: font=ImageFont.load_default()
    dr.text((5,4),label,fill="white",font=font)
    dr.multiline_text((5,17),text,fill="white",font=font,spacing=0)
    im.save(path)

def render_video(data):
    byid={k["key_id"]:k for k in data["keys"]}
    with tempfile.TemporaryDirectory(prefix="akv2-t004-") as td:
        td=Path(td)
        for i,state in enumerate(data["compile"]["timeline"]):
            body=byid[state["body"]]
            obj=byid[state["object"]]["pose_rig"]["ctrl"][0] if state.get("object") else None
            label=f"{i:02d} {state['body']} + {state.get('object') or 'CONFIG'}"
            if state.get("event"): label += " "+state["event"]
            png(body_frame(body,obj),td/f"f{i:03d}.png",label)
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(data["compile"]["fps"]),"-i",str(td/"f%03d.png"),"-map_metadata","-1","-c:v","libx264","-preset","veryslow","-crf","42","-pix_fmt","yuv420p","-movflags","+faststart",str(MP4)],check=True)

def make_page(data, ascii_text, media):
    payload={k:data[k] for k in ["schema","format_version","experiment_id","lane","title","principle","rig","keys","clock_channels","axis_separation","timing_doctrine","source","compile","compatibility","manifest","correction_hooks"]}
    j=json.dumps(payload,separators=(",",":"),sort_keys=True)
    a=html.escape(ascii_text); jj=html.escape(j); b64=base64.b64encode(media).decode("ascii")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Timing 004</title><style>:root{{color-scheme:dark}}body{{font-family:system-ui;margin:1rem}}nav{{display:flex;gap:.5rem;flex-wrap:wrap}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0;white-space:pre;overflow:auto;line-height:1}}video{{max-width:100%;height:auto}}</style></head><body><h1>Clock Rendezvous / Reacquire</h1><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre>{a}</pre></section><section id="json" hidden><pre>{jj}</pre></section><section id="video" hidden><video controls loop playsinline><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section><script>let b=[...document.querySelectorAll("button[data-view]")],s=[...document.querySelectorAll("section")];b.forEach(x=>x.onclick=()=>s.forEach(y=>y.hidden=y.id!==x.dataset.view));</script></body></html>'''

def main():
    data=json.loads(MOTION.read_text(encoding="utf-8"))
    render_video(data); media=MP4.read_bytes(); mh=sha(media); mb=len(media)
    declared=data["compile"].get("media_sha256") or ""
    if declared and declared!=mh: raise SystemExit(f"media hash mismatch declared={declared} built={mh}")
    ascii_text=sheet(data); ah=sha(ascii_text.encode("utf-8"))
    data["compile"]["media_sha256"]=mh; data["compile"]["media_bytes"]=mb; data["compile"]["ascii_sheet_sha256"]=ah
    data["manifest"]={"schema":"ascii-kinesis.swarm-manifest.v2","format_version":2,"status":"BUILT","primary_tabs":["ASCII","JSON","VIDEO"],"video_source":"abstract_ascii_rig_only","media_sha256":mh,"media_bytes":mb}
    HTML.write_text(make_page(data,ascii_text,media),encoding="utf-8")
    hooks=data["correction_hooks"]
    manifest={"schema":"ascii-kinesis.swarm-manifest.v2","format_version":2,"experiment_id":data["experiment_id"],"lane":"timing","primary_tabs":["ASCII","JSON","VIDEO"],"ascii_literal_text":True,"ascii_surface":"pre","ligatures_disabled":True,"whitespace_preserved":True,"video_required":True,"video_source":"abstract_ascii_rig_only","video_packaging":f"embedded MP4 data URI in {SLUG}.motion.html","media_sha256":mh,"media_bytes":mb,"source_art_embedded":False,"backward_compatible":True,"motion_dungeon":{"authored_ascii_keys":len(data["keys"]),"explicit_holds":True,"deterministic_connective_motion":True,"connective_frames_per_cycle":0,"connector_semantics_fail_closed":True,"ascii_only_frame_render":True,"fps":data["compile"]["fps"],"video_frames_total":len(data["compile"]["timeline"])},"source":{"site":data["source"]["site"],"asset_id":data["source"]["asset_id"],"page_url":data["source"]["page_url"],"whole_sheet_inspected":True,"source_timing_available":False},"files":["build.py","manifest.json","motion.json","receipt.json",f"{SLUG}.motion.html"],"reconstruction":"python3 build.py","contract_test":"python3 tools/test_ascii_kinesis_swarm_contract_v2.py","correction_hooks":hooks}
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    receipt={"schema":"ascii-kinesis.v2-receipt","experiment_id":data["experiment_id"],"status":"RENDERED_AWAITING_REPO_VERIFICATION","repo_path":f"experiments/ascii-kinesis/{data['experiment_id']}/","ship_commit":None,"verification_commit":None,"source":data["source"],"rights_note":data["source"]["rights_note"],"observation_inference_split":{"OBSERVED":data["source"]["observed"],"INFERRED":data["source"]["inferred"],"UNKNOWN":data["source"]["unknown"]},"key_timings":[{"key_id":k["key_id"],"name":k["name"],"clock_channel":k["clock_channel"],"timing_class":k["timing_class"],"timing_provenance":k["timing_provenance"]} for k in data["keys"]],"media_sha256":mh,"media_bytes":mb,"ascii_sheet_sha256":ah,"skill_mutation":{"performed":False,"owner":"POSE LAB v1 — Street Fighter II Temporal Kinesis","owner_drive_id":"1fYe-mDSfesKCX75_kYX4dZ4wGlaOrt78PECuxIWGSFw","reason":"No new reusable timing doctrine earned. This specimen applies existing v1.4 causal joins, v1.5 configuration separation, v1.9 independent clocks, and v1.10 scoped synchronization."},"reconstruction":"python3 build.py","target_contract_test":"PENDING","repo_wide_contract_test_boundary":"PENDING","repo_readback":"PENDING","correction_hooks":hooks}
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"media_sha256":mh,"media_bytes":mb,"ascii_sheet_sha256":ah,"frames":len(data["compile"]["timeline"]),"html_bytes":HTML.stat().st_size},sort_keys=True))

if __name__=="__main__": main()
