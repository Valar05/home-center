#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
MOTION=HERE/"motion.json"; MANIFEST=HERE/"manifest.json"; CONTACT=HERE/"contact-sheet.txt"
MP4=HERE/"drag-capture-whiplash-recovery.mp4"; SPA=HERE/"drag-capture-whiplash-recovery.motion.html"
W,H,GROUND_Y=72,27,23; HOLD={"ONES":1,"TWOS":2,"FOURS":4}
JOINTS=["head","neck","shoulder_l","shoulder_r","elbow_l","elbow_r","hand_l","hand_r","pelvis","knee_l","knee_r","foot_l","foot_r"]
LINKS=[("head","neck"),("neck","shoulder_l"),("neck","shoulder_r"),("shoulder_l","elbow_l"),("elbow_l","hand_l"),("shoulder_r","elbow_r"),("elbow_r","hand_r"),("neck","pelvis"),("pelvis","knee_l"),("knee_l","foot_l"),("pelvis","knee_r"),("knee_r","foot_r")]
def pose(o): return dict(zip(JOINTS,o["pose"]))
def bres(a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): return out
        e2=2*err
        if e2>=dy: err+=dy;x0+=sx
        if e2<=dx: err+=dx;y0+=sy
def glyph(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if abs(dx)>abs(dy)*1.8:return "-"
    if abs(dy)>abs(dx)*1.8:return "|"
    return "\\" if dx*dy>0 else "/"
def render_ascii(o,label=True):
    p=pose(o);g=[[" "]*W for _ in range(H)]
    def put(x,y,c,overwrite=False):
        if 0<=x<W and 0<=y<H and (overwrite or g[y][x]==" "):g[y][x]=c
    for x in range(W):g[GROUND_Y][x]="_"
    dp=o.get("drag_pose")
    if dp and o.get("drag_surface_state")!="STOWED":
        s=dp["surface"]
        for a,b in zip(s,s[1:]):
            for x,y in bres(a,b):put(x,y,"~",True)
        for a,b in ((s[0],dp["tether_l"]),(s[-1],dp["tether_r"])):
            c=glyph(a,b)
            for x,y in bres(a,b)[1:]:put(x,y,c,True)
    for a,b in LINKS:
        c=glyph(p[a],p[b])
        for x,y in bres(p[a],p[b])[1:-1]:put(x,y,c)
    for n,(x,y) in p.items():put(x,y,"O" if n=="head" else ("@" if n=="pelvis" else "o"),True)
    hx,hy=p["head"];put(hx+2,hy,">",True)
    sc=o["support_contact"]
    if sc in ("GROUND_BOTH","GROUND_LEFT","GROUND_LEFT_DOMINANT"):
        x,y=p["foot_l"];put(x,min(H-1,y+1),"=",True)
    if sc in ("GROUND_BOTH","GROUND_RIGHT","GROUND_RIGHT_DOMINANT"):
        x,y=p["foot_r"];put(x,min(H-1,y+1),"=",True)
    if label:
        px,py=p["pelvis"];m={"READY":"+","LOAD":"<","LAUNCH":"^","RISE":"^","APEX":"~","DESCENT_BEGIN":"v","DESCENT":"v","PRECONTACT":"?","CONTACT":"!","LAND_COMPRESSION":"#","REBOUND":"^","SETTLE":".","RECOVERY":":","RETURN":"+"}.get(o["vertical_phase"],"*")
        put(max(0,px-4),py,m,True)
    return "\n".join("".join(r).rstrip() for r in g)
def contact_sheet(d):
    out=["ASCII KINESIS V2 AIRBORNE 013 — DRAG-CAPTURE WHIPLASH RECOVERY","COPYABLE CONTACT SHEET — ABSTRACT RIG ONLY — NO SOURCE PIXELS","Legend: O head | @ pelvis/root | o joints | > facing | ~ drag surface | = grounded support",""]
    for k in d["keys"]:out.append(f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | support={k['support_contact']} | contact={k['contact_state']} | drag={k['drag_surface_state']} | phase={k['vertical_phase']}\n"+render_ascii(k))
    out.append("--- AUTHORED BRIDGES ---")
    for b in d["bridge_keys"]:out.append(f"{b['bridge_id']} {b['from_key']} -> {b['to_key']} | {b['timing_class']} {b['timing_provenance']} | geometry-only; semantic state unchanged")
    return "\n\n".join(out)
def sequence(d):
    bm={(b["from_key"],b["to_key"]):b for b in d["bridge_keys"]};out=[];ks=d["keys"]
    for i,k in enumerate(ks):
        out += [(k["key_id"],render_ascii(k),"decisive")]*HOLD[k["timing_class"]]
        if i+1<len(ks):
            n=ks[i+1];b=bm.get((k["key_id"],n["key_id"]))
            if b:
                if (k["support_contact"],k["contact_state"],k["drag_surface_state"])!=(n["support_contact"],n["contact_state"],n["drag_surface_state"]):raise RuntimeError("bridge crosses semantic state")
                out += [(b["bridge_id"],render_ascii(b,False),"bridge")]*HOLD[b["timing_class"]]
    return out
def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf","/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"):
        if Path(p).exists():return ImageFont.truetype(p,size)
    return ImageFont.load_default()
def frame(text,path,label):
    im=Image.new("RGB",(640,360),"black");dr=ImageDraw.Draw(im)
    dr.text((10,7),"ASCII KINESIS V2 — AIRBORNE 013 — DRAG CAPTURE WHIPLASH RECOVERY",font=font(10),fill="white")
    dr.text((10,22),label,font=font(10),fill="white");dr.multiline_text((7,38),text,font=font(11),fill="white",spacing=0);im.save(path)
def make_video(d):
    seq=sequence(d)
    with tempfile.TemporaryDirectory(prefix="air013-") as td:
        td=Path(td)
        for i,(lab,txt,kind) in enumerate(seq):frame(txt,td/f"f-{i:04d}.png",f"{i:03d} {lab} [{kind}]")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(d["compile"]["fps"]),"-i",str(td/"f-%04d.png"),"-c:v","libx264","-preset","veryslow","-crf","42","-pix_fmt","yuv420p","-movflags","+faststart",str(MP4)],check=True)
    return seq
def parts(t,n=3600):return "[\n"+",\n".join(json.dumps(t[i:i+n]) for i in range(0,len(t),n))+"\n]"
def pack(t):return base64.b64encode(gzip.compress(t.encode(),9,mtime=0)).decode()
def html_page(d,sheet,media):
    j=json.dumps(d,sort_keys=True,separators=(",",":"),ensure_ascii=False);V=parts(base64.b64encode(media).decode());A=parts(pack(sheet));J=parts(pack(j))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Airborne 013</title><style>:root{{color-scheme:dark;background:#0d0d0d;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1200px}}nav{{display:flex;gap:.5rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}video{{max-width:100%;height:auto}}</style></head><body><h1>Drag-Capture Whiplash Recovery</h1><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="ap"></pre></section><section id="json" hidden><pre id="jp"></pre></section><section id="video" hidden><video id="v" controls loop playsinline></video></section><script>const V={V},A={A},J={J};v.src="data:video/mp4;base64,"+V.join("");async function g(x){{const u=Uint8Array.from(atob(x.join("")),c=>c.charCodeAt(0));return new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([g(A),g(J)]).then(([a,j])=>{{ap.textContent=a;jp.textContent=j}});for(const b of document.querySelectorAll("button[data-view]"))b.onclick=()=>{{for(const s of document.querySelectorAll("section"))s.hidden=s.id!==b.dataset.view}};</script></body></html>'''
def main():
    d=json.loads(MOTION.read_text());seq=make_video(d);media=MP4.read_bytes();sha=hashlib.sha256(media).hexdigest();sheet=contact_sheet(d);ash=hashlib.sha256(sheet.encode()).hexdigest()
    if d["compile"].get("media_sha256") and d["compile"]["media_sha256"]!=sha:raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={d['compile']['media_sha256']} actual={sha}")
    if d.get("ascii_sheet_sha256") and d["ascii_sheet_sha256"]!=ash:raise SystemExit(f"ASCII_IDENTITY_MISMATCH expected={d['ascii_sheet_sha256']} actual={ash}")
    CONTACT.write_text(sheet);SPA.write_text(html_page(d,sheet,media))
    print(json.dumps({"media_sha256":sha,"media_bytes":len(media),"frames":len(seq),"ascii_sha256":ash},sort_keys=True))
if __name__=="__main__":main()
