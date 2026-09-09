#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,subprocess,tempfile,shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
MOTION=HERE/"motion.json"
CONTACT=HERE/"contact-sheet.txt"
SPA=HERE/"reference-frame-transfer-velocity-continuity.motion.html"
MP4=HERE/".timing024-authoritative.mp4"
def contact_text(m):
    out=["TIMING024 - REFERENCE-FRAME TRANSFER / VELOCITY CONTINUITY\n","Primitive: REFERENCE_FRAME_AUTHORITY_TRANSFER_WITH_VELOCITY_CONTINUITY\n","Pocket rule: TRANSFER SUPPORT AUTHORITY FIRST; PAY VELOCITY DEBT AFTER.\n","="*96+"\n"]
    for k in m["keys"]:
        out.append(f"{k['key_id']} {k['causal_role']} {k['timing_class']}/{k['exposure_ticks']}t PROV={k['timing_provenance']} SUPPORT={k['support_contact']} SPEED={k['speed_norm']:.2f} ROOTX={k['root_transform']['x']:.2f} FRAME={k['frame_state']}\n")
        out.append(k["pose_rig"]); out.append("-"*96+"\n")
    return "".join(out)
def render_video(m):
    frames=Path(tempfile.mkdtemp(prefix="timing024-frames-"))
    font_path=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    font=ImageFont.truetype(str(font_path),16); small=ImageFont.truetype(str(font_path),10)
    n=0
    for idx,k in enumerate(m["keys"]):
        for _ in range(int(k["exposure_ticks"])):
            im=Image.new("RGB",(640,320),"white"); d=ImageDraw.Draw(im)
            d.multiline_text((20,20),k["pose_rig"],fill="black",font=font,spacing=2)
            g=round(float(k["speed_norm"])*24)
            d.text((320,35),f"ROOT SPEED [{'#'*g}{'.'*(24-g)}] {k['speed_norm']:.2f}",fill="black",font=small)
            d.text((320,60),f"FRAME: {k['frame_state']}",fill="black",font=small)
            d.text((320,82),f"SUPPORT: {k['support_contact']}",fill="black",font=small)
            x0,y0=320,155; d.line((x0,y0,x0+280,y0),fill="black",width=1)
            for j,k2 in enumerate(m["keys"]):
                xx=x0+round(float(k2["root_transform"]["x"])/5.0*260)
                d.text((xx,y0-8),"@" if j==idx else "+",fill="black",font=small)
            d.text((320,180),"authority transfer precedes velocity match",fill="black",font=small)
            d.line((12,260,628,260),fill="black",width=1)
            d.text((14,274),f"Timing024 | {k['key_id']} | {k['causal_role']} | {k['timing_class']} | authored keys only",fill="black",font=small)
            im.save(frames/f"frame_{n:04d}.png"); n+=1
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(frames/"frame_%04d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","34","-map_metadata","-1",str(MP4)],check=True)
    b=MP4.read_bytes(); shutil.rmtree(frames,ignore_errors=True); return b
def spa_text(contact,raw,mp4):
    css="body{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}nav{display:flex;gap:.5rem;padding:.75rem}section{display:none;padding:1rem}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto}"
    vb=base64.b64encode(mp4).decode("ascii"); ab=base64.b64encode(gzip.compress(contact.encode("ascii"),compresslevel=9,mtime=0)).decode("ascii"); jb=base64.b64encode(gzip.compress(raw.encode("ascii"),compresslevel=9,mtime=0)).decode("ascii")
    return '<!doctype html><html><head><meta charset="utf-8"><title>Timing024</title><style>'+css+'</style></head><body><nav><button data-view="ascii" onclick="show(\'ascii\')">ASCII</button><button data-view="json" onclick="show(\'json\')">JSON</button><button data-view="video" onclick="show(\'video\')">VIDEO</button></nav><section id="ascii" class="active"><pre id="ascii-pre"></pre></section><section id="json"><pre id="json-pre"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+vb+'"></video></section><script>function show(id){for(const s of document.querySelectorAll("section"))s.classList.remove("active");document.getElementById(id).classList.add("active");}async function inflate64(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}Promise.all([inflate64("'+ab+'"),inflate64("'+jb+'")]).then(([a,j])=>{document.getElementById("ascii-pre").textContent=a;document.getElementById("json-pre").textContent=j;});</script></body></html>\n'
def main():
    m=json.loads(MOTION.read_text(encoding="ascii")); contact=contact_text(m); CONTACT.write_text(contact,encoding="ascii")
    mp4=render_video(m); got=hashlib.sha256(mp4).hexdigest(); m["compile"]["media"]["sha256"]=got; m["compile"]["media"]["bytes"]=len(mp4); m["revision"]["actual_render_sha256"]=got
    raw=json.dumps(m,ensure_ascii=True,sort_keys=True,separators=(",",":"))+"\n"; MOTION.write_text(raw,encoding="ascii"); SPA.write_text(spa_text(contact,raw,mp4),encoding="utf-8")
    print(json.dumps({"experiment_id":m["experiment_id"],"frames":m["compile"]["media"]["frames"],"media_sha256":got,"bytes":len(mp4),"ok":True},sort_keys=True))
if __name__=="__main__": main()
