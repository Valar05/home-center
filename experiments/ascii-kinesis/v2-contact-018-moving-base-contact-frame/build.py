#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,hashlib,json,math,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont

R=Path(__file__).resolve().parent
M=R/"motion.json"; A=R/"contact-sheet.txt"; S=R/"moving-base-contact-frame.motion.html"
T=R/".motion-build"; F=T/"frames"; V=T/"motion.mp4"
W,H,FPS=104,30,24
J=["head","shoulder","pelvis","hand_f","hand_b","knee_f","knee_b","foot_f","foot_b"]
HOLD={"ONES":1,"TWOS":2,"FOURS":4}
LOCKED={"BASE_LOCAL_LOCK"}

def P(v): return {n:[float(x),float(y)] for n,(x,y) in zip(J,v)}
def state(q):
    return {"id":q["id"],"phase":q["phase"],"A":P(q["pose"]),"base_x":float(q["base_x"]),
            "contact":q["contact"],"support":q["support"],"custody":q["custody"],
            "force_owner":q["force_owner"],"normal_force":float(q["normal_force"])}

def cells(a,b):
    x0,y0=map(round,a); x1,y1=map(round,b)
    dx=abs(x1-x0); dy=-abs(y1-y0); sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1
    e=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): return out
        e2=2*e
        if e2>=dy: e+=dy; x0+=sx
        if e2<=dx: e+=dx; y0+=sy

def line(g,a,b,ch,overwrite=False):
    for x,y in cells(a,b):
        if 0<=x<W and 0<=y<H and (overwrite or g[y][x]==" "): g[y][x]=ch

def interp_pose(a,b,t,curve=0.0):
    s=t*t*(3-2*t); out={}
    for n in a:
        x=a[n][0]+(b[n][0]-a[n][0])*s
        y=a[n][1]+(b[n][1]-a[n][1])*s
        if n in ("head","hand_f","hand_b","knee_f","knee_b"):
            y += curve*math.sin(math.pi*t)
        out[n]=[x,y]
    return out

def semantic_tuple(s):
    return (s["contact"],s["support"],s["custody"])

def legal_bridge(a,b):
    return semantic_tuple(a)==semantic_tuple(b)

def interp_state(a,b,t,curve=0.0):
    s=t*t*(3-2*t)
    bx=a["base_x"]+(b["base_x"]-a["base_x"])*s
    pose=interp_pose(a["A"],b["A"],t,curve)
    if a["contact"]=="BASE_LOCAL_LOCK" and b["contact"]=="BASE_LOCAL_LOCK":
        pose["foot_f"]=[bx+5,24]
    return {**a,"id":a["id"]+"~"+b["id"],"phase":"AUTHORED_CONNECTIVE",
            "A":pose,"base_x":bx,
            "normal_force":a["normal_force"]+(b["normal_force"]-a["normal_force"])*s}

def frame_ascii(s):
    g=[[" "]*W for _ in range(H)]
    ground_y=27
    for x in range(W):
        g[ground_y][x]="."
    bx=round(s["base_x"]); by=24; bw=22
    if 0<=bx<W: g[by][bx]="["
    for x in range(bx+1,bx+bw-1):
        if 0<=x<W: g[by][x]="="
    if 0<=bx+bw-1<W: g[by][bx+bw-1]="]"
    for i,ch in enumerate(">>>"):
        x=bx+bw-4+i
        if 0<=x<W and by+1<H: g[by+1][x]=ch

    a=s["A"]
    for p,q in [("head","shoulder"),("shoulder","pelvis"),("shoulder","hand_f"),("shoulder","hand_b"),
                ("pelvis","knee_f"),("knee_f","foot_f"),("pelvis","knee_b"),("knee_b","foot_b")]:
        dx=a[q][0]-a[p][0]; dy=a[q][1]-a[p][1]
        ch="-" if abs(dx)>abs(dy)*1.7 else ("|" if abs(dy)>abs(dx)*1.7 else ("\\" if dx*dy>0 else "/"))
        line(g,a[p],a[q],ch)
    marks=[("head","A"),("shoulder","O"),("pelvis","X"),("hand_f","*"),("hand_b","*"),
           ("knee_f","o"),("knee_b","o"),("foot_f","^"),("foot_b","^")]
    for n,ch in marks:
        x,y=map(round,a[n])
        if 0<=x<W and 0<=y<H: g[y][x]=ch

    ax=round(s["base_x"]+5); ay=24
    if s["contact"]=="BASE_POINT_ACQUIRE":
        if 0<=ax<W: g[ay][ax]="+"
    elif s["contact"]=="BASE_LOCAL_LOCK":
        if 0<=ax<W: g[ay][ax]="#"
        nf=max(0,min(7,round(s["normal_force"])))
        for k in range(1,nf+1):
            yy=ay-k
            if 0<=ax<W and yy>=0 and g[yy][ax]==" ": g[yy][ax]="!" if k<nf else "^"
    elif s["contact"]=="BASE_TOUCH_UNLOADED":
        if 0<=ax<W: g[ay][ax]="o"
    if s["contact"] in ("GROUND_POINT_ACQUIRE","GROUND_STABLE"):
        fx,fy=map(round,a["foot_f"])
        if 0<=fx<W and 0<=fy<H: g[fy][fx]="#"

    return "\n".join("".join(row).rstrip() for row in g)

def sequence(m):
    desired=[0,0,0,2,2,0,0,2,0,0,0,0]
    curves=[0,0,0,-.4,.5,0,0,.5,0,0,0,0]
    out=[]
    for i,q in enumerate(m["keys"]):
        a=state(q)
        out += [a]*HOLD[q["timing_class"]]
        if i<len(m["keys"])-1:
            b=state(m["keys"][i+1])
            n=desired[i] if legal_bridge(a,b) else 0
            for j in range(1,n+1):
                out.append(interp_state(a,b,j/(n+1),curves[i]))
    return out

def contact_sheet(m):
    out=[
        m["experiment_id"],
        m["principle"],
        "REVISION: NEW_CONCEPT | revises=null | negative_fixture=null | source_change=NOT_APPLICABLE_NEW_CONCEPT",
        f'SOURCE: TSR asset {m["source"]["asset_id"]} — {m["source"]["title"]} / {m["source"]["game"]} / {m["source"]["platform"]}',
        "SOURCE ROLE: POSE_REFERENCE + CONTACT_REFERENCE; NOT_TIMING_REFERENCE; source-authentic timing UNKNOWN.",
        "WHOLE SOURCE: authoritative campaign receipt 5572872470 records exact 136x172 PNG inspection; 1,985 bytes; SHA-256 a9d3f07c8a72278c80a15e85e335f5669d108d4d2d002eb40b2311279191a633.",
        "RIGHTS: commercial source is evidence only; output contains no source pixels/palette/costume/contours/layout/tracing/choreography/redistribution/close imitation.",
        "TIMING: every decisive key INFERRED / STREET_FIGHTER-CAPCOM. ONES/TWOS/FOURS are display classes, not seconds.",
        "VISIBLE LEGEND: A=head O=shoulder X=pelvis *=hands o=knees ^=feet  [===]=moving base  +=acquire  #=loaded anchor  o(base)=touch-unloaded  >>>=base world motion.",
        "RELATIONSHIP LAW: K3-K5 supported foot stays at base-local x=+5 while base translates in world. World motion alone does NOT buy a contact-state change."
    ]
    for q in m["keys"]:
        s=state(q)
        out += [
            "="*92,
            f'{q["id"]} {q["phase"]} [{q["timing_class"]}/{q["timing_provenance"]}]',
            f'contact={q["contact"]} | support={q["support"]} | custody={q["custody"]}',
            f'base_x={q["base_x"]} | base_local_anchor=+5 | force_owner={q["force_owner"]} | normal_force={q["normal_force"]}',
            f'role={q["role"]}',
            f'arc={q["arc"]}',
            frame_ascii(s)
        ]
    return "\n".join(out)+"\n"

def gz(s):
    return base64.b64encode(gzip.compress(s.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")

def spa(m,a,v):
    aa=gz(a)
    jj=gz(json.dumps(m,separators=(",",":"),ensure_ascii=True))
    vv=base64.b64encode(v).decode("ascii")
    title=m["experiment_id"]
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+title+'</title><style>html,body{margin:0;background:#0b0b0b;color:#eee;font-family:system-ui}nav{position:sticky;top:0;background:#111;padding:8px}button[data-view]{margin-right:8px;padding:8px 14px}section{display:none;padding:12px}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{display:block;max-width:100%;height:auto;margin:auto}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video id="v" controls autoplay loop muted playsinline></video></section><script>const A="'+aa+'",J="'+jj+'",V="'+vv+'";async function d(s){return new TextDecoder().decode(await new Response(new Blob([Uint8Array.from(atob(s),c=>c.charCodeAt(0))]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer())}(async()=>{a.textContent=await d(A);j.textContent=await d(J);v.src="data:video/mp4;base64,"+V})();document.querySelectorAll("button[data-view]").forEach(b=>b.onclick=()=>{document.querySelectorAll("section").forEach(s=>s.classList.remove("active"));document.getElementById(b.dataset.view).classList.add("active")});</script></body></html>'

def render_video(m):
    if T.exists(): shutil.rmtree(T)
    F.mkdir(parents=True)
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",8)
    q=sequence(m)
    for i,k in enumerate(q):
        im=Image.new("RGB",(640,360),(8,8,8))
        d=ImageDraw.Draw(im)
        d.text((8,6),f'{k["id"]} {k["phase"]}',font=font,fill=(245,245,245))
        d.text((8,18),f'CONTACT {k["contact"]} | SUPPORT {k["support"]} | CUSTODY {k["custody"]}',font=font,fill=(210,210,210))
        d.text((8,30),f'BASE_X {k["base_x"]:.1f} | LOCAL_ANCHOR +5 | FORCE {k["force_owner"]} | NORMAL {k["normal_force"]:.1f}',font=font,fill=(200,200,200))
        d.multiline_text((8,48),frame_ascii(k),font=font,fill=(248,248,248),spacing=0)
        im.save(F/f"f-{i:04d}.png")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(F/"f-%04d.png"),
                    "-c:v","libx264","-preset","veryslow","-crf","36","-pix_fmt","yuv420p","-movflags","+faststart",str(V)],check=True)
    return q,V.read_bytes()

def main():
    m=json.loads(M.read_text(encoding="utf-8"))
    q,v=render_video(m)
    m["motion_dungeon"]["media_sha256"]=hashlib.sha256(v).hexdigest()
    m["motion_dungeon"]["media_bytes"]=len(v)
    m["motion_dungeon"]["frames"]=len(q)
    M.write_text(json.dumps(m,separators=(",",":"),ensure_ascii=True),encoding="utf-8")
    a=contact_sheet(m); A.write_text(a,encoding="utf-8")
    S.write_text(spa(m,a,v),encoding="utf-8")
    print(json.dumps({"frames":len(q),"sha256":hashlib.sha256(v).hexdigest(),"bytes":len(v),"spa_bytes":S.stat().st_size},sort_keys=True))

if __name__=="__main__":
    main()
