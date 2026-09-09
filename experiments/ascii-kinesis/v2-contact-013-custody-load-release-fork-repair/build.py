#!/usr/bin/env python3
from pathlib import Path
import base64, gzip, hashlib, json, math, shutil, subprocess
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION_PATH=ROOT/'motion.json'
ASCII_PATH=ROOT/'contact-sheet.txt'
SPA_PATH=ROOT/'custody-load-release-fork-repair.motion.html'
TMP=ROOT/'.motion-build'; FRAMES=TMP/'frames'; MP4=TMP/'motion.mp4'
W,H,GROUND_Y=96,26,21
IMG_W,IMG_H,FPS=800,440,24
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
    j=state['A']
    for a,b in [('head','shoulder'),('shoulder','pelvis'),('shoulder','hand_f'),('shoulder','hand_b'),('pelvis','foot_f'),('pelvis','foot_b')]:
        paint_line(g,j[a],j[b],seg_char(j[a],j[b]))
    for n,ch in [('head','A'),('shoulder','O'),('pelvis','X'),('hand_f','*'),('hand_b','*'),('foot_f','^'),('foot_b','^')]:
        x,y=j[n]; x=int(round(x)); y=int(round(y))
        if 0<=x<W and 0<=y<H: g[y][x]=ch

    pin=state.get('pin')
    if pin:
        x,y=map(lambda v:int(round(v)),pin)
        if 0<=x<W and 0<=y<H: g[y][x]='#'

    px,py=state['P']; px=int(round(px)); py=int(round(py))
    payload='[Q]'
    for off,ch in zip((-1,0,1),payload):
        x=px+off
        if 0<=x<W and 0<=py<H: g[py][x]=ch

    z=state.get('anchor')
    if z and state['contact'] not in ('NONE','RELEASED'):
        zx,zy=map(lambda v:int(round(v)),z)
        paint_line(g,[zx,zy],[px,py],'=',overwrite=True)
        if 0<=zx<W and 0<=zy<H: g[zy][zx]='@'
        dx,dy=state.get('force',[0,0])
        if dx or dy:
            end=[zx+dx,zy+dy]
            paint_line(g,[zx,zy],end,'=',overwrite=True)
            ex,ey=map(lambda v:int(round(v)),end)
            if 0<=ex<W and 0<=ey<H:
                if abs(dx)>=abs(dy): g[ey][ex]='>' if dx>=0 else '<'
                else: g[ey][ex]='v' if dy>=0 else '^'
            if 0<=zx<W and 0<=zy<H: g[zy][zx]='@'
            # payload remains visually authoritative over the force axis
            for off,ch in zip((-1,0,1),payload):
                x=px+off
                if 0<=x<W and 0<=py<H: g[py][x]=ch

    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet(m):
    rev=m['revision']; src=m['source']
    lead=[
        m['experiment_id'],
        m['principle'],
        f"REVISION: revises={rev['revises']} | negative_fixture={rev['negative_fixture']} | source_change={str(rev['source_change']).lower()}.",
        f"SOURCE EVIDENCE: TSR asset {src['asset_id']}, {src['title']} — {src['game']} — {src['platform']}; archive SHA-256 {src['archive_sha256']}; {src['archive_items']} items ({src['nonpalette_pngs']} non-palette PNG + {src['palette_files']} palette); source timing/order unavailable.",
        "RIGHTS: evidence only; independent abstract ASCII rig; no source pixels/palette/layout/contours/tracing/choreography/redistribution/close imitation; Drew work not used.",
        "TIMING: ONES/TWOS/FOURS are display classes, never seconds; every decisive key INFERRED / STREET_FIGHTER-CAPCOM.",
        "VISIBLE LAW: @ is the custody seam; # is the current root pin; [Q] is the abstract payload. [Q] may not lead an independent clock until C013-K7 RELEASE."
    ]
    parts=['\n'.join(lead)]
    for q in m['keys']:
        state={'A':expand_pose(q['r']),'P':q['P'],'contact':q['c'],'anchor':q.get('z'),'force':q.get('f',[0,0]),'pin':q.get('pin')}
        meta=(f"{q['id']}  {q['p']}  [{q['timing']}/{q['provenance']}]\n"
              f"contact={q['c']} | custody={q['u']} | support={q['s']} | root={q['o']}\n"
              f"payload={q['payload_state']} | release_gate={q['release_gate']} | support_phase={q['support_phase']} | force={q['f']} | anchor={q.get('z')} | pin={q.get('pin')}\n"
              f"role={q['q']}\narc={q['a']}")
        parts.append(meta+'\n'+render_ascii(state))
    return ('\n'+'='*96+'\n').join(parts)+'\n'

def interp_pose(a0,a1,t,curve):
    out={}; s=t*t*(3-2*t)
    for n in a0:
        x0,y0=a0[n]; x1,y1=a1[n]
        x=x0+(x1-x0)*s; y=y0+(y1-y0)*s
        if n in ('head','hand_f','hand_b'): y+=curve*math.sin(math.pi*t)
        out[n]=[x,y]
    return out

def interp_pt(a,b,t,curve):
    s=t*t*(3-2*t)
    x=a[0]+(b[0]-a[0])*s
    y=a[1]+(b[1]-a[1])*s + curve*math.sin(math.pi*t)
    return [x,y]

def lerp_vec(a,b,t):
    if a is None or b is None: return a
    return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]

def semantic_signature(q):
    return (q['c'],q['u'],q['s'],q['o'],q['release_gate'],q['payload_state'])

def key_state(q):
    return {'id':q['id'],'phase':q['p'],'A':expand_pose(q['r']),'P':[float(q['P'][0]),float(q['P'][1])],
            'contact':q['c'],'custody':q['u'],'support_contact':q['s'],'root':q['o'],
            'release_gate':q['release_gate'],'payload_state':q['payload_state'],'anchor':q.get('z'),
            'force':q.get('f',[0,0]),'pin':q.get('pin')}

def sequence(m):
    out=[]
    for i,q in enumerate(m['keys']):
        k=key_state(q)
        out.extend([k]*TIMING[q['timing']])
        if i+1<len(m['keys']):
            n=m['keys'][i+1]
            if semantic_signature(q)==semantic_signature(n):
                nk=key_state(n)
                for t in (1/3,2/3):
                    out.append({**k,'id':q['id']+'~'+n['id'],'phase':'AUTHORED_CONNECTIVE',
                                'A':interp_pose(k['A'],nk['A'],t,float(q.get('curveA',-0.5))),
                                'P':interp_pt(k['P'],nk['P'],t,float(q.get('curveP',-1.0))),
                                'anchor':lerp_vec(k.get('anchor'),nk.get('anchor'),t),
                                'force':lerp_vec(k.get('force',[0,0]),nk.get('force',[0,0]),t),
                                'pin':lerp_vec(k.get('pin'),nk.get('pin'),t)})
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
        d.text((10,24),f"CONTACT {k['contact']}   CUSTODY {k['custody']}   RELEASE {k['release_gate']}   PAYLOAD {k['payload_state']}",font=smallf,fill=(205,205,205))
        d.text((10,40),f"SUPPORT {k['support_contact']}   ROOT {k['root']}   FORCE {k['force']}",font=smallf,fill=(175,175,175))
        d.multiline_text((10,62),render_ascii(k),font=mainf,fill=(248,248,248),spacing=-2)
        im.save(FRAMES/f'f-{i:04d}.png')
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(FRAMES/'f-%04d.png'),'-c:v','libx264','-preset','medium','-crf','40','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
    return seq

def gz64(text): return base64.b64encode(gzip.compress(text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
def js_chunks(s,n=960): return ',\n'.join(json.dumps(s[i:i+n]) for i in range(0,len(s),n))

def build_spa(m,sheet,mp4):
    a=gz64(sheet); j=gz64(json.dumps(m,separators=(',',':'),ensure_ascii=True)); v=base64.b64encode(mp4).decode('ascii')
    return f"""<!doctype html>
<html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{m['experiment_id']}</title>
<style>html,body{{margin:0;background:#0b0b0b;color:#eee;font-family:system-ui,sans-serif}}nav{{position:sticky;top:0;background:#111;padding:8px;border-bottom:1px solid #444}}button[data-view]{{margin-right:8px;padding:8px 14px}}section{{display:none;padding:12px}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Consolas,\"Liberation Mono\",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08}}video{{display:block;max-width:100%;height:auto;margin:auto}}</style></head>
<body><nav><button data-view=\"ascii\">ASCII</button><button data-view=\"json\">JSON</button><button data-view=\"video\">VIDEO</button></nav>
<section id=\"ascii\" class=\"active\"><pre id=\"a\"></pre></section>
<section id=\"json\"><pre id=\"j\"></pre></section>
<section id=\"video\"><video id=\"v\" controls autoplay loop muted playsinline src=\"data:video/mp4;base64,{v}\"></video></section>
<script>
const A={json.dumps(a)};
const J={json.dumps(j)};
const D=async s=>new TextDecoder().decode(await new Response(new Blob([Uint8Array.from(atob(s),c=>c.charCodeAt(0))]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());
(async()=>{{document.getElementById('a').textContent=await D(A);document.getElementById('j').textContent=await D(J);}})();
document.querySelectorAll('button[data-view]').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('section').forEach(s=>s.classList.remove('active'));document.getElementById(b.dataset.view).classList.add('active')}}));
</script></body></html>"""

def main():
    m=json.loads(MOTION_PATH.read_text(encoding='utf-8'))
    sheet=contact_sheet(m); ASCII_PATH.write_text(sheet,encoding='utf-8')
    seq=render_video(m); mp4=MP4.read_bytes(); got=hashlib.sha256(mp4).hexdigest()
    expected=m.get('motion_dungeon',{}).get('media_sha256')
    if expected and got!=expected: raise SystemExit(f'media hash mismatch expected={expected} got={got}')
    SPA_PATH.write_text(build_spa(m,sheet,mp4),encoding='utf-8')
    print(json.dumps({'frames':len(seq),'media_sha256':got,'media_bytes':len(mp4),'sheet_sha256':hashlib.sha256(sheet.encode()).hexdigest(),'spa_sha256':hashlib.sha256(SPA_PATH.read_bytes()).hexdigest()},sort_keys=True))

if __name__=='__main__': main()
