#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,html,json,os,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
SLUG="side-support-gates-second-impulse"
EDGES=[("head","neck"),("neck","shoulder_l"),("neck","shoulder_r"),("shoulder_l","elbow_l"),("elbow_l","hand_l"),("shoulder_r","elbow_r"),("elbow_r","hand_r"),("neck","pelvis"),("pelvis","knee_l"),("knee_l","foot_l"),("pelvis","knee_r"),("knee_r","foot_r")]
MARK={"head":"O","neck":"+","shoulder_l":"+","shoulder_r":"+","elbow_l":"o","elbow_r":"o","hand_l":"*","hand_r":"*","pelvis":"@","knee_l":"o","knee_r":"o","foot_l":"_","foot_r":"_"}
PREFIX=os.environ.get("PREFIX","")
FONTS=[Path(PREFIX)/"share/fonts/TTF/DejaVuSansMono.ttf",Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")]
BOLDS=[Path(PREFIX)/"share/fonts/TTF/DejaVuSansMono-Bold.ttf",Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")]
def first(ps):
    for p in ps:
        if p.is_file(): return str(p)
    raise SystemExit("missing DejaVu Sans Mono font")
FONT=first(FONTS); BOLD=first(BOLDS)
def line(a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);dy=-abs(y1-y0);sx=1 if x0<x1 else -1;sy=1 if y0<y1 else -1;err=dx+dy;o=[]
    while True:
        o.append((x0,y0))
        if (x0,y0)==(x1,y1): return o
        e=2*err
        if e>=dy: err+=dy;x0+=sx
        if e<=dx: err+=dx;y0+=sy
def glyph(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if abs(dx)>abs(dy)*1.5:return "-"
    if abs(dy)>abs(dx)*1.5:return "|"
    return "\\" if dx*dy>0 else "/"
def resolve_pose(s):
    cx=int(s["cx"]);cy=int(s["cy"]);mode=s.get("mode","neutral")
    p={"pelvis":[cx,cy],"neck":[cx,cy-5],"head":[cx,cy-7],"shoulder_l":[cx-2,cy-5],"shoulder_r":[cx+2,cy-5],"elbow_l":[cx-4,cy-3],"elbow_r":[cx+4,cy-3],"hand_l":[cx-5,cy-1],"hand_r":[cx+5,cy-1],"knee_l":[cx-2,cy+3],"knee_r":[cx+2,cy+3],"foot_l":[cx-3,cy+6],"foot_r":[cx+3,cy+6]}
    if mode=="load":
        p["head"][1]+=2;p["neck"][1]+=1;p["knee_l"]=[cx-3,cy+2];p["knee_r"]=[cx+3,cy+2];p["foot_l"]=[cx-5,cy+4];p["foot_r"]=[cx+5,cy+4];p["elbow_l"]=[cx-4,cy-2];p["elbow_r"]=[cx+4,cy-2]
    elif mode=="launch":
        p["hand_l"]=[cx-4,cy-7];p["hand_r"]=[cx+4,cy-7];p["knee_l"]=[cx-1,cy+3];p["knee_r"]=[cx+1,cy+3];p["foot_l"]=[cx-2,cy+6];p["foot_r"]=[cx+2,cy+6]
    elif mode=="tuck":
        p["elbow_l"]=[cx-4,cy-5];p["hand_l"]=[cx-5,cy-3];p["elbow_r"]=[cx+4,cy-5];p["hand_r"]=[cx+5,cy-3];p["knee_l"]=[cx-3,cy+1];p["knee_r"]=[cx+3,cy+1];p["foot_l"]=[cx-4,cy+3];p["foot_r"]=[cx+4,cy+3]
    elif mode=="side_approach":
        p["shoulder_r"]=[cx+3,cy-5];p["elbow_r"]=[cx+6,cy-4];p["hand_r"]=[cx+8,cy-4];p["knee_l"]=[cx-3,cy+2];p["foot_l"]=[cx-5,cy+4];p["knee_r"]=[cx+1,cy+3];p["foot_r"]=[cx+2,cy+5]
    elif mode=="side_contact":
        p["hand_r"]=[cx+9,cy-4];p["elbow_r"]=[cx+6,cy-4];p["foot_r"]=[cx+9,cy+4];p["knee_r"]=[cx+5,cy+2];p["knee_l"]=[cx-2,cy+2];p["foot_l"]=[cx-4,cy+4]
    elif mode=="side_load":
        p["head"][1]+=1;p["neck"][1]+=1;p["hand_r"]=[cx+9,cy-3];p["elbow_r"]=[cx+6,cy-3];p["foot_r"]=[cx+9,cy+4];p["knee_r"]=[cx+5,cy+2];p["knee_l"]=[cx-3,cy+1];p["foot_l"]=[cx-5,cy+3];p["hand_l"]=[cx-5,cy-5]
    elif mode=="side_release":
        p["hand_r"]=[cx+5,cy-7];p["hand_l"]=[cx-5,cy-7];p["foot_r"]=[cx+2,cy+6];p["foot_l"]=[cx-2,cy+6]
    elif mode=="open":
        p["hand_l"]=[cx-7,cy-3];p["hand_r"]=[cx+7,cy-3];p["foot_l"]=[cx-5,cy+6];p["foot_r"]=[cx+5,cy+6]
    elif mode=="precontact":
        p["hand_l"]=[cx-6,cy-1];p["hand_r"]=[cx+6,cy-1];p["knee_l"]=[cx-3,cy+3];p["knee_r"]=[cx+3,cy+3];p["foot_l"]=[cx-5,cy+6];p["foot_r"]=[cx+5,cy+6]
    elif mode=="compression":
        p["head"][1]+=2;p["neck"][1]+=1;p["knee_l"]=[cx-4,cy+2];p["knee_r"]=[cx+4,cy+2];p["foot_l"]=[cx-6,cy+4];p["foot_r"]=[cx+6,cy+4];p["hand_l"]=[cx-6,cy-2];p["hand_r"]=[cx+6,cy-2]
    elif mode=="rebound":
        p["head"][1]-=1;p["neck"][1]-=1;p["hand_l"]=[cx-5,cy-5];p["hand_r"]=[cx+5,cy-5]
    return p
def pose_text(p,label,support,phase):
    W,H=64,24;g=[[" "]*W for _ in range(H)]
    for x in range(W):g[21][x]="."
    if support=="SIDE":
        for y in range(1,22): g[y][44]="|"
    for a,b in EDGES:
        pa=tuple(p[a]);pb=tuple(p[b]);c=glyph(pa,pb)
        for x,y in line(pa,pb)[1:-1]:
            if 0<=x<W and 0<=y<H:g[y][x]=c
    for j,(x,y) in p.items():
        if 0<=x<W and 0<=y<H:g[y][x]=MARK[j]
    hx,hy=p["head"]
    if hx+2<W:g[hy][hx+2]=">"
    return f"{label} | {phase} | support={support}\n"+"\n".join("".join(r).rstrip() for r in g)
def midpoint(a,b):return {j:[round((a[j][0]+b[j][0])/2),round((a[j][1]+b[j][1])/2)] for j in a}
def exposure(t):return {"ONES":1,"TWOS":2,"FOURS":4}[t]
def sequence(m):
    out=[];ks=m["keys"]
    for i,k in enumerate(ks):
        for _ in range(exposure(k["timing_class"])):out.append((resolve_pose(k["pose_rig"]),k["name"],k["support_contact"],k["vertical_phase"],"HOLD"))
        if i+1<len(ks):
            n=ks[i+1]
            if k["support_contact"]==n["support_contact"] and k["contact_state"]==n["contact_state"]:
                out.append((midpoint(resolve_pose(k["pose_rig"]),resolve_pose(n["pose_rig"])),k["name"]+" -> "+n["name"],k["support_contact"],k["vertical_phase"]+"~"+n["vertical_phase"],"CONNECT"))
    return out
def sheet(m):
    o=["ASCII KINESIS V2 — AIRBORNE 005 — SIDE SUPPORT GATES SECOND IMPULSE",m["principle"],"Independent generic ASCII rig; no source pixels, palette, contours, costume, or sheet layout.","ONES/TWOS/FOURS are timing classes, never seconds.","All decisive timing: INFERRED / STREET_FIGHTER-CAPCOM.",""]
    for k in m["keys"]:
        o+=["="*64,f'{k["key_id"]}  {k["name"]}  timing={k["timing_class"]}  provenance={k["timing_provenance"]}',"role: "+k["causal_role"],"root: "+k["motion_arc_root_note"],pose_text(resolve_pose(k["pose_rig"]),k["name"],k["support_contact"],k["vertical_phase"]),""]
    return "\n".join(o).rstrip()+"\n"
def render_video(m):
    seq=sequence(m);allf=seq*m["compile"]["loop_repetitions"];d=HERE/"_frames";d.mkdir(exist_ok=True)
    for p in d.glob("*.png"):p.unlink()
    f=ImageFont.truetype(FONT,9);fb=ImageFont.truetype(BOLD,11)
    for i,(pose,label,support,phase,kind) in enumerate(allf):
        text=pose_text(pose,label,support,phase)
        im=Image.new("RGB",(480,270),(18,18,18));dr=ImageDraw.Draw(im)
        dr.text((16,10),"ASCII KINESIS / AIRBORNE 005",font=fb,fill=(238,238,238))
        dr.text((16,31),f"{label} [{kind}] support={support}",font=f,fill=(220,220,220))
        dr.multiline_text((16,50),text,font=f,fill=(238,238,238),spacing=1)
        dr.text((16,254),f"frame {i+1}/{len(allf)}",font=f,fill=(180,180,180));im.save(d/f"{i:05d}.png")
    out=HERE/(SLUG+".mp4")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(m["compile"]["fps"]),"-i",str(d/"%05d.png"),"-c:v","libx264","-pix_fmt","yuv420p","-crf","40","-preset","slow","-movflags","+faststart",str(out)],check=True)
    shutil.rmtree(d,ignore_errors=True);return out,len(seq),len(allf)
def make_html(m,man,a,vb):
    payload=json.dumps({"motion":m,"manifest":man},indent=2,sort_keys=True);b64=base64.b64encode(vb).decode()
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 — Airborne 005 — Side Support Gates Second Impulse</title><style>body{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}nav{display:flex;gap:.5rem;padding:1rem;position:sticky;top:0;background:#111}.view{display:none;padding:1rem}.view.active{display:block}pre{white-space:pre;font-family:monospace;font-variant-ligatures:none;overflow:auto;line-height:1.08}video{max-width:100%;height:auto}</style></head><body><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav><section id="ascii" class="view active"><pre>'+html.escape(a)+'</pre></section><section id="json" class="view"><pre>'+html.escape(payload)+'</pre></section><section id="video" class="view"><video controls loop playsinline src="data:video/mp4;base64,'+b64+'"></video></section><script>const b=[...document.querySelectorAll("nav button")],v=[...document.querySelectorAll(".view")];for(const x of b)x.onclick=()=>{for(const y of b)y.setAttribute("aria-selected",String(x===y));for(const z of v)z.classList.toggle("active",z.id===x.dataset.view)}</script></body></html>'
def main():
    m=json.loads((HERE/"motion.json").read_text());man=json.loads((HERE/"manifest.json").read_text());a=sheet(m)
    mp4,n,total=render_video(m);vb=mp4.read_bytes();sha=hashlib.sha256(vb).hexdigest();ash=hashlib.sha256(a.encode()).hexdigest()
    m["compile"]["media_sha256"]=sha;m["compile"]["media_bytes"]=len(vb);m["compile"]["semantic_frames_per_loop"]=n;m["compile"]["video_frames_total"]=total;m["ascii_sheet_sha256"]=ash
    man["media_sha256"]=sha;man["media_bytes"]=len(vb);man["ascii_sheet_sha256"]=ash;man["motion_dungeon"]["semantic_frames_per_loop"]=n;man["motion_dungeon"]["video_frames_total"]=total
    (HERE/"motion.json").write_text(json.dumps(m,indent=2,sort_keys=True)+"\n",encoding="utf-8");(HERE/"manifest.json").write_text(json.dumps(man,indent=2,sort_keys=True)+"\n",encoding="utf-8");(HERE/(SLUG+".motion.html")).write_text(make_html(m,man,a,vb),encoding="utf-8")
    print(json.dumps({"ok":True,"ascii_sheet_sha256":ash,"media_sha256":sha,"media_bytes":len(vb),"semantic_frames_per_loop":n,"video_frames_total":total},sort_keys=True))
if __name__=="__main__":main()
