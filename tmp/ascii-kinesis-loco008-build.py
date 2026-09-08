#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import base64, hashlib, html, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
M=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
GRID_W=int(M['rig']['grid']['width']); GRID_H=int(M['rig']['grid']['height']); GROUND=int(M['rig']['grid']['ground_y'])
FPS=int(M['motion_dungeon']['compile']['fps']); HOLDS={'ONES':1,'TWOS':2,'FOURS':4}; BONES=[tuple(x) for x in M['rig']['bones']]

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
    for x in range(GRID_W): g[GROUND][x]='─'
    for a,b in BONES:
        pa=j[a]; pb=j[b]
        for x,y in line_points(pa,pb)[1:-1]:
            if 0<=x<GRID_W and 0<=y<GRID_H and g[y][x]==' ':
                dx=pb[0]-pa[0]; dy=pb[1]-pa[1]
                g[y][x]='/' if dx*dy<0 else ('\\' if dx*dy>0 else ('─' if dy==0 else '│'))
    for name,(x,y) in j.items():
        if not(0<=x<GRID_W and 0<=y<GRID_H): raise SystemExit(f'JOINT_OOB {name} {(x,y)}')
        g[y][x]='O' if name=='head' else ('@' if name=='pelvis' else ('*' if name in {'l_hand','r_hand','l_foot','r_foot'} else 'o'))
    if support.startswith('LEFT_'):
        x,y=j['l_foot']; g[y][x]='!'
    if support=='RIGHT_FOOT_PROBE_CONTACT':
        x,y=j['r_foot']; g[y][x]='?'
    if support=='RIGHT_FOOT_OWNS_ROOT':
        x,y=j['r_foot']; g[y][x]='!'
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet():
    out=[M['title'], 'REVISION: '+M['revision']['revises'], 'LEGEND: @ pelvis/root   ! trusted support   ? probe only   O head   * extremity', '']
    for k in M['keys']:
        out += [f"{k['key_id']}  {k['name']}  [{k['timing_class']} / {k['timing_provenance']}]", f"SUPPORT: {k['support_contact']}", 'ROOT: '+k['motion_arc_root_note'], 'ROLE: '+k['causal_role'], art(k['joints'],k['support_contact']), '']
    return '\n'.join(out).rstrip()+'\n'

ct=contact_sheet(); (HERE/'contact_sheet.txt').write_text(ct,encoding='utf-8')
frames=[]
for k in M['keys']:
    pose=art(k['joints'],k['support_contact'])
    for _ in range(HOLDS[k['timing_class']]): frames.append((k,pose))
# presentation tail preserves the final debt pose without inventing a semantic state
for _ in range(5): frames.append((M['keys'][-1], art(M['keys'][-1]['joints'],M['keys'][-1]['support_contact'])))
M['motion_dungeon']['compile']['frame_count']=len(frames)

tmp=HERE/'_frames'; shutil.rmtree(tmp,ignore_errors=True); tmp.mkdir()
font_paths=['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf','/data/data/com.termux/files/usr/share/fonts/TTF/DejaVuSansMono.ttf','/system/fonts/DroidSansMono.ttf']
font_path=next((p for p in font_paths if Path(p).is_file()),None)
if not font_path: raise SystemExit('NO_MONO_FONT')
font=ImageFont.truetype(font_path,18); small=ImageFont.truetype(font_path,13); tiny=ImageFont.truetype(font_path,12)
for idx,(k,pose) in enumerate(frames):
    im=Image.new('RGB',(1280,720),(13,14,16)); d=ImageDraw.Draw(im)
    d.text((34,24),'ASCII KINESIS · LOCOMOTION 008 · REPAIR OF 001',font=small,fill=(185,185,185))
    d.text((34,49),f"{k['key_id']}  {k['name']}  {k['timing_class']} / {k['timing_provenance']}",font=small,fill=(245,245,242))
    d.text((34,71),f"SUPPORT={k['support_contact']}",font=tiny,fill=(195,195,195))
    d.multiline_text((34,101),pose,font=font,fill=(247,247,240),spacing=1)
    d.text((34,656),'@ ROOT/Pelvis    ! trusted support    ? probe-only contact    source art absent',font=tiny,fill=(170,170,170))
    d.text((1025,656),f'frame {idx+1:02d}/{len(frames):02d}',font=tiny,fill=(145,145,145))
    im.save(tmp/f'frame_{idx:04d}.png',compress_level=9)
mp4=HERE/'coiled-catch-recovery-debt.mp4'
subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(tmp/'frame_%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','comment=ASCII Kinesis abstract rig only',str(mp4)],check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(mp4),'-f','null','-'],check=True)
media_sha=hashlib.sha256(mp4.read_bytes()).hexdigest(); M['motion_dungeon']['compile']['media_sha256']=media_sha
(HERE/'motion.json').write_text(json.dumps(M,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
# Build GIF chat render from exact same frame images; this is not byte-identical to repo MP4.
gif=HERE/'coiled-catch-recovery-debt.chat.gif'
imgs=[Image.open(tmp/f'frame_{i:04d}.png') for i in range(len(frames))]
imgs[0].save(gif,save_all=True,append_images=imgs[1:],duration=round(1000/FPS),loop=0,optimize=False)
# self-contained SPA
motion_text=(HERE/'motion.json').read_text(encoding='utf-8')
video_b64=base64.b64encode(mp4.read_bytes()).decode('ascii')
page=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(M['title'])}</title><style>
:root{{color-scheme:dark}}*{{box-sizing:border-box}}body{{margin:0;background:#0d0f12;color:#f3f3ee;font:16px/1.35 system-ui,sans-serif}}header{{padding:1rem 1.2rem;border-bottom:1px solid #30343b}}header small{{display:block;color:#aeb4bd;margin-top:.3rem}}nav{{display:flex;gap:.5rem;padding:.7rem 1rem;position:sticky;top:0;background:#0d0f12;z-index:2}}button{{border:1px solid #48505b;background:#15191f;color:#f3f3ee;padding:.65rem 1rem;border-radius:.35rem;font-weight:700}}button[aria-selected="true"]{{background:#f3f3ee;color:#0d0f12}}main{{padding:0 1rem 1rem}}section[hidden]{{display:none}}pre{{font-family:"DejaVu Sans Mono","Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2;background:#11151a;border:1px solid #30343b;padding:1rem;max-height:78vh}}video{{display:block;width:min(100%,1280px);height:auto;background:#000;border:1px solid #30343b}}.note{{max-width:90ch;color:#aeb4bd}}</style></head><body>
<header><strong>{html.escape(M['title'])}</strong><small>Repair successor for {html.escape(M['revision']['negative_fixture'])}. Source art is not embedded.</small></header>
<nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav>
<main><section id="ascii"><pre>{html.escape(ct)}</pre></section><section id="json" hidden><pre>{html.escape(motion_text)}</pre></section><section id="video" hidden><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{video_b64}"></video><p class="note">MP4 rendered solely from the abstract ASCII rig and structured timing. SHA-256 {media_sha}</p></section></main>
<script>const b=[...document.querySelectorAll('button[data-view]')],s=[...document.querySelectorAll('main section')];for(const x of b)x.onclick=()=>{{for(const y of b)y.setAttribute('aria-selected',y===x?'true':'false');for(const z of s)z.hidden=z.id!==x.dataset.view}};</script></body></html>'''
spa=HERE/'coiled-catch-recovery-debt.motion.html'; spa.write_text(page,encoding='utf-8')
print(json.dumps({'ok':True,'frames':len(frames),'media_sha256':media_sha,'media_bytes':mp4.stat().st_size,'spa_sha256':hashlib.sha256(page.encode()).hexdigest(),'ascii_sha256':hashlib.sha256(ct.encode()).hexdigest(),'motion_sha256':hashlib.sha256(motion_text.encode()).hexdigest(),'gif_sha256':hashlib.sha256(gif.read_bytes()).hexdigest()},sort_keys=True))
