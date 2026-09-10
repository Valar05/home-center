#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import base64, gzip, hashlib, json, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

OUT=Path(__file__).resolve().parent
MOTION=json.loads((OUT/'motion.json').read_text(encoding='utf-8'))
SLUG=MOTION['slug']; KEYS=MOTION['keys']; W,H=MOTION['rig']['grid']; FPS=int(MOTION['timing']['fps']); FRAME_COUNT=int(MOTION['timing']['frame_count']); TARGET=tuple(MOTION['rig']['target_contact'])

def bresenham(a,b):
    x0,y0=map(int,a);x1,y1=map(int,b);pts=[];dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1:return pts
        e2=2*err
        if e2>=dy:err+=dy;x0+=sx
        if e2<=dx:err+=dx;y0+=sy

def line_char(a,b,kind='body'):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if kind=='tool':return '='
    if abs(dx)>=2*abs(dy):return '-'
    if abs(dy)>=2*abs(dx):return '|'
    return '\\' if dx*dy>0 else '/'

def interp_pose(a,b,t):
    return {k:[round(a[k][0]+(b[k][0]-a[k][0])*t),round(a[k][1]+(b[k][1]-a[k][1])*t)] for k in a}

def pose_at_frame(f):
    if f<=KEYS[0]['frame']:return KEYS[0]['pose'],KEYS[0]
    for i in range(len(KEYS)-1):
        ka,kb=KEYS[i],KEYS[i+1]
        if ka['frame']<=f<=kb['frame']:
            span=kb['frame']-ka['frame'];t=(f-ka['frame'])/span if span else 0.0;t=t*t*(3-2*t)
            return interp_pose(ka['pose'],kb['pose'],t), ka if t<0.5 else kb
    return KEYS[-1]['pose'],KEYS[-1]

def derive(p):
    ch=p['chest'];root=p['root'];ls=[ch[0]-2,ch[1]];rs=[ch[0]+2,ch[1]];lh=[root[0]-2,root[1]+1];rh=[root[0]+2,root[1]+1]
    def mid(a,b,bias=(0,0)):return [round((a[0]+b[0])/2+bias[0]),round((a[1]+b[1])/2+bias[1])]
    return dict(ls=ls,rs=rs,le=mid(ls,p['left_hand'],(-1,0)),re=mid(rs,p['right_hand'],(1,0)),lh=lh,rh=rh,lk=mid(lh,p['left_foot'],(-1,0)),rk=mid(rh,p['right_foot'],(1,0)))

def render_ascii(p,meta,w=W,h=H,compact=False):
    g=[[' ']*w for _ in range(h)]
    ground_y=h-1 if compact else 23
    for x in range(1,w-1):g[ground_y][x]='_'
    tx,ty=TARGET if not compact else (41,6)
    for yy in range(max(1,ty-4),min(h-1,ty+7)):g[yy][tx]='#'
    d=derive(p)
    def seg(a,b,kind='body'):
        ch=line_char(a,b,kind)
        for x,y in bresenham(a,b):
            if 0<=x<w and 0<=y<h and g[y][x]==' ':g[y][x]=ch
    seg(p['root'],p['chest']);seg(p['chest'],p['head']);seg(d['ls'],d['le']);seg(d['le'],p['left_hand']);seg(d['rs'],d['re']);seg(d['re'],p['right_hand']);seg(p['root'],d['lh']);seg(d['lh'],d['lk']);seg(d['lk'],p['left_foot']);seg(p['root'],d['rh']);seg(d['rh'],d['rk']);seg(d['rk'],p['right_foot']);seg(p['tool_butt'],p['tool_tip'],'tool')
    chars={'head':'o','chest':'+','root':'@','le':'o','re':'o','left_hand':'*','right_hand':'*','lk':'o','rk':'o','left_foot':'/','right_foot':'\\'}
    pts={'head':p['head'],'chest':p['chest'],'root':p['root'],'le':d['le'],'re':d['re'],'left_hand':p['left_hand'],'right_hand':p['right_hand'],'lk':d['lk'],'rk':d['rk'],'left_foot':p['left_foot'],'right_foot':p['right_foot']}
    for n,pt in pts.items():
        x,y=map(int,pt)
        if 0<=x<w and 0<=y<h:g[y][x]=chars[n]
    bx,by=map(int,p['tool_butt']);txp,typ=map(int,p['tool_tip'])
    if 0<=bx<w and 0<=by<h:g[by][bx]='<'
    if 0<=txp<w and 0<=typ<h:g[typ][txp]='X' if meta['contact']=='TARGET_CONTACT' else '>'
    return '\n'.join(''.join(r).rstrip() for r in g).rstrip()

def compact_pose(p):
    def q(pt):
        x=round(2+(pt[0]-18)*(39/50));y=round(1+(pt[1]-4)*(13/18));return [max(0,min(43,x)),max(0,min(14,y))]
    return {k:q(v) for k,v in p.items()}

def render_compact(p,meta):
    cp=compact_pose(p); g=[[' ']*46 for _ in range(16)]
    for x in range(1,45):g[15][x]='_'
    target=[41,6]
    for yy in range(2,14):g[yy][target[0]]='#'
    d=derive(cp)
    def seg(a,b,kind='body'):
        ch=line_char(a,b,kind)
        for x,y in bresenham(a,b):
            if 0<=x<46 and 0<=y<16 and g[y][x]==' ':g[y][x]=ch
    seg(cp['root'],cp['chest']);seg(cp['chest'],cp['head']);seg(d['ls'],d['le']);seg(d['le'],cp['left_hand']);seg(d['rs'],d['re']);seg(d['re'],cp['right_hand']);seg(cp['root'],d['lh']);seg(d['lh'],d['lk']);seg(d['lk'],cp['left_foot']);seg(cp['root'],d['rh']);seg(d['rh'],d['rk']);seg(d['rk'],cp['right_foot']);seg(cp['tool_butt'],cp['tool_tip'],'tool')
    chars={'head':'o','chest':'+','root':'@','le':'o','re':'o','left_hand':'*','right_hand':'*','lk':'o','rk':'o','left_foot':'/','right_foot':'\\'}
    pts={'head':cp['head'],'chest':cp['chest'],'root':cp['root'],'le':d['le'],'re':d['re'],'left_hand':cp['left_hand'],'right_hand':cp['right_hand'],'lk':d['lk'],'rk':d['rk'],'left_foot':cp['left_foot'],'right_foot':cp['right_foot']}
    for n,pt in pts.items():
        x,y=map(int,pt)
        if 0<=x<46 and 0<=y<16:g[y][x]=chars[n]
    bx,by=map(int,cp['tool_butt']);txp,typ=map(int,cp['tool_tip'])
    if 0<=bx<46 and 0<=by<16:g[by][bx]='<'
    if 0<=txp<46 and 0<=typ<16:g[typ][txp]='X' if meta['contact']=='TARGET_CONTACT' else '>'
    return '\n'.join(''.join(r).rstrip() for r in g).rstrip()

def make_contact_sheet():
    blocks=['ASCII KINESIS V2 STRIKES018 — CONTACT CLEARANCE GATES RECOVERY TURN DEBT','SOURCE ART: NOT EMBEDDED | ABSTRACT ASCII ONLY | SOURCE TIMING: UNKNOWN | AUTHORED: INFERRED / STREET_FIGHTER-CAPCOM',"POCKET: CONTACT EXIT MUST CLEAR THE CORRIDOR BEFORE ROOT REBASE CAN TURN. THE TURN OWES ITS EXISTENCE TO CLEARANCE.",'LEGEND body o/+/@/* | polearm <====> | target # | X contact | ground _','']
    for k in KEYS:
        blocks += [f"{k['key_id']} {k['name']} f{k['frame']:02d} {k['timing_class']}/{k['timing_provenance']} SUPPORT={k['support']} CONTACT={k['contact']} REL={k['relationship']}",'ROLE '+k['causal_role'],render_compact(k['pose'],k),'']
    text='\n'.join(blocks).rstrip()+'\n';(OUT/'contact_sheet.txt').write_text(text,encoding='utf-8');return text

def make_video():
    frames=OUT/'frames'
    if frames.exists():shutil.rmtree(frames)
    frames.mkdir()
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',17)
    for f in range(FRAME_COUNT):
        p,meta=pose_at_frame(f);art=render_ascii(p,meta);img=Image.new('RGB',(880,440),(8,8,8));dr=ImageDraw.Draw(img);dr.text((0,8),art,font=font,fill=(245,245,245),spacing=0);dr.text((12,410),f"STRIKES018  f{f:02d}  {meta['name']}",font=font,fill=(180,180,180));img.save(frames/f'{f:04d}.png')
    mp4=OUT/f'{SLUG}.mp4';subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-framerate',str(FPS),'-i',str(frames/'%04d.png'),'-c:v','libx264','-preset','slow','-crf','42','-pix_fmt','yuv420p','-profile:v','high','-level','4.0','-movflags','+faststart','-r',str(FPS),str(mp4)],check=True);return mp4.read_bytes()

def make_spa(contact,media):
    motion_text=(OUT/'motion.json').read_text(encoding='utf-8');a64=base64.b64encode(gzip.compress(contact.encode(),mtime=0)).decode();j64=base64.b64encode(gzip.compress(motion_text.encode(),mtime=0)).decode();v64=base64.b64encode(media).decode();css='body{margin:0;background:#0a0a0a;color:#eee;font-family:system-ui,sans-serif}nav{position:sticky;top:0;background:#111;padding:10px;display:flex;gap:8px}button{font:inherit;padding:8px 14px}section{display:none;padding:14px}section.active{display:block}pre{font-family:monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto;border:1px solid #555}'
    js=f"const P={{ascii:'{a64}',json:'{j64}'}};async function inflate(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream('gzip');return await new Response(new Blob([b]).stream().pipeThrough(ds)).text();}};(async()=>{{document.getElementById('ascii-pre').textContent=await inflate(P.ascii);document.getElementById('json-pre').textContent=await inflate(P.json);}})();const bs=[...document.querySelectorAll('button[data-view]')],ss=[...document.querySelectorAll('section[data-panel]')];function show(v){{ss.forEach(s=>s.classList.toggle('active',s.dataset.panel===v));}}bs.forEach(b=>b.onclick=()=>show(b.dataset.view));show('ascii');"
    page=f'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Strikes018</title><style>{css}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section data-panel="ascii"><pre id="ascii-pre"></pre></section><section data-panel="json"><pre id="json-pre"></pre></section><section data-panel="video"><video controls loop playsinline src="data:video/mp4;base64,{v64}"></video></section><script>{js}</script></body></html>';(OUT/f'{SLUG}.motion.html').write_text(page,encoding='utf-8')

def main():
    contact=make_contact_sheet();media=make_video();make_spa(contact,media);print(json.dumps({'sha256':hashlib.sha256(media).hexdigest(),'bytes':len(media),'frames':FRAME_COUNT,'fps':FPS},sort_keys=True))
if __name__=='__main__':main()
