#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import base64,hashlib,html,json,shutil,subprocess,tempfile
H=Path(__file__).resolve().parent
C=H/"contact-sheet.txt"; M=H/"motion.json"; V=H/".timing030-authoritative.mp4"; S=H/"occupied-line-release-reserve-admission.motion.html"
m=json.loads(M.read_text()); c=C.read_text(); ks=m["keys"]; ps=c.rstrip().split("\n"+"-"*68+"\n"); assert len(ps)==len(ks)
f=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",10); s=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",8)
d=Path(tempfile.mkdtemp(prefix="t030-")); n=0
try:
 for k,b in zip(ks,ps):
  for _ in range(int(k["exposure_ticks"])):
   im=Image.new("RGB",(520,240),"white"); q=ImageDraw.Draw(im)
   q.multiline_text((6,6),b,fill="black",font=f,spacing=0)
   q.text((6,229),"Timing030 | abstract ASCII only | shared-line admission",fill="black",font=s)
   im.save(d/f"frame_{n:04d}.png"); n+=1
 subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(d/"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","40","-map_metadata","-1",str(V)],check=True)
finally: shutil.rmtree(d,ignore_errors=True)
r=V.read_bytes(); e=m["compile"]["media"]; assert n==e["frames"] and len(r)==e["bytes"] and hashlib.sha256(r).hexdigest()==e["sha256"]
a=html.escape(c); j=html.escape(M.read_text()); b=base64.b64encode(r).decode()
page="""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Timing030</title><style>body{font-family:system-ui;margin:0}nav{display:flex;gap:.5rem;padding:.7rem}section{display:none;padding:1rem}section.active{display:block}pre{font-family:ui-monospace,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto}video{max-width:100%}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre>__ASCII__</pre></section><section id="json"><pre>__JSON__</pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,__VIDEO__"></video></section><script>document.querySelectorAll("[data-view]").forEach(x=>x.onclick=()=>{document.querySelectorAll("section").forEach(y=>y.classList.remove("active"));document.getElementById(x.dataset.view).classList.add("active")})</script></body></html>"""
S.write_text(page.replace("__ASCII__",a).replace("__JSON__",j).replace("__VIDEO__",b),encoding="utf-8")
print(json.dumps({"schema":"timing030.build","frames":n,"bytes":len(r),"sha256":e["sha256"],"spa":S.name},sort_keys=True))
