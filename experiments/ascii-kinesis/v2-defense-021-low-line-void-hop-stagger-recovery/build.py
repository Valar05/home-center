#!/usr/bin/env python3
from __future__ import annotations
import json, math, hashlib, subprocess, shutil, base64, html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
M=json.loads((ROOT/'motion.json').read_text(encoding='utf-8'))
W,H=M['rig']['grid']; FLOOR=M['rig']['floor_y']
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
    p='LEFT' if name=='foot_l' else 'RIGHT'; vals=[s for s in support if s.startswith(p)]
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

def draw(j,support,threat,label=''):
    g=[[' ']*W for _ in range(H)]
    for x in range(2,W-2):g[FLOOR][x]='_'
    if threat.get('active'):
        for x,y in bres(*threat['start'],*threat['end']):
            if 0<=x<W and 0<=y<H and g[y][x]==' ':g[y][x]=threat.get('glyph','-')
        ex,ey=map(lambda z:int(round(z)),threat['end'])
        if 0<=ex<W and 0<=ey<H:g[ey][ex]=threat.get('head','>')
    for a,b in LINKS:
        x0,y0=j[a]; x1,y1=j[b]; gl=glyph(x0,y0,x1,y1)
        for x,y in bres(x0,y0,x1,y1)[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==' ':g[y][x]=gl
    marks={'head':'O','neck':'o','shoulder_l':'o','shoulder_r':'o','elbow_l':'o','elbow_r':'o','hand_l':'+','hand_r':'+','pelvis':'@','knee_l':'o','knee_r':'o'}
    for name,(x,y) in j.items():
        if name in ('foot_l','foot_r'):continue
        x=int(round(x)); y=int(round(y))
        if 0<=x<W and 0<=y<H:g[y][x]=marks.get(name,'o')
    render_foot(g,'foot_l',j['foot_l'],support); render_foot(g,'foot_r',j['foot_r'],support)
    if label:
        for i,ch in enumerate(label[:78].ljust(78)):
            x=2+i
            if x<W-1:g[0][x]=ch
    return [''.join(r) for r in g]

def interp_threat(t0,t1,e):
    if not t0.get('active') or not t1.get('active'):return dict(t0)
    out=dict(t0)
    for fld in ('start','end'):
        a=t0[fld]; b=t1[fld]; out[fld]=[a[0]+(b[0]-a[0])*e,a[1]+(b[1]-a[1])*e]
    out['relation']=t0.get('relation','')
    return out

def interp(k0,k1,t):
    e=smooth(t); arcs=k0.get('bridge',{}).get('joint_arcs',{}); ra=k0.get('bridge',{}).get('root_arc',[0,0]); out={}
    j0=k0['pose_rig']['joint_xy']; j1=k1['pose_rig']['joint_xy']
    # Semantic support topology changes hard-cut at keys: bridge carries source key's support.
    for name in JOINTS:
        a=j0[name]; b=j1[name]; x=a[0]+(b[0]-a[0])*e; y=a[1]+(b[1]-a[1])*e
        if name not in ('foot_l','foot_r'):
            x+=math.sin(math.pi*t)*ra[0]*.35; y+=math.sin(math.pi*t)*ra[1]*.35
        if name in arcs:
            x+=math.sin(math.pi*t)*arcs[name][0]; y+=math.sin(math.pi*t)*arcs[name][1]
        out[name]=[x,y]
    return out,k0['support_contact'],interp_threat(k0['threat_state'],k1['threat_state'],e)

def compile_frames():
    fs=[]; ks=M['keys']
    for idx,k in enumerate(ks):
        for _ in range(int(k['hold_frames'])):
            fs.append((k['pose_rig']['joint_xy'],k['support_contact'],k['threat_state'],k['key_id']+' '+k['name']))
        if idx<len(ks)-1:
            n=int(k.get('bridge',{}).get('frames',0))
            for bi in range(1,n+1):
                j,s,t=interp(k,ks[idx+1],bi/(n+1)); fs.append((j,s,t,k['key_id']+'>'+ks[idx+1]['key_id']))
    return fs

def contact_sheet():
    x0,x1,y0,y1=22,76,1,28; cw=x1-x0
    smap={'LEFT_FOOT_FULL':'L#','RIGHT_FOOT_FULL':'R#','LEFT_FOREFOOT':'L^','RIGHT_FOREFOOT':'R^','LEFT_TOE_LIGHT':'L:','RIGHT_TOE_LIGHT':'R:','LEFT_TOE':'L.','RIGHT_TOE':'R.','LEFT_UNSUPPORTED':'Lx','RIGHT_UNSUPPORTED':'Rx'}
    blocks=[]
    for k in M['keys']:
        fr=draw(k['pose_rig']['joint_xy'],k['support_contact'],k['threat_state'],''); lines=[ln[x0:x1] for ln in fr[y0:y1]]
        sup='+'.join(smap.get(x,x) for x in k['support_contact']) or 'NONE'
        blocks.append([(k['key_id']+' '+k['name'])[:cw].ljust(cw),(k['timing_class']+'/INFERRED SUP='+sup)[:cw].ljust(cw),('THREAT='+k['threat_state']['relation'])[:cw].ljust(cw)]+lines)
    out=['ASCII KINESIS V2 DEFENSE021 — LOW-LINE VOID HOP / STAGGER RECOVERY',
         'SOURCE EVIDENCE: TSR asset 38136 Blanka — Street Fighter 2 / Super Street Fighter 2 — Arcade | commissioned whole-sheet campaign evidence.',
         'SOURCE ROLE: STYLE_REFERENCE only. OBSERVED: grounded compact, airborne/near-airborne, tuck/extension, consequence and recovery families. Source-authentic timing UNKNOWN.',
         'PRINCIPLE: PRECOMPRESS -> BOTH-SUPPORT RELEASE -> ZERO-CONTACT LOW-LINE VOID -> ASYM TUCK -> RIGHT-FIRST CATCH -> SECOND PLANT -> PAID GUARD DEBT.',
         'TIMING: every decisive compile timing class INFERRED / STREET_FIGHTER-CAPCOM. ONES/TWOS/FOURS are hold classes, never seconds.',
         'SUPPORT: # full | ^ forefoot | : light toe | x unsupported | @ pelvis. Threat line is evidence-free authored geometry, never source art.',
         'RIGHTS: independent abstract ASCII rig only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio.',
         '']
    for r in range(0,len(blocks),2):
        row=blocks[r:r+2]
        for li in range(max(map(len,row))):out.append('    '.join((b[li] if li<len(b) else ' '*cw) for b in row).rstrip())
        out.append('')
    return '\n'.join(out).rstrip()+'\n'

def render_media():
    fs=compile_frames(); fd=ROOT/'_frames'; shutil.rmtree(fd,ignore_errors=True); fd.mkdir()
    font=ImageFont.truetype(FONT,14)
    for i,(j,s,t,label) in enumerate(fs):
        im=Image.new('RGB',(800,450),'black')
        ImageDraw.Draw(im).multiline_text((10,8),'\n'.join(draw(j,s,t,label)),font=font,fill='white',spacing=0)
        im.save(fd/f'{i:04d}.png')
    out=ROOT/'low-line-void-hop-stagger-recovery.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(fd/'%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)
    subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True)
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(out)]))
    return fs,out,probe

def build_spa(ascii_text,video_path):
    import gzip
    raw_json=(ROOT/'motion.json').read_text(encoding='utf-8')
    enc=lambda s:base64.b64encode(gzip.compress(s.encode('utf-8'),mtime=0)).decode('ascii')
    ab64=enc(ascii_text); jb64=enc(raw_json); vb64=base64.b64encode(video_path.read_bytes()).decode('ascii')
    css='body{margin:0;background:#090909;color:#f2f2f2;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}nav{position:sticky;top:0;background:#111;padding:.7rem;display:flex;gap:.5rem;border-bottom:1px solid #444}button{font:inherit;background:#181818;color:#eee;border:1px solid #555;padding:.55rem .9rem}main{padding:1rem}.view{display:none}.view.active{display:block}pre{white-space:pre;overflow:auto;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;line-height:1.05}video{max-width:100%;height:auto;background:#000}'
    js='const bs=[...document.querySelectorAll("[data-view]")],vs=[...document.querySelectorAll(".view")];bs.forEach(b=>b.onclick=()=>vs.forEach(v=>v.classList.toggle("active",v.id===b.dataset.view)));async function gunzip64(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const ds=new DecompressionStream("gzip");return await new Response(new Blob([b]).stream().pipeThrough(ds)).text()}Promise.all([gunzip64(document.body.dataset.a),gunzip64(document.body.dataset.j)]).then(([a,j])=>{document.getElementById("ascii-pre").textContent=a;document.getElementById("json-pre").textContent=j});'
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Defense021 — Low-Line Void Hop / Stagger Recovery</title><style>'+css+'</style></head><body data-a="'+ab64+'" data-j="'+jb64+'"><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><main><section id="ascii" class="view active"><pre id="ascii-pre"></pre></section><section id="json" class="view"><pre id="json-pre"></pre></section><section id="video" class="view"><video controls loop playsinline src="data:video/mp4;base64,'+vb64+'"></video></section></main><script>'+js+'</script></body></html>'

def main():
    ascii_text=contact_sheet(); (ROOT/'contact-sheet.txt').write_text(ascii_text,encoding='utf-8')
    fs,out,probe=render_media(); sha=hashlib.sha256(out.read_bytes()).hexdigest()
    declared=M.get('media',{})
    if declared:
        if declared.get('authoritative_sha256')!=sha:raise SystemExit('media identity mismatch')
        if int(declared.get('frames',-1))!=len(fs):raise SystemExit('frame count mismatch')
        if int(declared.get('bytes',-1))!=out.stat().st_size:raise SystemExit('media size mismatch')
    (ROOT/'low-line-void-hop-stagger-recovery.motion.html').write_text(build_spa(ascii_text,out),encoding='utf-8')
    print(json.dumps({'frames':len(fs),'media_sha256':sha,'media_bytes':out.stat().st_size,'ascii_sha256':hashlib.sha256(ascii_text.encode()).hexdigest(),'motion_sha256':hashlib.sha256((ROOT/'motion.json').read_bytes()).hexdigest(),'probe':probe},sort_keys=True))
if __name__=='__main__':main()
