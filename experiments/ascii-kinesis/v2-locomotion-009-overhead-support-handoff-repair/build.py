#!/usr/bin/env python3
"""Reconstruct Locomotion 009 solely from persisted abstract motion.json.

No source sprites are read or required. Authored decisive ASCII keys are semantic authority.
Only explicitly declared same-support connectors are permitted; support/contact changes
occur only at authored decisive keys and fail closed otherwise. Requires Pillow + ffmpeg.
"""
from pathlib import Path
import base64, hashlib, html, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
M=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
GRID=M['rig']['grid']; W=int(GRID['width']); H=int(GRID['height']); GROUND=int(GRID['ground_y']); RAIL=int(GRID['overhead_rail_y'])
BONES=[tuple(x) for x in M['rig']['bones']]
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
CONN={(c['from'],c['to']):c for c in M['connectors']}
KEYS=M['keys']; FPS=int(M['motion_dungeon']['compile']['fps'])

def line_points(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; pts=[]
    while True:
        pts.append((x0,y0))
        if (x0,y0)==(x1,y1): return pts
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy

def art(j,support):
    g=[[' ']*W for _ in range(H)]
    for x in range(W): g[GROUND][x]='-'
    for x in range(2,W-2): g[RAIL][x]='='
    for a,b in BONES:
        pa,pb=j[a],j[b]
        for x,y in line_points(pa,pb)[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==' ':
                dx=pb[0]-pa[0]; dy=pb[1]-pa[1]
                g[y][x]='/' if dx*dy<0 else ('\\' if dx*dy>0 else ('-' if dy==0 else '|'))
    for name,(x,y) in j.items():
        if 0<=x<W and 0<=y<H:
            g[y][x]='O' if name=='head' else ('@' if name=='pelvis' else ('+' if name=='chest' else ('o' if 'elbow' in name or 'knee' in name else '*')))
    for side,node in [('L_FOOT','l_foot'),('R_FOOT','r_foot'),('L_HAND','l_hand'),('R_HAND','r_hand')]:
        x,y=j[node]
        if side+'_PROBE' in support: g[y][x]='?'
        elif side in support: g[y][x]='!'
    return '\n'.join(''.join(r).rstrip() for r in g)

def bridge(a,b,t,bend):
    s=t*t*(3-2*t); out={}
    for name,pa in a.items():
        pb=b[name]; x=pa[0]+(pb[0]-pa[0])*s; y=pa[1]+(pb[1]-pa[1])*s; amp=4*s*(1-s)*bend
        if name=='pelvis': y+=amp*.35
        elif name in ('head','chest'): y+=amp*.25
        elif name in ('l_hand','r_hand'): y+=amp*(.65 if name=='l_hand' else -.45)
        elif name in ('l_foot','r_foot'): y+=amp*(-.35 if name=='l_foot' else .25)
        out[name]=[round(x),round(y)]
    return out

def compile_frames():
    out=[]
    for i,k in enumerate(KEYS):
        if k['timing_class'] not in HOLD: raise SystemExit('UNSUPPORTED_TIMING_CLASS '+k['key_id'])
        out += [(k['joints'],k['support_contact'],k['key_id'],k['name'])]*HOLD[k['timing_class']]
        if i<len(KEYS)-1:
            n=KEYS[i+1]; c=CONN.get((k['key_id'],n['key_id']))
            if c:
                if k['support_contact']!=n['support_contact']: raise SystemExit('CONNECTOR_CROSSES_SUPPORT_CHANGE '+k['key_id']+'->'+n['key_id'])
                for q in range(1,int(c['frames'])+1):
                    out.append((bridge(k['joints'],n['joints'],q/(int(c['frames'])+1),int(c['bend'])),k['support_contact'],k['key_id']+'→'+n['key_id'],'AUTHORED_CONNECTOR'))
    out += [(KEYS[-1]['joints'],KEYS[-1]['support_contact'],KEYS[-1]['key_id'],KEYS[-1]['name'])]*int(M['motion_dungeon']['compile']['endpoint_hold_frames'])
    return out

def contact_sheet():
    out=['ASCII KINESIS V2 LOCOMOTION 009 — OVERHEAD SUPPORT HANDOFF REPAIR','Legend: ! trusted support   ? probe only   @ pelvis/root   + chest   = overhead rail   - ground','']
    for k in KEYS:
        out += [f"{k['key_id']} {k['name']}  [{k['timing_class']} / {k['timing_provenance']}]  SUPPORT={k['support_contact']}",'ROOT: '+k['motion_arc_root_note'],'ROLE: '+k['causal_role'],'ATTITUDE: '+k['attitude'],'',art(k['joints'],k['support_contact']),'','']
    return '\n'.join(out).rstrip()+'\n'

frames=compile_frames(); expected=int(M['motion_dungeon']['compile']['frame_count'])
if expected and len(frames)!=expected: raise SystemExit(f'FRAME_COUNT_MISMATCH {len(frames)} != {expected}')
tmp=HERE/'_rebuild_frames'; shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir()
fp=Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
if not fp.is_file(): raise SystemExit('REQUIRED_FONT_MISSING')
font=ImageFont.truetype(str(fp),10); small=ImageFont.truetype(str(fp),8)
for idx,(j,s,kid,name) in enumerate(frames):
    im=Image.new('RGB',(800,450),(13,13,14)); d=ImageDraw.Draw(im)
    d.text((16,10),'ASCII KINESIS · LOCOMOTION 009 · OVERHEAD SUPPORT HANDOFF REPAIR',font=small,fill=(180,180,180))
    d.text((16,24),f'{kid}  {name}  SUPPORT={s}',font=small,fill=(238,238,235))
    d.multiline_text((16,42),art(j,s),font=font,fill=(246,246,240),spacing=0)
    d.text((16,418),'! trusted support   ? probe only   @ pelvis/root   + chest   = rail   - ground',font=small,fill=(170,170,170))
    d.text((690,418),f'{idx+1:03d}/{len(frames):03d}',font=small,fill=(130,130,130))
    im.save(tmp/f'frame_{idx:04d}.png',compress_level=9)
mp4=HERE/'motion.mp4'
subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(tmp/'frame_%04d.png'),'-c:v','libx264','-preset','veryslow','-crf',str(M['motion_dungeon']['compile']['crf']),'-pix_fmt','yuv420p','-movflags','+faststart','-metadata','comment=ASCII Kinesis abstract rig only',str(mp4)],check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(mp4),'-f','null','-'],check=True)
sha=hashlib.sha256(mp4.read_bytes()).hexdigest(); exp=M['motion_dungeon']['compile']['media_sha256']
if exp!='PENDING' and sha!=exp: raise SystemExit(f'MEDIA_HASH_MISMATCH {sha} != {exp}')
if M['motion_dungeon']['compile']['media_bytes'] is not None and mp4.stat().st_size!=int(M['motion_dungeon']['compile']['media_bytes']): raise SystemExit('MEDIA_BYTE_COUNT_MISMATCH')
ct=contact_sheet(); (HERE/'contact_sheet.txt').write_text(ct,encoding='utf-8')
pretty=json.dumps(M,ensure_ascii=False,indent=2); b64=base64.b64encode(mp4.read_bytes()).decode('ascii')
page=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Locomotion 009 — Overhead Support Handoff Repair</title><style>:root{{color-scheme:dark}}body{{margin:0;background:#0e0e10;color:#f2f2ee;font:16px/1.35 ui-sans-serif,system-ui,sans-serif}}header{{padding:1rem 1.25rem;border-bottom:1px solid #333}}nav{{display:flex;gap:.5rem;padding:.75rem 1rem;position:sticky;top:0;background:#0e0e10}}button{{background:#19191b;color:#eee;border:1px solid #444;padding:.65rem 1rem;border-radius:.35rem}}button[aria-selected="true"]{{background:#eee;color:#111}}main{{padding:0 1rem 1rem}}section[hidden]{{display:none}}pre{{font-family:"DejaVu Sans Mono","Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2;background:#121214;border:1px solid #2d2d30;padding:1rem;max-height:78vh}}video{{display:block;width:min(100%,1280px);height:auto;background:#000;border:1px solid #333}}.note{{max-width:90ch;color:#aaa}}</style></head><body><header><strong>ASCII Kinesis V2 Locomotion 009 — Overhead Support Handoff Repair</strong><div class="note">Repairs rejected Locomotion 002. Source art is evidence-only and is not embedded. Support changes are authored events; deterministic bridges cannot invent them.</div></header><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav><main><section id="ascii"><pre id="ascii-text">{html.escape(ct)}</pre></section><section id="json" hidden><pre id="json-text">{html.escape(pretty)}</pre></section><section id="video" hidden><video id="motion-video" controls autoplay muted playsinline src="data:video/mp4;base64,{b64}"></video><p class="note">H.264/yuv420p 800×450 @ 24 fps · {len(frames)} frames · abstract ASCII rig only · SHA-256 {sha}</p></section></main><script>const buttons=[...document.querySelectorAll('button[data-view]')];const sections={{ascii:document.getElementById('ascii'),json:document.getElementById('json'),video:document.getElementById('video')}};for(const b of buttons)b.addEventListener('click',()=>{{for(const x of buttons)x.setAttribute('aria-selected',String(x===b));for(const [name,section]of Object.entries(sections))section.hidden=name!==b.dataset.view;}});</script></body></html>'''
(HERE/'overhead-support-handoff-repair.motion.html').write_text(page,encoding='utf-8')
print(json.dumps({'frame_count':len(frames),'media_sha256':sha,'media_bytes':mp4.stat().st_size,'contact_sheet_sha256':hashlib.sha256(ct.encode()).hexdigest(),'spa_sha256':hashlib.sha256(page.encode()).hexdigest()},sort_keys=True))
