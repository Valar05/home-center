#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import base64, hashlib, html, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent
SLUG = 'reciprocal-bind-release-debt'
MOTION = json.loads((OUT / 'motion.json').read_text(encoding='utf-8'))
KEYS = MOTION['keys']
W, H = MOTION['rig']['grid']
FPS = int(MOTION['timing']['fps'])
FRAME_COUNT = int(MOTION['timing']['frame_count'])

def bresenham(a, b):
    x0, y0 = map(int, a); x1, y1 = map(int, b); pts = []
    dx = abs(x1-x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1-y0); sy = 1 if y0 < y1 else -1; err = dx + dy
    while True:
        pts.append((x0,y0))
        if x0 == x1 and y0 == y1: return pts
        e2 = 2*err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy

def line_char(a,b,kind='body'):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if kind=='lead': return '='
    if kind=='reserve': return '~'
    if kind=='opp': return '#'
    if abs(dx)>=2*abs(dy): return '-'
    if abs(dy)>=2*abs(dx): return '|'
    return '\\' if dx*dy>0 else '/'

def interp_pose(a,b,t):
    return {k:[round(a[k][0]+(b[k][0]-a[k][0])*t),round(a[k][1]+(b[k][1]-a[k][1])*t)] for k in a}

def pose_at_frame(f):
    if f <= KEYS[0]['frame']: return KEYS[0]['pose'], KEYS[0]
    for i in range(len(KEYS)-1):
        ka,kb=KEYS[i],KEYS[i+1]
        if ka['frame'] <= f <= kb['frame']:
            span=kb['frame']-ka['frame']
            if ka['key_id']=='K05' and f<=17: return ka['pose'],ka
            if ka['key_id']=='K07' and f<=23: return ka['pose'],ka
            t=(f-ka['frame'])/span if span else 0.0
            t=t*t*(3-2*t)
            return interp_pose(ka['pose'],kb['pose'],t), ka if t<0.5 else kb
    return KEYS[-1]['pose'],KEYS[-1]

def derive(p):
    ch=p['chest']; root=p['root']; ls=[ch[0]-2,ch[1]]; rs=[ch[0]+2,ch[1]]
    lhip=[root[0]-2,root[1]+1]; rhip=[root[0]+2,root[1]+1]
    def mid(a,b,bias=(0,0)): return [round((a[0]+b[0])/2+bias[0]), round((a[1]+b[1])/2+bias[1])]
    return dict(ls=ls,rs=rs,le=mid(ls,p['left_hand'],(-1,0)),re=mid(rs,p['right_hand'],(1,0)),lhip=lhip,rhip=rhip,
                lk=mid(lhip,p['left_foot'],(-1,0)),rk=mid(rhip,p['right_foot'],(1,0)))

def render_ascii(p, meta):
    g=[[' ']*W for _ in range(H)]
    for x in range(8,W-5): g[23][x]='_'
    d=derive(p)
    def seg(a,b,kind='body'):
        ch=line_char(a,b,kind)
        for x,y in bresenham(a,b):
            if 0<=x<W and 0<=y<H and g[y][x]==' ': g[y][x]=ch
    seg(p['root'],p['chest']); seg(p['chest'],p['head'])
    seg(d['ls'],d['le']); seg(d['le'],p['left_hand'])
    seg(d['rs'],d['re']); seg(d['re'],p['right_hand'])
    seg(p['root'],d['lhip']); seg(d['lhip'],d['lk']); seg(d['lk'],p['left_foot'])
    seg(p['root'],d['rhip']); seg(d['rhip'],d['rk']); seg(d['rk'],p['right_foot'])
    seg(p['left_hand'],p['reserve_tip'],'reserve'); seg(p['opp_tip'],p['opp_anchor'],'opp'); seg(p['right_hand'],p['lead_tip'],'lead')
    pts={'head':p['head'],'chest':p['chest'],'root':p['root'],'le':d['le'],'re':d['re'],'left_hand':p['left_hand'],'right_hand':p['right_hand'],'lk':d['lk'],'rk':d['rk'],'left_foot':p['left_foot'],'right_foot':p['right_foot']}
    chars={'head':'o','chest':'+','root':'@','le':'o','re':'o','left_hand':'*','right_hand':'*','lk':'o','rk':'o','left_foot':'/','right_foot':'\\'}
    for n,pt in pts.items():
        x,y=map(int,pt)
        if 0<=x<W and 0<=y<H:g[y][x]=chars[n]
    for pt,ch in [(p['lead_tip'],'>'),(p['reserve_tip'],'<'),(p['opp_anchor'],'#')]:
        x,y=map(int,pt)
        if 0<=x<W and 0<=y<H:g[y][x]=ch
    if meta['contact']=='TOOL_TOOL_BIND':
        x,y=map(int,p['lead_tip'])
        if 0<=x<W and 0<=y<H:g[y][x]='X'
        if x-1>=0:g[y][x-1]='['
        if x+1<W:g[y][x+1]=']'
    elif meta['contact'] in ('RELEASE','PRECONTACT_GAP'):
        lx,ly=map(int,p['lead_tip']); ox,oy=map(int,p['opp_tip'])
        if 0<=lx<W and 0<=ly<H:g[ly][lx]='>'
        if 0<=ox<W and 0<=oy<H:g[oy][ox]='<'
    else:
        ox,oy=map(int,p['opp_tip'])
        if 0<=ox<W and 0<=oy<H:g[oy][ox]='<'
    return '\n'.join(''.join(r).rstrip() for r in g).rstrip()

def make_contact_sheet():
    blocks=[
      'ASCII KINESIS V2 STRIKES017 — RECIPROCAL BIND / RELEASE DEBT',
      'SOURCE ART: NOT EMBEDDED | RIG: ABSTRACT ASCII ONLY | SOURCE TIMING: UNKNOWN | AUTHORED TIMING: INFERRED / STREET_FIGHTER-CAPCOM',
      "POCKET: THE BIND BORROWS BOTH TOOLS' FREEDOM. RELEASE REPAYS THE BORROW ON A NEW AXIS.",
      'LEGEND: body o/+/@/*  lead tool ===>  reserve tool ~~~<  opposing abstract tool ###<  [X] acquired shared tool relationship frame','']
    for k in KEYS:
        blocks += [f"{k['key_id']} {k['name']} | FRAME={k['frame']} | {k['timing_class']} | {k['timing_provenance']} | SUPPORT={k['support']} | CONTACT={k['contact']} | REL={k['relationship']}",
                   'ROLE: '+k['causal_role'], render_ascii(k['pose'],k),'']
    text='\n'.join(blocks).rstrip()+'\n'
    (OUT/'contact_sheet.txt').write_text(text,encoding='utf-8')
    return text

def make_video():
    frames=OUT/'frames'
    if frames.exists(): shutil.rmtree(frames)
    frames.mkdir()
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',15)
    small=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',13)
    for f in range(FRAME_COUNT):
        p,meta=pose_at_frame(f); art=render_ascii(p,meta)
        img=Image.new('RGB',(880,440),(10,10,10)); dr=ImageDraw.Draw(img)
        dr.text((18,10),f"STRIKES017  {meta['key_id']}  {meta['name']}  f{f:02d}/{FRAME_COUNT-1:02d}",font=small,fill=(235,235,235))
        dr.text((0,35),art,font=font,fill=(245,245,245),spacing=0)
        dr.text((18,416),f"SUPPORT {meta['support']}   CONTACT {meta['contact']}   REL {meta['relationship']}",font=small,fill=(210,210,210))
        img.save(frames/f'{f:04d}.png')
    mp4=OUT/f'{SLUG}.mp4'
    subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-framerate',str(FPS),'-i',str(frames/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-profile:v','high','-level','4.0','-movflags','+faststart','-r',str(FPS),str(mp4)],check=True)
    return mp4.read_bytes()

def make_spa(contact_sheet, media):
    motion_text=(OUT/'motion.json').read_text(encoding='utf-8')
    css='body{margin:0;background:#0a0a0a;color:#eee;font-family:system-ui,sans-serif}nav{position:sticky;top:0;background:#111;padding:10px;display:flex;gap:8px}button{font:inherit;padding:8px 14px}section{display:none;padding:14px}section.active{display:block}pre{font-family:monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto;border:1px solid #555}'
    js="const bs=[...document.querySelectorAll('button[data-view]')],ss=[...document.querySelectorAll('section[data-panel]')];function show(v){ss.forEach(s=>s.classList.toggle('active',s.dataset.panel===v));}bs.forEach(b=>b.onclick=()=>show(b.dataset.view));show('ascii');"
    b64=base64.b64encode(media).decode('ascii')
    page=f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Strikes017</title><style>{css}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section data-panel="ascii"><pre>{html.escape(contact_sheet)}</pre></section><section data-panel="json"><pre>{html.escape(motion_text)}</pre></section><section data-panel="video"><video controls loop playsinline src="data:video/mp4;base64,{b64}"></video></section><script>{js}</script></body></html>'
    (OUT/f'{SLUG}.motion.html').write_text(page,encoding='utf-8')

if __name__=='__main__':
    contact=make_contact_sheet(); media=make_video(); make_spa(contact,media)
    mp4=OUT/f'{SLUG}.mp4'
    print(json.dumps({'sha256':hashlib.sha256(media).hexdigest(),'bytes':len(media),'frames':FRAME_COUNT,'fps':FPS},sort_keys=True))
