#!/usr/bin/env python3
from pathlib import Path
import base64, hashlib, html, json, subprocess, tempfile
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parent
MOTION=ROOT/"motion.json"
SHEET=ROOT/"contact-sheet.txt"
SPA=ROOT/"scoped-sync-grapple-root-com-transfer-repair.motion.html"
LOCAL_MP4=ROOT/".motion.mp4"
GRID_W,GRID_H=80,24

SEG={
 "A":[((0,1),(0.5,0)),((0.5,0),(1,1)),((.22,.58),(.78,.58))],
 "B":[((0,0),(0,1)),((0,0),(.65,0)),((.65,0),(1,.25)),((1,.25),(.65,.5)),((0,.5),(.65,.5)),((.65,.5),(1,.75)),((1,.75),(.65,1)),((.65,1),(0,1))],
 "a":[((.2,.45),(.5,.2)),((.5,.2),(.8,.45)),((.8,.45),(.5,.72)),((.5,.72),(.2,.45))],
 "b":[((.15,0),(.15,1)),((.15,.45),(.65,.3)),((.65,.3),(.9,.55)),((.9,.55),(.65,.82)),((.65,.82),(.15,.7))],
 "L":[((.1,0),(.1,1)),((.1,1),(.9,1))],
 "R":[((.1,0),(.1,1)),((.1,0),(.7,0)),((.7,0),(.9,.25)),((.9,.25),(.7,.5)),((.7,.5),(.1,.5)),((.5,.5),(.95,1))]
}

def glyph(d,c,x,y,cw,ch):
    p=lambda u,v:(x+2+u*(cw-4),y+2+v*(ch-4))
    col=(245,245,245); w=2
    if c==" ": return
    if c=="_": d.line((*p(0,1),*p(1,1)),fill=col,width=w)
    elif c=="-": d.line((*p(0,.5),*p(1,.5)),fill=col,width=w)
    elif c=="|": d.line((*p(.5,0),*p(.5,1)),fill=col,width=w)
    elif c=="/": d.line((*p(0,1),*p(1,0)),fill=col,width=w)
    elif c=="\\": d.line((*p(0,0),*p(1,1)),fill=col,width=w)
    elif c==":":
        d.ellipse((x+cw//2-1,y+ch//3-1,x+cw//2+1,y+ch//3+1),fill=col)
        d.ellipse((x+cw//2-1,y+2*ch//3-1,x+cw//2+1,y+2*ch//3+1),fill=col)
    elif c==".":
        d.ellipse((x+cw//2-1,y+ch-4,x+cw//2+1,y+ch-2),fill=col)
    elif c=="+":
        d.line((*p(0,.5),*p(1,.5)),fill=col,width=w); d.line((*p(.5,0),*p(.5,1)),fill=col,width=w)
    elif c in "*X":
        d.line((*p(0,0),*p(1,1)),fill=col,width=w); d.line((*p(0,1),*p(1,0)),fill=col,width=w)
        if c=="*": d.line((*p(.5,0),*p(.5,1)),fill=col,width=1)
    elif c=="^":
        d.line((*p(0,1),*p(.5,0)),fill=col,width=w); d.line((*p(.5,0),*p(1,1)),fill=col,width=w)
    elif c==">":
        d.line((*p(0,0),*p(1,.5)),fill=col,width=w); d.line((*p(1,.5),*p(0,1)),fill=col,width=w)
    elif c=="<":
        d.line((*p(1,0),*p(0,.5)),fill=col,width=w); d.line((*p(0,.5),*p(1,1)),fill=col,width=w)
    elif c=="v":
        d.line((*p(0,0),*p(.5,1)),fill=col,width=w); d.line((*p(.5,1),*p(1,0)),fill=col,width=w)
    elif c in SEG:
        for aa,bb in SEG[c]: d.line((*p(*aa),*p(*bb)),fill=col,width=w)

def raster(text,width,height):
    im=Image.new("RGB",(width,height),(7,7,7)); d=ImageDraw.Draw(im)
    cw=width//GRID_W; ch=height//GRID_H
    for r,line in enumerate(text.splitlines()[:GRID_H]):
        for col,c in enumerate(line[:GRID_W]): glyph(d,c,col*cw,r*ch,cw,ch)
    return im

def make_sheet(m):
    s=m["source"]; r=m["revision"]
    out=[
        m["experiment_id"],
        m["primitive"],
        f"RESET: issue #343 comment {m['reset_issue_comment']}",
        f"CHRONOLOGY: {m['chronology_bind_issue_comment']} | SUCCESSOR_CHURN_REBIND: {m['successor_churn_rebind_issue_comment']}",
        f"REVISION: revises={r['revises']} | negative_fixture={r['negative_fixture']} | source_change=false",
        f"QUARANTINED LATER CHURN: {r['later_churn_quarantined']}",
        f"SOURCE: TSR asset {s['asset_id']} | {s['name']} | {s['game']} | {s['platform']}",
        f"SOURCE EVIDENCE: Home Center {s['evidence_document_id']} | raw_sha256={s['raw_sha256']}",
        "SOURCE TIMING: UNKNOWN | timing_authority=false | roles=POSE_REFERENCE + CONTACT_TOPOLOGY_REFERENCE",
        "RIGHTS: evidence only; no source pixels/palette/costume/exact silhouette/choreography/tracing/redistribution.",
        "ASCII LEGEND: A/B=heads, a/b=pelvis roots, +=joint, L/R=feet, ^=trusted/braking support, .=light/released support, *=anchor, X=relationship center, :=force/arc.",
        f"AUTHORED CAUSAL SENTENCE: {m['direction']['sentence']}",
        "TIMING: every hold_frames value is authored/inferred; no source-authentic duration is claimed.",
        ""
    ]
    for k in m["keys"]:
        out += [
            "="*80,
            f"{k['key_id']} {k['name']} | {k['timing_class']} | hold_frames={k['hold_frames']} | timing={k['timing_provenance']}",
            f"CONTACT={k['contact_state']} | CUSTODY={k['custody']} | ROOT_OWNER={k['root_owner']}",
            f"SUPPORT_A={k['support_A']} | SUPPORT_B={k['support_B']}",
            f"ROLE: {k['causal_role']}",
            f"ARC: {k['motion_arc_root_note']}",
            k["ascii"],
            ""
        ]
    return "\n".join(out).rstrip()+"\n"

def build_video(m,tmp):
    cfg=m["compile"]; fd=tmp/"frames"; fd.mkdir()
    i=0
    for k in m["keys"]:
        im=raster(k["ascii"],cfg["width"],cfg["height"])
        for _ in range(int(k["hold_frames"])):
            im.save(fd/f"{i:04d}.png")
            i+=1
    out=tmp/"motion.mp4"
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-framerate",str(cfg["fps"]),
        "-i",str(fd/"%04d.png"),"-c:v","libx264","-preset","veryslow","-crf","30",
        "-pix_fmt","yuv420p","-movflags","+faststart","-metadata","encoder=ascii-kinesis-v2",str(out)
    ],check=True)
    return i,out

def make_spa(motion_text,sheet,video_bytes,experiment_id):
    import gzip
    enc=lambda s: base64.b64encode(gzip.compress(s.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    ascii_payload=enc(sheet); json_payload=enc(motion_text); video=base64.b64encode(video_bytes).decode("ascii")
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(experiment_id)}</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#090909;color:#eee;font-family:system-ui}}
nav{{position:sticky;top:0;z-index:2;background:#111;padding:10px;display:flex;gap:8px;border-bottom:1px solid #333}}
button{{padding:8px 14px;background:#1b1b1b;color:#eee;border:1px solid #555;border-radius:5px}}
section{{display:none;padding:12px}} section.active{{display:block}}
pre{{white-space:pre;overflow:auto;font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;line-height:1.12}}
video{{display:block;width:min(100%,800px);height:auto;background:#000}}
</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre id="ascii-pre"></pre></section>
<section id="json"><pre id="json-pre"></pre></section>
<section id="video"><video controls autoplay muted loop playsinline src="data:video/mp4;base64,{video}"></video></section>
<script>
const A="{ascii_payload}",J="{json_payload}";
async function inflate64(s){{const u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new TextDecoder().decode(await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer())}}
(async()=>{{document.getElementById("ascii-pre").textContent=await inflate64(A);document.getElementById("json-pre").textContent=await inflate64(J)}})();
for(const b of document.querySelectorAll("button[data-view]")) b.onclick=()=>{{
 for(const s of document.querySelectorAll("section")) s.classList.toggle("active",s.id===b.dataset.view);
}};
</script></body></html>
"""

def sha256(b): return hashlib.sha256(b).hexdigest()

def main():
    m=json.loads(MOTION.read_text())
    motion_text=json.dumps(m,indent=2,sort_keys=True)+"\n"
    if MOTION.read_text()!=motion_text:
        raise SystemExit("motion.json is not canonical pretty JSON")
    sheet=make_sheet(m)
    with tempfile.TemporaryDirectory() as td:
        count,mp4=build_video(m,Path(td)); raw=mp4.read_bytes()
    expected=m["compile"]
    if count!=expected["frames_total"]: raise SystemExit(f"frame count {count} != {expected['frames_total']}")
    if sha256(raw)!=expected["media_sha256"]: raise SystemExit("media SHA mismatch")
    if len(raw)!=expected["media_bytes"]: raise SystemExit("media byte count mismatch")
    SHEET.write_text(sheet)
    LOCAL_MP4.write_bytes(raw)
    SPA.write_text(make_spa(motion_text,sheet,raw,m["experiment_id"]))
    print(json.dumps({
        "frames":count,
        "media_bytes":len(raw),
        "media_sha256":sha256(raw),
        "motion_sha256":sha256(motion_text.encode()),
        "contact_sheet_sha256":sha256(sheet.encode()),
        "spa_sha256":sha256(SPA.read_bytes())
    },sort_keys=True))

if __name__=="__main__": main()
