#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, json, subprocess, tempfile, hashlib
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=json.loads((ROOT/'motion.json').read_text(encoding='utf-8'))
GW=MOTION['rig']['grid']['width']; GH=MOTION['rig']['grid']['height']
W=MOTION['compile']['width']; H=MOTION['compile']['height']; FPS=MOTION['compile']['fps']
HOLDS=MOTION['compile']['timing_frames']
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
VIDEO_NAME='detached-threat-impact-clock-fork-debt.mp4'
SPA_NAME='detached-threat-impact-clock-fork-debt.motion.html'

def bres(a,b):
    x0,y0=a; x1,y1=b; pts=[]; dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return pts

def put(g,x,y,ch):
    if 0<=x<GW and 0<=y<GH: g[y][x]=ch

def line(g,a,b,ch):
    for x,y in bres(tuple(a),tuple(b)): put(g,x,y,ch)

def interp(a,b,t):
    return [round(a[0]+(b[0]-a[0])*t), round(a[1]+(b[1]-a[1])*t)]

def topology(k):
    return (k['support_contact'], k['contact'], k['threat_state'], k['rear_foot_state'], k['front_foot_state'])

def blend(a,b,t):
    out=dict(a)
    for key in ['root','head','rear_hand','front_hand','rear_knee','front_knee','rear_foot','front_foot']:
        out[key]=interp(a[key],b[key],t)
    ta=a.get('threat'); tb=b.get('threat')
    out['threat']=interp(ta,tb,t) if ta is not None and tb is not None else (ta if ta is not None else tb)
    out['key_id']=f"{a['key_id']}~{b['key_id']}"
    out['name']='AUTHORED_CONNECTIVE'
    return out

def foot_symbol(state):
    return {'ACTIVE':'*','LIGHT':'.','AIR':'o','PROBE':'?'}[state]

def target_visible(k):
    return k['key_id'] in {'K06','K07','K08','K09'}

def threat_symbol(k):
    s=k['threat_state']
    if s=='PRECONTACT': return '?'
    if s=='IMPACT': return 'X'
    if s=='DISSIPATE': return '#'
    if s=='ABSENT': return None
    return '#'

def ascii_state(k,label=True):
    g=[[' ']*GW for _ in range(GH)]
    tx=k['target_x']
    if target_visible(k):
        for y in range(6,18): put(g,tx,y,'|')
    root=k['root']; head=k['head']
    neck=[round((root[0]+head[0])/2), max(root[1]-3,0)]
    line(g,root,neck,'|'); line(g,neck,head,'|'); put(g,*head,'O')
    line(g,neck,k['rear_hand'],'/'); line(g,neck,k['front_hand'],'\\')
    put(g,*k['rear_hand'],'+'); put(g,*k['front_hand'],'+')
    line(g,root,k['rear_knee'],'/'); line(g,k['rear_knee'],k['rear_foot'],'/')
    line(g,root,k['front_knee'],'\\'); line(g,k['front_knee'],k['front_foot'],'\\')
    put(g,*k['rear_knee'],'o'); put(g,*k['front_knee'],'o')
    put(g,*k['rear_foot'],foot_symbol(k['rear_foot_state']))
    put(g,*k['front_foot'],foot_symbol(k['front_foot_state']))
    put(g,*root,'@')
    th=k.get('threat'); sym=threat_symbol(k)
    if th is not None and sym is not None:
        put(g,*th,sym)
        if k['threat_state'] in {'FREE','TRAVEL','PRECONTACT'}:
            for x in range(max(th[0]-4,0), th[0]): put(g,x,th[1],'>')
        elif k['threat_state']=='DISSIPATE':
            if th[0]-1>=0: put(g,th[0]-1,th[1],'~')
            if th[0]+1<GW: put(g,th[0]+1,th[1],'~')
    for x in range(2,GW-2,4): put(g,x,22,'_')
    rows=[''.join(r).rstrip() for r in g]
    body='\n'.join(rows)
    if not label: return body
    return f"{k['key_id']} {k['name']}\n{body}"

def make_contact_sheet():
    legend=(
        "ASCII KINESIS V2 STRIKES023 - DETACHED THREAT IMPACT / CLOCK FORK DEBT\n"
        "Legend: O head | @ pelvis/root | + hands | o knees/air foot | * active support | . light support | ? probe/precontact | # detached threat | X threat impact | | abstract target\n"
        "Principle: THE BODY FIRES THE THREAT AND STARTS TO LEAVE; THE HIT ARRIVES ON ANOTHER CLOCK. IMPACT CANNOT REWIND THE LAUNCHER.\n"
        "All decisive timing provenance: INFERRED / STREET_FIGHTER-CAPCOM. Source-authentic timing and hit-stop: UNKNOWN.\n"
        "Rights: independent abstract ASCII rig only; no source pixels, palette, costume, contours, layout, source choreography, audio, tracing, redistribution, or close imitation.\n\n"
    )
    chunks=[]
    for k in MOTION['keys']:
        meta=(
            f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']} | causal_role={k['causal_role']}\n"
            f"support={k['support_contact']} | contact={k['contact']} | threat_state={k['threat_state']}\n"
            f"root_note={k['motion_arc_root_note']}\n"
            f"rear_foot={k['rear_foot_state']} | front_foot={k['front_foot_state']}"
        )
        chunks.append(ascii_state(k)+"\n"+meta)
    return legend+'\n\n'.join(chunks)+'\n'

def render_frame(k,path):
    img=Image.new('RGB',(W,H),'black'); d=ImageDraw.Draw(img)
    font=ImageFont.truetype(FONT,12); small=ImageFont.truetype(FONT,10)
    d.text((10,8),f"STRIKES023 | {k['key_id']} | {k['name']}",font=small,fill='white')
    d.multiline_text((10,28),ascii_state(k,label=False),font=font,fill='white',spacing=0)
    d.text((10,H-48),"LAUNCHER CLOCK: COIL -> DRIVE -> RELEASE -> RECOIL -> SUPPORT CATCH -> SHOULDER LAG -> DISPLACED READY",font=small,fill='white')
    d.text((10,H-34),"THREAT CLOCK: HELD -> RELEASED -> TRAVEL -> PRECONTACT -> IMPACT HOLD -> CLEAR",font=small,fill='white')
    d.text((10,H-20),"JOIN LAW: THREAT CONTACT MAY HOLD LOCALLY; IT DOES NOT FREEZE OR REWIND THE LAUNCHER",font=small,fill='white')
    img.save(path)

def compile_frames():
    frames=[]; keys=MOTION['keys']
    for i,k in enumerate(keys):
        frames.extend([k]*HOLDS[k['timing_class']])
        if i<len(keys)-1 and k.get('bridge_after',0):
            nxt=keys[i+1]
            if topology(k)==topology(nxt):
                frames.append(blend(k,nxt,0.5))
    return frames

def build_video(out):
    frames=compile_frames()
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,k in enumerate(frames): render_frame(k,td/f'{i:04d}.png')
        subprocess.run([
            'ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(td/'%04d.png'),
            '-c:v','libx264','-crf','38','-preset','veryslow','-pix_fmt','yuv420p','-movflags','+faststart',str(out)
        ],check=True)
    return len(frames)

def make_spa(ascii_text,motion_text,video_bytes):
    a64=base64.b64encode(gzip.compress(ascii_text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
    j64=base64.b64encode(gzip.compress(motion_text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
    v64=base64.b64encode(video_bytes).decode('ascii')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Strikes023 - Detached Threat Impact / Clock Fork Debt</title>
<style>body{{margin:0;background:#0b0c0f;color:#f3f3f3;font-family:ui-monospace,Menlo,Consolas,monospace}}nav{{position:sticky;top:0;background:#15171d;padding:10px;display:flex;gap:8px}}button{{font:inherit;padding:8px 14px}}main{{padding:12px}}section{{display:none}}section.active{{display:block}}pre{{white-space:pre;overflow:auto;font-variant-ligatures:none;line-height:1}}video{{max-width:100%;height:auto;background:black}}</style></head><body>
<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><main>
<section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls loop playsinline src="data:video/mp4;base64,{v64}"></video></section>
</main><script>
const ss=[...document.querySelectorAll('section')];for(const b of document.querySelectorAll('button[data-view]'))b.onclick=()=>{{ss.forEach(s=>s.classList.toggle('active',s.id===b.dataset.view));}};
async function gunzip(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip')));return r.text();}}
Promise.all([gunzip('{a64}'),gunzip('{j64}')]).then(([a,j])=>{{document.getElementById('a').textContent=a;document.getElementById('j').textContent=j;}});
</script></body></html>"""

def main():
    contact=make_contact_sheet()
    (ROOT/'contact-sheet.txt').write_text(contact,encoding='utf-8')
    video=ROOT/VIDEO_NAME
    n=build_video(video)
    motion_text=(ROOT/'motion.json').read_text(encoding='utf-8')
    (ROOT/SPA_NAME).write_text(make_spa(contact,motion_text,video.read_bytes()),encoding='utf-8')
    print(json.dumps({'frames':n,'fps':FPS,'video':str(video),'spa':str(ROOT/SPA_NAME),
                      'video_bytes':video.stat().st_size,'video_sha256':hashlib.sha256(video.read_bytes()).hexdigest()},sort_keys=True))

if __name__=='__main__': main()
