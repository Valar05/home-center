#!/usr/bin/env python3
from pathlib import Path
import base64, hashlib, html, json, math, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MOTION_PATH = ROOT / "motion.json"
ASCII_PATH = ROOT / "contact-sheet.txt"
SPA_PATH = ROOT / "latent-eligibility-force-transfer-repair.motion.html"
TMP = ROOT / ".motion-build"
FRAMES = TMP / "frames"
MP4 = TMP / "motion.mp4"

W, H = 72, 22
GROUND_Y = 17
IMG_W, IMG_H = 768, 400
FPS = 24
TIMING_FRAMES = {"ONES": 1, "TWOS": 2, "FOURS": 4}

def _line_cells(p0, p1):
    x0,y0 = map(int,p0); x1,y1 = map(int,p1)
    dx=abs(x1-x0); dy=-abs(y1-y0)
    sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1
    err=dx+dy; pts=[]
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return pts

def _seg_char(p0,p1):
    dx=p1[0]-p0[0]; dy=p1[1]-p0[1]
    if abs(dx)>abs(dy)*1.7: return "-"
    if abs(dy)>abs(dx)*1.7: return "|"
    return "\\" if dx*dy>0 else "/"

def _render_ascii(state):
    grid=[[" "]*W for _ in range(H)]
    for x in range(W): grid[GROUND_Y][x]="_"
    def actor(joints, headc):
        segs=[("head","shoulder"),("shoulder","pelvis"),("shoulder","hand_f"),("shoulder","hand_b"),
              ("pelvis","foot_f"),("pelvis","foot_b")]
        for a,b in segs:
            p0,p1=joints[a],joints[b]; ch=_seg_char(p0,p1)
            for x,y in _line_cells(p0,p1):
                if 0<=x<W and 0<=y<H and grid[y][x]==" ": grid[y][x]=ch
        for name,ch in [("head",headc),("shoulder","O"),("pelvis","X"),("hand_f","*"),("hand_b","*"),("foot_f","^"),("foot_b","^")]:
            x,y=joints[name]; x=int(round(x)); y=int(round(y))
            if 0<=x<W and 0<=y<H: grid[y][x]=ch
    actor(state["A"],"A"); actor(state["B"],"B")
    if state["contact"] not in ("NONE","RELEASED"):
        ax,ay=state["A"]["hand_f"]; bx,by=state["B"]["hand_f"]
        x=int(round((ax+bx)/2)); y=int(round((ay+by)/2))
        if 0<=x<W and 0<=y<H: grid[y][x]="@"
    return "\n".join("".join(r).rstrip() for r in grid)

def _interp_actor(a0,a1,t,curve):
    out={}
    for name in a0:
        x0,y0=a0[name]; x1,y1=a1[name]
        s=t*t*(3-2*t)
        x=x0+(x1-x0)*s; y=y0+(y1-y0)*s
        if name in ("head","hand_f","hand_b"):
            y += curve*math.sin(math.pi*t)
        out[name]=[x,y]
    return out

def _same_semantics(k0,k1):
    return all(k0[f]==k1[f] for f in ("contact","custody","support_contact"))

def _sequence(motion):
    raw=[]
    for q in motion["keys"]:
        k={
            "id":q["key_id"], "phase":q["phase"],
            "A":q["pose_rig"]["A"], "B":q["pose_rig"]["B"],
            "contact":q["contact"], "custody":q["custody"],
            "support_contact":q["support_contact"],
        }
        for _ in range(TIMING_FRAMES[q["timing_class"]]):
            raw.append(k)
        # bridge only if relationship-critical semantics remain unchanged
        i=motion["keys"].index(q)
        if i < len(motion["keys"])-1:
            n=motion["keys"][i+1]
            k1={
                "id":n["key_id"], "phase":n["phase"],
                "A":n["pose_rig"]["A"], "B":n["pose_rig"]["B"],
                "contact":n["contact"], "custody":n["custody"],
                "support_contact":n["support_contact"],
            }
            if _same_semantics(k,k1):
                raw.append({
                    **k,
                    "id":f"{k['id']}~{k1['id']}",
                    "phase":"CONNECTIVE",
                    "A":_interp_actor(k["A"],k1["A"],0.5,-0.35),
                    "B":_interp_actor(k["B"],k1["B"],0.5,0.35),
                })
    return raw

def _font(size):
    candidates=[
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return ImageFont.truetype(p,size)
    return ImageFont.load_default()

def _render_video(motion):
    if TMP.exists(): shutil.rmtree(TMP)
    FRAMES.mkdir(parents=True)
    font=_font(15); small=_font(12)
    seq=_sequence(motion)
    principle=motion["principle"]
    for idx,state in enumerate(seq):
        im=Image.new("RGB",(IMG_W,IMG_H),(8,8,8)); d=ImageDraw.Draw(im)
        d.text((18,10),f"{state['id']}  {state['phase']}",font=small,fill=(235,235,235))
        d.text((18,28),f"CONTACT {state['contact']}   CUSTODY {state['custody']}   SUPPORT {state['support_contact']}",font=small,fill=(180,180,180))
        d.multiline_text((18,52),_render_ascii(state),font=font,fill=(245,245,245),spacing=0)
        d.text((18,370),f"{idx+1:02d}/{len(seq)}  {principle[:90]}",font=small,fill=(150,150,150))
        im.save(FRAMES/f"frame-{idx:04d}.png")
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(FRAMES/"frame-%04d.png"),
        "-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(MP4)
    ],check=True)
    return seq

def _build_spa(motion, ascii_sheet, mp4_bytes):
    motion_text=json.dumps(motion,indent=2,ensure_ascii=True)
    video64=base64.b64encode(mp4_bytes).decode("ascii")
    esc_ascii=html.escape(ascii_sheet)
    esc_json=html.escape(motion_text)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis Contact 010 — Latent Eligibility Force Transfer Repair</title>
<style>
:root{{color-scheme:dark}}body{{margin:0;background:#0b0b0b;color:#eee;font-family:system-ui,sans-serif}}
nav{{position:sticky;top:0;display:flex;gap:.5rem;padding:.75rem;background:#111;border-bottom:1px solid #333}}
button{{font:inherit;padding:.55rem .9rem}}main{{padding:1rem}}section{{display:none}}section.active{{display:block}}
pre{{font-family:"DejaVu Sans Mono","Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}
video{{max-width:100%;height:auto;background:#000}}
</style></head><body>
<nav aria-label="Primary views">
<button data-view="ascii" data-tab="ASCII">ASCII</button><button data-view="json" data-tab="JSON">JSON</button><button data-view="video" data-tab="VIDEO">VIDEO</button>
</nav><main>
<section id="ASCII" class="active"><pre>{esc_ascii}</pre></section>
<section id="JSON"><pre>{esc_json}</pre></section>
<section id="VIDEO"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{video64}"></video></section>
</main><script>
const tabs=[...document.querySelectorAll("button[data-tab]")];
tabs.forEach(b=>b.onclick=()=>{{document.querySelectorAll("section").forEach(s=>s.classList.remove("active"));document.getElementById(b.dataset.tab).classList.add("active");}});
</script></body></html>"""

def main():
    motion=json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    ascii_sheet=ASCII_PATH.read_text(encoding="utf-8")
    seq=_render_video(motion)
    mp4_bytes=MP4.read_bytes()
    got=hashlib.sha256(mp4_bytes).hexdigest()
    expected=motion["motion_dungeon"]["media_sha256"]
    if got != expected:
        raise SystemExit(f"media hash mismatch: {got} != {expected}")
    SPA_PATH.write_text(_build_spa(motion,ascii_sheet,mp4_bytes),encoding="utf-8")
    print(json.dumps({
        "media_sha256":got,"media_bytes":len(mp4_bytes),"frames":len(seq),
        "spa_sha256":hashlib.sha256(SPA_PATH.read_bytes()).hexdigest(),
        "spa":SPA_PATH.name
    },sort_keys=True))

if __name__=="__main__":
    main()
