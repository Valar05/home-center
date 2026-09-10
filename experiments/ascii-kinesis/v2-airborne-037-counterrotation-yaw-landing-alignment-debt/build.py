#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION_PATH = HERE / "motion.json"
CONTACT_PATH = HERE / "contact-sheet.txt"
MP4_PATH = HERE / "authoritative.mp4"
SPA_PATH = HERE / "counterrotation-yaw-landing-alignment-debt.motion.html"

def hold_count(timing: str) -> int:
    return {"ONES":1,"TWOS":2,"FOURS":4}[timing]

def smooth(t: float) -> float:
    return t*t*(3.0-2.0*t)

def lerp(a: float,b: float,t: float) -> float:
    return a+(b-a)*t

def interp_point(a,b,t,arc_y=0.0):
    s=smooth(t)
    return {"x":lerp(a["x"],b["x"],s),
            "y":lerp(a["y"],b["y"],s)+4.0*arc_y*t*(1.0-t)}

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

def yaw_tag(prefix,deg):
    if deg < -5: return prefix+"<"
    if deg > 5: return prefix+">"
    return prefix+"="

def semantic_state_from_key(k):
    return {
        "root":dict(k["root"]),
        "joints":{n:dict(p) for n,p in k["joints"].items()},
        "support_contact":list(k["support_contact"]),
        "upper_yaw_deg":float(k["upper_yaw_deg"]),
        "lower_yaw_deg":float(k["lower_yaw_deg"]),
        "velocity_hint":k["velocity_hint"],
        "key_id":k["key_id"],
        "label":k["label"],
    }

def transition_state(a,b,t,arc_y):
    st={
        "root":interp_point(a["root"],b["root"],t,arc_y),
        "joints":{},
        "support_contact":list(a["support_contact"]),
        "upper_yaw_deg":lerp(float(a["upper_yaw_deg"]),float(b["upper_yaw_deg"]),smooth(t)),
        "lower_yaw_deg":lerp(float(a["lower_yaw_deg"]),float(b["lower_yaw_deg"]),smooth(t)),
        "velocity_hint":a["velocity_hint"],
        "key_id":f'{a["key_id"]}->{b["key_id"]}',
        "label":a["label"],
    }
    for n in a["joints"]:
        st["joints"][n]=interp_point(a["joints"][n],b["joints"][n],t,arc_y*0.2)
    return st

def put(grid,x,y,s):
    x=int(round(x)); y=int(round(y))
    for i,ch in enumerate(s):
        xx=x+i
        if 0<=y<len(grid) and 0<=xx<len(grid[y]): grid[y][xx]=ch

def grid_for_state(motion,state):
    cols=motion["rig"]["grid"]["columns"]; rows=motion["rig"]["grid"]["rows"]
    ground=motion["rig"]["grid"]["ground_y"]
    grid=[[" " for _ in range(cols)] for _ in range(rows)]
    for x in range(cols): grid[ground][x]="="
    pts={"root":state["root"],**state["joints"]}
    segments=[
        ("head","neck"),("neck","root"),
        ("neck","shoulder_l"),("shoulder_l","hand_l"),
        ("neck","shoulder_r"),("shoulder_r","hand_r"),
        ("root","knee_l"),("knee_l","foot_l"),
        ("root","knee_r"),("knee_r","foot_r"),
    ]
    for a_name,b_name in segments:
        a=pts[a_name]; b=pts[b_name]; ch=segment_char(a,b)
        for x,y in bresenham(a["x"],a["y"],b["x"],b["y"]):
            if 0<=x<cols and 0<=y<rows and grid[y][x]==" ": grid[y][x]=ch
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
    put(grid,max(0,state["root"]["x"]-15),max(1,state["root"]["y"]-12),yaw_tag("U",state["upper_yaw_deg"]))
    put(grid,max(0,state["root"]["x"]-15),max(1,state["root"]["y"]+1),yaw_tag("L",state["lower_yaw_deg"]))
    put(grid,max(0,state["root"]["x"]-15),max(1,state["root"]["y"]+3),state["velocity_hint"])
    return ["".join(row).rstrip() for row in grid]

def all_states(motion):
    keys=motion["keys"]
    trans={(t["from"],t["to"]):t for t in motion["transitions"]}
    out=[]
    for i,k in enumerate(keys):
        s=semantic_state_from_key(k)
        for _ in range(hold_count(k["timing_class"])):
            out.append((s,k["key_id"],k["label"]))
        if i<len(keys)-1:
            b=keys[i+1]; tr=trans[(k["key_id"],b["key_id"])]
            n=int(tr["frames"])
            for j in range(1,n+1):
                t=j/(n+1)
                out.append((transition_state(k,b,t,float(tr.get("root_arc",0.0))),k["key_id"],tr["curve"]))
    return out

def contact_sheet_text(motion):
    blocks=[]
    for k in motion["keys"]:
        st=semantic_state_from_key(k); rows=grid_for_state(motion,st)
        nonempty=[i for i,r in enumerate(rows) if r.strip()]
        lo=max(0,min(nonempty)-1); hi=min(len(rows),max(nonempty)+2)
        blocks.append(
            f'{k["key_id"]}  {k["label"]}  {k["timing_class"]} / {k["timing_provenance"]}\n'
            f'ROLE: {k["causal_role"]}\n'
            f'SUPPORT: {",".join(k["support_contact"]) if k["support_contact"] else "NONE"} | '
            f'UPPER_YAW: {k["upper_yaw_deg"]:+.0f} | LOWER_YAW: {k["lower_yaw_deg"]:+.0f} | {k["velocity_hint"]}\n'
            f'ROOT: {k["motion_arc_root_note"]}\n'
            + "\n".join(rows[lo:hi]).rstrip()+"\n"
        )
    return (
        "ASCII KINESIS V2 - AIRBORNE037\n"
        "PRIMITIVE: AIRBORNE_COUNTERROTATION_YAW_LANDING_ALIGNMENT_DEBT\n"
        "SOURCE ART: NONE - abstract ASCII rig only\n"
        "READ ORDER: coiled axis bank -> support break -> unsupported upper/lower counterrotation -> apex orientation split -> landing-axis lock -> separated precontact -> right-toe yaw brake -> torsional crush -> delayed trail-foot catch -> rebound counterswing -> displaced restack\n"
        "LAW: FACING MAY CHANGE IN AIR WITHOUT ROOT DIRECTION CHANGING; SUPPORT MUST PAY HEADING/VELOCITY MISALIGNMENT.\n\n"
        + "\n".join(blocks)
    )

def get_font(size=14):
    candidates=[
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
    ]
    for p in candidates:
        if Path(p).is_file(): return ImageFont.truetype(p,size=size)
    return ImageFont.load_default()

def render_mp4(motion,out_path):
    w=int(motion["compile"]["width"]); h=int(motion["compile"]["height"]); fps=int(motion["compile"]["fps"])
    font=get_font(14); headfont=get_font(13)
    states=all_states(motion)
    with tempfile.TemporaryDirectory(prefix="a037_frames_") as td:
        td=Path(td)
        for i,(state,kid,label) in enumerate(states):
            img=Image.new("RGB",(w,h),(8,10,12)); d=ImageDraw.Draw(img)
            d.text((12,8),f"AIRBORNE037  {kid}  {label}",font=headfont,fill=(235,237,240))
            d.text((12,24),"COUNTERROTATION / YAW-LANDING ALIGNMENT / TORSIONAL DEBT",font=font,fill=(180,184,190))
            lines=grid_for_state(motion,state)
            view_x0,view_x1=3,103; view_y0,view_y1=5,49
            x0=8; y0=46; line_h=8
            for rr,row_i in enumerate(range(view_y0,min(view_y1,len(lines)))):
                if y0+rr*line_h>=h: break
                d.text((x0,y0+rr*line_h),lines[row_i][view_x0:view_x1],font=font,fill=(238,238,238))
            img.save(td/f"frame_{i:04d}.png",optimize=False)
        cmd=[
            "ffmpeg","-hide_banner","-loglevel","error","-y",
            "-framerate",str(fps),"-i",str(td/"frame_%04d.png"),
            "-c:v","libx264","-preset","veryslow","-crf","42","-pix_fmt","yuv420p",
            "-movflags","+faststart","-metadata","creation_time=1970-01-01T00:00:00Z",str(out_path)
        ]
        subprocess.run(cmd,check=True)
    return len(states)

def compact_gzip_b64(text: str) -> str:
    return base64.b64encode(gzip.compress(text.encode("utf-8"),mtime=0)).decode("ascii")

def make_spa(motion,ascii_text,mp4_bytes):
    js=json.dumps(motion,indent=2,ensure_ascii=False)
    a=compact_gzip_b64(ascii_text)
    j=compact_gzip_b64(js)
    v=base64.b64encode(mp4_bytes).decode("ascii")
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Airborne037 - Counterrotation Yaw Landing Alignment Debt</title><style>body{{margin:0;background:#0b0d10;color:#e8eaed;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}nav{{position:sticky;top:0;background:#11151a;padding:10px;border-bottom:1px solid #444}}button{{font:inherit;margin-right:8px;padding:8px 14px}}section{{display:none;padding:14px}}section.active{{display:block}}pre{{white-space:pre;overflow:auto;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;line-height:1.08}}video{{max-width:100%;height:auto;background:#000}}</style></head><body><nav><button data-view="ascii" onclick="show('ascii')">ASCII</button><button data-view="json" onclick="show('json')">JSON</button><button data-view="video" onclick="show('video')">VIDEO</button></nav><section id="ascii" class="active"><h1>ASCII</h1><pre id="asciipre"></pre></section><section id="json"><h1>JSON</h1><pre id="jsonpre"></pre></section><section id="video"><h1>VIDEO</h1><video id="v" controls loop playsinline src="data:video/mp4;base64,{v}"></video><p>Compiled solely from abstract ASCII rig + authored timing. No source pixels or audio.</p></section><script>const A="{a}",J="{j}";async function ungz(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).text()}}Promise.all([ungz(A),ungz(J)]).then(([a,j])=>{{document.getElementById('asciipre').textContent=a;document.getElementById('jsonpre').textContent=j}});function show(id){{document.querySelectorAll('section').forEach(s=>s.classList.remove('active'));document.getElementById(id).classList.add('active')}}</script></body></html>'''

def main():
    motion=json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    ascii_text=contact_sheet_text(motion)
    CONTACT_PATH.write_text(ascii_text,encoding="utf-8")
    frames=render_mp4(motion,MP4_PATH)
    media=MP4_PATH.read_bytes()
    SPA_PATH.write_text(make_spa(motion,ascii_text,media),encoding="utf-8")
    print(json.dumps({
        "frames":frames,
        "media_bytes":len(media),
        "media_sha256":hashlib.sha256(media).hexdigest(),
        "contact_sha256":hashlib.sha256(ascii_text.encode("utf-8")).hexdigest(),
        "spa_sha256":hashlib.sha256(SPA_PATH.read_bytes()).hexdigest()
    },sort_keys=True))

if __name__=="__main__":
    main()
