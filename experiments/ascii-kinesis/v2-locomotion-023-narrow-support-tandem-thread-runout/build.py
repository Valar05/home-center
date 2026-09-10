#!/usr/bin/env python3
from __future__ import annotations
import base64, json, math, subprocess
from pathlib import Path
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
MOTION=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
W,H=map(int,MOTION['rig']['viewport']); FPS=int(MOTION['timing']['fps'])
FRAMES=HERE/'_frames'; MP4=HERE/'_authoritative.mp4'; ASCII=HERE/'contact-sheet.txt'; SPA=HERE/'narrow-support-tandem-thread-runout.motion.html'

def tangent(deg):
    r=math.radians(float(deg)); return math.cos(r),math.sin(r)
def perp(v): return -v[1],v[0]
def add(a,b,s=1.0): return a[0]+b[0]*s,a[1]+b[1]*s

def body(k):
    root=tuple(map(float,k['root'])); com=tuple(map(float,k['com']))
    rt=tangent(k['yaw_deg']); tt=tangent(k['torso_yaw_deg']); tn=perp(tt)
    chest=add(root,tt,30); head=add(chest,tt,22)
    ls=add(chest,tn,14); rs=add(chest,tn,-14); bias=float(k.get('arm_swing_bias',0))
    lh=add(add(ls,tt,18-5*bias),tn,8*bias); rh=add(add(rs,tt,18+5*bias),tn,8*bias)
    return {'root':root,'com':com,'chest':chest,'head':head,'ls':ls,'rs':rs,'lh':lh,'rh':rh,'lf':tuple(map(float,k['left_foot'])),'rf':tuple(map(float,k['right_foot']))}

def support_side(k): return 'left' if str(k['support']['owner']).startswith('LEFT') else 'right'

def lane_half_width(x):
    if x <= 120: return 54
    if x < 205: return 54 - (x-120)*(42/85)
    if x <= 315: return 12
    if x < 370: return 12 + (x-315)*(34/55)
    return 46

def lane_edge(x,sign): return 180 + sign*lane_half_width(x)

def draw_lane(d):
    xs=list(range(40,601,4))
    for sign in (-1,1): d.line([(x,lane_edge(x,sign)) for x in xs],fill=(72,80,90),width=2)
    d.line([(205,168),(315,168)],fill=(98,108,120),width=1); d.line([(205,192),(315,192)],fill=(98,108,120),width=1)

def draw_route(d):
    pts=[tuple(map(float,k['root'])) for k in MOTION['keys']]
    if len(pts)>1:d.line(pts,fill=(58,65,75),width=3)
    for x,y in pts:d.ellipse((x-2,y-2,x+2,y+2),fill=(91,99,111))

def draw_frame(k,idx,path):
    im=Image.new('RGB',(W,H),(13,15,18)); d=ImageDraw.Draw(im); draw_lane(d); draw_route(d); p=body(k)
    bodyc=(235,239,244); secondary=(177,186,198); rootc=(247,207,92); supportc=(111,199,142); comc=(225,126,150)
    side=support_side(k); sf=p['lf'] if side=='left' else p['rf']
    d.line((sf[0],sf[1],p['com'][0],p['com'][1]),fill=supportc,width=3)
    d.line((p['lf'][0],p['lf'][1],p['root'][0],p['root'][1]),fill=secondary,width=3); d.line((p['rf'][0],p['rf'][1],p['root'][0],p['root'][1]),fill=secondary,width=3)
    for nm,s in (('lf','left'),('rf','right')):
        x,y=p[nm]
        if s==side:d.ellipse((x-8,y-8,x+8,y+8),fill=supportc)
        else:d.ellipse((x-7,y-7,x+7,y+7),outline=bodyc,width=3)
    rx,ry=p['root']; cx,cy=p['com']
    d.polygon([(rx,ry-7),(rx+7,ry),(rx,ry+7),(rx-7,ry)],outline=rootc,width=3); d.ellipse((cx-5,cy-5,cx+5,cy+5),fill=comc)
    d.line((rx,ry,p['chest'][0],p['chest'][1]),fill=bodyc,width=6); d.line((p['ls'][0],p['ls'][1],p['lh'][0],p['lh'][1]),fill=secondary,width=4); d.line((p['rs'][0],p['rs'][1],p['rh'][0],p['rh'][1]),fill=secondary,width=4)
    hx,hy=p['head']; d.ellipse((hx-8,hy-8,hx+8,hy+8),outline=bodyc,width=4)
    rt=tangent(k['yaw_deg']); tip=(rx+rt[0]*34,ry+rt[1]*34); d.line((rx,ry,tip[0],tip[1]),fill=rootc,width=2)
    tn=perp(rt); a=(tip[0]-rt[0]*8+tn[0]*5,tip[1]-rt[1]*8+tn[1]*5); b=(tip[0]-rt[0]*8-tn[0]*5,tip[1]-rt[1]*8-tn[1]*5); d.polygon([tip,a,b],fill=rootc)
    d.text((12,10),f"{k['key_id']}  {k['name']}",fill=(135,145,158)); d.text((12,28),f"support {k['support']['owner']} | width {k['support_width_px']} | root d {k['root_spacing_px']} | phase {k['phase']}",fill=(106,116,128))
    im.save(path,'PNG',optimize=False)

def grid_line(g,x0,y0,x1,y1,ch):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        if 0<=y0<len(g) and 0<=x0<len(g[0]):g[y0][x0]=ch
        if x0==x1 and y0==y1:break
        e2=2*err
        if e2>=dy:err+=dy;x0+=sx
        if e2<=dx:err+=dx;y0+=sy

def to_grid(pt):
    x,y=pt; return int(round((x-35)/(W-70)*79)),int(round((y-110)/(H-190)*25))
def ascii_pose(k):
    g=[[' ']*80 for _ in range(26)]
    for gx in range(80):
        wx=35+gx*(W-70)/79
        for sign in (-1,1):
            gy=int(round((lane_edge(wx,sign)-110)/(H-190)*25))
            if 0<=gy<26:g[gy][gx]='#'
    route=[to_grid(tuple(map(float,x['root']))) for x in MOTION['keys']]
    for a,b in zip(route,route[1:]):grid_line(g,*a,*b,'.')
    p=body(k); side=support_side(k); sf=p['lf'] if side=='left' else p['rf']; grid_line(g,*to_grid(sf),*to_grid(p['com']),'!')
    grid_line(g,*to_grid(p['lf']),*to_grid(p['root']),'/'); grid_line(g,*to_grid(p['rf']),*to_grid(p['root']),'\\')
    grid_line(g,*to_grid(p['root']),*to_grid(p['chest']),'|'); grid_line(g,*to_grid(p['ls']),*to_grid(p['lh']),'/'); grid_line(g,*to_grid(p['rs']),*to_grid(p['rh']),'\\')
    rt=tangent(k['yaw_deg']); tip=add(p['root'],rt,34); grid_line(g,*to_grid(p['root']),*to_grid(tip),'-')
    for nm,ch in (('head','O'),('chest','T'),('root','@'),('com','c')):
        x,y=to_grid(p[nm]);
        if 0<=y<26 and 0<=x<80:g[y][x]=ch
    for nm,s in (('lf','left'),('rf','right')):
        x,y=to_grid(p[nm]);
        if 0<=y<26 and 0<=x<80:g[y][x]='*' if s==side else '~'
    x,y=to_grid(tip)
    if 0<=y<26 and 0<=x<80:g[y][x]='>'
    return '\n'.join(''.join(r).rstrip() for r in g)

def make_contact_sheet():
    out=['ASCII KINESIS V2 · LOCOMOTION 023 · NARROW SUPPORT / TANDEM THREAD / RUNOUT','legend: @ root · c COM · * support owner · ~ swing foot · ! support→COM · O head · . root route · # support-corridor edge · > tangent','source evidence: The Prince / Prince of Persia / Sega Genesis / TSR asset 36749 / Home Center artifact 18stTpX2ktEpoQgpU8lniX6ZMatYHRNv3vpS29mfbS7o','OBSERVED: commissioned evidence inspected the entire 552×1104 static sheet as one corpus; grounded, airborne, compressed, recovery, and edge-contact families are present; source timing is not exposed.','UNKNOWN: source chronology/exposure/root coordinates/support forces; no source evidence establishes this narrow-support choreography.','authored timing: INFERRED / STREET_FIGHTER-CAPCOM. rights firewall: independent abstract rig only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/redistribution/close imitation.','thesis: COM centers before entering a collapsing support width; forward travel continues through tandem support threading; corridor release produces an overlong/wider first free catch, then shorter displaced corrections.','']
    for k in MOTION['keys']:
        out.append(f"{k['key_id']} {k['name']} · {k['timing_class']}/{k['hold_frames']}f · {k['timing_provenance']} · support={k['support']['owner']} · phase={k['phase']} · rootΔ={k['root_spacing_px']}px · width={k['support_width_px']}px · yaw={k['yaw_deg']:+}° · torso={k['torso_yaw_deg']:+}°")
        out.append(ascii_pose(k)); out.append(f"causal: {k['causal_role']}"); out.append('')
    return '\n'.join(out).rstrip()+'\n'

def make_spa(ascii_text,motion_text,mp4_bytes):
    ab64=base64.b64encode(ascii_text.encode()).decode(); jb64=base64.b64encode(motion_text.encode()).decode(); vb64=base64.b64encode(mp4_bytes).decode(); title='ASCII Kinesis V2 · Locomotion 023 · Narrow Support / Tandem Thread / Runout'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>:root{{color-scheme:dark}}body{{margin:0;background:#0f1114;color:#edf0f3;font-family:system-ui,sans-serif}}header{{padding:14px 18px;border-bottom:1px solid #343943}}nav{{display:flex;gap:8px}}button{{font:inherit;padding:7px 12px;background:#1a1e24;color:inherit;border:1px solid #4a515d;border-radius:6px}}button[aria-selected="true"]{{background:#303641}}main{{padding:14px 18px}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #343943;padding:12px;max-height:78vh}}video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #343943}}</style></head><body><header><h1>{title}</h1><nav><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section id="ascii"><pre id="ascii-pre"></pre></section><section id="json" hidden><pre id="json-pre"></pre></section><section id="video" hidden><video controls loop muted playsinline src="data:video/mp4;base64,{vb64}"></video></section></main><script>function txt(s){{return new TextDecoder().decode(Uint8Array.from(atob(s),c=>c.charCodeAt(0)))}}document.getElementById('ascii-pre').textContent=txt('{ab64}');document.getElementById('json-pre').textContent=txt('{jb64}');const buttons=[...document.querySelectorAll('button[data-view]')];for(const b of buttons)b.addEventListener('click',()=>{{for(const q of buttons)q.setAttribute('aria-selected',q===b?'true':'false');for(const x of document.querySelectorAll('main section'))x.hidden=x.id!==b.dataset.view;}});</script></body></html>'''

def main():
    FRAMES.mkdir(exist_ok=True)
    for p in FRAMES.glob('*.png'):p.unlink()
    idx=0
    for k in MOTION['keys']:
        for _ in range(int(k['hold_frames'])):draw_frame(k,idx,FRAMES/f'frame-{idx:04d}.png');idx+=1
    assert idx==int(MOTION['timing']['total_frames'])
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(FRAMES/'frame-%04d.png'),'-vf','scale=480:270:flags=neighbor','-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)],check=True)
    ascii_text=make_contact_sheet(); ASCII.write_text(ascii_text,encoding='utf-8'); motion_text=(HERE/'motion.json').read_text(encoding='utf-8'); SPA.write_text(make_spa(ascii_text,motion_text,MP4.read_bytes()),encoding='utf-8')
if __name__=='__main__':main()
