#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
MOTION=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
W,H=map(int,MOTION['rig']['viewport']); FPS=int(MOTION['timing']['fps']); G=int(MOTION['rig']['ground_y'])
FRAMES=HERE/'_frames'; MP4=HERE/'_authoritative.mp4'; ASCII=HERE/'contact-sheet.txt'; SPA=HERE/'friction-break-slide-catch-runout.motion.html'

def fixed(v): return 'FIXED' in str(v)
def sliding(v): return 'SLIDING' in str(v)
def probe(v): return 'PROBE' in str(v)

def body(k):
    rx,ry=map(float,k['root']); lean=math.radians(float(k['torso_lean_deg']))
    vx,vy=math.sin(lean),-math.cos(lean); lag=float(k.get('secondary_lag_px',0))
    chest=(rx+vx*44+lag*.35,ry+vy*44)
    head=(chest[0]+vx*27+lag*.65,chest[1]+vy*27)
    return {'root':(rx,ry),'com':tuple(map(float,k['com'])),'chest':chest,'head':head,
            'lf':tuple(map(float,k['left_foot'])),'rf':tuple(map(float,k['right_foot']))}

def draw_route(d):
    pts=[tuple(map(float,k['root'])) for k in MOTION['keys']]
    d.line(pts,fill=(52,59,68),width=2)
    for p in pts:d.ellipse((p[0]-2,p[1]-2,p[0]+2,p[1]+2),fill=(86,94,106))

def draw_ground(d):
    d.line((24,G,616,G),fill=(105,112,124),width=2)
    for x in range(40,621,20):
        d.line((x,G-5,x,G+5),fill=(86,94,106),width=1)
        if x%40==0:d.text((x-7,G+8),str(x),fill=(75,84,96))

def draw_frame(k,idx,path):
    im=Image.new('RGB',(W,H),(13,15,18)); d=ImageDraw.Draw(im); draw_ground(d); draw_route(d); p=body(k)
    bodyc=(235,239,244); secondary=(170,181,196); rootc=(247,207,92); fixedc=(112,201,144); slidec=(245,164,91); probec=(146,191,235); comc=(225,126,150)
    rx,ry=p['root']; cx,cy=p['chest']; hx,hy=p['head']
    for side,nm in [('left','lf'),('right','rf')]:
        sv=k['support'][side]
        if fixed(sv): d.line((*p[nm],*p['com']),fill=fixedc,width=2)
        elif sliding(sv): d.line((*p[nm],*p['com']),fill=slidec,width=2)
        elif probe(sv): d.line((*p[nm],*p['com']),fill=probec,width=1)
    for side,nm in [('left','lf'),('right','rf')]:
        fx,fy=p[nm]; knee=((fx+rx)/2+(9 if side=='left' else -9),(fy+ry)/2-5)
        d.line((rx,ry,*knee,*p[nm]),fill=secondary,width=4)
        sv=k['support'][side]; box=(fx-9,fy-4,fx+9,fy+4)
        if fixed(sv): d.rectangle(box,fill=fixedc)
        elif sliding(sv): d.rectangle(box,fill=slidec)
        elif probe(sv): d.rectangle(box,outline=probec,width=2)
        else: d.rectangle(box,outline=bodyc,width=2)
    d.line((rx,ry,cx,cy),fill=bodyc,width=6)
    d.line((cx-18,cy+4,cx+20,cy-2),fill=secondary,width=4)
    d.ellipse((hx-9,hy-9,hx+9,hy+9),outline=bodyc,width=4)
    d.polygon([(rx,ry-7),(rx+7,ry),(rx,ry+7),(rx-7,ry)],outline=rootc,width=3)
    qx,qy=p['com']; d.ellipse((qx-5,qy-5,qx+5,qy+5),fill=comc)
    d.text((12,10),f"{k['key_id']}  {k['name']}",fill=(150,160,173))
    d.text((12,28),f"owner {k['support']['owner']} | rootD {k['root_spacing_px']} | phase {k['phase']}",fill=(112,124,139))
    d.text((12,46),f"L {k['support']['left']}  R {k['support']['right']}  lag {k['secondary_lag_px']:+}px",fill=(112,124,139))
    if sliding(k['support']['left']):
        d.line((p['lf'][0]-14,G+24,p['lf'][0]+14,G+24),fill=slidec,width=2)
    im.save(path,'PNG',optimize=False)

def grid_line(g,x0,y0,x1,y1,ch):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        if 0<=y0<len(g) and 0<=x0<len(g[0]): g[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy:err+=dy;x0+=sx
        if e2<=dx:err+=dx;y0+=sy

def to_grid(pt):
    x,y=pt
    return int(round((x-35)/(W-70)*83)),int(round((y-125)/(H-145)*23))

def ascii_pose(k):
    g=[[' ']*84 for _ in range(24)]
    gy=int(round((G-125)/(H-145)*23))
    if 0<=gy<24:
        for x in range(84): g[gy][x]='_'
        for x in range(1,84,6): g[gy][x]='|'
    route=[to_grid(tuple(map(float,q['root']))) for q in MOTION['keys']]
    for a,b in zip(route,route[1:]):grid_line(g,*a,*b,'.')
    p=body(k); r=to_grid(p['root']); c=to_grid(p['chest'])
    for nm in ('lf','rf'): grid_line(g,*to_grid(p[nm]),*r,'/')
    grid_line(g,*r,*c,'|')
    cx,cy=c
    if 0<=cy<24:
        for x in range(max(0,cx-3),min(84,cx+4)):g[cy][x]='-'
    for nm,ch in [('head','O'),('chest','T'),('root','@'),('com','c')]:
        x,y=to_grid(p[nm])
        if 0<=y<24 and 0<=x<84:g[y][x]=ch
    for nm,side in [('lf','left'),('rf','right')]:
        x,y=to_grid(p[nm]); sv=k['support'][side]
        if 0<=y<24 and 0<=x<84:
            g[y][x] = '*' if fixed(sv) else ('=' if sliding(sv) else ('?' if probe(sv) else '~'))
    return '\n'.join(''.join(r).rstrip() for r in g)

def make_contact_sheet():
    out=[
      'ASCII KINESIS V2 · LOCOMOTION 025 · FRICTION BREAK / SLIDE CATCH / RUNOUT',
      'legend: @ root · c COM · * world-fixed foot · = sliding-contact foot · ? probe contact · ~ free foot · . root route · | fixed ground ruler ticks',
      'source evidence: Ride Armor / Mega Man X / SNES / TSR asset 133611 / Home Center evidence document 13LNIYKD8DmWrc9trwiicS873bX-p-lku8QVNqdFk2Yc',
      'OBSERVED: whole static source family contains distinct walking, jumping/landing, dashing, action variants, and disassembled/auxiliary material; source timing was not measured.',
      'UNKNOWN: source-authentic chronology/exposure/root/support/friction behavior. Source grants no timing authority.',
      'authored timing: INFERRED / STREET_FIGHTER-CAPCOM. rights firewall: evidence-only source; independent abstract rig; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/redistribution/close imitation.',
      'thesis: a trusted support exceeds tangential authority and visibly slides while contact survives; opposite probe earns fixed catch, root/COM overruns it, then shorter corrections and secondary lag finish displaced.',
      ''
    ]
    for k in MOTION['keys']:
        out.append(f"{k['key_id']} {k['name']} · {k['timing_class']}/{k['hold_frames']}f · {k['timing_provenance']} · support={k['support']['owner']} · phase={k['phase']} · rootD={k['root_spacing_px']}px · lean={k['torso_lean_deg']:+}deg · lag={k['secondary_lag_px']:+}px")
        out.append(ascii_pose(k)); out.append(f"causal: {k['causal_role']}"); out.append('')
    return '\n'.join(out).rstrip()+'\n'

def make_spa(a,j,v):
    ab64=base64.b64encode(gzip.compress(a.encode(),mtime=0)).decode()
    jb64=base64.b64encode(gzip.compress(j.encode(),mtime=0)).decode()
    vb64=base64.b64encode(v).decode()
    title='ASCII Kinesis V2 · Locomotion 025 · Friction Break / Slide Catch / Runout'
    def parts(s,n=4000):return ',\n'.join(json.dumps(s[i:i+n]) for i in range(0,len(s),n))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>:root{{color-scheme:dark}}body{{margin:0;background:#0f1114;color:#edf0f3;font-family:system-ui,sans-serif}}header{{padding:14px 18px;border-bottom:1px solid #343943}}nav{{display:flex;gap:8px}}button{{font:inherit;padding:7px 12px;background:#1a1e24;color:inherit;border:1px solid #4a515d;border-radius:6px}}button[aria-selected="true"]{{background:#303641}}main{{padding:14px 18px}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #343943;padding:12px;max-height:78vh}}video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #343943}}</style></head>
<body><header><h1>{title}</h1><nav><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header>
<main><section id="ascii"><pre id="ascii-pre">loading exact persisted ASCII...</pre></section><section id="json" hidden><pre id="json-pre">loading exact persisted JSON...</pre></section><section id="video" hidden><video id="motion-video" controls loop muted playsinline></video></section></main>
<script>
const A=[{parts(ab64)}].join("");
const J=[{parts(jb64)}].join("");
const V=[{parts(vb64)}].join("");
const VIDEO_URI="data:video/mp4;base64,"+V;document.getElementById("motion-video").src=VIDEO_URI;
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
            draw_frame(k,idx,FRAMES/f'frame-{idx:04d}.png');idx+=1
    assert idx==int(MOTION['timing']['total_frames'])
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(FRAMES/'frame-%04d.png'),'-vf','scale=480:270:flags=neighbor','-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)],check=True)
    a=make_contact_sheet(); ASCII.write_text(a,encoding='utf-8')
    j=(HERE/'motion.json').read_text(encoding='utf-8')
    SPA.write_text(make_spa(a,j,MP4.read_bytes()),encoding='utf-8')
if __name__=='__main__':main()
