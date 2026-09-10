#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, html, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
MOTION_PATH = ROOT / "motion.json"
CONTACT_PATH = ROOT / "contact-sheet.txt"
VIDEO_PATH = ROOT / "rear-clearance-gates-commit-step-debt.mp4"
SPA_PATH = ROOT / "rear-clearance-gates-commit-step-debt.motion.html"
POINT_FIELDS = ["root","head","rear_hand","front_hand","rear_knee","front_knee","rear_foot","front_foot","rear_end","front_end"]

def bres(a,b):
    x0,y0=map(lambda v:int(round(v)),a); x1,y1=map(lambda v:int(round(v)),b)
    pts=[]; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return pts

def ascii_pose(k,m):
    grid=m["rig"]["grid"]; gw,gh=grid["width"],grid["height"]; gy=grid["ground_y"]; wx=grid["rear_wall_x"]; tx=grid["target_x"]
    g=[[" "]*gw for _ in range(gh)]
    def put(x,y,ch):
        x=int(round(x)); y=int(round(y))
        if 0<=x<gw and 0<=y<gh:g[y][x]=ch
    def line(a,b,ch):
        for x,y in bres(a,b): put(x,y,ch)
    for y in range(2,gy+1): put(wx,y,"#")
    for x in range(wx,gw-2): put(x,gy,"_")
    for y in range(7,gy+1): put(tx,y,"|")
    p=k["pose_rig"]; r=p["root"]; h=p["head"]; s=[round((r[0]+h[0])/2),max(h[1]+3,r[1]-3)]
    line(r,s,"|"); line(s,h,"|"); put(*h,"O")
    line(s,p["rear_hand"],"/"); line(s,p["front_hand"],"\\")
    line(r,p["rear_knee"],"/"); line(p["rear_knee"],p["rear_foot"],"/")
    line(r,p["front_knee"],"\\"); line(p["front_knee"],p["front_foot"],"\\")
    put(*p["rear_knee"],"o"); put(*p["front_knee"],"o")
    fm={"ACTIVE":"*","LIGHT":".","AIR":"^"}
    put(*p["rear_foot"],fm[k["rear_foot_state"]]); put(*p["front_foot"],fm[k["front_foot_state"]]); put(*r,"@")
    line(p["rear_end"],p["rear_hand"],"="); line(p["rear_hand"],p["front_hand"],"="); line(p["front_hand"],p["front_end"],"=")
    put(*p["rear_end"],"B"); put(*p["rear_hand"],"+"); put(*p["front_hand"],"+")
    put(*p["front_end"],"X" if k["contact"] in ("TARGET","TARGET_HOLD") else "T")
    rows=["".join(row).rstrip() for row in g]
    return "\n".join(rows[2:gy+1])

def make_contact(m):
    header=(
      "ASCII KINESIS V2 STRIKES025 — REAR CLEARANCE GATES COMMIT STEP DEBT\n"
      "Pocket rule: THE STRIKE OWES A STEP BEFORE IT OWES A THRUST. IF THE BUTT HAS NO REAR ROOM, ROOT SUPPORT MUST MOVE FIRST.\n"
      "Legend: # rear obstruction | | target | B staff butt | T staff tip | X target contact | + hands | O head | @ root | o knee | * active support | . light | ^ air | _ ground\n"
      "Source: STRIKES PASS 005 — VERIFIED | Home Center evidence 1BW6UzsUckanhIqsAIcO6mWhc7FNCHGCX7A5tsdfO1EU | TSR asset 23976 | Donatello — TMNT Tournament Fighters — SNES.\n"
      "Source roles: POSE_REFERENCE + CONTACT_REFERENCE. Timing authority=false. Source timing=UNKNOWN.\n"
      "OBSERVED: static long-weapon fighter sheet; front/rear staff volume; commissioned lifecycle proposes rear-occluded partial-cover follow-up testing root movement before coil.\n"
      "INFERRED: authored pose order, root/support clearance gate, contact/hit-stop implication, recoil, overshoot, secondary lag, recovery, all timing. Direction=STREET_FIGHTER/CAPCOM.\n"
      "Rights firewall: generic ASCII biped + line-segment staff only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/redistribution/close imitation.\n\n"
    )
    blocks=[]
    for k in m["keys"]:
        blocks.append(
          f"{k['key_id']} {k['name']} — timing={k['timing_class']} — provenance={k['timing_provenance']}\n"
          f"role={k['causal_role']} | support={k['support_contact']}\n"
          f"root_arc={k['motion_arc_root_note']} | clearance={k['clearance_note']}\n"
          + ascii_pose(k,m)
        )
    return header+"\n\n".join(blocks)+"\n"

def interp(a,b,t):
    e=t*t*(3-2*t); near=a if t<0.5 else b
    out={"pose_rig":{f:[a["pose_rig"][f][0]*(1-e)+b["pose_rig"][f][0]*e,
                         a["pose_rig"][f][1]*(1-e)+b["pose_rig"][f][1]*e] for f in POINT_FIELDS}}
    for f in ["key_id","name","rear_foot_state","front_foot_state","contact","support_contact","motion_arc_root_note","clearance_note","causal_role","timing_class","timing_provenance"]:
        out[f]=near[f]
    return out

def sequence(m):
    timing=m["compile"]["timing_frames"]; ov=m["compile"].get("hold_overrides",{})
    out=[]
    for i,k in enumerate(m["keys"]):
        out += [k]*ov.get(k["key_id"],timing[k["timing_class"]])
        if i<len(m["keys"])-1: out.append(interp(k,m["keys"][i+1],0.5))
    return out

def render(m):
    w,h,fps=m["compile"]["width"],m["compile"]["height"],m["compile"]["fps"]
    frames=ROOT/".frames"; shutil.rmtree(frames,ignore_errors=True); frames.mkdir()
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",10)
    font_big=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",14)
    seq=sequence(m)
    for idx,k in enumerate(seq):
        im=Image.new("RGB",(w,h),"#101216"); d=ImageDraw.Draw(im)
        d.text((14,10),"ASCII KINESIS / STRIKES025",font=font_big,fill="#f2f2f2")
        d.text((14,32),f"{k['key_id']} {k['name']}  {k['timing_class']}  {k['causal_role']}",font=font,fill="#e8e8e8")
        d.text((14,50),"DENIED COIL → CLEARING STEP → LEGAL COIL → CONTACT PIN → AXIAL WITHDRAW → DISPLACED READY",font=font,fill="#d0d0d0")
        d.multiline_text((14,76),ascii_pose(k,m),font=font,fill="#f5f5f5",spacing=0)
        d.text((14,h-42),f"SUPPORT: {k['support_contact']}",font=font,fill="#dedede")
        d.text((14,h-25),f"DEBT: {k['clearance_note'][:100]}",font=font,fill="#dedede")
        im.save(frames/f"{idx:04d}.png")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(fps),"-i",str(frames/"%04d.png"),
                    "-c:v","libx264","-preset","veryslow","-crf","45","-pix_fmt","yuv420p",str(VIDEO_PATH)],check=True)
    shutil.rmtree(frames)
    return seq

def make_spa(m, contact, media):
    js=json.dumps(m,indent=2,ensure_ascii=False)
    enc_ascii=base64.b64encode(gzip.compress(contact.encode("utf-8"))).decode("ascii")
    enc_json=base64.b64encode(gzip.compress(js.encode("utf-8"))).decode("ascii")
    vid=base64.b64encode(media).decode("ascii")
    return f"""<!doctype html><meta charset="utf-8"><title>ASCII Kinesis Strikes025</title>
<style>body{{font-family:system-ui;background:#101216;color:#eee;margin:0}}nav{{position:sticky;top:0;background:#181b20;padding:12px}}button{{margin-right:8px;padding:8px 14px}}section{{display:none;padding:14px}}section.on{{display:block}}pre{{white-space:pre;overflow:auto;font:12px/1.15 monospace;font-variant-ligatures:none}}video{{max-width:100%;height:auto}}</style>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="on"><pre></pre></section><section id="json"><pre></pre></section>
<section id="video"><video controls loop playsinline src="data:video/mp4;base64,{vid}"></video></section>
<script>
async function ungz(s){{let b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));let r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip')));return await r.text()}}
(async()=>{{document.querySelector('#ascii pre').textContent=await ungz('{enc_ascii}');document.querySelector('#json pre').textContent=await ungz('{enc_json}')}})();
for(const b of document.querySelectorAll('button[data-view]'))b.onclick=()=>{{document.querySelectorAll('section').forEach(s=>s.classList.remove('on'));document.getElementById(b.dataset.view).classList.add('on')}};
</script>"""

def main():
    m=json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    contact=make_contact(m); CONTACT_PATH.write_text(contact,encoding="utf-8")
    seq=render(m); media=VIDEO_PATH.read_bytes()
    sha=hashlib.sha256(media).hexdigest()
    m["compile"]["actual_frames"]=len(seq); m["compile"]["actual_media_bytes"]=len(media); m["compile"]["actual_media_sha256"]=sha
    MOTION_PATH.write_text(json.dumps(m,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    # regenerate contact is unchanged by compile facts; SPA uses final JSON
    SPA_PATH.write_text(make_spa(m,contact,media),encoding="utf-8")
    print(json.dumps({"video":VIDEO_PATH.name,"frames":len(seq),"bytes":len(media),"sha256":sha,"spa":SPA_PATH.name},sort_keys=True))

if __name__=="__main__": main()
