#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION_PATH=ROOT/"motion.json"
CONTACT_PATH=ROOT/"contact-sheet.txt"
VIDEO_PATH=ROOT/"deflection-rotates-return-corridor-debt.mp4"
SPA_PATH=ROOT/"deflection-rotates-return-corridor-debt.motion.html"
POINT_FIELDS=["root","head","rear_hand","front_hand","tool_butt","tool_head","rear_knee","front_knee","rear_foot","front_foot"]

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
    grid=m["rig"]["grid"]; gw,gh=grid["width"],grid["height"]; gy=grid["ground_y"]
    g=[[" "]*gw for _ in range(gh)]
    def put(x,y,ch):
        x=int(round(x)); y=int(round(y))
        if 0<=x<gw and 0<=y<gh: g[y][x]=ch
    def line(a,b,ch):
        for x,y in bres(a,b): put(x,y,ch)
    for x in range(2,gw-2): put(x,gy,"_")
    # synthetic diagonal deflector: evidence-independent test geometry
    for x,y in bres((53,6),(59,16)): put(x,y,":")
    p=k["pose_rig"]; r=p["root"]; h=p["head"]; sh=[round((r[0]+h[0])/2), max(h[1]+3,r[1]-3)]
    # body
    line(r,sh,"|"); line(sh,h,"|"); put(*h,"O"); put(*r,"@")
    line(sh,p["rear_hand"],"/"); line(sh,p["front_hand"],"\\")
    put(*p["rear_hand"],"r"); put(*p["front_hand"],"f")
    line(r,p["rear_knee"],"/"); line(p["rear_knee"],p["rear_foot"],"/")
    line(r,p["front_knee"],"\\"); line(p["front_knee"],p["front_foot"],"\\")
    put(*p["rear_knee"],"o"); put(*p["front_knee"],"o")
    fm={"ACTIVE":"#","LIGHT":".","AIR":"^"}
    put(*p["rear_foot"],fm[k["rear_foot_state"]]); put(*p["front_foot"],fm[k["front_foot_state"]])
    # hooked tool, drawn last so its rotation is unambiguous
    line(p["tool_butt"],p["tool_head"],"=")
    put(*p["tool_butt"],"<")
    put(*p["tool_head"],"X" if k["contact"].startswith("DEFLECTOR") else "J")
    return "\n".join("".join(row).rstrip() for row in g[2:gy+1])

def make_contact(m):
    header=(
      "ASCII KINESIS V2 STRIKES027 — DEFLECTION ROTATES RETURN CORRIDOR DEBT\n"
      "Pocket rule: CONTACT CAN ROTATE THE TOOL INTO A NEW RECOVERY PROBLEM. THE FEET MUST BUY A LEGAL RETURN CORRIDOR BEFORE THE HOOK CAN COME HOME.\n"
      "Legend: O head | @ root | r/f rear/front hand | o knee | < tool butt | J hooked tool head | X deflector contact | : synthetic deflector | # active support | . light | ^ air | _ ground\n"
      "Source: STRIKES PASS 007 — VERIFIED | Home Center evidence 1oG0Lk1WtECOXM-QrqxjwnqiyYKa4B3Xl84wNKke5QsE | TSR asset 215612 | Grim Reaper — Sword Master — NES — Enemies & Bosses.\n"
      "Source roles: TOOL_BODY_SEPARATION_REFERENCE + RETURN_CLEARANCE_REFERENCE + RECOVERY_DEBT_REFERENCE. Timing authority=false. Source timing=UNKNOWN.\n"
      "OBSERVED: complete 258x344 static source raster; long tool channel changes envelope while much lower-body/support mass remains comparatively stable; source page identifies axe/poleaxe family; sheet adjacency is not chronology.\n"
      "UNKNOWN: gameplay cell order/exposure/FPS/hit-stop/contact point/tool mass/root path/recovery identity.\n"
      "INFERRED: all authored poses, synthetic deflector, external shaft rotation, torque catch, corridor step, axial withdrawal, late rotation, regrip overshoot, secondary hand lag, displaced recovery, all timing. Direction=STREET_FIGHTER/CAPCOM.\n"
      "Rights firewall: generic ASCII biped + hooked tool + synthetic deflector only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/redistribution/close imitation.\n"
      "Lineage: NEW_CONCEPT | revises=null | negative_fixture=null | source_change=NOT_APPLICABLE_NEW_CONCEPT.\n\n"
    )
    blocks=[]
    for k in m["keys"]:
        blocks.append(
          f"{k['key_id']} {k['name']} — timing={k['timing_class']} — provenance={k['timing_provenance']}\n"
          f"role={k['causal_role']} | support={k['support_contact']} | contact={k['contact']}\n"
          f"root_arc={k['motion_arc_root_note']}\n"
          f"tool_arc={k['tool_arc_note']}\n"
          f"clearance={k['clearance_note']}\n"
          +ascii_pose(k,m)
        )
    return header+"\n\n".join(blocks)+"\n"

def interp(a,b,t):
    e=t*t*(3-2*t); near=a if t<0.5 else b
    out={"pose_rig":{f:[a["pose_rig"][f][0]*(1-e)+b["pose_rig"][f][0]*e,
                         a["pose_rig"][f][1]*(1-e)+b["pose_rig"][f][1]*e] for f in POINT_FIELDS}}
    for f in ["key_id","name","rear_foot_state","front_foot_state","contact","support_contact",
              "motion_arc_root_note","tool_arc_note","clearance_note","causal_role","timing_class","timing_provenance"]:
        out[f]=near[f]
    return out

def contact_group(v):
    return "DEFLECTOR" if v.startswith("DEFLECTOR") else v

def connector_safe(a,b):
    # Connect only when interpolation cannot invent support/contact state.
    return (
        a["rear_foot_state"]==b["rear_foot_state"]
        and a["front_foot_state"]==b["front_foot_state"]
        and contact_group(a["contact"])==contact_group(b["contact"])
    )

def sequence(m):
    timing=m["compile"]["timing_frames"]; ov=m["compile"].get("hold_overrides",{}); out=[]
    for i,k in enumerate(m["keys"]):
        out += [k]*ov.get(k["key_id"],timing[k["timing_class"]])
        if i<len(m["keys"])-1 and connector_safe(k,m["keys"][i+1]):
            out.append(interp(k,m["keys"][i+1],0.5))
    return out

def render(m):
    w,h,fps=m["compile"]["width"],m["compile"]["height"],m["compile"]["fps"]
    frames=ROOT/".frames"; shutil.rmtree(frames,ignore_errors=True); frames.mkdir()
    font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",10)
    font_big=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",14)
    seq=sequence(m)
    for idx,k in enumerate(seq):
        im=Image.new("RGB",(w,h),"#0f1115"); d=ImageDraw.Draw(im)
        d.text((14,10),"ASCII KINESIS / STRIKES027",font=font_big,fill="#f5f5f5")
        d.text((14,32),f"{k['key_id']} {k['name']}  {k['timing_class']}  {k['causal_role']}",font=font,fill="#eeeeee")
        d.text((14,49),"COIL → COMMIT → DEFLECT → ROOT OVERRUN → WRONG-SIDE RELEASE → CORRIDOR STEP → AXIAL CLEAR → LATE ROTATE → OVERSHOOT → DISPLACED READY",font=font,fill="#d5d5d5")
        d.multiline_text((14,72),ascii_pose(k,m),font=font,fill="#f4f4f4",spacing=0)
        d.text((14,h-58),f"SUPPORT: {k['support_contact'][:112]}",font=font,fill="#dedede")
        d.text((14,h-41),f"TOOL: {k['tool_arc_note'][:116]}",font=font,fill="#dedede")
        d.text((14,h-24),f"CLEAR: {k['clearance_note'][:114]}",font=font,fill="#dedede")
        im.save(frames/f"{idx:04d}.png")
    subprocess.run(["ffmpeg","-y","-loglevel","error","-framerate",str(fps),"-i",str(frames/"%04d.png"),
                    "-c:v","libx264","-preset","veryslow","-crf","42","-pix_fmt","yuv420p",str(VIDEO_PATH)],check=True)
    return seq

def make_spa(m,contact,media):
    js=json.dumps(m,indent=2,ensure_ascii=False)
    enc_ascii=base64.b64encode(gzip.compress(contact.encode("utf-8"))).decode("ascii")
    enc_json=base64.b64encode(gzip.compress(js.encode("utf-8"))).decode("ascii")
    vid=base64.b64encode(media).decode("ascii")
    return f"""<!doctype html><meta charset="utf-8"><title>ASCII Kinesis Strikes027</title>
<style>body{{font-family:system-ui;background:#0f1115;color:#eee;margin:0}}nav{{position:sticky;top:0;background:#181b20;padding:12px}}button{{margin-right:8px;padding:8px 14px}}section{{display:none;padding:14px}}section.on{{display:block}}pre{{white-space:pre;overflow:auto;font:12px/1.15 monospace;font-variant-ligatures:none}}video{{max-width:100%;height:auto}}</style>
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
    seq=render(m); media=VIDEO_PATH.read_bytes(); sha=hashlib.sha256(media).hexdigest()
    m["compile"]["actual_frames"]=len(seq); m["compile"]["actual_media_bytes"]=len(media); m["compile"]["actual_media_sha256"]=sha
    MOTION_PATH.write_text(json.dumps(m,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    SPA_PATH.write_text(make_spa(m,contact,media),encoding="utf-8")
    print(json.dumps({"video":VIDEO_PATH.name,"frames":len(seq),"bytes":len(media),"sha256":sha,"spa":SPA_PATH.name},sort_keys=True))

if __name__=="__main__": main()
