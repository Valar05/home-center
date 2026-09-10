#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, html, json, tempfile
from pathlib import Path
import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION_PATH=HERE/"motion.json"
CONTACT_PATH=HERE/"contact-sheet.txt"
SPA_PATH=HERE/"tool-tip-plant-pivot-release-landing-debt.motion.html"

def hold_count(t): return {"ONES":1,"TWOS":2,"FOURS":4}[t]
def smooth(t): return t*t*(3.0-2.0*t)
def lerp(a,b,t): return a+(b-a)*t
def interp_point(a,b,t,arc_y=0.0):
    s=smooth(t)
    return {"x":lerp(a["x"],b["x"],s),"y":lerp(a["y"],b["y"],s)+4.0*arc_y*t*(1.0-t)}
def bresenham(x0,y0,x1,y1):
    x0,y0,x1,y1=map(lambda v:int(round(v)),(x0,y0,x1,y1))
    pts=[]; dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return pts
def segment_char(a,b):
    dx=b["x"]-a["x"]; dy=b["y"]-a["y"]
    if abs(dx)>abs(dy)*1.7: return "-"
    if abs(dy)>abs(dx)*1.7: return "|"
    return "\\" if dx*dy>=0 else "/"
def tool_char(a,b):
    dx=b["x"]-a["x"]; dy=b["y"]-a["y"]
    if abs(dx)>abs(dy)*1.7: return "="
    if abs(dy)>abs(dx)*1.7: return "!"
    return "\\" if dx*dy>=0 else "/"
def semantic_state(k):
    return {"root":dict(k["root"]),
            "joints":{n:dict(p) for n,p in k["joints"].items()},
            "support_contact":list(k["support_contact"]),
            "velocity_hint":k["velocity_hint"],
            "tool":{"butt":dict(k["tool"]["butt"]),"tip":dict(k["tool"]["tip"]),
                    "mode":k["tool"]["mode"],"custody":k["tool"]["custody"],"contact":k["tool"]["contact"]},
            "key_id":k["key_id"],"label":k["label"]}
def transition_state(a,b,t,arc_y):
    st={"root":interp_point(a["root"],b["root"],t,arc_y),"joints":{},
        "support_contact":list(a["support_contact"]),"velocity_hint":a["velocity_hint"],
        "tool":{"butt":interp_point(a["tool"]["butt"],b["tool"]["butt"],t,0.0),
                "tip":interp_point(a["tool"]["tip"],b["tool"]["tip"],t,0.0),
                "mode":a["tool"]["mode"],"custody":a["tool"]["custody"],"contact":a["tool"]["contact"]},
        "key_id":f'{a["key_id"]}->{b["key_id"]}',"label":a["label"]}
    for n in a["joints"]:
        st["joints"][n]=interp_point(a["joints"][n],b["joints"][n],t,arc_y*0.18)
    return st
def put(grid,x,y,s):
    x=int(round(x)); y=int(round(y))
    for i,ch in enumerate(s):
        xx=x+i
        if 0<=y<len(grid) and 0<=xx<len(grid[y]): grid[y][xx]=ch
def draw_line(grid,a,b,ch,overwrite=False):
    for x,y in bresenham(a[0],a[1],b[0],b[1]):
        if 0<=y<len(grid) and 0<=x<len(grid[y]) and (overwrite or grid[y][x]==" "):
            grid[y][x]=ch

def grid_for_state(motion,state):
    cols=motion["rig"]["grid"]["columns"]; rows=motion["rig"]["grid"]["rows"]; ground=motion["rig"]["grid"]["ground_y"]
    grid=[[" " for _ in range(cols)] for _ in range(rows)]
    for x in range(cols): grid[ground][x]="="
    ta=state["tool"]["butt"]; tb=state["tool"]["tip"]; tch=tool_char(ta,tb)
    draw_line(grid,(ta["x"],ta["y"]),(tb["x"],tb["y"]),tch)
    put(grid,ta["x"],ta["y"],"b")
    put(grid,tb["x"],tb["y"],"X" if "TOOL_TIP_GROUND" in state["support_contact"] else "*")
    pts={"root":state["root"],**state["joints"]}
    segments=[("head","neck"),("neck","root"),("neck","shoulder_l"),("shoulder_l","hand_l"),
              ("neck","shoulder_r"),("shoulder_r","hand_r"),("root","knee_l"),("knee_l","foot_l"),
              ("root","knee_r"),("knee_r","foot_r")]
    for an,bn in segments:
        a=pts[an]; b=pts[bn]; ch=segment_char(a,b)
        draw_line(grid,(a["x"],a["y"]),(b["x"],b["y"]),ch)
    put(grid,state["joints"]["head"]["x"],state["joints"]["head"]["y"],"O")
    put(grid,state["root"]["x"],state["root"]["y"],"@")
    for n in ("shoulder_l","shoulder_r","knee_l","knee_r"):
        p=state["joints"][n]; put(grid,p["x"],p["y"],"o")
    for n in ("hand_l","hand_r"):
        p=state["joints"][n]; put(grid,p["x"],p["y"],"h")
    supports=set(state["support_contact"])
    if "LEFT_FOOT" in supports:
        p=state["joints"]["foot_l"]; put(grid,p["x"],ground,"^")
    if "RIGHT_FOOT" in supports:
        p=state["joints"]["foot_r"]; put(grid,p["x"],ground,"^")
    put(grid,2,2,state["velocity_hint"])
    put(grid,2,4,"TOOL:"+state["tool"]["mode"])
    put(grid,2,5,"SUPPORT:"+(",".join(state["support_contact"]) or "NONE"))
    return ["".join(row).rstrip() for row in grid]

def contact_text(motion):
    out=[
      "ASCII KINESIS V2 - AIRBORNE039",
      "Primitive: "+motion["primitive"],
      "Experiment: "+motion["experiment_id"],
      "Source evidence: TSR 23976 / campaign artifact 1BW6UzsUckanhIqsAIcO6mWhc7FNCHGCX7A5tsdfO1EU",
      "Source timing: UNKNOWN | decisive timing: INFERRED / STREET_FIGHTER-CAPCOM",
      "Rights firewall: source pixels/art/audio absent; abstract ASCII rig only.",
      "Legend: O head | @ root | o joint | h hand | b pole butt | * free pole tip | X planted pole tip/support | ^ foot support",
      ""
    ]
    for k in motion["keys"]:
        out += [
          f'{k["key_id"]}  {k["label"]}',
          f'timing={k["timing_class"]} provenance={k["timing_provenance"]} support={",".join(k["support_contact"]) or "NONE"} tool={k["tool"]["mode"]} contact={k["tool"]["contact"]}',
          f'causal_role={k["causal_role"]}',
          f'root_note={k["motion_arc_root_note"]}'
        ]
        frame=grid_for_state(motion,semantic_state(k))
        marks=[]; ground=motion["rig"]["grid"]["ground_y"]
        for y,row in enumerate(frame):
            for x,ch in enumerate(row):
                if (y==ground and ch not in (" ","=")) or (y!=ground and ch!=" "):
                    marks.append((x,y))
        xs=[x for x,_ in marks]; ys=[y for _,y in marks]
        x0=max(0,min(xs)-2); x1=min(motion["rig"]["grid"]["columns"],max(xs)+3)
        y0=max(0,min(ys)-1); y1=min(len(frame),max(max(ys)+2,ground+1))
        for y in range(y0,y1):
            row=frame[y]
            if y==ground:
                local=list(row[x0:x1].ljust(x1-x0))
                for i,ch in enumerate(local):
                    if ch==" ": local[i]="="
                out.append("".join(local).rstrip())
            else:
                out.append(row[x0:x1].rstrip())
        out.append("")
    return "\n".join(out).rstrip()+"\n"

def all_states(motion):
    keys=motion["keys"]; trans={(t["from"],t["to"]):t for t in motion["transitions"]}; out=[]
    for i,k in enumerate(keys):
        s=semantic_state(k)
        for _ in range(hold_count(k["timing_class"])): out.append((s,k["key_id"],k["label"]))
        if i<len(keys)-1:
            b=keys[i+1]; tr=trans[(k["key_id"],b["key_id"])]
            for j in range(1,int(tr["frames"])+1):
                t=j/(int(tr["frames"])+1)
                out.append((transition_state(k,b,t,float(tr.get("root_arc",0.0))),k["key_id"],tr["curve"]))
    return out

def get_font(size=12):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
              "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"]:
        if Path(p).is_file(): return ImageFont.truetype(p,size=size)
    return ImageFont.load_default()

def render_mp4(motion,out_path):
    w=int(motion["compile"]["width"]); h=int(motion["compile"]["height"]); fps=int(motion["compile"]["fps"])
    font=get_font(12); headfont=get_font(13); states=all_states(motion)
    writer=imageio.get_writer(
        str(out_path), fps=fps, codec="libx264", format="FFMPEG",
        ffmpeg_log_level="error",
        output_params=["-preset","veryslow","-crf","28","-pix_fmt","yuv420p",
                       "-movflags","+faststart","-metadata","creation_time=1970-01-01T00:00:00Z"]
    )
    try:
        for state,kid,label in states:
            img=Image.new("RGB",(w,h),(8,10,12)); d=ImageDraw.Draw(img)
            d.text((12,8),f"AIRBORNE039  {kid}  {label}",font=headfont,fill=(235,237,240))
            d.text((12,25),"TOOL-TIP PLANT / PIVOT REDIRECT / EXPLICIT RELEASE / LANDING DEBT",
                   font=font,fill=(180,184,190))
            lines=grid_for_state(motion,state)
            x0=8; y0=44; line_h=7
            for rr,row_i in enumerate(range(0,min(52,len(lines)))):
                if y0+rr*line_h>=h: break
                d.text((x0,y0+rr*line_h),lines[row_i][0:122],font=font,fill=(238,238,238))
            writer.append_data(np.asarray(img))
    finally:
        writer.close()
    return len(states)

def make_spa(motion,ascii_text,mp4_bytes):
    js=json.dumps(motion,indent=2,ensure_ascii=False)+"\n"
    a=html.escape(ascii_text); j=html.escape(js); v=base64.b64encode(mp4_bytes).decode("ascii")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Airborne039 - Tool Tip Plant Pivot Release Landing Debt</title>
<style>
body{{margin:0;background:#0b0d10;color:#e8eaed;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}
nav{{position:sticky;top:0;background:#11151a;padding:10px;border-bottom:1px solid #444}}
button{{font:inherit;margin-right:8px;padding:8px 14px}}
section{{display:none;padding:14px}}section.active{{display:block}}
pre{{white-space:pre;overflow:auto;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;line-height:1.08}}
video{{display:block;max-width:100%;height:auto;background:#000}}
small{{color:#aab0b6}}
</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><h1>ASCII</h1><small>Complete literal aligned selectable decisive-key specimen.</small><pre>{a}</pre></section>
<section id="json"><h1>JSON</h1><small>Structured rig / timing / provenance / rights / lineage.</small><pre>{j}</pre></section>
<section id="video"><h1>VIDEO</h1><video controls loop muted playsinline src="data:video/mp4;base64,{v}"></video></section>
<script>
const bs=[...document.querySelectorAll('button[data-view]')], ss=[...document.querySelectorAll('section')];
for(const b of bs)b.addEventListener('click',()=>{{for(const s of ss)s.classList.toggle('active',s.id===b.dataset.view);}});
</script></body></html>'''

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--video-out"); args=ap.parse_args()
    motion=json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    ascii_text=contact_text(motion); CONTACT_PATH.write_text(ascii_text,encoding="utf-8")
    if args.video_out:
        out=Path(args.video_out); frames=render_mp4(motion,out)
        SPA_PATH.write_text(make_spa(motion,ascii_text,out.read_bytes()),encoding="utf-8")
    else:
        with tempfile.TemporaryDirectory() as td:
            mp4=Path(td)/"air039.mp4"; frames=render_mp4(motion,mp4)
            SPA_PATH.write_text(make_spa(motion,ascii_text,mp4.read_bytes()),encoding="utf-8")
    assert frames==int(motion["compile"]["frames"])
    print(json.dumps({"experiment_id":motion["experiment_id"],"frames":frames,
                      "contact_sha256":hashlib.sha256(CONTACT_PATH.read_bytes()).hexdigest(),
                      "spa_sha256":hashlib.sha256(SPA_PATH.read_bytes()).hexdigest(),
                      "video_out":args.video_out},sort_keys=True))
if __name__=="__main__":
    main()
