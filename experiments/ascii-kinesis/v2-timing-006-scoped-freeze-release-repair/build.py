#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'; SLUG='scoped-freeze-release-repair'
MP4=HERE/f'{SLUG}.mp4'; GIF=HERE/f'{SLUG}.chat.gif'; HTML=HERE/f'{SLUG}.motion.html'; MANIFEST=HERE/'manifest.json'; RECEIPT=HERE/'receipt.json'; CONTACT=HERE/'contact-sheet.txt'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
def sha(b): return hashlib.sha256(b).hexdigest()
def bres(a,b):
 x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; e=dx+dy; out=[]
 while True:
  out.append((x0,y0))
  if (x0,y0)==(x1,y1): break
  q=2*e
  if q>=dy: e+=dy; x0+=sx
  if q<=dx: e+=dx; y0+=sy
 return out
def glyph(a,b):
 dx=b[0]-a[0]; dy=b[1]-a[1]
 if abs(dx)>abs(dy)*2:return '-'
 if abs(dy)>abs(dx)*2:return '|'
 return '\\' if dx*dy>0 else '/'
def ease(t,kind):
 if kind=='EASE_IN': return t*t
 if kind=='EASE_OUT': return 1-(1-t)*(1-t)
 if kind=='SMOOTHSTEP': return t*t*(3-2*t)
 return t
def qpoint(a,b,t,bias):
 c=[(a[0]+b[0])/2+bias[0],(a[1]+b[1])/2+bias[1]]; u=1-t
 return [round(u*u*a[0]+2*u*t*c[0]+t*t*b[0]),round(u*u*a[1]+2*u*t*c[1]+t*t*b[1])]
def interp_joints(a,b,t,bias):
 out={}
 for n,p in a.items():
  q=b[n]
  if 'foot' in n: out[n]=list(p) if p==q else qpoint(p,q,t,[0,0])
  elif 'hand' in n: out[n]=qpoint(p,q,t,[bias[0]*1.5,bias[1]*1.5])
  elif 'elbow' in n: out[n]=qpoint(p,q,t,bias)
  else: out[n]=qpoint(p,q,t,[bias[0]*0.35,bias[1]*0.35])
 return out
def hydrate_joints(d,k):
 lib=d['rig_schema']['state_library']; pr=k['pose_rig']; j={}
 j.update({n:list(v) for n,v in lib['fixed_lower'].items()}); j.update({n:list(v) for n,v in lib['base'][pr['base_state']].items()}); j.update({n:list(v) for n,v in lib['signal_A'][pr['signal_A_phase']].items()}); j.update({n:list(v) for n,v in lib['signal_B'][pr['signal_B_phase']].items()})
 cx=j['chest'][0]; j['left_shoulder']=[cx-4,10]; j['right_shoulder']=[cx+4,10]; return j
def frame_text(d,k,joints=None,gate=None):
 W,H=d['rig_schema']['grid']; j={n:list(v) for n,v in (joints or hydrate_joints(d,k)).items()}; g=[[' ']*W for _ in range(H)]
 def put(x,y,ch):
  if 0<=x<W and 0<=y<H:g[y][x]=ch
 for a,b in d['rig_schema']['links']:
  for x,y in bres(j[a],j[b])[1:-1]:
   if 0<=y<H and 0<=x<W and g[y][x]==' ':put(x,y,glyph(j[a],j[b]))
 marks={'root':'@','chest':'+','neck':':','head':'O','left_shoulder':'o','left_elbow':'o','left_hand':'A','right_shoulder':'o','right_elbow':'o','right_hand':'B','left_hip':'o','left_knee':'o','left_foot':'L','right_hip':'o','right_knee':'o','right_foot':'R'}
 for n,(x,y) in j.items():put(x,y,marks.get(n,'o'))
 fy=max(j['left_foot'][1],j['right_foot'][1])
 for x in range(min(j['left_foot'][0],j['right_foot'][0])-4,max(j['left_foot'][0],j['right_foot'][0])+5):put(x,fy+1,'=')
 put(j['left_foot'][0],fy+1,'^'); put(j['right_foot'][0],fy+1,'^')
 gate=gate or k['pose_rig']['gate_state']; put(j['head'][0],1,{'OPEN':'g','FREEZE_B':'F','RELEASE_B':'R'}[gate])
 if gate=='FREEZE_B': bx,by=j['right_hand']; put(bx-1,by,'['); put(bx+1,by,']')
 elif gate=='RELEASE_B': bx,by=j['right_hand']; put(bx-1,by,'<'); put(bx+1,by,'>')
 return '\n'.join(''.join(r).rstrip() for r in g)
def contact_sheet(d):
 out=['ASCII KINESIS V2 TIMING 006 — SCOPED FREEZE / RELEASE REPAIR',f"revises: {d['revises']}",f"negative_fixture: {d['negative_fixture']}",'SOURCE ART: NONE | TIMING: INFERRED | 1s/2s/4s => ONES/TWOS/FOURS','']
 for k in d['keys']:
  out += [f"[{k['key_id']}] {k['name']} | pose/rig={k['pose_rig']['rig_id']} | support/contact={k['support_contact']}",f"timing={k['timing_class']} | timing_provenance={k['timing_provenance']} | changed={','.join(k['changed_channels']) or 'NONE'}",f"root/motion-arc: {k['motion_arc_root_note']}",f"causal role: {k['causal_role']}",f"clocks: BASE={k['clock_state']['BASE']} A={k['clock_state']['SIGNAL_A']} B={k['clock_state']['SIGNAL_B']} GATE={k['clock_state']['GATE']}",frame_text(d,k),'']
 return '\n'.join(out).rstrip()+'\n'
def event(k): return bool(k.get('event')) or k['pose_rig']['gate_state'] in {'FREEZE_B','RELEASE_B'}
def bridge_frames(d,a,b):
 spec=a.get('bridge_to_next') or {}; n=int(spec.get('frames',0))
 if n<=0 or event(a) or event(b): return []
 if a['support_contact'].split('_RECENTERING')[0]!=b['support_contact'].split('_RECENTERING')[0]: return []
 out=[]
 for i in range(1,n+1):
  t=ease(i/(n+1),spec.get('easing','LINEAR')); j=interp_joints(hydrate_joints(d,a),hydrate_joints(d,b),t,spec.get('arc_bias',[0,0])); out.append(frame_text(d,a,j,gate=a['pose_rig']['gate_state']))
 return out
def sequence(d):
 seq=[]; keys=d['keys']
 for i,k in enumerate(keys):
  seq += [{'label':k['key_id'],'kind':'AUTHORED_HOLD','text':frame_text(d,k)} for _ in range(HOLD[k['timing_class']])]
  nxt=keys[(i+1)%len(keys)]
  seq += [{'label':f"{k['key_id']}~{nxt['key_id']}:{n}",'kind':'CONNECTIVE_ARC','text':txt} for n,txt in enumerate(bridge_frames(d,k,nxt),1)]
 return seq
def font(size):
 for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','DejaVuSansMono.ttf'):
  try:return ImageFont.truetype(p,size)
  except Exception:pass
 return ImageFont.load_default()
def png(text,path):
 im=Image.new('RGB',(960,540),'black'); dr=ImageDraw.Draw(im); dr.text((20,14),'SCOPED FREEZE / RELEASE  •  ABSTRACT ASCII RIG',fill='white',font=font(17)); dr.multiline_text((20,48),text,fill='white',font=font(20),spacing=0); im.save(path)
def render(d):
 seq=sequence(d); allf=seq*int(d['compile'].get('loop_repetitions',1))
 with tempfile.TemporaryDirectory(prefix='akv2timing006-') as td:
  td=Path(td)
  for n,item in enumerate(allf):png(item['text'],td/f'frame-{n:04d}.png')
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),'-i',str(td/'frame-%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','30','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),'-i',str(td/'frame-%04d.png'),'-vf','fps=12,scale=720:-1:flags=lanczos','-loop','0',str(GIF)],check=True)
 return seq,allf
def esc(s):return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def html_page(d,s,b64):
 p=json.dumps(d,indent=2,sort_keys=True)
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Timing 006 — Scoped Freeze / Release Repair</title><style>:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1180px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:82ch;line-height:1.45}}</style></head><body><h1>Scoped Freeze / Release — visible-performance repair</h1><p class="note">Successor to the preserved negative fixture. Same Robot / Nuclear Throne evidence family, no source art. The right local clock freezes at a high silhouette while the left arm and planted-body counterweight continue; release pays phase debt through snap, overshoot, rebound, secondary lag, and restack.</p><nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button></nav><section id="ascii" role="tabpanel"><pre>{esc(s)}</pre></section><section id="json" role="tabpanel" hidden><pre>{esc(p)}</pre></section><section id="video" role="tabpanel" hidden><video controls autoplay muted loop playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video><p class="note">MP4 compiled solely from the abstract ASCII rig, authored holds, and explicit deterministic curved bridge instructions. Event boundaries hard-cut; no source pixels.</p></section><script>const t=[...document.querySelectorAll('button[data-view]')],p=[...document.querySelectorAll('section[role=tabpanel]')];for(const x of t)x.addEventListener('click',()=>{{for(const b of t)b.setAttribute('aria-selected',b===x?'true':'false');for(const y of p)y.hidden=y.id!==x.dataset.view;}});</script></body></html>'''
def main():
 d=json.loads(MOTION.read_text()); s=contact_sheet(d); CONTACT.write_text(s); seq,allf=render(d); media=MP4.read_bytes(); ms=sha(media); sh=sha(s.encode()); d['ascii_sheet_sha256']=sh; d['compile'].update(media_sha256=ms,media_bytes=len(media),semantic_frames_per_loop=len(seq),video_frames_total=len(allf),authored_hold_frames_per_loop=sum(HOLD[k['timing_class']] for k in d['keys']),connective_frames_per_loop=sum(x['kind']=='CONNECTIVE_ARC' for x in seq)); MOTION.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n'); HTML.write_text(html_page(d,s,base64.b64encode(media).decode()))
 m={'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':d['experiment_id'],'lane':'timing','revises':d['revises'],'negative_fixture':d['negative_fixture'],'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'ascii_surface':'real preformatted DOM text','ligatures_disabled':True,'whitespace_preserved':True,'video_required':True,'video_source':'abstract_ascii_rig_only','video_packaging':f'embedded MP4 data URI in {SLUG}.motion.html','media_sha256':ms,'media_bytes':len(media),'source_art_embedded':False,'backward_compatible':True,'motion_dungeon':{'authored_ascii_keys':len(d['keys']),'explicit_holds':True,'deterministic_connective_motion':True,'connector_semantics_fail_closed':True,'curved_authored_bridges':True,'ascii_only_frame_render':True,'fps':d['compile']['fps'],'authored_hold_frames_per_loop':d['compile']['authored_hold_frames_per_loop'],'connective_frames_per_loop':d['compile']['connective_frames_per_loop'],'semantic_frames_per_loop':len(seq),'loop_repetitions':d['compile']['loop_repetitions'],'video_frames_total':len(allf)},'source':{'site':d['source']['site'],'asset_id':d['source']['asset_id'],'page_url':d['source']['page_url'],'raw_sha256':d['source']['raw_sha256'],'whole_sheet_inspected':True,'source_timing_available':False,'evidence_reused_from_negative_fixture':True},'evaluation':d['evaluation'],'files':['build.py','contact-sheet.txt','manifest.json','motion.json','receipt.json',f'{SLUG}.motion.html'],'reconstruction':'python3 build.py','contract_test':'python3 tools/test_ascii_kinesis_swarm_contract_v2.py','correction_hooks':d['correction_hooks']}; MANIFEST.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
 r={'schema':'ascii-kinesis.v2-receipt','experiment_id':d['experiment_id'],'status':'RENDERED_AWAITING_REPO_VERIFICATION','repo_path':f"experiments/ascii-kinesis/{d['experiment_id']}/",'revises':d['revises'],'negative_fixture':d['negative_fixture'],'source':d['source'],'rights_note':d['source']['rights_note'],'observation_inference_split':{'OBSERVED':d['source']['observed'],'INFERRED':'All decisive-key timing, authored clock phases, freeze/release placement, COM/support performance, bridge arcs, overshoot/lag, and cadence in this successor.','UNKNOWN':d['source']['unknown']},'key_timings':[{'key_id':k['key_id'],'name':k['name'],'timing_class':k['timing_class'],'timing_provenance':k['timing_provenance']} for k in d['keys']],'media_sha256':ms,'media_bytes':len(media),'ascii_sheet_sha256':sh,'evaluation':d['evaluation'],'skill_mutation':d['skill_mutation'],'reconstruction':'python3 build.py','contract_test':'PENDING_EXTERNAL_RUN','repo_readback':'PENDING','issue_343_receipt':'PENDING','correction_hooks':d['correction_hooks']}; RECEIPT.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n'); print(json.dumps({'experiment_id':d['experiment_id'],'media_sha256':ms,'media_bytes':len(media),'ascii_sheet_sha256':sh,'semantic_frames_per_loop':len(seq),'video_frames_total':len(allf),'gif_bytes':GIF.stat().st_size},sort_keys=True))
if __name__=='__main__':main()
