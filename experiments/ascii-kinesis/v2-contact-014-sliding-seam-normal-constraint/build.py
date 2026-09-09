#!/usr/bin/env python3
from pathlib import Path
import base64, gzip, hashlib, json, math, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION_PATH=ROOT/'motion.json'
ASCII_PATH=ROOT/'contact-sheet.txt'
SPA_PATH=ROOT/'sliding-seam-normal-constraint.motion.html'
TMP=ROOT/'.motion-build'; FRAMES=TMP/'frames'; MP4=TMP/'motion.mp4'
W,H,GROUND_Y,WALL_X=76,26,21,64
IMG_W,IMG_H,FPS=800,450,24
TIMING={'ONES':1,'TWOS':2,'FOURS':4}
JOINTS=['head','shoulder','pelvis','hand_f','hand_b','foot_f','foot_b']

def expand_pose(p):
    return {j:[float(p[i][0]),float(p[i][1])] for i,j in enumerate(JOINTS)}

def line_cells(p0,p1):
    x0,y0=map(lambda v:int(round(v)),p0); x1,y1=map(lambda v:int(round(v)),p1)
    dx=abs(x1-x0); dy=-abs(y1-y0); sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1; err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if x0==x1 and y0==y1: return out
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def seg_char(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>abs(dy)*1.7: return '-'
    if abs(dy)>abs(dx)*1.7: return '|'
    return '\\' if dx*dy>0 else '/'

def paint_line(g,p0,p1,ch,overwrite=False):
    for x,y in line_cells(p0,p1):
        if 0<=x<W and 0<=y<H and (overwrite or g[y][x]==' '): g[y][x]=ch

def render_ascii(state):
    g=[[' ']*W for _ in range(H)]
    for x in range(W): g[GROUND_Y][x]='_'
    for y in range(3,GROUND_Y+1): g[y][WALL_X]='|'
    j=state['A']
    for a,b in [('head','shoulder'),('shoulder','pelvis'),('shoulder','hand_f'),
                ('shoulder','hand_b'),('pelvis','foot_f'),('pelvis','foot_b')]:
        paint_line(g,j[a],j[b],seg_char(j[a],j[b]))
    for n,ch in [('head','A'),('shoulder','O'),('pelvis','X'),
                 ('hand_f','*'),('hand_b','*'),('foot_f','^'),('foot_b','^')]:
        x,y=j[n]; x=int(round(x)); y=int(round(y))
        if 0<=x<W and 0<=y<H: g[y][x]=ch
    if state['contact'] in ('NORMAL_CONTACT','SLIDING_CONTACT'):
        sx,sy=map(lambda v:int(round(v)),state['seam'])
        if 0<=sx<W and 0<=sy<H: g[sy][sx]='@'
        paint_line(g,j['hand_f'],[sx,sy],'=',overwrite=True)
        if 0<=sx<W and 0<=sy<H: g[sy][sx]='@'
    if 'REAR_PIN' in state.get('root',''):
        x,y=j['foot_b']; x=int(round(x)); y=int(round(y))
        if 0<=x<W and 0<=y<H: g[y][x]='#'
    if 'LEAD' in state.get('root','') and state['contact']!='FREE':
        x,y=j['foot_f']; x=int(round(x)); y=int(round(y))
        if 0<=x<W and 0<=y<H: g[y][x]='#'
    force=state.get('force',[0,0])
    if force!=[0,0]:
        origin=j['pelvis']; end=[origin[0]+force[0],origin[1]+force[1]]
        paint_line(g,origin,end,'=',overwrite=True)
        ex,ey=map(lambda v:int(round(v)),end)
        if 0<=ex<W and 0<=ey<H:
            dx,dy=force
            g[ey][ex]=('>' if dx>=0 else '<') if abs(dx)>=abs(dy) else ('v' if dy>=0 else '^')
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet(m):
    rev=m['revision']; src=m['source']
    lead=[
        m['experiment_id'],
        m['principle'],
        f"REVISION: kind={rev['kind']} | revises={rev['revises']} | negative_fixture={rev['negative_fixture']} | source_change={rev['source_change']}.",
        f"SOURCE EVIDENCE: TSR asset {src['asset_id']}, {src['title']} — {src['game']} — {src['platform']}; archive {src['archive_bytes']} bytes; SHA-256 {src['archive_sha256']}; {src['archive_entries']} entries / {src['png_count']} PNGs; whole corpus campaign-audited.",
        "RIGHTS: evidence only; independent ASCII rig; no source pixels/palette/costume/contours/exact silhouettes/layout/tracing/choreography/redistribution/close imitation; Drew work not used.",
        "OBSERVED: Wall Hit evidence changes local shape with minimal image-space centroid translation; source-authentic playback timing/order remains UNKNOWN.",
        "TIMING: ONES/TWOS/FOURS are display classes, never seconds; every decisive key is INFERRED / STREET_FIGHTER-CAPCOM.",
        "VISIBLE LAW: @ is the wall seam. During NORMAL_CONTACT/SLIDING_CONTACT the seam owns the NORMAL axis only; tangent motion may migrate the @ before separately authored release."
    ]
    parts=['\n'.join(lead)]
    for q in m['keys']:
        state={'A':expand_pose(q['a']),'contact':q['contact'],'relationship_owner':q['relationship_owner'],
               'support':q['support'],'root':q['root'],'seam':q['seam'],
               'normal_axis':q['normal_axis'],'tangent_axis':q['tangent_axis'],'force':q.get('force',[0,0])}
        meta=(f"{q['id']}  {q['p']}  [{q['timing']}/{q['provenance']}]\n"
              f"contact={q['contact']} | owner={q['relationship_owner']} | normal={q['normal_axis']} | tangent={q['tangent_axis']}\n"
              f"support={q['support']} | root={q['root']} | seam={q['seam']} | force={q['force']}\n"
              f"role={q['role']}\narc={q['arc']}")
        parts.append(meta+'\n'+render_ascii(state))
    return ('\n'+'='*92+'\n').join(parts)+'\n'

def interp_pose(a0,a1,t,curve):
    s=t*t*(3-2*t); out={}
    for n in a0:
        x0,y0=a0[n]; x1,y1=a1[n]
        x=x0+(x1-x0)*s; y=y0+(y1-y0)*s
        if n in ('head','hand_b'): y+=curve*math.sin(math.pi*t)
        out[n]=[x,y]
    return out

def lerp(a,b,t):
    return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]

def key_state(q):
    return {'id':q['id'],'phase':q['p'],'A':expand_pose(q['a']),'contact':q['contact'],
            'relationship_owner':q['relationship_owner'],'support':q['support'],'root':q['root'],
            'seam':[float(q['seam'][0]),float(q['seam'][1])],
            'normal_axis':q['normal_axis'],'tangent_axis':q['tangent_axis'],'force':q.get('force',[0,0])}

def sequence(m):
    out=[]
    # Connective geometry is subordinate to current semantics. Acquisition and release hard-cut.
    bridge_counts={
        'C014-K0':2,'C014-K1':2,
        'C014-K3':2,'C014-K4':2,'C014-K5':2,'C014-K6':1,'C014-K7':2,
        'C014-K9':2,'C014-K10':2,'C014-K11':2
    }
    for i,q in enumerate(m['keys']):
        k=key_state(q)
        out.extend([k]*TIMING[q['timing']])
        if i+1<len(m['keys']):
            n=m['keys'][i+1]; nk=key_state(n); count=bridge_counts.get(q['id'],0)
            # No interpolation across semantic acquire/release boundaries.
            if (q['contact']!=n['contact']) and {q['contact'],n['contact']} & {'FREE','ELIGIBLE_NO_CONTACT'}:
                count=0
            for j in range(1,count+1):
                t=j/(count+1)
                out.append({**k,'id':q['id']+'~'+n['id'],'phase':'AUTHORED_CONNECTIVE',
                            'A':interp_pose(k['A'],nk['A'],t,-0.55),
                            'seam':lerp(k['seam'],nk['seam'],t),
                            'force':lerp(k['force'],nk['force'],t)})
    return out

def fonts():
    p='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    if Path(p).exists(): return ImageFont.truetype(p,12),ImageFont.truetype(p,11)
    return ImageFont.load_default(),ImageFont.load_default()

def render_video(m):
    if TMP.exists(): shutil.rmtree(TMP)
    FRAMES.mkdir(parents=True)
    mainf,smallf=fonts(); seq=sequence(m)
    for i,k in enumerate(seq):
        im=Image.new('RGB',(IMG_W,IMG_H),(8,8,8)); d=ImageDraw.Draw(im)
        d.text((10,8),f"{k['id']}  {k['phase']}",font=smallf,fill=(245,245,245))
        d.text((10,24),f"CONTACT {k['contact']}   OWNER {k['relationship_owner']}",font=smallf,fill=(205,205,205))
        d.text((10,40),f"NORMAL {k['normal_axis']}   TANGENT {k['tangent_axis']}   SUPPORT {k['support']}",font=smallf,fill=(175,175,175))
        d.multiline_text((10,62),render_ascii(k),font=mainf,fill=(248,248,248),spacing=-2)
        im.save(FRAMES/f'f-{i:04d}.png')
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(FRAMES/'f-%04d.png'),
                    '-c:v','libx264','-preset','medium','-crf','39','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
    return seq

def gz64(text):
    return base64.b64encode(gzip.compress(text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
def js_chunks(s,n=960):
    return ',\n'.join(json.dumps(s[i:i+n]) for i in range(0,len(s),n))

def build_spa(m,sheet,mp4):
    a=gz64(sheet); j=gz64(json.dumps(m,separators=(',',':'),ensure_ascii=True)); v=base64.b64encode(mp4).decode('ascii')
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{m['experiment_id']}</title>
<style>html,body{{margin:0;background:#0b0b0b;color:#eee;font-family:system-ui,sans-serif}}nav{{position:sticky;top:0;background:#111;padding:8px;border-bottom:1px solid #444}}button[data-view]{{margin-right:8px;padding:8px 14px}}section{{display:none;padding:12px}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08}}video{{display:block;max-width:100%;height:auto;margin:auto}}</style></head>
<body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii" class="active"><pre id="a"></pre></section>
<section id="json"><pre id="j"></pre></section>
<section id="video"><video id="v" controls autoplay loop muted playsinline></video></section>
<script>
const A=[
{js_chunks(a)}
].join('');
const J=[
{js_chunks(j)}
].join('');
const V=[
{js_chunks(v)}
].join('');
const D=async s=>new TextDecoder().decode(await new Response(new Blob([Uint8Array.from(atob(s),c=>c.charCodeAt(0))]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
(async()=>{{document.getElementById('a').textContent=await D(A);document.getElementById('j').textContent=await D(J);document.getElementById('v').src='data:video/mp4;base64,'+V;}})();
document.querySelectorAll('button[data-view]').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('section').forEach(s=>s.classList.remove('active'));document.getElementById(b.dataset.view).classList.add('active')}}));
</script></body></html>"""

def main():
    m=json.loads(MOTION_PATH.read_text(encoding='utf-8'))
    sheet=contact_sheet(m); ASCII_PATH.write_text(sheet,encoding='utf-8')
    seq=render_video(m); mp4=MP4.read_bytes(); got=hashlib.sha256(mp4).hexdigest()
    m['motion_dungeon']['media_sha256']=got
    m['motion_dungeon']['media_bytes']=len(mp4)
    m['motion_dungeon']['frames']=len(seq)
    MOTION_PATH.write_text(json.dumps(m,indent=2),encoding='utf-8')
    SPA_PATH.write_text(build_spa(m,sheet,mp4),encoding='utf-8')
    print(json.dumps({'frames':len(seq),'media_sha256':got,'media_bytes':len(mp4),
                      'sheet_sha256':hashlib.sha256(sheet.encode()).hexdigest(),
                      'motion_sha256':hashlib.sha256(MOTION_PATH.read_bytes()).hexdigest(),
                      'spa_sha256':hashlib.sha256(SPA_PATH.read_bytes()).hexdigest()},sort_keys=True))

if __name__=='__main__': main()
