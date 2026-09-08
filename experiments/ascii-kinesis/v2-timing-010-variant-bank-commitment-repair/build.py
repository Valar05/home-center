#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

D=Path(__file__).resolve().parent
M=D/'motion.json'
C=D/'contact-sheet.txt'
V=D/'variant-bank-commitment-repair.motion.mp4'
H=D/'variant-bank-commitment-repair.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
GW,GH=52,22
W,HPIX=720,400
GROUND=20
MARK={'root':'@','chest':'+','head':'O','left_shoulder':'o','left_elbow':'o','left_hand':'a',
      'right_shoulder':'o','right_elbow':'o','right_hand':'b','left_hip':'o','left_knee':'o',
      'left_foot':'L','right_hip':'o','right_knee':'o','right_foot':'R'}

def sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()

def bline(a,b):
    x,y=a; X,Y=b; dx=abs(X-x); sx=1 if x<X else -1; dy=-abs(Y-y); sy=1 if y<Y else -1; e=dx+dy; out=[]
    while True:
        out.append((x,y))
        if (x,y)==(X,Y): return out
        q=2*e
        if q>=dy: e+=dy; x+=sx
        if q<=dx: e+=dx; y+=sy

def glyph(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>2*abs(dy): return '-'
    if abs(dy)>2*abs(dx): return '|'
    return '\\' if dx*dy>0 else '/'

def resolved(m,k):
    names=m['rig_schema']['joint_order']
    return {n:list(k['pose_rig']['coords'][i]) for i,n in enumerate(names)}

def ease(t,name):
    if name=='EASE_IN': return t*t
    if name=='EASE_OUT': return 1-(1-t)*(1-t)
    if name=='SMOOTHSTEP': return t*t*(3-2*t)
    return t

def quad(p,q,t,bias,mag):
    cx=(p[0]+q[0])/2+bias[0]*mag
    cy=(p[1]+q[1])/2+bias[1]*mag
    u=1-t
    return [round(u*u*p[0]+2*u*t*cx+t*t*q[0]), round(u*u*p[1]+2*u*t*cy+t*t*q[1])]

def interpolate(a,b,t,bias):
    out={}
    for n,p in a.items():
        q=b[n]
        mag=2.2 if ('hand' in n or 'head' in n) else 1.7 if ('elbow' in n or 'knee' in n) else 1.0
        out[n]=quad(p,q,t,bias,mag)
    return out

def art(m,state):
    links=[tuple(x) for x in m['rig_schema']['links']]
    g=[[' ']*GW for _ in range(GH)]
    def put(x,y,c):
        if 0<=x<GW and 0<=y<GH: g[y][x]=c
    j={n:tuple(state[n]) for n in m['rig_schema']['joint_order']}
    for a,b in links:
        for x,y in bline(j[a],j[b])[1:-1]:
            if 0<=x<GW and 0<=y<GH and g[y][x]==' ': put(x,y,glyph(j[a],j[b]))
    for n,(x,y) in j.items(): put(x,y,MARK[n])
    for x in range(4,48):
        if g[GROUND][x]==' ': put(x,GROUND,'_')
    return '\n'.join(''.join(r).rstrip() for r in g)

def branch_timeline(m,branch):
    by={k['key_id']:k for k in m['keys']}
    seq=m['variant_bank']['variants'][branch]['sequence']
    frames=[]
    for i,kid in enumerate(seq):
        k=by[kid]
        p=resolved(m,k)
        h=HOLD[k['timing_class']]
        for n in range(h):
            frames.append({'state':p,'key':k,'branch':branch,'kind':'HOLD','detail':f'{n+1}/{h}'})
        if i==len(seq)-1: continue
        nxt=by[seq[i+1]]
        spec=k['bridge_to_next']; q=int(spec['frames'])
        if q:
            if k['support_topology'] != nxt['support_topology']:
                raise SystemExit(f"bridge crosses support topology: {k['key_id']}->{nxt['key_id']}")
            if k['contact_topology'] != nxt['contact_topology']:
                raise SystemExit(f"bridge crosses contact topology: {k['key_id']}->{nxt['key_id']}")
            a=p; b=resolved(m,nxt)
            for z in range(1,q+1):
                t=ease(z/(q+1),spec['easing'])
                frames.append({'state':interpolate(a,b,t,spec['arc_bias']),
                               'key':k,'branch':branch,'kind':'ARC','detail':f'{z}/{q}->{nxt["key_id"]}'})
    return frames

def key_block(m,k):
    state=resolved(m,k)
    return [
      f"[{k['key_id']}] {k['name']} | branch={k['branch']}",
      f"pose/rig={k['pose_rig']['rig_id']}",
      f"support/contact={k['support_contact']} | support_topology={k['support_topology']} | contact_topology={k['contact_topology']}",
      f"root/motion-arc={k['motion_arc_root_note']}",
      f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']} | policy=STREET_FIGHTER/CAPCOM",
      f"causal_role={k['causal_role']}",
      f"clocks BODY={k['clock_state']['BODY_CLOCK']} | CONFIG={k['clock_state']['CONFIG_AXIS']}",
      art(m,state),''
    ]

def sheet(m):
    by={k['key_id']:k for k in m['keys']}
    out=[
      'ASCII KINESIS V2 TIMING 010 - VARIANT BANK / ZERO-TIME COMMITMENT REPAIR',
      f"revises: {m['revises']}",
      f"negative_fixture: {m['negative_fixture']}",
      'SOURCE ART: NONE | TSR ASSET 41182 EVIDENCE FAMILY INHERITED | SOURCE TIMING: NONE OBSERVED',
      'TIMING: STREET_FIGHTER/CAPCOM | ONES=1 display frame | TWOS=2 | FOURS=4 | 1s/2s/4s ARE CLASSES, NEVER SECONDS',
      'ZERO-TIME LAW: BANK_SELECT changes CONFIG_AXIS only, consumes 0 BODY_CLOCK ticks, and creates no full-body key.',
      'VISIBLE TEST: the same shared READY -> QUERY -> DEEP COIL feeds two alternate compilations; A and B must diverge in support, silhouette, cadence, overshoot/lag, and recovery debt.',
      'GLYPHS: O head, @ COM/root, L/R feet, a/b hands.',
      '',
      '=== SHARED PRECOMMIT KEYS ===',''
    ]
    for kid in m['variant_bank']['shared_prefix']: out.extend(key_block(m,by[kid]))
    out += [
      '=== ZERO-TIME CONFIG AXIS EVENT ===',
      'BANK_SELECT {scope=CONFIG_AXIS, BODY_CLOCK=PRESERVE_PHASE, body_tick_cost=0}',
      'No pose exists for selection itself. The next authored body key is the selected branch commitment.',
      '',
      '=== VARIANT A : LOW_RIGHT_CROSS ===',''
    ]
    for kid in m['variant_bank']['variants']['A']['sequence'][len(m['variant_bank']['shared_prefix']):]:
        out.extend(key_block(m,by[kid]))
    out += ['=== VARIANT B : HIGH_LEFT_WHIP ===','']
    for kid in m['variant_bank']['variants']['B']['sequence'][len(m['variant_bank']['shared_prefix']):]:
        out.extend(key_block(m,by[kid]))
    out += [
      'RIGHTS FIREWALL: no source pixels, palette, contours, costume, sheet layout, tracing, choreography, redistribution, or close imitation.',
      'CONNECTIVE MOTION: deterministic authored arcs only while support/contact topology is unchanged; support changes snap only at decisive keys.',
      'PRESENTATION: VIDEO serializes two alternate compilations A then B. The between-compile card is presentation time only, not BODY_CLOCK.'
    ]
    return '\n'.join(out).rstrip()+'\n'

def get_font(size):
    for fp in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf'):
        try: return ImageFont.truetype(fp,size)
        except Exception: pass
    return ImageFont.load_default()

def frame_text(m,f):
    k=f['key']; br=f['branch']; label=m['variant_bank']['variants'][br]['label']
    return '\n'.join([
      f"COMPILE {br} / {label}",
      f"{k['key_id']}  {k['name']}   {k['timing_class']} / {k['timing_provenance']}",
      f"BODY={k['clock_state']['BODY_CLOCK']}   CONFIG={k['clock_state']['CONFIG_AXIS']}   {f['kind']} {f['detail']}",
      '',
      art(m,f['state'])
    ])

def gap_text(m):
    return '\n'.join([
      'ALTERNATE COMPILE',
      '',
      'BANK_SELECT -> B',
      'CONFIG_AXIS changes at ZERO BODY TICKS.',
      'BODY_CLOCK is not rewound by a hidden pose.',
      '',
      'Same shared precommit keys follow; different commitment earns different motion.'
    ])

def render_png(text,path):
    im=Image.new('RGB',(W,HPIX),'black')
    d=ImageDraw.Draw(im)
    d.multiline_text((58,12),text,font=get_font(15),fill='white',spacing=1)
    im.save(path)

def spa(m,s,v):
    def b64lines(data:bytes)->str:
        enc=base64.b64encode(data).decode('ascii')
        return '\n'.join(enc[i:i+76] for i in range(0,len(enc),76))
    ascii_gz=b64lines(gzip.compress(s.encode('utf-8'),compresslevel=9,mtime=0))
    motion_raw=(json.dumps(m,separators=(',',':'),ensure_ascii=False)+'\n').encode('utf-8')
    motion_gz=b64lines(gzip.compress(motion_raw,compresslevel=9,mtime=0))
    vid=b64lines(v)
    return rf'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Timing 010 Variant Bank Commitment Repair</title>
<style>:root{{color-scheme:dark;background:#0f0f0f;color:#eee}}body{{margin:1rem;font-family:system-ui}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#0f0f0f;padding:.4rem 0}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0;white-space:pre;overflow:auto;line-height:1.08}}video{{max-width:100%;height:auto}}</style>
</head>
<body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>
<section id="ascii"><pre id="ascii-text"></pre></section>
<section id="json" hidden><pre id="json-text"></pre></section>
<section id="video" hidden><video id="motion-video" controls autoplay muted loop playsinline></video></section>
<script id="ascii-gzip" type="text/plain">
{ascii_gz}
</script>
<script id="motion-gzip" type="text/plain">
{motion_gz}
</script>
<script id="video-data" type="text/plain">
{vid}
</script>
<script>
const compact=id=>document.querySelector(id).textContent.replace(/\s+/g,"");
const bytes=b64=>Uint8Array.from(atob(b64),c=>c.charCodeAt(0));
async function gunzipText(b64){{
  const stream=new Blob([bytes(b64)]).stream().pipeThrough(new DecompressionStream("gzip"));
  return new TextDecoder().decode(await new Response(stream).arrayBuffer());
}}
Promise.all([gunzipText(compact("#ascii-gzip")),gunzipText(compact("#motion-gzip"))]).then(([a,j])=>{{
  document.querySelector("#ascii-text").textContent=a;
  document.querySelector("#json-text").textContent=JSON.stringify(JSON.parse(j),null,2);
}});
const VIDEO_PREFIX="data:video/mp4;base64,";
document.querySelector("#motion-video").src=VIDEO_PREFIX+compact("#video-data");
const B=[...document.querySelectorAll("button[data-view]")],S=[...document.querySelectorAll("section")];
B.forEach(b=>b.onclick=()=>S.forEach(s=>s.hidden=s.id!==b.dataset.view));
</script>
</body>
</html>
'''

def main():
    m=json.loads(M.read_text(encoding='utf-8'))
    s=sheet(m); C.write_text(s,encoding='utf-8')
    frames=[]
    for branch in m['compile']['branch_order']:
        frames.extend(branch_timeline(m,branch))
        if branch != m['compile']['branch_order'][-1]:
            frames.extend([{'card':True,'branch':branch} for _ in range(int(m['compile']['presentation_gap_frames']))])
    with tempfile.TemporaryDirectory(prefix='akv2-t010-') as td:
        td=Path(td)
        for i,f in enumerate(frames):
            render_png(gap_text(m) if f.get('card') else frame_text(m,f),td/f'f{i:03d}.png')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(m['compile']['fps']),
                        '-i',str(td/'f%03d.png'),'-an','-c:v','libx264','-preset','veryslow','-crf','27',
                        '-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1','-threads','1',
                        '-fflags','+bitexact','-flags:v','+bitexact',str(V)],check=True)
    v=V.read_bytes()
    m['compile'].update(video_frames_total=len(frames),media_sha256=sha(v),media_bytes=len(v),ascii_sheet_sha256=sha(s.encode()))
    M.write_text(json.dumps(m,separators=(',',':'),ensure_ascii=False)+'\n',encoding='utf-8')
    H.write_text(spa(m,s,v),encoding='utf-8')
    print(json.dumps({'video_frames_total':len(frames),'media_sha256':sha(v),'media_bytes':len(v),
                      'ascii_sheet_sha256':sha(s.encode()),'html_sha256':sha(H.read_bytes())},sort_keys=True))

if __name__=='__main__':
    main()
