#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
MOTION=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
W,H=map(int,MOTION['rig']['viewport']); FPS=int(MOTION['timing']['fps']); G=int(MOTION['rig']['ground_y'])
FRAMES=HERE/'_frames'; MP4=HERE/'_authoritative.mp4'; ASCII=HERE/'contact-sheet.txt'
SPA=HERE/'relationship-drag-support-revocation-runout.motion.html'

def support_trusted(v):
    s=str(v)
    return 'PLANTED_FIXED' in s or 'UNLOADING_FIXED' in s

def body(root,com,lf,rf,lean_deg,scale=1.0):
    rx,ry=map(float,root); lean=math.radians(float(lean_deg))
    vx=math.sin(lean); vy=-math.cos(lean)
    chest=(rx+vx*43*scale,ry+vy*43*scale)
    head=(chest[0]+vx*26*scale,chest[1]+vy*26*scale)
    return {'root':(rx,ry),'com':tuple(map(float,com)),'lf':tuple(map(float,lf)),'rf':tuple(map(float,rf)),
            'chest':chest,'head':head}

def actor(k,prefix):
    return body(k[f'{prefix}_root'],k[f'{prefix}_com'],k[f'{prefix}_left_foot'],k[f'{prefix}_right_foot'],
                k[f'{prefix}_lean_deg'], 1.0 if prefix=='a' else .92)

def shoulder_hand(p, toward_x, arm_drop=7):
    cx,cy=p['chest']; sign=1 if toward_x>=cx else -1
    return (cx+sign*31,cy+arm_drop)

def draw_route(d,prefix,fill):
    pts=[tuple(map(float,k[f'{prefix}_root'])) for k in MOTION['keys']]
    d.line(pts,fill=fill,width=2)
    for p in pts:d.ellipse((p[0]-2,p[1]-2,p[0]+2,p[1]+2),fill=fill)

def draw_person(d,p,support,root_fill,com_fill,body_fill,limb_fill,tag):
    rx,ry=p['root']
    for nm,side in [('lf','left'),('rf','right')]:
        foot=p[nm]; fx,fy=foot
        knee=((fx+rx)/2+(7 if side=='left' else -7),(fy+ry)/2-3)
        d.line((rx,ry,*knee,*foot),fill=limb_fill,width=4)
        if support_trusted(support[side]): d.ellipse((fx-8,fy-5,fx+8,fy+5),fill=(116,201,145))
        else: d.ellipse((fx-7,fy-4,fx+7,fy+4),outline=body_fill,width=2)
    d.line((*p['root'],*p['chest']),fill=body_fill,width=6)
    hx,hy=p['head']; d.ellipse((hx-9,hy-9,hx+9,hy+9),outline=body_fill,width=4)
    back=shoulder_hand(p,p['chest'][0]-24,9); d.line((*p['chest'],*back),fill=limb_fill,width=4)
    d.polygon([(rx,ry-7),(rx+7,ry),(rx,ry+7),(rx-7,ry)],outline=root_fill,width=3)
    cx,cy=p['com']; d.ellipse((cx-5,cy-5,cx+5,cy+5),fill=com_fill); d.text((rx-4,ry+12),tag,fill=body_fill)

def relationship_active(k): return not str(k['relationship']['state']).startswith('NONE')

def draw_frame(k,idx,path):
    im=Image.new('RGB',(W,H),(13,15,18)); d=ImageDraw.Draw(im)
    d.line((24,G,616,G),fill=(82,89,98),width=2)
    draw_route(d,'a',(68,77,88)); draw_route(d,'b',(49,57,66))
    a=actor(k,'a'); b=actor(k,'b')
    draw_person(d,b,k['b_support'],(224,170,93),(180,137,224),(190,199,211),(129,140,155),'B')
    draw_person(d,a,k['a_support'],(247,207,92),(225,126,150),(237,241,245),(171,183,198),'A')
    if relationship_active(k):
        fr=tuple(map(float,k['relationship']['frame'])); ah=shoulder_hand(a,b['chest'][0],6); bh=shoulder_hand(b,a['chest'][0],6)
        state=k['relationship']['state']; loaded='LOADED' in state or 'TRANSFER' in state
        col=(246,158,89) if loaded else (127,190,235)
        d.line((*a['chest'],*ah),fill=(171,183,198),width=4); d.line((*b['chest'],*bh),fill=(129,140,155),width=4)
        d.line((*ah,*fr),fill=col,width=4); d.line((*fr,*bh),fill=col,width=4)
        x,y=fr; d.ellipse((x-7,y-7,x+7,y+7),outline=col,width=3); d.text((x-4,y-5),'R',fill=col)
    elif k['phase'] in ('FRAME_RELEASE','FREE_OVERRUN','BRAKE_COMPRESSION'):
        lag={'FRAME_RELEASE':32,'FREE_OVERRUN':26,'BRAKE_COMPRESSION':17}[k['phase']]
        ah=(a['chest'][0]+lag,a['chest'][1]+7); d.line((*a['chest'],*ah),fill=(171,183,198),width=4)
    d.text((12,10),f"{k['key_id']}  {k['name']}",fill=(150,160,173))
    d.text((12,28),f"A:{k['a_support']['owner']}  B:{k['b_support']['owner']}  R:{k['relationship']['state']}",fill=(111,123,138))
    d.text((12,45),f"A d {k['a_root_spacing_px']:.1f}  B d {k['b_root_spacing_px']:.1f}  lag {k['partner_lag_px']}  phase {k['phase']}",fill=(111,123,138))
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
    x,y=pt; return int(round((x-30)/(W-60)*95)),int(round((y-125)/(H-145)*24))

def ascii_actor(g,p,support,root_ch,com_ch,head_ch):
    for nm in ('lf','rf'):grid_line(g,*to_grid(p[nm]),*to_grid(p['root']),'/')
    grid_line(g,*to_grid(p['root']),*to_grid(p['chest']),'|')
    for nm,ch in [('head',head_ch),('root',root_ch),('com',com_ch)]:
        x,y=to_grid(p[nm])
        if 0<=y<len(g) and 0<=x<len(g[0]):g[y][x]=ch
    for nm,side in [('lf','left'),('rf','right')]:
        x,y=to_grid(p[nm])
        if 0<=y<len(g) and 0<=x<len(g[0]):g[y][x]='*' if support_trusted(support[side]) else '~'

def ascii_pose(k):
    g=[[' ']*96 for _ in range(25)]
    gy=int(round((G-125)/(H-145)*24))
    if 0<=gy<25:
        for x in range(96):g[gy][x]='_'
    for prefix in ('a','b'):
        route=[to_grid(tuple(map(float,q[f'{prefix}_root']))) for q in MOTION['keys']]
        for p,q in zip(route,route[1:]):grid_line(g,*p,*q,'.')
    a=actor(k,'a'); b=actor(k,'b'); ascii_actor(g,b,k['b_support'],'&','d','o'); ascii_actor(g,a,k['a_support'],'@','c','O')
    if relationship_active(k):
        fr=tuple(map(float,k['relationship']['frame'])); ah=shoulder_hand(a,b['chest'][0],6); bh=shoulder_hand(b,a['chest'][0],6)
        grid_line(g,*to_grid(ah),*to_grid(fr),'='); grid_line(g,*to_grid(fr),*to_grid(bh),'=')
        x,y=to_grid(fr)
        if 0<=y<25 and 0<=x<96:g[y][x]='R'
    return '\n'.join(''.join(r).rstrip() for r in g)

def make_contact_sheet():
    out=[
      'ASCII KINESIS V2 · LOCOMOTION 025 · RELATIONSHIP DRAG / SUPPORT REVOCATION / RELEASE RUNOUT',
      'legend: A=@/c/O carrier root/COM/head · B=&/d/o partner root/COM/head · *=trusted fixed support · ~=free/untrusted foot · R== relationship frame · .=root routes',
      'source evidence: Billy & Jimmy / Double Dragon II: The Revenge / NES / TSR asset 30327 / Home Center artifact 1icTndAfTH5fge6tCAL35HzU9X7dsKVzRa0ah_n6gwWk',
      'OBSERVED: commissioned full-sheet evidence contains neutral/travel plus attacker and receiver relationship families, including explicit held/grabbed/kneed/throw states; source is a static PNG.',
      'UNKNOWN: exact source chronology, root paths, grip points, support-revocation timing, paired opponent pose, mass/force values, and source-authentic exposure.',
      'authored timing: INFERRED / STREET_FIGHTER-CAPCOM. rights firewall: independent abstract two-body rig only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/redistribution/close imitation.',
      'thesis: first touch does not steal partner support. Carrier travel loads a locked relationship against grounded partner support; partner support must unload/revoke before shared travel. Release then removes braking load, causing a larger carrier overrun, shorter corrections, unsynchronized partner lag, and displaced settle.',
      ''
    ]
    for k in MOTION['keys']:
        out.append(f"{k['key_id']} {k['name']} · {k['timing_class']}/{k['hold_frames']}f · {k['timing_provenance']} · A={k['a_support']['owner']} · B={k['b_support']['owner']} · R={k['relationship']['state']} · AΔ={k['a_root_spacing_px']:.1f}px · BΔ={k['b_root_spacing_px']:.1f}px · lag={k['partner_lag_px']}px")
        out.append(ascii_pose(k)); out.append(f"causal: {k['causal_role']}"); out.append('')
    return '\n'.join(out).rstrip()+'\n'

def make_spa(a,j,v):
    ab64=base64.b64encode(gzip.compress(a.encode(),mtime=0)).decode(); jb64=base64.b64encode(gzip.compress(j.encode(),mtime=0)).decode(); vb64=base64.b64encode(v).decode()
    title='ASCII Kinesis V2 · Locomotion 025 · Relationship Drag / Support Revocation / Release Runout'
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
    for p in FRAMES.glob('*.png'):p.unlink()
    idx=0
    for k in MOTION['keys']:
        for _ in range(int(k['hold_frames'])): draw_frame(k,idx,FRAMES/f'frame-{idx:04d}.png'); idx+=1
    assert idx==int(MOTION['timing']['total_frames'])
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(FRAMES/'frame-%04d.png'),
                    '-vf','scale=480:270:flags=neighbor','-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',
                    '-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)],check=True)
    a=make_contact_sheet(); ASCII.write_text(a,encoding='utf-8'); j=(HERE/'motion.json').read_text(encoding='utf-8')
    SPA.write_text(make_spa(a,j,MP4.read_bytes()),encoding='utf-8')
if __name__=='__main__': main()
