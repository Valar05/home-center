#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,hashlib,html,json,math,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
MOTION_PATH=ROOT/'motion.json'; ASCII_PATH=ROOT/'contact-sheet.txt'; SPA_PATH=ROOT/'latent-eligibility-force-transfer-repair.motion.html'
TMP=ROOT/'.motion-build'; FRAMES=TMP/'frames'; MP4=TMP/'motion.mp4'
W,H,GROUND_Y=72,22,17; IMG_W,IMG_H,FPS=256,144,24; TIMING={'ONES':1,'TWOS':2,'FOURS':4}
def line_cells(p0,p1):
 x0,y0=map(int,p0);x1,y1=map(int,p1);dx=abs(x1-x0);dy=-abs(y1-y0);sx=1 if x0<x1 else -1;sy=1 if y0<y1 else -1;err=dx+dy;out=[]
 while True:
  out.append((x0,y0))
  if x0==x1 and y0==y1: return out
  e2=2*err
  if e2>=dy:err+=dy;x0+=sx
  if e2<=dx:err+=dx;y0+=sy
def seg_char(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 if abs(dx)>abs(dy)*1.7:return '-'
 if abs(dy)>abs(dx)*1.7:return '|'
 return '\\' if dx*dy>0 else '/'
def render_ascii(state):
 g=[[' ']*W for _ in range(H)]
 for x in range(W):g[GROUND_Y][x]='_'
 def actor(j,hc):
  for a,b in [('head','shoulder'),('shoulder','pelvis'),('shoulder','hand_f'),('shoulder','hand_b'),('pelvis','foot_f'),('pelvis','foot_b')]:
   ch=seg_char(j[a],j[b])
   for x,y in line_cells(j[a],j[b]):
    if 0<=x<W and 0<=y<H and g[y][x]==' ':g[y][x]=ch
  for n,ch in [('head',hc),('shoulder','O'),('pelvis','X'),('hand_f','*'),('hand_b','*'),('foot_f','^'),('foot_b','^')]:
   x,y=j[n];x=int(round(x));y=int(round(y))
   if 0<=x<W and 0<=y<H:g[y][x]=ch
 actor(state['A'],'A');actor(state['B'],'B')
 if state['contact'] not in ('NONE','RELEASED'):
  ax,ay=state['A']['hand_f'];bx,by=state['B']['hand_f'];x=round((ax+bx)/2);y=round((ay+by)/2)
  if 0<=x<W and 0<=y<H:g[y][x]='@'
 return '\n'.join(''.join(r).rstrip() for r in g)
def contact_sheet(motion):
 parts=[]
 for q in motion['keys']:
  state={'A':q['pose_rig']['A'],'B':q['pose_rig']['B'],'contact':q['contact']}
  parts.append(f"{q['key_id']}  {q['phase']}  [{q['timing_class']}/{q['timing_provenance']}]\ncontact={q['contact']} | eligibility={q['eligibility']} | custody={q['custody']}\nsupport={q['support_contact']}\n"+render_ascii(state))
 return ('\n'+'='*72+'\n').join(parts)+'\n'
def interp(a0,a1,t,curve):
 out={};s=t*t*(3-2*t)
 for n in a0:
  x0,y0=a0[n];x1,y1=a1[n];x=x0+(x1-x0)*s;y=y0+(y1-y0)*s
  if n in ('head','hand_f','hand_b'):y+=curve*math.sin(math.pi*t)
  out[n]=[x,y]
 return out
def same_sem(a,b):return all(a[f]==b[f] for f in ('contact','custody','support_contact'))
def sequence(m):
 out=[]
 for i,q in enumerate(m['keys']):
  k={'id':q['key_id'],'phase':q['phase'],'A':q['pose_rig']['A'],'B':q['pose_rig']['B'],'contact':q['contact'],'custody':q['custody'],'support_contact':q['support_contact']}
  out.extend([k]*TIMING[q['timing_class']])
  if i+1<len(m['keys']):
   n=m['keys'][i+1];k1={'id':n['key_id'],'phase':n['phase'],'A':n['pose_rig']['A'],'B':n['pose_rig']['B'],'contact':n['contact'],'custody':n['custody'],'support_contact':n['support_contact']}
   if same_sem(k,k1):out.append({**k,'id':k['id']+'~'+k1['id'],'phase':'CONNECTIVE','A':interp(k['A'],k1['A'],.5,-.35),'B':interp(k['B'],k1['B'],.5,.35)})
 return out
def font(n):
 p='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
 return ImageFont.truetype(p,n) if Path(p).exists() else ImageFont.load_default()
def render_video(m):
 if TMP.exists():shutil.rmtree(TMP)
 FRAMES.mkdir(parents=True);f=font(5);s=font(4);seq=sequence(m)
 for i,k in enumerate(seq):
  im=Image.new('RGB',(IMG_W,IMG_H),(8,8,8));d=ImageDraw.Draw(im);d.text((4,2),f"{k['id']} {k['phase']}",font=s,fill=(235,235,235));d.text((4,8),f"CONTACT {k['contact']} CUSTODY {k['custody']} SUPPORT {k['support_contact']}",font=s,fill=(180,180,180));d.multiline_text((3,14),render_ascii(k),font=f,fill=(245,245,245),spacing=-1);im.save(FRAMES/f'f-{i:04d}.png')
 subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(FRAMES/'f-%04d.png'),'-c:v','libx264','-preset','medium','-crf','18','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
 return seq
def gz64(text):return base64.b64encode(gzip.compress(text.encode(),compresslevel=9,mtime=0)).decode()
def build_spa(m,sheet,mp4):
 a=gz64(sheet);j=gz64(json.dumps(m,separators=(',',':'),ensure_ascii=True));v=base64.b64encode(mp4).decode()
 return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{{background:#0b0b0b;color:#eee;font-family:system-ui}}section{{display:none}}section.active{{display:block}}pre{{font-family:monospace;font-variant-ligatures:none;white-space:pre;overflow:auto}}video{{max-width:100%}}</style></head><body><nav><button data-view="ascii" data-tab="ASCII">ASCII</button><button data-view="json" data-tab="JSON">JSON</button><button data-view="video" data-tab="VIDEO">VIDEO</button></nav><section id="ASCII" class="active"><pre id="a"></pre></section><section id="JSON"><pre id="j"></pre></section><section id="VIDEO"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{v}"></video></section><script>const D=async s=>new TextDecoder().decode(await new Response(new Blob([Uint8Array.from(atob(s),c=>c.charCodeAt(0))]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());(async()=>{{a.textContent=await D('{a}');j.textContent=await D('{j}')}})();document.querySelectorAll('button[data-tab]').forEach(b=>b.onclick=()=>{{document.querySelectorAll('section').forEach(s=>s.classList.remove('active'));document.getElementById(b.dataset.tab).classList.add('active')}})</script></body></html>'''
def main():
 m=json.loads(MOTION_PATH.read_text());sheet=contact_sheet(m);ASCII_PATH.write_text(sheet);seq=render_video(m);mp4=MP4.read_bytes();got=hashlib.sha256(mp4).hexdigest()
 if got!=m['motion_dungeon']['media_sha256']:raise SystemExit(f'media hash mismatch {got}')
 SPA_PATH.write_text(build_spa(m,sheet,mp4));print(json.dumps({'frames':len(seq),'media_sha256':got,'media_bytes':len(mp4),'sheet_sha256':hashlib.sha256(sheet.encode()).hexdigest(),'spa_sha256':hashlib.sha256(SPA_PATH.read_bytes()).hexdigest()},sort_keys=True))
if __name__=='__main__':main()
