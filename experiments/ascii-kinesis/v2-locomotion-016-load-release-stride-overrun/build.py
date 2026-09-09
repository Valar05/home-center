#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,html,json,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
MOTION=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
SLUG='load-release-stride-overrun'
FPS=int(MOTION['motion_dungeon']['compile']['fps'])
HOLDS=MOTION['motion_dungeon']['compile']['timing_hold_frames']
BONES=[tuple(v) for v in MOTION['rig']['bones']]
WW=int(MOTION['rig']['world_grid']['width'])
WH=int(MOTION['rig']['world_grid']['height'])
GY=int(MOTION['rig']['world_grid']['ground_y'])
SUP=MOTION['rig']['support_nodes']

def pose(k):
    return {n:tuple(v) for n,v in zip(MOTION['rig']['joints'],k['pose_rig'])}

def line(a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1
    dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;o=[]
    while True:
        o.append((x0,y0))
        if (x0,y0)==(x1,y1): return o
        e=2*err
        if e>=dy:err+=dy;x0+=sx
        if e<=dx:err+=dx;y0+=sy

def support_node(k):
    return SUP.get(k['support_contact'])

def probe_node(k):
    return SUP.get(k.get('probe_node')) if k.get('probe_node') else None

def draw_load(g,k,off=(0,0)):
    m=k['mechanics']
    if m['task_contact']=='LOAD_OFFSTAGE': return
    lx=int(round(m['load_x'])); ox,oy=off; x=lx-ox
    if x>=len(g[0])+6 or x<-6: return
    top=21-oy; bot=GY-oy
    for yy in range(max(0,top), min(len(g),bot+1)):
        for xx in range(max(0,x), min(len(g[0]),x+5)):
            edge=(yy in (top,bot) or xx in (x,x+4))
            if edge and g[yy][xx]==' ': g[yy][xx]='#'

def draw(g,k,off=(0,0)):
    j=pose(k);ox,oy=off;h=len(g);w=len(g[0]);q=lambda p:(p[0]-ox,p[1]-oy)
    draw_load(g,k,off)
    for a,b in BONES:
        pa,pb=q(j[a]),q(j[b]);dx=pb[0]-pa[0];dy=pb[1]-pa[1]
        ch='/' if dx*dy<0 else ('\\' if dx*dy>0 else ('-' if dy==0 else '|'))
        for x,y in line(pa,pb)[1:-1]:
            if 0<=x<w and 0<=y<h and g[y][x]==' ':g[y][x]=ch
    for n,p in j.items():
        x,y=q(p)
        if 0<=x<w and 0<=y<h:
            g[y][x]='O' if n=='head' else ('@' if n=='pelvis' else ('+' if n=='chest' else ('o' if ('elbow' in n or 'knee' in n) else '*')))
    sn=support_node(k);pn=probe_node(k)
    if sn and sn in j:
        x,y=q(j[sn])
        if 0<=x<w and 0<=y<h:g[y][x]='!'
    if pn and pn in j:
        x,y=q(j[pn])
        if 0<=x<w and 0<=y<h:g[y][x]='?'

def local_ascii(k):
    j=pose(k);xs=[p[0] for p in j.values()];ys=[p[1] for p in j.values()]
    lx=int(round(k['mechanics']['load_x']))
    if k['mechanics']['task_contact']!='LOAD_OFFSTAGE' and lx<WW+5: xs += [lx,lx+5]; ys += [21,GY]
    minx,maxx=min(xs)-3,max(xs)+3;miny,maxy=min(ys)-3,max(ys)+3
    w=max(30,maxx-minx+1);h=max(17,maxy-miny+1)
    g=[[' ']*w for _ in range(h)]
    gy=GY-miny
    if 0<=gy<h:
        for x in range(w):g[gy][x]='_'
    draw(g,k,(minx,miny))
    return '\n'.join(''.join(r).rstrip() for r in g)

def world_ascii(k):
    g=[[' ']*WW for _ in range(WH)]
    for x in range(WW):g[0][x]=g[-1][x]='-'
    for y in range(WH):g[y][0]=g[y][-1]='|'
    for x in range(1,WW-1):g[GY][x]='_'
    draw(g,k)
    return '\n'.join(''.join(r).rstrip() for r in g)

def spacing_map():
    W=70;H=10;g=[[' ']*W for _ in range(H)]
    vals=[int(k['mechanics']['spacing_from_prev']) for k in MOTION['keys']]
    maxv=max(vals) or 1
    for x in range(W):g[0][x]=g[-1][x]='-'
    for y in range(H):g[y][0]=g[y][-1]='|'
    for i,v in enumerate(vals):
        x=3+i*5;y=H-2-int(round((v/maxv)*(H-4)))
        if 0<x<W-1 and 0<y<H-1:g[y][x]='S' if i==0 else ('R' if MOTION['keys'][i]['name']=='LOAD_RELEASE_SPIKE' else 'o')
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet():
    L=[
      'ASCII KINESIS V2 LOCOMOTION 016 — LOAD-RELEASE STRIDE OVERRUN',
      'Legend: ! trusted support   ? next support probe   @ pelvis/root   + chest   O head   # generic resisted load   _ ground',
      'Timing: every decisive key is INFERRED / STREET_FIGHTER-CAPCOM. ONES/TWOS/FOURS are display-frame exposure classes.',
      'Causality: resisted drive -> resistance falls -> load release -> spacing spike -> long first free probe -> surge catch -> shorter corrective catches -> displaced ready.',
      'Novel law: LOAD RELEASE CHANGES ROOT ACCELERATION BEFORE SUPPORT CADENCE CAN REPHASE.',
      '',
      'ROOT-SPACING MAP — S=start, R=release; vertical position encodes authored spacing from previous key:',
      spacing_map(),''
    ]
    for k in MOTION['keys']:
        m=k['mechanics']
        L += [
          f"{k['key_id']} {k['name']}  [{k['timing_class']} / {k['timing_provenance']}]  SUPPORT={k['support_contact']}  CONTACT={k['contact_state']}  TASK={m['task_contact']}",
          f"ROOT={m['root_xy']}  SPACING={m['spacing_from_prev']}  LEAN={m['body_lean_deg']:+.0f}deg  LOAD_X={m['load_x']}  LOAD_V={m['load_velocity_units']:+.1f}",
          f"ROLE: {k['causal_role']}",
          local_ascii(k),''
        ]
    return '\n'.join(L).rstrip()+'\n'

def render(path):
    frames=[]
    for k in MOTION['keys']:
        frames += [(k,world_ascii(k))]*int(HOLDS[k['timing_class']])
    assert len(frames)==MOTION['motion_dungeon']['compile']['frame_count']
    tmp=HERE/'.motion-frames';shutil.rmtree(tmp,ignore_errors=True);tmp.mkdir()
    mono='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    font=ImageFont.truetype(mono,7);small=ImageFont.truetype(mono,10)
    for i,(k,art) in enumerate(frames):
        im=Image.new('RGB',(640,360),(10,10,11));d=ImageDraw.Draw(im)
        d.text((7,4),'ASCII KINESIS · L016 · LOAD-RELEASE STRIDE OVERRUN',font=small,fill=(190,190,190))
        d.text((7,17),f"{k['key_id']} {k['name']} · SUPPORT {k['support_contact']} · {k['mechanics']['task_contact']}",font=small,fill=(238,238,235))
        d.multiline_text((7,32),art,font=font,fill=(246,246,240),spacing=0)
        d.text((7,347),f'{i+1:02d}/{len(frames)} · abstract ASCII only',font=small,fill=(160,160,160))
        im.save(tmp/f'f_{i:04d}.png',compress_level=9)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(tmp/'f_%04d.png'),
                    '-c:v','libx264','-preset','veryslow','-crf',str(MOTION['motion_dungeon']['compile']['crf']),
                    '-pix_fmt','yuv420p','-movflags','+faststart','-metadata','comment=ASCII Kinesis abstract rig only',str(path)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)

def gz64(b):
    return base64.b64encode(gzip.compress(b,9,mtime=0)).decode('ascii')

def spa(video):
    a=(HERE/'contact-sheet.txt').read_bytes()
    j=(HERE/'motion.json').read_bytes()
    v=base64.b64encode(video.read_bytes()).decode('ascii')
    ag=gz64(a);jg=gz64(j)
    page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(MOTION['title'])}</title><style>body{{font-family:system-ui,sans-serif;margin:0;padding:16px}}nav{{display:flex;gap:8px;position:sticky;top:0;background:Canvas;padding:8px 0}}section{{display:none}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}video{{max-width:100%;height:auto;background:#000}}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="ap"></pre></section><section id="json"><pre id="jp"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{v}"></video></section><script>const B=async(s)=>{{let b=Uint8Array.from(atob(s),c=>c.charCodeAt(0)),r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip')));return await r.text()}};Promise.all([B('{ag}'),B('{jg}')]).then(([a,j])=>{{ap.textContent=a;jp.textContent=JSON.stringify(JSON.parse(j),null,2)}});for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>{{for(const s of document.querySelectorAll('section'))s.classList.remove('active');document.getElementById(b.dataset.view).classList.add('active')}};</script></body></html>'''
    (HERE/f'{SLUG}.motion.html').write_text(page,encoding='utf-8')

if __name__=='__main__':
    (HERE/'contact-sheet.txt').write_text(contact_sheet(),encoding='utf-8')
    mp4=HERE/f'{SLUG}.motion.mp4'
    render(mp4)
    b=mp4.read_bytes();d=hashlib.sha256(b).hexdigest();exp=MOTION['motion_dungeon']['compile']
    exp['media_bytes']=len(b);exp['media_sha256']=d
    (HERE/'motion.json').write_text(json.dumps(MOTION,separators=(',',':')),encoding='utf-8')
    (HERE/'contact-sheet.txt').write_text(contact_sheet(),encoding='utf-8')
    spa(mp4)
    print(json.dumps({'frames':exp['frame_count'],'bytes':len(b),'sha256':d}))
