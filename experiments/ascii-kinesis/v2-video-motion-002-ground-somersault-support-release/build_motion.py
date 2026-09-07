#!/usr/bin/env python3
"""Deterministic Motion Dungeon builder for ASCII Kinesis V2 Video Motion 002.

Input authority: motion.json only. Source footage is never opened by this builder.
It renders an abstract ASCII rig, compiles that rig to H.264 MP4, and emits an
offline SPA whose only primary views are ASCII | JSON | VIDEO.
"""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOTION_PATH = ROOT / "motion.json"
CONTACT_PATH = ROOT / "contact_sheet.txt"
MP4_PATH = ROOT / "motion.mp4"
HTML_PATH = ROOT / "ground-somersault-support-release.motion.html"
MANIFEST_PATH = ROOT / "manifest.json"
RECEIPT_PATH = ROOT / "receipt.json"

FONT = {
    " ": ["00000"] * 7,
    "O": ["01110","10001","10001","10001","10001","10001","01110"],
    "@": ["01110","10001","10111","10101","10111","10000","01111"],
    "|": ["00100","00100","00100","00100","00100","00100","00100"],
    "/": ["00001","00010","00010","00100","01000","01000","10000"],
    "\\": ["10000","01000","01000","00100","00010","00010","00001"],
    "-": ["00000","00000","00000","11111","00000","00000","00000"],
    "_": ["00000","00000","00000","00000","00000","00000","11111"],
    "?": ["01110","10001","00010","00100","00100","00000","00100"],
    "*": ["00100","10101","01110","11111","01110","10101","00100"],
    "X": ["10001","01010","00100","00100","00100","01010","10001"],
}

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def put(grid: list[list[str]], x: int, y: int, ch: str) -> None:
    if not (0 <= y < len(grid) and 0 <= x < len(grid[0])):
        return
    old = grid[y][x]
    if old == " " or ch == old or ch == "_":
        grid[y][x] = ch
    elif old == "_" and ch != "_":
        grid[y][x] = ch
    else:
        grid[y][x] = "X"

def line(grid: list[list[str]], a: tuple[int,int], b: tuple[int,int]) -> None:
    x0, y0 = a; x1, y1 = b
    dx, dy = x1-x0, y1-y0
    steps = max(abs(dx), abs(dy), 1)
    for i in range(steps + 1):
        t = i / steps
        x = round(x0 + dx*t); y = round(y0 + dy*t)
        if abs(dx) >= abs(dy)*2:
            ch = "-"
        elif dx*dy < 0:
            ch = "/"
        elif dx == 0:
            ch = "|"
        else:
            ch = "\\"
        put(grid, x, y, ch)

def interp(a: list[int], b: list[int], t: float) -> tuple[int,int]:
    return (round(a[0] + (b[0]-a[0])*t), round(a[1] + (b[1]-a[1])*t))

def geometry(key: dict, nxt: dict | None, t: float) -> dict[str, tuple[int,int]]:
    if nxt is None:
        nxt = key; t = 0.0
    return {name: interp(key["joints"][name], nxt["joints"][name], t) for name in key["joints"]}

def render_grid(motion: dict, key: dict, nxt: dict | None = None, t: float = 0.0) -> list[str]:
    cols, rows = motion["motion_dungeon"]["render_grid"]
    ground_y = int(motion["motion_dungeon"]["ground_y"])
    g = [[" " for _ in range(cols)] for _ in range(rows)]
    for x in range(cols): put(g, x, ground_y, "_")
    p = geometry(key, nxt, t)
    head, root = p["head"], p["root"]
    shoulder = ((head[0]+root[0])//2, (head[1]+root[1])//2)
    line(g, head, root)
    line(g, shoulder, p["left_hand"]); line(g, shoulder, p["right_hand"])
    line(g, root, p["left_foot"]); line(g, root, p["right_foot"])
    put(g, head[0], head[1], "O"); put(g, root[0], root[1], "@")
    support = key.get("support_state", "")
    if support.startswith("GROUND_CONTACT_VISIBLE"):
        for foot in (p["left_foot"], p["right_foot"]):
            if foot[1] >= ground_y-1: put(g, foot[0], ground_y+1, "?")
    elif support == "SUPPORT_TRANSITION_UNRESOLVED":
        put(g, root[0], min(rows-1, ground_y+1), "?")
    return ["".join(row) for row in g]

def build_contact_sheet(motion: dict) -> str:
    out = [
        "ASCII KINESIS V2 · VIDEO MOTION 002 · GROUND SOMERSAULT SUPPORT RELEASE",
        "Source: Ground flip (1080p 120fps - take 02).webm · selected action 0.500–3.750 s presentation time",
        "Rights: PoseidonSports · CC BY-SA 4.0 · analysis only; NO SOURCE PIXELS IN THIS OUTPUT",
        "Legend: O=head  @=root/pelvis proxy  /\\-|=segments  _=ground  ?=support/contact side unresolved  X=line overlap",
        "Timing: source timestamps OBSERVED; compile cadence INFERRED FOURS/TWOS/ONES because source presentation is slow motion.",
        ""
    ]
    for k in motion["keys"]:
        out.append(f"{k['key_id']} · {k['source_time_s']:.3f} s source presentation · OBSERVED · {k['causal_role']} · compile {k['compile_timing_class']} (INFERRED)")
        out.extend(render_grid(motion, k))
        out.append(f"support: {k['support_state']}")
        out.append(f"contact: {k['contact_note']}")
        out.append(f"root/force: {k['root_arc_note']}")
        out.append("")
    out.extend([
        "CAUSAL BRACKETS",
        "toe-off: exact transition unresolved between grounded K2 (2.500) and clearly airborne K4 (3.000); K3 is a fail-closed transition key.",
        "landing: first strike unresolved between airborne-descending K6 (3.500) and returned ground support K7 (3.750); no landing side invented.",
        "real-time cadence: UNKNOWN; 120 fps transport/presentation is not promoted to athletic timing.",
    ])
    return "\n".join(out) + "\n"

def bitmap_rgb(lines: list[str], cell_w: int, cell_h: int, scale: int) -> bytes:
    rows, cols = len(lines), len(lines[0])
    width, height = cols*cell_w*scale, rows*cell_h*scale
    out = bytearray(b"\x08" * (width*height*3))
    for gy, row in enumerate(lines):
        for gx, ch in enumerate(row):
            pat = FONT.get(ch)
            if not pat: continue
            for py, bits in enumerate(pat):
                for px, bit in enumerate(bits):
                    if bit != "1": continue
                    ox=(gx*cell_w+px)*scale; oy=(gy*cell_h+py)*scale
                    for sy in range(scale):
                        for sx in range(scale):
                            x=ox+sx; y=oy+sy
                            if x>=width or y>=height: continue
                            pos=(y*width+x)*3
                            out[pos:pos+3]=b"\xf2\xf2\xf2"
    return bytes(out)

def compile_frames(motion: dict) -> list[bytes]:
    keys = motion["keys"]
    specs: list[tuple[dict,dict|None,float]] = []
    for i, key in enumerate(keys[:-1]):
        nxt = keys[i+1]
        span = max(1, int(nxt["compile_frame"]) - int(key["compile_frame"]))
        hold = max(1, min(int(key["compile_hold_frames"]), span))
        if key.get("causal_boundary_to_next"):
            hold = span
        specs.extend((key,nxt,0.0) for _ in range(hold))
        remaining = span-hold
        for j in range(remaining):
            t=(j+1)/(remaining+1)
            specs.append((key,nxt,t))
    final = keys[-1]
    specs.extend((final,None,0.0) for _ in range(int(motion["motion_dungeon"]["final_hold_frames"])))
    cw,ch = motion["motion_dungeon"]["cell_pixels"]
    scale=int(motion["motion_dungeon"]["scale"])
    return [bitmap_rgb(render_grid(motion,k,n,t),cw,ch,scale) for k,n,t in specs]

def compile_mp4(motion: dict, frames: list[bytes]) -> tuple[bytes,str]:
    cols,rows=motion["motion_dungeon"]["render_grid"]
    cw,ch=motion["motion_dungeon"]["cell_pixels"]
    scale=int(motion["motion_dungeon"]["scale"])
    w,h=cols*cw*scale,rows*ch*scale
    fps=int(motion["timing"]["compile_fps"])
    cmd=["ffmpeg","-hide_banner","-loglevel","error","-y","-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{w}x{h}","-r",str(fps),"-i","-","-an","-c:v","libx264","-preset","medium","-crf","20","-threads","1","-pix_fmt","yuv420p","-movflags","+faststart","-map_metadata","-1","-metadata","creation_time=1970-01-01T00:00:00Z",str(MP4_PATH)]
    p=subprocess.run(cmd,input=b"".join(frames),stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
    if p.returncode: raise SystemExit(p.stderr.decode("utf-8","replace"))
    data=MP4_PATH.read_bytes()
    version=subprocess.check_output(["ffmpeg","-version"],text=True).splitlines()[0]
    return data,version

def esc(s: str) -> str:
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def build_html(motion: dict, manifest: dict, contact: str, mp4: bytes) -> str:
    audit=json.dumps({"motion":motion,"manifest":manifest},indent=2,ensure_ascii=False)
    b64=base64.b64encode(mp4).decode("ascii")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 · Video Motion 002</title><style>:root{{color-scheme:dark;background:#0a0a0a;color:#f2f2f2;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}}*{{box-sizing:border-box}}body{{margin:0;min-height:100vh;background:#0a0a0a;color:#f2f2f2}}header{{position:sticky;top:0;background:#111;border-bottom:1px solid #444;padding:.75rem;z-index:2}}nav{{display:flex;gap:.5rem}}button{{font:inherit;padding:.6rem .9rem;background:#1c1c1c;color:#eee;border:1px solid #555;border-radius:.35rem;cursor:pointer}}button[aria-selected="true"]{{background:#eee;color:#111}}main{{padding:1rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;tab-size:2;overflow:auto;line-height:1.15;margin:0;padding:1rem;border:1px solid #333;background:#0d0d0d;max-width:100%}}video{{display:block;width:min(100%,960px);height:auto;border:1px solid #333;background:#000}}.small{{max-width:72rem;margin:0 0 1rem;line-height:1.5}}</style></head><body><header><nav aria-label="Primary views"><button type="button" data-view="ascii" aria-selected="true">ASCII</button><button type="button" data-view="json" aria-selected="false">JSON</button><button type="button" data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section id="view-ascii"><p class="small">Literal selectable/copyable ASCII contact sheet. No source pixels are present.</p><pre id="ascii-sheet">{esc(contact)}</pre></section><section id="view-json" hidden><p class="small">Structured rig, keys, timing provenance, rights, compatibility, manifest, and exact media identity.</p><pre id="json-audit">{esc(audit)}</pre></section><section id="view-video" hidden><p class="small">Motion Dungeon MP4 generated solely from the abstract ASCII rig and authored compile timing.</p><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{b64}"></video></section></main><script>const buttons=[...document.querySelectorAll('nav button')];const sections={{ascii:document.getElementById('view-ascii'),json:document.getElementById('view-json'),video:document.getElementById('view-video')}};for(const b of buttons){{b.addEventListener('click',()=>{{for(const x of buttons)x.setAttribute('aria-selected',String(x===b));for(const [name,s] of Object.entries(sections))s.hidden=name!==b.dataset.view;}})}}</script></body></html>'''

def main() -> None:
    motion=json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    contact=build_contact_sheet(motion)
    CONTACT_PATH.write_text(contact,encoding="utf-8")
    frames=compile_frames(motion)
    mp4,ffver=compile_mp4(motion,frames)
    media_hash=sha256_bytes(mp4)
    motion["media"].update({"sha256":media_hash,"bytes":len(mp4),"frame_count":len(frames),"compile_fps":int(motion["timing"]["compile_fps"]),"ffmpeg_version":ffver})
    motion["status"]="RENDERED_PENDING_REPO_READBACK"
    MOTION_PATH.write_text(json.dumps(motion,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    manifest={
        "schema":"ascii-kinesis.v2-manifest","format_version":2,"entry":motion["experiment_id"],"lane":"video-motion","primary_tabs":["ASCII","JSON","VIDEO"],
        "ascii_literal_text":True,"video_required":True,"video_source":"abstract_ascii_rig_only","source_art_embedded":False,"backward_compatible":True,"offline_spa":True,
        "source":{"title":motion["source"]["title"],"url":motion["source"]["page_url"],"author":motion["source"]["author"],"rights_status":motion["source"]["rights_status"],"license_id":motion["source"]["license_id"],"source_sha256":motion["source"]["source_sha256"],"selected_action_segment_s":motion["source"]["selected_action_segment_s"],"whole_action_inspection":motion["source"]["whole_action_inspection"]},
        "media":{"mime":"video/mp4","sha256":media_hash,"bytes":len(mp4),"frame_count":len(frames),"compile_fps":motion["timing"]["compile_fps"],"embedded_in_spa":True,"tracked_mp4":"motion.mp4","embedded_matches_tracked_mp4":True,"source_pixels_used":False,"render_dimensions":[motion["motion_dungeon"]["render_grid"][0]*motion["motion_dungeon"]["cell_pixels"][0]*motion["motion_dungeon"]["scale"],motion["motion_dungeon"]["render_grid"][1]*motion["motion_dungeon"]["cell_pixels"][1]*motion["motion_dungeon"]["scale"]]},
        "builder":{"path":"build_motion.py","method":"Motion Dungeon","input":"motion.json only; contact sheet, MP4, manifest, receipt, SPA are deterministic outputs","source_video_dependency":False,"ffmpeg_version":ffver},
        "files":["contact_sheet.txt","motion.json","motion.mp4","build_motion.py","manifest.json","receipt.json","ground-somersault-support-release.motion.html"],
        "compatibility":{"v1_untouched":True,"v2_three_tab_read_path":True,"network_required":False},
        "correction_hooks":motion["correction_hooks"],"status":"RENDERED_PENDING_REPO_READBACK"
    }
    MANIFEST_PATH.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    HTML_PATH.write_text(build_html(motion,manifest,contact,mp4),encoding="utf-8")
    receipt={
        "schema":"ascii-kinesis.v2-receipt","entry":motion["experiment_id"],"source":motion["source"],"rights_status":motion["source"]["rights_status"],
        "observed_key_times_s":{k["key_id"]:k["source_time_s"] for k in motion["keys"]},
        "observed_summary":motion["evidence_boundary"]["observed"],"inferred":motion["evidence_boundary"]["inferred"],"unknown":motion["evidence_boundary"]["unknown"],
        "compile_timing_classes":{k["key_id"]:k["compile_timing_class"] for k in motion["keys"]},"media_sha256":media_hash,"media_bytes":len(mp4),"media_frame_count":len(frames),"media_source":"abstract_ascii_rig_only",
        "repo_path":f"experiments/ascii-kinesis/{motion['experiment_id']}/","repo_readback_verified":False,"contract_test_exact_readback":False,
        "status":"RENDERED_PENDING_REPO_READBACK","correction_hooks":motion["correction_hooks"],
        "verification_assertion":"Do not promote VERIFIED until exact GitHub readback, contract/media validation, and issue #343 receipt complete."
    }
    RECEIPT_PATH.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps({"entry":motion["experiment_id"],"frames":len(frames),"mp4_bytes":len(mp4),"mp4_sha256":media_hash,"html_bytes":HTML_PATH.stat().st_size,"ffmpeg":ffver},sort_keys=True))

if __name__=="__main__": main()
