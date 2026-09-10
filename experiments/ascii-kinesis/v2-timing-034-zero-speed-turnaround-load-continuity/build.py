#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import base64,gzip,hashlib,json,shutil,subprocess,tempfile

R=Path(__file__).resolve().parent
C=R/"contact-sheet.txt"
M=R/"motion.json"
V=R/".zero-speed-turnaround-load-continuity.mp4"
S=R/"zero-speed-turnaround-load-continuity.motion.html"

contact=C.read_text(encoding="utf-8")
motion=json.loads(M.read_text(encoding="utf-8"))
blocks=[b.strip("\n") for b in contact.split("------------------------------------------------------------------------------\n") if b.strip() and b.startswith("K")]
by={b.split()[0]:b for b in blocks}

font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",16)
small=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",11)
W,H=780,360
td=Path(tempfile.mkdtemp(prefix="ascii-kinesis-t034-"))
n=0
try:
    for k in motion["keys"]:
        b=by[k["key_id"]]
        for _ in range(int(k["exposure_ticks"])):
            im=Image.new("RGB",(W,H),"white")
            d=ImageDraw.Draw(im)
            d.multiline_text((12,10),b,fill="black",font=font,spacing=2)
            d.text((12,337),"Timing034 | zero speed is not zero load | both support contacts persist | abstract ASCII only",fill="black",font=small)
            im.save(td/f"f_{n:04d}.png")
            n+=1
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(td/"f_%04d.png"),
        "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","39","-map_metadata","-1",str(V)
    ],check=True)
finally:
    shutil.rmtree(td,ignore_errors=True)

raw=V.read_bytes()
motion["compile"]={
    "renderer":"Motion Dungeon ASCII-only deterministic key-exposure renderer",
    "fps":24,"frame_count":n,
    "media":{"codec":"h264","pix_fmt":"yuv420p","width":W,"height":H,"fps":24,"frames":n,
             "bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest()}
}
M.write_text(json.dumps(motion,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
mt=M.read_text(encoding="utf-8")

c64=base64.b64encode(gzip.compress(contact.encode("utf-8"),mtime=0)).decode("ascii")
j64=base64.b64encode(gzip.compress(mt.encode("utf-8"),mtime=0)).decode("ascii")
v64=base64.b64encode(raw).decode("ascii")
page=f'''<!doctype html><meta charset="utf-8"><title>Timing034 - Zero-Speed Turnaround / Load Continuity</title>
<style>body{{font-family:system-ui,sans-serif;margin:0;padding:1rem}}nav{{display:flex;gap:.5rem;margin-bottom:1rem}}button{{font:inherit;padding:.5rem .75rem}}section{{display:none}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;border:1px solid currentColor;padding:.75rem;line-height:1.08}}video{{max-width:100%;height:auto}}</style>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section>
<section id="video"><video controls loop muted playsinline src="data:video/mp4;base64,{v64}"></video></section>
<script>const G=async(s)=>{{let b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));let x=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip")));return x.text()}};G("{c64}").then(x=>a.textContent=x);G("{j64}").then(x=>j.textContent=x);const q=[...document.querySelectorAll("section")];document.querySelectorAll("button[data-view]").forEach(b=>b.onclick=()=>q.forEach(s=>s.classList.toggle("active",s.id===b.dataset.view)));</script>'''
S.write_text(page,encoding="utf-8")
print(json.dumps(motion["compile"],sort_keys=True))
