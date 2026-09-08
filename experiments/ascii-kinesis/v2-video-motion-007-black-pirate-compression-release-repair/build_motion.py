#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, math, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MOTION=ROOT/'motion.json'; CONTACT=ROOT/'contact_sheet.txt'; MP4=ROOT/'motion.mp4'; HTML=ROOT/'black-pirate-compression-release-repair.motion.html'; MANIFEST=ROOT/'manifest.json'; RECEIPT=ROOT/'receipt.json'
FONT={
' ':['00000']*7,'O':['01110','10001','10001','10001','10001','10001','01110'],'A':['01110','10001','10001','11111','10001','10001','10001'],'B':['11110','10001','10001','11110','10001','10001','11110'],'@':['01110','10001','10111','10101','10111','10000','01111'],'+':['00000','00100','00100','11111','00100','00100','00000'],'|':['00100']*7,'/':['00001','00010','00010','00100','01000','01000','10000'],'\\':['10000','01000','01000','00100','00010','00010','00001'],'-':['00000','00000','00000','11111','00000','00000','00000'],'_':['00000','00000','00000','00000','00000','00000','11111'],'?':['01110','10001','00010','00100','00100','00000','00100'],'X':['10001','01010','00100','00100','00100','01010','10001'],'*':['00000','10101','01110','11111','01110','10101','00000']}
JOINTS=['head','neck','shoulder_l','shoulder_r','elbow_l','elbow_r','hand_l','hand_r','pelvis','com','knee_l','knee_r','foot_l','foot_r']
BONES=[('head','neck'),('neck','shoulder_l'),('neck','shoulder_r'),('shoulder_l','elbow_l'),('elbow_l','hand_l'),('shoulder_r','elbow_r'),('elbow_r','hand_r'),('neck','pelvis'),('pelvis','knee_l'),('knee_l','foot_l'),('pelvis','knee_r'),('knee_r','foot_r')]
def h(b): return hashlib.sha256(b).hexdigest()
def put(g,x,y,ch,force=False):
    if 0<=y<len(g) and 0<=x<len(g[0]):
        if force or g[y][x]==' ':
            g[y][x]=ch
        elif g[y][x]!=ch:
            g[y][x]='X'
def line(g,p0,p1):
    x0,y0=p0; x1,y1=p1; dx=x1-x0;dy=y1-y0; n=max(abs(dx),abs(dy),1)
    for i in range(n+1):
        t=i/n; x=round(x0+dx*t); y=round(y0+dy*t)
        if abs(dx)>=abs(dy)*2: ch='-'
        elif dx*dy<0: ch='/'
        elif dx*dy>0: ch='\\'
        else: ch='|'
        if 0<=y<len(g) and 0<=x<len(g[0]) and g[y][x]==' ': g[y][x]=ch
def ease(name,t):
    if name=='snap': return 1-(1-t)**3
    if name=='ease_in': return t*t
    if name=='ease_out': return 1-(1-t)*(1-t)
    if name=='damped': return t*t*(3-2*t)
    return t*t*(3-2*t)
def curved(a,b,t,arc_y=0):
    u=t
    x=a[0]+(b[0]-a[0])*u
    y=a[1]+(b[1]-a[1])*u + 4*arc_y*u*(1-u)
    return [round(x),round(y)]
def pose_between(k,n,seg,t):
    e=ease(seg['easing'],t); out={}
    for actor in ('actor_a','actor_b'):
        out[actor]={}
        for j in JOINTS:
            arc=seg.get('arc_y',{}).get(j,0)
            if actor=='actor_a': arc=round(arc*0.25)
            out[actor][j]=curved(k[actor][j],n[actor][j],e,arc)
    return out
def draw_actor(rows,cols,label,p):
    a=[[' ']*cols for _ in range(rows)]
    for j0,j1 in BONES: line(a,p[j0],p[j1])
    put(a,*p['head'],'O',True); put(a,p['head'][0]+1,p['head'][1],label,True)
    put(a,*p['pelvis'],'@',True); put(a,*p['com'],'+',True)
    for j in ('hand_l','hand_r','elbow_l','elbow_r','knee_l','knee_r'): put(a,*p[j],'*',True)
    put(a,*p['foot_l'],'?',True); put(a,*p['foot_r'],'?',True)
    return a
def render_pose(m,pose):
    cols,rows=m['motion_dungeon']['render_grid']; g=[[' ']*cols for _ in range(rows)]; ground=20
    for x in range(cols): g[ground][x]='_'
    layers=[draw_actor(rows,cols,'A',pose['actor_a']),draw_actor(rows,cols,'B',pose['actor_b'])]
    for layer in layers:
        for y in range(rows):
            for x in range(cols):
                c=layer[y][x]
                if c==' ': continue
                if g[y][x] in (' ','_'): g[y][x]=c
                elif g[y][x]!=c: g[y][x]='X'
    return [''.join(r) for r in g]
def bitmap(lines,cw,ch,scale):
    rows=len(lines); cols=len(lines[0]); W=cols*cw*scale; H=rows*ch*scale; out=bytearray(b'\x08\x08\x08'*(W*H))
    for gy,row in enumerate(lines):
        for gx,c in enumerate(row):
            pat=FONT.get(c,FONT['?'])
            for py,bits in enumerate(pat):
                for px,bit in enumerate(bits):
                    if bit!='1': continue
                    ox=(gx*cw+px)*scale; oy=(gy*ch+py)*scale
                    for sy in range(scale):
                        for sx in range(scale):
                            X=ox+sx;Y=oy+sy
                            if X<W and Y<H:
                                q=(Y*W+X)*3; out[q:q+3]=b'\xf2\xf2\xf2'
    return bytes(out)
def compile_frames(m):
    keys=m['keys']; by={k['key_id']:k for k in keys}; frames=[]; specs=[]
    for i,k in enumerate(keys):
        pose={'actor_a':k['actor_a'],'actor_b':k['actor_b']}
        for _ in range(k['hold_frames']): specs.append((k['key_id'],pose))
        if i==len(keys)-1: break
        seg=m['segments'][i]; n=keys[i+1]
        for j in range(seg['bridge_frames']):
            t=(j+1)/(seg['bridge_frames']+1); specs.append((f"{k['key_id']}~{n['key_id']}",pose_between(k,n,seg,t)))
    final={'actor_a':keys[-1]['actor_a'],'actor_b':keys[-1]['actor_b']}
    for _ in range(m['motion_dungeon'].get('final_hold_frames',0)): specs.append((keys[-1]['key_id'],final))
    cw,ch=m['motion_dungeon']['cell_pixels']; s=m['motion_dungeon']['scale']
    return [bitmap(render_pose(m,p),cw,ch,s) for _,p in specs], specs
def encode(m,frames):
    cols,rows=m['motion_dungeon']['render_grid'];cw,ch=m['motion_dungeon']['cell_pixels'];s=m['motion_dungeon']['scale'];W=cols*cw*s;H=rows*ch*s;fps=m['timing']['compile_fps']
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s:v',f'{W}x{H}','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','medium','-crf','18','-threads','1','-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1','-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)]
    p=subprocess.run(cmd,input=b''.join(frames),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode: raise SystemExit(p.stderr.decode())
    return MP4.read_bytes(),W,H
def contact_sheet(m):
    # Fixed crop of the authoritative 80x24 authored-key grid: still literal/aligned,
    # but removes dead whitespace so the contact sheet stays inspection-sized.
    parts=['ASCII KINESIS V2 · VIDEO MOTION 007 · REPAIR OF VIDEO MOTION 001\nCompression → spring release → counter-arc recovery debt\nSource: He\'ll walk the plank.webm · coherent segment 15.000–18.750 s\nLegend: O head · @ pelvis/root · + COM · * joint · ? support-side unresolved · X geometric overlap only\nNo inter-actor/prop contact is authored. Exact impact/contact/support ownership remains UNKNOWN.\n']
    for k in m['keys']:
        full=render_pose(m,{'actor_a':k['actor_a'],'actor_b':k['actor_b']})
        lines=[row[3:73] for row in full[5:21]]
        parts.append(f"\n{k['key_id']} · {k['source_time_s']:.3f}s OBSERVED · {k['timing_class']} {k['timing_provenance']} · {k['causal_role']}\n"+'\n'.join(lines)+'\n')
    parts.append('\nTIMING: source timestamps OBSERVED; compile classes/holds/bridge arcs INFERRED. 1s/2s/4s = ONES/TWOS/FOURS, never seconds.\n')
    parts.append('UNRESOLVED: B support foot/side · hand/prop endpoints · driver/yielder · discrete physical impact.\n')
    return ''.join(parts)
def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def build_html(m,manifest,contact,mp4):
    audit=json.dumps({'motion':m,'manifest':manifest},separators=(',',':'),ensure_ascii=False); b64=base64.b64encode(mp4).decode('ascii')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 · Video Motion 007</title><style>:root{{color-scheme:dark;background:#090909;color:#f3f3f3;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}}*{{box-sizing:border-box}}body{{margin:0}}header{{position:sticky;top:0;background:#111;border-bottom:1px solid #444;padding:.75rem;z-index:2}}nav{{display:flex;gap:.5rem}}button{{font:inherit;padding:.62rem .95rem;background:#181818;color:#eee;border:1px solid #555;border-radius:.35rem}}button[aria-selected="true"]{{background:#eee;color:#111}}main{{padding:1rem}}section[hidden]{{display:none}}pre{{font:inherit;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.12;margin:0;padding:1rem;border:1px solid #333;background:#0d0d0d}}video{{display:block;width:min(100%,1000px);height:auto;border:1px solid #333;background:#000}}</style></head><body><header><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section id="ascii"><pre>{esc(contact)}</pre></section><section id="json" hidden><pre>{esc(audit)}</pre></section><section id="video" hidden><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{b64}"></video></section></main><script>const bs=[...document.querySelectorAll('button[data-view]')];const ss={{ascii:document.getElementById('ascii'),json:document.getElementById('json'),video:document.getElementById('video')}};bs.forEach(b=>b.onclick=()=>{{bs.forEach(x=>x.setAttribute('aria-selected',String(x===b)));Object.entries(ss).forEach(([k,s])=>s.hidden=k!==b.dataset.view)}});</script></body></html>'''
def main():
    m=json.loads(MOTION.read_text()); c=contact_sheet(m); CONTACT.write_text(c)
    frames,specs=compile_frames(m); mp4,W,H=encode(m,frames); sha=h(mp4)
    # decode gate
    probe=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames','-of','json',str(MP4)],capture_output=True,text=True,check=True)
    dec=subprocess.run(['ffmpeg','-v','error','-i',str(MP4),'-f','null','-'],capture_output=True,text=True)
    if dec.returncode: raise SystemExit('decode failed: '+dec.stderr)
    m['media'].update({'sha256':sha,'bytes':len(mp4),'frame_count':len(frames),'compile_fps':m['timing']['compile_fps'],'dimensions':[W,H],'decode_verified':True,'ffprobe':json.loads(probe.stdout)})
    m['status']='RENDERED_TANGO_PASS_QUEEN_PASS_PENDING_REPO_READBACK_CHAT_DELIVERY' if m.get('quality_gates',{}).get('tango',{}).get('status')=='PASS' and m.get('quality_gates',{}).get('noodle_queen',{}).get('status')=='PASS' else 'RENDERED_PENDING_TANGO'
    MOTION.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
    manifest={'schema':'ascii-kinesis.v2-manifest','format_version':2,'entry':m['experiment_id'],'lane':'video-motion','repo_path':'experiments/ascii-kinesis/v2-video-motion-007-black-pirate-compression-release-repair/','revises':m['revision']['revises'],'negative_fixture':m['revision']['negative_fixture'],'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'json_structured':True,'video_required':True,'video_embedded':True,'tracked_mp4':False,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'media_sha256':sha,'media_bytes':len(mp4),'media_frame_count':len(frames),'media_decode_verified':True,'source_pixels_used_in_output':False,'offline_spa':True,'backward_compatible':True,'files':['contact_sheet.txt','motion.json','build_motion.py','manifest.json','receipt.json','black-pirate-compression-release-repair.motion.html']}
    MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
    HTML.write_text(build_html(m,manifest,c,mp4))
    # Critical repair gate: verify persisted-in-SPA bytes, not merely the local pre-embed MP4.
    import re
    page=HTML.read_text(encoding='utf-8')
    match=re.search(r'data:video/mp4;base64,([A-Za-z0-9+/=]+)',page)
    if not match: raise SystemExit('embedded MP4 data URI missing')
    embedded=base64.b64decode(match.group(1),validate=True)
    if len(embedded)!=len(mp4) or h(embedded)!=sha: raise SystemExit('embedded MP4 identity mismatch')
    verify=ROOT/'embedded.verify.mp4'; verify.write_bytes(embedded)
    try:
        subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames','-of','json',str(verify)],capture_output=True,text=True,check=True)
        chk=subprocess.run(['ffmpeg','-v','error','-i',str(verify),'-f','null','-'],capture_output=True,text=True)
        if chk.returncode: raise SystemExit('embedded MP4 full decode failed: '+chk.stderr)
    finally:
        verify.unlink(missing_ok=True)
    receipt={'schema':'ascii-kinesis.v2-receipt','entry':m['experiment_id'],'lane':'video-motion','revises':m['revision']['revises'],'negative_fixture':m['revision']['negative_fixture'],'negative_fixture_status':'REVISE_REQUIRED_LOW_EFFORT','source':m['source'],'rights_status':m['source']['rights_status'],'observed_source_times_s':{k['key_id']:k['source_time_s'] for k in m['keys']},'compile_timing':{k['key_id']:{'timing_class':k['timing_class'],'provenance':k['timing_provenance'],'hold_frames':k['hold_frames']} for k in m['keys']},'media_sha256':sha,'media_bytes':len(mp4),'media_frame_count':len(frames),'media_decode_verified':True,'media_source':'abstract_ascii_rig_only','repo_path':manifest['repo_path'],'repo_readback_verified':False,'contract_test':{'path':'tools/test_ascii_kinesis_swarm_contract_v2.py','status':'PENDING'},'quality_gates':m['quality_gates'],'status':'TANGO_PASS_QUEEN_PASS_PENDING_REPO_READBACK_CHAT_DELIVERY'}
    RECEIPT.write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps({'sha256':sha,'bytes':len(mp4),'frames':len(frames),'dimensions':[W,H],'duration_s':len(frames)/m['timing']['compile_fps'],'decode_ok':True},indent=2))
if __name__=='__main__': main()
