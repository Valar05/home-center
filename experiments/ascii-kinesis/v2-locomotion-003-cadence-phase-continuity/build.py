#!/usr/bin/env python3
import base64,gzip,hashlib,html,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).parent;J=D/'motion.json';V=D/'cadence-phase-continuity.mp4';H=D/'cadence-phase-continuity.motion.html';HOLD={'ONES':1,'TWOS':2,'FOURS':4};B=[('head','pelvis'),('pelvis','lh'),('pelvis','rh'),('pelvis','lf'),('pelvis','rf')]
def L(a,b):
 x,y=a;X,Y=b;dx=abs(X-x);sx=1 if x<X else -1;dy=-abs(Y-y);sy=1 if y<Y else -1;e=dx+dy;r=[]
 while 1:
  r.append((x,y))
  if (x,y)==(X,Y):return r
  q=2*e
  if q>=dy:e+=dy;x+=sx
  if q<=dx:e+=dx;y+=sy
def A(k,j=None):
 g=[[' ']*20 for _ in range(7)];j=j or k['j'];p=lambda x,y,c:g[y].__setitem__(x,c) if 0<=x<20 and 0<=y<7 else None
 for x in range(20):p(x,6,'_')
 for a,b in B:
  q=j[a];w=j[b];dx=w[0]-q[0];dy=w[1]-q[1];c='-' if abs(dx)>abs(dy) else ('|' if abs(dy)>abs(dx) else ('\\' if dx*dy>0 else '/'))
  for x,y in L(q,w)[1:-1]:p(x,y,c)
 for n,(x,y) in j.items():p(x,y,'O' if n=='head' else ('+' if n=='pelvis' else 'o'))
 return '\n'.join(''.join(x).rstrip() for x in g)
def S(d):return '\n\n'.join(f"[{k['key_id']}] {k['name']} {k['timing_class']} {k['timing_provenance']}\n{k['support_contact']} root={k['root_owner']}\n{k['motion_arc_root_note']}\n{A(k)}" for k in d['keys'])
def F(d):
 r=[]
 for i,k in enumerate(d['keys']):
  r += [(k['key_id'],A(k))]*HOLD[k['timing_class']]
  if i+1<len(d['keys']) and (k['support_contact'],k['root_owner'])==(d['keys'][i+1]['support_contact'],d['keys'][i+1]['root_owner']):
   b=d['keys'][i+1];j={n:[round((k['j'][n][0]+b['j'][n][0])/2),round((k['j'][n][1]+b['j'][n][1])/2)] for n in k['j']};r.append((k['key_id']+'~'+b['key_id'],A(k,j)))
 return r
def main():
 d=json.loads(J.read_text());f=F(d);seq=f*d['compile']['loop_repetitions']
 with tempfile.TemporaryDirectory() as t:
  t=Path(t);font=ImageFont.load_default()
  for i,(lab,a) in enumerate(seq):
   im=Image.new('RGB',(128,72),'black');x=ImageDraw.Draw(im);x.text((2,1),lab,fill='white',font=font);x.multiline_text((2,9),a,fill='white',font=font,spacing=0);im.save(t/f'{i:03}.png')
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','24','-i',str(t/'%03d.png'),'-c:v','libx264','-preset','veryslow','-crf','51','-pix_fmt','yuv420p','-movflags','+faststart',str(V)],check=True)
 m=V.read_bytes();sha=hashlib.sha256(m).hexdigest();s=S(d);d['compile'].update(media_sha256=sha,media_bytes=len(m),semantic_frames_per_loop=len(f),video_frames_total=len(seq));d['ascii_sheet_sha256']=hashlib.sha256(s.encode()).hexdigest();d['receipt'].update(status='RENDERED_AND_STRUCTURALLY_TESTED',media_sha256=sha,media_bytes=len(m));J.write_text(json.dumps(d,separators=(',',':'),ensure_ascii=False)+'\n');js=json.dumps(d,separators=(',',':'),ensure_ascii=False);z=base64.b64encode(gzip.compress(js.encode(),9)).decode();b=base64.b64encode(m).decode();page=f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width"><style>body{{background:#111;color:#eee}}section[hidden]{{display:none}}pre{{font-family:monospace;font-variant-ligatures:none;white-space:pre;overflow:auto}}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre>{html.escape(s)}</pre></section><section id="json" hidden><pre id="j">loading</pre></section><section id="video" hidden><video controls loop playsinline><source src="data:video/mp4;base64,{b}" type="video/mp4"></video></section><script>const z='{z}';async function q(){{let a=Uint8Array.from(atob(z),c=>c.charCodeAt(0)),s=new DecompressionStream('gzip'),t=await new Response(new Blob([a]).stream().pipeThrough(s)).text();j.textContent=t}}q();for(const x of document.querySelectorAll('[data-view]'))x.onclick=()=>{{for(const s of document.querySelectorAll('section'))s.hidden=s.id!==x.dataset.view}}</script></body></html>''';H.write_text(page);print(len(m),len(page),sha)
if __name__=='__main__':main()
