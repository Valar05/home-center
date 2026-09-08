#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, math, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'; SLUG='scoped-sync-grapple-repair'
MP4=HERE/f'{SLUG}.mp4'; GIF=HERE/f'{SLUG}.chat.gif'; HTML=HERE/f'{SLUG}.motion.html'
CONTACT=HERE/'contact-sheet.txt'; MANIFEST=HERE/'manifest.json'; RECEIPT=HERE/'receipt.json'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
def sha(b:bytes)->str:return hashlib.sha256(b).hexdigest()
def bres(a,b):
 x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; e=dx+dy; out=[]
 while True:
  out.append((x0,y0))
  if (x0,y0)==(x1,y1):break
  q=2*e
  if q>=dy:e+=dy;x0+=sx
  if q<=dx:e+=dx;y0+=sy
 return out
def glyph(a,b):
 dx=b[0]-a[0]; dy=b[1]-a[1]
 if abs(dx)>abs(dy)*2:return '-'
 if abs(dy)>abs(dx)*2:return '|'
 return '\\' if dx*dy>0 else '/'
def qpoint(a,b,t,bias=(0,0)):
 c=((a[0]+b[0])/2+bias[0],(a[1]+b[1])/2+bias[1]);u=1-t
 return [round(u*u*a[0]+2*u*t*c[0]+t*t*b[0]),round(u*u*a[1]+2*u*t*c[1]+t*t*b[1])]
def rotate_point(p,c,deg,t):
 ang=math.radians(deg*t); x=p[0]-c[0];y=p[1]-c[1];cs=math.cos(ang);sn=math.sin(ang)
 return [round(c[0]+x*cs-y*sn),round(c[1]+x*sn+y*cs)]
def topo(k):
 return (k['contact_state'],k['custody'],k['support_A'],k['support_B'],k['root_owner'],tuple((a['a'],a['b'],a.get('owner','')) for a in k['anchors']))
def interp_actor(a,b,t,bias):
 return {n:qpoint(a[n],b[n],t,bias if n not in {'foot_l','foot_r'} else (0,0)) for n in a}
def locked_interp(a,b,t,center0,center1,deg):
 c=qpoint(center0,center1,t,(0,0)); out={}
 for actor in ('A','B'):
  sign=1 if actor=='A' else -1
  out[actor]={}
  for n,p in a[actor].items():
   rp=rotate_point(p,center0,deg*sign,t)
   target=b[actor][n]
   out[actor][n]=[round(rp[0]*(1-t)+target[0]*t),round(rp[1]*(1-t)+target[1]*t)]
 return out,c
def support_foot_active(s,side):
 if s in {'BOTH','GROUND'}:return True
 if s=='LEFT':return side=='l'
 if s=='RIGHT':return side=='r'
 return False
def frame_text(d,k,actors=None,shared_center=None,anchors=None):
 W,H=d['rig_schema']['grid']; g=[[' ']*W for _ in range(H)]; actors=actors or {'A':k['A'],'B':k['B']}; sc=k.get('shared_center') if shared_center is None else shared_center; anchors=k['anchors'] if anchors is None else anchors
 def put(x,y,ch):
  if 0<=x<W and 0<=y<H:g[y][x]=ch
 for actor in ('A','B'):
  j=actors[actor]
  for a,b in d['rig_schema']['links']:
   for x,y in bres(j[a],j[b])[1:-1]:
    if 0<=x<W and 0<=y<H and g[y][x]==' ':put(x,y,glyph(j[a],j[b]))
  marks={'head':actor,'pelvis':'@' if actor=='A' else '&','hand_l':'a' if actor=='A' else 'b','hand_r':'a' if actor=='A' else 'b','foot_l':actor,'foot_r':actor,'shoulder_l':'o','shoulder_r':'o','knee_l':'o','knee_r':'o'}
  for n,(x,y) in j.items():put(x,y,marks.get(n,'o'))
 floor=21
 for x in range(W): put(x,floor,'=')
 for actor in ('A','B'):
  s=k['support_A'] if actor=='A' else k['support_B']; j=actors[actor]
  for side in ('l','r'):
   if support_foot_active(s,side):
    x,y=j[f'foot_{side}'];put(x,min(floor,y+1),'^')
 for an in anchors:
  x,y=an['at'];put(x,y,'*')
 if sc:
  cx,cy=sc;put(cx,cy,'X')
  if cx-1>=0: put(cx-1,cy,'>')
  if cx+1<W: put(cx+1,cy,'<')
 put(1,1,'A');put(3,1,'>');put(W-4,1,'<');put(W-2,1,'B')
 return '\n'.join(''.join(r).rstrip() for r in g)
def bridge_frames(d,a,b):
 spec=a.get('bridge_to_next') or {};n=int(spec.get('frames',0))
 if n<=0 or topo(a)!=topo(b):return []
 out=[];mode=spec.get('mode','LOCAL_ARC')
 for i in range(1,n+1):
  t=i/(n+1); t=t*t*(3-2*t)
  if mode=='LOCKED_POLAR' and a.get('shared_center') and b.get('shared_center'):
   ab,c=locked_interp(a,b,t,a['shared_center'],b['shared_center'],float(spec.get('rotation_degrees',0)))
   ans=[]
   for aa,bb in zip(a['anchors'],b['anchors']):
    an=dict(aa);an['at']=qpoint(aa['at'],bb['at'],t,(0,-1));ans.append(an)
    for endpoint in (an['a'],an['b']):
     actor,joint=endpoint.split('.',1);ab[actor][joint]=list(an['at'])
   out.append(frame_text(d,a,ab,c,ans))
  else:
   aa=interp_actor(a['A'],b['A'],t,tuple(spec.get('arc_bias_A',[0,0])))
   bb=interp_actor(a['B'],b['B'],t,tuple(spec.get('arc_bias_B',[0,0])))
   out.append(frame_text(d,a,{'A':aa,'B':bb},None,[]))
 return out
def sequence(d):
 scale=int(d['compile'].get('preview_time_scale',1));seq=[]
 for i,k in enumerate(d['keys']):
  for _ in range(HOLD[k['timing_class']]*scale):seq.append({'kind':'AUTHORED_HOLD','key':k['key_id'],'text':frame_text(d,k)})
  if i+1<len(d['keys']):
   for n,txt in enumerate(bridge_frames(d,k,d['keys'][i+1]),1):
    for _ in range(scale):seq.append({'kind':'CONNECTIVE_ARC','key':f"{k['key_id']}~{d['keys'][i+1]['key_id']}:{n}",'text':txt})
 return seq
def contact_sheet(d):
 out=['ASCII KINESIS V2 CONTACT 007 - SCOPED SYNCHRONIZATION GRAPPLE REPAIR',f"revises: {d['revises']}",f"negative_fixture: {d['negative_fixture']}",'source art: NONE | timing: all INFERRED | 1s/2s/4s => ONES/TWOS/FOURS','legend: A/@/a = carrier head/root/hand | B/&/b = partner | *=anchor | X=shared center | >/< = opposing force path | ^=support','']
 for k in d['keys']:
  out += [f"[{k['key_id']}] {k['name']} | timing={k['timing_class']} | provenance={k['timing_provenance']}",f"contact={k['contact_state']} custody={k['custody']} root_owner={k['root_owner']} support_A={k['support_A']} support_B={k['support_B']}",f"root/arc: {k['motion_arc_root_note']}",f"causal: {k['causal_role']}",frame_text(d,k),'']
 return '\n'.join(out).rstrip()+'\n'
def font(size):
 for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','DejaVuSansMono.ttf'):
  try:return ImageFont.truetype(p,size)
  except:pass
 return ImageFont.load_default()
def png(text,path):
 im=Image.new('RGB',(480,270),'black');dr=ImageDraw.Draw(im);f=font(8);hdr=font(8)
 dr.text((22,14),'SCOPED SYNC GRAPPLE REPAIR - ABSTRACT ASCII RELATIONSHIP RIG',font=hdr,fill='white')
 dr.multiline_text((22,50),text,font=f,fill='white',spacing=0);im.save(path)
def render(d):
 seq=sequence(d);reps=int(d['compile'].get('loop_repetitions',1));frames=seq*reps
 with tempfile.TemporaryDirectory(prefix='akv2contact007-') as td:
  td=Path(td)
  for i,item in enumerate(frames):png(item['text'],td/f'frame-{i:04d}.png')
  cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),'-i',str(td/'frame-%04d.png'),'-map_metadata','-1','-c:v','libx264','-threads','1','-preset','veryslow','-crf','38','-pix_fmt','yuv420p','-movflags','+faststart','-fflags','+bitexact','-flags:v','+bitexact',str(MP4)]
  subprocess.run(cmd,check=True)
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(d['compile']['fps']),'-i',str(td/'frame-%04d.png'),'-vf','fps=12,scale=960:-1:flags=lanczos','-loop','0',str(GIF)],check=True)
 return seq,frames
def spa(d,s,b64):
 j=json.dumps(d,sort_keys=True,separators=(',',':'));esc=lambda x:html.escape(x,quote=False)
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Contact 007 - Scoped Sync Grapple Repair</title><style>:root{{color-scheme:dark;background:#0e0e0e;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1280px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#0e0e0e;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.04}}video{{max-width:100%;height:auto;border:1px solid #555}}</style></head><body><h1>Scoped Synchronization Grapple - repair</h1><nav role="tablist" aria-label="Primary views"><button type="button" data-view="ascii" aria-selected="true">ASCII</button><button type="button" data-view="json" aria-selected="false">JSON</button><button type="button" data-view="video" aria-selected="false">VIDEO</button></nav><section id="ascii"><pre>{esc(s)}</pre></section><section id="json" hidden><pre>{esc(j)}</pre></section><section id="video" hidden><video controls autoplay muted loop playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section><script>const t=[...document.querySelectorAll('button[data-view]')],p=[...document.querySelectorAll('section')];for(const x of t)x.onclick=()=>{{for(const b of t)b.setAttribute('aria-selected',b===x?'true':'false');for(const y of p)y.hidden=y.id!==x.dataset.view;}};</script></body></html>'''
def main():
 d=json.loads(MOTION.read_text());s=contact_sheet(d);CONTACT.write_text(s)
 seq,frames=render(d);media=MP4.read_bytes();ms=sha(media);ss=sha(s.encode())
 d['ascii_sheet_sha256']=ss;d['compile'].update(media_sha256=ms,media_bytes=len(media),semantic_frames_per_loop=len(seq),video_frames_total=len(frames),authored_hold_frames_per_loop=sum(HOLD[k['timing_class']]*d['compile']['preview_time_scale'] for k in d['keys']),connective_frames_per_loop=sum(x['kind']=='CONNECTIVE_ARC' for x in seq))
 MOTION.write_text(json.dumps(d,sort_keys=True,separators=(',',':'))+'\n')
 HTML.write_text(spa(d,s,base64.b64encode(media).decode()))
 m={'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':d['experiment_id'],'lane':'contact','revises':d['revises'],'negative_fixture':d['negative_fixture'],'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'ascii_surface':'real preformatted DOM text','ligatures_disabled':True,'whitespace_preserved':True,'video_required':True,'video_source':'abstract_ascii_rig_only','video_packaging':f'embedded MP4 data URI in {SLUG}.motion.html','media_sha256':ms,'media_bytes':len(media),'source_art_embedded':False,'backward_compatible':True,'motion_dungeon':{'authored_ascii_keys':len(d['keys']),'explicit_holds':True,'deterministic_connective_motion':True,'connector_semantics_fail_closed':True,'curved_authored_bridges':True,'ascii_only_frame_render':True,'fps':d['compile']['fps'],'preview_time_scale':d['compile']['preview_time_scale'],'semantic_frames_per_loop':len(seq),'video_frames_total':len(frames)},'source':{'site':d['source']['site'],'asset_id':d['source']['asset_id'],'page_url':d['source']['page_url'],'raw_sha256':d['source']['raw_sha256'],'whole_sheet_inspected':True,'source_timing_available':False,'evidence_reused_from_negative_fixture':True},'evaluation':d['evaluation'],'files':['build.py','contact-sheet.txt','manifest.json','motion.json','receipt.json',f'{SLUG}.motion.html'],'reconstruction':'python3 build.py','contract_test':'python3 tools/test_ascii_kinesis_swarm_contract_v2.py','correction_hooks':d['correction_hooks']};MANIFEST.write_text(json.dumps(m,indent=2,sort_keys=True)+'\n')
 r={'schema':'ascii-kinesis.v2-receipt','experiment_id':d['experiment_id'],'status':'RENDERED_AWAITING_REPO_VERIFICATION','repo_path':f"experiments/ascii-kinesis/{d['experiment_id']}/",'revises':d['revises'],'negative_fixture':d['negative_fixture'],'source':d['source'],'rights_note':d['source']['rights_note'],'observation_inference_split':{'OBSERVED':d['source']['observed'],'INFERRED':['All decisive key timing classes','All authored relationship geometry, leverage, support/root transfer, release, recoil/lag, overshoot, settle, recovery debt, and bridge arcs'],'UNKNOWN':d['source']['unknown']},'key_timings':[{'key_id':k['key_id'],'name':k['name'],'timing_class':k['timing_class'],'timing_provenance':k['timing_provenance']} for k in d['keys']],'media_sha256':ms,'media_bytes':len(media),'ascii_sheet_sha256':ss,'evaluation':d['evaluation'],'reconstruction':'python3 build.py','contract_test':'PENDING_EXTERNAL_RUN','repo_readback':'PENDING','issue_343_receipt':'PENDING','correction_hooks':d['correction_hooks']};RECEIPT.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n')
 print(json.dumps({'media_sha256':ms,'media_bytes':len(media),'gif_bytes':GIF.stat().st_size,'semantic_frames_per_loop':len(seq),'video_frames_total':len(frames),'ascii_sheet_sha256':ss},sort_keys=True))
if __name__=='__main__':main()
