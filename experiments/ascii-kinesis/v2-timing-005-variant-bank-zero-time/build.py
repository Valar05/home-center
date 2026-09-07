#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SLUG = "variant-bank-zero-time"
MOTION = HERE / "motion.json"
MP4 = HERE / f"{SLUG}.mp4"
HTML = HERE / f"{SLUG}.motion.html"
MANIFEST = HERE / "manifest.json"
RECEIPT = HERE / "receipt.json"
W, H = 40, 15
LINKS = [(0,1),(1,2),(1,3),(1,4),(0,5),(0,6),(5,7),(6,8)]
CHARS = ["@","+","O","l","r","o","o","L","R"]

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def bresenham(a, b):
    x0,y0=a; x1,y1=b
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1):
            return out
        e=2*err
        if e>=dy:
            err+=dy; x0+=sx
        if e<=dx:
            err+=dx; y0+=sy

def limb(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>2*abs(dy): return "-"
    if abs(dy)>2*abs(dx): return "|"
    return "\\" if dx*dy>0 else "/"

def ascii_pose(key):
    pts=key["pose_rig"]["j"]
    g=[[" "]*W for _ in range(H)]
    def put(x,y,c):
        if 0<=x<W and 0<=y<H: g[y][x]=c
    for a,b in LINKS:
        for x,y in bresenham(pts[a],pts[b])[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ":
                put(x,y,limb(pts[a],pts[b]))
    for i,(x,y) in enumerate(pts):
        put(x,y,CHARS[i])
    for x in range(14,28): put(x,13,"=")
    put(13,13,"["); put(28,13,"]")
    return "\n".join("".join(row).rstrip() for row in g)

def contact_sheet(data):
    out=[
      "ASCII KINESIS V2 TIMING 005 — VARIANT BANK / ZERO-TIME CONFIGURATION",
      "SOURCE ART: NOT EMBEDDED. ABSTRACT GENERIC RIG ONLY.",
      "SOURCE TIMING: NONE OBSERVED. ALL AUTHORED CADENCE BELOW IS INFERRED.",
      "AXIS NORMALIZATION: BODY_CLOCK = temporal; CONFIG_AXIS = NON-TEMPORAL; EFFECT_AXIS = unbound.",
      ""
    ]
    for key in data["keys"]:
        out += [
          f"[{key['key_id']}] {key['name']} | rig={key['pose_rig']['rig_id']} | clock={key['clock_channel']}",
          f"support/contact={key['support_contact']}",
          f"root/motion-arc={key['motion_arc_root_note']}",
          f"timing={key['timing_class']} | provenance={key['timing_provenance']} | causal_role={key['causal_role']}",
          f"config applicability={','.join(key['configuration_applicability'])} (NO EXTRA TIME KEYS)",
          ascii_pose(key),
          ""
        ]
    out += [
      "NON-TEMPORAL CONFIGURATION BANK:",
      "  CFG_A   CFG_B   CFG_C   CFG_D",
      "  selection changes presentation state only in this specimen; it does not advance BODY_CLOCK.",
      "",
      "COMPILED BODY_CLOCK:",
      "  T50 FOURS -> T51 TWOS -> T52 ONES -> T53 TWOS -> T54 ONES -> T55 TWOS -> T56 FOURS",
      "  total authored display frames at nominal 24 fps: 16",
      "  compiled configuration: CFG_A; alternate configurations reuse the identical key/timing graph.",
      "",
      "ONES = new drawing/key sample every display frame.",
      "TWOS = one drawing/key held two display frames.",
      "FOURS = one drawing/key held four display frames.",
      "At nominal 24 fps these correspond to ~24/~12/~6 samples per second.",
      "User shorthand 1s/2s/4s means ONES/TWOS/FOURS, never seconds.",
      "STREET_FIGHTER/CAPCOM = nonuniform authored gameplay timing; INFERRED timing is not source-authentic.",
      "",
      "TRANSFERABLE RULE EXERCISED:",
      "  COLLAPSE CONFIGURATION MULTIPLICITY BEFORE CADENCE.",
      "  A VARIANT BANK SPENDS ZERO TEMPORAL BANDWIDTH UNTIL A CAUSAL EVENT MAKES CONFIGURATION ITSELF TEMPORAL."
    ]
    return "\n".join(out)

def render_png(text, path, label):
    image=Image.new("RGB",(320,180),"black")
    draw=ImageDraw.Draw(image)
    try:
        font=ImageFont.truetype("DejaVuSansMono.ttf",8)
    except Exception:
        font=ImageFont.load_default()
    draw.text((5,4),label,fill="white",font=font)
    draw.multiline_text((5,17),text,fill="white",font=font,spacing=0)
    image.save(path)

def render_video(data):
    by_id={k["key_id"]:k for k in data["keys"]}
    with tempfile.TemporaryDirectory(prefix="akv2-t005-") as temp:
        td=Path(temp)
        for state in data["compile"]["timeline"]:
            key=by_id[state["body"]]
            label=f"{state['frame']:02d} {state['body']} {key['timing_class']} CFG_A(non-temporal)"
            render_png(ascii_pose(key),td/f"f{state['frame']:03d}.png",label)
        subprocess.run([
          "ffmpeg","-hide_banner","-loglevel","error","-y",
          "-framerate",str(data["compile"]["fps"]),
          "-i",str(td/"f%03d.png"),
          "-map_metadata","-1",
          "-c:v","libx264","-preset","veryslow","-crf","42",
          "-pix_fmt","yuv420p","-movflags","+faststart",
          str(MP4)
        ],check=True)

def make_page(data, ascii_text, media):
    audit_keys=[{
      "key_id":k["key_id"],
      "pose_rig":k["pose_rig"],
      "support_contact":k["support_contact"],
      "motion_arc_root_note":k["motion_arc_root_note"],
      "timing_class":k["timing_class"],
      "timing_provenance":k["timing_provenance"],
      "causal_role":k["causal_role"],
      "clock_channel":k["clock_channel"]
    } for k in data["keys"]]
    payload={
      "schema":data["schema"],"format_version":data["format_version"],
      "experiment_id":data["experiment_id"],"lane":data["lane"],"title":data["title"],
      "principle":data["principle"],"rig":data["rig"],"keys":audit_keys,
      "clock_channels":data["clock_channels"],"axis_separation":data["axis_separation"],
      "timing_doctrine":data["timing_doctrine"],
      "timing_provenance":{
        "OBSERVED":["TSR identity/422x414 PNG/full-sheet visual inspection","many full-body action families","lower repeated configuration/color rows","separate head/reference sprites","Animations(0)"],
        "INFERRED":["generic rig/causal roles","all ONES/TWOS/FOURS","BODY_CLOCK and zero-time CFG_A/B/C/D equivalence"],
        "UNKNOWN":["source chronology/exposures/cadence/hit-stop","runtime configuration semantics","source cross-channel synchronization"]
      },
      "source_rights":{
        "site":data["source"]["site"],"identity":data["source"]["identity"],
        "asset_id":data["source"]["asset_id"],"page_url":data["source"]["page_url"],
        "whole_sheet_inspected":True,"rights_note":"copyrighted whole-sheet evidence only; no source pixels/palette/contours/layout/tracing/redistribution/close imitation/choreography embedded"
      },
      "compile":{
        "fps":data["compile"]["fps"],
        "sequence":[f"{k['key_id']}:{k['timing_class']}" for k in data["keys"]],
        "frames_total":len(data["compile"]["timeline"]),
        "configuration_bank":data["compile"]["configuration_bank"],
        "configuration_keys_consumed":0,
        "connective_motion":"none; decisive keys + explicit holds only",
        "media_sha256":data["compile"]["media_sha256"],
        "media_bytes":data["compile"]["media_bytes"]
      },
      "compatibility":data["compatibility"],
      "manifest":data["manifest"],
      "correction_hooks":data["correction_hooks"]
    }
    compact=json.dumps(payload,separators=(",",":"),sort_keys=True)
    a=html.escape(ascii_text); j=html.escape(compact); b64=base64.b64encode(media).decode("ascii")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Timing 005</title><style>:root{{color-scheme:dark}}body{{font-family:system-ui;margin:1rem}}nav{{display:flex;gap:.5rem;flex-wrap:wrap}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0;white-space:pre;overflow:auto;line-height:1}}video{{max-width:100%;height:auto}}</style></head><body><h1>Variant Bank / Zero-Time Configuration</h1><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre>{a}</pre></section><section id="json" hidden><pre>{j}</pre></section><section id="video" hidden><video controls loop playsinline><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section><script>const b=[...document.querySelectorAll("button[data-view]")],s=[...document.querySelectorAll("section")];b.forEach(x=>x.onclick=()=>s.forEach(y=>y.hidden=y.id!==x.dataset.view));</script></body></html>'''

def main():
    data=json.loads(MOTION.read_text(encoding="utf-8"))
    render_video(data)
    media=MP4.read_bytes()
    media_hash=sha(media)
    media_bytes=len(media)
    declared=data["compile"].get("media_sha256") or ""
    if declared and declared != media_hash:
        raise SystemExit(f"media hash mismatch declared={declared} built={media_hash}")
    ascii_text=contact_sheet(data)
    ascii_hash=sha(ascii_text.encode("utf-8"))
    data["compile"]["media_sha256"]=media_hash
    data["compile"]["media_bytes"]=media_bytes
    data["compile"]["ascii_sheet_sha256"]=ascii_hash
    data["manifest"]={
      "schema":"ascii-kinesis.swarm-manifest.v2",
      "format_version":2,
      "status":"BUILT",
      "primary_tabs":["ASCII","JSON","VIDEO"],
      "video_source":"abstract_ascii_rig_only",
      "media_sha256":media_hash,
      "media_bytes":media_bytes
    }
    MOTION.write_text(json.dumps(data,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    HTML.write_text(make_page(data,ascii_text,media),encoding="utf-8")
    manifest={
      "schema":"ascii-kinesis.swarm-manifest.v2",
      "format_version":2,
      "experiment_id":data["experiment_id"],
      "lane":"timing",
      "primary_tabs":["ASCII","JSON","VIDEO"],
      "ascii_literal_text":True,
      "ascii_surface":"pre",
      "ligatures_disabled":True,
      "whitespace_preserved":True,
      "video_required":True,
      "video_source":"abstract_ascii_rig_only",
      "video_packaging":f"embedded MP4 data URI in {SLUG}.motion.html",
      "media_sha256":media_hash,
      "media_bytes":media_bytes,
      "source_art_embedded":False,
      "backward_compatible":True,
      "motion_dungeon":{
        "authored_ascii_keys":len(data["keys"]),
        "explicit_holds":True,
        "deterministic_connective_motion":True,
        "connective_frames_per_cycle":0,
        "connector_semantics_fail_closed":True,
        "ascii_only_frame_render":True,
        "fps":data["compile"]["fps"],
        "video_frames_total":len(data["compile"]["timeline"])
      },
      "source":{
        "site":data["source"]["site"],
        "asset_id":data["source"]["asset_id"],
        "page_url":data["source"]["page_url"],
        "whole_sheet_inspected":True,
        "source_timing_available":False
      },
      "files":["build.py","manifest.json","motion.json","receipt.json",f"{SLUG}.motion.html"],
      "reconstruction":"python3 build.py",
      "contract_test":"python3 tools/test_ascii_kinesis_swarm_contract_v2.py",
      "correction_hooks":data["correction_hooks"]
    }
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    receipt={
      "schema":"ascii-kinesis.v2-receipt",
      "experiment_id":data["experiment_id"],
      "status":"RENDERED_AWAITING_REPO_VERIFICATION",
      "repo_path":f"experiments/ascii-kinesis/{data['experiment_id']}/",
      "ship_commit":None,
      "verification_commit":None,
      "source":data["source"],
      "rights_note":data["source"]["rights_note"],
      "observation_inference_split":{
        "OBSERVED":data["source"]["observed"],
        "INFERRED":data["source"]["inferred"],
        "UNKNOWN":data["source"]["unknown"]
      },
      "key_timings":[
        {
          "key_id":k["key_id"],"name":k["name"],"clock_channel":k["clock_channel"],
          "timing_class":k["timing_class"],"timing_provenance":k["timing_provenance"]
        } for k in data["keys"]
      ],
      "media_sha256":media_hash,
      "media_bytes":media_bytes,
      "ascii_sheet_sha256":ascii_hash,
      "skill_mutation":{
        "performed":False,
        "owner":"POSE LAB v1 — Street Fighter II Temporal Kinesis",
        "owner_drive_id":"1fYe-mDSfesKCX75_kYX4dZ4wGlaOrt78PECuxIWGSFw",
        "reason":"No new reusable rule earned. The specimen compiles existing v1.3 temporal-equivalence and v1.5 assembly/configuration separation under the V2 SPA delivery contract."
      },
      "reconstruction":"python3 build.py",
      "target_contract_test":"PENDING",
      "repo_wide_contract_test_boundary":"PENDING",
      "repo_readback":"PENDING",
      "issue_343_receipt":None,
      "correction_hooks":data["correction_hooks"]
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
      "media_sha256":media_hash,"media_bytes":media_bytes,
      "ascii_sheet_sha256":ascii_hash,"frames":len(data["compile"]["timeline"]),
      "html_bytes":HTML.stat().st_size
    },sort_keys=True))

if __name__=="__main__":
    main()
