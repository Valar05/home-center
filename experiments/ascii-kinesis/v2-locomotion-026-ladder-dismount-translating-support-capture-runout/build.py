#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw

HERE=Path(__file__).resolve().parent
MOTION=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
W,H=map(int,MOTION['rig']['viewport']); FPS=int(MOTION['timing']['fps'])
FRAMES=HERE/'_frames'; MP4=HERE/'_authoritative.mp4'; ASCII=HERE/'contact-sheet.txt'; SPA=HERE/'ladder-dismount-translating-support-capture-runout.motion.html'

def body(k):
    rx,ry=map(float,k['root']); lean=math.radians(float(k['torso_lean_deg']))
    vx=math.sin(lean); vy=-math.cos(lean)
    chest=(rx+vx*34,ry+vy*34); head=(chest[0]+vx*19,chest[1]+vy*19)
    com=tuple(map(float,k['com']))
    return {
        'root':(rx,ry),'com':com,'chest':chest,'head':head,
        'lf':tuple(map(float,k['left_foot'])),'rf':tuple(map(float,k['right_foot'])),
        'lh':tuple(map(float,k['left_hand'])),'rh':tuple(map(float,k['right_hand']))
    }

def state(k,name): return str(k['support'].get(name,'FREE'))
def is_owning(s): return s in ('RUNG_FIXED','RUNG_UNLOADING','PLATFORM_PLANTED','PLATFORM_UNLOADING')
def is_probe(s): return 'PROBE' in s or 'TOUCH' in s

def draw_frame(k,idx,path):
    im=Image.new('RGB',(W,H),(12,14,18)); d=ImageDraw.Draw(im)
    lx=int(MOTION['rig']['ladder']['x']); top=int(MOTION['rig']['ladder']['top']); bot=int(MOTION['rig']['ladder']['bottom'])
    d.line((lx-9,top,lx-9,bot),fill=(88,95,105),width=3); d.line((lx+9,top,lx+9,bot),fill=(88,95,105),width=3)
    for y in range(top+8,bot,20): d.line((lx-9,y,lx+9,y),fill=(88,95,105),width=2)
    px=float(k['platform_x']); py=float(MOTION['rig']['platform']['y']); pw=float(MOTION['rig']['platform']['width']); ph=float(MOTION['rig']['platform']['height'])
    d.rounded_rectangle((px-pw/2,py,px+pw/2,py+ph),radius=3,fill=(64,78,94),outline=(135,151,170),width=2)
    d.line((px-38,py+16,px+38,py+16),fill=(88,104,122),width=2)
    d.polygon([(px+38,py+12),(px+48,py+16),(px+38,py+20)],fill=(88,104,122))
    pts=[tuple(map(float,q['root'])) for q in MOTION['keys']]
    d.line(pts,fill=(48,55,65),width=2)
    for q in pts: d.ellipse((q[0]-2,q[1]-2,q[0]+2,q[1]+2),fill=(70,80,94))
    p=body(k)
    bodyc=(236,239,244); limb=(177,188,203); rootc=(247,205,91); comc=(224,123,151)
    supportc=(106,207,151); probec=(242,177,94); rungc=(121,174,231)
    rx,ry=p['root']; cx,cy=p['com']
    for nm,side in [('lf','left_foot'),('rf','right_foot')]:
        fx,fy=p[nm]; knee=((fx+rx)/2+(7 if nm=='lf' else -7),(fy+ry)/2-4)
        d.line((rx,ry,*knee,*p[nm]),fill=limb,width=4)
        s=state(k,side)
        if is_owning(s):
            d.ellipse((fx-7,fy-4,fx+7,fy+4),fill=supportc if 'PLATFORM' in s else rungc)
            d.line((fx,fy,cx,cy),fill=supportc if 'PLATFORM' in s else rungc,width=2)
        elif is_probe(s): d.ellipse((fx-7,fy-4,fx+7,fy+4),outline=probec,width=3)
        else: d.ellipse((fx-6,fy-3,fx+6,fy+3),outline=bodyc,width=2)
    d.line((*p['root'],*p['chest']),fill=bodyc,width=6)
    hx,hy=p['head']; d.ellipse((hx-8,hy-8,hx+8,hy+8),outline=bodyc,width=3)
    for nm,handkey in [('lh','left_hand'),('rh','right_hand')]:
        hx2,hy2=p[nm]; d.line((*p['chest'],hx2,hy2),fill=limb,width=4); s=state(k,handkey)
        if is_owning(s):
            d.ellipse((hx2-5,hy2-5,hx2+5,hy2+5),fill=rungc); d.line((hx2,hy2,cx,cy),fill=rungc,width=2)
        else: d.ellipse((hx2-4,hy2-4,hx2+4,hy2+4),outline=bodyc,width=2)
    d.polygon([(rx,ry-6),(rx+6,ry),(rx,ry+6),(rx-6,ry)],outline=rootc,width=3)
    d.ellipse((cx-4,cy-4,cx+4,cy+4),fill=comc)
    d.text((10,8),f"{k['key_id']}  {k['name']}",fill=(158,168,184))
    d.text((10,25),f"owner {k['support']['owner']} | root delta {k['root_spacing_px']} | deck v {k['platform_v']} | {k['timing_class']}",fill=(117,130,148))
    d.text((10,42),"stationary ladder  ||   translating deck  >>>",fill=(102,116,133))
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
    return int(round((x-34)/(W-58)*88)),int(round((y-64)/(H-70)*24))

def ascii_pose(k):
    g=[[' ']*90 for _ in range(25)]
    lx=int(MOTION['rig']['ladder']['x'])
    for y in range(72,229,20):
        a=to_grid((lx-9,y)); b=to_grid((lx+9,y)); grid_line(g,*a,*b,'=')
    a=to_grid((lx-9,70)); b=to_grid((lx-9,228)); grid_line(g,*a,*b,'|')
    a=to_grid((lx+9,70)); b=to_grid((lx+9,228)); grid_line(g,*a,*b,'|')
    px=float(k['platform_x']); py=float(MOTION['rig']['platform']['y']); pw=float(MOTION['rig']['platform']['width'])
    a=to_grid((px-pw/2,py)); b=to_grid((px+pw/2,py)); grid_line(g,*a,*b,'_')
    route=[to_grid(tuple(map(float,q['root']))) for q in MOTION['keys']]
    for a,b in zip(route,route[1:]): grid_line(g,*a,*b,'.')
    p=body(k)
    for nm in ('lf','rf'): grid_line(g,*to_grid(p[nm]),*to_grid(p['root']),'/')
    grid_line(g,*to_grid(p['root']),*to_grid(p['chest']),'|')
    for nm in ('lh','rh'): grid_line(g,*to_grid(p['chest']),*to_grid(p[nm]),'-')
    for nm,ch in [('head','O'),('chest','T'),('root','@'),('com','c')]:
        x,y=to_grid(p[nm])
        if 0<=y<25 and 0<=x<90:g[y][x]=ch
    for nm,key in [('lf','left_foot'),('rf','right_foot'),('lh','left_hand'),('rh','right_hand')]:
        x,y=to_grid(p[nm]); s=state(k,key)
        if 0<=y<25 and 0<=x<90:g[y][x]='*' if is_owning(s) else ('?' if is_probe(s) else '~')
    ax,ay=to_grid((px+pw/2+8,py))
    if 0<=ay<25 and 0<=ax<90:g[ay][ax]='>'
    return '\n'.join(''.join(r).rstrip() for r in g)

def make_contact_sheet():
    out=[
      'ASCII KINESIS V2 · LOCOMOTION 026 · LADDER DISMOUNT / TRANSLATING SUPPORT CAPTURE / RUNOUT',
      'legend: @ root · c COM · * authoritative support · ? low-confidence probe/touch · ~ free endpoint · . authored root route · |/= stationary ladder · _=> translating platform',
      'source evidence: Bullwinkle / The Adventures of Rocky and Bullwinkle and Friends / NES / TSR asset 81106 / Home Center artifact 1zQGdJx7uIqTnvJlHp2NfydUu_EDDNvt01tCAlQvlYQ8',
      'OBSERVED: whole static sheet exposes Charge, Idle, Using Stairs, Walking; these distinguish rest, level travel, high-commitment travel, and discrete-height locomotion. Animated GIFs (0).',
      'INFERRED CAMPAIGN HANDLE: commissioned evidence promotes ladder dismount onto a moving platform, requiring hands/rungs to transfer support authority to translating foot support without a freefall gap.',
      'UNKNOWN: source-authentic chronology/exposures/stair direction/root displacement/contact frames/platform motion/source timing. Source grants NO timing authority.',
      'authored timing: INFERRED / STREET_FIGHTER-CAPCOM. rights firewall: independent abstract ASCII rig only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/redistribution/close imitation.',
      'thesis: translating foot support becomes trustworthy before final ladder release; last-hand pivot delays velocity inheritance; release produces an overlong deck catch, shorter correction, and displaced deck-relative settle.',
      ''
    ]
    for k in MOTION['keys']:
        sup=k['support']
        out.append(f"{k['key_id']} {k['name']} · {k['timing_class']}/{k['hold_frames']}f · {k['timing_provenance']} · owner={sup['owner']} · phase={k['phase']} · rootΔ={k['root_spacing_px']}px · deckX={k['platform_x']} · deckV={k['platform_v']}")
        out.append(ascii_pose(k)); out.append(f"causal: {k['causal_role']}"); out.append('')
    return '\n'.join(out).rstrip()+'\n'

def make_spa(a,j,v):
    ab64=base64.b64encode(gzip.compress(a.encode(),mtime=0)).decode()
    jb64=base64.b64encode(gzip.compress(j.encode(),mtime=0)).decode()
    vb64=base64.b64encode(v).decode()
    title='ASCII Kinesis V2 · Locomotion 026 · Ladder Dismount / Translating Support Capture / Runout'
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
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(FRAMES/'frame-%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','35','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)],check=True)
    a=make_contact_sheet(); ASCII.write_text(a,encoding='utf-8')
    j=(HERE/'motion.json').read_text(encoding='utf-8')
    SPA.write_text(make_spa(a,j,MP4.read_bytes()),encoding='utf-8')

if __name__=='__main__': main()
