#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,json,subprocess,tempfile,math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent
M=P/'motion.json'
HTML=P/'guard-support-fork-repair.motion.html'
MP4=P/'guard-support-fork-repair.mp4'
W,H=56,22
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
LINKS=[('head','neck'),('neck','shoulder_l'),('neck','shoulder_r'),('shoulder_l','elbow_l'),('elbow_l','hand_l'),('shoulder_r','elbow_r'),('elbow_r','hand_r'),('neck','pelvis'),('pelvis','knee_l'),('pelvis','knee_r'),('knee_l','foot_l'),('knee_r','foot_r')]

def bres(a,b):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;out=[]
 while True:
  out.append((x0,y0))
  if (x0,y0)==(x1,y1): return out
  e=2*err
  if e>=dy: err+=dy;x0+=sx
  if e<=dx: err+=dx;y0+=sy

def glyph(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 if abs(dx)>2*abs(dy): return '-'
 if abs(dy)>2*abs(dx): return '|'
 return '\\' if dx*dy>0 else '/'

def support_feet(state):
 if state in {'BOTH','BOTH_REAR_BIASED'}: return {'foot_l','foot_r'}
 if state=='REAR_ONLY': return {'foot_l'}
 if state=='FRONT_ONLY': return {'foot_r'}
 return set()

def pose(k,j=None):
 j=j or k['joints']; g=[[' ']*W for _ in range(H)]
 def put(x,y,c):
  if 0<=x<W and 0<=y<H: g[y][x]=c
 for a,b in LINKS:
  for x,y in bres(j[a],j[b])[1:-1]:
   if 0<=x<W and 0<=y<H and g[y][x]==' ': put(x,y,glyph(j[a],j[b]))
 for n,(x,y) in j.items(): put(x,y,'@' if n=='pelvis' else ('O' if n=='head' else 'o'))
 for n in support_feet(k['support_contact']):
  x,y=j[n];put(x,min(H-1,y+1),'=')
 if k['support_contact']=='BOTH_REAR_BIASED':
  x,y=j['foot_l'];put(x,max(0,y-1),'^')
 if k['guard_authority'] in {'OWNED','CARRIED','RECOVERING'}:
  hx,hy=j['hand_r'];put(min(W-1,hx+1),hy,']')
 if k['contact_state']=='IMPACT_RIGHT':
  hx,hy=j['hand_r']
  put(min(W-1,hx+2),hy,'X')
  for x in range(min(W-1,hx+4),min(W-1,hx+12)): put(x,hy,'<')
 if k['recoil_debt'] >= .55:
  px,py=j['pelvis']
  for d in range(1,4): put(max(0,px-d),min(H-1,py+1),'~')
 return '\n'.join(''.join(r).rstrip() for r in g)

def topology(k):
 return tuple(k[x] for x in ('support_contact','contact_state','root_state','guard_authority','readiness','impact_memory'))

def interp_point(a,b,t,arc):
 e=(1-math.cos(math.pi*t))/2
 x=a[0]+(b[0]-a[0])*e
 y=a[1]+(b[1]-a[1])*e
 if arc:
  x += 4*t*(1-t)*arc[0]
  y += 4*t*(1-t)*arc[1]
 return [round(x),round(y)]

def interpolate(a,b,t,arcmap):
 return {n:interp_point(a['joints'][n],b['joints'][n],t,arcmap.get(n,[0,0])) for n in a['joints']}

def sheet(d):
 out=[]
 for k in d['keys']:
  out.append(
f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | support={k['support_contact']} | contact={k['contact_state']} | root={k['root_state']} | guard={k['guard_authority']} | debt={k['recoil_debt']:.2f} | lag={k['secondary_lag']}\n"
f"role: {k['causal_role']}\nroot: {k['motion_arc_root_note']}\n{pose(k)}")
 return '\n\n'.join(out)

def font(size=19):
 for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/font/truetype/dejavu/DejaVuSansMono.ttf']:
  if Path(p).exists(): return ImageFont.truetype(p,size)
 return ImageFont.load_default()

def render_png(text,path,label):
 im=Image.new('RGB',(896,504),'black');dr=ImageDraw.Draw(im);f=font(19);small=font(15)
 dr.text((16,10),label,fill='white',font=small)
 dr.multiline_text((16,38),text,fill='white',font=f,spacing=0)
 im.save(path)

def compile_video(d):
 seq=[]
 for i,k in enumerate(d['keys']):
  seq += [(k['key_id'],pose(k))]*HOLD[k['timing_class']]
  if i+1<len(d['keys']):
   conn=k.get('connective_to_next',{})
   b=d['keys'][i+1]
   if conn.get('authorized') and topology(k)==topology(b):
    for t in (.25,.5,.75):
     seq.append((k['key_id']+'~'+b['key_id'],pose(k,interpolate(k,b,t,conn.get('arc',{})))))
 with tempfile.TemporaryDirectory() as td:
  td=Path(td); frames=seq*int(d['compile']['loop_repetitions'])
  for i,(lab,txt) in enumerate(frames): render_png(txt,td/f'f{i:04d}.png',lab)
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),
                  '-i',str(td/'f%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','25',
                  '-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
 return len(seq)

def probe():
 q=json.loads(subprocess.run(['ffprobe','-v','error','-select_streams','v:0',
   '-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration',
   '-of','json',str(MP4)],check=True,capture_output=True,text=True).stdout)
 s=q['streams'][0]
 return {'tool':'ffprobe','codec':s['codec_name'],'width':int(s['width']),'height':int(s['height']),
         'fps':s['r_frame_rate'],'frames':int(s['nb_frames']),'duration_seconds':float(q['format']['duration'])}

def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def page(d,s,b64):
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Defense 007</title><style>:root{{color-scheme:dark;background:#0e0f10;color:#eee;font-family:system-ui,sans-serif}}
body{{margin:0;padding:1rem;max-width:1200px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#0e0f10;padding:.5rem 0}}
button{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.0}}
video{{display:block;max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:88ch;line-height:1.45}}</style></head>
<body><h1>Guard / Support Authority Fork — Performance Repair</h1>
<p class="note">Successor repair of the oldest Defense V2 negative fixture. Abstract ASCII performance only; source sprite art never enters output.</p>
<nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button></nav>
<section id="ascii" role="tabpanel"><pre>{esc(s)}</pre></section>
<section id="json" role="tabpanel" hidden><pre>{esc(json.dumps(d,separators=(',',':'),sort_keys=True))}</pre></section>
<section id="video" role="tabpanel" hidden><video controls playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video>
<p class="note">Motion Dungeon compile: decisive ASCII keys + explicit holds + only topology-safe authored connective arcs → ASCII-only frame raster → embedded H.264 MP4. No source pixels.</p></section>
<script>const T=[...document.querySelectorAll('[data-view]')],S=[...document.querySelectorAll('section[role=tabpanel]')];T.forEach(t=>t.onclick=()=>{{T.forEach(b=>b.setAttribute('aria-selected',b===t?'true':'false'));S.forEach(s=>s.hidden=s.id!==t.dataset.view}});</script>
</body></html>'''

def manifest(d,pr,per):
 return {'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':d['experiment_id'],'lane':'defense',
 'revision':d['revision'],'principle':d['principle'],'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,
 'ascii_surface':'real preformatted DOM text','ligatures_disabled':True,'whitespace_preserved':True,'video_required':True,
 'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'backward_compatible':True,'compatibility':d['compatibility'],
 'files':['build.py','manifest.json','motion.json','receipt.md','guard-support-fork-repair.motion.html'],
 'reconstruction':'python3 build.py','video_packaging':'authoritative embedded MP4 data URI in guard-support-fork-repair.motion.html',
 'tracked_media_sidecar':False,'media_sha256':d['compile']['media_sha256'],'media_bytes':d['compile']['media_bytes'],
 'media_decode_preflight':pr,'motion_dungeon':{'authored_ascii_keys':len(d['keys']),'explicit_holds':True,
 'deterministic_connective_motion':True,'connector_semantics_fail_closed':True,'ascii_only_frame_render':True,
 'fps':d['compile']['fps'],'loop_repetitions':d['compile']['loop_repetitions'],'semantic_frames_per_loop':per,'video_frames_total':pr['frames']},
 'source':d['source'],'rights':d['rights'],'timing_provenance_required':True,
 'quality_gates':d['quality_gates'],'validation':d.get('validation',{}),'correction_hooks':d['correction_hooks'],'receipt_status':'QUALITY_GATES_RECORDED / READY_FOR_REPO_READBACK'}

def receipt(d,pr):
 times='\n'.join(f"- {k['key_id']} {k['name']} — {k['timing_class']} — {k['timing_provenance']}" for k in d['keys'])
 return f'''# ASCII Kinesis V2 Defense 007 — repair receipt

Status: QUALITY_GATES_RECORDED / READY_FOR_REPO_READBACK

## Revision
- revises: `{d['revision']['revises']}`
- negative_fixture: `{d['revision']['negative_fixture']}`
- predecessor verdict: `{d['revision']['verdict']}`
- predecessor preserved unchanged: required / confirmed by separate repo readback
- source change: false

## Product
`experiments/ascii-kinesis/v2-defense-007-guard-support-fork-repair/`
Exactly `ASCII | JSON | VIDEO`; literal selectable `<pre>` ASCII; real embedded H.264 MP4 from abstract rig/timing only.

## Source / rights
The Spriters Resource — Cammy — *Super Street Fighter II: The New Challengers* — SNES — asset 5553 — {d['source']['url']}
Same whole-sheet evidence family as the negative fixture. No fresh source/new concept. No Drew work. No source pixels/palette/contour/layout/tracing/choreography/redistribution/close imitation enters output.

## Observation / inference
OBSERVED: inherited predecessor whole-sheet evidence only; compact defensive and broader consequence/re-entry families were established there. No source-authentic timing measured.
INFERRED: asymmetrical brace, directional contact, compression, support break, recoil arc, overshoot, secondary lag, consequence hold, trustworthy plant, settle and recovery debt are independently authored abstract performance choices.
UNKNOWN: source chronology, exposure timing, hit-stop, exact hitbox, exact support foot, source root path.

## Timing
All decisive keys INFERRED / STREET_FIGHTER-CAPCOM. `1s/2s/4s` = ONES/TWOS/FOURS, never seconds.
{times}

## Compile
Motion Dungeon: authored ASCII keys -> explicit holds/timing -> deterministic topology-safe connective arcs -> ASCII-only frame render -> MP4 -> SPA.
MP4 SHA-256 `{d['compile']['media_sha256']}`; {d['compile']['media_bytes']} bytes; H.264 {pr['width']}×{pr['height']}; {pr['fps']}; {pr['frames']} frames; {pr['duration_seconds']:.6f}s.
ASCII SHA-256 `{d['ascii_sheet_sha256']}`.

## Tango
{json.dumps(d['quality_gates']['tango'],sort_keys=True)}

## Noodle Queen
{json.dumps(d['quality_gates']['noodle_queen'],sort_keys=True)}

## Contract regression
Isolated exact-script successor check: {json.dumps(d.get('validation',{}).get('successor_isolated_exact_script',{}),sort_keys=True)}
Full-repository boundary: {json.dumps(d.get('validation',{}).get('full_repository_regression',{}),sort_keys=True)}

## Correction hooks
KEEP / REJECT / EXAGGERATE / COMPRESS / RETIME / CHANGE SOURCE / PROMOTE / SPAWN VARIANT / FIX BLOCKER / RERUN
'''

def main():
 d=json.loads(M.read_text())
 per=compile_video(d); raw=MP4.read_bytes(); pr=probe(); s=sheet(d)
 d['compile'].update(media_sha256=hashlib.sha256(raw).hexdigest(),media_bytes=len(raw),semantic_frames_per_loop=per,video_frames_total=pr['frames'],media_decode_preflight=pr)
 d['ascii_sheet_sha256']=hashlib.sha256(s.encode()).hexdigest()
 M.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
 (P/'manifest.json').write_text(json.dumps(manifest(d,pr,per),indent=2,sort_keys=True)+'\n')
 (P/'receipt.md').write_text(receipt(d,pr))
 HTML.write_text(page(d,s,base64.b64encode(raw).decode()))
 print(json.dumps({'media_sha256':d['compile']['media_sha256'],'media_bytes':len(raw),'frames':pr['frames'],'duration':pr['duration_seconds'],'semantic_frames_per_loop':per,'ascii_sheet_sha256':d['ascii_sheet_sha256']},sort_keys=True))
if __name__=='__main__': main()
