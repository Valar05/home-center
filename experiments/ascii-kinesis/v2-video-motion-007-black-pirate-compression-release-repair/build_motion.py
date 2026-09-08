#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, re, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parent
MOTION=ROOT/'motion.json'; CONTACT=ROOT/'contact_sheet.txt'; MP4=ROOT/'motion.mp4'; HTML=ROOT/'black-pirate-compression-release-repair.motion.html'; MANIFEST=ROOT/'manifest.json'; RECEIPT=ROOT/'receipt.json'
FONT={
' ':['00000']*7,
'O':['01110','10001','10001','10001','10001','10001','01110'],
'A':['01110','10001','10001','11111','10001','10001','10001'],
'B':['11110','10001','10001','11110','10001','10001','11110'],
'@':['01110','10001','10111','10101','10111','10000','01111'],
'+':['00000','00100','00100','11111','00100','00100','00000'],
'|':['00100']*7,
'/':['00001','00010','00010','00100','01000','01000','10000'],
'\\':['10000','01000','01000','00100','00010','00010','00001'],
'-':['00000','00000','00000','11111','00000','00000','00000'],
'_':['00000','00000','00000','00000','00000','00000','11111'],
'?':['01110','10001','00010','00100','00100','00000','00100'],
'X':['10001','01010','00100','00100','00100','01010','10001'],
'*':['00000','10101','01110','11111','01110','10101','00000']}
JOINTS=['head','neck','shoulder_l','shoulder_r','elbow_l','elbow_r','hand_l','hand_r','pelvis','com','knee_l','knee_r','foot_l','foot_r']
BONES=[('head','neck'),('neck','shoulder_l'),('neck','shoulder_r'),('shoulder_l','elbow_l'),('elbow_l','hand_l'),('shoulder_r','elbow_r'),('elbow_r','hand_r'),('neck','pelvis'),('pelvis','knee_l'),('knee_l','foot_l'),('pelvis','knee_r'),('knee_r','foot_r')]
def sha(b): return hashlib.sha256(b).hexdigest()
def line(layer,p0,p1):
    x0,y0=p0; x1,y1=p1; dx=x1-x0;dy=y1-y0;n=max(abs(dx),abs(dy),1)
    for i in range(n+1):
        t=i/n;x=round(x0+dx*t);y=round(y0+dy*t)
        if abs(dx)>=abs(dy)*2: ch='-'
        elif dx*dy<0: ch='/'
        elif dx*dy>0: ch='\\'
        else: ch='|'
        if 0<=y<len(layer) and 0<=x<len(layer[0]) and layer[y][x]==' ': layer[y][x]=ch
def put(layer,p,ch):
    x,y=p
    if 0<=y<len(layer) and 0<=x<len(layer[0]): layer[y][x]=ch
def actor_layer(rows,cols,label,p):
    g=[[' ']*cols for _ in range(rows)]
    for a,b in BONES: line(g,p[a],p[b])
    put(g,p['head'],'O')
    if p['head'][0]+1<cols: put(g,[p['head'][0]+1,p['head'][1]],label)
    put(g,p['pelvis'],'@');put(g,p['com'],'+')
    for j in ('hand_l','hand_r','elbow_l','elbow_r','knee_l','knee_r'): put(g,p[j],'*')
    put(g,p['foot_l'],'?');put(g,p['foot_r'],'?')
    return g
def render_pose(m,pose):
    cols,rows=m['motion_dungeon']['render_grid']; g=[[' ']*cols for _ in range(rows)]; ground=20
    for x in range(cols): g[ground][x]='_'
    for layer in (actor_layer(rows,cols,'A',pose['actor_a']),actor_layer(rows,cols,'B',pose['actor_b'])):
        for y in range(rows):
            for x in range(cols):
                c=layer[y][x]
                if c==' ': continue
                if g[y][x] in (' ','_'): g[y][x]=c
                elif g[y][x]!=c: g[y][x]='X'
    return [''.join(r) for r in g]
def smooth(t): return t*t*(3-2*t)
def snap(t): return 1-(1-t)**3
def damp(t): return 1-(1-t)**2*(1+1.6*t)
def ease(name,t): return snap(t) if name=='snap' else damp(t) if name=='damped' else smooth(t)
def interp_point(a,b,t,arc=0):
    x=a[0]+(b[0]-a[0])*t
    y=a[1]+(b[1]-a[1])*t + 4*arc*t*(1-t)
    return [round(x),round(y)]
def between(k,n,seg,t):
    u=ease(seg['easing'],t); out={}
    for actor in ('actor_a','actor_b'):
        out[actor]={}
        for j in JOINTS:
            arc=seg.get('arc_y',{}).get(actor,{}).get(j,0)
            out[actor][j]=interp_point(k[actor][j],n[actor][j],u,arc)
    return out
def compile_specs(m):
    keys=m['keys']; specs=[]
    for i,k in enumerate(keys):
        pose={'actor_a':k['actor_a'],'actor_b':k['actor_b']}
        for _ in range(k['hold_frames']): specs.append((k['key_id'],pose))
        if i==len(keys)-1: break
        n=keys[i+1]; seg=m['segments'][i]
        for j in range(seg['bridge_frames']):
            t=(j+1)/(seg['bridge_frames']+1)
            specs.append((f"{k['key_id']}~{n['key_id']}",between(k,n,seg,t)))
    for _ in range(m['motion_dungeon']['final_hold_frames']):
        specs.append((keys[-1]['key_id'],{'actor_a':keys[-1]['actor_a'],'actor_b':keys[-1]['actor_b']}))
    return specs
def bitmap(lines,scale=2):
    cw,ch=6,8; rows=len(lines);cols=len(lines[0]);W=cols*cw*scale;H=rows*ch*scale
    out=bytearray(b'\x08\x08\x08'*(W*H))
    for gy,row in enumerate(lines):
        for gx,c in enumerate(row):
            pat=FONT.get(c,FONT['?'])
            for py,bits in enumerate(pat):
                for px,bit in enumerate(bits):
                    if bit!='1': continue
                    ox=(gx*cw+px)*scale; oy=(gy*ch+py)*scale
                    for sy in range(scale):
                        for sx in range(scale):
                            X=ox+sx;Y=oy+sy;q=(Y*W+X)*3
                            out[q:q+3]=b'\xf2\xf2\xf2'
    return bytes(out),W,H
def encode(m,specs):
    frames=[];W=H=None
    for _,p in specs:
        b,W,H=bitmap(render_pose(m,p),m['motion_dungeon']['scale']);frames.append(b)
    fps=m['timing']['compile_fps']
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s:v',f'{W}x{H}','-r',str(fps),'-i','-','-an','-c:v','libx264','-preset','veryslow','-crf','28','-threads','1','-pix_fmt','yuv420p','-movflags','+faststart','-map_metadata','-1','-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)]
    p=subprocess.run(cmd,input=b''.join(frames),capture_output=True)
    if p.returncode: raise SystemExit(p.stderr.decode())
    return MP4.read_bytes(),W,H
def contact_sheet(m):
    parts=["ASCII KINESIS V2 · VIDEO MOTION 007 · BLACK PIRATE COMPRESSION / RELEASE REPAIR\n",
           "Source evidence family: He'll walk the plank.webm · coherent action 15.000–18.750 s\n",
           "Legend: O head · @ pelvis/root · + COM · * joint · ? ground contact, support side UNKNOWN · X silhouette overlap only\n",
           "No inter-actor / prop contact is asserted. Source timestamps are OBSERVED; compile cadence/arcs are INFERRED.\n"]
    for k in m['keys']:
        pose={'actor_a':k['actor_a'],'actor_b':k['actor_b']}
        full=render_pose(m,pose)
        crop=[r[4:74] for r in full[4:21]]
        parts += [f"\n{k['key_id']}  t={k['source_time_s']:.3f}s OBSERVED  {k['timing_class']} {k['timing_provenance']}  {k['causal_role']}\n", '\n'.join(crop)+'\n',
                  f"support/contact: {k['support_contact']}\nroot/arc: {k['motion_arc_root_note']}\n"]
    parts += ["\nTIMING LAW: 1s/2s/4s = ONES/TWOS/FOURS, never seconds.\n",
              "UNRESOLVED: exact B support foot/side; exact hand/prop endpoints; driver/yielder; discrete physical impact.\n"]
    return ''.join(parts)
def html_escape(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def build_html(m,manifest,contact,mp4):
    audit=json.dumps({'motion':m,'manifest':manifest},ensure_ascii=False,indent=2)
    b64=base64.b64encode(mp4).decode('ascii')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 · Video Motion 007 Repair</title><style>:root{{color-scheme:dark;background:#090909;color:#f3f3f3;font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace}}*{{box-sizing:border-box}}body{{margin:0}}header{{position:sticky;top:0;background:#111;border-bottom:1px solid #444;padding:.75rem;z-index:2}}nav{{display:flex;gap:.5rem}}button{{font:inherit;padding:.62rem .95rem;background:#181818;color:#eee;border:1px solid #555;border-radius:.35rem}}button[aria-selected="true"]{{background:#eee;color:#111}}main{{padding:1rem}}section[hidden]{{display:none}}pre{{font:inherit;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.12;margin:0;padding:1rem;border:1px solid #333;background:#0d0d0d}}video{{display:block;width:min(100%,1000px);height:auto;border:1px solid #333;background:#000}}</style></head><body><header><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section id="ascii"><pre>{html_escape(contact)}</pre></section><section id="json" hidden><pre>{html_escape(audit)}</pre></section><section id="video" hidden><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{b64}"></video></section></main><script>const bs=[...document.querySelectorAll('button[data-view]')],ss={{ascii:document.getElementById('ascii'),json:document.getElementById('json'),video:document.getElementById('video')}};bs.forEach(b=>b.onclick=()=>{{bs.forEach(x=>x.setAttribute('aria-selected',String(x===b)));Object.entries(ss).forEach(([k,s])=>s.hidden=k!==b.dataset.view)}});</script></body></html>'''
def main():
    m=json.loads(MOTION.read_text())
    c=contact_sheet(m); CONTACT.write_text(c)
    specs=compile_specs(m); mp4,W,H=encode(m,specs); media_sha=sha(mp4)
    probe=subprocess.run(['ffprobe','-v','error','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames','-of','json',str(MP4)],capture_output=True,text=True,check=True)
    dec=subprocess.run(['ffmpeg','-v','error','-i',str(MP4),'-f','null','-'],capture_output=True,text=True)
    if dec.returncode: raise SystemExit('decode failed '+dec.stderr)
    m['media']={'sha256':media_sha,'bytes':len(mp4),'frame_count':len(specs),'compile_fps':m['timing']['compile_fps'],'dimensions':[W,H],'decode_verified':True,'ffprobe':json.loads(probe.stdout),'source':'abstract_ascii_rig_only'}
    m['status']='TANGO_PASS_QUEEN_PASS_MEDIA_DECODED_PENDING_REPO_READBACK_CHAT_DELIVERY' if m.get('quality_gates',{}).get('tango',{}).get('status')=='PASS' and m.get('quality_gates',{}).get('noodle_queen',{}).get('status')=='PASS' else 'RENDERED_TANGO_REVIEW_REQUIRED'
    MOTION.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
    manifest={'schema':'ascii-kinesis.v2-manifest','format_version':2,'entry':m['experiment_id'],'lane':'video-motion','repo_path':'experiments/ascii-kinesis/v2-video-motion-007-black-pirate-compression-release-repair/','revises':m['revision']['revises'],'negative_fixture':m['revision']['negative_fixture'],'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'json_structured':True,'video_required':True,'video_embedded':True,'tracked_mp4':False,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'source_pixels_used_in_output':False,'media_sha256':media_sha,'media_bytes':len(mp4),'media_frame_count':len(specs),'media_decode_verified':True,'offline_spa':True,'backward_compatible':True,'files':['contact_sheet.txt','motion.json','build_motion.py','manifest.json','receipt.json','black-pirate-compression-release-repair.motion.html']}
    MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n')
    page=build_html(m,manifest,c,mp4); HTML.write_text(page)
    mm=re.search(r'data:video/mp4;base64,([A-Za-z0-9+/=]+)',page); assert mm
    embedded=base64.b64decode(mm.group(1),validate=True)
    assert sha(embedded)==media_sha and len(embedded)==len(mp4)
    temp=ROOT/'embedded.verify.mp4';temp.write_bytes(embedded)
    subprocess.run(['ffprobe','-v','error',str(temp)],check=True)
    chk=subprocess.run(['ffmpeg','-v','error','-i',str(temp),'-f','null','-'],capture_output=True,text=True)
    temp.unlink()
    if chk.returncode: raise SystemExit('embedded decode failed '+chk.stderr)
    rec={'schema':'ascii-kinesis.v2-receipt','entry':m['experiment_id'],'lane':'video-motion','revises':m['revision']['revises'],'negative_fixture':m['revision']['negative_fixture'],'negative_fixture_status':'REVISE_REQUIRED_LOW_EFFORT','source':m['source'],'rights_status':m['source']['rights_status'],'observed_source_times_s':{k['key_id']:k['source_time_s'] for k in m['keys']},'compile_timing':{k['key_id']:{'timing_class':k['timing_class'],'provenance':k['timing_provenance'],'hold_frames':k['hold_frames']} for k in m['keys']},'media_sha256':media_sha,'media_bytes':len(mp4),'media_frame_count':len(specs),'media_decode_verified':True,'embedded_media_identity_verified':True,'media_source':'abstract_ascii_rig_only','repo_path':'experiments/ascii-kinesis/v2-video-motion-007-black-pirate-compression-release-repair/','repo_readback_verified':False,'contract_test':{'path':'tools/test_ascii_kinesis_swarm_contract_v2.py','status':'PENDING_OR_SUCCESSOR_SCOPE_ONLY','boundary':'Full repository checkout unavailable in Standard Chat; successor can be checked against fetched test logic but full-repo-wide execution must not be claimed.'},'quality_gates':m.get('quality_gates',{'tango':{'status':'PENDING_ACTUAL_RENDER_REVIEW','iterations':[]},'noodle_queen':{'status':'BLOCKED_UNTIL_TANGO_PASS'}}),'status':m['status']}
    RECEIPT.write_text(json.dumps(rec,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'sha256':media_sha,'bytes':len(mp4),'frames':len(specs),'dims':[W,H],'probe':json.loads(probe.stdout)},indent=2))
if __name__=='__main__': main()
