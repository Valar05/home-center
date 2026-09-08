#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

P = Path(__file__).resolve().parent
M = json.loads((P / "motion.json").read_text(encoding="utf-8"))
K = M["keys"]
FPS = M["timing"]["compile_fps"]
C, R, G = 48, 20, 18
CW, CH = 11, 19
PX = PY = 22
W = C * CW + 2 * PX
H = ((R + 3) * CH + 2 * PY + 1) // 2 * 2
ORDER = ["head","neck","root","le","lh","re","rh","lk","lf","rk","rf"]
BONES = [("head","neck"),("neck","root"),("neck","le"),("le","lh"),("neck","re"),("re","rh"),("root","lk"),("lk","lf"),("root","rk"),("rk","rf")]

def phase(s):
    return "air" if s.startswith("AIRBORNE") else ("prep" if ("LAST_SUPPORT" in s or "PEEL" in s) else "ground")

def sm(t):
    return t*t*(3-2*t)

def ij(a,b,t,n,p):
    q=sm(t)
    x=a[0]+(b[0]-a[0])*q
    y=a[1]+(b[1]-a[1])*q
    if n in {"lh","rh"}:
        y-=math.sin(math.pi*t)*(0.8 if p in {"air","prep"} else 0.4)
    elif n in {"lf","rf"} and p=="air":
        y-=math.sin(math.pi*t)*0.7
    return [round(x),round(y)]

def glyph(dx,dy):
    return "-" if abs(dx)>=abs(dy)*2 else ("|" if abs(dy)>=abs(dx)*2 else ("\\" if dx*dy>=0 else "/"))

def line(g,a,b):
    x0,y0=a; x1,y1=b
    dx=x1-x0; dy=y1-y0
    n=max(abs(dx),abs(dy),1); ch=glyph(dx,dy)
    for i in range(1,n):
        x=round(x0+dx*i/n); y=round(y0+dy*i/n)
        if 0<=x<C and 0<=y<R and g[y][x]==" ":
            g[y][x]=ch

def ascii_pose(j,s):
    g=[[" "]*C for _ in range(R)]
    for x in range(C): g[G][x]="_"
    for x in range(22,41,4): g[G][x]="."
    for a,b in BONES: line(g,j[a],j[b])
    for n,ch in {"head":"O","neck":"+","root":"@","le":"+","lh":"*","re":"+","rh":"*","lk":"+","lf":"L","rk":"+","rf":"R"}.items():
        x,y=j[n]
        if 0<=x<C and 0<=y<R: g[y][x]=ch
    if "LEFT" in s or "BOTH" in s:
        g[G][max(0,min(C-1,j["lf"][0]))]="L"
    if "RIGHT" in s or "BOTH" in s:
        g[G][max(0,min(C-1,j["rf"][0]))]="R"
    return "\n".join("".join(r).rstrip() for r in g)

def frames():
    out=[]; n=0
    for i,k in enumerate(K):
        j=k["pose_rig"]["joints"]
        for _ in range(k["compile_hold_frames"]):
            out.append((n,k["causal_role"],k["support"],j)); n+=1
        if i+1<len(K):
            z=K[i+1]; tr=k["travel_to_next_frames"]
            for q in range(1,tr+1):
                if k["causal_boundary_to_next"] or z["causal_boundary_to_next"] or k["support"]!=z["support"]:
                    jj=z["pose_rig"]["joints"]; s=z["support"]; role=z["causal_role"]
                else:
                    t=q/(tr+1); p=phase(k["support"])
                    jj={a:ij(j[a],z["pose_rig"]["joints"][a],t,a,p) for a in ORDER}
                    s=k["support"]; role=k["causal_role"]+" > "+z["causal_role"]
                out.append((n,role,s,jj)); n+=1
    return out

def render_mp4(out):
    fs=frames()
    fp=next((x for x in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf","/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"] if Path(x).exists()),None)
    font=ImageFont.truetype(fp,16) if fp else ImageFont.load_default()
    with tempfile.TemporaryDirectory() as td:
        d=Path(td)
        for no,role,s,j in fs:
            text=f"{no:03d}  {role[:34]:34}  {s[:28]}\n"+"-"*C+"\n"+ascii_pose(j,s)
            im=Image.new("RGB",(W,H),(8,8,8))
            ImageDraw.Draw(im).multiline_text((PX,PY),text,font=font,fill=(238,238,238),spacing=2)
            im.save(d/f"{no:04d}.png")
        subprocess.run(["ffmpeg","-hide_banner","-loglevel","error","-y","-framerate",str(FPS),"-i",str(d/"%04d.png"),"-an","-c:v","libx264","-pix_fmt","yuv420p","-profile:v","baseline","-level","3.0","-crf","28","-preset","veryslow","-movflags","+faststart",str(out)],check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(out),"-f","null","-"],check=True)
    return fs

def make_contact_sheet():
    blocks=[]
    for k in K:
        src=k.get("source_anchor")
        src_line=f"src {src['time_s']:.3f}s {src['provenance']}" if src else "src —"
        header=f"{k['key_id']} {k['causal_role']} | {k['timing_class']} / {k['timing_provenance']}\n{src_line}\nsupport {k['support']}"
        blocks.append(header+"\n\n"+ascii_pose(k["pose_rig"]["joints"],k["support"]))
    return M["title"]+"\n"+M["experiment_id"]+" | abstract ASCII rig only | source pixels/audio absent\n\n"+"\n\n".join(blocks)+"\n"

def media_probe(path):
    raw=subprocess.check_output(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames","-show_entries","format=duration,size","-of","json",str(path)],text=True)
    return json.loads(raw)

def write_products():
    mp4=P/"motion.mp4"
    fs=render_mp4(mp4)
    b=mp4.read_bytes()
    sha=hashlib.sha256(b).hexdigest()
    probe=media_probe(mp4)
    M["timing"]["total_frames"]=len(fs)
    M["media"]={"authoritative":"embedded_mp4_in_spa","tracked_mp4":False,"sha256":sha,"bytes":len(b),"probe":probe,"decode_verified":True,"derived_only_from_abstract_ascii_rig_and_timing":True}
    (P/"motion.json").write_text(json.dumps(M,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    contact=make_contact_sheet()
    (P/"contact_sheet.txt").write_text(contact,encoding="utf-8")
    manifest={
        "schema":"ascii-kinesis.swarm-entry.v2","format_version":2,
        "experiment_id":M["experiment_id"],"lane":"video-motion",
        "primary_tabs":["ASCII","JSON","VIDEO"],"ascii_literal_text":True,"video_required":True,
        "video_source":"abstract_ascii_rig_only","source_art_embedded":False,"source_audio_embedded":False,
        "backward_compatible":True,
        "revises":M["revision"]["revises"],"negative_fixture":M["revision"]["negative_fixture"],"source_change":False,
        "files":["build_motion.py","contact_sheet.txt","manifest.json","motion.json","receipt.json","ground-flip-support-release-repair.motion.html"],
        "media_sha256":sha,"media_embedded":True,"tracked_mp4":False,"deterministic_builder":"build_motion.py",
        "contract_test":{"script_blob_sha":"09f0bcf233dbb770ce6b6df047fe18d94be8aa7c","candidate_scoped":M.get("acceptance",{}).get("contract",{}).get("candidate_scoped","PENDING_CURRENT_WORKER"),"repo_global":M.get("acceptance",{}).get("contract",{}).get("repo_global","NOT_CLAIMED")}
    }
    (P/"manifest.json").write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    json_compact=json.dumps(M,ensure_ascii=False,separators=(",",":"))
    page=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Ground flip support release repair</title><style>:root{{color-scheme:dark;background:#080808;color:#eee;font-family:system-ui}}body{{margin:0}}nav{{position:sticky;top:0;background:#111;padding:.6rem;display:flex;gap:.5rem}}button{{background:#181818;color:#eee;border:1px solid #555;padding:.5rem .8rem}}section{{display:none;padding:1rem}}section.active{{display:block}}pre{{font-family:monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.2;font-size:12px}}video{{max-width:100%;height:auto;background:#000}}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="asciiText">{html.escape(contact)}</pre></section><section id="json"><pre id="jsonText"></pre></section><section id="video"><video controls loop playsinline src="data:video/mp4;base64,{base64.b64encode(b).decode("ascii")}"></video></section><script id="motionData" type="application/json">{json_compact}</script><script>const M=JSON.parse(document.getElementById('motionData').textContent);document.getElementById('jsonText').textContent=JSON.stringify(M,null,2);const btns=[...document.querySelectorAll('button[data-view]')];for(const b of btns)b.onclick=()=>{{for(const s of document.querySelectorAll('section'))s.classList.remove('active');document.getElementById(b.dataset.view).classList.add('active')}};</script></body></html>'''
    (P/"ground-flip-support-release-repair.motion.html").write_text(page,encoding="utf-8")
    return {"frames":len(fs),"bytes":len(b),"sha256":sha,"probe":probe,"spa_bytes":len(page.encode()),"contact_bytes":len(contact.encode())}

if __name__=="__main__":
    print(json.dumps(write_products(),sort_keys=True))
