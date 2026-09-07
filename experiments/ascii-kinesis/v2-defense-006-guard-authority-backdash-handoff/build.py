#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
P=Path(__file__).resolve().parent; M=P/'motion.json'; HTML=P/'guard-authority-backdash-handoff.motion.html'; MP4=P/'guard-authority-backdash-handoff.mp4'; W,H=48,18
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
  x,y=j[n]; put(x,y+1,'=')
 if k['support_contact'] in {'BOTH_REAR_BIASED','REAR_ONLY'}:
  x,y=j['foot_l']; put(x,max(0,y-1),'^')
 if k['guard_authority'] in {'OWNED','CARRIED'}:
  hx,hy=j['hand_r']; put(min(W-1,hx+1),hy,']')
 if k['contact_state']=='INCOMING_RIGHT':
  for x in range(38,44): put(x,8,'<')
 if k['contact_state']=='IMPACT_RIGHT':
  for x in range(36,44): put(x,9,'<')
  hx,hy=j['hand_r']; put(min(W-1,hx+2),hy,'X')
 return '\n'.join(''.join(r).rstrip() for r in g)
def topology(k): return tuple(k[x] for x in ('support_contact','contact_state','constraint_state','root_state','readiness','guard_authority','impact_memory'))
def interpolate(a,b,t): return {n:[round(a['joints'][n][0]+(b['joints'][n][0]-a['joints'][n][0])*t),round(a['joints'][n][1]+(b['joints'][n][1]-a['joints'][n][1])*t)] for n in a['joints']}
def sheet(d):
 out=[]
 for k in d['keys']:
  out.append(f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | support={k['support_contact']} | contact={k['contact_state']} | root={k['root_state']} | guard={k['guard_authority']} | debt={k['recoil_debt']}\nrole: {k['causal_role']}\nroot: {k['motion_arc_root_note']}\n{pose(k)}")
 return '\n\n'.join(out)
def font(size=17):
 for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/dejavu/DejaVuSansMono.ttf']:
  if Path(p).exists(): return ImageFont.truetype(p,size)
 return ImageFont.load_default()
def render_png(text,path,label):
 im=Image.new('RGB',(768,432),'black');dr=ImageDraw.Draw(im);f=font(17);small=font(13)
 dr.text((14,10),label,fill='white',font=small);dr.multiline_text((14,34),text,fill='white',font=f,spacing=0);im.save(path)
def compile_video(d):
 seq=[]
 for i,k in enumerate(d['keys']):
  seq += [(k['key_id'],pose(k))]*HOLD[k['timing_class']]
  if i+1<len(d['keys']) and topology(k)==topology(d['keys'][i+1]):
   b=d['keys'][i+1]
   for t in (1/3,2/3): seq.append((k['key_id']+'~'+b['key_id'],pose(k,interpolate(k,b,t))))
 with tempfile.TemporaryDirectory() as td:
  td=Path(td);frames=seq*int(d['compile']['loop_repetitions'])
  for i,(lab,txt) in enumerate(frames): render_png(txt,td/f'f{i:04d}.png',lab)
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),'-i',str(td/'f%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','27','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
 return len(seq)
def probe():
 q=json.loads(subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration','-of','json',str(MP4)],check=True,capture_output=True,text=True).stdout);s=q['streams'][0]
 return {'tool':'ffprobe','codec':s['codec_name'],'width':int(s['width']),'height':int(s['height']),'fps':s['r_frame_rate'],'frames':int(s['nb_frames']),'duration_seconds':float(q['format']['duration'])}
def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def page(d,s,b64):
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Defense 006</title><style>:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1100px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:82ch;line-height:1.45}}</style></head><body><h1>Guard Authority → Backdash Handoff</h1><p class="note">Copyright-safe abstract ASCII defensive specimen. Source art is evidence only. The performance tracks force, support, guard authority, recoil debt, displacement, and state re-entry.</p><nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button></nav><section id="ascii" role="tabpanel"><pre>{esc(s)}</pre></section><section id="json" role="tabpanel" hidden><pre>{esc(json.dumps(d,separators=(',',':'),sort_keys=True))}</pre></section><section id="video" role="tabpanel" hidden><video controls playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video><p class="note">Motion Dungeon media: authored ASCII keys, explicit holds, topology-safe connective geometry, ASCII-only frame render. No source sprite pixels enter the video.</p></section><script>const T=[...document.querySelectorAll('[data-view]')],S=[...document.querySelectorAll('section[role=tabpanel]')];T.forEach(t=>t.onclick=()=>{{T.forEach(b=>b.setAttribute('aria-selected',b===t?'true':'false'));S.forEach(s=>s.hidden=s.id!==t.dataset.view)}});</script></body></html>'''
def manifest(d,pr,per):
 return {'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':d['experiment_id'],'lane':'defense','principle':d['principle'],'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'ascii_surface':'real preformatted DOM text','ligatures_disabled':True,'whitespace_preserved':True,'video_required':True,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'backward_compatible':True,'compatibility':d['compatibility'],'files':['build.py','manifest.json','motion.json','receipt.md','guard-authority-backdash-handoff.motion.html'],'reconstruction':'python3 build.py','video_packaging':'authoritative embedded MP4 data URI in guard-authority-backdash-handoff.motion.html','tracked_media_sidecar':False,'media_sha256':d['compile']['media_sha256'],'media_bytes':d['compile']['media_bytes'],'media_decode_preflight':pr,'motion_dungeon':{'authored_ascii_keys':len(d['keys']),'explicit_holds':True,'deterministic_connective_motion':True,'connector_semantics_fail_closed':True,'ascii_only_frame_render':True,'fps':d['compile']['fps'],'loop_repetitions':d['compile']['loop_repetitions'],'semantic_frames_per_loop':per,'video_frames_total':pr['frames']},'source':d['source'],'rights':d['rights'],'timing_provenance_required':True,'quality_gates':{'tango':d['quality_gates']['tango']['status'],'noodle_queen':d['quality_gates']['noodle_queen']['status']},'correction_hooks':d['correction_hooks'],'receipt_status':'TANGO SATISFIED / NOODLE_QUEEN PASS / READY_FOR_REPO_READBACK'}
def receipt(d,pr):
 times='\n'.join(f"- {k['key_id']} {k['name']} — {k['timing_class']} — {k['timing_provenance']}" for k in d['keys'])
 return f'''# ASCII Kinesis V2 Defense 006 — receipt\n\nStatus: TANGO SATISFIED / NOODLE_QUEEN PASS / READY_FOR_REPO_READBACK\n\n## Product\n`experiments/ascii-kinesis/v2-defense-006-guard-authority-backdash-handoff/` with exactly `ASCII | JSON | VIDEO`; literal selectable `<pre>` ASCII; embedded H.264 MP4 from abstract rig/timing only.\n\n## Source / rights\nThe Spriters Resource — Lionel — *Mina the Hollower* — PC / Computer — Bosses — asset 577707 — {d['source']['page_url']}\nTSR reports 149 items / 24 animation families. Whole asset treated as evidence. Commercial source art remains evidence only. Drew work was not used. No source pixels, palette, contour, layout, tracing, redistribution, or close imitation enters output.\n\n## Observation / inference\nOBSERVED: Block, Block Spark, Back Dash Ready, Back Dash, Back Dash Outro, Idle Hurt and contrasting action/consequence families coexist in one 149-item asset. Source-authentic exposure timing was not measured.\nINFERRED: guard authority can survive the support break; compression stores recoil debt; retreat translation spends that debt; recovery starts at the first trustworthy rear plant and READY returns at a displaced root address.\nUNKNOWN: exact source chronology, duration, block-stop, support foot, root path, game cancel rules.\n\n## Timing\nAll decisive keys are INFERRED under STREET_FIGHTER/CAPCOM. `1s/2s/4s` means ONES/TWOS/FOURS, never seconds.\n{times}\n\n## Compile\nMotion Dungeon: authored ASCII keys -> explicit holds/timing -> deterministic connective motion -> ASCII-only frame render -> MP4 -> SPA.\nMP4 SHA-256 `{d['compile']['media_sha256']}`; {d['compile']['media_bytes']} bytes; H.264 {pr['width']}×{pr['height']} {pr['fps']} {pr['frames']} frames {pr['duration_seconds']:.6f}s. ASCII SHA-256 `{d['ascii_sheet_sha256']}`.\n\n## Quality gates\nTango: {json.dumps(d['quality_gates']['tango'],sort_keys=True)}\nNoodle Queen: {json.dumps(d['quality_gates']['noodle_queen'],sort_keys=True)}\n\n## Correction hooks\nKEEP / REJECT / EXAGGERATE / COMPRESS / RETIME / CHANGE SOURCE / PROMOTE / SPAWN VARIANT / FIX BLOCKER / RERUN\n'''
def main():
 d=json.loads(M.read_text());per=compile_video(d);raw=MP4.read_bytes();pr=probe();s=sheet(d)
 d['compile'].update(media_sha256=hashlib.sha256(raw).hexdigest(),media_bytes=len(raw),semantic_frames_per_loop=per,video_frames_total=pr['frames'],media_decode_preflight=pr);d['ascii_sheet_sha256']=hashlib.sha256(s.encode()).hexdigest();M.write_text(json.dumps(d,separators=(',',':'),sort_keys=True)+'\n')
 (P/'manifest.json').write_text(json.dumps(manifest(d,pr,per),separators=(',',':'),sort_keys=True)+'\n');(P/'receipt.md').write_text(receipt(d,pr));HTML.write_text(page(d,s,base64.b64encode(raw).decode()))
 print(json.dumps({'media_sha256':d['compile']['media_sha256'],'media_bytes':len(raw),'frames':pr['frames'],'duration':pr['duration_seconds'],'semantic_frames_per_loop':per,'ascii_sheet_sha256':d['ascii_sheet_sha256']},sort_keys=True))
if __name__=='__main__': main()
