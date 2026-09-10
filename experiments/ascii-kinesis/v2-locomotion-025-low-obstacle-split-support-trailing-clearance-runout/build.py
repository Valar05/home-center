#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
MOTION=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
W,H=map(int,MOTION['rig']['viewport']); FPS=int(MOTION['timing']['fps']); G=int(MOTION['rig']['ground_y'])
OBS=MOTION['rig']['obstacle']; FRAMES=HERE/'_frames'; MP4=HERE/'_authoritative.mp4'; ASCII=HERE/'contact-sheet.txt'; SPA=HERE/'low-obstacle-split-support-trailing-clearance-runout.motion.html'
def supported(k,side):
    return str(k['support'][side]) in ('PLANTED_FIXED','UNLOADING_FIXED')
def body(k):
    rx,ry=map(float,k['root']); lean=math.radians(float(k['torso_lean_deg']))
    vx=math.sin(lean); vy=-math.cos(lean)
    chest=(rx+vx*44,ry+vy*44); head=(chest[0]+vx*27,chest[1]+vy*27)
    com=tuple(map(float,k['com'])); lf=tuple(map(float,k['left_foot'])); rf=tuple(map(float,k['right_foot']))
    lag=math.radians(float(k.get('free_foot_lag_deg',0)))
    shoulder=(chest[0],chest[1]+4)
    arm_front=(shoulder[0]+31*math.cos(lag),shoulder[1]+13+20*math.sin(lag))
    arm_rear=(shoulder[0]-25*math.cos(lag*.7),shoulder[1]+17-16*math.sin(lag*.7))
    return {'root':(rx,ry),'com':com,'chest':chest,'head':head,'lf':lf,'rf':rf,'shoulder':shoulder,'af':arm_front,'ar':arm_rear}
def draw_route(d):
    pts=[tuple(map(float,k['root'])) for k in MOTION['keys']]
    d.line(pts,fill=(52,58,68),width=3)
    for p in pts:d.ellipse((p[0]-2,p[1]-2,p[0]+2,p[1]+2),fill=(78,87,99))
def draw_obstacle(d):
    x0,x1,yt,yg=map(int,(OBS['x0'],OBS['x1'],OBS['top_y'],OBS['ground_y']))
    d.rectangle((x0,yt,x1,yg),fill=(66,72,80),outline=(170,179,190),width=2)
    d.line((x0+5,yt+6,x1-5,yt+6),fill=(117,128,140),width=2)
def draw_frame(k,idx,path):
    im=Image.new('RGB',(W,H),(13,15,18)); d=ImageDraw.Draw(im)
    d.line((26,G,614,G),fill=(80,87,97),width=2); draw_route(d); draw_obstacle(d); p=body(k)
    bodyc=(235,239,244); secondary=(170,181,195); rootc=(247,207,92); supportc=(112,201,144); comc=(225,126,150); probec=(235,190,96)
    for side,nm in [('left','lf'),('right','rf')]:
        fx,fy=p[nm]; rx,ry=p['root']; knee=((fx+rx)/2+(9 if side=='left' else -9),(fy+ry)/2-7)
        d.line((rx,ry,*knee,*p[nm]),fill=secondary,width=4)
        state=str(k['support'][side])
        if supported(k,side):
            d.ellipse((fx-9,fy-5,fx+9,fy+5),fill=supportc); d.line((fx,fy,*p['com']),fill=supportc,width=2)
        elif state=='PROBE': d.ellipse((fx-8,fy-5,fx+8,fy+5),outline=probec,width=3)
        else: d.ellipse((fx-7,fy-4,fx+7,fy+4),outline=bodyc,width=2)
    d.line((*p['root'],*p['chest']),fill=bodyc,width=6)
    hx,hy=p['head']; d.ellipse((hx-9,hy-9,hx+9,hy+9),outline=bodyc,width=4)
    d.line((*p['shoulder'],*p['af']),fill=bodyc,width=4); d.line((*p['shoulder'],*p['ar']),fill=secondary,width=4)
    for q in (p['af'],p['ar']):d.ellipse((q[0]-4,q[1]-4,q[0]+4,q[1]+4),fill=bodyc)
    rx,ry=p['root']; d.polygon([(rx,ry-7),(rx+7,ry),(rx,ry+7),(rx-7,ry)],outline=rootc,width=3)
    cx,cy=p['com']; d.ellipse((cx-5,cy-5,cx+5,cy+5),fill=comc)
    d.text((12,10),f"{k['key_id']}  {k['name']}",fill=(144,154,167))
    d.text((12,28),f"support {k['support']['owner']} | rootd {k['root_spacing_px']} | {k['clearance_state']} | phase {k['phase']}",fill=(109,120,134))
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
    x,y=pt; return int(round((x-35)/(W-70)*83)),int(round((y-130)/(H-150)*23))
def ascii_pose(k):
    g=[[' ']*84 for _ in range(24)]
    gy=int(round((G-130)/(H-150)*23))
    if 0<=gy<24:
        for x in range(84):g[gy][x]='_'
    x0,y0=to_grid((OBS['x0'],OBS['top_y'])); x1,y1=to_grid((OBS['x1'],OBS['ground_y']))
    for yy in range(max(0,y0),min(24,y1+1)):
        for xx in range(max(0,x0),min(84,x1+1)):g[yy][xx]='#'
    route=[to_grid(tuple(map(float,q['root']))) for q in MOTION['keys']]
    for a,b in zip(route,route[1:]):grid_line(g,*a,*b,'.')
    p=body(k)
    for nm in ('lf','rf'):grid_line(g,*to_grid(p[nm]),*to_grid(p['root']),'/')
    grid_line(g,*to_grid(p['root']),*to_grid(p['chest']),'|')
    grid_line(g,*to_grid(p['shoulder']),*to_grid(p['af']),'-')
    grid_line(g,*to_grid(p['shoulder']),*to_grid(p['ar']),'-')
    for nm,ch in [('head','O'),('chest','T'),('root','@'),('com','c')]:
        x,y=to_grid(p[nm])
        if 0<=y<24 and 0<=x<84:g[y][x]=ch
    for nm,side in [('lf','left'),('rf','right')]:
        x,y=to_grid(p[nm]); state=str(k['support'][side])
        if 0<=y<24 and 0<=x<84:g[y][x]='*' if supported(k,side) else ('?' if state=='PROBE' else '~')
    return '\n'.join(''.join(r).rstrip() for r in g)
def make_contact_sheet():
    out=[
      'ASCII KINESIS V2 · LOCOMOTION 025 · LOW OBSTACLE SPLIT SUPPORT / TRAILING CLEARANCE RUNOUT',
      'legend: @ root · c COM · * trusted foot support · ? probe · ~ free foot · # fixed low obstacle · . root route',
      'source evidence: Bob / Bob the Builder: Fix It Fun! / Game Boy-GBC / TSR asset 128015 / Home Center artifact 1fshOV6xbFjFc2KYyeEfW9f7A8lCzfwRZwDYC6ZHMmSM',
      'OBSERVED: commissioned evidence treated the entire 506x428 static sheet as one corpus with ten named families including Walk, Run, Duck, Climb, Off Ladder, Push and Pick Item.',
      'UNKNOWN: source-authentic chronology/exposure/root path/obstacle choreography/clearance/support force. Source grants no timing authority.',
      'authored timing: INFERRED / STREET_FIGHTER-CAPCOM. rights firewall: independent abstract rig only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/redistribution/close imitation.',
      'thesis: lead foot clears and catches beyond a low obstacle while rear support remains behind; root/COM traverse that split-support bridge; trailing foot clears late into an overlong catch; shorter corrections pay surviving debt.',
      ''
    ]
    for k in MOTION['keys']:
        out.append(f"{k['key_id']} {k['name']} · {k['timing_class']}/{k['hold_frames']}f · {k['timing_provenance']} · support={k['support']['owner']} · phase={k['phase']} · rootΔ={k['root_spacing_px']}px · lean={k['torso_lean_deg']:+}° · lag={k['free_foot_lag_deg']:+}° · clearance={k['clearance_state']}")
        out.append(ascii_pose(k)); out.append(f"causal: {k['causal_role']}"); out.append('')
    return '\n'.join(out).rstrip()+'\n'
def make_spa(a,j,v):
    ab64=base64.b64encode(gzip.compress(a.encode(),mtime=0)).decode(); jb64=base64.b64encode(gzip.compress(j.encode(),mtime=0)).decode(); vb64=base64.b64encode(v).decode()
    title='ASCII Kinesis V2 · Locomotion 025 · Low Obstacle Split Support / Trailing Clearance Runout'
    def parts(s,n=4000): return ',\n'.join(json.dumps(s[i:i+n]) for i in range(0,len(s),n))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>:root{{color-scheme:dark}}body{{margin:0;background:#0f1114;color:#edf0f3;font-family:system-ui,sans-serif}}header{{padding:14px 18px;border-bottom:1px solid #343943}}nav{{display:flex;gap:8px}}button{{font:inherit;padding:7px 12px;background:#1a1e24;color:inherit;border:1px solid #4a515d;border-radius:6px}}button[aria-selected="true"]{{background:#303641}}main{{padding:14px 18px}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #343943;padding:12px;max-height:78vh}}video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #343943}}</style></head>
<body><header><h1>{title}</h1><nav><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header>
<main><section id="ascii"><pre id="ascii-pre">loading exact persisted ASCII...</pre></section><section id="json" hidden><pre id="json-pre">loading exact persisted JSON...</pre></section><section id="video" hidden><video id="motion-video" controls loop muted playsinline></video></section></main>
<script>
const A=[
{parts(ab64)}
].join("");
const J=[
{parts(jb64)}
].join("");
const V=[
{parts(vb64)}
].join("");
document.getElementById("motion-video").src="data:video/mp4;base64,"+V;
async function gunzip64(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}}
Promise.all([gunzip64(A),gunzip64(J)]).then(([a,j])=>{{document.getElementById("ascii-pre").textContent=a;document.getElementById("json-pre").textContent=j;}});
const buttons=[...document.querySelectorAll('button[data-view]')];for(const b of buttons)b.addEventListener('click',()=>{{for(const q of buttons)q.setAttribute('aria-selected',q===b?'true':'false');for(const x of document.querySelectorAll('main section'))x.hidden=x.id!==b.dataset.view;}});
</script></body></html>
'''
def main():
    FRAMES.mkdir(exist_ok=True)
    for p in FRAMES.glob('*.png'):p.unlink()
    idx=0
    for k in MOTION['keys']:
        for _ in range(int(k['hold_frames'])):
            draw_frame(k,idx,FRAMES/f'frame-{idx:04d}.png'); idx+=1
    assert idx==int(MOTION['timing']['total_frames'])
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(FRAMES/'frame-%04d.png'),'-vf','scale=480:270:flags=neighbor','-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)],check=True)
    a=make_contact_sheet(); ASCII.write_text(a,encoding='utf-8')
    j=(HERE/'motion.json').read_text(encoding='utf-8'); SPA.write_text(make_spa(a,j,MP4.read_bytes()),encoding='utf-8')
if __name__=='__main__':main()
