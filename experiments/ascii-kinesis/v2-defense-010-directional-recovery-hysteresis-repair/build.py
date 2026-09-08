#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

P = Path(__file__).resolve().parent
MOTION = P / "motion.json"
HTML = P / "directional-recovery-hysteresis-repair.motion.html"
MP4 = P / "directional-recovery-hysteresis-repair.mp4"
MANIFEST = P / "manifest.json"
RECEIPT = P / "receipt.md"

GRID_W, GRID_H = 62, 20
HOLD = {"ONES": 1, "TWOS": 2, "FOURS": 4}
LINKS = [
    ("head","neck"), ("neck","shoulder_l"), ("neck","shoulder_r"),
    ("shoulder_l","elbow_l"), ("elbow_l","hand_l"),
    ("shoulder_r","elbow_r"), ("elbow_r","hand_r"),
    ("neck","pelvis"), ("pelvis","knee_l"), ("pelvis","knee_r"),
    ("knee_l","foot_l"), ("knee_r","foot_r")
]

def bres(a, b):
    x0,y0=a; x1,y1=b
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy; out=[]
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

def locked_support_joints(state):
    if state in {"BOTH_RIGHT_BIASED","BOTH_LEFT_BIASED","BOTH_OFFSET"}:
        return {"foot_l","foot_r"}
    if state in {"RIGHT_DOMINANT","RIGHT_ONLY","RIGHT_TOE"}:
        return {"foot_r"}
    if state == "LEFT_ONLY":
        return {"foot_l"}
    if state == "HAND_R_ONLY":
        return {"hand_r"}
    return set()

def pose_text(k, coords=None):
    j = coords or k["joints"]
    g = [[" "]*GRID_W for _ in range(GRID_H)]
    def put(x,y,c):
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            g[y][x]=c

    for x in range(2, GRID_W-2):
        put(x,18,"_")

    for a,b in LINKS:
        for x,y in bres(j[a],j[b])[1:-1]:
            if 0<=x<GRID_W and 0<=y<GRID_H and g[y][x]==" ":
                put(x,y,limb(j[a],j[b]))

    for name,(x,y) in j.items():
        put(x,y,"@" if name=="pelvis" else ("O" if name=="head" else "o"))

    s=k["support_contact"]
    if s in {"BOTH_RIGHT_BIASED","BOTH_LEFT_BIASED","BOTH_OFFSET"}:
        for n in ("foot_l","foot_r"):
            x,y=j[n]; put(x,min(GRID_H-1,y+1),"=")
    elif s in {"RIGHT_DOMINANT","RIGHT_ONLY","RIGHT_TOE"}:
        x,y=j["foot_r"]; put(x,min(GRID_H-1,y+1),"=")
        put(x,max(0,y-1),"!" if s!="RIGHT_TOE" else "'")
    elif s=="LEFT_ONLY":
        x,y=j["foot_l"]; put(x,min(GRID_H-1,y+1),"="); put(x,max(0,y-1),"!")
    elif s=="HAND_R_ONLY":
        x,y=j["hand_r"]; put(x,min(GRID_H-1,y+1),"#")

    if s=="BOTH_RIGHT_BIASED":
        x,y=j["foot_r"]; put(x,max(0,y-1),"^")
    if s=="BOTH_LEFT_BIASED":
        x,y=j["foot_l"]; put(x,max(0,y-1),"^")

    if k["contact_state"]=="IMPACT_LEFT":
        x,y=j["hand_l"]; put(x,y,"X")
        for q in range(max(2,x-10), max(2,x-2)):
            put(q,y,">")
    if k["contact_state"]=="GROUND_SKID_HAND_R":
        x,y=j["hand_r"]; put(x,y,"X")

    if k["recovery_debt"] >= .18:
        x,y=j["pelvis"]
        for q in range(1,4):
            put(max(0,x-q),min(GRID_H-1,y+1),"~")

    rows=["".join(r).rstrip() for r in g]
    while rows and not rows[-1]: rows.pop()
    return "\n".join(rows)

def qbez(a,b,t,offset):
    e=t*t*(3-2*t)
    bulge=4*t*(1-t)
    return [
        round(a[0]+(b[0]-a[0])*e + offset[0]*bulge),
        round(a[1]+(b[1]-a[1])*e + offset[1]*bulge)
    ]

def connector_coords(a,b,t,cfg):
    root_arc=cfg.get("root_arc",[0,0])
    secondary=cfg.get("secondary_lag",{})
    locked=locked_support_joints(a["support_contact"])
    out={}
    for n in a["joints"]:
        if n in locked:
            out[n]=list(a["joints"][n])
            continue
        extra=secondary.get(n,[0,0])
        if n=="pelvis":
            scale=1.0
        elif n in {"head","neck","shoulder_l","shoulder_r"}:
            scale=.75
        else:
            scale=.45
        off=[root_arc[0]*scale+extra[0], root_arc[1]*scale+extra[1]]
        out[n]=qbez(a["joints"][n], b["joints"][n], t, off)
    return out

def frame_sequence(d):
    seq=[]
    for i,k in enumerate(d["keys"]):
        for _ in range(HOLD[k["timing_class"]]):
            seq.append({"label":k["key_id"],"name":k["name"],"semantic":k,"coords":k["joints"],"decisive":True})
        if i+1 < len(d["keys"]):
            cfg=k.get("connective_to_next",{})
            n=int(cfg.get("frames",0))
            nxt=d["keys"][i+1]
            for q in range(1,n+1):
                t=q/(n+1)
                seq.append({
                    "label":f'{k["key_id"]}~{nxt["key_id"]}',
                    "name":f'{k["name"]} -> {nxt["name"]}',
                    "semantic":k,
                    "coords":connector_coords(k,nxt,t,cfg),
                    "decisive":False
                })
    return seq

def contact_sheet(d):
    rows=[
        "ASCII KINESIS V2 DEFENSE 010 — DIRECTIONAL RECOVERY HYSTERESIS REPAIR",
        f'revises: {d["revision"]["revises"]}',
        f'negative_fixture: {d["revision"]["negative_fixture"]}',
        f'source: TSR Lunar / Mischief Makers / N64 / Bosses / asset {d["source"]["asset_id"]} — inherited whole-sheet evidence family',
        "legend: @ pelvis/root | O head | o joint | = trusted support | ! sole/dominant support | ' toe-only failure | # consequence hand support | X contact | ~ recovery debt",
        ""
    ]
    for k in d["keys"]:
        rows.extend([
            f'[{k["key_id"]}] {k["name"]} | {k["timing_class"]} | {k["timing_provenance"]}',
            f'support={k["support_contact"]} root={k["root_state"]} contact={k["contact_state"]} force={k["force_direction"]} guard={k["guard_authority"]} readiness={k["readiness"]} memory={k["impact_memory"]} debt={k["recovery_debt"]:.2f}',
            f'role={k["causal_role"]}',
            f'arc={k["motion_arc_root_note"]}',
            pose_text(k),
            ""
        ])
    return "\n".join(rows).rstrip()+"\n"

def get_font(size):
    for fp in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"
    ):
        if Path(fp).exists():
            return ImageFont.truetype(fp,size)
    return ImageFont.load_default()

def render_frame(frame,path):
    sem=frame["semantic"]
    im=Image.new("RGB",(640,360),"black")
    dr=ImageDraw.Draw(im)
    f10=get_font(10); f13=get_font(13)
    dr.text((12,8),f'{frame["label"]}  {frame["name"]}',fill="white",font=f10)
    dr.text((12,25),f'support={sem["support_contact"]}  root={sem["root_state"]}  debt={sem["recovery_debt"]:.2f}',fill="white",font=f10)
    dr.text((12,40),f'contact={sem["contact_state"]}  force={sem["force_direction"]}  memory={sem["impact_memory"]}',fill="white",font=f10)
    dr.multiline_text((12,63),pose_text(sem,frame["coords"]),fill="white",font=f13,spacing=0)
    dr.text((12,343),f'{sem["timing_class"]} / {sem["timing_provenance"]}',fill="white",font=f10)
    im.save(path)

def compile_video(d, frame_dir=None):
    seq=frame_sequence(d)
    tmp=None
    if frame_dir is None:
        tmp=tempfile.TemporaryDirectory()
        td=Path(tmp.name)
    else:
        td=Path(frame_dir); td.mkdir(parents=True,exist_ok=True)
    for i,frame in enumerate(seq):
        render_frame(frame,td/f"f{i:04d}.png")
    subprocess.run([
        "ffmpeg","-hide_banner","-loglevel","error","-y",
        "-framerate",str(d["compile"]["fps"]),"-i",str(td/"f%04d.png"),
        "-an","-c:v","libx264","-preset","veryslow","-crf","42",
        "-pix_fmt","yuv420p","-threads","1",
        "-fflags","+bitexact","-flags:v","+bitexact","-map_metadata","-1",
        "-movflags","+faststart",str(MP4)
    ],check=True)
    if tmp: tmp.cleanup()
    return seq

def probe(mp4):
    raw=subprocess.run([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration",
        "-of","json",str(mp4)
    ],check=True,capture_output=True,text=True).stdout
    q=json.loads(raw); s=q["streams"][0]
    return {
        "tool":"ffprobe","codec":s["codec_name"],"width":int(s["width"]),
        "height":int(s["height"]),"fps":s["r_frame_rate"],
        "frames":int(s["nb_frames"]),"duration_seconds":float(q["format"]["duration"])
    }

def make_manifest(d,sheet,media,decode):
    return {
        "schema":"ascii-kinesis.swarm-manifest.v2","format_version":2,
        "experiment_id":d["experiment_id"],"lane":"defense",
        "revision":d["revision"],"principle":d["principle"],
        "primary_tabs":["ASCII","JSON","VIDEO"],
        "ascii_literal_text":True,"ascii_surface":"real preformatted DOM text",
        "ligatures_disabled":True,"whitespace_preserved":True,
        "video_required":True,"video_source":"abstract_ascii_rig_only",
        "source_art_embedded":False,"backward_compatible":True,
        "compatibility":d["compatibility"],
        "files":["build.py","manifest.json","motion.json","receipt.md","directional-recovery-hysteresis-repair.motion.html"],
        "reconstruction":"python3 build.py",
        "video_packaging":"authoritative MP4 bytes embedded as data URI in SPA",
        "tracked_media_sidecar":False,
        "media_sha256":hashlib.sha256(media).hexdigest(),"media_bytes":len(media),
        "media_decode_preflight":decode,
        "ascii_sheet_sha256":hashlib.sha256(sheet.encode()).hexdigest(),
        "motion_dungeon":{
            "authored_ascii_keys":len(d["keys"]),"explicit_holds":True,
            "deterministic_connective_motion":True,
            "connector_semantics_fail_closed":True,
            "trusted_support_joint_locking":True,
            "authored_non_linear_arcs":True,"authored_bridge_keys":True,
            "ascii_only_frame_render":True,"fps":d["compile"]["fps"],
            "video_frames_total":decode["frames"],"automatic_loop":False
        },
        "source":d["source"],"rights":d["rights"],"evidence":d["evidence"],
        "timing_provenance_required":True,
        "quality_gates":d["quality_gates"],"validation":d["validation"],
        "correction_hooks":d["correction_hooks"],
        "receipt_status":(
            "QUALITY_GATES_PASS / REPO_READBACK_REQUIRED"
            if d["quality_gates"]["tango"]["status"]=="PASS"
            and d["quality_gates"]["noodle_queen"]["status"]=="PASS"
            else "QUALITY_GATES_PENDING"
        )
    }

def make_spa(d,sheet,media,manifest):
    payload={
        "schema":"ascii-kinesis.motion-spa-json.v2",
        "experiment_id":d["experiment_id"],"lane":"defense",
        "revision":d["revision"],"principle":d["principle"],
        "source":d["source"],"rights":d["rights"],
        "whole_source_evidence":d["evidence"],
        "compatibility":d["compatibility"],"rig":d["rig_schema"],
        "timing_policy":d["timing_policy"],
        "keys":[{
            "key_id":k["key_id"],"name":k["name"],"pose_rig":k["joints"],
            "support_contact":k["support_contact"],"root_state":k["root_state"],
            "constraint_state":k["constraint_state"],"contact_state":k["contact_state"],
            "force_direction":k["force_direction"],"guard_authority":k["guard_authority"],
            "readiness":k["readiness"],"impact_memory":k["impact_memory"],
            "recovery_debt":k["recovery_debt"],
            "timing_class":k["timing_class"],"timing_provenance":k["timing_provenance"],
            "causal_role":k["causal_role"],"motion_arc_root_note":k["motion_arc_root_note"],
            "connective_to_next":k.get("connective_to_next")
        } for k in d["keys"]],
        "compile":{
            "method":d["compile"]["motion_dungeon_method"],"fps":d["compile"]["fps"],
            "connector_rule":d["compile"]["connector_rule"],
            "transitions_invent_semantics":False,
            "media_sha256":manifest["media_sha256"],"media_bytes":manifest["media_bytes"],
            "media_decode_preflight":manifest["media_decode_preflight"],
            "ascii_sheet_sha256":manifest["ascii_sheet_sha256"]
        },
        "manifest_receipt":{
            "schema":manifest["schema"],"files":manifest["files"],
            "primary_tabs":manifest["primary_tabs"],"receipt_status":manifest["receipt_status"],
            "quality_gates":d["quality_gates"],"validation":d["validation"]
        },
        "correction_hooks":d["correction_hooks"]
    }
    structured=json.dumps(payload,indent=2,sort_keys=True)
    media64=base64.b64encode(media).decode("ascii")
    ascii64=base64.b64encode(gzip.compress(sheet.encode(),compresslevel=9,mtime=0)).decode("ascii")
    json64=base64.b64encode(gzip.compress(structured.encode(),compresslevel=9,mtime=0)).decode("ascii")
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Defense 010 — Directional Recovery Hysteresis Repair</title>
<style>
:root{{color-scheme:dark;background:#0b0c0d;color:#eee;font-family:system-ui,sans-serif}}
body{{margin:0;padding:1rem;max-width:1200px}} nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#0b0c0d;padding:.5rem 0}}
button{{font:inherit;padding:.55rem .9rem}} section[hidden]{{display:none}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1}}
video{{display:block;max-width:100%;height:auto}}
</style></head>
<body><h1>Directional Recovery Hysteresis — Defense004 Repair</h1>
<nav role="tablist"><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii"><pre></pre></section>
<section id="json" hidden><pre></pre></section>
<section id="video" hidden><video controls playsinline preload="metadata"><source src="data:video/mp4;base64,{media64}" type="video/mp4"></video></section>
<script>
const B=[...document.querySelectorAll("[data-view]")],S=[...document.querySelectorAll("section")];
B.forEach(b=>b.onclick=()=>S.forEach(s=>s.hidden=s.id!==b.dataset.view));
async function ungzip(x){{const a=Uint8Array.from(atob(x),c=>c.charCodeAt(0));return new Response(new Blob([a]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}
Promise.all([ungzip("{ascii64}"),ungzip("{json64}")]).then(([a,j])=>{{document.querySelector("#ascii pre").textContent=a;document.querySelector("#json pre").textContent=j;}});
</script></body></html>
'''

def make_receipt(d,manifest):
    lines=[
        "# ASCII Kinesis V2 Defense 010 — Directional Recovery Hysteresis Repair",
        "",
        f"- status: `{manifest['receipt_status']}`",
        f"- experiment: `{d['experiment_id']}`",
        f"- revises: `{d['revision']['revises']}`",
        f"- negative_fixture: `{d['revision']['negative_fixture']}`",
        f"- predecessor_preserved: `{str(d['revision']['predecessor_preserved']).lower()}`",
        f"- source_change: `{str(d['revision']['source_change']).lower()}`",
        f"- source: TSR Lunar / Mischief Makers / Nintendo 64 / Bosses / asset `{d['source']['asset_id']}`",
        f"- source URL: {d['source']['url']}",
        f"- inherited source PNG: {d['source']['whole_sheet']['bytes']} bytes; {d['source']['whole_sheet']['width']}x{d['source']['whole_sheet']['height']}; SHA-256 `{d['source']['whole_sheet']['sha256']}`; Animations(0)",
        "- rights: commercial sprite art is evidence only; no source pixels/palette/contours/layout/tracing/choreography/redistribution/close imitation enter output.",
        f"- decisive keys: {len(d['keys'])}; every key timing is `INFERRED / STREET_FIGHTER-CAPCOM` because source-authentic timing is unavailable.",
        f"- media: H.264 {manifest['media_decode_preflight']['width']}x{manifest['media_decode_preflight']['height']} @ {manifest['media_decode_preflight']['fps']}; {manifest['media_decode_preflight']['frames']} frames; {manifest['media_bytes']} bytes; SHA-256 `{manifest['media_sha256']}`.",
        f"- ASCII sheet SHA-256: `{manifest['ascii_sheet_sha256']}`.",
        f"- Tango: `{d['quality_gates']['tango']['status']}`.",
        f"- Noodle Queen: `{d['quality_gates']['noodle_queen']['status']}`.",
        f"- contract: `{d['validation']['contract_test']['status']}` — {d['validation']['contract_test'].get('boundary','pending')}.",
        "- repo readback: REQUIRED after persistence; this receipt does not pre-claim it.",
        "- chat delivery: REQUIRED after exact persisted readback in ordered PART 1 ASCII -> PART 2 JSON -> PART 3 VIDEO.",
        "",
        "Correction hooks: KEEP / REJECT / EXAGGERATE / COMPRESS / RETIME / CHANGE SOURCE / PROMOTE / SPAWN VARIANT / FIX BLOCKER / RERUN."
    ]
    return "\n".join(lines)+"\n"

def main():
    d=json.loads(MOTION.read_text())
    sheet=contact_sheet(d)
    seq=compile_video(d)
    media=MP4.read_bytes()
    dec=probe(MP4)
    if dec["frames"] != len(seq):
        raise SystemExit(f"frame mismatch: encoded={dec['frames']} expected={len(seq)}")
    manifest=make_manifest(d,sheet,media,dec)
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    HTML.write_text(make_spa(d,sheet,media,manifest))
    RECEIPT.write_text(make_receipt(d,manifest))
    print(json.dumps({
        "experiment_id":d["experiment_id"],
        "keys":len(d["keys"]),"frames":len(seq),
        "media_sha256":manifest["media_sha256"],
        "media_bytes":manifest["media_bytes"],
        "ascii_sheet_sha256":manifest["ascii_sheet_sha256"],
        "receipt_status":manifest["receipt_status"]
    },sort_keys=True))

if __name__=="__main__":
    main()
