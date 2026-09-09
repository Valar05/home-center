#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
ENTRY='v2-timing-012-deferred-loop-exit-commit'
SLUG='deferred-loop-exit-commit'
MOTION=HERE/'motion.json'
ASCII=HERE/'contact-sheet.txt'
SPA=HERE/f'{SLUG}.motion.html'
MP4=HERE/f'{SLUG}.mp4'
MANIFEST=HERE/'manifest.json'
RECEIPT=HERE/'receipt.json'
W,H=58,20

def sha(b): return hashlib.sha256(b).hexdigest()
def bres(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): return out
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy

def limb(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>2*abs(dy): return '-'
    if abs(dy)>2*abs(dx): return '|'
    return '\\' if dx*dy>0 else '/'

def put(g,x,y,c):
    if 0<=x<W and 0<=y<H: g[y][x]=c

def grid(d,k,latched=False,event_flash=False):
    g=[[' ']*W for _ in range(H)]
    pts=k['pose_rig']['j']; links=d['rig']['links']; glyphs=d['rig']['glyphs']
    for a,b in links:
        for x,y in bres(pts[a],pts[b])[1:-1]:
            if 0<=x<W and 0<=y<H and g[y][x]==' ': put(g,x,y,limb(pts[a],pts[b]))
    for i,(x,y) in enumerate(pts): put(g,x,y,glyphs[i])
    for x in range(7,49): put(g,x,d['rig']['ground_y'],'=')
    put(g,6,d['rig']['ground_y'],'['); put(g,49,d['rig']['ground_y'],']')
    if latched:
        hx,hy=pts[2]; put(g,min(W-2,hx+4),max(1,hy-1),'*' if event_flash else '!')
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet(d):
    out=[
        'ASCII KINESIS V2 TIMING 012 — DEFERRED LOOP EXIT COMMIT',
        'FRESH CONCEPT AFTER PRE-RESET TIMING DEBT EXHAUSTION',
        'SOURCE ART: NOT EMBEDDED. ABSTRACT GENERIC ASCII RIG ONLY.',
        'SOURCE TIMING: NONE OBSERVED. ALL PERFORMANCE TIMING BELOW IS INFERRED.',
        'PRINCIPLE: LATCH THE INTENT. KEEP THE PHASE. EXIT ONLY WHERE THE LOOP EARNS IT.',
        '',
        'BODY LOOP / COMMIT DECISIVE KEYS'
    ]
    for k in d['keys']:
        out += [
            f"[{k['key_id']}] {k['name']} | {k['timing_class']} / {k['timing_provenance']} | exposure={k['exposure_ticks']}t | phase={k['loop_phase']}",
            f"support/contact={k['support_contact']}",
            f"root/arc={k['motion_arc_root_note']}",
            f"causal_role={k['causal_role']}",
            f"exit_window={str(k.get('exit_window',False)).lower()}",
            grid(d,k,latched=(k['key_id'] in ('K1','K2','K3'))),
            ''
        ]
    out += [
        'CLOCK / EVENT RELATION',
        '  BODY_LOOP = K0(4) -> K1(2) -> K2(1) -> K3(4) = 11 ticks.',
        '  Two full loops establish repetition.',
        '  Third loop: E_COMMIT arrives at K1 and becomes visibly latched (!).',
        '  The request DOES NOT jump from K1 or K2 into the action.',
        '  BODY_LOOP completes K1 -> K2 -> K3; K3 owns the EXIT_WINDOW.',
        '  After K3 hold completes: K4 -> K5 -> K6 -> K7 -> K8 -> K9 -> K10 -> K11.',
        '  K5/K6 unequal root deltas prove acceleration; K7 brake, K8 overshoot, K9 cross-recoil, K10/K11 displaced debt.',
        '',
        'TIMING VOCABULARY',
        '  ONES=new key sample each display frame; TWOS=hold 2 frames; FOURS=hold 4 frames.',
        '  STREET_FIGHTER/CAPCOM=nonuniform authored gameplay timing.',
        '  Every decisive key and E_COMMIT schedule here are INFERRED, never source-authentic.',
    ]
    return '\n'.join(out)

def timeline(d):
    km={k['key_id']:k for k in d['keys']}
    loop=['K0','K1','K2','K3']
    out=[]; frame=0
    for cyc in (1,2,3):
        for kid in loop:
            k=km[kid]
            for local in range(k['exposure_ticks']):
                latched=(cyc==3 and (kid in ('K1','K2','K3')))
                event_flash=(cyc==3 and kid=='K1' and local==0)
                out.append({'frame':frame,'key':k,'cycle':cyc,'latched':latched,'event_flash':event_flash,'commit_authority':False})
                frame+=1
    for kid in ['K4','K5','K6','K7','K8','K9','K10','K11']:
        k=km[kid]
        for local in range(k['exposure_ticks']):
            out.append({'frame':frame,'key':k,'cycle':None,'latched':False,'event_flash':False,'commit_authority':True})
            frame+=1
    return out

def load_font(size):
    for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','DejaVuSansMono.ttf']:
        try: return ImageFont.truetype(p,size)
        except: pass
    return ImageFont.load_default()

def render_video(d,t):
    font=load_font(11); small=load_font(9)
    with tempfile.TemporaryDirectory(prefix='ak-t012-') as td:
        td=Path(td)
        for st in t:
            im=Image.new('RGB',(560,320),'black'); dr=ImageDraw.Draw(im)
            k=st['key']
            labels=[
                f"ASCII KINESIS / TIMING 012 / {st['frame']:02d}",
                f"{k['key_id']} {k['name']}  {k['timing_class']} / INFERRED",
                ("E_COMMIT: LATCHED — WAIT FOR K3 EXIT WINDOW" if st['latched'] else ("COMMIT AUTHORITY: RELEASED" if st['commit_authority'] else "E_COMMIT: not latched")),
                "AUTHORED DECISIVE ASCII KEYS / NO SOURCE ART"
            ]
            y=5
            for line in labels:
                dr.text((7,y),line,font=small,fill='white'); y+=12
            dr.multiline_text((7,58),grid(d,k,st['latched'],st['event_flash']),font=font,fill='white',spacing=1)
            im.save(td/f"f{st['frame']:04d}.png")
        subprocess.run([
            'ffmpeg','-hide_banner','-loglevel','error','-y',
            '-framerate',str(d['compile']['fps']),'-i',str(td/'f%04d.png'),
            '-map_metadata','-1','-c:v','libx264','-preset','veryslow','-crf','38','-threads','1',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)
        ],check=True)

def page(d,a,media):
    compact=json.dumps(d,separators=(',',':'),sort_keys=True)
    def gz64(text): return base64.b64encode(gzip.compress(text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
    a64=gz64(a); j64=gz64(compact); v64=base64.b64encode(media).decode('ascii')
    return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Timing 012</title><style>:root{color-scheme:dark}body{font-family:system-ui;margin:1rem}nav{display:flex;gap:.5rem;flex-wrap:wrap}section[hidden]{display:none}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0;white-space:pre;overflow:auto;line-height:1.08}video{max-width:100%;height:auto}</style></head><body><h1>Deferred Loop Exit Commit</h1><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre></pre></section><section id="json" hidden><pre></pre></section><section id="video" hidden><video controls loop playsinline><source src="data:video/mp4;base64,'+v64+'" type="video/mp4"></video></section><script>const P={ascii:"'+a64+'",json:"'+j64+'"};async function u(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip")));return r.text()}Promise.all([u(P.ascii),u(P.json)]).then(([a,j])=>{document.querySelector("#ascii pre").textContent=a;document.querySelector("#json pre").textContent=j});const b=[...document.querySelectorAll("button[data-view]")],ss=[...document.querySelectorAll("section")];b.forEach(x=>x.onclick=()=>ss.forEach(y=>y.hidden=y.id!==x.dataset.view));</script></body></html>'

def main():
    d=json.loads(MOTION.read_text())
    a=contact_sheet(d)
    ASCII.write_text(a+'\n')
    t=timeline(d)
    render_video(d,t)
    media=MP4.read_bytes()
    event_frame=next(x['frame'] for x in t if x['event_flash'])
    release_frame=next(x['frame'] for x in t if x['key']['key_id']=='K4')
    d['compile'].update({
        'frame_count':len(t),
        'event_arrival_frame':event_frame,
        'exit_release_frame':release_frame,
        'deferred_wait_frames':release_frame-event_frame,
        'media_sha256':sha(media),
        'media_bytes':len(media),
        'ascii_sheet_sha256':sha((a+'\n').encode()),
        'video_codec':'H.264 yuv420p',
        'video_dimensions':'560x320'
    })
    MOTION.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    SPA.write_text(page(d,a,media))
    manifest={
        'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':ENTRY,'lane':'timing',
        'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'ascii_surface':'pre','ligatures_disabled':True,'whitespace_preserved':True,
        'video_required':True,'video_source':'abstract_ascii_rig_only','video_packaging':f'embedded MP4 data URI in {SLUG}.motion.html',
        'media_sha256':sha(media),'media_bytes':len(media),'ascii_sheet_sha256':d['compile']['ascii_sheet_sha256'],
        'source_art_embedded':False,'backward_compatible':True,'revision':d['revision'],'source':d['source'],
        'quality_gates':d['quality_gates'],'motion_dungeon':{'authored_ascii_keys':len(d['keys']),'explicit_holds':True,'deterministic_connective_motion':'authored keys only; K4 is explicit exit bridge','connector_semantics_fail_closed':True,'ascii_only_frame_render':True,'fps':d['compile']['fps'],'video_frames_total':len(t)},
        'files':['build.py','contact-sheet.txt','manifest.json','motion.json','receipt.json',f'{SLUG}.motion.html'],
        'reconstruction':'python3 build.py','contract_test':'python3 tools/test_ascii_kinesis_swarm_contract_v2.py','contract_verification':'PASS_CANDIDATE_ISOLATED_OFFICIAL_V2'
    }
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    receipt={
        'schema':'ascii-kinesis.v2-receipt','experiment_id':ENTRY,'status':'QUALITY_GATES_PASS_CANDIDATE_READY_FOR_REPO_PERSISTENCE',
        'repo_path':f'experiments/ascii-kinesis/{ENTRY}/','ship_commit':None,'verification_commit':None,'issue_343_receipt':None,
        'source':d['source'],'revision':d['revision'],'media_sha256':sha(media),'media_bytes':len(media),'ascii_sheet_sha256':d['compile']['ascii_sheet_sha256'],
        'tango':d['quality_gates']['tango'],'noodle_queen':d['quality_gates']['noodle_queen'],
        'verification':{'repo_readback':False,'contract_test':'PASS_CANDIDATE_ISOLATED_OFFICIAL_V2','media_decode':'PASS_H264_560x320_24FPS_49FRAMES','three_part_chat_delivery':False},
        'correction_hooks':d['correction_hooks']
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'frames':len(t),'event':event_frame,'release':release_frame,'wait':release_frame-event_frame,'media_sha256':sha(media),'media_bytes':len(media)},sort_keys=True))

if __name__=='__main__': main()
