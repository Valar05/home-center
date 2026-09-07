#!/usr/bin/env python3
from __future__ import annotations
import base64,hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json';OUT_MP4=HERE/'occlusion-anchor-invariants.mp4';OUT_HTML=HERE/'occlusion-anchor-invariants.motion.html'
W,H=58,20;HOLD={'ONES':1,'TWOS':2,'FOURS':4}
LINKS=[('head','shoulder_l'),('head','shoulder_r'),('shoulder_l','shoulder_r'),('shoulder_l','hand_l'),('shoulder_r','hand_r'),('shoulder_l','pelvis'),('shoulder_r','pelvis'),('pelvis','knee_l'),('pelvis','knee_r'),('knee_l','foot_l'),('knee_r','foot_r')]
def lerp(a,b,t):return [round(a[0]+(b[0]-a[0])*t),round(a[1]+(b[1]-a[1])*t)]
def bres(a,b):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;pts=[]
 while True:
  pts.append((x0,y0))
  if x0==x1 and y0==y1:break
  e=2*err
  if e>=dy:err+=dy;x0+=sx
  if e<=dx:err+=dx;y0+=sy
 return pts
def glyph(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 if abs(dx)>abs(dy)*2:return '-'
 if abs(dy)>abs(dx)*2:return '|'
 return '\\' if dx*dy>0 else '/'
def render_ascii(k,ov=None):
 g=[[' ']*W for _ in range(H)]
 def put(x,y,ch):
  if 0<=x<W and 0<=y<H:g[y][x]=ch
 A={j:list(v) for j,v in k['A'].items()};obj={'rect':list(k['object']['rect']),'center':list(k['object']['center'])}
 if ov:A=ov['A'];obj=ov['object']
 for a,b in LINKS:
  ch=glyph(A[a],A[b])
  for x,y in bres(A[a],A[b])[1:-1]:
   if 0<=x<W and 0<=y<H and g[y][x]==' ':put(x,y,ch)
 for j,(x,y) in A.items():put(x,y,'@' if j=='pelvis' else ('A' if j=='head' else 'o'))
 if k['support_A'] in {'BOTH','LEFT'}:
  x,y=A['foot_l'];put(x,y+1,'=')
 if k['support_A'] in {'BOTH','RIGHT'}:
  x,y=A['foot_r'];put(x,y+1,'=')
 x0,y0,x1,y1=obj['rect']
 for y in range(y0,y1+1):
  for x in range(x0,x1+1):put(x,y,'#' if x in (x0,x1) or y in (y0,y1) else '.')
 cx,cy=obj['center'];put(cx,cy,'O')
 if k.get('shared_center'):
  x,y=k['shared_center'];put(x,y,'X')
 for a in k.get('anchors',[]):
  x,y=a['at'];put(x,y,'*')
 label='CONTACT' if k['contact_state']!='NONE' else ''
 for i,ch in enumerate(label):put(1+i,1,ch)
 label='A>CUSTODY' if k['custody']=='A' else ('FREE' if k['custody']=='FREE' else '')
 for i,ch in enumerate(label):put(1+i,2,ch)
 return '\n'.join(''.join(r).rstrip() for r in g)
def topology(k):return (k['contact_state'],k['support_A'],k['object_support'],k['root_owner'],k['custody'])
def connector(a,b,t=.5):
 return render_ascii(a,{'A':{j:lerp(a['A'][j],b['A'][j],t) for j in a['A']},'object':{'rect':[round(a['object']['rect'][i]+(b['object']['rect'][i]-a['object']['rect'][i])*t) for i in range(4)],'center':lerp(a['object']['center'],b['object']['center'],t)}})
def sheet(data):
 out=[]
 for k in data['keys']:
  h=f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | contact={k['contact_state']} | support={k['support_A']} | object_support={k['object_support']} | root={k['root_owner']} | custody={k['custody']}"
  out.append(h+'\n'+render_ascii(k))
 return '\n\n'.join(out)
def png(text,path,label):
 im=Image.new('RGB',(720,400),'black');d=ImageDraw.Draw(im);font=ImageFont.load_default(size=18);d.text((18,12),label,fill='white',font=font);d.multiline_text((18,42),text,fill='white',font=font,spacing=1);im.save(path,optimize=False)
def video(data):
 sem=[];ks=data['keys']
 for i,k in enumerate(ks):
  p=render_ascii(k)
  for _ in range(HOLD[k['timing_class']]):sem.append((k['key_id'],p))
  if i+1<len(ks) and topology(k)==topology(ks[i+1]):sem.append((k['key_id']+'~'+ks[i+1]['key_id'],connector(k,ks[i+1])))
 seq=sem*int(data['compile']['loop_repetitions'])
 with tempfile.TemporaryDirectory(prefix='ascii-kinesis-v2-') as td:
  td=Path(td)
  for n,(lab,txt) in enumerate(seq):png(txt,td/f'frame-{n:04d}.png',lab)
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(data['compile']['fps']),'-i',str(td/'frame-%04d.png'),'-map_metadata','-1','-c:v','libx264','-preset','veryslow','-crf','38','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT_MP4)],check=True)
 return sem
def esc(s):return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def html(data,ascii_sheet,media_b64):
 pretty=json.dumps(data,indent=2,sort_keys=True)
 return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Contact 004 - Occlusion Anchor Invariants</title>
<style>:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1100px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:76ch;line-height:1.45}}</style></head><body>
<h1>Occlusion Anchor Invariants</h1><p class="note">Copyright-safe abstract relationship rig. Source art is evidence only and is not embedded. Payload overlap may hide the carrier silhouette, but contact ownership remains legible because custody is encoded by explicit anchors, support, root ownership, and a shared center rather than by outline overlap.</p>
<nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button></nav>
<section id="ascii" role="tabpanel"><pre>{esc(ascii_sheet)}</pre></section><section id="json" role="tabpanel" hidden><pre>{esc(pretty)}</pre></section><section id="video" role="tabpanel" hidden><video controls loop playsinline preload="metadata"><source src="data:video/mp4;base64,{media_b64}" type="video/mp4"></video><p class="note">MP4 compiled solely from authored abstract ASCII rig keys, explicit holds, and topology-safe connective geometry. No source sprite pixels are present.</p></section>
<script>const tabs=[...document.querySelectorAll('button[data-view]')];const panels=[...document.querySelectorAll('section[role=tabpanel]')];for(const t of tabs)t.addEventListener('click',()=>{{for(const b of tabs)b.setAttribute('aria-selected',b===t?'true':'false');for(const p of panels)p.hidden=p.id!==t.dataset.view;}});</script></body></html>"""
def main():
 data=json.loads(MOTION.read_text());sem=video(data);media=OUT_MP4.read_bytes();sha=hashlib.sha256(media).hexdigest()
 data['compile'].update(media_sha256=sha,media_bytes=len(media),semantic_frames_per_loop=len(sem),video_frames_total=len(sem)*int(data['compile']['loop_repetitions']))
 data['manifest_receipt']['verification_state']='BUILT'
 s=sheet(data);data['ascii_sheet_sha256']=hashlib.sha256(s.encode()).hexdigest();MOTION.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
 OUT_HTML.write_text(html(data,s,base64.b64encode(media).decode('ascii')))
 print(json.dumps({'media_sha256':sha,'media_bytes':len(media),'semantic_frames_per_loop':len(sem),'video_frames_total':data['compile']['video_frames_total'],'ascii_sheet_sha256':data['ascii_sheet_sha256']},sort_keys=True))
if __name__=='__main__':main()
