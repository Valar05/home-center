#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent; MOTION=HERE/'motion.json'; OUT_MP4=HERE/'custody-latch-load-release.mp4'; OUT_HTML=HERE/'custody-latch-load-release.motion.html'
W,H=56,20; HOLD={'ONES':1,'TWOS':2,'FOURS':4}; LINKS=[('head','shoulder_l'),('head','shoulder_r'),('shoulder_l','shoulder_r'),('shoulder_l','hand_l'),('shoulder_r','hand_r'),('shoulder_l','pelvis'),('shoulder_r','pelvis'),('pelvis','knee_l'),('pelvis','knee_r'),('knee_l','foot_l'),('knee_r','foot_r')]
def lerp(a,b,t): return [round(a[0]+(b[0]-a[0])*t),round(a[1]+(b[1]-a[1])*t)]
def bres(a,b):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;pts=[]
 while True:
  pts.append((x0,y0))
  if x0==x1 and y0==y1: break
  e=2*err
  if e>=dy: err+=dy;x0+=sx
  if e<=dx: err+=dx;y0+=sy
 return pts
def glyph(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 if abs(dx)>abs(dy)*2:return '-'
 if abs(dy)>abs(dx)*2:return '|'
 return '\\' if dx*dy>0 else '/'
def topology(k):return (k['contact_state'],k['custody'],k['support_A'],k['root_owner'])
def render_ascii(k,A=None,obj=None):
 A=A or k['A']; oc=(obj or {}).get('center',k['object_center']); og=(obj or {}).get('grip',k['object_grip']); g=[[' ']*W for _ in range(H)]
 def put(x,y,ch):
  if 0<=x<W and 0<=y<H:g[y][x]=ch
 for a,b in LINKS:
  ch=glyph(A[a],A[b])
  for x,y in bres(A[a],A[b])[1:-1]:
   if g[y][x]==' ':put(x,y,ch)
 for j,(x,y) in A.items(): put(x,y,'@' if j=='pelvis' else ('A' if j=='head' else 'o'))
 # object is an abstract 5-char payload, not source likeness
 ox,oy=oc
 for dx,ch in [(-3,'{'),(-2,'='),(-1,'='),(0,'O'),(1,'='),(2,'='),(3,'}')]:put(ox+dx,oy,ch)
 gx,gy=og;put(gx,gy,'*')
 if k.get('shared_center'):x,y=k['shared_center'];put(x,y,'X')
 for j in ('foot_l','foot_r'):
  x,y=A[j];put(x,y+1,'=')
 if k['custody']=='A_OWNS':
  ax,ay=A['hand_r']; bx,by=og
  for x,y in bres((ax,ay),(bx,by))[1:-1]:
   if g[y][x]==' ':put(x,y,':')
 lines=[''.join(r).rstrip() for r in g]
 return '\n'.join(lines)
def connector(a,b,t):
 A={j:lerp(a['A'][j],b['A'][j],t) for j in a['A']}; obj={'center':lerp(a['object_center'],b['object_center'],t),'grip':lerp(a['object_grip'],b['object_grip'],t)}
 return render_ascii(a,A,obj)
def contact_sheet(data):
 out=[]
 for k in data['keys']:
  out.append(f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} | contact={k['contact_state']} | custody={k['custody']} | support={k['support_A']} | root={k['root_owner']}\n{render_ascii(k)}")
 return '\n\n'.join(out)
def render_png(text,path,label):
 im=Image.new('RGB',(960,540),'black');d=ImageDraw.Draw(im);font=ImageFont.load_default(size=22);d.text((22,16),label,fill='white',font=font);d.multiline_text((22,54),text,fill='white',font=font,spacing=2);im.save(path)
def build_video(data):
 scale=int(data['compile']['preview_time_scale']); sub=int(data['compile']['connector_subframes']); semantic=[]; keys=data['keys']
 for i,k in enumerate(keys):
  for _ in range(HOLD[k['timing_class']]*scale):semantic.append((k['key_id'],render_ascii(k)))
  if i+1<len(keys) and topology(k)==topology(keys[i+1]):
   for s in range(1,sub+1):semantic.append((k['key_id']+'~'+keys[i+1]['key_id'],connector(k,keys[i+1],s/(sub+1))))
 seq=semantic*int(data['compile']['loop_repetitions'])
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  for n,(lab,txt) in enumerate(seq):render_png(txt,td/f'frame-{n:04d}.png',lab)
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(data['compile']['fps']),'-i',str(td/'frame-%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','32','-pix_fmt','yuv420p','-movflags','+faststart',str(OUT_MP4)],check=True)
 return semantic
def esc(s):return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')
def html(data,sheet,b64):
 pretty=json.dumps(data,indent=2,sort_keys=True)
 return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Contact 006 — Custody Latch Load Release</title><style>:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1200px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}</style></head><body><h1>Custody Latch: Load → Release</h1><nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button></nav><section id="ascii" role="tabpanel"><pre>{esc(sheet)}</pre></section><section id="json" role="tabpanel" hidden><pre>{esc(pretty)}</pre></section><section id="video" role="tabpanel" hidden><video controls loop playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section><script>const tabs=[...document.querySelectorAll('button[data-view]')],panels=[...document.querySelectorAll('section[role=tabpanel]')];for(const t of tabs)t.addEventListener('click',()=>{{for(const b of tabs)b.setAttribute('aria-selected',b===t?'true':'false');for(const p of panels)p.hidden=p.id!==t.dataset.view;}});</script></body></html>'''
def main():
 data=json.loads(MOTION.read_text()); sem=build_video(data); media=OUT_MP4.read_bytes(); sheet=contact_sheet(data); data['compile'].update(media_sha256=hashlib.sha256(media).hexdigest(),media_bytes=len(media),semantic_frames_per_loop=len(sem),video_frames_total=len(sem)*int(data['compile']['loop_repetitions'])); data['ascii_sheet_sha256']=hashlib.sha256(sheet.encode()).hexdigest(); MOTION.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n'); OUT_HTML.write_text(html(data,sheet,base64.b64encode(media).decode())); print(json.dumps({'media_sha256':data['compile']['media_sha256'],'media_bytes':len(media),'semantic_frames_per_loop':len(sem),'video_frames_total':data['compile']['video_frames_total'],'ascii_sheet_sha256':data['ascii_sheet_sha256']},sort_keys=True))
if __name__=='__main__':main()
