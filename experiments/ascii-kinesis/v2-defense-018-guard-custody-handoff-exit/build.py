#!/usr/bin/env python3
from __future__ import annotations
import json, math, hashlib, subprocess, shutil, base64, html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
M=json.loads((ROOT/'motion.json').read_text(encoding='utf-8'))
W,H=M['rig']['grid']; FLOOR=M['rig']['floor_y']; LINKS=M['rig']['links']; JOINTS=M['rig']['joint_order']
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

def smooth(t): return t*t*(3-2*t)
def bres(x0,y0,x1,y1):
    x0,y0,x1,y1=map(lambda z:int(round(z)),(x0,y0,x1,y1))
    out=[]; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        out.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return out

def glyph(x0,y0,x1,y1):
    dx=x1-x0; dy=y1-y0
    if abs(dx)>=2*abs(dy): return '-'
    if abs(dy)>=2*abs(dx): return '|'
    return '\\' if dx*dy>0 else '/'

def supported_feet(support):
    sup=set()
    for s in support:
        if s.startswith('LEFT'): sup.add('foot_l')
        if s.startswith('RIGHT'): sup.add('foot_r')
    return sup

def draw(j,support,threat,label=''):
    g=[[' ']*W for _ in range(H)]
    for x in range(2,W-2): g[FLOOR][x]='_'
    if threat.get('active'):
        st,en=threat['start'],threat['end']
        for x,y in bres(*st,*en):
            if 0<=x<W and 0<=y<H and y!=FLOOR: g[y][x]=threat.get('glyph','-')
        ex,ey=en
        if 0<=ex<W and 0<=ey<H:g[ey][ex]=threat.get('head','<')
    for a,b in LINKS:
        x0,y0=j[a];x1,y1=j[b];gl=glyph(x0,y0,x1,y1)
        for x,y in bres(x0,y0,x1,y1)[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==' ':g[y][x]=gl
    sup=supported_feet(support)
    marks={'head':'O','neck':'o','shoulder_l':'o','shoulder_r':'o','elbow_l':'o','elbow_r':'o','hand_l':'+','hand_r':'+','pelvis':'@','knee_l':'o','knee_r':'o','foot_l':'#' if 'foot_l' in sup else 'x','foot_r':'#' if 'foot_r' in sup else 'x'}
    for name,(x,y) in j.items():
        x=int(round(x));y=int(round(y))
        if 0<=x<W and 0<=y<H:g[y][x]=marks.get(name,'o')
    if label:
        for i,ch in enumerate(label[:68].ljust(68)):
            x=3+i
            if x<W-1 and g[0][x]==' ':g[0][x]=ch
    return [''.join(r) for r in g]

def interp(k0,k1,t):
    e=smooth(t); arcs=k0.get('bridge',{}).get('joint_arcs',{}); ra=k0.get('bridge',{}).get('root_arc',[0,0]); out={}
    j0=k0['pose_rig']['joint_xy']; j1=k1['pose_rig']['joint_xy']
    for name in JOINTS:
        a=j0[name]; b=j1[name]
        x=a[0]+(b[0]-a[0])*e; y=a[1]+(b[1]-a[1])*e
        if name not in ('foot_l','foot_r'):
            x+=math.sin(math.pi*t)*ra[0]*.35; y+=math.sin(math.pi*t)*ra[1]*.35
        if name in arcs:
            x+=math.sin(math.pi*t)*arcs[name][0]; y+=math.sin(math.pi*t)*arcs[name][1]
        out[name]=[x,y]
    return out,k0['support_contact'],k0['threat_state']

def compile_frames():
    fs=[];ks=M['keys']
    for idx,k in enumerate(ks):
        for _ in range(int(k['hold_frames'])):
            fs.append((k['pose_rig']['joint_xy'],k['support_contact'],k['threat_state'],k['key_id']+' '+k['name']))
        if idx<len(ks)-1:
            n=int(k.get('bridge',{}).get('frames',0))
            for bi in range(1,n+1):
                j,s,t=interp(k,ks[idx+1],bi/(n+1))
                fs.append((j,s,t,k['key_id']+'>'+ks[idx+1]['key_id']))
    return fs

def contact_sheet():
    x0,x1,y0,y1=20,60,1,23; cw=x1-x0
    blocks=[]
    smap={'LEFT_FOOT_FULL':'L#','RIGHT_FOOT_FULL':'R#','LEFT_FOOT_TOE_SKID':'Lt~','RIGHT_FOOT_TOE_SKID':'Rt~','LEFT_TOE_LIGHT':'Lt','RIGHT_TOE_LIGHT':'Rt'}
    for k in M['keys']:
        fr=draw(k['pose_rig']['joint_xy'],k['support_contact'],k['threat_state'],'')
        lines=[ln[x0:x1] for ln in fr[y0:y1]]
        sup='+'.join(smap.get(x,x) for x in k['support_contact']) or 'NONE'
        blocks.append([
            (k['key_id']+' '+k['name'])[:cw].ljust(cw),
            (k['timing_class']+'/INFERRED SUP='+sup)[:cw].ljust(cw)
        ]+lines)
    out=[
      'ASCII KINESIS V2 DEFENSE018 — GUARD CUSTODY HANDOFF / EXIT',
      'SOURCE EVIDENCE: TSR asset 1611 Link — Zelda II NES | whole 332x275 PNG campaign custody | source timing UNKNOWN',
      'TIMING: every decisive compile timing class INFERRED / STREET_FIGHTER-CAPCOM | # support | x unsupported | @ pelvis',
      'RIGHTS: independent abstract ASCII rig only; no source pixels/palette/costume/contours/layout/tracing/choreography.',
      ''
    ]
    for r in range(0,len(blocks),3):
        row=blocks[r:r+3]
        for li in range(max(map(len,row))):
            out.append('   '.join((b[li] if li<len(b) else ' '*cw) for b in row).rstrip())
        out.append('')
    return '\n'.join(out).rstrip()+'\n'

def render_media():
    fs=compile_frames(); fd=ROOT/'_frames'; shutil.rmtree(fd,ignore_errors=True); fd.mkdir()
    font=ImageFont.truetype(FONT,14)
    for i,(j,s,t,label) in enumerate(fs):
        im=Image.new('RGB',(800,450),'black'); d=ImageDraw.Draw(im)
        d.multiline_text((10,8),'\n'.join(draw(j,s,t,label)),font=font,fill='white',spacing=0)
        im.save(fd/f'{i:04d}.png')
    out=ROOT/'guard-custody-handoff-exit.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(fd/'%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out)]))
    return fs,out,probe

def build_spa(ascii_text, video_path):
    raw_json=(ROOT/'motion.json').read_text(encoding='utf-8')
    b64=base64.b64encode(video_path.read_bytes()).decode('ascii')
    css='body{margin:0;background:#090909;color:#f2f2f2;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}nav{position:sticky;top:0;background:#111;padding:.7rem;display:flex;gap:.5rem;border-bottom:1px solid #444}button{font:inherit;background:#181818;color:#eee;border:1px solid #555;padding:.55rem .9rem}main{padding:1rem}.view{display:none}.view.active{display:block}pre{white-space:pre;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;line-height:1.05}video{max-width:100%;height:auto;background:#000}'
    esc=lambda s: html.escape(s,quote=False)
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Defense018 — Guard Custody Handoff / Exit</title><style>'+css+'</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><main><section id="ascii" class="view active"><pre>'+esc(ascii_text)+'</pre></section><section id="json" class="view"><pre>'+esc(raw_json)+'</pre></section><section id="video" class="view"><video controls loop playsinline src="data:video/mp4;base64,'+b64+'"></video></section></main><script>const bs=[...document.querySelectorAll("[data-view]")];const vs=[...document.querySelectorAll(".view")];bs.forEach(b=>b.onclick=()=>{vs.forEach(v=>v.classList.toggle("active",v.id===b.dataset.view));});</script></body></html>'

def main():
    ascii_text=contact_sheet()
    (ROOT/'contact-sheet.txt').write_text(ascii_text,encoding='utf-8')
    fs,out,probe=render_media()
    spa=build_spa(ascii_text,out)
    (ROOT/'guard-custody-handoff-exit.motion.html').write_text(spa,encoding='utf-8')
    print(json.dumps({
      'frames':len(fs),'media_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),
      'media_bytes':out.stat().st_size,'ascii_sha256':hashlib.sha256(ascii_text.encode()).hexdigest(),
      'motion_sha256':hashlib.sha256((ROOT/'motion.json').read_bytes()).hexdigest(),
      'probe':probe},sort_keys=True))
if __name__=='__main__':main()
