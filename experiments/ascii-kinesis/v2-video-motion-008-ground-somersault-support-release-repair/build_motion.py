#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, math, subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent
MOTION=ROOT/'motion.json'; CONTACT=ROOT/'contact_sheet.txt'; MP4=ROOT/'motion.mp4'
HTML=ROOT/'ground-somersault-support-release-repair.motion.html'; MANIFEST=ROOT/'manifest.json'; RECEIPT=ROOT/'receipt.json'

FONT={
' ':['00000']*7,
'O':['01110','10001','10001','10001','10001','10001','01110'],
'@':['01110','10001','10111','10101','10111','10000','01111'],
'o':['00000','00000','01110','01010','01110','00000','00000'],
'|':['00100']*7,
'/':['00001','00010','00010','00100','01000','01000','10000'],
'\\':['10000','01000','01000','00100','00010','00010','00001'],
'-':['00000','00000','00000','11111','00000','00000','00000'],
'_':['00000','00000','00000','00000','00000','00000','11111'],
'?':['01110','10001','00010','00100','00100','00000','00100'],
'^':['00100','01010','10001','00000','00000','00000','00000'],
'X':['10001','01010','00100','00100','00100','01010','10001'],
'+':['00100','00100','11111','00100','00100','00000','00000'],
}

def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def put(g,x,y,ch):
    if not (0<=y<len(g) and 0<=x<len(g[0])): return
    old=g[y][x]
    if old==' ' or old==ch: g[y][x]=ch
    elif ch=='_':
        if old==' ': g[y][x]='_'
    elif old=='_': g[y][x]=ch
    else: g[y][x]='X'

def line(g,a,b):
    x0,y0=a; x1,y1=b; dx=x1-x0; dy=y1-y0; n=max(abs(dx),abs(dy),1)
    for i in range(n+1):
        t=i/n; x=round(x0+dx*t); y=round(y0+dy*t)
        if abs(dx)>=abs(dy)*2: ch='-'
        elif dx==0: ch='|'
        elif dx*dy<0: ch='/'
        else: ch='\\'
        put(g,x,y,ch)

def bezier(p0,p3,t,arc):
    ax,ay=arc
    p1=(p0[0]+(p3[0]-p0[0])/3+ax, p0[1]+(p3[1]-p0[1])/3+ay)
    p2=(p0[0]+2*(p3[0]-p0[0])/3+ax, p0[1]+2*(p3[1]-p0[1])/3+ay)
    u=1-t
    x=u**3*p0[0]+3*u*u*t*p1[0]+3*u*t*t*p2[0]+t**3*p3[0]
    y=u**3*p0[1]+3*u*u*t*p1[1]+3*u*t*t*p2[1]+t**3*p3[1]
    return round(x),round(y)

def geom(key,nxt=None,t=0.0):
    if nxt is None: return {k:tuple(v) for k,v in key['joints'].items()}
    arcs=key.get('arc_to_next',{})
    return {name:bezier(key['joints'][name],nxt['joints'][name],t,arcs.get(name,[0,0])) for name in key['joints']}

def render(m,key,nxt=None,t=0.0):
    cols,rows=m['motion_dungeon']['render_grid']; gy=m['motion_dungeon']['ground_y']
    g=[[' ']*cols for _ in range(rows)]
    for x in range(cols): put(g,x,gy,'_')
    p=geom(key,nxt,t)
    # body graph, deliberately articulated
    for a,b in [('head','neck'),('neck','root'),('shoulder_l','shoulder_r'),('neck','shoulder_l'),('neck','shoulder_r'),
                ('shoulder_l','elbow_l'),('elbow_l','hand_l'),('shoulder_r','elbow_r'),('elbow_r','hand_r'),
                ('root','knee_l'),('knee_l','foot_l'),('root','knee_r'),('knee_r','foot_r')]: line(g,p[a],p[b])
    for name in ('neck','shoulder_l','shoulder_r','elbow_l','elbow_r','knee_l','knee_r'): put(g,*p[name],'o')
    put(g,*p['head'],'O'); put(g,*p['root'],'@')
    support=key.get('support_state','')
    if support.startswith('GROUND_'):
        for foot in ('foot_l','foot_r'):
            x,y=p[foot]
            if y>=gy-1 and gy+1<rows: put(g,x,gy+1,'^')
    elif support=='SUPPORT_TRANSITION_UNRESOLVED':
        rx,_=p['root']
        if gy+1<rows: put(g,rx,gy+1,'?')
    return [''.join(r) for r in g]

def contact_sheet(m):
    out=[
      'ASCII KINESIS V2 · VIDEO MOTION 008 · GROUND SOMERSAULT REPAIR',
      'REVISES: experiments/ascii-kinesis/v2-video-motion-002-ground-somersault-support-release/',
      'Source family: Ground flip (1080p 120fps - take 02).webm · PoseidonSports · CC BY-SA 4.0',
      'Evidence: source presentation timestamps are OBSERVED anchors; slow-motion transport is NOT athletic cadence.',
      'Output: independent abstract ASCII rig only; no source frames/pixels/audio.',
      'Legend: O head · @ root/pelvis · o articulated joint · ^ visible ground contact · ? unresolved causal gate · _ ground',
      ''
    ]
    for k in m['keys']:
        st='—' if k['source_time_s'] is None else f"{k['source_time_s']:.3f}s OBSERVED presentation"
        out.append(f"{k['key_id']} · {k['causal_role']} · source {st} · compile {k['timing_class']} / {k['timing_provenance']}")
        out.extend(render(m,k))
        out.append('support: '+k['support_state'])
        out.append('load: '+(k.get('support_load_note') or '—'))
        out.append('contact: '+k['contact_note'])
        out.append('root/arc: '+k['root_arc_note'])
        out.append('')
    out += [
      'CAUSAL / TIMING FIREWALL',
      'toe-off: OBSERVED bracket 2.500–3.000 s presentation; K5 is fail-closed, K6 is first clearly AIRBORNE anchor.',
      'landing: OBSERVED bracket 3.500–3.750 s presentation; K10 is fail-closed, K11 is first recorded ground-reacquired anchor.',
      'compile cadence: entirely INFERRED ONES/TWOS/FOURS/STREET_FIGHTER-CAPCOM; 1s/2s/4s are classes, not seconds.',
      'recovery: K12–K14 are authored animation-performance inference, not claims about unmeasured source athletic timing.'
    ]
    return '\n'.join(out)+'\n'

def bitmap(lines,cw,ch,scale):
    rows=len(lines); cols=len(lines[0]); w=cols*cw*scale; h=rows*ch*scale
    bg=8; fg=242; out=bytearray([bg])*(w*h*3)
    for gy,row in enumerate(lines):
        for gx,c in enumerate(row):
            pat=FONT.get(c)
            if not pat: continue
            for py,bits in enumerate(pat):
                for px,bit in enumerate(bits):
                    if bit!='1': continue
                    ox=(gx*cw+px)*scale; oy=(gy*ch+py)*scale
                    for sy in range(scale):
                        for sx in range(scale):
                            x=ox+sx; y=oy+sy
                            if x>=w or y>=h: continue
                            pos=(y*w+x)*3; out[pos:pos+3]=bytes((fg,fg,fg))
    return bytes(out)

def frame_specs(m):
    keys=m['keys']; specs=[]
    for i,k in enumerate(keys):
        specs += [(k,None,0.0)]*int(k['compile_hold_frames'])
        if i==len(keys)-1: continue
        n=keys[i+1]; travel=int(k.get('compile_travel_frames_to_next',0))
        if k.get('causal_boundary_to_next'): travel=0
        for j in range(1,travel+1): specs.append((k,n,j/(travel+1)))
    return specs

def compile_mp4(m):
    specs=frame_specs(m); cw,ch=m['motion_dungeon']['cell_pixels']; scale=m['motion_dungeon']['scale']; cols,rows=m['motion_dungeon']['render_grid']
    w=cols*cw*scale; h=rows*ch*scale; raw=b''.join(bitmap(render(m,k,n,t),cw,ch,scale) for k,n,t in specs)
    fps=m['timing']['compile_fps']
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s:v',f'{w}x{h}','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','medium','-crf','18','-threads','1','-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1','-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)]
    p=subprocess.run(cmd,input=raw,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode: raise SystemExit(p.stderr.decode())
    return MP4.read_bytes(),len(specs),w,h,subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0]

def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def html(m,manifest,receipt,contact,mp4):
    audit=json.dumps({'motion':m,'manifest':manifest,'receipt':receipt},separators=(',',':'),ensure_ascii=False)
    vb64=base64.b64encode(mp4).decode('ascii')
    cgz=base64.b64encode(gzip.compress(contact.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
    jgz=base64.b64encode(gzip.compress(audit.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 - Video Motion 008</title><style>:root{{color-scheme:dark;background:#080808;color:#f2f2f2;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}}*{{box-sizing:border-box}}body{{margin:0}}header{{position:sticky;top:0;background:#101010;border-bottom:1px solid #444;padding:.75rem;z-index:2}}nav{{display:flex;gap:.5rem}}button{{font:inherit;padding:.6rem .9rem;background:#1b1b1b;color:#eee;border:1px solid #555;border-radius:.35rem}}button[aria-selected="true"]{{background:#eee;color:#111}}main{{padding:1rem}}section[hidden]{{display:none}}pre{{font:inherit;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05;margin:0;padding:1rem;border:1px solid #333;background:#0c0c0c}}video{{width:min(100%,1000px);height:auto;background:#000;border:1px solid #333}}.note{{max-width:80rem;line-height:1.5}}</style></head><body><header><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section id="ascii"><p class="note">Literal selectable/copyable aligned contact sheet. No source pixels.</p><pre id="sheet"></pre></section><section id="json" hidden><p class="note">Structured rig/timing/provenance/rights/revision/manifest payload.</p><pre id="audit"></pre></section><section id="video" hidden><p class="note">Motion Dungeon MP4 generated solely from abstract ASCII rig + authored timing.</p><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{vb64}"></video></section></main><script>const bs=[...document.querySelectorAll('nav button')],ss={{ascii:document.getElementById('ascii'),json:document.getElementById('json'),video:document.getElementById('video')}};for(const b of bs)b.onclick=()=>{{for(const x of bs)x.setAttribute('aria-selected',String(x===b));for(const [n,s] of Object.entries(ss))s.hidden=n!==b.dataset.view;}};async function gz(b64){{const u=Uint8Array.from(atob(b64),c=>c.charCodeAt(0));const st=new Blob([u]).stream().pipeThrough(new DecompressionStream('gzip'));return await new Response(st).text()}};(async()=>{{document.getElementById('sheet').textContent=await gz('{cgz}');document.getElementById('audit').textContent=await gz('{jgz}')}})();</script></body></html>'''

def main():
    m=json.loads(MOTION.read_text())
    contact=contact_sheet(m); CONTACT.write_text(contact)
    mp4,n,w,h,ff=compile_mp4(m); media_hash=sha(mp4)
    m['media'].update({'sha256':media_hash,'bytes':len(mp4),'frame_count':n,'compile_fps':m['timing']['compile_fps'],'ffmpeg_version':ff,'render_dimensions':[w,h]})
    m['status']='READY_FOR_REPO_PERSISTENCE' if (m.get('quality_gates',{}).get('tango',{}).get('status')=='PASS' and m.get('quality_gates',{}).get('noodle_queen',{}).get('status')=='PASS' and m.get('verification',{}).get('media_decode',{}).get('status')=='PASS' and m.get('verification',{}).get('contract_regression',{}).get('status')=='PASS') else 'RENDERED_PENDING_QUALITY_AND_REPO_READBACK'; MOTION.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
    manifest={'schema':'ascii-kinesis.v2-manifest','format_version':2,'entry':m['experiment_id'],'lane':'video-motion','primary_tabs':['ASCII','JSON','VIDEO'],
      'revision':m['revision'],'ascii_literal_text':True,'video_required':True,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'source_audio_embedded':False,
      'backward_compatible':True,'offline_spa':True,'source':{'title':m['source']['title'],'url':m['source']['page_url'],'author':m['source']['author'],'license_id':m['source']['license_id'],'rights_status':m['source']['rights_status'],'source_sha256':m['source']['source_sha256'],'selected_action_segment_s':m['source']['selected_action_segment_s'],'presentation_cadence_note':m['source']['presentation_cadence_note']},
      'media':{'mime':'video/mp4','sha256':media_hash,'bytes':len(mp4),'frame_count':n,'compile_fps':m['timing']['compile_fps'],'embedded_in_spa':True,'tracked_mp4':'motion.mp4','embedded_matches_tracked_mp4':True,'source_pixels_used':False,'source_audio_used':False,'render_dimensions':[w,h]},
      'builder':{'path':'build_motion.py','method':'Motion Dungeon','input':'motion.json only','source_video_dependency':False,'connective_motion':'authored cubic Bezier controls between authored keys; causal boundaries cut discretely','ffmpeg_version':ff},
      'files':['contact_sheet.txt','motion.json','motion.mp4','build_motion.py','manifest.json','receipt.json','ground-somersault-support-release-repair.motion.html'],
      'compatibility':m['compatibility'],'quality_gates':m['quality_gates'],'verification':m.get('verification',{}),'correction_hooks':m['correction_hooks'],'status':m['status']}
    receipt={'schema':'ascii-kinesis.v2-receipt','entry':m['experiment_id'],'revision':m['revision'],'source':m['source'],'rights_status':m['source']['rights_status'],
      'observed_key_times_s':{k['key_id']:k['source_time_s'] for k in m['keys'] if k['source_time_s'] is not None},
      'inferred_bridge_keys':[k['key_id'] for k in m['keys'] if k['source_time_s'] is None],
      'compile_timing_classes':{k['key_id']:k['timing_class'] for k in m['keys']},'timing_provenance':{k['key_id']:k['timing_provenance'] for k in m['keys']},
      'media_sha256':media_hash,'media_bytes':len(mp4),'media_frame_count':n,'media_source':'abstract_ascii_rig_only','repo_path':f"experiments/ascii-kinesis/{m['experiment_id']}/",
      'repo_readback_verified':False,'contract_test':m.get('verification',{}).get('contract_regression',{'status':'PENDING'}),'media_decode':m.get('verification',{}).get('media_decode',{'status':'PENDING'}),'embedded_tracked_identity':m.get('verification',{}).get('embedded_tracked_identity',{'status':'PENDING'}),'quality_gates':m['quality_gates'],'chat_delivery':'PENDING','status':m['status'],'correction_hooks':m['correction_hooks']}
    MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n'); RECEIPT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
    HTML.write_text(html(m,manifest,receipt,contact,mp4),encoding='utf-8')
    print(json.dumps({'entry':m['experiment_id'],'frames':n,'mp4_bytes':len(mp4),'mp4_sha256':media_hash,'render':[w,h],'html_bytes':HTML.stat().st_size,'ffmpeg':ff},sort_keys=True))
if __name__=='__main__': main()
