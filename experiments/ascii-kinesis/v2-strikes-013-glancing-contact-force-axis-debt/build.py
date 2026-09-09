#!/usr/bin/env python3
# Motion Dungeon builder for ASCII Kinesis V2 Strikes013.
# Authority: motion.json decisive abstract ASCII rig keys + inferred timing.
# No source pixels, palette, contours, layout, audio, or character art are read.
from __future__ import annotations
import base64, gzip, hashlib, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=json.loads((ROOT/"motion.json").read_text(encoding="utf-8"))
FPS=int(MOTION["timing_policy"]["display_fps"])
WIDTH,HEIGHT=480,240
GRID_W,GRID_H=MOTION["rig"]["grid"]
DEF_A=tuple(MOTION["rig"]["deflector"]["a"])
DEF_B=tuple(MOTION["rig"]["deflector"]["b"])
CONTACT=tuple(MOTION["rig"]["deflector"]["contact"])
SLUG="glancing-contact-force-axis-debt"

def bres(a,b):
    x0,y0=a;x1,y1=b;pts=[];dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1:return pts
        e2=2*err
        if e2>=dy:err+=dy;x0+=sx
        if e2<=dx:err+=dx;y0+=sy

def line_char(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if abs(dx)>=2*abs(dy):return "-"
    if abs(dy)>=2*abs(dx):return "|"
    return "\\" if dx*dy>0 else "/"

def derive(p):
    root=tuple(p["root"]);chest=tuple(p["chest"])
    ls=(chest[0]-2,chest[1]);rs=(chest[0]+2,chest[1]);lhp=(root[0]-2,root[1]+1);rhp=(root[0]+2,root[1]+1)
    def mid(a,b,bias=(0,0)):return ((a[0]+b[0])//2+bias[0],(a[1]+b[1])//2+bias[1])
    return {"ls":ls,"rs":rs,"lhp":lhp,"rhp":rhp,"le":mid(ls,tuple(p["left_hand"]),(-1,0)),"re":mid(rs,tuple(p["right_hand"]),(1,0)),"lk":mid(lhp,tuple(p["left_foot"]),(-1,0)),"rk":mid(rhp,tuple(p["right_foot"]),(1,0))}

def seg(g,a,b,ch=None):
    ch=ch or line_char(a,b)
    for x,y in bres(a,b):
        if 0<=x<GRID_W and 0<=y<GRID_H and g[y][x]==" ":g[y][x]=ch

def ascii_pose(p,contact_state):
    g=[[" "]*GRID_W for _ in range(GRID_H)]
    for x in range(2,GRID_W-2):g[23][x]="_"
    seg(g,DEF_A,DEF_B,"/")
    pts={k:tuple(v) for k,v in p.items() if isinstance(v,list) and len(v)==2};pts.update(derive(p))
    for a,b in [(pts["root"],pts["chest"]),(pts["chest"],pts["head"]),(pts["ls"],pts["le"]),(pts["le"],pts["left_hand"]),(pts["rs"],pts["re"]),(pts["re"],pts["right_hand"]),(pts["root"],pts["lhp"]),(pts["lhp"],pts["lk"]),(pts["lk"],pts["left_foot"]),(pts["root"],pts["rhp"]),(pts["rhp"],pts["rk"]),(pts["rk"],pts["right_foot"])]:
        seg(g,a,b)
    sword_ch="=" if abs(pts["tool_tip"][0]-pts["right_hand"][0])>=abs(pts["tool_tip"][1]-pts["right_hand"][1]) else "/"
    seg(g,pts["right_hand"],pts["tool_tip"],sword_ch)
    for name,ch in [("head","o"),("chest","+"),("root","@"),("ls","+"),("rs","+"),("le","o"),("re","o"),("left_hand","*"),("right_hand","#"),("lk","o"),("rk","o"),("left_foot","/"),("right_foot","\\"),("tool_tip",">")]:
        x,y=pts[name]
        if 0<=x<GRID_W and 0<=y<GRID_H:g[y][x]=ch
    if contact_state=="TOOL_DEFLECTOR_CONTACT":
        x,y=CONTACT;g[y][x]="X"
    return "\n".join("".join(row).rstrip() for row in g).rstrip()

def interp_pt(a,b,t,arc=0):
    u=t*t*(3-2*t)
    return [round(a[0]+(b[0]-a[0])*u),round(a[1]+(b[1]-a[1])*u+arc*math.sin(math.pi*t))]

def interp_pose(a,b,t,arc=0):
    return {fld:interp_pt(a[fld],b[fld],t,arc if fld in {"root","chest","head"} else 0) for fld in ["root","chest","head","left_foot","right_foot","left_hand","right_hand","tool_tip","deflector_contact"]}

def compile_frames():
    out=[]
    for i,k in enumerate(MOTION["keys"]):
        out += [(ascii_pose(k["pose_rig"],k["contact_state"]),k["key_id"])]*int(k["compile_hold_frames"])
        if i==len(MOTION["keys"])-1:continue
        br=MOTION["bridges"][i];n=MOTION["keys"][i+1]
        for q in range(int(br["frames"])):
            t=(q+1)/(int(br["frames"])+1)
            out.append((ascii_pose(interp_pose(k["pose_rig"],n["pose_rig"],t,int(br["root_arc_offset_y"])),k["contact_state"]),f'{k["key_id"]}>{n["key_id"]}'))
    return out

def contact_sheet():
    blocks=["ASCII KINESIS V2 STRIKES013 — GLANCING CONTACT / FORCE-AXIS DEBT","SOURCE ART: NOT EMBEDDED | RIG: ABSTRACT ASCII ONLY | SOURCE TIMING: UNKNOWN | AUTHORED TIMING: INFERRED / STREET_FIGHTER-CAPCOM","POCKET: A GLANCING HIT DOES NOT STOP THE STRIKE; IT ROTATES THE DEBT.","LEGEND: # sword hand | > sword tip | / abstract deflector | X contact",""]
    for k in MOTION["keys"]:
        blocks.append(f'{k["key_id"]} {k["name"]} | {k["timing_class"]} | {k["timing_provenance"]} | SUPPORT={k["support_contact"]} | CONTACT={k["contact_state"]}\nROLE: {k["causal_role"]}\n{ascii_pose(k["pose_rig"],k["contact_state"])}\n')
    return "\n".join(blocks).rstrip()+"\n"

def font():
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf","/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"]:
        if Path(p).exists():return ImageFont.truetype(p,14)
    return ImageFont.load_default()

def render_mp4(path):
    frames=compile_frames();fnt=font()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for idx,(txt,kid) in enumerate(frames):
            im=Image.new("RGB",(WIDTH,HEIGHT),"black");d=ImageDraw.Draw(im)
            d.text((18,10),f"ASCII KINESIS V2 STRIKES013  {kid}  frame {idx+1:02d}/{len(frames):02d}",font=fnt,fill="white")
            d.multiline_text((18,32),txt,font=fnt,fill="white",spacing=1)
            im.save(td/f"f{idx:04d}.png")
        subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(td/"f%04d.png"),"-c:v","libx264","-crf","42","-preset","veryslow","-pix_fmt","yuv420p","-movflags","+faststart",str(path)],check=True)
    return {"sha256":hashlib.sha256(path.read_bytes()).hexdigest(),"bytes":path.stat().st_size,"frames":len(frames)}

def spa(contact,motion_text,mp4_bytes):
    vb=base64.b64encode(mp4_bytes).decode("ascii");ag=base64.b64encode(gzip.compress(contact.encode(),9,mtime=0)).decode();jg=base64.b64encode(gzip.compress(motion_text.encode(),9,mtime=0)).decode()
    return f'''<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Strikes013 — Glancing Contact / Force-Axis Debt</title><style>
:root{{color-scheme:dark;background:#0b0b0c;color:#f2f2f2;font-family:system-ui,sans-serif}}body{{margin:0;padding:16px;max-width:1200px}}
nav{{display:flex;gap:8px;position:sticky;top:0;background:#0b0b0c;padding:8px 0}}button{{font:inherit;padding:8px 12px}}section{{display:none}}section.active{{display:block}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08;font-size:12px}}video{{max-width:100%;height:auto;background:#000}}
</style></head><body><h1>ASCII Kinesis V2 Strikes013 — Glancing Contact / Force-Axis Debt</h1>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre id="ascii-pre"></pre></section><section id="json"><pre id="json-pre"></pre></section>
<section id="video"><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{vb}"></video></section>
<script>const A='{ag}',J='{jg}';async function gz64(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'));return new TextDecoder().decode(await new Response(ds).arrayBuffer())}};(async()=>{{document.getElementById('ascii-pre').textContent=await gz64(A);document.getElementById('json-pre').textContent=await gz64(J)}})();const B=[...document.querySelectorAll('button[data-view]')],S=[...document.querySelectorAll('section')];for(const b of B)b.onclick=()=>{{for(const s of S)s.classList.toggle('active',s.id===b.dataset.view)}};</script></body></html>'''

def main():
    contact=contact_sheet();(ROOT/"contact_sheet.txt").write_text(contact,encoding="utf-8")
    media=render_mp4(ROOT/f"{SLUG}.mp4")
    m=json.loads((ROOT/"motion.json").read_text(encoding="utf-8"));m["media"].update(media)
    (ROOT/"motion.json").write_text(json.dumps(m,separators=(",",":"),ensure_ascii=False),encoding="utf-8")
    mt=(ROOT/"motion.json").read_text(encoding="utf-8")
    (ROOT/f"{SLUG}.motion.html").write_text(spa(contact,mt,(ROOT/f"{SLUG}.mp4").read_bytes()),encoding="utf-8")
    print(json.dumps(media,sort_keys=True))
if __name__=="__main__":main()
