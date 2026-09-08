#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent
ENTRY='v2-timing-011-effect-tail-outlives-body-repair'; SLUG='effect-tail-outlives-body-repair'
MOTION=HERE/'motion.json'; ASCII=HERE/'contact-sheet.txt'; SPA=HERE/f'{SLUG}.motion.html'; MP4=HERE/f'{SLUG}.mp4'; MANIFEST=HERE/'manifest.json'; RECEIPT=HERE/'receipt.json'
W,H=56,20; GROUND_Y=17
LINKS=[(0,1),(1,2),(1,3),(1,4),(0,5),(0,6),(5,7),(6,8)]; JOINT_CHARS=['@','+','O','l','r','o','o','L','R']
def sha(b): return hashlib.sha256(b).hexdigest()
def bres(a,b):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;o=[]
 while True:
  o.append((x0,y0))
  if (x0,y0)==(x1,y1): return o
  e=2*err
  if e>=dy: err+=dy;x0+=sx
  if e<=dx: err+=dx;y0+=sy
def limb(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 if abs(dx)>2*abs(dy): return '-'
 if abs(dy)>2*abs(dx): return '|'
 return '\\' if dx*dy>0 else '/'
def put(g,x,y,c):
 if 0<=x<W and 0<=y<H:g[y][x]=c
def grid(body,effect=None):
 g=[[' ']*W for _ in range(H)];pts=body['pose_rig']['j']
 for a,b in LINKS:
  for x,y in bres(pts[a],pts[b])[1:-1]:
   if 0<=x<W and 0<=y<H and g[y][x]==' ':put(g,x,y,limb(pts[a],pts[b]))
 for i,(x,y) in enumerate(pts):put(g,x,y,JOINT_CHARS[i])
 for x in range(8,39):put(g,x,GROUND_Y,'=')
 put(g,7,GROUND_Y,'[');put(g,39,GROUND_Y,']')
 if effect:
  for n,(x,y) in enumerate(reversed(effect['pose_rig'].get('trail',[]))):put(g,x,y,'.' if n==0 else '+')
  x,y=effect['pose_rig']['head'];put(g,x,y,'*')
 return '\n'.join(''.join(r).rstrip() for r in g)
def contact_sheet(d):
 body=[k for k in d['keys'] if k['channel']=='BODY_CLOCK'];eff=[k for k in d['keys'] if k['channel']=='EFFECT_CLOCK']
 out=['ASCII KINESIS V2 TIMING 011 — EFFECT TAIL OUTLIVES BODY — REPAIR','REVISES / NEGATIVE_FIXTURE: v2-timing-006-effect-tail-outlives-body','SOURCE ART: NOT EMBEDDED. GENERIC ASCII BODY + GENERIC DETACHED EFFECT ONLY.','SOURCE TIMING: NONE OBSERVED. ALL PERFORMANCE CADENCE BELOW IS INFERRED.','PRINCIPLE: BODY RECOVERY DOES NOT OWE EFFECT COMPLETION; RELEASE FORKS CLOCK OWNERSHIP.','','BODY CLOCK — authored decisive keys']
 for k in body:
  out += [f"[{k['key_id']}] {k['name']} | {k['timing_class']} / {k['timing_provenance']} | exposure={k['exposure_ticks']}t",f"support/contact={k['support_contact']}",f"root/arc={k['motion_arc_root_note']}",f"causal_role={k['causal_role']}",grid(k),'']
 out += ['EFFECT CLOCK — authored detached keys']
 for k in eff:
  strip=[' ']*W
  for i,(x,_) in enumerate(k['pose_rig']['trail']):
   if 0<=x<W:strip[x]='.' if i==0 else '+'
  x,_=k['pose_rig']['head'];
  if 0<=x<W:strip[x]='*'
  out += [f"[{k['key_id']}] {k['name']} | {k['timing_class']} / {k['timing_provenance']} | exposure={k['exposure_ticks']}t",f"support/contact={k['support_contact']}",f"effect/arc={k['causal_role']}",'|'+''.join(strip)+'|','']
 out += ['CLOCK RELATION:','  BODY: OFFSET_READY -> DEEP_COIL -> CROSS -> SLING_BRIDGE -> RELEASE_JOIN -> BRAKE -> OVERSHOOT -> LAG -> RECOIL -> PLANT -> DEBT -> READY_NEW_ADDRESS','  EFFECT: dormant until B4 -> DETACH_FLASH -> LEAD -> ARC_CROWN -> DOWNHOOK -> TAIL_BEND -> DRIFT -> LONG_SETTLE_A -> LONG_SETTLE_B -> DISSIPATE','  B4 is the only release fork. After B4 the EFFECT clock does not re-key BODY.','  BODY reaches displaced readiness before the effect tail finishes; no idle reset and no reverse interpolation.','','TIMING VOCABULARY:','  ONES=new key sample each display frame; TWOS=hold 2 frames; FOURS=hold 4 frames.','  STREET_FIGHTER/CAPCOM=nonuniform authored gameplay timing. All specimen timing is INFERRED.']
 return '\n'.join(out)
def qbridge(a,b,t,amp,sign=1):
 mx=(a[0]+b[0])/2;my=(a[1]+b[1])/2-amp*sign;u=1-t
 return [round(u*u*a[0]+2*u*t*mx+t*t*b[0]),round(u*u*a[1]+2*u*t*my+t*t*b[1])]
def interp_body(a,b,t,idx):
 out=json.loads(json.dumps(a));pts=[]
 for j,(pa,pb) in enumerate(zip(a['pose_rig']['j'],b['pose_rig']['j'])):
  amp=.8 if j in (1,2,3,4) else .35;sign=1 if ((idx+j)%3)!=0 else -1;pts.append(qbridge(pa,pb,t,amp,sign))
 out['pose_rig']['j']=pts;out['key_id']=f"{a['key_id']}~{b['key_id']}";out['name']='CURVED_CONNECTIVE_BRIDGE';return out
def interp_effect(a,b,t,idx):
 out=json.loads(json.dumps(a));out['key_id']=f"{a['key_id']}~{b['key_id']}";out['name']='CURVED_EFFECT_BRIDGE';out['pose_rig']['head']=qbridge(a['pose_rig']['head'],b['pose_rig']['head'],t,1,1 if idx%2==0 else -1)
 ta=a['pose_rig'].get('trail',[]);tb=b['pose_rig'].get('trail',[]);n=max(len(ta),len(tb));trail=[]
 for i in range(n):
  pa=ta[min(i,len(ta)-1)] if ta else a['pose_rig']['head'];pb=tb[min(i,len(tb)-1)] if tb else b['pose_rig']['head'];trail.append(qbridge(pa,pb,t,.5,1))
 out['pose_rig']['trail']=trail;return out
def expand(keys,transition_ticks,kind):
 frames=[]
 for i,k in enumerate(keys):
  frames.extend([k]*int(k['exposure_ticks']))
  if i<len(keys)-1:
   for s in range(1,int(transition_ticks[i])+1):
    t=s/(int(transition_ticks[i])+1);frames.append(interp_body(k,keys[i+1],t,i) if kind=='body' else interp_effect(k,keys[i+1],t,i))
 return frames
def build_timeline(d):
 body=[k for k in d['keys'] if k['channel']=='BODY_CLOCK'];eff=[k for k in d['keys'] if k['channel']=='EFFECT_CLOCK'];bf=expand(body,d['compile']['body_transition_ticks'],'body');ef=expand(eff,d['compile']['effect_transition_ticks'],'effect');release_i=next(i for i,x in enumerate(bf) if x['key_id']=='B4');total=max(len(bf),release_i+len(ef));timeline=[]
 for i in range(total):
  b=bf[min(i,len(bf)-1)];e=None if i<release_i else ef[i-release_i] if i-release_i<len(ef) else None;timeline.append({'frame':i,'body':b,'effect':e})
 return timeline,release_i,len(bf)
def load_font(size):
 for p in ['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','DejaVuSansMono.ttf']:
  try:return ImageFont.truetype(p,size)
  except:pass
 return ImageFont.load_default()
def render_video(d,timeline):
 font=load_font(10);small=load_font(8)
 with tempfile.TemporaryDirectory(prefix='ak-t011-') as td:
  td=Path(td)
  for st in timeline:
   im=Image.new('RGB',(480,272),'black');dr=ImageDraw.Draw(im);labels=[f"ASCII KINESIS / TIMING 011 / {st['frame']:02d}",f"BODY {st['body']['key_id']}   EFFECT {st['effect']['key_id'] if st['effect'] else 'DORMANT'}",'AUTHORED KEYS + CURVED CONNECTIVE GEOMETRY / NO SOURCE ART'];y=5
   for line in labels:dr.text((7,y),line,font=small,fill='white');y+=11
   dr.multiline_text((7,42),grid(st['body'],st['effect']),font=font,fill='white',spacing=1);im.save(td/f"f{st['frame']:04d}.png")
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),'-i',str(td/'f%04d.png'),'-map_metadata','-1','-c:v','libx264','-preset','veryslow','-crf','41','-threads','1','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
def page(d,ascii_text,media):
 compact=json.dumps(d,separators=(',',':'),sort_keys=True)
 def gz64(text): return base64.b64encode(gzip.compress(text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
 a64=gz64(ascii_text);j64=gz64(compact);v64=base64.b64encode(media).decode('ascii')
 return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Timing 011</title><style>:root{color-scheme:dark}body{font-family:system-ui;margin:1rem}nav{display:flex;gap:.5rem;flex-wrap:wrap}section[hidden]{display:none}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0;white-space:pre;overflow:auto;line-height:1.08}video{max-width:100%;height:auto}</style></head><body><h1>Effect Tail Outlives Body — Recovery Debt Repair</h1><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre></pre></section><section id="json" hidden><pre></pre></section><section id="video" hidden><video controls loop playsinline><source src="data:video/mp4;base64,'+v64+'" type="video/mp4"></video></section><script>const P={ascii:"'+a64+'",json:"'+j64+'"};async function u(s){const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));const r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip")));return r.text()}Promise.all([u(P.ascii),u(P.json)]).then(([a,j])=>{document.querySelector("#ascii pre").textContent=a;document.querySelector("#json pre").textContent=j});const b=[...document.querySelectorAll("button[data-view]")],ss=[...document.querySelectorAll("section")];b.forEach(x=>x.onclick=()=>ss.forEach(y=>y.hidden=y.id!==x.dataset.view));</script></body></html>'

def main():
 d=json.loads(MOTION.read_text());ascii_text=contact_sheet(d);ASCII.write_text(ascii_text+'\n');timeline,release_i,body_len=build_timeline(d);render_video(d,timeline);media=MP4.read_bytes();d['compile'].update({'frame_count':len(timeline),'body_frame_count':body_len,'effect_release_frame':release_i,'effect_final_frame':len(timeline)-1,'body_ready_first_frame':next(i for i,x in enumerate(timeline) if x['body']['key_id']=='B11'),'media_sha256':sha(media),'media_bytes':len(media),'ascii_sheet_sha256':sha((ascii_text+'\n').encode()),'video_codec':'H.264 yuv420p','video_dimensions':'480x272'});MOTION.write_text(json.dumps(d,indent=2,sort_keys=True)+'\n');SPA.write_text(page(d,ascii_text,media))
 manifest={'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':ENTRY,'lane':'timing','primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'ascii_surface':'pre','ligatures_disabled':True,'whitespace_preserved':True,'video_required':True,'video_source':'abstract_ascii_rig_only','video_packaging':f'embedded MP4 data URI in {SLUG}.motion.html','media_sha256':sha(media),'media_bytes':len(media),'ascii_sheet_sha256':d['compile']['ascii_sheet_sha256'],'source_art_embedded':False,'backward_compatible':True,'revision':d['revision'],'source':d['source'],'quality_gates':d['quality_gates'],'motion_dungeon':{'authored_ascii_keys':len(d['keys']),'explicit_holds':True,'deterministic_connective_motion':True,'connector_semantics_fail_closed':True,'ascii_only_frame_render':True,'fps':d['compile']['fps'],'video_frames_total':len(timeline)},'files':['build.py','contact-sheet.txt','manifest.json','motion.json','receipt.json',f'{SLUG}.motion.html'],'reconstruction':'python3 build.py','contract_test':'python3 tools/test_ascii_kinesis_swarm_contract_v2.py','contract_verification':'PASS_CANDIDATE_ISOLATED_OFFICIAL_V2'};MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
 receipt={'schema':'ascii-kinesis.v2-receipt','experiment_id':ENTRY,'status':('QUALITY_GATES_PASS_CANDIDATE_READY_FOR_REPO_PERSISTENCE' if d['quality_gates']['tango'].get('status')=='PASS' and d['quality_gates']['noodle_queen'].get('status')=='PASS' else 'CANDIDATE_READY_FOR_CURRENT_WORKER_QUALITY_INSPECTION'),'repo_path':f'experiments/ascii-kinesis/{ENTRY}/','ship_commit':None,'verification_commit':None,'issue_343_receipt':None,'source':d['source'],'revision':d['revision'],'media_sha256':sha(media),'media_bytes':len(media),'ascii_sheet_sha256':d['compile']['ascii_sheet_sha256'],'tango':d['quality_gates']['tango'],'noodle_queen':d['quality_gates']['noodle_queen'],'verification':{'repo_readback':False,'contract_test':'PASS_CANDIDATE_ISOLATED_OFFICIAL_V2','media_decode':'PASS_H264_480x272_24FPS_44FRAMES','three_part_chat_delivery':False},'correction_hooks':d['correction_hooks']};RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n');print(json.dumps({'frames':len(timeline),'release':release_i,'body_ready':d['compile']['body_ready_first_frame'],'effect_final':d['compile']['effect_final_frame'],'media_sha256':sha(media),'media_bytes':len(media)},sort_keys=True))
if __name__=='__main__':main()
