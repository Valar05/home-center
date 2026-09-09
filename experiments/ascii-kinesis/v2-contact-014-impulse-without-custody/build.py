#!/usr/bin/env python3
from pathlib import Path
import base64, gzip, hashlib, json, math, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION_PATH=ROOT/'motion.json'
ASCII_PATH=ROOT/'contact-sheet.txt'
SPA_PATH=ROOT/'impulse-without-custody.motion.html'
TMP=ROOT/'.motion-build'; FRAMES=TMP/'frames'; MP4=TMP/'motion.mp4'
W,H,GROUND_Y=96,28,22
IMG_W,IMG_H,FPS=800,450,24
TIMING={'ONES':1,'TWOS':2,'FOURS':4}
JOINTS=['head','shoulder','pelvis','hand_f','hand_b','knee_f','knee_b','foot_f','foot_b']

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

def draw_object(g,p):
    x,y=map(lambda v:int(round(v)),p)
    for dx,ch in [(-1,'['),(0,'O'),(1,']')]:
        if 0<=x+dx<W and 0<=y<H: g[y][x+dx]=ch

def render_ascii(state):
    g=[[' ']*W for _ in range(H)]
    for x in range(W): g[GROUND_Y][x]='_'
    j=state['A']
    for a,b in [('head','shoulder'),('shoulder','pelvis'),('shoulder','hand_f'),('shoulder','hand_b'),('pelvis','knee_f'),('knee_f','foot_f'),('pelvis','knee_b'),('knee_b','foot_b')]:
        paint_line(g,j[a],j[b],seg_char(j[a],j[b]))
    for n,ch in [('head','A'),('shoulder','O'),('pelvis','X'),('hand_f','*'),('hand_b','*'),('knee_f','o'),('knee_b','o'),('foot_f','^'),('foot_b','^')]:
        x,y=j[n]; x=int(round(x)); y=int(round(y))
        if 0<=x<W and 0<=y<H: g[y][x]=ch
    if state.get('support')=='REAR_PIN':
        x,y=j['foot_b']; x=int(round(x)); y=int(round(y))
        if 0<=x<W and 0<=y<H: g[y][x]='#'
    force=state.get('force',[0,0])
    if force != [0,0]:
        if state['contact'] in ('IMPACT_JOIN','IMPULSE_COUPLED'):
            origin=[state['object'][0]-3,state['object'][1]-2]
            scale=0.7
        else:
            origin=j['pelvis']
            scale=0.7
        end=[origin[0]+force[0]*scale,origin[1]+force[1]*scale]
        paint_line(g,origin,end,'=',overwrite=False)
        ex,ey=map(lambda v:int(round(v)),end)
        if 0<=ex<W and 0<=ey<H:
            dx,dy=force
            g[ey][ex]=('>' if dx>=0 else '<') if abs(dx)>=abs(dy) else ('v' if dy>=0 else '^')
    draw_object(g,state['object'])
    if state['contact'] in ('IMPACT_JOIN','IMPULSE_COUPLED'):
        foot=j['foot_f']; obj=state['object']
        start=[foot[0]+1,foot[1]]; end=[obj[0]-2,obj[1]]
        paint_line(g,start,end,'=',overwrite=True)
        sx,sy=map(lambda v:int(round(v)),[(foot[0]+obj[0])/2,(foot[1]+obj[1])/2])
        if 0<=sx<W and 0<=sy<H: g[sy][sx]='@'
        draw_object(g,obj)
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet(m):
    s=m['source']; r=m['revision']
    lead=[m['experiment_id'],m['principle'],f"REVISION: kind={r['kind']} | revises={r['revises']} | negative_fixture={r['negative_fixture']} | source_change={r['source_change']}",f"SOURCE EVIDENCE: TSR asset {s['asset_id']}, {s['title']} — {s['game']} — {s['platform']}; whole 1023x853 campaign sheet evidence inspected; static-sheet source timing unavailable.","OBSERVED SOURCE HOOK: complete sheet includes labeled kick table/barrel family; this earns a body→environment-object contact problem but not this synthetic choreography.","RIGHTS: evidence only; independent generic ASCII rig; no source pixels/palette/costume/contours/layout/tracing/choreography/redistribution/close imitation; Drew work not used.","TIMING: every decisive key is INFERRED / STREET_FIGHTER-CAPCOM. ONES/TWOS/FOURS are display classes, never seconds.","VISIBLE LAW: [O] is a generic object, @ is a TRANSIENT NON-CUSTODIAL seam, # is A's trusted rear/root pin. CUSTODY remains NONE in every key."]
    parts=['\n'.join(lead)]
    for q in m['keys']:
        st={'A':expand_pose(q['a']),'object':[float(q['object'][0]),float(q['object'][1])],'contact':q['contact'],'custody':q['custody'],'object_support':q['object_support'],'support':q['support'],'root':q['root'],'force':q.get('force',[0,0])}
        meta=(f"{q['id']}  {q['p']}  [{q['timing']}/{q['provenance']}]\n" f"contact={q['contact']} | custody={q['custody']} | object_support={q['object_support']} | support={q['support']} | root={q['root']}\n" f"force={q['force']} | object={q['object']}\nrole={q['role']}\narc={q['arc']}")
        parts.append(meta+'\n'+render_ascii(st))
    return ('\n'+'='*96+'\n').join(parts)+'\n'

def lerp(a,b,t): return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]

def interp_pose(a0,a1,t,curve=0.0):
    s=t*t*(3-2*t); out={}
    for n in a0:
        x0,y0=a0[n]; x1,y1=a1[n]; x=x0+(x1-x0)*s; y=y0+(y1-y0)*s
        if n in ('head','hand_f','hand_b','knee_f','foot_f'): y += curve*math.sin(math.pi*t)
        out[n]=[x,y]
    return out

def key_state(q):
    return {'id':q['id'],'phase':q['p'],'A':expand_pose(q['a']),'object':[float(q['object'][0]),float(q['object'][1])],'contact':q['contact'],'custody':q['custody'],'object_support':q['object_support'],'support':q['support'],'root':q['root'],'force':q.get('force',[0,0])}

def sequence(m):
    out=[]
    bridge_counts={'C014-K0':2,'C014-K1':2,'C014-K2':3,'C014-K4':1,'C014-K6':2,'C014-K7':2,'C014-K8':2,'C014-K9':1,'C014-K10':2}
    curves={'C014-K0':-0.3,'C014-K1':0.6,'C014-K2':-1.1,'C014-K4':0.25,'C014-K6':1.0,'C014-K7':0.8,'C014-K8':-0.7,'C014-K9':-0.5,'C014-K10':0.35}
    for i,q in enumerate(m['keys']):
        k=key_state(q); out.extend([k]*TIMING[q['timing']])
        if i+1 < len(m['keys']):
            n=m['keys'][i+1]; nk=key_state(n); count=bridge_counts.get(q['id'],0)
            for j in range(1,count+1):
                t=j/(count+1); obj=lerp(k['object'],nk['object'],t)
                out.append({**k,'id':q['id']+'~'+n['id'],'phase':'AUTHORED_CONNECTIVE','A':interp_pose(k['A'],nk['A'],t,curves.get(q['id'],0.0)),'object':obj,'force':lerp(k['force'],nk['force'],t)})
    return out

def fonts():
    p='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
    if Path(p).exists(): return ImageFont.truetype(p,12), ImageFont.truetype(p,11)
    return ImageFont.load_default(), ImageFont.load_default()

def render_video(m):
    if TMP.exists(): shutil.rmtree(TMP)
    FRAMES.mkdir(parents=True); mainf,smallf=fonts(); seq=sequence(m)
    for i,k in enumerate(seq):
        im=Image.new('RGB',(IMG_W,IMG_H),(8,8,8)); d=ImageDraw.Draw(im)
        d.text((10,8),f"{k['id']}  {k['phase']}",font=smallf,fill=(245,245,245))
        d.text((10,24),f"CONTACT {k['contact']}   CUSTODY {k['custody']}   OBJECT {k['object_support']}",font=smallf,fill=(205,205,205))
        d.text((10,40),f"SUPPORT {k['support']}   ROOT {k['root']}   FORCE {k['force']}",font=smallf,fill=(175,175,175))
        d.multiline_text((10,62),render_ascii(k),font=mainf,fill=(248,248,248),spacing=-2)
        im.save(FRAMES/f"f-{i:04d}.png")
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(FRAMES/'f-%04d.png'),'-c:v','libx264','-preset','medium','-crf','38','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
    return seq

def gz64(text): return base64.b64encode(gzip.compress(text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
def js_chunks(s,n=960): return ',\n'.join(json.dumps(s[i:i+n]) for i in range(0,len(s),n))

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
    m=json.loads(MOTION_PATH.read_text(encoding='utf-8')); sheet=contact_sheet(m); ASCII_PATH.write_text(sheet,encoding='utf-8')
    seq=render_video(m); mp4=MP4.read_bytes(); got=hashlib.sha256(mp4).hexdigest(); expected=m.get('motion_dungeon',{}).get('media_sha256')
    if expected and got != expected: raise SystemExit(f"media hash mismatch expected={expected} got={got}")
    SPA_PATH.write_text(build_spa(m,sheet,mp4),encoding='utf-8')
    print(json.dumps({'frames':len(seq),'media_sha256':got,'media_bytes':len(mp4),'sheet_sha256':hashlib.sha256(sheet.encode()).hexdigest(),'spa_sha256':hashlib.sha256(SPA_PATH.read_bytes()).hexdigest()},sort_keys=True))

if __name__=='__main__': main()
