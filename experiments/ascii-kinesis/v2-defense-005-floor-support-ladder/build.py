#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
P=Path(__file__).resolve().parent
M=P/'motion.json'; SPA=P/'floor-support-ladder.motion.html'; MP4=P/'floor-support-ladder.mp4'
W,H=48,18
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
LINKS=[('head','shoulder_l'),('head','shoulder_r'),('shoulder_l','shoulder_r'),('shoulder_l','hand_l'),('shoulder_r','hand_r'),('shoulder_l','pelvis'),('shoulder_r','pelvis'),('pelvis','knee_l'),('pelvis','knee_r'),('knee_l','foot_l'),('knee_r','foot_r')]
def bres(a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;pts=[]
    while True:
        pts.append((x0,y0))
        if (x0,y0)==(x1,y1): return pts
        e=2*err
        if e>=dy: err+=dy;x0+=sx
        if e<=dx: err+=dx;y0+=sy
def glyph(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if abs(dx)>2*abs(dy): return '-'
    if abs(dy)>2*abs(dx): return '|'
    return '\\' if dx*dy>0 else '/'
def support_marks(k):
    s=k['support_contact']
    if s=='BOTH_FEET': return {'foot_l','foot_r'}
    if s=='REAR_FOOT': return {'foot_r'}
    if s=='FLOOR_MULTI': return {'hand_l','pelvis','knee_l','knee_r'}
    if s=='HAND_KNEE': return {'hand_l','knee_l'}
    if s=='FRONT_FOOT_HAND': return {'foot_r','hand_l'}
    return set()
def pose(k,j=None):
    j=j or k['joints'];g=[[' ']*W for _ in range(H)]
    def put(x,y,c):
        if 0<=x<W and 0<=y<H:g[y][x]=c
    for a,b in LINKS:
        for x,y in bres(j[a],j[b])[1:-1]:
            if g[y][x]==' ': put(x,y,glyph(j[a],j[b]))
    for n,(x,y) in j.items(): put(x,y,'@' if n=='pelvis' else ('O' if n=='head' else 'o'))
    for n in support_marks(k):
        x,y=j[n];put(x,min(y+1,H-1),'=')
    if k['contact_state']=='INCOMING_LOW_RIGHT':
        for x in range(35,42): put(x,13,'<')
    elif k['contact_state']=='IMPACT_LOW_RIGHT':
        for x in range(34,40): put(x,14,'<')
        x,y=j['knee_r'];put(min(x+2,W-1),y,'X')
    if k['constraint_state']=='FLOOR':
        for x in range(3,44): put(x,16,'_')
    return '\n'.join(''.join(r).rstrip() for r in g)
def topo(k): return tuple(k[x] for x in ('support_contact','contact_state','constraint_state','root_state','readiness'))
def contact_sheet(d):
    out=[]
    for k in d['keys']:
        out.append(f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | support={k['support_contact']} | contact={k['contact_state']} | root={k['root_state']} | ready={k['readiness']}\nrole: {k['causal_role']}\nroot: {k['motion_arc_root_note']}\n{pose(k)}")
    return '\n\n'.join(out)
def png(text,path,label):
    im=Image.new('RGB',(640,360),'black');dr=ImageDraw.Draw(im)
    try: font=ImageFont.load_default(size=18)
    except TypeError: font=ImageFont.load_default()
    dr.text((16,9),label,fill='white',font=font);dr.multiline_text((16,38),text,fill='white',font=font,spacing=1);im.save(path)
def compile_video(d):
    seq=[]
    for i,k in enumerate(d['keys']):
        seq += [(k['key_id'],pose(k))]*HOLD[k['timing_class']]
        if i+1<len(d['keys']) and topo(k)==topo(d['keys'][i+1]):
            b=d['keys'][i+1]
            jj={n:[round(k['joints'][n][z]+(b['joints'][n][z]-k['joints'][n][z])*0.5) for z in (0,1)] for n in k['joints']}
            seq.append((k['key_id']+'~'+b['key_id'],pose(k,jj)))
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        frames=seq*int(d['compile']['loop_repetitions'])
        for i,(lab,txt) in enumerate(frames): png(txt,td/f'f{i:04d}.png',lab)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),'-i',str(td/'f%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','35','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
    return len(seq)
def probe():
    raw=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration','-of','json',str(MP4)],check=True,capture_output=True,text=True).stdout
    q=json.loads(raw);s=q['streams'][0]
    return {'tool':'ffprobe','codec':s['codec_name'],'width':int(s['width']),'height':int(s['height']),'fps':s['r_frame_rate'],'frames':int(s['nb_frames']),'duration_seconds':float(q['format']['duration'])}
def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def page(d,s,b64):
    payload=json.dumps(d,separators=(',',':'),sort_keys=True)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Defense 005</title><style>:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1100px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:78ch;line-height:1.45}}</style></head><body><h1>Floor-Support Recovery Ladder</h1><p class="note">Abstract ASCII-only knockdown recovery specimen. Source art is evidence only and is not embedded. The body regains support authority before it regains height and action readiness.</p><nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button tye="tab" data-view="video" aria-selected="false">VIDEO</button></nav><section id="ascii" role="tabpanel"><pre>{esc(s)}</pre></section><section id="json" role="tabpanel" hidden><pre>{esc(payload)}</pre></section><section id="video" role="tabpanel" hidden><video controls loop playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video><p class="note">Motion Dungeon media is generated solely from the independently authored ASCII rig coordinates, explicit holds, and fail-closed connective geometry.</p></section><script>const T=[...document.querySelectorAll('[data-view]')],S=[...document.querySelectorAll('section[role=tabpanel]')];T.forEach(t=>t.onclick=()=>{{T.forEach(b=>b.setAttribute('aria-selected',b===t?'true':'false'));S.forEach(s=>s.hidden=s.id!==t.dataset.view)}});</script></body></html>'''
def manifest(d,p):
    return {'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':d['experiment_id'],'lane':'defense','principle':d['principle'],'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'ascii_surface':'real preformatted DOM text','ligatures_disabled':True,'whitespace_preserved':True,'video_required':True,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'backward_compatible':True,'compatibility':d['compatibility'],'files':['build.py','manifest.json','motion.json','receipt.md','floor-support-ladder.motion.html'],'reconstruction':'python3 build.py','video_packaging':'authoritative embedded MP4 data URI in floor-support-ladder.motion.html','tracked_media_sidecar':False,'media_sha256':d['compile']['media_sha256'],'media_bytes':d['compile']['media_bytes'],'media_decode_preflight':p,'motion_dungeon':{'authored_ascii_keys':len(d['keys']),'explicit_holds':True,'deterministic_connective_motion':True,'connector_semantics_fail_closed':True,'ascii_only_frame_render':True,'fps':d['compile']['fps'],'loop_repetitions':d['compile']['loop_repetitions'],'semantic_frames_per_loop':d['compile']['semantic_frames_per_loop'],'video_frames_total':d['compile']['video_frames_total']},'source':d['source'],'rights':d['rights'],'timing_provenance_required':True,'correction_hooks':d['correction_hooks'],'receipt_status':'RENDERED / STRUCTURALLY_TESTED / READY_FOR_REPO_READBACK'}
def receipt(d,p):
    timing='\n'.join(f"- {k['key_id']} {k['name']} — {k['timing_class']} — {k['timing_provenance']}" for k in d['keys'])
    return f'''# ASCII Kinesis V2 Defense 005 — receipt\n\nStatus: RENDERED / STRUCTURALLY_TESTED / READY_FOR_REPO_READBACK\n\n## Product\n`experiments/ascii-kinesis/v2-defense-005-floor-support-ladder/` with exactly `ASCII | JSON | VIDEO`; literal selectable `<pre>` ASCII; embedded H.264 MP4 from abstract rig/timing only.\n\n## Source / rights\nThe Spriters Resource — Chun-Li — *Street Fighter III (Bootleg)* — NES — asset 36391 — {d['source']['page_url']}\nTSR metadata: {d['source']['dimensions'][0]}×{d['source']['dimensions'][1]} PNG. Complete rendered sheet inspected as one image. Commercial source art is evidence only. Drew work was not used. No source pixels, palette, contour, layout, tracing, redistribution, close imitation, or source choreography enters output.\n\n## Observation / inference\nOBSERVED: complete-sheet labeled consequence/recovery families include Hit High, Hit Low, Crouch Hit, Falling, Down, and Get Up among broader upright/crouching actions; consequence silhouettes materially lower/broaden the body axis before return-to-upright material. Source timing is not established.\nINFERRED: recovery is a support-authority ladder: both-feet stance -> narrowed impact support -> unsupported balance loss -> broad floor support -> posted hand/knee support -> foot plant -> stacked ready. Height recovery is downstream of trustworthy support recovery.\nUNKNOWN: source chronology/exposure, hit-stop, exact anatomical support sequence, exact contact force/root path/game-state transition.\n\n## Timing\nAll decisive keys are INFERRED under STREET_FIGHTER/CAPCOM. `1s/2s/4s` means ONES/TWOS/FOURS, never seconds.\n{timing}\n\n## Compile\nMotion Dungeon: authored decisive ASCII keys -> explicit holds/timing -> deterministic connective motion -> ASCII-only frame render -> MP4 -> SPA. Connector state tuple support/contact/constraint/root/readiness fails closed; causal joins hard-cut.\nMP4 SHA-256 `{d['compile']['media_sha256']}`; {d['compile']['media_bytes']} bytes; H.264 {p['width']}×{p['height']} {p['fps']} {p['frames']} frames {p['duration_seconds']:.6f}s. ASCII SHA-256 `{d['ascii_sheet_sha256']}`.\n\n## Correction hooks\nKEEP / REJECT / EXAGGERATE / COMPRESS / RETIME / CHANGE SOURCE / PROMOTE / SPAWN VARIANT / FIX BLOCKER / RERUN\n'''
def main():
    d=json.loads(M.read_text());n=compile_video(d);raw=MP4.read_bytes();p=probe();s=contact_sheet(d)
    d['compile'].update(media_sha256=hashlib.sha256(raw).hexdigest(),media_bytes=len(raw),semantic_frames_per_loop=n,video_frames_total=n*int(d['compile']['loop_repetitions']),media_decode_preflight=p)
    d['ascii_sheet_sha256']=hashlib.sha256(s.encode()).hexdigest()
    M.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
    (P/'manifest.json').write_text(json.dumps(manifest(d,p),indent=2,sort_keys=True)+'\n')
    (P/'receipt.md').write_text(receipt(d,p))
    SPA.write_text(page(d,s,base64.b64encode(raw).decode()))
    print(json.dumps({'media_sha256':d['compile']['media_sha256'],'media_bytes':len(raw),'semantic_frames_per_loop':n,'video_frames_total':p['frames'],'duration':p['duration_seconds'],'ascii_sheet_sha256':d['ascii_sheet_sha256']},sort_keys=True))
if __name__=='__main__': main()
