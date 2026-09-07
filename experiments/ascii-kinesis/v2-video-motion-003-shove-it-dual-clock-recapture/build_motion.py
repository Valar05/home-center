#!/usr/bin/env python3
"""Deterministic Motion Dungeon builder for ASCII Kinesis V2 Video Motion 003.

Input authority: motion.json decisive abstract ASCII rig keys + compile timing.
Output: contact_sheet.txt, motion.mp4, and the self-contained three-tab SPA.
No source video, source frames, or source audio are read by this builder.
"""
from __future__ import annotations
import base64, hashlib, json, math, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOTION = ROOT / "motion.json"
W, H = 40, 18
FPS = 24
CELL_W, CELL_H = 8, 10
VIDEO_W, VIDEO_H = W * CELL_W, H * CELL_H
FONT = {
    'O':["01110","10001","10011","10101","11001","10001","01110"],
    '@':["01110","10001","10111","10101","10111","10000","01111"],
    '|':["00100","00100","00100","00100","00100","00100","00100"],
    '-':["00000","00000","00000","11111","00000","00000","00000"],
    '_':["00000","00000","00000","00000","00000","00000","11111"],
    '/':["00001","00010","00100","01000","10000","00000","00000"],
    '\\':["10000","01000","00100","00010","00001","00000","00000"],
    '=':["00000","00000","11111","00000","11111","00000","00000"],
    '<':["00010","00100","01000","10000","01000","00100","00010"],
    '>':["01000","00100","00010","00001","00010","00100","01000"],
    '+':["00000","00100","00100","11111","00100","00100","00000"],
    '.':["00000","00000","00000","00000","00000","00110","00110"],
    '#':["01010","11111","01010","11111","01010","00000","00000"],
    '[':["01110","01000","01000","01000","01000","01000","01110"],
    ']':["01110","00010","00010","00010","00010","00010","01110"],
    '?':["01110","10001","00010","00100","00100","00000","00100"],
    ' ':["00000"]*7,
}
def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()
def line(grid, a, b, glyph=None):
    x0,y0=a; x1,y1=b
    dx=abs(x1-x0); dy=-abs(y1-y0); sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<H and grid[y0][x0]==' ':
            if glyph: ch=glyph
            elif x0==x1: ch='|'
            elif y0==y1: ch='-'
            else: ch='\\' if (x1-x0)*(y1-y0)>0 else '/'
            grid[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
def pose_grid(key):
    g=[[' ']*W for _ in range(H)]
    for x in range(W): g[16][x]='_'
    j=key['joints']; head=tuple(j['head']); root=tuple(j['root']); lh=tuple(j['left_hand']); rh=tuple(j['right_hand']); lf=tuple(j['left_foot']); rf=tuple(j['right_foot'])
    neck=(head[0], min(root[1]-1, head[1]+2))
    line(g,head,root); line(g,neck,lh); line(g,neck,rh); line(g,root,lf); line(g,root,rf)
    hx,hy=head; rx,ry=root
    if 0<=hy<H and 0<=hx<W: g[hy][hx]='O'
    if 0<=ry<H and 0<=rx<W: g[ry][rx]='@'
    for p in (lh,rh,lf,rf):
        x,y=p
        if 0<=y<H and 0<=x<W: g[y][x]='+'
    board=key['board']; cx,cy=board['center']; angle=math.radians(board['angle_deg']); half=board['half_length']
    ax=int(round(cx-math.cos(angle)*half)); ay=int(round(cy-math.sin(angle)*half)); bx=int(round(cx+math.cos(angle)*half)); by=int(round(cy+math.sin(angle)*half))
    bg='=' if abs(math.sin(angle))<0.35 else ('/' if math.sin(angle)<0 else '\\')
    line(g,(ax,ay),(bx,by),bg)
    if 0<=cy<H and 0<=cx<W: g[cy][cx]='#'
    return [''.join(row) for row in g]
def combine_contact(keys):
    panels=[]
    for key in keys:
        body=pose_grid(key); label=f"{key['key_id']} {key['causal_role']} [{key['timing_class']}/{key['timing_provenance']}]"
        panels.append([label[:W].ljust(W)]+body+[f"SUP:{key['support_state']}"[:W].ljust(W),f"ROOT:{key['root_arc_note']}"[:W].ljust(W)])
    rows=[]
    for block in range(0,len(panels),2):
        pair=panels[block:block+2]
        while len(pair)<2: pair.append([' '*W]*len(panels[0]))
        for i in range(len(pair[0])): rows.append(pair[0][i]+'   '+pair[1][i])
        rows.append('')
    return '\n'.join(rows).rstrip()+'\n'
def interpolate(a,b,t):
    out=json.loads(json.dumps(a))
    if a.get('semantic_group') != b.get('semantic_group'): return out
    for name,pt in a['joints'].items():
        q=b['joints'][name]; out['joints'][name]=[int(round(pt[0]+(q[0]-pt[0])*t)),int(round(pt[1]+(q[1]-pt[1])*t))]
    p=a['board']['center']; q=b['board']['center']; out['board']['center']=[int(round(p[0]+(q[0]-p[0])*t)),int(round(p[1]+(q[1]-p[1])*t))]
    aa=a['board']['angle_deg']; bb=b['board']['angle_deg']; out['board']['angle_deg']=aa+(bb-aa)*t
    return out
def compile_frames(keys):
    last=max(k['compile_frame']+k['compile_hold_frames'] for k in keys); frames=[]
    for f in range(last):
        prev=max((k for k in keys if k['compile_frame']<=f),key=lambda k:k['compile_frame']); future=[k for k in keys if k['compile_frame']>prev['compile_frame']]; nxt=min(future,key=lambda k:k['compile_frame']) if future else None
        if nxt and f>=prev['compile_frame']+prev['compile_hold_frames']:
            span=max(1,nxt['compile_frame']-(prev['compile_frame']+prev['compile_hold_frames'])); t=min(1.0,max(0.0,(f-(prev['compile_frame']+prev['compile_hold_frames'])+1)/span)); pose=interpolate(prev,nxt,t)
        else: pose=prev
        frames.append(pose_grid(pose))
    return frames
def ppm_bytes(lines):
    width,height=VIDEO_W,VIDEO_H; pix=bytearray([246,246,246])*(width*height)
    def setpx(x,y,v=18):
        if 0<=x<width and 0<=y<height:
            i=(y*width+x)*3; pix[i:i+3]=bytes((v,v,v))
    for gy,row in enumerate(lines):
        for gx,ch in enumerate(row):
            glyph=FONT.get(ch,FONT['?']); ox=gx*CELL_W+1; oy=gy*CELL_H+1
            for yy,bits in enumerate(glyph):
                for xx,bit in enumerate(bits):
                    if bit=='1': setpx(ox+xx,oy+yy)
    return f'P6\n{width} {height}\n255\n'.encode()+bytes(pix)
def render_mp4(frames,out):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,fr in enumerate(frames): (td/f'{i:04d}.ppm').write_bytes(ppm_bytes(fr))
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(td/'%04d.ppm'),'-an','-c:v','libx264','-pix_fmt','yuv420p','-profile:v','baseline','-level','3.0','-movflags','+faststart','-metadata','encoder=ascii-kinesis-motion-dungeon','-map_metadata','-1',str(out)],check=True)
def make_html(contact,motion,mp4):
    payload=base64.b64encode(mp4).decode('ascii'); motion_text=json.dumps(motion,indent=2,sort_keys=True); title=motion['title']
    def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
    return f'''<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>{esc(title)}</title><style>\n:root{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;background:#f4f4f1;color:#151515}}body{{margin:0;min-height:100vh}}header{{padding:1rem;border-bottom:1px solid #bbb}}h1{{font-size:1rem;margin:.1rem 0}}nav{{display:flex;gap:.4rem;padding:.6rem 1rem;border-bottom:1px solid #bbb;position:sticky;top:0;background:#f4f4f1}}button{{font:inherit;padding:.45rem .8rem}}main{{padding:1rem}}section[hidden]{{display:none}}pre{{font:12px/1.1 ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2}}video{{display:block;max-width:100%;height:auto;border:1px solid #999;background:#fff}}.note{{max-width:72ch;line-height:1.4}}\n</style></head><body><header><h1>{esc(title)}</h1><div class="note">ASCII Kinesis V2 · Video Motion 003 · source pixels excluded from output</div></header>\n<nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>\n<main><section id="ascii"><pre>{esc(contact)}</pre></section><section id="json" hidden><pre>{esc(motion_text)}</pre></section><section id="video" hidden><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{payload}"></video><p class="note">Motion Dungeon compile: abstract ASCII rig only. No source frames, pixels, or audio are embedded.</p></section></main>\n<script>const buttons=[...document.querySelectorAll('[data-view]')];const sections=[...document.querySelectorAll('main>section')];buttons.forEach(b=>b.addEventListener('click',()=>{{buttons.forEach(x=>x.setAttribute('aria-selected',String(x===b)));sections.forEach(s=>s.hidden=s.id!==b.dataset.view)}}));</script></body></html>'''
def main():
    motion=json.loads(MOTION.read_text()); keys=motion['keys']; contact=combine_contact(keys); (ROOT/'contact_sheet.txt').write_text(contact); frames=compile_frames(keys); render_mp4(frames,ROOT/'motion.mp4'); media=(ROOT/'motion.mp4').read_bytes(); sha=sha256_bytes(media)
    motion['media']={'path':'motion.mp4','sha256':sha,'bytes':len(media),'codec':'H.264','pixel_format':'yuv420p','width':VIDEO_W,'height':VIDEO_H,'fps':FPS,'frame_count':len(frames),'source':'abstract_ascii_rig_only'}; MOTION.write_text(json.dumps(motion,indent=2,sort_keys=True)+'\n'); html=make_html(contact,motion,media); (ROOT/'shove-it-dual-clock-recapture.motion.html').write_text(html)
    print(json.dumps({'media_sha256':sha,'media_bytes':len(media),'frames':len(frames),'html_bytes':len(html.encode()),'contact_bytes':len(contact.encode())},sort_keys=True))
if __name__=='__main__': main()
