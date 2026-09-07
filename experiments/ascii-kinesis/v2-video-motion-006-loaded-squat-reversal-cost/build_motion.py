#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
MOTION=ROOT/'motion.json'
W,H=48,18
SCALE=4
FPS=24
OUT_W,OUT_H=768,432

def bres(a,b):
    x0,y0=a; x1,y1=b; pts=[]; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return pts

def segment(grid,a,b,ch):
    for x,y in bres(tuple(a),tuple(b)):
        if 0<=x<W and 0<=y<H and grid[y][x]==' ': grid[y][x]=ch

def pose_ascii(key,label=True):
    j=key['joints']; g=[[' ']*W for _ in range(H)]
    for x in range(7,42): g[16][x]='_'
    segment(g,j['bar_left'],j['bar_right'],'=')
    segment(g,j['shoulder'],j['root'],'|'); segment(g,j['shoulder'],j['left_hand'],'/'); segment(g,j['shoulder'],j['right_hand'],'\\')
    segment(g,j['root'],j['left_knee'],'/'); segment(g,j['left_knee'],j['left_foot'],'\\'); segment(g,j['root'],j['right_knee'],'\\'); segment(g,j['right_knee'],j['right_foot'],'/')
    for name,ch in [('bar_left','o'),('bar_right','o'),('left_hand','x'),('right_hand','x'),('head','O'),('shoulder','#'),('root','@'),('left_knee','+'),('right_knee','+'),('left_foot','L'),('right_foot','R')]:
        x,y=j[name]
        if 0<=x<W and 0<=y<H:g[y][x]=ch
    lines=[''.join(r) for r in g]
    if label:
        return f"{key['key_id']} {key['causal_role']}  src={key['source_time_s']:.2f}s OBSERVED  compile={key['compile_timing_class']} INFERRED\n"+'\n'.join(lines)
    return '\n'.join(lines)

def sheet(keys):
    panes=[]
    for k in keys:
        panes.append([f"{k['key_id']} {k['causal_role']}"[:W].ljust(W),f"src {k['source_time_s']:.2f}s OBS | {k['compile_timing_class']} INF"[:W].ljust(W)]+pose_ascii(k,False).splitlines())
    rows=[]
    for start in (0,4):
        group=panes[start:start+4]
        if not group: continue
        for y in range(len(group[0])): rows.append('   '.join(p[y] for p in group).rstrip())
        rows.append('')
    return '\n'.join(rows).rstrip()+'\n'

def interpolate(a,b,t):
    u=t*t*(3-2*t); out=json.loads(json.dumps(a))
    for name,pa in a['joints'].items():
        pb=b['joints'][name]; out['joints'][name]=[round(pa[0]+(pb[0]-pa[0])*u),round(pa[1]+(pb[1]-pa[1])*u)]
    out['key_id']=a['key_id']+'~'+b['key_id']; out['causal_role']=a['causal_role']+'→'+b['causal_role']; out['source_time_s']=a['source_time_s']+(b['source_time_s']-a['source_time_s'])*u
    return out

def compile_frames(keys):
    end=keys[-1]['compile_frame']+keys[-1]['compile_hold_frames']+4; frames=[]
    for fi in range(end):
        chosen=None
        for k in keys:
            if k['compile_frame']<=fi<k['compile_frame']+k['compile_hold_frames']: chosen=k; break
        if chosen is not None: frames.append((fi,chosen)); continue
        prev=max((k for k in keys if k['compile_frame']<fi),key=lambda k:k['compile_frame'],default=keys[0]); nxt=min((k for k in keys if k['compile_frame']>fi),key=lambda k:k['compile_frame'],default=keys[-1])
        start=prev['compile_frame']+prev['compile_hold_frames']; t=max(0,min(1,(fi-start+1)/max(1,nxt['compile_frame']-start)))
        frames.append((fi,prev if prev.get('causal_boundary_to_next') else interpolate(prev,nxt,t)))
    return frames

def frame_png(key,fi,target):
    text=pose_ascii(key,False).splitlines(); img=Image.new('RGB',(OUT_W,OUT_H),(7,10,13)); d=ImageDraw.Draw(img); font=ImageFont.load_default(size=18)
    d.text((24,18),f"ASCII KINESIS V2 / LOADED SQUAT / FRAME {fi:02d}",font=font,fill=(238,241,235)); d.text((24,43),key['causal_role'].replace('→',' > '),font=font,fill=(200,205,197)); d.text((24,67),"support: L+R grounded  |  bar: carried  |  source pixels: NONE",font=font,fill=(165,174,165))
    font2=ImageFont.load_default(size=22); y=104
    for line in text: d.text((58,y),line,font=font2,fill=(242,244,238)); y+=16
    img.save(target,'PNG',compress_level=9)

def encode_mp4(frames,out):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for fi,k in frames: frame_png(k,fi,td/f'f{fi:04d}.png')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(td/'f%04d.png'),'-an','-c:v','libx264','-preset','veryslow','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',str(out)],check=True)

def build():
    m=json.loads(MOTION.read_text()); keys=m['keys']; contact=sheet(keys); (ROOT/'contact_sheet.txt').write_text(contact)
    frames=compile_frames(keys); mp4=ROOT/'motion.mp4'; encode_mp4(frames,mp4); raw=mp4.read_bytes(); sha=hashlib.sha256(raw).hexdigest(); m['media'].update({'sha256':sha,'bytes':len(raw),'frame_count':len(frames)}); MOTION.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
    manifest={'schema':'ascii-kinesis.v2-manifest','format_version':2,'entry':m['experiment_id'],'lane':'video-motion','primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'video_required':True,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'backward_compatible':True,'offline_spa':True,'files':['contact_sheet.txt','motion.json','build_motion.py','manifest.json','receipt.json','loaded-squat-reversal-cost.motion.html'],'source':{'title':m['source']['title'],'url':m['source']['page_url'],'author':m['source']['author'],'rights_status':m['source']['rights_status'],'license_id':m['source']['license_id'],'source_sha256':m['source']['source_sha256'],'selected_action_segment_s':m['source']['selected_action_segment_s'],'whole_action_inspection':m['source']['whole_action_inspection']},'builder':{'path':'build_motion.py','method':'Motion Dungeon','input':'motion.json only; source video is never required for output rendering','source_video_dependency':False},'media':{'mime':'video/mp4','sha256':sha,'bytes':len(raw),'frame_count':len(frames),'compile_fps':FPS,'render_dimensions':[OUT_W,OUT_H],'embedded_in_spa':True,'source_pixels_used':False,'tracked_binary_sidecar':False},'compatibility':{'network_required':False,'v1_untouched':True,'v2_three_tab_read_path':True},'quality_gates':m['quality_gates'],'correction_hooks':['KEEP','REJECT','EXAGGERATE','COMPRESS','RETIME','CHANGE SOURCE','PROMOTE','SPAWN VARIANT','FIX BLOCKER','RERUN'],'status':'CANDIDATE_PRE_REPO_READBACK'}
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n')
    receipt={'schema':'ascii-kinesis.v2-receipt','entry':m['experiment_id'],'repo_path':'experiments/ascii-kinesis/v2-video-motion-006-loaded-squat-reversal-cost/','status':'CANDIDATE_PRE_REPO_READBACK','source':m['source'],'observed':m['evidence_boundary']['observed'],'inferred':m['evidence_boundary']['inferred'],'unknown':m['evidence_boundary']['unknown'],'observed_key_times_s':{k['key_id']:k['source_time_s'] for k in keys},'compile_timing_classes':{k['key_id']:k['compile_timing_class'] for k in keys},'media_sha256':sha,'media_bytes':len(raw),'media_frame_count':len(frames),'media_source':'abstract_ascii_rig_only','source_pixels_used_in_output':False,'quality_gates':m['quality_gates'],'repo_readback_verified':False,'issue_receipt_posted':False,'validation':{'contract_test':'tools/test_ascii_kinesis_swarm_contract_v2.py','entry_scoped_equivalent_check':'PENDING','repo_wide_test':'PENDING','embedded_mp4_identity':'PENDING','full_decode':'PENDING'},'correction_hooks':['KEEP','REJECT','EXAGGERATE','COMPRESS','RETIME','CHANGE SOURCE','PROMOTE','SPAWN VARIANT','FIX BLOCKER','RERUN']}
    (ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n')
    mtext=json.dumps(m,indent=2,ensure_ascii=False); b64=base64.b64encode(raw).decode('ascii'); agz=base64.b64encode(gzip.compress(contact.encode('utf-8'),mtime=0)).decode('ascii'); jgz=base64.b64encode(gzip.compress(mtext.encode('utf-8'),mtime=0)).decode('ascii')
    html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis · Loaded Squat Reversal Cost</title><style>body{{margin:0;background:#090c0f;color:#edf0eb;font-family:ui-monospace,SFMono-Regular,Consolas,monospace}}nav{{position:sticky;top:0;padding:12px;background:#11161b;border-bottom:1px solid #394148}}button{{font:inherit;padding:10px 16px;margin-right:8px;background:#1c242b;color:#edf0eb;border:1px solid #56616b;border-radius:6px}}button[aria-selected="true"]{{background:#edf0eb;color:#090c0f}}main{{padding:18px}}section{{display:none}}section.active{{display:block}}pre{{font:14px/1.05 ui-monospace,SFMono-Regular,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2}}video{{width:min(100%,960px);background:#000;display:block}}</style></head><body><nav><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav><main><section id="ascii" class="active"><pre id="ascii-pre"></pre></section><section id="json"><pre id="json-pre"></pre></section><section id="video"><video id="motion-video" controls loop playsinline preload="metadata"></video></section></main><script>const A="{agz}",J="{jgz}",V="{b64}";async function gun(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip')));return await r.text()}}Promise.all([gun(A),gun(J)]).then(([a,j])=>{{document.getElementById('ascii-pre').textContent=a;document.getElementById('json-pre').textContent=j;}});document.getElementById('motion-video').src="data:video/mp4;base64,"+V;const bs=[...document.querySelectorAll('button[data-view]')];bs.forEach(b=>b.onclick=()=>{{bs.forEach(x=>x.setAttribute('aria-selected',String(x===b)));document.querySelectorAll('main section').forEach(s=>s.classList.toggle('active',s.id===b.dataset.view));}});</script></body></html>'''
    (ROOT/'loaded-squat-reversal-cost.motion.html').write_text(html); print(json.dumps({'media_sha256':sha,'media_bytes':len(raw),'frames':len(frames)},sort_keys=True))
if __name__=='__main__': build()
