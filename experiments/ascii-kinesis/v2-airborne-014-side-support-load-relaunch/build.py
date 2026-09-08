#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
SPA = HERE / "side-support-load-relaunch.motion.html"
W, H, GROUND_Y, WALL_X = 72, 27, 23, 66
HOLD = {"ONES":1,"TWOS":2,"FOURS":4}
JOINTS = ["head","neck","shoulder_l","shoulder_r","elbow_l","elbow_r","hand_l","hand_r","pelvis","knee_l","knee_r","foot_l","foot_r"]
LINKS = [
    ("head","neck"),("neck","shoulder_l"),("neck","shoulder_r"),
    ("shoulder_l","elbow_l"),("elbow_l","hand_l"),
    ("shoulder_r","elbow_r"),("elbow_r","hand_r"),
    ("neck","pelvis"),("pelvis","knee_l"),("knee_l","foot_l"),
    ("pelvis","knee_r"),("knee_r","foot_r"),
]

def pose(obj):
    return dict(zip(JOINTS, obj["pose"]))

def bres(a,b):
    x0,y0=a; x1,y1=b
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1):
            return out
        e2=2*err
        if e2>=dy:
            err+=dy; x0+=sx
        if e2<=dx:
            err+=dx; y0+=sy

def glyph(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>abs(dy)*1.8: return "-"
    if abs(dy)>abs(dx)*1.8: return "|"
    return "\\" if dx*dy>0 else "/"

def render_ascii(obj,label=True):
    p=pose(obj)
    grid=[[" "]*W for _ in range(H)]
    def put(x,y,c,overwrite=False):
        if 0<=x<W and 0<=y<H and (overwrite or grid[y][x]==" "):
            grid[y][x]=c
    for x in range(W):
        grid[GROUND_Y][x]="_"
    for y in range(2,GROUND_Y+1):
        put(WALL_X,y,"|",True)
    for a,b in LINKS:
        c=glyph(p[a],p[b])
        for x,y in bres(p[a],p[b])[1:-1]:
            put(x,y,c)
    for name,(x,y) in p.items():
        put(x,y,"O" if name=="head" else ("@" if name=="pelvis" else "o"),True)
    hx,hy=p["head"]
    put(hx+2,hy,">",True)
    support=obj["support_contact"]
    if support in ("GROUND_BOTH","GROUND_LEFT","GROUND_LEFT_DOMINANT"):
        x,y=p["foot_l"]; put(x,min(H-1,y+1),"=",True)
    if support in ("GROUND_BOTH","GROUND_RIGHT","GROUND_RIGHT_DOMINANT"):
        x,y=p["foot_r"]; put(x,min(H-1,y+1),"=",True)
    if support=="SIDE_RIGHT_HAND_FOOT":
        for j in ("hand_r","foot_r"):
            x,y=p[j]; put(min(W-1,x+1),y,"=",True)
    if label:
        px,py=p["pelvis"]
        mark={
            "READY":"+","LOAD":"<","LAUNCH":"^","RISE":"^","APEX":"~","DESCENT":"v",
            "PRECONTACT":"?","SIDE_CONTACT":"!","SIDE_LOAD":"#","RELAUNCH":"^",
            "CONTACT":"!","LAND_COMPRESSION":"#","SETTLE":">","REBOUND":"^",
            "RECOVERY":".","RETURN":"+"
        }.get(obj["vertical_phase"],"*")
        put(max(0,px-4),py,mark,True)
    return "\n".join("".join(row).rstrip() for row in grid)

def contact_sheet(data):
    out=[
        "ASCII KINESIS V2 AIRBORNE 014 — SIDE SUPPORT LOAD RELAUNCH",
        "COPYABLE CONTACT SHEET — ABSTRACT RIG ONLY — NO SOURCE PIXELS",
        "Legend: O head | @ pelvis/root | o joints | > facing | | support plane | = authored support | ^/v/# phase",
        "",
    ]
    for k in data["keys"]:
        out.append(
            f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | "
            f"support={k['support_contact']} | contact={k['contact_state']} | phase={k['vertical_phase']} | "
            f"role={k['causal_role']} | root={k['motion_arc_root_note']}\n{render_ascii(k)}"
        )
    out.append("--- AUTHORED BRIDGES ---")
    for b in data["bridge_keys"]:
        out.append(
            f"{b['bridge_id']} {b['from_key']} -> {b['to_key']} | {b['timing_class']} {b['timing_provenance']} | "
            "explicit geometry-only bridge; semantic state unchanged"
        )
    return "\n\n".join(out)

def sequence(data):
    bridge_map={(b["from_key"],b["to_key"]):b for b in data["bridge_keys"]}
    out=[]
    keys=data["keys"]
    for i,key in enumerate(keys):
        out += [render_ascii(key)] * HOLD[key["timing_class"]]
        if i+1 < len(keys):
            nxt=keys[i+1]
            bridge=bridge_map.get((key["key_id"],nxt["key_id"]))
            if bridge:
                lhs=(key["support_contact"],key["contact_state"])
                rhs=(nxt["support_contact"],nxt["contact_state"])
                mid=(bridge["support_contact"],bridge["contact_state"])
                if lhs != rhs or lhs != mid:
                    raise RuntimeError("authored bridge crosses semantic state")
                out += [render_ascii(bridge,False)] * HOLD[bridge["timing_class"]]
    return out

def mono_font(size):
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate,size)
    return ImageFont.load_default()

def make_media(data,destination):
    frames=sequence(data)
    font=mono_font(11)
    with tempfile.TemporaryDirectory(prefix="air014-") as td:
        td=Path(td)
        for index,text in enumerate(frames):
            image=Image.new("RGB",(640,360),"black")
            draw=ImageDraw.Draw(image)
            draw.multiline_text((7,8),text,font=font,fill="white",spacing=0)
            image.save(td/f"f-{index:04d}.png")
        subprocess.run([
            "ffmpeg","-hide_banner","-loglevel","error","-y",
            "-framerate",str(data["compile"]["fps"]),
            "-i",str(td/"f-%04d.png"),
            "-c:v","libx264","-preset","veryslow","-crf",str(data["compile"]["encoder_crf"]),
            "-pix_fmt","yuv420p","-movflags","+faststart",str(destination)
        ],check=True)
    return frames

def make_html(data,sheet,media):
    json_text=json.dumps(data,separators=(",",":"),sort_keys=True,ensure_ascii=False)
    def pack(text):
        return base64.b64encode(gzip.compress(text.encode("utf-8"),9,mtime=0)).decode("ascii")
    ascii64=pack(sheet)
    json64=pack(json_text)
    video64=base64.b64encode(media).decode("ascii")
    return f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Side Support Load Relaunch</title><style>
:root{{color-scheme:dark}}body{{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}}nav{{position:sticky;top:0;display:flex;gap:8px;padding:10px;background:#181818;border-bottom:1px solid #444}}button{{font:inherit;padding:8px 12px}}section{{padding:12px}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1.05}}video{{display:block;max-width:100%;width:640px;height:auto;background:#000}}
</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="a"></pre></section><section id="json" hidden><pre id="j"></pre></section><section id="video" hidden><video id="v" controls loop playsinline></video></section><script>
const A="{ascii64}",J="{json64}",V="{video64}";
async function gz(x){{const u=Uint8Array.from(atob(x),c=>c.charCodeAt());return new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}
Promise.all([gz(A),gz(J)]).then(([aa,jj])=>{{document.getElementById("a").textContent=aa;document.getElementById("j").textContent=jj}});
document.getElementById("v").src="data:video/mp4;base64,"+V;
for(const b of document.querySelectorAll("button[data-view]"))b.onclick=()=>{{for(const s of document.querySelectorAll("section"))s.hidden=s.id!==b.dataset.view}};
</script></body></html>"""

def main():
    data=json.loads(MOTION.read_text(encoding="utf-8"))
    sheet=contact_sheet(data)
    ascii_sha=hashlib.sha256(sheet.encode()).hexdigest()
    if ascii_sha != data["ascii_sheet_sha256"]:
        raise SystemExit(f"ASCII_IDENTITY_MISMATCH expected={data['ascii_sheet_sha256']} actual={ascii_sha}")
    with tempfile.TemporaryDirectory(prefix="air014-media-") as td:
        media_path=Path(td)/"side-support-load-relaunch.mp4"
        frames=make_media(data,media_path)
        media=media_path.read_bytes()
    media_sha=hashlib.sha256(media).hexdigest()
    if media_sha != data["compile"]["media_sha256"]:
        raise SystemExit(f"MEDIA_IDENTITY_MISMATCH expected={data['compile']['media_sha256']} actual={media_sha}")
    if len(media) != data["compile"]["media_bytes"] or len(frames) != data["compile"]["video_frames_total"]:
        raise SystemExit("MEDIA_FACT_MISMATCH")
    SPA.write_text(make_html(data,sheet,media),encoding="utf-8")
    print(json.dumps({"ascii_sha256":ascii_sha,"media_sha256":media_sha,"media_bytes":len(media),"frames":len(frames),"spa":SPA.name},sort_keys=True))

if __name__=="__main__":
    main()
