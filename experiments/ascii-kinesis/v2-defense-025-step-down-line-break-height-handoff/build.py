#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, math, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
M=json.loads((ROOT/"motion.json").read_text(encoding="utf-8"))
W,H=M["rig"]["grid"]; T=M["rig"]["terrain"]; EDGE=T["edge_x"]; UPPER=T["upper_y"]; LOWER=T["lower_y"]
LINKS=M["rig"]["links"]; JOINTS=M["rig"]["joint_order"]
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"

def smooth(t): return t*t*(3-2*t)
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

def draw_terrain(g):
    for x in range(0,EDGE): g[LOWER][x]="_"
    for y in range(UPPER,LOWER+1): g[y][EDGE]="|"
    for x in range(EDGE,W): g[UPPER][x]="_"

def render_foot(g,name,pos,support):
    x,y=map(lambda z:int(round(z)),pos); st=support_state(name,support)
    if 0<=x<W and 0<=y<H:
        if "PROBE" in st: g[y][x]="?"
        elif "UNSUPPORTED" in st: g[y][x]="x"
        else: g[y][x]="o"
    if "FULL" in st:
        floor=LOWER if "LOWER" in st else UPPER
        for dx,ch in [(-2,"="),(-1,"="),(0,"#"),(1,"="),(2,"=")]:
            xx=x+dx
            if 0<=xx<W and 0<=floor<H:g[floor][xx]=ch
    elif "FOREFOOT" in st:
        floor=LOWER if "LOWER" in st else UPPER
        d=-1 if name=="foot_l" else 1
        for dx in (0,d,2*d):
            xx=x+dx
            if 0<=xx<W and 0<=floor<H:g[floor][xx]="^"

def draw(j,support,threat,guard,label=""):
    g=[[" "]*W for _ in range(H)]
    draw_terrain(g)
    if threat.get("active"):
        pts=bres(*threat["start"],*threat["end"])
        for x,y in pts:
            if 0<=x<W and 0<=y<H and g[y][x]==" ": g[y][x]=threat.get("glyph","-")
        ex,ey=map(lambda z:int(round(z)),threat["end"])
        if 0<=ex<W and 0<=ey<H:g[ey][ex]=threat.get("head","<")
    for a,b in LINKS:
        A=j[a]; B=j[b]; gl=glyph(A,B)
        for x,y in bres(*A,*B)[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ":g[y][x]=gl
    marks={"head":"O","neck":"o","shoulder_l":"o","shoulder_r":"o","elbow_l":"o","elbow_r":"o",
           "hand_l":"+","hand_r":"+","pelvis":"@","knee_l":"o","knee_r":"o"}
    for name,(x,y) in j.items():
        if name in ("foot_l","foot_r"): continue
        x=int(round(x)); y=int(round(y))
        if 0<=x<W and 0<=y<H:g[y][x]=marks.get(name,"o")
    render_foot(g,"foot_l",j["foot_l"],support); render_foot(g,"foot_r",j["foot_r"],support)
    if threat.get("active") and threat.get("relation") in ("THREAT_PASSES_ABOVE","HIGH_LINE_CONTINUES_PAST","THREAT_BEYOND_BODY"):
        hx,hy=map(lambda z:int(round(z)),j["head"]); ty=int(round(threat["end"][1]))
        if hy>ty+1 and 0<=hx<W:
            for yy in range(ty+1,hy):
                if 0<=yy<H and g[yy][hx]==" ": g[yy][hx]=":"
    if label:
        txt=(label+" | "+guard.get("relation",""))[:92].ljust(92)
        for i,ch in enumerate(txt):
            x=2+i
            if x<W-1:g[0][x]=ch
    return ["".join(r) for r in g]

def lp(a,b,e): return [a[0]+(b[0]-a[0])*e,a[1]+(b[1]-a[1])*e]
def interp_threat(a,b,e):
    if not a.get("active") or not b.get("active"): return dict(a)
    out=dict(a); out["start"]=lp(a["start"],b["start"],e); out["end"]=lp(a["end"],b["end"],e)
    return out

def interp(k0,k1,t):
    e=smooth(t); br=k0.get("bridge",{}); ra=br.get("root_arc",[0,0]); arcs=br.get("joint_arcs",{})
    j0=k0["pose_rig"]["joint_xy"]; j1=k1["pose_rig"]["joint_xy"]; out={}
    for name in JOINTS:
        p=lp(j0[name],j1[name],e)
        if name not in ("foot_l","foot_r"):
            p[0]+=math.sin(math.pi*t)*ra[0]*.35
            p[1]+=math.sin(math.pi*t)*ra[1]*.35
        if name in arcs:
            p[0]+=math.sin(math.pi*t)*arcs[name][0]
            p[1]+=math.sin(math.pi*t)*arcs[name][1]
        out[name]=p
    return out,k0["support_contact"],interp_threat(k0["threat_state"],k1["threat_state"],e),dict(k0["guard_state"])

def compile_frames():
    fs=[]; ks=M["keys"]
    for i,k in enumerate(ks):
        for _ in range(int(k["hold_frames"])):
            fs.append((k["pose_rig"]["joint_xy"],k["support_contact"],k["threat_state"],k["guard_state"],k["key_id"]+" "+k["name"]))
        if i<len(ks)-1:
            n=int(k.get("bridge",{}).get("frames",0))
            for bi in range(1,n+1):
                j,s,t,g=interp(k,ks[i+1],bi/(n+1))
                fs.append((j,s,t,g,k["key_id"]+">"+ks[i+1]["key_id"]))
    return fs

def support_short(support):
    out=[]
    for s in support:
        if s=="LEFT_UPPER_FULL":out.append("L U#")
        elif s=="RIGHT_UPPER_FULL":out.append("R U#")
        elif s=="LEFT_LOWER_FULL":out.append("L L#")
        elif s=="RIGHT_LOWER_FULL":out.append("R L#")
        elif s=="LEFT_LOWER_PROBE":out.append("L L?")
        elif s=="RIGHT_LOWER_PROBE":out.append("R L?")
        elif s=="LEFT_UPPER_FOREFOOT":out.append("L U^")
        elif s=="RIGHT_UPPER_FOREFOOT":out.append("R U^")
        elif s=="LEFT_UNSUPPORTED":out.append("L x")
        elif s=="RIGHT_UNSUPPORTED":out.append("R x")
        else:out.append(s)
    return "+".join(out)

def contact_sheet():
    out=[
      "ASCII KINESIS V2 DEFENSE025 — STEP-DOWN LINE BREAK / HEIGHT HANDOFF",
      "SOURCE EVIDENCE: TSR asset 81106 Bullwinkle — The Adventures of Rocky and Bullwinkle and Friends — NES; commissioned evidence artifact 1zQGdJx7uIqTnvJlHp2NfydUu_EDDNvt01tCAlQvlYQ8; whole 187x432 static PNG sheet inspected there.",
      "SOURCE ROLE: STYLE_REFERENCE. OBSERVED: separate Idle / Walking / Charge / Using Stairs families; static sheet provides no source-authentic decisive-key timing or exact support chronology.",
      "AUTHORED PRINCIPLE: LOWER-TREAD PROBE -> TRUSTWORTHY MIXED-HEIGHT CATCH -> EARNED ROOT DROP UNDER HIGH LINE -> UPPER SUPPORT RELEASE -> TRAILING LOWER CATCH -> COUNTER-RISE -> LATE GUARD REOPEN.",
      "TIMING: every decisive compile timing class INFERRED / STREET_FIGHTER-CAPCOM. ONES/TWOS/FOURS are cadence classes, never seconds.",
      "LEGEND: upper tread '_' at y29 right of riser | lower tread '_' at y32 left of riser | # full support | ^ forefoot | ? probe | x unsupported | @ pelvis | threat ----< | ':' visible clearance witness.",
      "RIGHTS: independent abstract ASCII rig only; no source pixels/palette/character contour/costume/face/antlers/layout/tracing/choreography/audio.",
      ""
    ]
    for k in M["keys"]:
        fr=draw(k["pose_rig"]["joint_xy"],k["support_contact"],k["threat_state"],k["guard_state"])
        out.extend([
            f"{k['key_id']} {k['name']} [{k['timing_class']}/INFERRED] SUPPORT={support_short(k['support_contact'])}",
            f"THREAT={k['threat_state']['relation']} | GUARD={k['guard_state']['relation']}",
            "ROOT: "+k["motion_arc_root_note"],
            "ROLE: "+k["causal_role"],
            *fr[1:35],
            ""
        ])
    return "\n".join(out).rstrip()+"\n"

def render_media():
    fs=compile_frames(); fd=ROOT/"_frames"; shutil.rmtree(fd,ignore_errors=True); fd.mkdir()
    font=ImageFont.truetype(FONT,12); small=ImageFont.truetype(FONT,10)
    for i,(j,s,t,g,label) in enumerate(fs):
        im=Image.new("RGB",(800,450),"black"); d=ImageDraw.Draw(im)
        d.multiline_text((8,3),"\n".join(draw(j,s,t,g,label)),font=font,fill="white",spacing=0)
        d.text((640,432),f"{i+1:03d}/{len(fs):03d}",font=small,fill="white")
        im.save(fd/f"{i:04d}.png",compress_level=9)
    out=ROOT/"step-down-line-break-height-handoff.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(fd/"%04d.png"),
                    "-c:v","libx264","-preset","veryslow","-crf","28","-pix_fmt","yuv420p",
                    "-movflags","+faststart","-map_metadata","-1",str(out)],check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(out),"-f","null","-"],check=True)
    return fs,out

def build_spa(ascii_text,video_path):
    raw_json=(ROOT/"motion.json").read_text(encoding="utf-8")
    pack=lambda txt:base64.b64encode(gzip.compress(txt.encode("utf-8"),mtime=0)).decode("ascii")
    ab64=pack(ascii_text); jb64=pack(raw_json); vb64=base64.b64encode(video_path.read_bytes()).decode("ascii")
    css='body{margin:0;background:#090909;color:#f2f2f2;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}nav{position:sticky;top:0;background:#111;padding:.7rem;display:flex;gap:.5rem;border-bottom:1px solid #444}button{font:inherit;background:#181818;color:#eee;border:1px solid #555;padding:.55rem .9rem}main{padding:1rem}.view{display:none}.view.active{display:block}pre{white-space:pre;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;line-height:1.05}video{max-width:100%;height:auto;background:#000}'
    js='const bs=[...document.querySelectorAll("[data-view]")],vs=[...document.querySelectorAll(".view")];bs.forEach(b=>b.onclick=()=>vs.forEach(v=>v.classList.toggle("active",v.id===b.dataset.view)));async function unpack(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0)),ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text()}Promise.all([unpack(document.body.dataset.a),unpack(document.body.dataset.j)]).then(([a,j])=>{document.getElementById("ap").textContent=a;document.getElementById("jp").textContent=JSON.stringify(JSON.parse(j),null,2)});'
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Defense025 — Step-Down Line Break / Height Handoff</title><style>'+css+'</style></head><body data-a="'+ab64+'" data-j="'+jb64+'"><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><main><section id="ascii" class="view active"><pre id="ap"></pre></section><section id="json" class="view"><pre id="jp"></pre></section><section id="video" class="view"><video controls loop playsinline src="data:video/mp4;base64,'+vb64+'"></video></section></main><script>'+js+'</script></body></html>'

def main():
    asc=contact_sheet(); (ROOT/"contact-sheet.txt").write_text(asc,encoding="utf-8")
    fs,out=render_media(); sha=hashlib.sha256(out.read_bytes()).hexdigest()
    declared=M.get("media",{})
    if declared.get("authoritative_sha256") not in (None,"PENDING",sha): raise SystemExit("MEDIA_IDENTITY_MISMATCH")
    if declared.get("authoritative_sha256")==sha:
        if int(declared.get("frames",-1))!=len(fs): raise SystemExit("frame count mismatch")
        if int(declared.get("bytes",-1))!=out.stat().st_size: raise SystemExit("media size mismatch")
    (ROOT/"step-down-line-break-height-handoff.motion.html").write_text(build_spa(asc,out),encoding="utf-8")
    print(json.dumps({"frames":len(fs),"bytes":out.stat().st_size,"sha256":sha,"decode":True},sort_keys=True))

if __name__=="__main__": main()
