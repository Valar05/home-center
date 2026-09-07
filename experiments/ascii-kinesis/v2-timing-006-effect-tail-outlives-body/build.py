#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
SLUG = "effect-tail-outlives-body"
MOTION = HERE / "motion.json"
MP4 = HERE / f"{SLUG}.mp4"
HTML = HERE / f"{SLUG}.motion.html"
MANIFEST = HERE / "manifest.json"
RECEIPT = HERE / "receipt.json"

W, H = 48, 18
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

def body_grid(key, effect=None):
    g=[[" "]*W for _ in range(H)]
    def put(x,y,c):
        if 0<=x<W and 0<=y<H: g[y][x]=c
    pts=key["pose_rig"]["j"]
    for a,b in LINKS:
        for x,y in bresenham(pts[a],pts[b])[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ":
                put(x,y,limb(pts[a],pts[b]))
    for i,(x,y) in enumerate(pts):
        put(x,y,CHARS[i])
    for x in range(10,27): put(x,16,"=")
    put(9,16,"["); put(27,16,"]")
    if effect:
        ex,ey=effect["pose_rig"]["j"][0]
        put(ex,ey,"*")
    return "\n".join("".join(row).rstrip() for row in g)

def effect_strip(key):
    g=[" "]*W
    ex,_=key["pose_rig"]["j"][0]
    if 0<=ex<W: g[ex]="*"
    return "".join(g).rstrip()

def contact_sheet(data):
    body=[k for k in data["keys"] if k["clock_channel"]=="BODY_CLOCK"]
    eff=[k for k in data["keys"] if k["clock_channel"]=="EFFECT_CLOCK"]
    out=[
      "ASCII KINESIS V2 TIMING 006 — EFFECT TAIL OUTLIVES BODY RECOVERY",
      "SOURCE ART: NOT EMBEDDED. GENERIC ASCII RIG + GENERIC EFFECT POINT ONLY.",
      "SOURCE TIMING: NONE OBSERVED. ALL AUTHORED CADENCE BELOW IS INFERRED.",
      "AXES: temporal=BODY_CLOCK + post-release EFFECT_CLOCK | variant/config=NON-TEMPORAL/UNCOMPILED | source layout != chronology",
      "",
      "BODY CLOCK — decisive authored keys"
    ]
    for key in body:
        out += [
          f"[{key['key_id']}] {key['name']} | rig={key['pose_rig']['rig_id']} | clock={key['clock_channel']}",
          f"support/contact={key['support_contact']}",
          f"root/motion-arc={key['motion_arc_root_note']}",
          f"timing={key['timing_class']} | provenance={key['timing_provenance']} | causal_role={key['causal_role']}",
          body_grid(key),
          ""
        ]
    out += ["EFFECT CLOCK — decisive authored detached keys"]
    for key in eff:
        out += [
          f"[{key['key_id']}] {key['name']} | rig={key['pose_rig']['rig_id']} | clock={key['clock_channel']}",
          f"support/contact={key['support_contact']}",
          f"root/motion-arc={key['motion_arc_root_note']}",
          f"timing={key['timing_class']} | provenance={key['timing_provenance']} | causal_role={key['causal_role']}",
          f"|{effect_strip(key):<48}|",
          ""
        ]
    out += [
      "COMPILED CLOCK RELATION:",
      "  BODY   B60 FOURS -> B61 TWOS -> B62 ONES -> B63 TWOS -> B64 TWOS -> B65 FOURS",
      "  EFFECT dormant   -> E60 ONES -> E61 ONES -> E62 TWOS -> E63 TWOS -> E64 TWOS -> dormant",
      "  RELEASE_JOIN at display frame 06 starts EFFECT_CLOCK.",
      "  BODY reaches B65 READY_RETURN at display frame 11 while EFFECT remains E63/E64 through frame 13.",
      "  No body re-key is spent merely to let the detached effect finish.",
      "",
      "TIMING DOCTRINE:",
      "  ONES  = new drawing/key sample every display frame.",
      "  TWOS  = one drawing/key held two display frames.",
      "  FOURS = one drawing/key held four display frames.",
      "  At nominal 24 fps: ~24/~12/~6 samples per second.",
      "  User shorthand 1s/2s/4s means ONES/TWOS/FOURS, never seconds.",
      "  STREET_FIGHTER/CAPCOM = nonuniform authored gameplay timing; all specimen durations are INFERRED.",
      "",
      "TRANSFERABLE PRINCIPLE EXERCISED:",
      "  BODY RECOVERY DOES NOT OWE EFFECT COMPLETION.",
      "  A detached effect may outlive body recoil/recovery without forcing duplicate body keys."
    ]
    return "\n".join(out)

def render_png(text, path, label_lines):
    image=Image.new("RGB",(640,360),"black")
    draw=ImageDraw.Draw(image)
    try:
        font=ImageFont.truetype("DejaVuSansMono.ttf",13)
        small=ImageFont.truetype("DejaVuSansMono.ttf",11)
    except Exception:
        font=ImageFont.load_default()
        small=font
    y=8
    for line in label_lines:
        draw.text((8,y),line,fill="white",font=small)
        y += 15
    draw.multiline_text((8,58),text,fill="white",font=font,spacing=1)
    image.save(path)

def render_video(data):
    by_id={k["key_id"]:k for k in data["keys"]}
    with tempfile.TemporaryDirectory(prefix="akv2-t006-") as temp:
        td=Path(temp)
        for state in data["compile"]["timeline"]:
            body=by_id[state["body"]]
            effect=by_id[state["effect"]] if state["effect"] else None
            effect_label = f"{state['effect']} {effect['timing_class']}" if effect else "DORMANT"
            labels=[
                f"ASCII KINESIS / TIMING 006 / frame {state['frame']:02d}",
                f"BODY {state['body']} {body['timing_class']}   EFFECT {effect_label}",
                "AUTHORED KEYS + EXPLICIT HOLDS / NO SOURCE ART / NO TWEEN SEMANTICS"
            ]
            render_png(body_grid(body,effect), td/f"f{state['frame']:03d}.png", labels)
        subprocess.run([
          "ffmpeg","-hide_banner","-loglevel","error","-y",
          "-framerate",str(data["compile"]["fps"]),
          "-i",str(td/"f%03d.png"),
          "-map_metadata","-1",
          "-c:v","libx264","-preset","veryslow","-crf","38","-threads","1",
          "-pix_fmt","yuv420p","-movflags","+faststart",
          str(MP4)
        ],check=True)

def make_page(data, ascii_text, media):
    compact=json.dumps(data,separators=(",",":"),sort_keys=True)
    a=html.escape(ascii_text); j=html.escape(compact)
    b64=base64.b64encode(media).decode("ascii")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Timing 006</title><style>:root{{color-scheme:dark}}body{{font-family:system-ui;margin:1rem}}nav{{display:flex;gap:.5rem;flex-wrap:wrap}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0;white-space:pre;overflow:auto;line-height:1}}video{{max-width:100%;height:auto}}</style></head><body><h1>Effect Tail Outlives Body Recovery</h1><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre>{a}</pre></section><section id="json" hidden><pre>{j}</pre></section><section id="video" hidden><video controls loop playsinline><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section><script>const b=[...document.querySelectorAll("button[data-view]")],s=[...document.querySelectorAll("section")];b.forEach(x=>x.onclick=()=>s.forEach(y=>y.hidden=y.id!==x.dataset.view));</script></body></html>'''

def main():
    data=json.loads(MOTION.read_text(encoding="utf-8"))
    render_video(data)
    media=MP4.read_bytes()
    media_hash=sha(media); media_bytes=len(media)
    declared=data["compile"].get("media_sha256") or ""
    if declared and declared != media_hash:
        raise SystemExit(f"media hash mismatch declared={declared} built={media_hash}")
    ascii_text=contact_sheet(data)
    ascii_hash=sha(ascii_text.encode("utf-8"))
    data["compile"]["media_sha256"]=media_hash
    data["compile"]["media_bytes"]=media_bytes
    data["compile"]["ascii_sheet_sha256"]=ascii_hash
    data["manifest"].update({
      "status":"BUILT",
      "media_sha256":media_hash,
      "media_bytes":media_bytes,
      "ascii_sheet_sha256":ascii_hash,
      "video_source":"abstract_ascii_rig_only"
    })
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
      "ascii_sheet_sha256":ascii_hash,
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
        "source_timing_available":False,
        "source_sha256":data["source"]["source_sha256"],
        "source_bytes":data["source"]["source_bytes"]
      },
      "quality_gates":data["quality_gates"],
      "files":["build.py","manifest.json","motion.json","receipt.json",f"{SLUG}.motion.html"],
      "reconstruction":"python3 build.py",
      "contract_test":"python3 tools/test_ascii_kinesis_swarm_contract_v2.py",
      "correction_hooks":data["correction_hooks"]
    }
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    if not RECEIPT.exists():
        receipt={
          "schema":"ascii-kinesis.v2-receipt",
          "experiment_id":data["experiment_id"],
          "status":"RENDERED_AWAITING_REPO_VERIFICATION",
          "repo_path":f"experiments/ascii-kinesis/{data['experiment_id']}/",
          "ship_commit":None,
          "verification_commit":None,
          "issue_343_receipt":"POSTED_AFTER_REPO_VERIFICATION",
          "source":data["source"],
          "rights_note":data["source"]["rights_note"],
          "observation_inference_split":{"OBSERVED":data["source"]["observed"],"INFERRED":data["source"]["inferred"],"UNKNOWN":data["source"]["unknown"]},
          "key_timings":[{"key_id":k["key_id"],"name":k["name"],"clock_channel":k["clock_channel"],"timing_class":k["timing_class"],"timing_provenance":k["timing_provenance"]} for k in data["keys"]],
          "media_sha256":media_hash,
          "media_bytes":media_bytes,
          "ascii_sheet_sha256":ascii_hash,
          "skill_mutation":{"performed":False,"owner":"POSE LAB v1 — Street Fighter II Temporal Kinesis","owner_drive_id":"1fYe-mDSfesKCX75_kYX4dZ4wGlaOrt78PECuxIWGSFw","reason":"Specimen exercises existing v1.4/v1.9 detached-channel independence; no genuinely new reusable timing rule earned."},
          "tango":data["quality_gates"]["tango"],
          "noodle_queen":data["quality_gates"]["noodle_queen"],
          "verification":{"repo_readback":False,"contract_test":"NOT_RUN","deterministic_rebuild":False,"three_part_chat_delivery":False},
          "correction_hooks":data["correction_hooks"]
        }
        RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
