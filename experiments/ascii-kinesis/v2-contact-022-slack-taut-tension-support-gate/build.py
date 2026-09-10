#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import base64, gzip, hashlib, json, math, shutil, subprocess

ROOT=Path(__file__).resolve().parent
MOTION_PATH=ROOT/"motion.json"
ASCII_PATH=ROOT/"contact-sheet.txt"
BUILD=ROOT/".motion-build"
VIDEO=BUILD/"motion.mp4"
SPA=ROOT/"slack-taut-tension-support-gate.motion.html"
TIMING_FRAMES={"ONES":1,"TWOS":2,"FOURS":4}
CANVAS=(560,330)
BONES=[("head","neck"),("neck","shoulder_l"),("neck","shoulder_r"),
("shoulder_l","elbow_l"),("elbow_l","hand_l"),("shoulder_r","elbow_r"),
("elbow_r","hand_r"),("neck","pelvis"),("pelvis","knee_l"),("knee_l","foot_l"),
("pelvis","knee_r"),("knee_r","foot_r")]

def bres(p0,p1):
    x0,y0=p0;x1,y1=p1;pts=[];dx=abs(x1-x0);sx=1 if x0<x1 else -1
    dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy:err+=dy;x0+=sx
        if e2<=dx:err+=dx;y0+=sy
    return pts

def linechar(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if abs(dx)>=2*abs(dy):return "-"
    if abs(dy)>=2*abs(dx):return "|"
    return "\\" if dx*dy>0 else "/"

def tether_points(anchor,pelvis,state):
    ax,ay=anchor; px,py=pelvis
    if state=="TAUT":
        return bres((ax,ay),(px,py))
    n=max(abs(px-ax),abs(py-ay),8)
    sag=3.0 if state=="SLACK" else 1.0
    pts=[]
    for i in range(n+1):
        t=i/n
        x=ax+(px-ax)*t
        y=ay+(py-ay)*t + 4*sag*t*(1-t)
        pts.append((round(x),round(y)))
    out=[]
    for p in pts:
        if not out or p!=out[-1]: out.append(p)
    return out

def render_ascii(k):
    W=k["_grid_w"];H=k["_grid_h"];floor_y=k["_floor_y"]
    g=[[" "]*W for _ in range(H)]
    ax,ay=k["anchor"]; g[ay][ax]="@"
    pts=k["pose_rig"]; pelvis=tuple(pts["pelvis"])
    tchar="=" if k["tension_load"]>0 else (":" if k["tether_state"]=="TAUT" else "~")
    for x,y in tether_points((ax,ay),pelvis,k["tether_state"])[1:-1]:
        if 0<=x<W and 0<=y<H and g[y][x]==" ": g[y][x]=tchar
    for x in range(2,W-2):
        if g[floor_y][x]==" ": g[floor_y][x]="_"
    for a,b in BONES:
        p0=tuple(pts[a]);p1=tuple(pts[b]);ch=linechar(p0,p1)
        for x,y in bres(p0,p1)[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ": g[y][x]=ch
    for n,p in pts.items():
        x,y=p;c="O" if n=="head" else ("+" if n=="pelvis" else "o")
        if 0<=x<W and 0<=y<H:g[y][x]=c
    px,py=pts["pelvis"]
    if 0<=px<W and 0<=py-1<H and g[py-1][px]==" ":g[py-1][px]="x"
    if "GROUND_LEFT" in k["support_contact"] or "GROUND_BOTH" in k["support_contact"]:
        fx,fy=pts["foot_l"]
        if 0<=fx<W and 0<=fy<H:g[fy][fx]="!"
    if "GROUND_RIGHT" in k["support_contact"] or "GROUND_BOTH" in k["support_contact"]:
        fx,fy=pts["foot_r"]
        if 0<=fx<W and 0<=fy<H:g[fy][fx]="!"
    return "\n".join("".join(r).rstrip() for r in g)

def build_contact_sheet(m):
    out=[
      "ASCII KINESIS V2 CONTACT022 — SLACK / TAUT TENSION SUPPORT GATE",
      "Legend: @ fixed external anchor | ~ slack relation | : taut zero-load | = taut loaded | + pelvis/harness | x COM | ! ground support",
      "Source art is NOT present. All geometry below is an independent abstract ASCII rig.",
      ""
    ]
    for k in m["keys"]:
        kk=dict(k);kk["_grid_w"]=m["rig"]["grid"]["width"];kk["_grid_h"]=m["rig"]["grid"]["height"];kk["_floor_y"]=m["rig"]["grid"]["floor_y"]
        out += [
          f'{k["key_id"]}  {k["name"]}  [{k["timing_class"]}/{k["timing_provenance"]}]',
          f'ATTACHMENT={k["contact_state"]}  REL={k["relationship_state"]}  SUPPORT={k["support_contact"]}  CUSTODY={k["custody"]}',
          f'TETHER={k["tether_state"]}  TENSION={k["tension_load"]:.2f}  LENGTH={k["length_at_key"]:.3f}/{k["max_length"]:.3f}  FORCE_AXIS={k["force_axis"]}',
          f'CAUSE: {k["root_com_note"]}',
          render_ascii(kk),
          ""
        ]
    return "\n".join(out).rstrip()+"\n"

def font(size):
    p=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    if not p.is_file(): raise SystemExit("MISSING_REQUIRED_FONT: DejaVuSansMono.ttf")
    return ImageFont.truetype(str(p),size)

def ease(t):
    return t*t*(3-2*t)

def lerp(a,b,t):
    return a+(b-a)*t

def interp_key(a,b,t,m):
    e=ease(t)
    A=a["pose_rig"];B=b["pose_rig"]
    anchor=tuple(a["anchor"]); L=a["max_length"]
    pa=A["pelvis"]; pb=B["pelvis"]
    if a["tether_state"]=="TAUT" and b["tether_state"]=="TAUT":
        aa=math.atan2(pa[1]-anchor[1],pa[0]-anchor[0]); bb=math.atan2(pb[1]-anchor[1],pb[0]-anchor[0])
        d=(bb-aa+math.pi)%(2*math.pi)-math.pi
        ang=aa+d*e
        pxf=anchor[0]+L*math.cos(ang); pyf=anchor[1]+L*math.sin(ang)
    else:
        pxf=lerp(pa[0],pb[0],e); pyf=lerp(pa[1],pb[1],e)
    pose={}
    for n in A:
        if n=="pelvis":
            pose[n]=(round(pxf),round(pyf));continue
        ao=(A[n][0]-pa[0],A[n][1]-pa[1]); bo=(B[n][0]-pb[0],B[n][1]-pb[1])
        ox=lerp(ao[0],bo[0],e);oy=lerp(ao[1],bo[1],e)
        pose[n]=(round(pxf+ox),round(pyf+oy))
    k=dict(a);k["pose_rig"]=pose
    k["name"]=a["name"]+" -> "+b["name"]
    if a["tether_state"]=="TAUT" and b["tether_state"]=="TAUT":
        k["tension_load"]=lerp(a["tension_load"],b["tension_load"],e)
    k["_grid_w"]=m["rig"]["grid"]["width"];k["_grid_h"]=m["rig"]["grid"]["height"];k["_floor_y"]=m["rig"]["grid"]["floor_y"]
    return k

def frame_for(k,m,fnt):
    kk=dict(k);kk["_grid_w"]=m["rig"]["grid"]["width"];kk["_grid_h"]=m["rig"]["grid"]["height"];kk["_floor_y"]=m["rig"]["grid"]["floor_y"]
    art=render_ascii(kk)
    im=Image.new("RGB",CANVAS,(10,10,12));d=ImageDraw.Draw(im)
    d.text((8,5),"CONTACT022 | SLACK->TAUT TENSION SUPPORT GATE",font=fnt["small"],fill=(235,235,235))
    d.text((8,17),f'{k["key_id"]}  {k["name"]}',font=fnt["small"],fill=(235,235,235))
    y=30
    for ln in art.splitlines():
        d.text((8,y),ln,font=fnt["art"],fill=(242,242,242));y+=9
    d.text((8,298),f'attachment=ATTACHED  tether={k["tether_state"]}  tension={k["tension_load"]:.2f}  support={k["support_contact"]}',font=fnt["tiny"],fill=(220,220,220))
    d.text((8,310),"force can turn ON/OFF without attachment topology changing",font=fnt["tiny"],fill=(220,220,220))
    return im

def b64gzip(text):
    return base64.b64encode(gzip.compress(text.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")

def make_spa(a_text,j_text,video):
    a=b64gzip(a_text);j=b64gzip(j_text);v=base64.b64encode(video).decode("ascii")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Contact022 - Slack-Taut Tension Support Gate</title><style>body{{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}}nav{{position:sticky;top:0;padding:10px;background:#191919;border-bottom:1px solid #555}}button{{margin-right:8px;padding:8px 14px}}section{{display:none;padding:16px}}section.active{{display:block}}pre{{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="ascii-out"></pre></section><section id="json"><pre id="json-out"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{v}"></video></section><script>const A="{a}",J="{j}";async function inflate(s){{const u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([u]).stream().pipeThrough(ds)).text();}}Promise.all([inflate(A),inflate(J)]).then(([a,j])=>{{document.getElementById("ascii-out").textContent=a;document.getElementById("json-out").textContent=j;}});for(const b of document.querySelectorAll("button[data-view]"))b.onclick=()=>{{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view);}};</script></body></html>'''

def main():
    m=json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    ASCII_PATH.write_text(build_contact_sheet(m),encoding="utf-8")
    if BUILD.exists():shutil.rmtree(BUILD)
    BUILD.mkdir(); fd=BUILD/"frames";fd.mkdir()
    fnt={"art":font(9),"small":font(8),"tiny":font(7)}
    idx=0
    for i,k in enumerate(m["keys"]):
        for _ in range(TIMING_FRAMES[k["timing_class"]]):
            frame_for(k,m,fnt).save(fd/f"{idx:04d}.png");idx+=1
        if i+1<len(m["keys"]):
            b=m["keys"][i+1]
            q=interp_key(k,b,0.55,m)
            frame_for(q,m,fnt).save(fd/f"{idx:04d}.png");idx+=1
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(fd/"%04d.png"),
                    "-map_metadata","-1","-c:v","libx264","-threads","1","-pix_fmt","yuv420p","-crf","38",
                    "-movflags","+faststart","-fflags","+bitexact","-flags:v","+bitexact",str(VIDEO)],check=True)
    video=VIDEO.read_bytes(); sha=hashlib.sha256(video).hexdigest()
    expected=m["compile"].get("media_sha256")
    if expected and sha!=expected: raise SystemExit(f"MEDIA_IDENTITY_MISMATCH: expected {expected} got {sha}")
    SPA.write_text(make_spa(ASCII_PATH.read_text(encoding="utf-8"),MOTION_PATH.read_text(encoding="utf-8"),video),encoding="utf-8")
    print(json.dumps({"ok":True,"frames":idx,"media_sha256":sha,"media_bytes":len(video),"spa":SPA.name},sort_keys=True))
if __name__=="__main__":main()
