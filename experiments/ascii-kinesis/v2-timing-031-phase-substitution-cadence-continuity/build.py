#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import base64,gzip,hashlib,html,json,shutil,subprocess,tempfile
H=Path(__file__).resolve().parent
C=H/"contact-sheet.txt"; M=H/"motion.json"; V=H/".timing031-authoritative.mp4"; S=H/"phase-substitution-cadence-continuity.motion.html"
m=json.loads(M.read_text()); c=C.read_text(); ks=m["keys"]; ps=c.rstrip().split("\n"+"-"*68+"\n"); assert len(ps)==len(ks)
f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",10); s=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",8)
d=Path(tempfile.mkdtemp(prefix="t031-")); n=0
try:
 for k,b in zip(ks,ps):
  for _ in range(int(k["exposure_ticks"])):
   im=Image.new("RGB",(620,270),"white"); q=ImageDraw.Draw(im); q.multiline_text((8,5),b,fill="black",font=f,spacing=0)
   q.text((8,258),"Timing031 | abstract ASCII only | pass-slot substitution",fill="black",font=s); im.save(d/f"frame_{n:04d}.png"); n+=1
 subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(d/"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","38","-map_metadata","-1",str(V)],check=True)
finally: shutil.rmtree(d,ignore_errors=True)
r=V.read_bytes(); e=m["compile"]["media"]; assert n==e["frames"] and len(r)==e["bytes"] and hashlib.sha256(r).hexdigest()==e["sha256"]
pack=lambda x:base64.b64encode(gzip.compress(x.encode(),compresslevel=9,mtime=0)).decode()
a=pack(c); j=pack(M.read_text()); b=base64.b64encode(r).decode()
page="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Timing031</title><style>body{font-family:system-ui;margin:0}nav{display:flex;gap:.5rem;padding:.7rem}section{display:none;padding:1rem}section.active{display:block}pre{font-family:ui-monospace,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto}video{max-width:100%}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,__VIDEO__"></video></section><script>const gz=async(s)=>{const u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()};Promise.all([gz("__ASCII__"),gz("__JSON__")]).then(([a,j])=>{document.getElementById("a").textContent=a;document.getElementById("j").textContent=j});document.querySelectorAll("[data-view]").forEach(x=>x.onclick=()=>{document.querySelectorAll("section").forEach(y=>y.classList.remove("active"));document.getElementById(x.dataset.view).classList.add("active")})</script></body></html>"""
S.write_text(page.replace("__ASCII__",a).replace("__JSON__",j).replace("__VIDEO__",b),encoding="utf-8")
print(json.dumps({"schema":"timing031.build","frames":n,"bytes":len(r),"sha256":e["sha256"],"spa":S.name},sort_keys=True))
