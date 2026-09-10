#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/"motion.json"
CONTACT=HERE/"contact-sheet.txt"
SPA=HERE/"flexible-link-impact-tension-return-debt.motion.html"
TMP_MP4=HERE/".strikes020-render.mp4"
FRAME_DIR=HERE/".strikes020-frames"
W,H=72,22
TIMING={"ONES":1,"TWOS":2,"FOURS":4}

def line_chars(g,p0,p1,ch="-",overwrite=False):
    x0,y0=[int(round(v)) for v in p0]; x1,y1=[int(round(v)) for v in p1]
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy; x,y=x0,y0
    while True:
        if 0<=x<W and 0<=y<H and (overwrite or g[y][x]==" "): g[y][x]=ch
        if x==x1 and y==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x+=sx
        if e2<=dx: err+=dx; y+=sy

def put(g,p,ch):
    x,y=[int(round(v)) for v in p]
    if 0<=x<W and 0<=y<H: g[y][x]=ch

def ascii_pose(key,rig=None,semantic=None):
    r=rig or key["rig"]; sem=semantic or key
    g=[[" "]*W for _ in range(H)]
    for x in range(8,63): g[20][x]="_"
    # Target is an authored synthetic contact plane, not source art.
    for y in range(5,16): g[y][59]="|"
    g[4][59]="#"; g[16][59]="#"

    mid=((r["left_shoulder"][0]+r["right_shoulder"][0])/2,
         (r["left_shoulder"][1]+r["right_shoulder"][1])/2)
    line_chars(g,mid,r["pelvis"],"|")
    line_chars(g,r["left_shoulder"],r["left_hand"],"/")
    line_chars(g,r["right_shoulder"],r["right_hand"],"\\")
    line_chars(g,r["pelvis"],r["left_foot"],"/")
    line_chars(g,r["pelvis"],r["right_foot"],"\\")
    line_chars(g,r["left_shoulder"],r["right_shoulder"],"-")
    # Flexible link is three segments so authored curvature can carry the acting.
    line_chars(g,r["handle"],r["tether_mid1"],"~")
    line_chars(g,r["tether_mid1"],r["tether_mid2"],"~")
    line_chars(g,r["tether_mid2"],r["distal"],"~")
    put(g,r["head"],"O"); put(g,r["pelvis"],"^")
    for p in ("left_hand","right_hand","left_shoulder","right_shoulder"): put(g,r[p],"o")
    put(g,r["left_foot"],"/"); put(g,r["right_foot"],"\\")
    put(g,r["handle"],"]"); put(g,r["distal"],"@")
    if sem.get("contact_event"):
        x,y=[int(round(v)) for v in r["distal"]]
        if x+1<W: g[y][x+1]="X"
        for ox,oy,ch in [(-2,-1,"<"),(-3,-2,"<"),(-4,-3,"^")]:
            xx=x+ox; yy=y+oy
            if 0<=xx<W and 0<=yy<H and g[yy][xx]==" ": g[yy][xx]=ch
    elif sem.get("force_vector"):
        x,y=[int(round(v)) for v in r["handle"]]
        for ox,oy,ch in [(-2,-1,"<"),(-3,-2,"^")]:
            xx=x+ox; yy=y+oy
            if 0<=xx<W and 0<=yy<H and g[yy][xx]==" ": g[yy][xx]=ch
    return "\n".join("".join(row).rstrip() for row in g).rstrip()

def build_contact(motion):
    blocks=[]
    for k in motion["keys"]:
        blocks.append(
          f"{k['key_id']} {k['name']} | {k['timing_class']} | {k['timing_provenance']} | support={k['support_contact']} | tether={k['tether_state']}\n"
          f"role={k['causal_role']}\n"
          f"{ascii_pose(k)}\n"
          f"root_note={k['motion_arc_root_note']}\n"
        )
    return (
      f"ASCII KINESIS V2 STRIKES020 — {motion['principle']}\n"
      "Legend: O head | ^ pelvis/root | o joint/hand | ] handle | ~ flexible link | @ distal mass | X authored contact | | target plane | _ ground\n"
      "Source art is evidence-only and is not reproduced. All Strikes020 pose/timing/tether/contact mechanics are INFERRED / STREET_FIGHTER-CAPCOM.\n"
      "Pocket: THE DISTAL HIT LANDS FIRST; THE BODY RECEIVES THE BILL THROUGH THE TETHER ONE BEAT LATER.\n\n"
      + "\n".join(blocks)
    )

def interp_rig(a,b,t):
    return {n:[pa[0]+(b[n][0]-pa[0])*t,pa[1]+(b[n][1]-pa[1])*t] for n,pa in a.items()}

def font(sz):
    for name in ("DejaVuSansMono.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        try: return ImageFont.truetype(name,sz)
        except Exception: pass
    return ImageFont.load_default()

def render_frame(text,out_path):
    img=Image.new("RGB",(480,270),(12,12,14))
    d=ImageDraw.Draw(img); f=font(10)
    y=20
    for line in text.splitlines():
        d.text((38,y),line,font=f,fill=(238,238,238))
        y+=10
    img.save(out_path,compress_level=9)

def compile_frames(motion):
    frames=[]; keys=motion["keys"]
    for i,k in enumerate(keys):
        for _ in range(TIMING[k["timing_class"]]):
            frames.append((k["rig"],k))
        if i+1<len(keys):
            nk=keys[i+1]; n=int(k.get("transition_frames_to_next",0))
            for step in range(1,n+1):
                t=step/(n+1)
                # Geometry connects deterministically. Semantic contact/support/tether labels remain source-key owned.
                frames.append((interp_rig(k["rig"],nk["rig"],t),k))
    return frames

def render_mp4(motion):
    if FRAME_DIR.exists(): shutil.rmtree(FRAME_DIR)
    FRAME_DIR.mkdir()
    frames=compile_frames(motion)
    for i,(rig,sem) in enumerate(frames):
        render_frame(ascii_pose(sem,rig=rig,semantic=sem),FRAME_DIR/f"f{i:04d}.png")
    cmd=[
      "ffmpeg","-loglevel","error","-y","-framerate","24","-i",str(FRAME_DIR/"f%04d.png"),
      "-an","-c:v","libx264","-pix_fmt","yuv420p","-profile:v","high","-level","4.0",
      "-preset","veryslow","-crf","29","-g","120","-bf","2",
      "-x264-params","scenecut=0:open_gop=0:nal-hrd=none",
      "-map_metadata","-1","-fflags","+bitexact","-flags:v","+bitexact",
      "-movflags","+faststart",str(TMP_MP4)
    ]
    subprocess.run(cmd,check=True)
    shutil.rmtree(FRAME_DIR)
    return frames

def make_spa(motion,contact,media):
    media64=base64.b64encode(media).decode("ascii")
    ascii64=base64.b64encode(gzip.compress(contact.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    json_text=json.dumps(motion,separators=(",",":"),ensure_ascii=True)
    json64=base64.b64encode(gzip.compress(json_text.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    css="""body{margin:0;background:#0d0d0f;color:#eee;font-family:ui-monospace,Consolas,monospace}nav{position:sticky;top:0;background:#17171b;padding:12px;border-bottom:1px solid #444}button{font:inherit;margin-right:8px;padding:8px 14px;background:#222;color:#eee;border:1px solid #666}section{display:none;padding:18px}section.active{display:block}pre{font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.12}video{display:block;max-width:100%;margin:auto;background:#000}"""
    return f"""<!doctype html><html><head><meta charset="utf-8"><title>ASCII Kinesis V2 Strikes020</title><style>{css}</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre id="ascii-pre"></pre></section>
<section id="json"><pre id="json-pre"></pre></section>
<section id="video"><video controls playsinline src="data:video/mp4;base64,{media64}"></video></section>
<script>
const bs=[...document.querySelectorAll('button[data-view]')],ss=[...document.querySelectorAll('section')];
bs.forEach(b=>b.onclick=()=>ss.forEach(s=>s.classList.toggle('active',s.id===b.dataset.view)));
async function ungzip(b64,id){{const a=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));const st=new Blob([a]).stream().pipeThrough(new DecompressionStream('gzip'));document.getElementById(id).textContent=await new Response(st).text();}}
ungzip('{ascii64}','ascii-pre');ungzip('{json64}','json-pre');
</script></body></html>"""

def main():
    motion=json.loads(MOTION.read_text(encoding="utf-8"))
    contact=build_contact(motion)
    CONTACT.write_text(contact,encoding="utf-8")
    frames=render_mp4(motion)
    media=TMP_MP4.read_bytes()
    sha=hashlib.sha256(media).hexdigest()
    motion["compile"].update({"frame_count":len(frames),"media_sha256":sha,"media_bytes":len(media),"width":480,"height":270})
    MOTION.write_text(json.dumps(motion,separators=(",",":"),ensure_ascii=True),encoding="utf-8")
    SPA.write_text(make_spa(motion,contact,media),encoding="utf-8")
    print(json.dumps({"media_sha256":sha,"media_bytes":len(media),"frames":len(frames),"spa_bytes":SPA.stat().st_size},sort_keys=True))

if __name__=="__main__":
    main()
