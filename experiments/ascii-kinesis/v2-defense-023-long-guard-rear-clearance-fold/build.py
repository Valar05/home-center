#!/usr/bin/env python3
from __future__ import annotations
import json, math, hashlib, subprocess, shutil, base64, html, gzip
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
M=json.loads((ROOT/'motion.json').read_text(encoding='utf-8'))
W,H=M['rig']['grid']; FLOOR=M['rig']['floor_y']; CLEAR=M['rig']['clearance_x']
LINKS=M['rig']['links']; JOINTS=M['rig']['joint_order']
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

def smooth(t): return t*t*(3-2*t)
def bres(x0,y0,x1,y1):
    x0,y0,x1,y1=map(lambda z:int(round(z)),(x0,y0,x1,y1)); out=[]
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
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

def support_state(name,support):
    p='LEFT' if name=='foot_l' else 'RIGHT'
    vals=[s for s in support if s.startswith(p)]
    return vals[0] if vals else p+'_UNSUPPORTED'

def render_foot(g,name,pos,support):
    x,y=map(lambda z:int(round(z)),pos); st=support_state(name,support); d=-1 if name=='foot_l' else 1
    if 0<=x<W and 0<=y<H:g[y][x]='o'
    if 'FULL' in st:
        for dx,ch in [(-2,'='),(-1,'='),(0,'#'),(1,'='),(2,'=')]:
            xx=x+dx
            if 0<=xx<W:g[FLOOR][xx]=ch
    elif 'FOREFOOT' in st:
        for dx,ch in [(0,'^'),(d,'^'),(2*d,'^')]:
            xx=x+dx
            if 0<=xx<W:g[FLOOR][xx]=ch
    elif 'TOE_LIGHT' in st:
        xx=x+2*d
        if 0<=xx<W:g[FLOOR][xx]=':'
    elif 'TOE' in st:
        xx=x+2*d
        if 0<=xx<W:g[FLOOR][xx]='.'
    elif 0<=x<W and 0<=y<H:
        g[y][x]='x'

def draw(j,support,threat,tool,contact,label=''):
    g=[[' ']*W for _ in range(H)]
    for x in range(2,W-2):g[FLOOR][x]='_'
    for y in range(3,FLOOR-1):
        if 0<=CLEAR<W:g[y][CLEAR]=':'
    if 1<CLEAR<W-2:
        txt='REAR CLEARANCE'
        for i,ch in enumerate(txt):
            xx=CLEAR-len(txt)+i
            if 0<=xx<W:g[2][xx]=ch
    if threat.get('active'):
        for x,y in bres(*threat['start'],*threat['end']):
            if 0<=x<W and 0<=y<H and g[y][x]==' ':g[y][x]=threat.get('glyph','-')
        ex,ey=map(lambda z:int(round(z)),threat['end'])
        if 0<=ex<W and 0<=ey<H:g[ey][ex]=threat.get('head','>')
    # guard first, so body joints visibly sit on top of it.
    tx,ty=tool['tip']; bx,by=tool['butt']
    for x,y in bres(tx,ty,bx,by):
        if 0<=x<W and 0<=y<H and g[y][x]==' ':g[y][x]='='
    txi,tyi=map(lambda z:int(round(z)),(tx,ty)); bxi,byi=map(lambda z:int(round(z)),(bx,by))
    if 0<=txi<W and 0<=tyi<H:g[tyi][txi]='<'
    if 0<=bxi<W and 0<=byi<H:g[byi][bxi]=']'
    for a,b in LINKS:
        x0,y0=j[a]; x1,y1=j[b]; gl=glyph(x0,y0,x1,y1)
        for x,y in bres(x0,y0,x1,y1)[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==' ':g[y][x]=gl
    marks={'head':'O','neck':'o','shoulder_l':'o','shoulder_r':'o','elbow_l':'o','elbow_r':'o','hand_l':'+','hand_r':'+','pelvis':'@','knee_l':'o','knee_r':'o'}
    for name,(x,y) in j.items():
        if name in ('foot_l','foot_r'):continue
        x=int(round(x)); y=int(round(y))
        if 0<=x<W and 0<=y<H:g[y][x]=marks.get(name,'o')
    if contact.get('active'):
        cx,cy=map(lambda z:int(round(z)),contact['point'])
        if 0<=cx<W and 0<=cy<H:g[cy][cx]='X'
    render_foot(g,'foot_l',j['foot_l'],support); render_foot(g,'foot_r',j['foot_r'],support)
    if label:
        txt=label[:90].ljust(90)
        for i,ch in enumerate(txt):
            x=2+i
            if x<W-1:g[0][x]=ch
    return [''.join(r) for r in g]

def lerp_pair(a,b,e): return [a[0]+(b[0]-a[0])*e,a[1]+(b[1]-a[1])*e]
def interp_threat(t0,t1,e):
    if not t0.get('active') or not t1.get('active'): return dict(t0)
    out=dict(t0)
    out['start']=lerp_pair(t0['start'],t1['start'],e); out['end']=lerp_pair(t0['end'],t1['end'],e)
    return out
def interp_tool(t0,t1,e): return {'tip':lerp_pair(t0['tip'],t1['tip'],e),'butt':lerp_pair(t0['butt'],t1['butt'],e),'relation':t0['relation']}
def interp(k0,k1,t):
    e=smooth(t); arcs=k0.get('bridge',{}).get('joint_arcs',{}); ra=k0.get('bridge',{}).get('root_arc',[0,0]); out={}
    j0=k0['pose_rig']['joint_xy']; j1=k1['pose_rig']['joint_xy']
    for name in JOINTS:
        a=j0[name]; b=j1[name]; x=a[0]+(b[0]-a[0])*e; y=a[1]+(b[1]-a[1])*e
        if name not in ('foot_l','foot_r'):
            x+=math.sin(math.pi*t)*ra[0]*.35; y+=math.sin(math.pi*t)*ra[1]*.35
        if name in arcs:
            x+=math.sin(math.pi*t)*arcs[name][0]; y+=math.sin(math.pi*t)*arcs[name][1]
        out[name]=[x,y]
    return out,k0['support_contact'],interp_threat(k0['threat_state'],k1['threat_state'],e),interp_tool(k0['guard_tool'],k1['guard_tool'],e),dict(k0['guard_contact'])

def compile_frames():
    fs=[]; ks=M['keys']
    for idx,k in enumerate(ks):
        for _ in range(int(k['hold_frames'])):
            fs.append((k['pose_rig']['joint_xy'],k['support_contact'],k['threat_state'],k['guard_tool'],k['guard_contact'],k['key_id']+' '+k['name']))
        if idx<len(ks)-1:
            n=int(k.get('bridge',{}).get('frames',0))
            for bi in range(1,n+1):
                j,s,t,tool,c=interp(k,ks[idx+1],bi/(n+1))
                fs.append((j,s,t,tool,c,k['key_id']+'>'+ks[idx+1]['key_id']))
    return fs

def contact_sheet():
    x0,x1,y0,y1=20,83,1,30; cw=x1-x0
    smap={'LEFT_FOOT_FULL':'L#','RIGHT_FOOT_FULL':'R#','LEFT_FOREFOOT':'L^','RIGHT_FOREFOOT':'R^','LEFT_TOE_LIGHT':'L:','RIGHT_TOE_LIGHT':'R:','LEFT_TOE':'L.','RIGHT_TOE':'R.','LEFT_UNSUPPORTED':'Lx','RIGHT_UNSUPPORTED':'Rx'}
    blocks=[]
    for k in M['keys']:
        fr=draw(k['pose_rig']['joint_xy'],k['support_contact'],k['threat_state'],k['guard_tool'],k['guard_contact'],'')
        lines=[ln[x0:x1] for ln in fr[y0:y1]]
        sup='+'.join(smap.get(x,x) for x in k['support_contact']) or 'NONE'
        con='ON@'+','.join(str(v) for v in k['guard_contact']['point']) if k['guard_contact']['active'] else 'OFF'
        blocks.append([
            (k['key_id']+' '+k['name'])[:cw].ljust(cw),
            (k['timing_class']+'/INFERRED SUP='+sup+' CONTACT='+con)[:cw].ljust(cw),
            ('THREAT='+k['threat_state']['relation'])[:cw].ljust(cw),
            ('TOOL='+k['guard_tool']['relation'])[:cw].ljust(cw)
        ]+lines)
    out=[
        'ASCII KINESIS V2 DEFENSE023 — LONG GUARD / REAR-CLEARANCE FOLD',
        'SOURCE EVIDENCE: TSR asset 255871 Spear — Legend of Heroes — Arcade | exact whole source 502x715 PNG / 53,816 bytes / SHA-256 e850b6944ee00b9087d67d3aebf96d7a8676a495c80bfcaf091df9949d41f611.',
        'SOURCE ROLE: STYLE_REFERENCE. OBSERVED only: long tool occupancy changes body envelope and spends space on both sides of hands. Source-authentic timing UNKNOWN.',
        'AUTHORED PRINCIPLE: MIDSPAN PIN -> REAR-END CLEARANCE FOLD UNDER CONTINUOUS TWO-HAND CUSTODY -> PELVIS LOAD -> CONTACT RELEASE -> REAR-FOOT BREAK/SWEEP/CATCH -> COUNTERTORQUE -> LATE RESPAN.',
        'TIMING: every decisive compile timing class INFERRED / STREET_FIGHTER-CAPCOM. ONES/TWOS/FOURS are hold classes, never seconds.',
        'LEGEND: # full support | ^ forefoot | x unsupported | @ pelvis | X active midspan contact | = long guard | ] rear butt | : rear clearance plane.',
        'RIGHTS: independent abstract ASCII rig only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio.',
        ''
    ]
    for r in range(0,len(blocks),2):
        row=blocks[r:r+2]
        for li in range(max(map(len,row))):
            out.append('    '.join((b[li] if li<len(b) else ' '*cw) for b in row).rstrip())
        out.append('')
    return '\n'.join(out).rstrip()+'\n'

def render_media():
    fs=compile_frames(); fd=ROOT/'_frames'; shutil.rmtree(fd,ignore_errors=True); fd.mkdir()
    font=ImageFont.truetype(FONT,13)
    for i,(j,s,t,tool,c,label) in enumerate(fs):
        im=Image.new('RGB',(800,450),'black')
        ImageDraw.Draw(im).multiline_text((8,6),'\n'.join(draw(j,s,t,tool,c,label)),font=font,fill='white',spacing=0)
        im.save(fd/f'{i:04d}.png')
    out=ROOT/'long-guard-rear-clearance-fold.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(fd/'%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out)]))
    return fs,out,probe

def build_spa(ascii_text,video_path):
    raw_json=(ROOT/'motion.json').read_text(encoding='utf-8')
    pack=lambda text:base64.b64encode(gzip.compress(text.encode('utf-8'),mtime=0)).decode('ascii')
    ab64=pack(ascii_text); jb64=pack(raw_json); vb64=base64.b64encode(video_path.read_bytes()).decode('ascii')
    css='body{margin:0;background:#090909;color:#f2f2f2;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}nav{position:sticky;top:0;background:#111;padding:.7rem;display:flex;gap:.5rem;border-bottom:1px solid #444}button{font:inherit;background:#181818;color:#eee;border:1px solid #555;padding:.55rem .9rem}main{padding:1rem}.view{display:none}.view.active{display:block}pre{white-space:pre;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;line-height:1.05}video{max-width:100%;height:auto;background:#000}'
    js='const bs=[...document.querySelectorAll("[data-view]")],vs=[...document.querySelectorAll(".view")];bs.forEach(b=>b.onclick=()=>vs.forEach(v=>v.classList.toggle("active",v.id===b.dataset.view)));async function unpack(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0)),ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text()}Promise.all([unpack(document.body.dataset.a),unpack(document.body.dataset.j)]).then(([a,j])=>{document.getElementById("ap").textContent=a;document.getElementById("jp").textContent=j});'
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Defense023 — Long Guard / Rear-Clearance Fold</title><style>'+css+'</style></head><body data-a="'+ab64+'" data-j="'+jb64+'"><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><main><section id="ascii" class="view active"><pre id="ap"></pre></section><section id="json" class="view"><pre id="jp"></pre></section><section id="video" class="view"><video controls loop playsinline src="data:video/mp4;base64,'+vb64+'"></video></section></main><script>'+js+'</script></body></html>'

def main():
    ascii_text=contact_sheet(); (ROOT/'contact-sheet.txt').write_text(ascii_text,encoding='utf-8')
    fs,out,probe=render_media(); sha=hashlib.sha256(out.read_bytes()).hexdigest()
    declared=M.get('media',{})
    if declared.get('authoritative_sha256') not in (None,'PENDING',sha): raise SystemExit('media identity mismatch')
    if declared.get('authoritative_sha256')==sha:
        if int(declared.get('frames',-1))!=len(fs): raise SystemExit('frame count mismatch')
        if int(declared.get('bytes',-1))!=out.stat().st_size: raise SystemExit('media size mismatch')
    (ROOT/'long-guard-rear-clearance-fold.motion.html').write_text(build_spa(ascii_text,out),encoding='utf-8')
    print(json.dumps({'frames':len(fs),'media_sha256':sha,'media_bytes':out.stat().st_size,'ascii_sha256':hashlib.sha256(ascii_text.encode()).hexdigest(),'motion_sha256':hashlib.sha256((ROOT/'motion.json').read_bytes()).hexdigest(),'probe':probe},sort_keys=True))
if __name__=='__main__': main()
