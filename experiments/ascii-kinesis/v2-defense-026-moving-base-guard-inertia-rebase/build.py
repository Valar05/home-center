#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,math,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parent
M=json.loads((ROOT/"motion.json").read_text(encoding="utf-8"))
W,H=M["rig"]["grid"]; LINKS=M["rig"]["links"]; JOINTS=M["rig"]["joint_order"]
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
PIN=M["rig"]["world"]["world_pin_x"]; DATUM=M["rig"]["world"]["datum_y"]

def smooth(t): return t*t*(3-2*t)
def lp(a,b,e): return [a[0]+(b[0]-a[0])*e,a[1]+(b[1]-a[1])*e]
def bres(x0,y0,x1,y1):
    x0,y0,x1,y1=map(lambda z:int(round(z)),(x0,y0,x1,y1)); out=[]
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        out.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return out
def glyph(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>=2*abs(dy): return "-"
    if abs(dy)>=2*abs(dx): return "|"
    return "\\" if dx*dy>0 else "/"

def support_state(name,support):
    p="LEFT" if name=="foot_l" else "RIGHT"
    vals=[s for s in support if s.startswith(p)]
    return vals[0] if vals else p+"_UNSUPPORTED"

def draw_world(g,base):
    x0,x1,y=map(lambda z:int(round(z)),base)
    for x in range(max(0,x0),min(W,x1+1)): g[y][x]="="
    if 0<=x0<W:g[y][x0]="["
    if 0<=x1<W:g[y][x1]="]"
    if 0<=DATUM<H:
        for x in range(W):
            if g[DATUM][x]==" ": g[DATUM][x]="."
    if 0<=PIN<W and 0<=DATUM<H:
        g[DATUM][PIN]="^"
        if DATUM-1>=0:g[DATUM-1][PIN]="|"

def render_foot(g,name,pos,support,base):
    x,y=map(lambda z:int(round(z)),pos); st=support_state(name,support)
    if 0<=x<W and 0<=y<H:
        g[y][x]="?" if "PROBE" in st else ("x" if "UNSUPPORTED" in st else "#")
    if ("FULL" in st or "FOREFOOT" in st) and 0<=int(round(base[2]))<H:
        by=int(round(base[2])); ch="#" if "FULL" in st else "^"
        for dx in (-1,0,1):
            xx=x+dx
            if 0<=xx<W:g[by][xx]=ch

def draw(j,support,base,threat,guard,label=""):
    g=[[" "]*W for _ in range(H)]
    draw_world(g,base)
    if threat.get("active"):
        for x,y in bres(*threat["start"],*threat["end"]):
            if 0<=x<W and 0<=y<H and g[y][x]==" ":g[y][x]=threat.get("glyph","-")
        ex,ey=map(lambda z:int(round(z)),threat["end"])
        if 0<=ex<W and 0<=ey<H:g[ey][ex]=threat.get("head","<")
    for a,b in LINKS:
        A=j[a]; B=j[b]; gl=glyph(A,B)
        for x,y in bres(*A,*B)[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ":g[y][x]=gl
    marks={"head":"O","neck":"o","shoulder_l":"o","shoulder_r":"o","elbow_l":"o","elbow_r":"o","hand_l":"+","hand_r":"+","pelvis":"@","knee_l":"o","knee_r":"o"}
    for n,(x,y) in j.items():
        if n in ("foot_l","foot_r"):continue
        x=int(round(x));y=int(round(y))
        if 0<=x<W and 0<=y<H:g[y][x]=marks.get(n,"o")
    render_foot(g,"foot_l",j["foot_l"],support,base);render_foot(g,"foot_r",j["foot_r"],support,base)
    txt=(label+" | "+guard.get("relation",""))[:92].ljust(92)
    for i,ch in enumerate(txt):
        x=2+i
        if x<W-1:g[0][x]=ch
    return ["".join(r) for r in g]

def interp(k0,k1,t):
    e=smooth(t); br=k0.get("bridge",{}); ra=br.get("root_arc",[0,0]); arcs=br.get("joint_arcs",{})
    j0=k0["pose_rig"]["joint_xy"]; j1=k1["pose_rig"]["joint_xy"]; out={}
    for n in JOINTS:
        p=lp(j0[n],j1[n],e)
        if n not in ("foot_l","foot_r"):
            p[0]+=math.sin(math.pi*t)*ra[0]*.35; p[1]+=math.sin(math.pi*t)*ra[1]*.35
        if n in arcs:
            p[0]+=math.sin(math.pi*t)*arcs[n][0];p[1]+=math.sin(math.pi*t)*arcs[n][1]
        out[n]=p
    b0=k0["base_state"]; b1=k1["base_state"]
    base=[b0["surface_x0"]+(b1["surface_x0"]-b0["surface_x0"])*e,
          b0["surface_x1"]+(b1["surface_x1"]-b0["surface_x1"])*e,
          b0["surface_y"]+(b1["surface_y"]-b0["surface_y"])*e]
    th=dict(k0["threat_state"])
    return out,k0["support_contact"],base,th,dict(k0["guard_state"])

def compile_frames():
    fs=[];ks=M["keys"]
    for i,k in enumerate(ks):
        base=[k["base_state"]["surface_x0"],k["base_state"]["surface_x1"],k["base_state"]["surface_y"]]
        for _ in range(int(k["hold_frames"])):
            fs.append((k["pose_rig"]["joint_xy"],k["support_contact"],base,k["threat_state"],k["guard_state"],k["key_id"]+" "+k["name"]))
        if i<len(ks)-1:
            n=int(k.get("bridge",{}).get("frames",0))
            for bi in range(1,n+1):
                j,s,b,t,g=interp(k,ks[i+1],bi/(n+1))
                fs.append((j,s,b,t,g,k["key_id"]+">"+ks[i+1]["key_id"]))
    return fs

def support_short(s):
    m={"LEFT_BASE_FULL":"L#","RIGHT_BASE_FULL":"R#","LEFT_BASE_FOREFOOT":"L^","RIGHT_BASE_FOREFOOT":"R^","LEFT_UNSUPPORTED":"Lx","RIGHT_UNSUPPORTED":"Rx"}
    return "+".join(m.get(x,x) for x in s)

def mini_frame(k):
    # Exact authored coordinates projected to a compact selectable audit view.
    mw,mh=48,17; g=[[" "]*mw for _ in range(mh)]
    def p(pt): return max(0,min(mw-1,int(round((pt[0]-20)*.55)))),max(0,min(mh-1,int(round((pt[1]-4)*.5))))
    b=k["base_state"]; x0,y0=p([b["surface_x0"],b["surface_y"]]);x1,_=p([b["surface_x1"],b["surface_y"]])
    for x in range(x0,x1+1):g[y0][x]="="
    g[y0][x0]="[";g[y0][x1]="]"
    _,dy=p([0,DATUM]);px,_=p([PIN,DATUM])
    if 0<=dy<mh:
        for x in range(mw):
            if g[dy][x]==" ":g[dy][x]="."
    if 0<=px<mw and 0<=dy<mh:g[dy][px]="^"
    th=k["threat_state"]
    if th.get("active"):
        a=p(th["start"]);z=p(th["end"])
        for x,y in bres(*a,*z):
            if 0<=x<mw and 0<=y<mh and g[y][x]==" ":g[y][x]="-"
        if 0<=z[0]<mw and 0<=z[1]<mh:g[z[1]][z[0]]="<"
    j={n:p(v) for n,v in k["pose_rig"]["joint_xy"].items()}
    for a,bn in LINKS:
        A=j[a];B=j[bn];gl=glyph(A,B)
        for x,y in bres(*A,*B)[1:-1]:
            if 0<=x<mw and 0<=y<mh and g[y][x]==" ":g[y][x]=gl
    marks={"head":"O","neck":"o","shoulder_l":"o","shoulder_r":"o","elbow_l":"o","elbow_r":"o","hand_l":"+","hand_r":"+","pelvis":"@","knee_l":"o","knee_r":"o"}
    for n,(x,y) in j.items():
        if n in ("foot_l","foot_r"):continue
        g[y][x]=marks.get(n,"o")
    for n in ("foot_l","foot_r"):
        x,y=j[n];st=support_state(n,k["support_contact"]);g[y][x]="x" if "UNSUPPORTED" in st else ("^" if "FOREFOOT" in st else "#")
    return ["".join(r).rstrip() for r in g]

def contact_sheet():
    out=[
      "ASCII KINESIS V2 DEFENSE026 — MOVING-BASE GUARD INERTIA / REBASE",
      "SOURCE: TSR asset 133611 Ride Armor — Mega Man X — SNES | commissioned evidence 13LNIYKD8DmWrc9trwiicS873bX-p-lku8QVNqdFk2Yc | whole 900x800 static sheet inspected.",
      "ROLE: STYLE_REFERENCE | timing authority=false | source timing UNKNOWN | authored timing INFERRED / STREET_FIGHTER-CAPCOM.",
      "PRINCIPLE: moving base owns lateral impulse -> body/guard inertial lag -> trailing pressure decays -> foot peel/sweep -> new base catch -> base brake/root overrun -> counter-torque -> late guard reopen.",
      "LEGEND: # trusted base support | ^ forefoot pressure | x unsupported | @ pelvis | O head | [====] moving base | ^ fixed world datum | <---- fixed threat bearing.",
      "RIGHTS: abstract ASCII only; no source pixels/palette/contours/costume/layout/tracing/choreography/audio/redistribution/close imitation.",
      ""
    ]
    for k in M["keys"]:
        out.extend([
          f"{k['key_id']} {k['name']} [{k['timing_class']}/{k['timing_provenance']}] SUPPORT={support_short(k['support_contact'])}",
          f"BASE=x{k['base_state']['surface_x0']}..{k['base_state']['surface_x1']} | THREAT={k['threat_state']['relation']} | GUARD={k['guard_state']['relation']}",
          "ROOT: "+k["motion_arc_root_note"],
          "ROLE: "+k["causal_role"],
          *mini_frame(k),""
        ])
    return "\n".join(out).rstrip()+"\n"

def render_media():
    fs=compile_frames();fd=ROOT/"_frames";shutil.rmtree(fd,ignore_errors=True);fd.mkdir()
    font=ImageFont.truetype(FONT,12);small=ImageFont.truetype(FONT,10)
    for i,(j,s,b,t,g,label) in enumerate(fs):
        im=Image.new("RGB",(800,450),"black");d=ImageDraw.Draw(im)
        d.multiline_text((8,3),"\n".join(draw(j,s,b,t,g,label)),font=font,fill="white",spacing=0)
        d.text((625,432),f"{i+1:03d}/{len(fs):03d} BASE[{int(round(b[0])):02d}]",font=small,fill="white")
        im.save(fd/f"{i:04d}.png",compress_level=9)
    out=ROOT/"moving-base-guard-inertia-rebase.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(fd/"%04d.png"),"-c:v","libx264","-preset","veryslow","-crf","28","-pix_fmt","yuv420p","-movflags","+faststart","-map_metadata","-1",str(out)],check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(out),"-f","null","-"],check=True)
    return fs,out

def build_spa(ascii_text,video_path):
    raw=(ROOT/"motion.json").read_text(encoding="utf-8")
    pack=lambda t:base64.b64encode(gzip.compress(t.encode("utf-8"),mtime=0)).decode("ascii")
    a=pack(ascii_text);j=pack(raw);v=base64.b64encode(video_path.read_bytes()).decode("ascii")
    css='body{margin:0;background:#090909;color:#f2f2f2;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}nav{position:sticky;top:0;background:#111;padding:.7rem;display:flex;gap:.5rem;border-bottom:1px solid #444}button{font:inherit;background:#181818;color:#eee;border:1px solid #555;padding:.55rem .9rem}main{padding:1rem}.view{display:none}.view.active{display:block}pre{white-space:pre;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;line-height:1.05}video{max-width:100%;height:auto;background:#000}'
    js='const bs=[...document.querySelectorAll("[data-view]")],vs=[...document.querySelectorAll(".view")];bs.forEach(b=>b.onclick=()=>vs.forEach(v=>v.classList.toggle("active",v.id===b.dataset.view)));async function unpack(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0)),ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text()}Promise.all([unpack(document.body.dataset.a),unpack(document.body.dataset.j)]).then(([a,j])=>{document.getElementById("ap").textContent=a;document.getElementById("jp").textContent=JSON.stringify(JSON.parse(j),null,2)});'
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Defense026 — Moving-Base Guard Inertia / Rebase</title><style>'+css+'</style></head><body data-a="'+a+'" data-j="'+j+'"><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><main><section id="ascii" class="view active"><pre id="ap"></pre></section><section id="json" class="view"><pre id="jp"></pre></section><section id="video" class="view"><video controls loop playsinline src="data:video/mp4;base64,'+v+'"></video></section></main><script>'+js+'</script></body></html>'

def main():
    asc=contact_sheet();(ROOT/"contact-sheet.txt").write_text(asc,encoding="utf-8")
    fs,out=render_media();sha=hashlib.sha256(out.read_bytes()).hexdigest()
    M["media"].update({"frames":len(fs),"bytes":out.stat().st_size,"authoritative_sha256":sha,"duration_seconds":len(fs)/24,"decode_verified":True})
    (ROOT/"motion.json").write_text(json.dumps(M,separators=(",",":"),ensure_ascii=False),encoding="utf-8")
    asc=contact_sheet();(ROOT/"contact-sheet.txt").write_text(asc,encoding="utf-8")
    (ROOT/"moving-base-guard-inertia-rebase.motion.html").write_text(build_spa(asc,out),encoding="utf-8")
    print(json.dumps({"frames":len(fs),"bytes":out.stat().st_size,"sha256":sha,"decode":True},sort_keys=True))

if __name__=="__main__":main()
