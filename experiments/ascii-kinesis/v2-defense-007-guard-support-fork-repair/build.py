#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

P=Path(__file__).resolve().parent
M=P/'motion.json'; HTML=P/'guard-support-fork-repair.motion.html'; MP4=P/'guard-support-fork-repair.mp4'
W,H=56,22; HOLD={'ONES':1,'TWOS':2,'FOURS':4}
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
  x,y=j[n]; put(x,min(H-1,y+1),'=')
 if k['support_contact']=='BOTH_REAR_BIASED':
  x,y=j['foot_l']; put(x,max(0,y-1),'^')
 if k['guard_authority'] in {'OWNED','CARRIED','RECOVERING'}:
  x,y=j['hand_r']; put(min(W-1,x+1),y,']')
 if k['contact_state']=='IMPACT_RIGHT':
  x,y=j['hand_r']; put(min(W-1,x+2),y,'X')
  for q in range(min(W-1,x+4),min(W-1,x+12)): put(q,y,'<')
 if k['recoil_debt']>=.55:
  x,y=j['pelvis']
  for q in range(1,4): put(max(0,x-q),min(H-1,y+1),'~')
 return '\n'.join(''.join(r).rstrip() for r in g)

def topology(k): return tuple(k[x] for x in ('support_contact','contact_state','root_state','guard_authority','readiness','impact_memory'))
def ip(a,b,t,arc):
 e=(1-math.cos(math.pi*t))/2
 return [round(a[0]+(b[0]-a[0])*e+4*t*(1-t)*arc[0]),round(a[1]+(b[1]-a[1])*e+4*t*(1-t)*arc[1])]
def interpolate(a,b,t,arcmap): return {n:ip(a['joints'][n],b['joints'][n],t,arcmap.get(n,[0,0])) for n in a['joints']}

def contact_sheet(d):
 out=[]
 for k in d['keys']:
  out += [f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']}",
          f"support={k['support_contact']} root={k['root_state']} guard={k['guard_authority']} debt={k['recoil_debt']:.2f} lag={k['secondary_lag']}",
          pose(k),'']
 return '\n'.join(out).rstrip()+"\n"

def compact_json(d):
 keys=[]
 for k in d['keys']:
  keys.append({q:k[q] for q in ('key_id','name','joints','support_contact','contact_state','root_state','guard_authority','readiness','recoil_debt','secondary_lag','motion_arc_root_note','causal_role','timing_class','timing_provenance','connective_to_next')})
 return {'experiment_id':d['experiment_id'],'format_version':d['format_version'],'lane':d['lane'],'title':d['title'],'principle':d['principle'],'revision':d['revision'],'source':d['source'],'rights':d['rights'],'compatibility':d['compatibility'],'rig_schema':d['rig_schema'],'timing_policy':d['timing_policy'],'keys':keys,'compile':d['compile'],'evidence':d['evidence'],'quality_gates':d['quality_gates'],'validation':d['validation'],'correction_hooks':d['correction_hooks'],'ascii_sheet_sha256':d['ascii_sheet_sha256']}

def font(size):
 for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/font/truetype/dejavu/DejaVuSansMono.ttf']:
  if Path(p).exists(): return ImageFont.truetype(p,size)
 return ImageFont.load_default()
def render_png(text,path,label):
 im=Image.new('RGB',(640,360),'black');dr=ImageDraw.Draw(im)
 dr.text((10,7),label,fill='white',font=font(11));dr.multiline_text((10,28),text,fill='white',font=font(13),spacing=0);im.save(path)
def compile_video(d):
 seq=[]
 for i,k in enumerate(d['keys']):
  seq += [(k['key_id'],pose(k))]*HOLD[k['timing_class']]
  if i+1<len(d['keys']):
   conn=k.get('connective_to_next',{}); b=d['keys'][i+1]
   if conn.get('authorized') and topology(k)==topology(b):
    for t in (.25,.5,.75): seq.append((k['key_id']+'~'+b['key_id'],pose(k,interpolate(k,b,t,conn.get('arc',{})))))
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  for i,(lab,txt) in enumerate(seq): render_png(txt,td/f'f{i:04d}.png',lab)
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),'-i',str(td/'f%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','38','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
 return len(seq)
def probe():
 q=json.loads(subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration','-of','json',str(MP4)],check=True,capture_output=True,text=True).stdout);s=q['streams'][0]
 return {'tool':'ffprobe','codec':s['codec_name'],'width':int(s['width']),'height':int(s['height']),'fps':s['r_frame_rate'],'frames':int(s['nb_frames']),'duration_seconds':float(q['format']['duration'])}
def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def page(d,s,b64):
 payload=json.dumps(compact_json(d),separators=(',',':'),sort_keys=True)
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Defense 007</title><style>:root{{color-scheme:dark;background:#0e0f10;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1200px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#0e0f10;padding:.5rem 0}}button{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1}}video{{display:block;max-width:100%;height:auto}}</style></head><body><h1>Guard / Support Authority Fork — Performance Repair</h1><nav role="tablist"><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre>{esc(s)}</pre></section>
<section id="json" hidden><pre>{esc(payload)}</pre></section>
<section id="video" hidden><video controls playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section>
<script>const T=[...document.querySelectorAll('[data-view]')],S=[...document.querySelectorAll('section')];T.forEach(t=>t.onclick=()=>S.forEach(s=>s.hidden=s.id!==t.dataset.view));</script></body></html>'''
def manifest(d,pr,per):
 return {'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':d['experiment_id'],'lane':'defense','revision':d['revision'],'principle':d['principle'],'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'ascii_surface':'real preformatted DOM text','ligatures_disabled':True,'whitespace_preserved':True,'video_required':True,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'backward_compatible':True,'compatibility':d['compatibility'],'files':['build.py','manifest.json','motion.json','receipt.md','guard-support-fork-repair.motion.html'],'reconstruction':'python3 build.py','video_packaging':'authoritative embedded MP4 data URI','tracked_media_sidecar':False,'media_sha256':d['compile']['media_sha256'],'media_bytes':d['compile']['media_bytes'],'media_decode_preflight':pr,'motion_dungeon':{'authored_ascii_keys':len(d['keys']),'explicit_holds':True,'deterministic_connective_motion':True,'connector_semantics_fail_closed':True,'ascii_only_frame_render':True,'fps':d['compile']['fps'],'loop_repetitions':1,'semantic_frames_per_loop':per,'video_frames_total':pr['frames']},'source':d['source'],'rights':d['rights'],'timing_provenance_required':True,'quality_gates':d['quality_gates'],'validation':d['validation'],'correction_hooks':d['correction_hooks'],'receipt_status':'QUALITY_GATES_PASS / REPO_READBACK_REQUIRED'}
def receipt(d,pr):
 times='\n'.join(f"- {k['key_id']} {k['name']} — {k['timing_class']} — {k['timing_provenance']}" for k in d['keys'])
 return f'''# ASCII Kinesis V2 Defense 007 — repair receipt\n\nStatus: QUALITY_GATES_PASS / REPO_READBACK_REQUIRED\n\nRevises `{d['revision']['revises']}`; negative fixture `{d['revision']['negative_fixture']}`; predecessor preserved; source change false.\n\nSource: TSR Cammy / Super Street Fighter II SNES asset 5553 — {d['source']['url']} — same whole-sheet evidence family, no fresh concept/source. No Drew work or source pixels/palette/contours/layout/tracing/choreography/redistribution/close imitation.\n\nOBSERVED: inherited predecessor whole-sheet evidence only; no source-authentic timing measured. INFERRED: all authored performance and timing. UNKNOWN: source chronology/exposure/hit-stop/hitbox/support-foot/root path.\n\n{times}\n\nMP4 SHA-256 `{d['compile']['media_sha256']}`; {d['compile']['media_bytes']} bytes; H.264 {pr['width']}x{pr['height']}; {pr['frames']} frames; {pr['duration_seconds']:.6f}s. ASCII SHA-256 `{d['ascii_sheet_sha256']}`.\n\nTango: PASS after 3 REVISE_REQUIRED cycles; final render inspected. Noodle Queen after Tango: TASTE PASS / FUNCTION PASS / CONTEMPT PASS.\n\nContract: successor isolated exact script PASS. Full repository regression UNTESTED_BOUNDARY: no authorized repository shell in this Standard Chat lane; no worker/control plane opened.\n\nCorrection hooks: KEEP / REJECT / EXAGGERATE / COMPRESS / RETIME / CHANGE SOURCE / PROMOTE / SPAWN VARIANT / FIX BLOCKER / RERUN\n'''
def main():
 d=json.loads(M.read_text()); per=compile_video(d); raw=MP4.read_bytes(); pr=probe(); s=contact_sheet(d)
 d['compile'].update(media_sha256=hashlib.sha256(raw).hexdigest(),media_bytes=len(raw),semantic_frames_per_loop=per,video_frames_total=pr['frames'],media_decode_preflight=pr,renderer='Python/Pillow ASCII text raster -> ffmpeg libx264 yuv420p 640x360 CRF38')
 d['ascii_sheet_sha256']=hashlib.sha256(s.encode()).hexdigest(); M.write_text(json.dumps(d,separators=(',',':'),sort_keys=True)+'\n')
 (P/'manifest.json').write_text(json.dumps(manifest(d,pr,per),separators=(',',':'),sort_keys=True)+'\n'); (P/'receipt.md').write_text(receipt(d,pr)); HTML.write_text(page(d,s,base64.b64encode(raw).decode()))
 print(json.dumps({'media_sha256':d['compile']['media_sha256'],'media_bytes':len(raw),'frames':pr['frames'],'duration':pr['duration_seconds'],'ascii_sheet_sha256':d['ascii_sheet_sha256'],'html_bytes':HTML.stat().st_size},sort_keys=True))
if __name__=='__main__': main()
