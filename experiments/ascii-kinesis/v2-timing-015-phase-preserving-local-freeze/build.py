#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, shutil, subprocess
from pathlib import Path

HERE=Path(__file__).resolve().parent
MOTION=json.loads((HERE/"motion.json").read_text(encoding="utf-8"))
W=int(MOTION["rig"]["grid"]["columns"]); H=int(MOTION["rig"]["grid"]["rows"])
GROUND_Y=int(MOTION["rig"]["ground_y"])
OUT_W,OUT_H=map(int,MOTION["motion_dungeon"]["render_size"]); FPS=int(MOTION["motion_dungeon"]["fps"])
JOINT_KEYS=list(MOTION["rig"]["joints"])
CELL_W=CELL_H=8
GLYPHS={
" ":["00000"]*7,
"-":["00000","00000","00000","11111","00000","00000","00000"],
"|":["00100","00100","00100","00100","00100","00100","00100"],
"/":["00001","00010","00100","01000","10000","00000","00000"],
"\\":["10000","01000","00100","00010","00001","00000","00000"],
"+":["00100","00100","11111","00100","00100","00000","00000"],
"O":["01110","10001","10001","10001","10001","10001","01110"],
"@":["01110","10001","10111","10101","10111","10000","01111"],
"*":["00100","10101","01110","11111","01110","10101","00100"],
"_":["00000","00000","00000","00000","00000","00000","11111"],
"=":["00000","00000","11111","00000","11111","00000","00000"],
}
def line_cells(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return out
def seg_char(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>=2*abs(dy): return "-"
    if abs(dy)>=2*abs(dx): return "|"
    return "\\" if dx*dy>0 else "/"
def render_pose(p):
    g=[[" "]*W for _ in range(H)]
    for x in range(W): g[GROUND_Y][x]="="
    for akey,bkey in [("root","chest"),("ls","le"),("le","lh"),("rs","re"),("re","rh"),("root","lk"),("lk","lf"),("root","rk"),("rk","rf")]:
        a=tuple(round(v) for v in p[akey]); b=tuple(round(v) for v in p[bkey]); ch=seg_char(a,b)
        for x,y in line_cells(a,b)[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==" ": g[y][x]=ch
    for key,ch in [("head","O"),("root","@"),("chest","+"),("ls","+"),("rs","+"),("le","+"),("re","+"),("lk","+"),("rk","+"),("lh","*"),("rh","*"),("lf","_"),("rf","_")]:
        x,y=(round(v) for v in p[key])
        if 0<=x<W and 0<=y<H: g[y][x]=ch
    return "\n".join("".join(r) for r in g)
def contact_sheet():
    lines=[
        "TIMING015 - PHASE PRESERVING LOCAL FREEZE",
        "PAUSE THE LOCAL CLOCK, NOT THE WHOLE BODY. RESUME THE HELD PHASE; DO NOT CATCH UP.",
        "",
        "SOURCE EVIDENCE",
        "TSR asset 154244 - Tails - Sonic Advance 2 - GBA - evidence only",
        "Entire-sheet custody: 1544x1226 RGBA PNG | 349,461 bytes | sha256 e9a1219b5d267a790bb0431a0e61019f3849c9b92aafe564efcc7d26438765db",
        "Source-authentic timing: UNAVAILABLE. All decisive timing below is INFERRED / STREET_FIGHTER-CAPCOM.",
        "",
        "KEY LEDGER",
    ]
    for k in MOTION["keys"]:
        sc=k["support_contact"]; ch=k["channel_state"]
        lines.append(
            f'{k["key_id"]}  {k["causal_role"]:<27} class={k["timing_class"]:<5} hold={k["exposure_ticks"]:<2} '
            f'prov={k["timing_provenance"]:<8} support={sc["support"]:<14} '
            f'BASE={ch["base_state"]:<11} TASK={ch["task_state"]:<20} policy={ch["task_clock_policy"]}'
        )
    lines += ["","CONTACT SHEET",""]
    panels=[(f'{k["key_id"]} {k["causal_role"]}',render_pose(k["pose_rig"])) for k in MOTION["keys"]]
    for row in range(0,len(panels),2):
        pair=panels[row:row+2]; headers=[name[:W].ljust(W) for name,_ in pair]; bodies=[body.splitlines() for _,body in pair]
        if len(pair)==1: headers.append(" "*W); bodies.append([" "*W]*H)
        lines.append("  ".join(headers))
        for i in range(H): lines.append("  ".join(bodies[j][i] for j in range(2)))
        lines.append("")
    lines += [
        "FREEZE INVARIANT",
        "T015-K3 .. T015-K6 keep TASK state R3_FROZEN_HIGH_REAR and identical TASK local offsets while BASE/support changes.",
        "T015-K7 resumes R4_FORWARD_DROP: the next authored local phase. It does not catch up to wall time, restart at R0, quantize to a safe phase, or rebind BASE.",
    ]
    return "\n".join(lines).rstrip()+"\n"
def ease(t,c):
    if c=="ease_in": return t*t
    if c=="ease_out": return 1-(1-t)*(1-t)
    if c=="smooth": return t*t*(3-2*t)
    if c=="snap": return t**0.55
    if c=="compress": return 1-(1-t)**2.4
    return t
def validate_clock_invariant():
    ks={k["key_id"]:k for k in MOTION["keys"]}
    frozen=[ks[f"T015-K{i}"] for i in range(3,7)]
    states={k["channel_state"]["task_state"] for k in frozen}
    offsets={json.dumps(k["channel_state"]["task_local_offsets"],sort_keys=True) for k in frozen}
    bases={k["channel_state"]["base_state"] for k in frozen}
    if states!={"R3_FROZEN_HIGH_REAR"} or len(offsets)!=1 or len(bases)<4:
        raise SystemExit("phase-freeze invariant failed")
    if ks["T015-K7"]["channel_state"]["task_state"]!="R4_FORWARD_DROP":
        raise SystemExit("resume does not continue from next authored local phase")
def compile_frames():
    out=[]; keys=MOTION["keys"]
    for i,k in enumerate(keys):
        if i:
            prev=keys[i-1]; n=int(k["transition_frames"])
            for j in range(1,n+1):
                t=ease(j/(n+1),k["bridge_curve"]); p={}
                for name in JOINT_KEYS:
                    a=prev["pose_rig"][name]; b=k["pose_rig"][name]
                    p[name]=[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]
                out.append(render_pose(p))
        for _ in range(int(k["exposure_ticks"])): out.append(render_pose(k["pose_rig"]))
    return out
def raster_ascii(text):
    img=bytearray(OUT_W*OUT_H); xoff=(OUT_W-W*CELL_W)//2; yoff=(OUT_H-H*CELL_H)//2
    for gy,row in enumerate(text.splitlines()):
        for gx,ch in enumerate(row):
            pat=GLYPHS.get(ch,GLYPHS[" "]); ox=xoff+gx*CELL_W+(CELL_W-5)//2; oy=yoff+gy*CELL_H+(CELL_H-7)//2
            for py,bits in enumerate(pat):
                for px,bit in enumerate(bits):
                    if bit!="1": continue
                    x=ox+px; y=oy+py
                    if 0<=x<OUT_W and 0<=y<OUT_H: img[y*OUT_W+x]=255
    return bytes(img)
def render_mp4(frames):
    d=HERE/".motion-frames"
    if d.exists(): shutil.rmtree(d)
    d.mkdir()
    for i,text in enumerate(frames):
        (d/f"{i:04d}.pgm").write_bytes(f"P5\n{OUT_W} {OUT_H}\n255\n".encode("ascii")+raster_ascii(text))
    out=HERE/"phase-preserving-local-freeze.mp4"
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(FPS),"-i",str(d/"%04d.pgm"),"-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","42",str(out)],check=True)
    shutil.rmtree(d)
    return out
def build_spa(ascii_text,mp4):
    import gzip
    video=base64.b64encode(mp4.read_bytes()).decode("ascii")
    json_text=json.dumps(MOTION,sort_keys=True,ensure_ascii=True,separators=(",",":"))
    ascii_gz=base64.b64encode(gzip.compress(ascii_text.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    json_gz=base64.b64encode(gzip.compress(json_text.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    css=":root{color-scheme:dark;background:#080808;color:#f3f3f3;font-family:system-ui,sans-serif}body{margin:0;padding:1rem;max-width:100vw;overflow-x:hidden}nav{display:flex;gap:.5rem;position:sticky;top:0;background:#080808;padding:.5rem 0}button{font:inherit;padding:.55rem .9rem}section{display:none}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08}video{max-width:100%;height:auto;border:1px solid currentColor}"
    script=(
        "const z={a:'"+ascii_gz+"',j:'"+json_gz+"'};"
        "async function g(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).text()}"
        "Promise.all([g(z.a),g(z.j)]).then(([a,j])=>{document.getElementById('ap').textContent=a;document.getElementById('jp').textContent=j});"
        "const b=[...document.querySelectorAll('[data-view]')],s=[...document.querySelectorAll('main section')];function show(v){s.forEach(x=>x.classList.toggle('active',x.id===v))}b.forEach(x=>x.addEventListener('click',()=>show(x.dataset.view)));show('ascii');"
    )
    page=(
        "<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>Timing015 Phase Preserving Local Freeze</title><style>"+css+"</style></head><body>"
        "<nav><button data-view=\"ascii\">ASCII</button><button data-view=\"json\">JSON</button><button data-view=\"video\">VIDEO</button></nav><main>"
        "<section id=\"ascii\"><pre id=\"ap\"></pre></section>"
        "<section id=\"json\"><pre id=\"jp\"></pre></section>"
        "<section id=\"video\"><video controls loop muted playsinline src=\"data:video/mp4;base64,"+video+"\"></video></section>"
        "</main><script>"+script+"</script></body></html>"
    )
    out=HERE/"phase-preserving-local-freeze.motion.html"; out.write_text(page,encoding="utf-8"); return out

def main():
    validate_clock_invariant()
    ascii_text=contact_sheet(); (HERE/"contact-sheet.txt").write_text(ascii_text,encoding="ascii")
    frames=compile_frames()
    if len(frames)!=int(MOTION["motion_dungeon"]["frame_count"]): raise SystemExit(f"frame count mismatch {len(frames)}")
    mp4=render_mp4(frames); actual=hashlib.sha256(mp4.read_bytes()).hexdigest()
    if actual!=MOTION["media"]["sha256"]: raise SystemExit(f"media sha mismatch expected {MOTION['media']['sha256']} got {actual}")
    if len(mp4.read_bytes())!=int(MOTION["media"]["bytes"]): raise SystemExit("media byte count mismatch")
    build_spa(ascii_text,mp4)
    print(json.dumps({"frames":len(frames),"media_sha256":actual,"ok":True},sort_keys=True))
if __name__=="__main__": main()
