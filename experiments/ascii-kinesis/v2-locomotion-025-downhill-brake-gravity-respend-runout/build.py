#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
MOTION=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
W,H=map(int,MOTION['rig']['viewport']); FPS=int(MOTION['timing']['fps'])
FRAMES=HERE/'_frames'; MP4=HERE/'_authoritative.mp4'; ASCII=HERE/'contact-sheet.txt'; SPA=HERE/'downhill-brake-gravity-respend-runout.motion.html'

def ground_y(x):
    g=MOTION['rig']['ground_model']
    return float(g['y_at_x50']) + float(g['rise_per_px'])*(float(x)-50.0)

def body(k):
    rx,ry=map(float,k['root']); lean=math.radians(float(k['torso_lean_deg']))
    vx=math.sin(lean); vy=-math.cos(lean)
    chest=(rx+vx*43,ry+vy*43); head=(chest[0]+vx*25,chest[1]+vy*25)
    com=tuple(map(float,k['com'])); lf=tuple(map(float,k['left_foot'])); rf=tuple(map(float,k['right_foot']))
    lag=math.radians(float(k.get('arm_lag_deg',0)))
    sh=(chest[0],chest[1]+4)
    lead=(sh[0]+math.cos(lag)*31,sh[1]+math.sin(lag)*31)
    trail=(sh[0]-math.cos(lag)*26,sh[1]-math.sin(lag)*26)
    return {'root':(rx,ry),'com':com,'chest':chest,'head':head,'lf':lf,'rf':rf,'lead':lead,'trail':trail}

def supported(k,side):
    return str(k['support'][side]) in ('PLANTED_FIXED','UNLOADING_FIXED')

def probing(k,side):
    return str(k['support'][side])=='PROBE'

def draw_frame(k,idx,path):
    im=Image.new('RGB',(W,H),(13,15,18)); d=ImageDraw.Draw(im)
    ground=[(x,ground_y(x)) for x in range(25,W-15,8)]
    d.line(ground,fill=(86,92,101),width=3)
    pts=[tuple(map(float,q['root'])) for q in MOTION['keys']]
    d.line(pts,fill=(48,55,64),width=3)
    for p in pts:d.ellipse((p[0]-2,p[1]-2,p[0]+2,p[1]+2),fill=(75,84,95))
    p=body(k)
    bodyc=(236,239,244); limb=(178,188,202); rootc=(246,204,88); supportc=(104,204,145); probec=(239,177,93); comc=(225,126,150)
    rx,ry=p['root']; cx,cy=p['com']
    for nm,side in [('lf','left'),('rf','right')]:
        fx,fy=p[nm]
        knee=((fx+rx)/2+(8 if side=='left' else -8),(fy+ry)/2-5)
        d.line((rx,ry,*knee,*p[nm]),fill=limb,width=4)
        if supported(k,side):
            d.ellipse((fx-8,fy-5,fx+8,fy+5),fill=supportc)
            d.line((fx,fy,cx,cy),fill=supportc,width=2)
        elif probing(k,side):
            d.ellipse((fx-8,fy-5,fx+8,fy+5),outline=probec,width=3)
        else:
            d.ellipse((fx-7,fy-4,fx+7,fy+4),outline=bodyc,width=2)
    d.line((*p['root'],*p['chest']),fill=bodyc,width=6)
    hx,hy=p['head']; d.ellipse((hx-9,hy-9,hx+9,hy+9),outline=bodyc,width=4)
    d.line((*p['chest'],*p['lead']),fill=limb,width=4); d.line((*p['chest'],*p['trail']),fill=limb,width=4)
    d.polygon([(rx,ry-7),(rx+7,ry),(rx,ry+7),(rx-7,ry)],outline=rootc,width=3)
    d.ellipse((cx-5,cy-5,cx+5,cy+5),fill=comc)
    d.text((12,10),f"{k['key_id']}  {k['name']}",fill=(149,159,173))
    d.text((12,28),f"owner {k['support']['owner']} | root delta {k['root_spacing_px']} | {k['phase']} | {k['timing_class']}",fill=(113,125,140))
    d.text((12,46),"downhill field  >>>",fill=(109,120,134))
    im.save(path,'PNG',optimize=False)

def grid_line(g,x0,y0,x1,y1,ch):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        if 0<=y0<len(g) and 0<=x0<len(g[0]): g[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def to_grid(pt):
    x,y=pt
    return int(round((x-35)/(W-70)*83)),int(round((y-105)/(H-115)*23))

def ascii_pose(k):
    g=[[' ']*84 for _ in range(24)]
    slope=[to_grid((x,ground_y(x))) for x in range(40,W-25,8)]
    for a,b in zip(slope,slope[1:]): grid_line(g,*a,*b,'_')
    route=[to_grid(tuple(map(float,q['root']))) for q in MOTION['keys']]
    for a,b in zip(route,route[1:]): grid_line(g,*a,*b,'.')
    p=body(k)
    for nm in ('lf','rf'): grid_line(g,*to_grid(p[nm]),*to_grid(p['root']),'/')
    grid_line(g,*to_grid(p['root']),*to_grid(p['chest']),'|')
    grid_line(g,*to_grid(p['chest']),*to_grid(p['lead']),'-')
    grid_line(g,*to_grid(p['chest']),*to_grid(p['trail']),'-')
    for nm,ch in [('head','O'),('chest','T'),('root','@'),('com','c')]:
        x,y=to_grid(p[nm])
        if 0<=y<24 and 0<=x<84:g[y][x]=ch
    for nm,side in [('lf','left'),('rf','right')]:
        x,y=to_grid(p[nm])
        if 0<=y<24 and 0<=x<84:
            g[y][x]='*' if supported(k,side) else ('?' if probing(k,side) else '~')
    return '\n'.join(''.join(r).rstrip() for r in g)

def make_contact_sheet():
    out=[
      'ASCII KINESIS V2 · LOCOMOTION 025 · DOWNHILL BRAKE / GRAVITY RESPEND / CATCH RUNOUT',
      'legend: @ root · c COM · * trusted fixed foot support · ? probe contact · ~ free foot · . authored root route · _ downhill ground',
      'source evidence: Garfield (The Curse of Cleofatra) / Garfield: Caught in the Act / Sega Genesis / TSR asset 123160 / Home Center artifact 1EcndzQbqHcHQ99qxELwoXpttbCITiJJ56WhzIgjBGMc',
      'OBSERVED: whole static sheet includes Run, Slip, Edge, Fall, Push and jump/travel families; Push shows trustworthy contact with suppressed translation while Slip shows visible contact with continuing translation.',
      'OBSERVED CAMPAIGN HANDLE: downhill braking was explicitly proposed as the next scene where friction is trustworthy but gravity continuously re-spends root momentum after each catch.',
      'UNKNOWN: source-authentic chronology, exposure counts, exact root coordinates, friction coefficients, gameplay velocity curves. Source grants NO timing authority.',
      'authored timing: INFERRED / STREET_FIGHTER-CAPCOM. rights firewall: independent abstract ASCII rig only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/redistribution/close imitation.',
      'thesis: a trusted brake catch can reduce downhill velocity without ending the action; the field re-expands root spacing after each catch, producing a later overlong runout catch and shorter displaced corrections.',
      ''
    ]
    for k in MOTION['keys']:
        out.append(f"{k['key_id']} {k['name']} · {k['timing_class']}/{k['hold_frames']}f · {k['timing_provenance']} · support={k['support']['owner']} · phase={k['phase']} · rootΔ={k['root_spacing_px']}px · lean={k['torso_lean_deg']:+}° · armLag={k['arm_lag_deg']:+}°")
        out.append(ascii_pose(k))
        out.append(f"causal: {k['causal_role']}")
        out.append('')
    return '\n'.join(out).rstrip()+'\n'

def make_spa(a,j,v):
    ab64=base64.b64encode(gzip.compress(a.encode(),mtime=0)).decode()
    jb64=base64.b64encode(gzip.compress(j.encode(),mtime=0)).decode()
    vb64=base64.b64encode(v).decode()
    title='ASCII Kinesis V2 · Locomotion 025 · Downhill Brake / Gravity Respend / Catch Runout'
    def js_parts(s,n=4000): return ',\n'.join(json.dumps(s[i:i+n]) for i in range(0,len(s),n))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>:root{{color-scheme:dark}}body{{margin:0;background:#0f1114;color:#edf0f3;font-family:system-ui,sans-serif}}header{{padding:14px 18px;border-bottom:1px solid #343943}}nav{{display:flex;gap:8px}}button{{font:inherit;padding:7px 12px;background:#1a1e24;color:inherit;border:1px solid #4a515d;border-radius:6px}}button[aria-selected="true"]{{background:#303641}}main{{padding:14px 18px}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #343943;padding:12px;max-height:78vh}}video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #343943}}</style></head>
<body><header><h1>{title}</h1><nav><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header>
<main><section id="ascii"><pre id="ascii-pre">loading exact persisted ASCII...</pre></section><section id="json" hidden><pre id="json-pre">loading exact persisted JSON...</pre></section><section id="video" hidden><video id="motion-video" controls loop muted playsinline></video></section></main>
<script>
const A=[
{js_parts(ab64)}
].join("");
const J=[
{js_parts(jb64)}
].join("");
const V=[
{js_parts(vb64)}
].join("");
const VIDEO_URI="data:video/mp4;base64,"+V;
document.getElementById("motion-video").src=VIDEO_URI;
async function gunzip64(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}}
Promise.all([gunzip64(A),gunzip64(J)]).then(([a,j])=>{{document.getElementById("ascii-pre").textContent=a;document.getElementById("json-pre").textContent=j;}});
const buttons=[...document.querySelectorAll('button[data-view]')];for(const b of buttons)b.addEventListener('click',()=>{{for(const q of buttons)q.setAttribute('aria-selected',q===b?'true':'false');for(const x of document.querySelectorAll('main section'))x.hidden=x.id!==b.dataset.view;}});
</script></body></html>
'''

def main():
    FRAMES.mkdir(exist_ok=True)
    for p in FRAMES.glob('*.png'): p.unlink()
    idx=0
    for k in MOTION['keys']:
        for _ in range(int(k['hold_frames'])):
            draw_frame(k,idx,FRAMES/f'frame-{idx:04d}.png'); idx+=1
    assert idx==int(MOTION['timing']['total_frames'])
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(FRAMES/'frame-%04d.png'),'-vf','scale=480:270:flags=neighbor','-c:v','libx264','-preset','veryslow','-crf','40','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)],check=True)
    a=make_contact_sheet(); ASCII.write_text(a,encoding='utf-8')
    j=(HERE/'motion.json').read_text(encoding='utf-8')
    SPA.write_text(make_spa(a,j,MP4.read_bytes()),encoding='utf-8')
if __name__=='__main__': main()
