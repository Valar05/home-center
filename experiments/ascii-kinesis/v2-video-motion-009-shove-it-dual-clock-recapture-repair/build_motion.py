#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, html, json, math, subprocess, tempfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MOTION_PATH=ROOT/'motion.json'
CONTACT_PATH=ROOT/'contact_sheet.txt'
SPA_PATH=ROOT/'shove-it-dual-clock-recapture-repair.motion.html'
W,H,FPS,GROUND_Y,CELL_W,CELL_H=54,22,24,20,8,10
VIDEO_W,VIDEO_H=W*CELL_W,H*CELL_H
FONT={
'O':["01110","10001","10011","10101","11001","10001","01110"],
'@':["01110","10001","10111","10101","10111","10000","01111"],
'o':["00000","01110","01010","01110","00000","00000","00000"],
'|':["00100"]*7,'-':["00000","00000","00000","11111","00000","00000","00000"],
'_':["00000","00000","00000","00000","00000","00000","11111"],
'/':["00001","00010","00100","01000","10000","00000","00000"],
'\\':["10000","01000","00100","00010","00001","00000","00000"],
'=':["00000","11111","00000","11111","00000","00000","00000"],
'+':["00000","00100","00100","11111","00100","00100","00000"],
'#':["01010","11111","01010","11111","01010","00000","00000"],
'A':["01110","10001","10001","11111","10001","10001","10001"],
'B':["11110","10001","10001","11110","10001","10001","11110"],
' ':["00000"]*7}
MARK={"head":"O","neck":"o","root":"@","left_shoulder":"o","left_elbow":"o","left_hand":"+","right_shoulder":"o","right_elbow":"o","right_hand":"+","left_knee":"o","left_foot":"+","right_knee":"o","right_foot":"+"}
EDGES=[("head","neck"),("neck","root"),("neck","left_shoulder"),("left_shoulder","left_elbow"),("left_elbow","left_hand"),("neck","right_shoulder"),("right_shoulder","right_elbow"),("right_elbow","right_hand"),("root","left_knee"),("left_knee","left_foot"),("root","right_knee"),("right_knee","right_foot")]

def sha(data): return hashlib.sha256(data).hexdigest()
def line(g,a,b,glyph=None):
    x0,y0=map(int,a); x1,y1=map(int,b); dx=abs(x1-x0); dy=-abs(y1-y0); sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<H and g[y0][x0]==' ':
            g[y0][x0]=glyph or ('|' if x0==x1 else '-' if y0==y1 else '\\' if (x1-x0)*(y1-y0)>0 else '/')
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def grid(k):
    g=[[' ']*W for _ in range(H)]
    for x in range(W): g[GROUND_Y][x]='_'
    j=k['joints']
    for a,b in EDGES: line(g,j[a],j[b])
    board=k['board']; cx,cy=map(int,board['center']); half=int(board['half_length']); yaw=float(board['yaw_deg'])%360
    projected=max(1,int(round(half*abs(math.cos(math.radians(yaw)))))); ax=max(0,cx-projected); bx=min(W-1,cx+projected)
    if ax==bx: ax=max(0,cx-1); bx=min(W-1,cx+1)
    line(g,(ax,cy),(bx,cy),'='); g[cy][cx]='#'
    lm,rm=('A','B') if math.cos(math.radians(yaw))>=0 else ('B','A')
    g[cy][ax]=lm; g[cy][bx]=rm
    for name,ch in MARK.items():
        x,y=map(int,j[name])
        if 0<=x<W and 0<=y<H: g[y][x]=ch
    return [''.join(row).rstrip() for row in g]

def contact(m):
    out=[m['title'],m['experiment_id']+' | abstract ASCII rig only | source pixels/audio absent','Observed source presentation evidence is provenance only; every decisive compile timing and acting key below is INFERRED.','']
    for k in m['keys']:
        out += [f"{k['key_id']} {k['causal_role']} | {k['timing_class']}/{k['timing_provenance']}",f"SUPPORT: {k['support_contact']}",f"BODY CLOCK: {k['body_clock']}",f"BOARD CLOCK: {k['board_clock']}",*grid(k),f"ROOT/ARC: {k['root_arc_note']}",'']
    return '\n'.join(out).rstrip()+'\n'

def clone(v): return json.loads(json.dumps(v))
def quad(a,b,c,t): return a+(b-a)*t+4*t*(1-t)*c
def same(a,b): return a['semantic_group']==b['semantic_group'] and not a.get('causal_boundary_to_next',False)
def interp(a,b,t):
    if not same(a,b): return clone(a)
    o=clone(a); arc=a.get('transition_arc',[0,0])
    for n,p in a['joints'].items():
        q=b['joints'][n]; o['joints'][n]=[int(round(quad(p[0],q[0],arc[0],t))),int(round(quad(p[1],q[1],arc[1],t)))]
    p=a['board']['center']; q=b['board']['center']; o['board']['center']=[int(round(quad(p[0],q[0],arc[0]*.5,t))),int(round(quad(p[1],q[1],arc[1]*.5,t)))]
    aa=a['board']['yaw_deg']; bb=b['board']['yaw_deg']; o['board']['yaw_deg']=aa+(bb-aa)*(t*t*(3-2*t))
    return o

def frames(keys):
    out=[]
    for i,k in enumerate(keys):
        out += [grid(k)]*int(k['hold_frames'])
        if i==len(keys)-1: continue
        nxt=keys[i+1]; travel=int(k.get('travel_frames_to_next',0))
        if travel<=0: continue
        if not same(k,nxt): out += [grid(k)]*travel
        else:
            for s in range(1,travel+1): out.append(grid(interp(k,nxt,s/(travel+1))))
    return out

def ppm(lines):
    pix=bytearray([246,246,246])*(VIDEO_W*VIDEO_H)
    def px(x,y,v=20):
        if 0<=x<VIDEO_W and 0<=y<VIDEO_H:
            i=(y*VIDEO_W+x)*3; pix[i:i+3]=bytes((v,v,v))
    for gy,row in enumerate(lines):
        for gx,ch in enumerate(row):
            for yy,bits in enumerate(FONT.get(ch,FONT[' '])):
                for xx,bit in enumerate(bits):
                    if bit=='1': px(gx*CELL_W+1+xx,gy*CELL_H+1+yy)
    return f'P6\n{VIDEO_W} {VIDEO_H}\n255\n'.encode()+bytes(pix)

def render(seq):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,fr in enumerate(seq): (td/f'{i:04d}.ppm').write_bytes(ppm(fr))
        out=td/'motion.mp4'
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(td/'%04d.ppm'),'-an','-c:v','libx264','-crf','28','-preset','veryslow','-pix_fmt','yuv420p','-profile:v','baseline','-level','3.0','-movflags','+faststart','-map_metadata','-1',str(out)],check=True)
        subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True)
        return out.read_bytes()

def pack_text(text): return base64.b64encode(gzip.compress(text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
def spa(contact_text,m,media):
    title=html.escape(m['title']); mp4=base64.b64encode(media).decode('ascii'); c=pack_text(contact_text); j=pack_text(json.dumps(m,separators=(',',':'),ensure_ascii=False))
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>:root{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;background:#f5f5f2;color:#151515}}*{{box-sizing:border-box}}body{{margin:0;min-height:100vh}}header{{padding:1rem;border-bottom:1px solid #aaa}}h1{{font-size:1rem;margin:.1rem 0 .35rem}}.sub,.note{{font-size:.8rem;max-width:86ch}}nav{{display:flex;gap:.4rem;padding:.6rem 1rem;border-bottom:1px solid #aaa;position:sticky;top:0;background:#f5f5f2;z-index:2}}button{{font:inherit;padding:.45rem .8rem}}main{{padding:1rem}}section[hidden]{{display:none}}pre{{font:12px/1.08 ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2}}video{{display:block;width:min(100%,864px);height:auto;background:#fff;border:1px solid #999}}</style></head><body><header><h1>{title}</h1><div class="sub">Video Motion 009 repair · Wikimedia Commons Shove it.webm / TheContreOfficial / CC BY 3.0 · source pixels/audio excluded from output</div></header><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav><main><section id="ascii"><pre id="ascii-pre"></pre></section><section id="json" hidden><pre id="json-pre"></pre></section><section id="video" hidden><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{mp4}"></video><p class="note">Motion Dungeon output: abstract ASCII rig + structured inferred timing only. No source video frames, pixels, audio, tracing, face, costume, or source layout are embedded.</p></section></main><script>const C="{c}",J="{j}";async function u(b){{const a=Uint8Array.from(atob(b),x=>x.charCodeAt(0)),s=new Blob([a]).stream().pipeThrough(new DecompressionStream("gzip"));return new TextDecoder().decode(await new Response(s).arrayBuffer())}}Promise.all([u(C),u(J)]).then(([c,j])=>{{document.getElementById("ascii-pre").textContent=c;document.getElementById("json-pre").textContent=j}});const buttons=[...document.querySelectorAll('button[data-view]')],sections=[...document.querySelectorAll('main>section')];buttons.forEach(b=>b.addEventListener('click',()=>{{buttons.forEach(x=>x.setAttribute('aria-selected',String(x===b)));sections.forEach(s=>s.hidden=s.id!==b.dataset.view)}}));</script></body></html>'''

def main():
    m=json.loads(MOTION_PATH.read_text()); c=contact(m); seq=frames(m['keys']); media=render(seq)
    m['timing']['total_frames']=len(seq); m['timing']['duration_s']=len(seq)/FPS
    m['media']={'authoritative':'embedded_mp4_in_spa','tracked_mp4':False,'sha256':sha(media),'bytes':len(media),'codec':'H.264','pixel_format':'yuv420p','width':VIDEO_W,'height':VIDEO_H,'fps':FPS,'frame_count':len(seq),'duration_s':len(seq)/FPS,'source':'abstract_ascii_rig_only','decode_verified':True,'encode':{'crf':28,'preset':'veryslow','profile':'baseline','level':'3.0'}}
    CONTACT_PATH.write_text(c); MOTION_PATH.write_text(json.dumps(m,separators=(',',':'),ensure_ascii=False)+'\n'); SPA_PATH.write_text(spa(c,m,media))
    (ROOT/'motion.mp4').write_bytes(media)
    print(json.dumps({'frames':len(seq),'duration_s':len(seq)/FPS,'media_sha256':sha(media),'media_bytes':len(media),'spa_bytes':SPA_PATH.stat().st_size,'contact_bytes':CONTACT_PATH.stat().st_size},sort_keys=True))
if __name__=='__main__': main()
