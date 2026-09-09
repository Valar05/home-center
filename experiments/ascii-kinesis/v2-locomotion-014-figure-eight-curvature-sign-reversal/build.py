#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,html,json,shutil,subprocess
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
MOTION=json.loads((HERE/'motion.json').read_text(encoding='utf-8'))
SLUG='figure-eight-curvature-sign-reversal'
FPS=int(MOTION['motion_dungeon']['compile']['fps']); HOLDS=MOTION['motion_dungeon']['compile']['timing_hold_frames']
BONES=[tuple(v) for v in MOTION['rig']['bones']]; WW=int(MOTION['rig']['world_grid']['width']); WH=int(MOTION['rig']['world_grid']['height']); CROSS=tuple(MOTION['rig']['world_grid']['crossover_xy'])
def pose(k): return {n:tuple(v) for n,v in zip(MOTION['rig']['joints'],k['pose_rig'])}
def mech(k):
 m=k['mechanics']; return {'root_xy':[m[0],m[1]],'heading_deg':m[2],'curvature':m[3],'bank_units':m[4],'spacing_from_prev':m[5]} if isinstance(m,list) else m
def line(a,b):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy;o=[]
 while True:
  o.append((x0,y0))
  if (x0,y0)==(x1,y1): return o
  e=2*err
  if e>=dy:err+=dy;x0+=sx
  if e<=dx:err+=dx;y0+=sy
def draw(g,k,off=(0,0)):
 j=pose(k);ox,oy=off;h=len(g);w=len(g[0]);q=lambda p:(p[0]-ox,p[1]-oy)
 for a,b in BONES:
  pa,pb=q(j[a]),q(j[b])
  for x,y in line(pa,pb)[1:-1]:
   if 0<=x<w and 0<=y<h and g[y][x]==' ':
    dx=pb[0]-pa[0];dy=pb[1]-pa[1];g[y][x]='/' if dx*dy<0 else ('\\' if dx*dy>0 else ('-' if dy==0 else '|'))
 for n,p in j.items():
  x,y=q(p)
  if 0<=x<w and 0<=y<h:g[y][x]='O' if n=='head' else ('@' if n=='pelvis' else ('+' if n=='chest' else ('o' if ('elbow' in n or 'knee' in n) else '*')))
 for side,node in [('L','l_foot'),('R','r_foot')]:
  x,y=q(j[node])
  if 0<=x<w and 0<=y<h:g[y][x]='?' if k['contact_state']=='PRECONTACT' and k.get('probe_foot')==side else ('!' if k['support_contact']==side else '~')
def local_ascii(k):
 j=pose(k);xs=[p[0] for p in j.values()];ys=[p[1] for p in j.values()];minx,maxx=min(xs)-3,max(xs)+3;miny,maxy=min(ys)-3,max(ys)+3;w=max(22,maxx-minx+1);h=max(16,maxy-miny+1);g=[[' ']*w for _ in range(h)];draw(g,k,(minx,miny));return '\n'.join(''.join(r).rstrip() for r in g)
def world_ascii(k):
 g=[[' ']*WW for _ in range(WH)]
 for x in range(WW):g[0][x]=g[-1][x]='-'
 for y in range(WH):g[y][0]=g[y][-1]='|'
 g[CROSS[1]][CROSS[0]]='x';draw(g,k);return '\n'.join(''.join(r).rstrip() for r in g)
def root_map():
 g=[[' ']*WW for _ in range(WH)]
 for x in range(WW):g[0][x]=g[-1][x]='-'
 for y in range(WH):g[y][0]=g[y][-1]='|'
 cx,cy=CROSS;g[cy][cx]='x';pts=[]
 for k in MOTION['keys']:
  x,y=[int(round(v)) for v in mech(k)['root_xy']];pts.append((x,y))
  if 0<x<WW-1 and 0<y<WH-1:g[y][x]='o'
 for a,b in zip(pts,pts[1:]):
  for x,y in line(a,b)[1:-1]:
   if 0<x<WW-1 and 0<y<WH-1 and g[y][x]==' ':g[y][x]='.'
 if pts:g[pts[0][1]][pts[0][0]]='S';g[pts[-1][1]][pts[-1][0]]='E'
 return '\n'.join(''.join(r).rstrip() for r in g)
def contact_sheet():
 L=['ASCII KINESIS V2 LOCOMOTION 014 — FIGURE-EIGHT CURVATURE SIGN REVERSAL','Legend: ! trusted support   ? precontact probe   ~ free foot   @ pelvis/root   + chest   O head   x crossover','Timing: ONES/TWOS/FOURS are display-frame exposure classes; every decisive timing here is INFERRED / STREET_FIGHTER-CAPCOM.','','ROOT TRAVEL MAP — fixed world address; dots audit authored root travel and do not reproduce source choreography:',root_map(),'']
 for k in MOTION['keys']:
  m=mech(k);L += [f"{k['key_id']} {k['name']}  [{k['timing_class']} / {k['timing_provenance']}]  SUPPORT={k['support_contact']}  CONTACT={k['contact_state']}",f"ROOT={m['root_xy']}  HEADING={m['heading_deg']:+.1f}deg  CURVATURE={m['curvature']:+.2f}  BANK={m['bank_units']:+.2f}  SPACING={m['spacing_from_prev']}",f"ROLE: {k['causal_role']}",local_ascii(k),'']
 return '\n'.join(L).rstrip()+'\n'
def render(path):
 frames=[]
 for k in MOTION['keys']:frames += [(k,world_ascii(k))]*int(HOLDS[k['timing_class']])
 assert len(frames)==55
 tmp=HERE/'.motion-frames';shutil.rmtree(tmp,ignore_errors=True);tmp.mkdir();mono='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf';font=ImageFont.truetype(mono,5);small=ImageFont.truetype(mono,6)
 for i,(k,art) in enumerate(frames):
  im=Image.new('RGB',(384,256),(10,10,11));d=ImageDraw.Draw(im);d.text((5,2),'ASCII KINESIS · L014 · FIGURE-EIGHT CURVATURE SIGN REVERSAL',font=small,fill=(190,190,190));d.text((5,10),f"{k['key_id']} {k['name']} {k['support_contact']} {k['contact_state']}",font=small,fill=(238,238,235));d.multiline_text((5,20),art,font=font,fill=(246,246,240),spacing=0);d.text((5,246),f'{i+1:02d}/55 · abstract ASCII only',font=small,fill=(160,160,160));im.save(tmp/f'f_{i:04d}.png',compress_level=9)
 subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(tmp/'f_%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','38','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','comment=ASCII Kinesis abstract rig only',str(path)],check=True);subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','null','-'],check=True)
def gz64(b):return base64.b64encode(gzip.compress(b,9,mtime=0)).decode('ascii')
def spa(video):
 a=(HERE/'contact-sheet.txt').read_bytes();j=(HERE/'motion.json').read_bytes();v=base64.b64encode(video.read_bytes()).decode('ascii');ag=gz64(a);jg=gz64(j)
 page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(MOTION['title'])}</title><style>body{{font-family:system-ui,sans-serif;margin:0;padding:16px}}nav{{display:flex;gap:8px;position:sticky;top:0;background:Canvas;padding:8px 0}}section{{display:none}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}}video{{max-width:100%;height:auto;background:#000}}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="ap"></pre></section><section id="json"><pre id="jp"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{v}"></video></section><script>const B=async(s)=>{{let b=Uint8Array.from(atob(s),c=>c.charCodeAt(0)),r=new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip')));return await r.text()}};Promise.all([B('{ag}'),B('{jg}')]).then(([a,j])=>{{ap.textContent=a;jp.textContent=JSON.stringify(JSON.parse(j),null,2)}});for(const b of document.querySelectorAll('[data-view]'))b.onclick=()=>{{for(const s of document.querySelectorAll('section'))s.classList.remove('active');document.getElementById(b.dataset.view).classList.add('active')}};</script></body></html>'''
 (HERE/f'{SLUG}.motion.html').write_text(page,encoding='utf-8')
if __name__=='__main__':
 c=contact_sheet();(HERE/'contact-sheet.txt').write_text(c,encoding='utf-8');mp4=HERE/f'{SLUG}.motion.mp4';render(mp4);b=mp4.read_bytes();d=hashlib.sha256(b).hexdigest();exp=MOTION['motion_dungeon']['compile'];assert len(b)==exp['media_bytes'] and d==exp['media_sha256'];spa(mp4)
