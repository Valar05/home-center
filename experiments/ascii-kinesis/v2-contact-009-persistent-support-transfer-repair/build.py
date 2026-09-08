#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import base64, gzip, hashlib, json, subprocess, tempfile
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
W, H = 64, 25
CELL_W, CELL_H = 12, 16
PIX_W, PIX_H = W * CELL_W, H * CELL_H
TIMING = {"ONES": 1, "TWOS": 2, "FOURS": 4}

def clamp(v, lo=0.0, hi=1.0):
    return max(lo, min(hi, v))

def smooth(t):
    t = clamp(t)
    return t*t*(3.0-2.0*t)

def qbez(a, b, bias, t):
    t = smooth(t)
    c = ((a[0]+b[0])/2.0+bias[0], (a[1]+b[1])/2.0+bias[1])
    u = 1.0 - t
    return [round(u*u*a[0] + 2*u*t*c[0] + t*t*b[0]),
            round(u*u*a[1] + 2*u*t*c[1] + t*t*b[1])]

def semantic_signature(k):
    s = k["support_contact"]
    return (s["contact_state"], s["custody"], s["support_A"], s["support_B"],
            s["root_owner"], s.get("relationship_anchor"))

def bridge(k, n, t):
    meta = k["bridge_to_next"]
    if meta["mode"].startswith("SNAP") or meta["mode"] == "END":
        return json.loads(json.dumps(k))
    if semantic_signature(k) != semantic_signature(n):
        return json.loads(json.dumps(k))
    out = json.loads(json.dumps(k))
    lag_b = float(meta.get("lag_B", 0.0))
    ta = clamp(t)
    tb = 0.0 if t <= lag_b else clamp((t-lag_b)/max(1e-6, 1.0-lag_b))
    ba = meta.get("arc_bias_A", [0, 0])
    bb = meta.get("arc_bias_B", [0, 0])
    out["pose_rig"]["A"] = {j:qbez(k["pose_rig"]["A"][j], n["pose_rig"]["A"][j], ba, ta)
                            for j in k["pose_rig"]["A"]}
    out["pose_rig"]["B"] = {j:qbez(k["pose_rig"]["B"][j], n["pose_rig"]["B"][j], bb, tb)
                            for j in k["pose_rig"]["B"]}
    if out["support_contact"].get("relationship_anchor") == "A.hand_r<->B.hand_l":
        out["pose_rig"]["B"]["hand_l"] = list(out["pose_rig"]["A"]["hand_r"])
    out["environment_anchors"] = [
        {"body":a["body"], "joint":a["joint"], "at":list(out["pose_rig"][a["body"]][a["joint"]])}
        for a in k.get("environment_anchors", [])
    ]
    sc0 = k["relationship_frame"].get("shared_center")
    sc1 = n["relationship_frame"].get("shared_center")
    if sc0 is not None and sc1 is not None:
        out["relationship_frame"]["shared_center"] = qbez(sc0, sc1, [0, 0], t)
    return out

def bres(grid, p0, p1, ch=None):
    x0, y0 = map(int, p0); x1, y1 = map(int, p1)
    dx = abs(x1-x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1-y0); sy = 1 if y0 < y1 else -1
    err = dx + dy
    if ch is None:
        if abs(x1-x0) > abs(y1-y0)*1.7: ch = "-"
        elif abs(y1-y0) > abs(x1-x0)*1.7: ch = "|"
        else: ch = "\\" if (x1-x0)*(y1-y0) > 0 else "/"
    while True:
        if 0 <= x0 < W and 0 <= y0 < H and grid[y0][x0] == " ":
            grid[y0][x0] = ch
        if x0 == x1 and y0 == y1: break
        e2 = 2*err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy

def put(grid, p, ch):
    if p is None: return
    x, y = map(int, p)
    if 0 <= x < W and 0 <= y < H: grid[y][x] = ch

def draw_body(grid, pose, body):
    sl, sr, pel = pose["shoulder_l"], pose["shoulder_r"], pose["pelvis"]
    for a, b in [
        (sl,sr),(sl,pel),(sr,pel),
        (sl,pose["elbow_l"]),(pose["elbow_l"],pose["hand_l"]),
        (sr,pose["elbow_r"]),(pose["elbow_r"],pose["hand_r"]),
        (pel,pose["knee_l"]),(pel,pose["knee_r"]),
        (pose["knee_l"],pose["foot_l"]),(pose["knee_r"],pose["foot_r"])
    ]: bres(grid, a, b)
    neck = ((sl[0]+sr[0])//2, (sl[1]+sr[1])//2)
    bres(grid, neck, pose["head"], "|")
    put(grid, pose["head"], "a" if body == "A" else "b")
    put(grid, pel, body)
    for j in ("shoulder_l","shoulder_r","elbow_l","elbow_r","hand_l","hand_r","knee_l","knee_r"):
        put(grid, pose[j], "+")
    put(grid, pose["foot_l"], "L" if body == "A" else "l")
    put(grid, pose["foot_r"], "R" if body == "A" else "r")

def ascii_frame(k):
    g = [[" "]*W for _ in range(H)]
    for x in range(8,34,2): g[23][x] = "."
    for x in range(39,59): g[18][x] = "_"
    for y in range(14,19): g[y][39] = "|"
    draw_body(g, k["pose_rig"]["A"], "A")
    draw_body(g, k["pose_rig"]["B"], "B")
    for a in k.get("environment_anchors", []): put(g, a["at"], "#")
    sc = k["relationship_frame"].get("shared_center")
    if k["support_contact"].get("relationship_anchor") == "A.hand_r<->B.hand_l" and sc is not None:
        cp = k["pose_rig"]["A"]["hand_r"]
        bres(g, sc, cp, "-")
        put(g, cp, "@")
    put(g, sc, "*")
    return "\n".join("".join(row).rstrip() for row in g)

def contact_sheet(data):
    out = []
    for k in data["keys"]:
        s = k["support_contact"]; r = k["relationship_frame"]
        out += [
            f"{k['key_id']} {k['name']} | {k['timing_class']}/{k['timing_provenance']} | "
            f"contact={s['contact_state']} custody={s['custody']} | "
            f"A={s['support_A']} B={s['support_B']} root={s['root_owner']} | force={r['force_axis']}",
            f"ROLE: {k['causal_role']}",
            f"ARC:  {k['motion_arc_root_note']}",
            ascii_frame(k), ""
        ]
    return "\n".join(out).rstrip() + "\n"

def sequence(data):
    seq = []
    ks = data["keys"]
    for _ in range(int(data["compile"]["loop_repetitions"])):
        for i, k in enumerate(ks):
            seq.extend([k] * TIMING[k["timing_class"]])
            if i < len(ks)-1:
                meta = k["bridge_to_next"]; nxt = ks[i+1]
                n = int(meta.get("frames", 0))
                if meta["mode"].startswith("SNAP") or semantic_signature(k) != semantic_signature(nxt): n = 0
                for j in range(1, n+1): seq.append(bridge(k, nxt, j/(n+1)))
    return seq

def glyph(d, c, x, y, cw, ch):
    x0,y0=x+1,y+1; x1,y1=x+cw-2,y+ch-2; xm,ym=(x0+x1)//2,(y0+y1)//2
    kw=dict(fill="white", width=2)
    if c==".": d.ellipse((xm-1,y1-2,xm+1,y1),fill="white")
    elif c=="_": d.line((x0,y1,x1,y1),**kw)
    elif c=="-": d.line((x0,ym,x1,ym),**kw)
    elif c=="|": d.line((xm,y0,xm,y1),**kw)
    elif c=="/": d.line((x0,y1,x1,y0),**kw)
    elif c=="\\": d.line((x0,y0,x1,y1),**kw)
    elif c=="+": d.line((x0,ym,x1,ym),**kw); d.line((xm,y0,xm,y1),**kw)
    elif c=="#":
        d.line((x0+2,y0,x0+2,y1),**kw); d.line((x1-2,y0,x1-2,y1),**kw)
        d.line((x0,ym-2,x1,ym-2),**kw); d.line((x0,ym+2,x1,ym+2),**kw)
    elif c=="@":
        d.ellipse((x0,y0,x1,y1),outline="white",width=2)
        d.line((xm,y0+2,xm,y1-2),**kw); d.line((x0+2,ym,x1-2,ym),**kw)
    elif c=="*":
        d.line((x0,ym,x1,ym),**kw); d.line((xm,y0,xm,y1),**kw)
        d.line((x0+1,y0+1,x1-1,y1-1),**kw); d.line((x0+1,y1-1,x1-1,y0+1),**kw)
    elif c in ("a","b"):
        d.ellipse((x0+1,y0+1,x1-1,y1-1),outline="white",width=2)
        if c=="a": d.line((xm,y0+3,x1-1,y1-1),**kw)
        else: d.line((x0+2,y0,x0+2,y1),**kw)
    elif c=="A":
        d.line((x0,y1,xm,y0),**kw); d.line((xm,y0,x1,y1),**kw); d.line((x0+2,ym,x1-2,ym),**kw)
    elif c=="B":
        d.line((x0+1,y0,x0+1,y1),**kw)
        d.arc((x0,y0,x1,ym+2),-90,90,fill="white",width=2)
        d.arc((x0,ym-2,x1,y1),-90,90,fill="white",width=2)
    elif c in ("L","l"):
        d.line((x0,y0,x0,y1),**kw); d.line((x0,y1,x1,y1),**kw)
        if c=="l": d.line((xm,y0,xm,y1),fill="white",width=1)
    elif c in ("R","r"):
        d.line((x0,y0,x0,y1),**kw); d.line((x0,y0,x1,y0),**kw)
        d.line((x0,ym,x1,ym),**kw); d.line((x1,y0,x1,ym),**kw); d.line((xm,ym,x1,y1),**kw)
        if c=="r": d.ellipse((x0,y0,x1,ym),outline="white",width=1)

def raster(k, path):
    text = ascii_frame(k)
    im = Image.new("RGB", (PIX_W,PIX_H), "black")
    d = ImageDraw.Draw(im)
    for r,line in enumerate(text.splitlines()[:H]):
        for c,chv in enumerate(line[:W]):
            if chv != " ": glyph(d, chv, c*CELL_W, r*CELL_H, CELL_W, CELL_H)
    im.save(path)

def render(data, tmp):
    seq = sequence(data)
    frames = tmp/"frames"; frames.mkdir()
    for i,k in enumerate(seq): raster(k, frames/f"{i:04d}.png")
    mp4 = tmp/"motion.mp4"
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-framerate",str(data["compile"]["fps"]),
        "-i",str(frames/"%04d.png"),"-c:v","libx264","-preset","veryslow",
        "-crf",str(data["compile"]["crf"]),"-pix_fmt","yuv420p","-movflags","+faststart",
        "-map_metadata","-1","-fflags","+bitexact","-flags:v","+bitexact",str(mp4)
    ], check=True)
    subprocess.run(["ffmpeg","-v","error","-i",str(mp4),"-f","null","-"],check=True)
    probe=json.loads(subprocess.check_output([
        "ffprobe","-v","error","-select_streams","v:0",
        "-show_entries","stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration",
        "-of","json",str(mp4)
    ], text=True))
    return mp4,seq,probe

def page(data, sheet, raw):
    payload=json.dumps(data,sort_keys=True,indent=2,ensure_ascii=True).encode()
    a=base64.b64encode(gzip.compress(sheet.encode(),compresslevel=9,mtime=0)).decode("ascii")
    j=base64.b64encode(gzip.compress(payload,compresslevel=9,mtime=0)).decode("ascii")
    v=base64.b64encode(gzip.compress(raw,compresslevel=9,mtime=0)).decode("ascii")
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{data["experiment_id"]}</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#080808;color:#eee;font-family:system-ui,sans-serif}}header{{padding:12px 16px;border-bottom:1px solid #444}}nav{{display:flex;gap:8px;padding:10px 16px;position:sticky;top:0;background:#080808}}button{{font:inherit;padding:8px 14px}}section{{display:none;padding:12px 16px}}section.active{{display:block}}pre{{margin:0;overflow:auto;white-space:pre;font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;tab-size:2;line-height:1.05}}video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #444}}</style></head><body><header><strong>ASCII Kinesis V2 · CONTACT 009 · Persistent Support Transfer Repair</strong></header><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="ascii-pre"></pre></section><section id="json"><pre id="json-pre"></pre></section><section id="video"><video id="motion-video" controls autoplay muted loop playsinline></video></section><script>const A='{a}',J='{j}',V='{v}';const bs=[...document.querySelectorAll('button[data-view]')],ss=[...document.querySelectorAll('section')];for(const b of bs)b.onclick=()=>{{for(const s of ss)s.classList.toggle('active',s.id===b.dataset.view)}};async function gzb(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip')));return new Uint8Array(await r.arrayBuffer())}}async function gzt(s){{return new TextDecoder().decode(await gzb(s))}}function b64(b){{let o='';for(let i=0;i<b.length;i+=8192)o+=String.fromCharCode(...b.subarray(i,i+8192));return btoa(o)}};(async()=>{{document.getElementById('ascii-pre').textContent=await gzt(A);document.getElementById('json-pre').textContent=await gzt(J);document.getElementById('motion-video').src='data:video/mp4;base64,'+b64(await gzb(V))}})();</script></body></html>'''

def main():
    data=json.loads(MOTION.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as td:
        mp4,seq,probe=render(data,Path(td)); raw=mp4.read_bytes()
    media_sha=hashlib.sha256(raw).hexdigest(); stream=probe["streams"][0]
    data["compile"]["video_frames_total"]=len(seq)
    data["compile"]["media_bytes"]=len(raw)
    data["compile"]["media_sha256"]=media_sha
    data["compile"]["full_decode"]="PASS"
    data["compile"]["decode"]={"codec":stream.get("codec_name"),"width":int(stream.get("width",PIX_W)),
        "height":int(stream.get("height",PIX_H)),"fps":int(data["compile"]["fps"]),
        "frames":int(stream.get("nb_frames") or len(seq)),"duration_seconds":float(probe["format"]["duration"])}
    MOTION.write_text(json.dumps(data,sort_keys=True,indent=2,ensure_ascii=True)+"\n",encoding="utf-8")
    sheet=contact_sheet(data); (HERE/"contact-sheet.txt").write_text(sheet,encoding="utf-8")
    pg=page(data,sheet,raw); (HERE/"persistent-support-transfer-repair.motion.html").write_text(pg,encoding="utf-8")
    print(json.dumps({"media_sha256":media_sha,"media_bytes":len(raw),"frames":len(seq),
        "motion_sha256":hashlib.sha256(MOTION.read_bytes()).hexdigest(),
        "sheet_sha256":hashlib.sha256((HERE/"contact-sheet.txt").read_bytes()).hexdigest(),
        "spa_sha256":hashlib.sha256(pg.encode()).hexdigest(),"spa_bytes":len(pg.encode()),
        "decode":data["compile"]["decode"]},sort_keys=True))

if __name__=="__main__": main()
