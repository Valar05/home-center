#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/"motion.json"
CONTACT=HERE/"contact-sheet.txt"
SPA=HERE/"curvature-sign-crossing-phase-continuity.motion.html"
MP4=HERE/"curvature-sign-crossing-phase-continuity.mp4"
FRAMES=Path(tempfile.mkdtemp(prefix="timing022-frames-"))
W,H=78,23

def line(c,x0,y0,x1,y1,ch):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<H and c[y0][x0]==" ": c[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def map_points(motion):
    xs=[float(k["root_transform"]["x"]) for k in motion["keys"]]
    ys=[float(k["root_transform"]["y"]) for k in motion["keys"]]
    xmin,xmax=min(xs),max(xs); ymin,ymax=min(ys),max(ys)
    pts=[]
    for x,y in zip(xs,ys):
        mx=53 + round((x-xmin)/(xmax-xmin or 1)*21)
        my=16 - round((y-ymin)/(ymax-ymin or 1)*10)
        pts.append((mx,my))
    return pts

def make_pose(k,motion):
    c=[[" "]*W for _ in range(H)]
    for x in range(3,49): c[19][x]="_"
    p={name:tuple(xy) for name,xy in k["joints"].items()}
    for a,b,ch in [
        ("head","neck","|"),("neck","pelvis","|"),
        ("neck","l_shoulder","-"),("neck","r_shoulder","-"),
        ("l_shoulder","l_elbow","/"),("l_elbow","l_hand","/"),
        ("r_shoulder","r_elbow","\\"),("r_elbow","r_hand","\\"),
        ("pelvis","l_knee","/"),("l_knee","l_foot","/"),
        ("pelvis","r_knee","\\"),("r_knee","r_foot","\\")]:
        line(c,*p[a],*p[b],ch)
    owner=k.get("support_owner","")
    glyphs={"head":"O","neck":"o","pelvis":"@","l_shoulder":"o","r_shoulder":"o",
            "l_elbow":"o","r_elbow":"o","l_hand":"o","r_hand":"o","l_knee":"o","r_knee":"o",
            "l_foot":"*" if owner=="LEFT" else "+",
            "r_foot":"*" if owner=="RIGHT" else "+"}
    for name,ch in glyphs.items():
        x,y=p[name]
        if 0<=x<W and 0<=y<H: c[y][x]=ch
    bank=int(k["bank_deg"])
    arrow=">" if k["root_transform"]["heading_deg"]>=-8 and k["root_transform"]["heading_deg"]<=8 else ("↗" if k["root_transform"]["heading_deg"]>8 else "↘")
    px,py=p["pelvis"]
    if px+2<W: c[py][px+2]=arrow
    for x in range(51,77):
        if 0<=18<H: c[18][x]="."
    pts=map_points(motion)
    for idx,(mx,my) in enumerate(pts):
        if 0<=mx<W and 0<=my<H:
            c[my][mx]="@" if motion["keys"][idx]["key_id"]==k["key_id"] else "+"
    label=f"S-CURVE ROOT | bank={bank:+d} | curv={k['curvature_state']}"
    for i,ch in enumerate(label[:26]):
        if 51+i<W: c[2][51+i]=ch
    return "\n".join("".join(row).rstrip() for row in c).rstrip()+"\n"

def contact_text(motion):
    out=[]
    for k in motion["keys"]:
        r=k["root_transform"]
        out.append(
            f"{k['key_id']} {k['causal_role']} {k['timing_class']}/{k['exposure_ticks']}t "
            f"PROV={k['timing_provenance']} GAIT={k['gait_phase']} OWNER={k['support_owner']} "
            f"CURV={k['curvature_state']} BANK={k['bank_deg']:+d} SPEED={k['speed_norm']:.1f} "
            f"ROOT=({r['x']:.1f},{r['y']:.1f}) HDG={r['heading_deg']:+d}\n"
        )
        bank=int(k["bank_deg"])
        shift=max(-2,min(2,round(bank/5)))
        head_pad=7+shift
        owner=k["support_owner"]
        left="*" if owner=="LEFT" else "+"
        right="*" if owner=="RIGHT" else "+"
        arrow=">" if -8<=r["heading_deg"]<=8 else ("^/" if r["heading_deg"]>8 else "\\v")
        out.extend([
            " "*head_pad+"O\n",
            " "*(head_pad-1)+"/|\\\n",
            "       @"+arrow+"\n",
            "      / \\\n",
            f"     {left}   {right}\n",
            f"  S: {k['curvature_state']:<14} bank {bank:+3d}\n",
            "  "+("-"*46)+"\n",
        ])
    return "".join(out)

def render_video(motion):
    FRAMES.mkdir(exist_ok=True)
    fp=Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    if not fp.exists(): raise SystemExit("DejaVuSansMono.ttf required")
    font=ImageFont.truetype(str(fp),12)
    footer=ImageFont.truetype(str(fp),10)
    n=0
    for k in motion["keys"]:
        pose=make_pose(k,motion)
        for _ in range(int(k["exposure_ticks"])):
            im=Image.new("RGB",(780,360),"white")
            d=ImageDraw.Draw(im)
            d.multiline_text((10,5),pose,fill="black",font=font,spacing=0)
            d.text((10,337),f"Timing022 | {k['key_id']} | {k['causal_role']} | {k['timing_class']} | gait clock CONTINUES",fill="black",font=footer)
            im.save(FRAMES/f"frame_{n:04d}.png"); n+=1
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-framerate","24","-i",str(FRAMES/"frame_%04d.png"),
        "-c:v","libx264","-pix_fmt","yuv420p","-movflags","+faststart","-crf","30",
        "-map_metadata","-1",str(MP4)
    ],check=True)
    return MP4.read_bytes()

def spa_text(contact,motion_raw,mp4):
    css="body{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}nav{display:flex;gap:.5rem;padding:.75rem;position:sticky;top:0;background:#111}button{padding:.6rem 1rem}section{display:none;padding:1rem}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto}"
    video_b64=base64.b64encode(mp4).decode("ascii")
    ascii_b64=base64.b64encode(gzip.compress(contact.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    json_b64=base64.b64encode(gzip.compress(motion_raw.encode("utf-8"),compresslevel=9,mtime=0)).decode("ascii")
    return '<!doctype html>\n<html><head><meta charset="utf-8"><title>Timing022 - Curvature Sign Crossing / Phase Continuity</title><style>'+css+'</style></head>\n<body>\n<nav>\n<button data-view="ascii" onclick="show(\'ascii\')">ASCII</button>\n<button data-view="json" onclick="show(\'json\')">JSON</button>\n<button data-view="video" onclick="show(\'video\')">VIDEO</button>\n</nav>\n<section id="ascii" class="active"><pre id="ascii-pre"></pre></section>\n<section id="json"><pre id="json-pre"></pre></section>\n<section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+video_b64+'"></video></section>\n<script>\nfunction show(id){for(const s of document.querySelectorAll(\'section\'))s.classList.remove(\'active\');document.getElementById(id).classList.add(\'active\');}\nasync function inflate64(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream(\'gzip\');return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}\nPromise.all([inflate64(\''+ascii_b64+'\'),inflate64(\''+json_b64+'\')]).then(([a,j])=>{document.getElementById(\'ascii-pre\').textContent=a;document.getElementById(\'json-pre\').textContent=j;});\n</script></body></html>\n'

def main():
    raw=MOTION.read_text(encoding="utf-8")
    motion=json.loads(raw)
    contact=contact_text(motion)
    CONTACT.write_text(contact,encoding="utf-8")
    mp4=render_video(motion)
    got=hashlib.sha256(mp4).hexdigest()
    media=motion["compile"]["media"]
    media["sha256"]=got
    media["bytes"]=len(mp4)
    raw=json.dumps(motion,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n"
    MOTION.write_text(raw,encoding="utf-8")
    SPA.write_text(spa_text(contact,raw,mp4),encoding="utf-8")
    print(json.dumps({"experiment_id":motion["experiment_id"],"frames":media["frames"],"media_sha256":got,"bytes":len(mp4),"ok":True},sort_keys=True))

if __name__=="__main__":
    main()
