#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
HERE=Path(__file__).resolve().parent
SLUG='precontact-landing-window'
EDGES=[('head','neck'),('neck','shoulder_l'),('neck','shoulder_r'),('shoulder_l','elbow_l'),('elbow_l','hand_l'),('shoulder_r','elbow_r'),('elbow_r','hand_r'),('neck','pelvis'),('pelvis','knee_l'),('knee_l','foot_l'),('pelvis','knee_r'),('knee_r','foot_r')]
MARK={'head':'O','neck':'+','shoulder_l':'+','shoulder_r':'+','elbow_l':'o','elbow_r':'o','hand_l':'*','hand_r':'*','pelvis':'@','knee_l':'o','knee_r':'o','foot_l':'_','foot_r':'_'}
PREFIX=os.environ.get('PREFIX','')
FONT_CANDIDATES=[Path(PREFIX)/'share/fonts/TTF/DejaVuSansMono.ttf',Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')]
BOLD_CANDIDATES=[Path(PREFIX)/'share/fonts/TTF/DejaVuSansMono-Bold.ttf',Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf')]
def font_path(candidates):
 for p in candidates:
  if p.is_file(): return str(p)
 raise SystemExit('missing DejaVu Sans Mono font')
FONT=font_path(FONT_CANDIDATES); BOLD=font_path(BOLD_CANDIDATES)
def line(a,b):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);dy=-abs(y1-y0);sx=1 if x0<x1 else -1;sy=1 if y0<y1 else -1;err=dx+dy;o=[]
 while True:
  o.append((x0,y0))
  if (x0,y0)==(x1,y1):return o
  e=2*err
  if e>=dy:err+=dy;x0+=sx
  if e<=dx:err+=dx;y0+=sy
def glyph(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 if abs(dx)>abs(dy)*1.5:return '-'
 if abs(dy)>abs(dx)*1.5:return '|'
 return '\\' if dx*dy>0 else '/'
def pose_text(p,label,support,phase):
 W,H=60,23;g=[[' ']*W for _ in range(H)]
 for x in range(W):g[21][x]='.'
 for a,b in EDGES:
  pa=tuple(p[a]);pb=tuple(p[b]);c=glyph(pa,pb)
  for x,y in line(pa,pb)[1:-1]:
   if 0<=x<W and 0<=y<H:g[y][x]=c
 for j,(x,y) in p.items():
  if 0<=x<W and 0<=y<H:g[y][x]=MARK[j]
 hx,hy=p['head']
 if hx+2<W:g[hy][hx+2]='>'
 return f'{label} | {phase} | support={support}\n'+'\n'.join(''.join(r).rstrip() for r in g)
def midpoint(a,b):return {j:[round((a[j][0]+b[j][0])/2),round((a[j][1]+b[j][1])/2)] for j in a}
def exposure(t):return {'ONES':1,'TWOS':2,'FOURS':4}[t]
def sequence(m):
 out=[];ks=m['keys']
 for i,k in enumerate(ks):
  for _ in range(exposure(k['timing_class'])):out.append((k['pose_rig'],k['name'],k['support_contact'],k['vertical_phase'],'HOLD'))
  if i+1<len(ks):
   n=ks[i+1]
   if k['support_contact']==n['support_contact'] and k['contact_state']==n['contact_state']:
    out.append((midpoint(k['pose_rig'],n['pose_rig']),k['name']+' -> '+n['name'],k['support_contact'],k['vertical_phase']+'~'+n['vertical_phase'],'CONNECT'))
 return out
def sheet(m):
 o=['ASCII KINESIS V2 — AIRBORNE 002 — PRECONTACT LANDING WINDOW','Independent abstract rig; no source sprite pixels or traced contours.','Timing shorthand: ONES/TWOS/FOURS are exposure classes, not seconds.','All decisive timings in this specimen: INFERRED / STREET_FIGHTER-CAPCOM.','']
 for k in m['keys']:
  o += ['='*60,f"{k['key_id']}  {k['name']}  timing={k['timing_class']}  provenance={k['timing_provenance']}",'role: '+k['causal_role'],'root: '+k['motion_arc_root_note'],pose_text(k['pose_rig'],k['name'],k['support_contact'],k['vertical_phase']),'']
 return '\n'.join(o).rstrip()+'\n'
def render_video(m):
 seq=sequence(m);allf=seq*m['compile']['loop_repetitions'];d=HERE/'_frames';d.mkdir(exist_ok=True)
 for p in d.glob('*.png'):p.unlink()
 f=ImageFont.truetype(FONT,11);fb=ImageFont.truetype(BOLD,13)
 for i,(pose,label,support,phase,kind) in enumerate(allf):
  im=Image.new('RGB',(640,360),(18,18,18));dr=ImageDraw.Draw(im)
  dr.text((18,12),'ASCII KINESIS / AIRBORNE 002',font=fb,fill=(238,238,238));dr.text((18,34),f'{label}  [{kind}]  support={support}',font=f,fill=(220,220,220));dr.multiline_text((18,55),pose_text(pose,label,support,phase),font=f,fill=(238,238,238),spacing=1);dr.text((18,342),f'frame {i+1}/{len(allf)}',font=f,fill=(180,180,180));im.save(d/f'{i:05d}.png')
 out=HERE/(SLUG+'.mp4');subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(m['compile']['fps']),'-i',str(d/'%05d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-crf','32','-preset','slow','-movflags','+faststart',str(out)],check=True);return out,len(seq),len(allf)
def make_html(m,man,a,vb):
 payload=json.dumps({'motion':m,'manifest':man},indent=2,sort_keys=True)
 b64=base64.b64encode(vb).decode()
 return '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 — Airborne 002 — Precontact Landing Window</title><style>body{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}nav{display:flex;gap:.5rem;padding:1rem}.view{display:none;padding:1rem}.view.active{display:block}pre{white-space:pre;font-family:monospace;font-variant-ligatures:none;overflow:auto}video{max-width:100%;height:auto}</style></head><body><nav><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav><section id="ascii" class="view active"><pre>'+html.escape(a)+'</pre></section><section id="json" class="view"><pre>'+html.escape(payload)+'</pre></section><section id="video" class="view"><video controls loop playsinline src="data:video/mp4;base64,'+b64+'"></video></section><script>const b=[...document.querySelectorAll("nav button")],v=[...document.querySelectorAll(".view")];for(const x of b)x.onclick=()=>{for(const y of b)y.setAttribute("aria-selected",String(x===y));for(const z of v)z.classList.toggle("active",z.id===x.dataset.view)}</script></body></html>'
def main():
 m=json.loads((HERE/'motion.json').read_text());man=json.loads((HERE/'manifest.json').read_text());a=sheet(m);mp4,n,total=render_video(m);vb=mp4.read_bytes();sha=hashlib.sha256(vb).hexdigest()
 expected=m['compile'].get('media_sha256','')
 if len(expected)==64 and all(c in '0123456789abcdef' for c in expected.lower()) and sha!=expected:raise SystemExit(f'media hash mismatch: {sha} != {expected}')
 (HERE/(SLUG+'.motion.html')).write_text(make_html(m,man,a,vb),encoding='utf-8')
 print(json.dumps({'ok':True,'media_sha256':sha,'media_bytes':len(vb),'semantic_frames_per_loop':n,'video_frames_total':total},sort_keys=True))
if __name__=='__main__':main()
