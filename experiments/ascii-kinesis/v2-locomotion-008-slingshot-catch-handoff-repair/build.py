#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import base64, gzip, hashlib, html, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
W,H,G=70,20,18
HOLD={"ONES":1,"TWOS":2,"FOURS":4}
FONT="/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
MP4="slingshot-catch-handoff-repair.mp4"
SPA="slingshot-catch-handoff-repair.motion.html"

def line(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; pts=[]
    while True:
        pts.append((x0,y0))
        if (x0,y0)==(x1,y1): return pts
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def pose_rows(k,bones,joint_order):
    grid=[[" "]*W for _ in range(H)]
    for x in range(W): grid[G][x]="."
    j={n:tuple(v) for n,v in zip(joint_order,k["pose"])} if "pose" in k else {n:tuple(v) for n,v in k["joints"].items()}
    for a,b in bones:
        p,q=j[a],j[b]; dx=q[0]-p[0]; dy=q[1]-p[1]
        ch="-" if abs(dx)>2*abs(dy) else ("|" if abs(dy)>2*abs(dx) else ("\\" if dx*dy>0 else "/"))
        for x,y in line(p,q)[1:-1]:
            if 0<=x<W and 0<=y<H and grid[y][x]==" ": grid[y][x]=ch
    special={"head":"O","chest":"#","pelvis":"@","l_hand":"*","r_hand":"*","l_foot":"*","r_foot":"*"}
    for n,(x,y) in j.items():
        ch=special.get(n,"o")
        if n=="r_foot" and k["support_contact"]=="RIGHT_FOOT_PROBE_CONTACT": ch="?"
        elif n=="r_foot" and k["support_contact"]=="RIGHT_FOOT_OWNS_ROOT": ch="!"
        elif n=="l_foot" and k["support_contact"] in {"LEFT_FOOT_OWNS_ROOT","LEFT_FOREFOOT_OWNS_ROOT","LEFT_TOE_OWNS_ROOT","LEFT_TOE_LAST_SUPPORT"}: ch="!"
        if 0<=x<W and 0<=y<H: grid[y][x]=ch
    return ["".join(r).rstrip() for r in grid]

def contact_sheet(keys,rows):
    parts=[]
    for k,rr in zip(keys,rows):
        pts=[(x,y) for y,row in enumerate(rr[:G]) for x,ch in enumerate(row) if ch!=" "]
        minx=max(0,min(x for x,y in pts)-1); maxx=min(W-1,max(x for x,y in pts)+1)
        miny=max(0,min(y for x,y in pts)-1); maxy=min(G,max(y for x,y in pts)+1)
        parts.append(f'{k["key_id"]} {k["name"]} | {k["key_role"]} | {k["timing_class"]} {k["timing_provenance"]} | {k["support_contact"]} | crop_origin=({minx},{miny})')
        parts.extend(r[minx:maxx+1].ljust(maxx-minx+1) for r in rr[miny:maxy+1]); parts.append("")
    return "\n".join(parts).rstrip()+"\n"

def build():
    motion=json.loads((HERE/"motion.json").read_text(encoding="utf-8"))
    keys=motion["keys"]; bones=[tuple(x) for x in motion["rig"]["bones"]]
    joint_order=motion["rig"].get("joint_order",[])
    rows=[pose_rows(k,bones,joint_order) for k in keys]
    sheet=contact_sheet(keys,rows)
    (HERE/"contact_sheet.txt").write_text(sheet,encoding="utf-8")
    work=HERE/".build-frames"; shutil.rmtree(work,ignore_errors=True); work.mkdir()
    font=ImageFont.truetype(FONT,18); small=ImageFont.truetype(FONT,14)
    idx=0
    for k,rr in zip(keys,rows):
        for _ in range(HOLD[k["timing_class"]]):
            im=Image.new("RGB",(640,360),"black"); d=ImageDraw.Draw(im)
            d.text((10,7),f'{k["key_id"]} {k["name"]}  {k["timing_class"]}  {k["support_contact"]}',font=small,fill="white")
            y=34
            for row in rr: d.text((10,y),row,font=font,fill="white"); y+=16
            im.save(work/f"{idx:04d}.png",optimize=True); idx+=1
    cmd=["ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(work/"%04d.png"),"-vf","scale=320:180","-c:v","libx264","-preset","veryslow","-crf","37","-pix_fmt","yuv420p","-movflags","+faststart",str(HERE/MP4)]
    subprocess.run(cmd,check=True); shutil.rmtree(work)
    media=(HERE/MP4).read_bytes(); sha=hashlib.sha256(media).hexdigest()
    expected=motion["motion_dungeon"]["media"]["sha256"]
    if expected!="PENDING" and sha!=expected: raise SystemExit(f"media hash mismatch {sha} != {expected}")
    motion_text=(HERE/"motion.json").read_text(encoding="utf-8")
    css="body{margin:0;background:#080a0e;color:#e8edf2;font-family:system-ui,sans-serif}header{padding:16px 20px;border-bottom:1px solid #303843}nav{display:flex;gap:8px;padding:12px 20px}button{padding:10px 18px;background:#141a22;color:#e8edf2;border:1px solid #3a4654;border-radius:8px}button.active{background:#243140}section{display:none;padding:0 20px 20px}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Consolas,'Liberation Mono',monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2;line-height:1.08}video{display:block;max-width:100%;width:100%;background:#000;border:1px solid #303843}small{color:#9ca9b6}"
    b64=base64.b64encode(media).decode("ascii")
    sheet_gz=base64.b64encode(gzip.compress(sheet.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    json_gz=base64.b64encode(gzip.compress(motion_text.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    boot=(
        "async function ungzip(id,b64){const u=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));"
        "const t=await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream('gzip'))).text();"
        "document.getElementById(id).textContent=t}"
        f"ungzip('ascii-pre','{sheet_gz}');ungzip('json-pre','{json_gz}');"
        "const bs=[...document.querySelectorAll('button[data-view]')],ss=[...document.querySelectorAll('section')];"
        "for(const b of bs)b.onclick=()=>{for(const x of bs)x.classList.toggle('active',x===b);for(const s of ss)s.classList.toggle('active',s.id===b.dataset.view)}"
    )
    page=('<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(motion["title"])+'</title><style>'+css+'</style></head><body><header><strong>'+html.escape(motion["title"])+'</strong><br><small>repair successor · no source art embedded · Motion Dungeon ASCII-rig media</small></header><nav><button data-view="ascii" class="active">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="ascii-pre"></pre></section><section id="json"><pre id="json-pre"></pre></section><section id="video"><video controls autoplay muted playsinline preload="metadata"><source src="data:video/mp4;base64,'+b64+'" type="video/mp4"></video></section><script>'+boot+'</script></body></html>')
    (HERE/SPA).write_text(page,encoding="utf-8")
    print(json.dumps({"entry":motion["id"],"frames":idx,"media_sha256":sha,"spa_sha256":hashlib.sha256(page.encode()).hexdigest(),"contact_sha256":hashlib.sha256(sheet.encode()).hexdigest()},sort_keys=True))
if __name__=="__main__": build()
