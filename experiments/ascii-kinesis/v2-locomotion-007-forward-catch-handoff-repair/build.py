#!/usr/bin/env python3
"""Reconstruct Locomotion 007 from committed motion.json only.

Source sprite art is not read, copied, or required. Requires Pillow and ffmpeg.
Decisive keys are semantic authority. Connector semantics fail closed by holding
source-key support until the next decisive key.
"""
from pathlib import Path
import json, hashlib, base64, html, subprocess, shutil
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
M=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
FPS=int(M['motion_dungeon']['compile']['fps'])
GRID_W=M['rig']['grid']['width']; GRID_H=M['rig']['grid']['height']; GROUND=M['rig']['grid']['ground_y']
BONES=[tuple(x) for x in M['rig']['bones']]
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
CONN={(c['from'],c['to']):c for c in M['connectors']}
KEYS=M['keys']

def line_points(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; pts=[]
    while True:
        pts.append((x0,y0))
        if (x0,y0)==(x1,y1): return pts
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy

def art(j,support):
    g=[[' ']*GRID_W for _ in range(GRID_H)]
    for x in range(GRID_W): g[GROUND][x]='-'
    for a,b in BONES:
        pa=j[a]; pb=j[b]
        for x,y in line_points(pa,pb)[1:-1]:
            if 0<=x<GRID_W and 0<=y<GRID_H and g[y][x]==' ':
                g[y][x]='/' if (pb[0]-pa[0])*(pb[1]-pa[1])<0 else ('\\' if (pb[0]-pa[0])*(pb[1]-pa[1])>0 else ('-' if pb[1]==pa[1] else '|'))
    for n,(x,y) in j.items():
        g[y][x]='O' if n=='head' else ('@' if n=='pelvis' else ('*' if n in ('l_hand','r_hand','l_foot','r_foot') else 'o'))
    if support.startswith('LEFT_'):
        x,y=j['l_foot']; g[y][x]='!'
    if support=='RIGHT_FOOT_PROBE_CONTACT':
        x,y=j['r_foot']; g[y][x]='?'
    if support=='RIGHT_FOOT_OWNS_ROOT':
        x,y=j['r_foot']; g[y][x]='!'
    return '\n'.join(''.join(r).rstrip() for r in g)

def bridge(a,b,t,bend):
    s=t*t*(3-2*t); out={}
    for name,pa in a.items():
        pb=b[name]; x=pa[0]+(pb[0]-pa[0])*s; y=pa[1]+(pb[1]-pa[1])*s; amp=4*s*(1-s)*bend
        if name in ('head','chest'): y+=amp*0.35
        elif name in ('l_hand','r_hand'): y+=amp*(0.8 if name=='l_hand' else -0.6)
        elif name in ('l_knee','r_knee'): y+=amp*0.25
        elif name=='pelvis': y+=amp*0.20
        out[name]=[round(x),round(y)]
    return out

def contact():
    out=[]
    for k in KEYS:
        out += [
            f"{k['key_id']} {k['name']}  [{k['timing_class']} / {k['timing_provenance']}]  SUPPORT={k['support_contact']}",
            'ROOT: '+k['motion_arc_root_note'], 'ROLE: '+k['causal_role']]
        out += art(k['joints'],k['support_contact']).splitlines(); out.append('')
    return '\n'.join(out).rstrip()+'\n'

frames=[]
for i,k in enumerate(KEYS):
    frames += [(k['joints'],k['support_contact'],k['key_id'],k['name'])]*HOLD[k['timing_class']]
    if i<len(KEYS)-1:
        n=KEYS[i+1]; c=CONN.get((k['key_id'],n['key_id']))
        if c:
            for q in range(1,int(c['frames'])+1):
                frames.append((bridge(k['joints'],n['joints'],q/(int(c['frames'])+1),int(c['bend'])),k['support_contact'],k['key_id']+'→'+n['key_id'],'AUTHORED_CONNECTOR'))
frames += [(KEYS[-1]['joints'],KEYS[-1]['support_contact'],KEYS[-1]['key_id'],KEYS[-1]['name'])]*4

tmp=HERE/'_rebuild_frames'; shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir()
font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',18)
small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',14)
for idx,(j,s,kid,name) in enumerate(frames):
    im=Image.new('RGB',(1280,720),(15,15,16)); d=ImageDraw.Draw(im)
    d.text((36,24),'ASCII KINESIS · LOCOMOTION 007 · FORWARD CATCH HANDOFF REPAIR',font=small,fill=(180,180,180))
    d.text((36,50),f'{kid}  {name}  SUPPORT={s}',font=small,fill=(235,235,235))
    d.multiline_text((36,92),art(j,s),font=font,fill=(245,245,240),spacing=2)
    d.text((36,660),'! trusted support   ? probe only   @ pelvis/root   * extremity',font=small,fill=(170,170,170))
    d.text((920,660),f'frame {idx+1:03d}/{len(frames):03d}',font=small,fill=(130,130,130))
    im.save(tmp/f'frame_{idx:04d}.png',compress_level=9)

mp4=HERE/'motion.mp4'
subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(tmp/'frame_%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','comment=ASCII Kinesis abstract rig only',str(mp4)],check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(mp4),'-f','null','-'],check=True)
sha=hashlib.sha256(mp4.read_bytes()).hexdigest(); expected=M['motion_dungeon']['compile']['media_sha256']
if sha!=expected: raise SystemExit(f'MEDIA_HASH_MISMATCH {sha} != {expected}')
ct=contact(); (HERE/'contact_sheet.txt').write_text(ct,encoding='utf-8'); jt=(HERE/'motion.json').read_text(encoding='utf-8'); vb=base64.b64encode(mp4.read_bytes()).decode('ascii')
page='''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>
:root{{color-scheme:dark}}body{{margin:0;background:#0f0f10;color:#f2f2ee;font:16px/1.35 ui-sans-serif,system-ui,sans-serif}}header{{padding:1rem 1.25rem;border-bottom:1px solid #333}}nav{{display:flex;gap:.5rem;padding:.75rem 1rem;position:sticky;top:0;background:#0f0f10}}button{{background:#19191b;color:#eee;border:1px solid #444;padding:.65rem 1rem;border-radius:.35rem}}button[aria-selected=true]{{background:#eee;color:#111}}main{{padding:0 1rem 1rem}}section[hidden]{{display:none}}pre{{font-family:"DejaVu Sans Mono","Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2;background:#121214;border:1px solid #2d2d30;padding:1rem;max-height:78vh}}video{{display:block;width:min(100%,1280px);height:auto;background:#000;border:1px solid #333}}.note{{max-width:80ch;color:#aaa}}</style></head><body>
<header><strong>{title}</strong><div class="note">Repair successor. Source art is not embedded. Decisive ASCII keys are semantic authority.</div></header>
<nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav>
<main><section id="ascii"><pre>{ascii}</pre></section><section id="json" hidden><pre>{json}</pre></section><section id="video" hidden><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{video}"></video><p class="note">H.264 MP4 generated only from the abstract ASCII rig and structured timing. SHA-256 {sha}</p></section></main>
<script>const bs=[...document.querySelectorAll('button[data-view]')],ss=[...document.querySelectorAll('main section')];for(const b of bs)b.onclick=()=>{{for(const x of bs)x.setAttribute('aria-selected',x===b?'true':'false');for(const s of ss)s.hidden=s.id!==b.dataset.view;}};</script></body></html>'''.format(title=html.escape(M['title']),ascii=html.escape(ct),json=html.escape(jt),video=vb,sha=sha)
(HERE/'forward-catch-handoff-repair.motion.html').write_text(page,encoding='utf-8')
print(json.dumps({'ok':True,'media_sha256':sha,'frames':len(frames),'spa_sha256':hashlib.sha256(page.encode()).hexdigest()},sort_keys=True))
