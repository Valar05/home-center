#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'; SLUG='scoped-freeze-release'
MP4=HERE/f'{SLUG}.mp4'; HTML=HERE/f'{SLUG}.motion.html'; MANIFEST=HERE/'manifest.json'; RECEIPT=HERE/'receipt.json'
W,H=49,19; HOLD={'ONES':1,'TWOS':2,'FOURS':4}
LINKS=[('root','mast'),('mast','head'),('mast','left_pivot'),('left_pivot','left_tip'),('mast','right_pivot'),('right_pivot','right_tip')]

def sha(b): return hashlib.sha256(b).hexdigest()
def lerp(a,b,t=.5): return [round(a[0]+(b[0]-a[0])*t),round(a[1]+(b[1]-a[1])*t)]
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

def ascii_frame(k,joints=None):
 j={n:list(v) for n,v in (joints or k['pose_rig']['joints']).items()}; g=[[' ']*W for _ in range(H)]
 def put(x,y,ch):
  if 0<=x<W and 0<=y<H:g[y][x]=ch
 for a,b in LINKS:
  for x,y in bres(j[a],j[b])[1:-1]:
   if g[y][x]==' ':put(x,y,glyph(j[a],j[b]))
 for n,(x,y) in j.items(): put(x,y,{'root':'@','mast':'+','head':'O','left_pivot':'o','right_pivot':'o','left_tip':'A','right_tip':'B'}.get(n,'o'))
 rx,ry=j['root']
 for x in range(rx-7,rx+8):put(x,ry+1,'=')
 put(j['head'][0],2,{'OPEN':'g','FREEZE_B':'F','RELEASE_B':'R'}[k['pose_rig']['gate_state']])
 return '\n'.join(''.join(r).rstrip() for r in g)

def sheet(d):
 out=[]
 for k in d['keys']:
  out.append(f"[{k['key_id']}] {k['name']} | pose/rig={k['pose_rig']['rig_id']} | support/contact={k['support_contact']} | timing={k['timing_class']} {k['timing_provenance']}\nroot/motion-arc: {k['motion_arc_root_note']}\ncausal role: {k['causal_role']}\nclocks: BASE={k['clock_state']['BASE']} A={k['clock_state']['SIGNAL_A']} B={k['clock_state']['SIGNAL_B']} GATE={k['clock_state']['GATE']}\n"+ascii_frame(k))
 return '\n\n'.join(out)
def event(k): return bool(k.get('event')) or k['pose_rig']['gate_state'] in {'FREEZE_B','RELEASE_B'}
def connect_ok(a,b): return not event(a) and not event(b) and a['support_contact']==b['support_contact'] and a['pose_rig']['gate_state']==b['pose_rig']['gate_state']
def connector(a,b):
 j={n:list(v) for n,v in a['pose_rig']['joints'].items()}
 for n in ('left_tip','right_tip'):j[n]=lerp(a['pose_rig']['joints'][n],b['pose_rig']['joints'][n])
 return ascii_frame(a,j)
def png(text,path,label):
 im=Image.new('RGB',(768,432),'black'); d=ImageDraw.Draw(im)
 try:f=ImageFont.truetype('DejaVuSansMono.ttf',18)
 except Exception:f=ImageFont.load_default()
 d.text((20,14),label,fill='white',font=f); d.multiline_text((20,48),text,fill='white',font=f,spacing=1); im.save(path)
def video(d):
 seq=[]; con=0
 for i,k in enumerate(d['keys']):
  for _ in range(HOLD[k['timing_class']]):seq.append((k['key_id'],ascii_frame(k),'AUTHORED_HOLD'))
  if i+1<len(d['keys']) and connect_ok(k,d['keys'][i+1]):seq.append((k['key_id']+'~'+d['keys'][i+1]['key_id'],connector(k,d['keys'][i+1]),'CONNECTIVE')); con+=1
 allf=seq*int(d['compile']['loop_repetitions'])
 with tempfile.TemporaryDirectory(prefix='akv2timing-') as td:
  td=Path(td)
  for n,(lab,txt,kind) in enumerate(allf):png(txt,td/f'frame-{n:04d}.png',f'{lab} | {kind}')
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),'-i',str(td/'frame-%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','34','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
 return seq,con
def esc(s):return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def page(d,s,b64):
 p=json.dumps(d,indent=2,sort_keys=True)
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Timing 001 — Scoped Freeze / Release</title><style>:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1100px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:76ch;line-height:1.45}}</style></head><body><h1>Scoped Freeze / Release Clock Grammar</h1><p class="note">Abstract generic ASCII rig. Source sprites are evidence only and are not embedded. A scoped freeze pauses SIGNAL_B while SIGNAL_A and BASE retain authority and phase.</p><nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button></nav><section id="ascii" role="tabpanel"><pre>{esc(s)}</pre></section><section id="json" role="tabpanel" hidden><pre>{esc(p)}</pre></section><section id="video" role="tabpanel" hidden><video controls loop playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video><p class="note">MP4 compiled only from the abstract rig, generated ASCII frames, explicit holds, and fail-closed local-tip connectors.</p></section><script>const t=[...document.querySelectorAll('button[data-view]')],p=[...document.querySelectorAll('section[role=tabpanel]')];for(const x of t)x.addEventListener('click',()=>{{for(const b of t)b.setAttribute('aria-selected',b===x?'true':'false');for(const y of p)y.hidden=y.id!==x.dataset.view;}});</script></body></html>'''

def main():
 d=json.loads(MOTION.read_text()); seq,con=video(d); media=MP4.read_bytes(); ms=sha(media); s=sheet(d)
 d['ascii_sheet_sha256']=sha(s.encode()); d['compile'].update(media_sha256=ms,media_bytes=len(media),connective_frames_per_loop=con,semantic_frames_per_loop=len(seq),video_frames_total=len(seq)*d['compile']['loop_repetitions']); MOTION.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n')
 HTML.write_text(page(d,s,base64.b64encode(media).decode()))
 m={'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':d['experiment_id'],'lane':'timing','primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'ascii_surface':'real preformatted DOM text','ligatures_disabled':True,'whitespace_preserved':True,'video_required':True,'video_source':'abstract_ascii_rig_only','video_packaging':f'embedded MP4 data URI in {SLUG}.motion.html','media_sha256':ms,'media_bytes':len(media),'source_art_embedded':False,'backward_compatible':True,'motion_dungeon':{'authored_ascii_keys':len(d['keys']),'explicit_holds':True,'deterministic_connective_motion':True,'connector_semantics_fail_closed':True,'ascii_only_frame_render':True,'fps':d['compile']['fps'],'authored_hold_frames_per_loop':d['compile']['authored_hold_frames_per_loop'],'connective_frames_per_loop':con,'semantic_frames_per_loop':len(seq),'loop_repetitions':d['compile']['loop_repetitions'],'video_frames_total':len(seq)*d['compile']['loop_repetitions']},'source':{'site':d['source']['site'],'asset_id':d['source']['asset_id'],'page_url':d['source']['page_url'],'raw_sha256':d['source']['raw_sha256'],'whole_sheet_inspected':True,'source_timing_available':False},'files':['build.py','manifest.json','motion.json','receipt.json',f'{SLUG}.motion.html'],'reconstruction':'python3 build.py','contract_test':'python3 tools/test_ascii_kinesis_swarm_contract_v2.py','correction_hooks':d['correction_hooks']}; MANIFEST.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
 r={'schema':'ascii-kinesis.v2-receipt','experiment_id':d['experiment_id'],'status':'RENDERED_AWAITING_REPO_VERIFICATION','repo_path':f"experiments/ascii-kinesis/{d['experiment_id']}/",'source':d['source'],'rights_note':d['source']['rights_note'],'observation_inference_split':{'OBSERVED':d['source']['observed'],'INFERRED':'All decisive-key timings, authored clock phases, freeze/release placement, connectors, and cadence.','UNKNOWN':d['source']['unknown']},'key_timings':[{'key_id':k['key_id'],'name':k['name'],'timing_class':k['timing_class'],'timing_provenance':k['timing_provenance']} for k in d['keys']],'media_sha256':ms,'media_bytes':len(media),'skill_mutation':{'performed':False,'reason':'Exercises existing PoseLab v1.10 scoped FREEZE_UNTIL_RELEASE; no new reusable rule earned.'},'reconstruction':'python3 build.py','contract_test':'PENDING_EXTERNAL_RUN','repo_readback':'PENDING','correction_hooks':d['correction_hooks']}; RECEIPT.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'media_sha256':ms,'media_bytes':len(media),'ascii_sheet_sha256':d['ascii_sheet_sha256'],'semantic_frames_per_loop':len(seq),'connective_frames_per_loop':con,'video_frames_total':d['compile']['video_frames_total']},sort_keys=True))
if __name__=='__main__':main()
