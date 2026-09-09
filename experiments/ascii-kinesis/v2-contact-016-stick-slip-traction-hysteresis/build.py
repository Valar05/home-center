#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,hashlib,json,math,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent; M=R/'motion.json'; A=R/'contact-sheet.txt'; S=R/'stick-slip-traction-hysteresis.motion.html'; T=R/'.motion-build'; F=T/'frames'; V=T/'motion.mp4'
W,H,FPS=96,29,24; J=['head','shoulder','pelvis','hand_f','hand_b','knee_f','knee_b','foot_f','foot_b']; HOLD={'ONES':1,'TWOS':2,'FOURS':4}
def P(v): return {n:[float(x),float(y)] for n,(x,y) in zip(J,v)}
def cells(a,b):
 x0,y0=map(round,a);x1,y1=map(round,b);dx=abs(x1-x0);dy=-abs(y1-y0);sx=1 if x0<x1 else -1;sy=1 if y0<y1 else -1;e=dx+dy;o=[]
 while 1:
  o.append((x0,y0))
  if (x0,y0)==(x1,y1): return o
  e2=2*e
  if e2>=dy:e+=dy;x0+=sx
  if e2<=dx:e+=dx;y0+=sy
def line(g,a,b,ch):
 for x,y in cells(a,b):
  if 0<=x<W and 0<=y<H and g[y][x]==' ':g[y][x]=ch
def fr(s):
 g=[[' ']*W for _ in range(H)];gy=25
 for x in range(4,W-3):g[gy][x]='_'
 a=s['A'];c=s['contact'];patch=s.get('patch')
 if patch is not None:
  px=round(patch)
  if c in ('STICK','STICK_THRESHOLD','RESTICK'):g[gy][px]='#'
  if c in ('SLIP','RESTICK_ELIGIBLE'):
   old=55;g[gy][old]='|';fx=round(a['foot_f'][0]);lo,hi=sorted((old,fx))
   for x in range(lo+1,hi):g[gy][x]=':'
 for p,q in [('head','shoulder'),('shoulder','pelvis'),('shoulder','hand_f'),('shoulder','hand_b'),('pelvis','knee_f'),('knee_f','foot_f'),('pelvis','knee_b'),('knee_b','foot_b')]:
  dx=a[q][0]-a[p][0];dy=a[q][1]-a[p][1];ch='-' if abs(dx)>abs(dy)*1.7 else ('|' if abs(dy)>abs(dx)*1.7 else ('\\' if dx*dy>0 else '/'));line(g,a[p],a[q],ch)
 for n,ch in [('head','A'),('shoulder','O'),('pelvis','X'),('hand_f','*'),('hand_b','*'),('knee_f','o'),('knee_b','o'),('foot_f','^'),('foot_b','^')]:
  x,y=map(round,a[n]);g[y][x]=ch
 fo=s.get('force',[0,0])
 if fo!=[0,0]:
  x,y=map(round,a['foot_f']);d=1 if fo[0]>0 else -1
  for k in range(1,min(6,abs(int(fo[0])))+1):
   xx=x+d*k
   if 0<=xx<W:g[max(0,y-1)][xx]='+' if k<abs(int(fo[0])) else ('>' if d>0 else '<')
 return '\n'.join(''.join(r).rstrip() for r in g)
def st(q):return {'id':q['id'],'phase':q['phase'],'A':P(q['pose']),'contact':q['contact'],'custody':'NONE','support':q['support'],'force_owner':q['force_owner'],'force':q['force'],'patch':q['patch']}
def interp(a,b,t,c=0,freeze=False):
 s=t*t*(3-2*t);o={}
 for n in a:
  if freeze and n=='foot_f':o[n]=a[n][:];continue
  x=a[n][0]+(b[n][0]-a[n][0])*s;y=a[n][1]+(b[n][1]-a[n][1])*s
  if n in ('head','hand_f','hand_b','knee_f','knee_b'):y+=c*math.sin(math.pi*t)
  o[n]=[x,y]
 return o
def seq(m):
 cnt=[2,2,1,2,3,1,2,2,1,1,2,2];cur=[.3,.6,.2,-.5,-.8,-.2,.9,.6,-.4,-.6,.4,.2];out=[]
 for i,q in enumerate(m['keys']):
  a=st(q);out += [a]*HOLD[q['timing_class']]
  if i<len(m['keys'])-1:
   b=st(m['keys'][i+1]);freeze=a['contact'] in ('STICK','STICK_THRESHOLD') and b['contact']=='SLIP'
   for j in range(1,cnt[i]+1):
    t=j/(cnt[i]+1);out.append({**a,'id':a['id']+'~'+b['id'],'phase':'AUTHORED_CONNECTIVE','A':interp(a['A'],b['A'],t,cur[i],freeze),'force':[a['force'][0]+(b['force'][0]-a['force'][0])*t,0]})
 return out
def sheet(m):
 out=[m['experiment_id'],m['principle'],'REVISION: NEW_CONCEPT | revises=null | negative_fixture=null | source_change=NOT_APPLICABLE_NEW_CONCEPT',f"SOURCE: TSR asset {m['source']['asset_id']} {m['source']['title']} / {m['source']['game']} / {m['source']['platform']} — whole-family campaign evidence inspected; source-authentic timing UNKNOWN.",'RIGHTS: evidence only; no source pixels/palette/costume/contours/layout/tracing/choreography/redistribution/close imitation.','TIMING: every decisive key INFERRED / STREET_FIGHTER-CAPCOM; ONES/TWOS/FOURS are display classes.','VISIBLE LAW: # static patch | abandoned patch : slip trail. Normal contact persists through slip; custody is NONE.']
 for q in m['keys']:
  full=fr(st(q)).splitlines(); mini='\n'.join((full[y]+' '*82)[22:82].rstrip() for y in range(7,27,2))
  out += ['='*72,f"{q['id']} {q['phase']} [{q['timing_class']}/{q['timing_provenance']}]",f"contact={q['contact']} | custody=NONE | support={q['support']} | force={q['force_owner']} | patch={q['patch']}",f"role={q['role']} | arc={q['arc']}",mini]
 return '\n'.join(out)+'\n'
def gz(s):return base64.b64encode(gzip.compress(s.encode(),compresslevel=9,mtime=0)).decode()
def spa(m,a,v):
 A=gz(a);J=gz(json.dumps(m,separators=(',',':'),ensure_ascii=True));V=base64.b64encode(v).decode()
 return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+m['experiment_id']+'</title><style>html,body{margin:0;background:#0b0b0b;color:#eee;font-family:system-ui}nav{position:sticky;top:0;background:#111;padding:8px}button[data-view]{margin-right:8px;padding:8px 14px}section{display:none;padding:12px}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{display:block;max-width:100%;height:auto;margin:auto}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video id="v" controls autoplay loop muted playsinline></video></section><script>const A="'+A+'",J="'+J+'",V="'+V+'";async function d(s){return new TextDecoder().decode(await new Response(new Blob([Uint8Array.from(atob(s),c=>c.charCodeAt(0))]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer())}(async()=>{a.textContent=await d(A);j.textContent=await d(J);v.src="data:video/mp4;base64,"+V})();document.querySelectorAll("button[data-view]").forEach(b=>b.onclick=()=>{document.querySelectorAll("section").forEach(s=>s.classList.remove("active"));document.getElementById(b.dataset.view).classList.add("active")});</script></body></html>'
def main():
 m=json.loads(M.read_text());a=sheet(m);A.write_text(a)
 if T.exists():shutil.rmtree(T)
 F.mkdir(parents=True);font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',7);q=seq(m)
 for i,k in enumerate(q):
  im=Image.new('RGB',(480,270),(8,8,8));d=ImageDraw.Draw(im);d.text((8,6),f"{k['id']} {k['phase']}",font=font,fill=(245,245,245));d.text((8,17),f"CONTACT {k['contact']} | SUPPORT {k['support']} | FORCE {k['force_owner']}",font=font,fill=(200,200,200));d.multiline_text((8,31),fr(k),font=font,fill=(248,248,248),spacing=-1);im.save(F/f'f-{i:04d}.png')
 subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(F/'f-%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','40','-pix_fmt','yuv420p','-movflags','+faststart',str(V)],check=True)
 v=V.read_bytes();m['motion_dungeon']['media_sha256']=hashlib.sha256(v).hexdigest();m['motion_dungeon']['media_bytes']=len(v);m['motion_dungeon']['frames']=len(q);M.write_text(json.dumps(m,separators=(',',':'),ensure_ascii=True));a=sheet(m);A.write_text(a);S.write_text(spa(m,a,v));print(json.dumps({'frames':len(q),'sha256':hashlib.sha256(v).hexdigest(),'bytes':len(v),'spa_bytes':S.stat().st_size},sort_keys=True))
if __name__=='__main__':main()
