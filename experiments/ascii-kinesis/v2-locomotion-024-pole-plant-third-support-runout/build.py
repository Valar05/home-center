#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
MOTION=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
W,H=map(int,MOTION['rig']['viewport']); FPS=int(MOTION['timing']['fps']); G=int(MOTION['rig']['ground_y'])
FRAMES=HERE/'_frames'; MP4=HERE/'_authoritative.mp4'; ASCII=HERE/'contact-sheet.txt'; SPA=HERE/'pole-plant-third-support-runout.motion.html'
def body(k):
    rx,ry=map(float,k['root']); lean=math.radians(float(k['torso_lean_deg'])); vx=math.sin(lean); vy=-math.cos(lean)
    chest=(rx+vx*44,ry+vy*44); head=(chest[0]+vx*27,chest[1]+vy*27); com=tuple(map(float,k['com'])); lf=tuple(map(float,k['left_foot'])); rf=tuple(map(float,k['right_foot'])); pt=tuple(map(float,k['pole_tip']))
    lag=math.radians(float(k.get('pole_lag_deg',0))); grip=(chest[0]+18+math.cos(lag)*5,chest[1]+9+math.sin(lag)*5)
    dx=grip[0]-pt[0]; dy=grip[1]-pt[1]; n=max(1e-6,math.hypot(dx,dy)); ux,uy=dx/n,dy/n
    butt=(grip[0]+ux*52,grip[1]+uy*52); rear_hand=(grip[0]+ux*18,grip[1]+uy*18)
    return {'root':(rx,ry),'com':com,'chest':chest,'head':head,'lf':lf,'rf':rf,'pt':pt,'grip':grip,'butt':butt,'rear_hand':rear_hand}
def foot_supported(k,side):
    v=str(k['support'][side]); return 'PLANTED_FIXED' in v or 'UNLOADING_FIXED' in v
def pole_supported(k): return str(k['support']['pole']) in ('PLANTED_FIXED','UNLOADING_FIXED')
def draw_route(d):
    pts=[tuple(map(float,k['root'])) for k in MOTION['keys']]; d.line(pts,fill=(53,60,70),width=3)
    for p in pts:d.ellipse((p[0]-2,p[1]-2,p[0]+2,p[1]+2),fill=(80,89,101))
def draw_frame(k,idx,path):
    im=Image.new('RGB',(W,H),(13,15,18)); d=ImageDraw.Draw(im); d.line((26,G,614,G),fill=(80,87,97),width=2); draw_route(d); p=body(k)
    bodyc=(235,239,244); secondary=(172,183,198); rootc=(247,207,92); supportc=(112,201,144); comc=(225,126,150); polec=(146,191,235); polehot=(245,164,91)
    for side,nm in [('left','lf'),('right','rf')]:
        if foot_supported(k,side): d.line((*p[nm],*p['com']),fill=supportc,width=2)
    if pole_supported(k): d.line((*p['pt'],*p['com']),fill=polehot,width=2)
    for nm,side in [('lf','left'),('rf','right')]:
        fx,fy=p[nm]; rx,ry=p['root']; knee=((fx+rx)/2+(8 if side=='left' else -8),(fy+ry)/2-4); d.line((rx,ry,*knee,*p[nm]),fill=secondary,width=4)
        if foot_supported(k,side): d.ellipse((fx-8,fy-5,fx+8,fy+5),fill=supportc)
        else: d.ellipse((fx-7,fy-4,fx+7,fy+4),outline=bodyc,width=2)
    d.line((*p['root'],*p['chest']),fill=bodyc,width=6); hx,hy=p['head']; d.ellipse((hx-9,hy-9,hx+9,hy+9),outline=bodyc,width=4)
    rx,ry=p['root']; d.polygon([(rx,ry-7),(rx+7,ry),(rx,ry+7),(rx-7,ry)],outline=rootc,width=3); cx,cy=p['com']; d.ellipse((cx-5,cy-5,cx+5,cy+5),fill=comc)
    d.line((*p['pt'],*p['butt']),fill=polec,width=5); tx,ty=p['pt']
    if pole_supported(k): d.ellipse((tx-7,ty-5,tx+7,ty+5),fill=polehot)
    else: d.ellipse((tx-6,ty-4,tx+6,ty+4),outline=polec,width=2)
    d.line((*p['chest'],*p['grip']),fill=secondary,width=4); d.line((*p['chest'],*p['rear_hand']),fill=secondary,width=4)
    for q in (p['grip'],p['rear_hand']): d.ellipse((q[0]-4,q[1]-4,q[0]+4,q[1]+4),fill=bodyc)
    d.text((12,10),f"{k['key_id']}  {k['name']}",fill=(144,154,167)); d.text((12,28),f"support {k['support']['owner']} | pole {k['support']['pole']} | rootΔ {k['root_spacing_px']} | phase {k['phase']}",fill=(109,120,134)); im.save(path,'PNG',optimize=False)
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
    g=[[' ']*84 for _ in range(24)]; gy=int(round((G-130)/(H-150)*23))
    if 0<=gy<24:
        for x in range(84):g[gy][x]='_'
    route=[to_grid(tuple(map(float,q['root']))) for q in MOTION['keys']]
    for a,b in zip(route,route[1:]):grid_line(g,*a,*b,'.')
    p=body(k)
    for nm in ('lf','rf'):grid_line(g,*to_grid(p[nm]),*to_grid(p['root']),'/')
    grid_line(g,*to_grid(p['root']),*to_grid(p['chest']),'|'); grid_line(g,*to_grid(p['pt']),*to_grid(p['butt']),'/'); grid_line(g,*to_grid(p['chest']),*to_grid(p['grip']),'-'); grid_line(g,*to_grid(p['chest']),*to_grid(p['rear_hand']),'-')
    for nm,ch in [('head','O'),('chest','T'),('root','@'),('com','c')]:
        x,y=to_grid(p[nm]);
        if 0<=y<24 and 0<=x<84:g[y][x]=ch
    for nm,side in [('lf','left'),('rf','right')]:
        x,y=to_grid(p[nm]);
        if 0<=y<24 and 0<=x<84:g[y][x]='*' if foot_supported(k,side) else '~'
    x,y=to_grid(p['pt'])
    if 0<=y<24 and 0<=x<84:g[y][x]='P' if pole_supported(k) else '^'
    return '\n'.join(''.join(r).rstrip() for r in g)
def make_contact_sheet():
    out=['ASCII KINESIS V2 · LOCOMOTION 024 · POLE PLANT / THIRD SUPPORT / RUNOUT','legend: @ root · c COM · * trusted foot support · ~ free foot · P planted pole tip · ^ airborne pole tip · / pole/limb · . root route','source evidence: Donatello / TMNT Tournament Fighters / SNES / TSR asset 23976 / Home Center artifact 1BW6UzsUckanhIqsAIcO6mWhc7FNCHGCX7A5tsdfO1EU','OBSERVED: commissioned evidence treated the full 568×2297 static sheet as one corpus spanning travel/jump, long-staff extension, action, special-effect, and consequence/recovery families.','UNKNOWN: source-authentic chronology/exposure/root/support/pole-plant locomotion choreography. The source grants no timing authority.','authored timing: INFERRED / STREET_FIGHTER-CAPCOM. rights firewall: independent abstract rig only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/redistribution/close imitation.','thesis: plant the pole as a true fixed third support, pass root/COM around it, earn a new foot catch before release, preserve velocity into an overlong free catch, then pay shorter correction and tool-lag debt.','']
    for k in MOTION['keys']:
        out.append(f"{k['key_id']} {k['name']} · {k['timing_class']}/{k['hold_frames']}f · {k['timing_provenance']} · support={k['support']['owner']} · pole={k['support']['pole']} · phase={k['phase']} · rootΔ={k['root_spacing_px']}px · lean={k['torso_lean_deg']:+}° · lag={k['pole_lag_deg']:+}°"); out.append(ascii_pose(k)); out.append(f"causal: {k['causal_role']}"); out.append('')
    return '\n'.join(out).rstrip()+'\n'
def make_spa(a,j,v):
    ab64=base64.b64encode(gzip.compress(a.encode(),mtime=0)).decode(); jb64=base64.b64encode(gzip.compress(j.encode(),mtime=0)).decode(); vb64=base64.b64encode(v).decode(); title='ASCII Kinesis V2 · Locomotion 024 · Pole Plant / Third Support / Runout'
    def js_parts(s,n=4000): return ',\n'.join(json.dumps(s[i:i+n]) for i in range(0,len(s),n))
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<style>:root{{color-scheme:dark}}body{{margin:0;background:#0f1114;color:#edf0f3;font-family:system-ui,sans-serif}}header{{padding:14px 18px;border-bottom:1px solid #343943}}nav{{display:flex;gap:8px}}button{{font:inherit;padding:7px 12px;background:#1a1e24;color:inherit;border:1px solid #4a515d;border-radius:6px}}button[aria-selected="true"]{{background:#303641}}main{{padding:14px 18px}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #343943;padding:12px;max-height:78vh}}video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #343943}}</style></head>
<body><header><h1>{title}</h1><nav><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header>
<main><section id="ascii"><pre id="ascii-pre">loading exact persisted ASCII…</pre></section><section id="json" hidden><pre id="json-pre">loading exact persisted JSON…</pre></section><section id="video" hidden><video id="motion-video" controls loop muted playsinline></video></section></main>
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
        for _ in range(int(k['hold_frames'])):draw_frame(k,idx,FRAMES/f'frame-{idx:04d}.png');idx+=1
    assert idx==int(MOTION['timing']['total_frames'])
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(FRAMES/'frame-%04d.png'),'-vf','scale=480:270:flags=neighbor','-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)],check=True)
    a=make_contact_sheet(); ASCII.write_text(a,encoding='utf-8'); j=(HERE/'motion.json').read_text(encoding='utf-8'); SPA.write_text(make_spa(a,j,MP4.read_bytes()),encoding='utf-8')
if __name__=='__main__':main()
