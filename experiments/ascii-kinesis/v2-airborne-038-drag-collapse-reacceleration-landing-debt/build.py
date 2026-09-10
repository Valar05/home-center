#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, tempfile
import imageio.v2 as imageio
import numpy as np
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION_PATH=HERE/"motion.json"
CONTACT_PATH=HERE/"contact-sheet.txt"
SPA_PATH=HERE/"drag-collapse-reacceleration-landing-debt.motion.html"

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
def semantic_state(k):
    return {"root":dict(k["root"]),"joints":{n:dict(p) for n,p in k["joints"].items()},
            "support_contact":list(k["support_contact"]),"velocity_hint":k["velocity_hint"],
            "drag_surface":dict(k["drag_surface"]),"key_id":k["key_id"],"label":k["label"]}
def transition_state(a,b,t,arc_y):
    st={"root":interp_point(a["root"],b["root"],t,arc_y),"joints":{},
        "support_contact":list(a["support_contact"]),"velocity_hint":a["velocity_hint"],
        "drag_surface":dict(a["drag_surface"]),"key_id":f'{a["key_id"]}->{b["key_id"]}',"label":a["label"]}
    for n in a["joints"]:
        st["joints"][n]=interp_point(a["joints"][n],b["joints"][n],t,arc_y*0.2)
    return st
def put(grid,x,y,s):
    x=int(round(x)); y=int(round(y))
    for i,ch in enumerate(s):
        xx=x+i
        if 0<=y<len(grid) and 0<=xx<len(grid[y]): grid[y][xx]=ch
def draw_line(grid,a,b,ch):
    for x,y in bresenham(a[0],a[1],b[0],b[1]):
        if 0<=y<len(grid) and 0<=x<len(grid[y]) and grid[y][x]==" ": grid[y][x]=ch

def draw_drag(grid,state):
    d=state["drag_surface"]; mode=d["mode"]
    if mode=="STOWED": return
    cx=int(round(state["root"]["x"]+d["center_dx"]))
    top=int(round(state["root"]["y"]+d["top_dy"]))
    span=int(d["span"])
    if mode=="DEPLOYING":
        left=cx-span//2; right=cx+span//2
        put(grid,left,top,"~"*max(3,span))
        draw_line(grid,(left,top),(state["joints"]["shoulder_l"]["x"],state["joints"]["shoulder_l"]["y"]),":")
        draw_line(grid,(right,top),(state["joints"]["shoulder_r"]["x"],state["joints"]["shoulder_r"]["y"]),":")
    elif mode=="CAPTURED":
        left=cx-span//2; right=cx+span//2
        put(grid,left,top,"~"*span)
        put(grid,left+2,top-1,"/" + "_"*max(1,span-6) + "\\")
        draw_line(grid,(left+2,top),(state["joints"]["shoulder_l"]["x"],state["joints"]["shoulder_l"]["y"]),":")
        draw_line(grid,(right-2,top),(state["joints"]["shoulder_r"]["x"],state["joints"]["shoulder_r"]["y"]),":")
    elif mode=="COLLAPSING":
        left=cx-span//2
        put(grid,left,top,"~"*span)
        put(grid,cx,top+1,"\\~")
        draw_line(grid,(cx-2,top),(state["joints"]["shoulder_l"]["x"],state["joints"]["shoulder_l"]["y"]),":")
        draw_line(grid,(cx+2,top),(state["joints"]["shoulder_r"]["x"],state["joints"]["shoulder_r"]["y"]),":")
    elif mode=="COLLAPSED":
        put(grid,cx,top,"~~~")
        put(grid,cx+1,top+1,"~")
        draw_line(grid,(cx+1,top+1),(state["joints"]["shoulder_l"]["x"],state["joints"]["shoulder_l"]["y"]),":")
        draw_line(grid,(cx+2,top+1),(state["joints"]["shoulder_r"]["x"],state["joints"]["shoulder_r"]["y"]),":")

def grid_for_state(motion,state):
    cols=motion["rig"]["grid"]["columns"]; rows=motion["rig"]["grid"]["rows"]; ground=motion["rig"]["grid"]["ground_y"]
    grid=[[" " for _ in range(cols)] for _ in range(rows)]
    for x in range(cols): grid[ground][x]="="
    draw_drag(grid,state)
    pts={"root":state["root"],**state["joints"]}
    segments=[("head","neck"),("neck","root"),("neck","shoulder_l"),("shoulder_l","hand_l"),
              ("neck","shoulder_r"),("shoulder_r","hand_r"),("root","knee_l"),("knee_l","foot_l"),
              ("root","knee_r"),("knee_r","foot_r")]
    for an,bn in segments:
        a=pts[an]; b=pts[bn]; ch=segment_char(a,b)
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
    put(grid,max(0,state["root"]["x"]-14),max(1,state["root"]["y"]+2),state["velocity_hint"])
    put(grid,max(0,state["root"]["x"]-14),max(1,state["root"]["y"]+4),"D:"+state["drag_surface"]["mode"])
    return ["".join(row).rstrip() for row in grid]

def contact_text(motion):
    out=[
      "ASCII KINESIS V2 - AIRBORNE038",
      "Primitive: "+motion["primitive"],
      "Experiment: "+motion["experiment_id"],
      "Source evidence: TSR 500827 / campaign artifact 1vTgZso5TSriX11FmZyBCDo65XfSCX5-0a36ffMbv6mQ",
      "Source timing: UNKNOWN | decisive timing: INFERRED / STREET_FIGHTER-CAPCOM",
      "Rights firewall: source pixels/art/audio absent; abstract ASCII rig only.",
      "Legend: O head | @ root | o joint | h hand | ^ support | ~ external drag surface | : tether",
      ""
    ]
    for k in motion["keys"]:
        out += [
          f'{k["key_id"]}  {k["label"]}',
          f'timing={k["timing_class"]} provenance={k["timing_provenance"]} support={",".join(k["support_contact"]) or "NONE"} drag={k["drag_surface"]["mode"]}',
          f'causal_role={k["causal_role"]}',
          f'root_note={k["motion_arc_root_note"]}'
        ]
        out.extend(grid_for_state(motion,semantic_state(k)))
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

def get_font(size=13):
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf","/usr/share/fonts/dejavu/DejaVuSansMono.ttf","/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf"]:
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
        for i,(state,kid,label) in enumerate(states):
            img=Image.new("RGB",(w,h),(8,10,12)); d=ImageDraw.Draw(img)
            d.text((12,8),f"AIRBORNE038  {kid}  {label}",font=headfont,fill=(235,237,240))
            d.text((12,25),"DRAG AUTHORITY COLLAPSE / REACCELERATION / LANDING DEBT",font=font,fill=(180,184,190))
            lines=grid_for_state(motion,state)
            view_x0,view_x1=2,114; view_y0,view_y1=2,51
            x0=8; y0=44; line_h=8
            for rr,row_i in enumerate(range(view_y0,min(view_y1,len(lines)))):
                if y0+rr*line_h>=h: break
                d.text((x0,y0+rr*line_h),lines[row_i][view_x0:view_x1],font=font,fill=(238,238,238))
            writer.append_data(np.asarray(img))
    finally:
        writer.close()
    return len(states)

def compact_gzip_b64(text):
    return base64.b64encode(gzip.compress(text.encode("utf-8"),mtime=0)).decode("ascii")
def make_spa(motion,ascii_text,mp4_bytes):
    js=json.dumps(motion,indent=2,ensure_ascii=False)+"\n"
    a=compact_gzip_b64(ascii_text); j=compact_gzip_b64(js); v=base64.b64encode(mp4_bytes).decode("ascii")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Airborne038 - Drag Collapse Reacceleration Landing Debt</title><style>body{{margin:0;background:#0b0d10;color:#e8eaed;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}nav{{position:sticky;top:0;background:#11151a;padding:10px;border-bottom:1px solid #444}}button{{font:inherit;margin-right:8px;padding:8px 14px}}section{{display:none;padding:14px}}section.active{{display:block}}pre{{white-space:pre;overflow:auto;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;line-height:1.08}}video{{max-width:100%;height:auto;background:#000}}</style></head><body><nav><button data-view="ascii" onclick="show('ascii')">ASCII</button><button data-view="json" onclick="show('json')">JSON</button><button data-view="video" onclick="show('video')">VIDEO</button></nav><section id="ascii" class="active"><h1>ASCII</h1><pre id="asciipre"></pre></section><section id="json"><h1>JSON</h1><pre id="jsonpre"></pre></section><section id="video"><h1>VIDEO</h1><video id="v" controls loop playsinline src="data:video/mp4;base64,{v}"></video><p>Compiled solely from abstract ASCII rig + authored timing. No source pixels or audio.</p></section><script>const A="{a}",J="{j}";async function ungz(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).text()}}Promise.all([ungz(A),ungz(J)]).then(([a,j])=>{{document.getElementById('asciipre').textContent=a;document.getElementById('jsonpre').textContent=j}});function show(id){{document.querySelectorAll('section').forEach(s=>s.classList.remove('active'));document.getElementById(id).classList.add('active')}}</script></body></html>"""

def main():
    motion=json.loads(MOTION_PATH.read_text(encoding="utf-8"))
    ascii_text=contact_text(motion)
    CONTACT_PATH.write_text(ascii_text,encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="a038_media_") as td:
        mp4_path=Path(td)/"authoritative.mp4"
        frames=render_mp4(motion,mp4_path)
        media=mp4_path.read_bytes()
    SPA_PATH.write_text(make_spa(motion,ascii_text,media),encoding="utf-8")
    print(json.dumps({"frames":frames,"media_bytes":len(media),"media_sha256":hashlib.sha256(media).hexdigest(),
                      "contact_sha256":hashlib.sha256(ascii_text.encode("utf-8")).hexdigest(),
                      "spa_sha256":hashlib.sha256(SPA_PATH.read_bytes()).hexdigest()},sort_keys=True))
if __name__=="__main__": main()
