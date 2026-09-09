#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,hashlib,json,math,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
R=Path(__file__).resolve().parent; M=R/'motion.json'; A=R/'contact-sheet.txt'; S=R/'slack-taut-tension-coupling.motion.html'; T=R/'.motion-build'; F=T/'frames'; V=T/'motion.mp4'
W,H=96,29; FPS=24; JOINTS=['head','shoulder','pelvis','hand_f','hand_b','knee_f','knee_b','foot_f','foot_b']; EXP={'ONES':1,'TWOS':2,'FOURS':4}
def pose(p): return {j:[float(p[i][0]),float(p[i][1])] for i,j in enumerate(JOINTS)}
def cells(a,b):
 x0,y0=map(round,a); x1,y1=map(round,b); x0,y0,x1,y1=map(int,(x0,y0,x1,y1)); dx=abs(x1-x0); dy=-abs(y1-y0); sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1; e=dx+dy; o=[]
 while True:
  o.append((x0,y0))
  if x0==x1 and y0==y1:return o
  e2=2*e
  if e2>=dy:e+=dy;x0+=sx
  if e2<=dx:e+=dx;y0+=sy
def paint(g,a,b,ch,over=False):
 for x,y in cells(a,b):
  if 0<=x<W and 0<=y<H and (over or g[y][x]==' '):g[y][x]=ch
def sch(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 return '-' if abs(dx)>abs(dy)*1.7 else ('|' if abs(dy)>abs(dx)*1.7 else ('\\' if dx*dy>0 else '/'))
def ascii_frame(st):
 g=[[' ']*W for _ in range(H)]; a=st['A']; an=st['anchor']; ax,ay=map(lambda z:int(round(z)),an)
 if 1<=ax<W-1 and 0<=ay<H:g[ay][ax-1:ax+2]=['[','D',']']
 sh=a['shoulder']; c=st['contact']
 if c=='ATTACHED_SLACK':mid=[(an[0]+sh[0])/2,(an[1]+sh[1])/2+5];paint(g,an,mid,'~');paint(g,mid,sh,'~')
 elif c=='TAUT_ELIGIBLE':mid=[(an[0]+sh[0])/2,(an[1]+sh[1])/2+1.5];paint(g,an,mid,'~');paint(g,mid,sh,'~')
 else:paint(g,an,sh,'=',True);mx,my=map(lambda z:int(round(z)),[(an[0]+sh[0])/2,(an[1]+sh[1])/2]);g[my][mx]='@' if 0<=mx<W and 0<=my<H else g[my][mx]
 for p,q in [('head','shoulder'),('shoulder','pelvis'),('shoulder','hand_f'),('shoulder','hand_b'),('pelvis','knee_f'),('knee_f','foot_f'),('pelvis','knee_b'),('knee_b','foot_b')]:paint(g,a[p],a[q],sch(a[p],a[q]))
 for n,ch in [('head','A'),('shoulder','O'),('pelvis','X'),('hand_f','*'),('hand_b','*'),('knee_f','o'),('knee_b','o'),('foot_f','^'),('foot_b','^')]:
  x,y=map(lambda z:int(round(z)),a[n]);
  if 0<=x<W and 0<=y<H:g[y][x]=ch
 fo=st.get('force',[0,0])
 if fo!=[0,0]:
  o=a['pelvis'];e=[o[0]+fo[0]*1.4,o[1]+fo[1]*1.2];paint(g,o,e,'+');ex,ey=map(lambda z:int(round(z)),e)
  if 0<=ex<W and 0<=ey<H:g[ey][ex]=('<' if fo[0]<0 else '>') if abs(fo[0])>=abs(fo[1]) else ('^' if fo[1]<0 else 'v')
 return '\n'.join(''.join(r).rstrip() for r in g)
def state(q):return {'id':q['id'],'phase':q['p'],'A':pose(q['a']),'anchor':q['anchor'],'contact':q['contact'],'custody':q['custody'],'support':q['support'],'force_owner':q['force_owner'],'force':q['force']}
def lerp(a,b,t):return[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]
def ip(a,b,t,c=0):
 s=t*t*(3-2*t);o={}
 for n in a:
  x=a[n][0]+(b[n][0]-a[n][0])*s;y=a[n][1]+(b[n][1]-a[n][1])*s
  if n in ('head','hand_f','hand_b','knee_f','foot_f'):y+=c*math.sin(math.pi*t)
  o[n]=[x,y]
 return o
def seq(m):
 counts={'C015-K0':2,'C015-K1':2,'C015-K2':1,'C015-K3':2,'C015-K4':3,'C015-K5':2,'C015-K6':2,'C015-K7':2,'C015-K8':2};curves={'C015-K0':.2,'C015-K1':.5,'C015-K2':.2,'C015-K3':-1,'C015-K4':-1.2,'C015-K5':.9,'C015-K6':.6,'C015-K7':-.4,'C015-K8':.2};o=[]
 for i,q in enumerate(m['keys']):
  k=state(q);o.extend([k]*EXP[q['timing']])
  if i+1<len(m['keys']):
   n=state(m['keys'][i+1]);c=counts.get(q['id'],0)
   for j in range(1,c+1):t=j/(c+1);o.append({**k,'id':q['id']+'~'+n['id'],'phase':'AUTHORED_CONNECTIVE','A':ip(k['A'],n['A'],t,curves.get(q['id'],0)),'anchor':lerp(k['anchor'],n['anchor'],t),'force':lerp(k['force'],n['force'],t)})
 return o
def sheet(m):
 s=m['source'];r=m['revision'];p=[m['experiment_id'],m['principle'],f"REVISION: kind={r['kind']} | revises={r['revises']} | negative_fixture={r['negative_fixture']} | source_change={r['source_change']}",f"SOURCE EVIDENCE: TSR asset {s['asset_id']}, {s['title']} — {s['game']} — {s['platform']}; commissioned whole 576x720 sheet record re-inspected after fresh preflight.","OBSERVED SOURCE HOOK: whole-sheet record includes Parachute / Soldier descends by parachute among eight named families; this earns an external-drag relationship problem, not this synthetic choreography.","RIGHTS: evidence only; independent generic ASCII body+tether+drag plate; no source pixels/palette/costume/contours/layout/tracing/choreography/redistribution/close imitation; Drew work not used.","TIMING: all decisive keys INFERRED / STREET_FIGHTER-CAPCOM; ONES/TWOS/FOURS are display classes, never seconds.","VISIBLE LAW: [D] is generic external drag; ~ means ATTACHED BUT SLACK (zero load); =/@ means TAUT load path. CUSTODY and body support remain NONE."];out=['\n'.join(p)]
 for q in m['keys']:
  meta=f"{q['id']}  {q['p']}  [{q['timing']}/{q['provenance']}]\ncontact={q['contact']} | custody={q['custody']} | support={q['support']} | force_owner={q['force_owner']}\nforce={q['force']} | anchor={q['anchor']}\nrole={q['role']}\narc={q['arc']}";out.append(meta+'\n'+ascii_frame(state(q)))
 return ('\n'+'='*96+'\n').join(out)+'\n'
def gz(t):return base64.b64encode(gzip.compress(t.encode(),compresslevel=9,mtime=0)).decode()
def chunks(s,n=960):return ',\n'.join(json.dumps(s[i:i+n]) for i in range(0,len(s),n))
def spa(m,a,v):
 aa=gz(a);jj=gz(json.dumps(m,separators=(',',':'),ensure_ascii=True));vv=base64.b64encode(v).decode()
 return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{m['experiment_id']}</title><style>html,body{{margin:0;background:#0b0b0b;color:#eee;font-family:system-ui,sans-serif}}nav{{position:sticky;top:0;background:#111;padding:8px;border-bottom:1px solid #444}}button[data-view]{{margin-right:8px;padding:8px 14px}}section{{display:none;padding:12px}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.08}}video{{display:block;max-width:100%;height:auto;margin:auto}}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video id="v" controls autoplay loop muted playsinline></video></section><script>const A=[{chunks(aa)}].join('');const J=[{chunks(jj)}].join('');const V=[{chunks(vv)}].join('');const D=async s=>new TextDecoder().decode(await new Response(new Blob([Uint8Array.from(atob(s),c=>c.charCodeAt(0))]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());(async()=>{{document.getElementById('a').textContent=await D(A);document.getElementById('j').textContent=await D(J);document.getElementById('v').src='data:video/mp4;base64,'+V;}})();document.querySelectorAll('button[data-view]').forEach(b=>b.addEventListener('click',()=>{{document.querySelectorAll('section').forEach(s=>s.classList.remove('active'));document.getElementById(b.dataset.view).classList.add('active')}}));</script></body></html>'''
def main():
 m=json.loads(M.read_text());a=sheet(m);A.write_text(a);
 if T.exists():shutil.rmtree(T)
 F.mkdir(parents=True);font='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf';mf=ImageFont.truetype(font,9);sf=ImageFont.truetype(font,9);q=seq(m)
 for i,k in enumerate(q):
  im=Image.new('RGB',(640,360),(8,8,8));d=ImageDraw.Draw(im);d.text((10,8),f"{k['id']}  {k['phase']}",font=sf,fill=(245,245,245));d.text((10,24),f"RELATION {k['contact']}   CUSTODY {k['custody']}   BODY SUPPORT {k['support']}",font=sf,fill=(205,205,205));d.text((10,40),f"FORCE OWNER {k['force_owner']}   FORCE {k['force']}",font=sf,fill=(175,175,175));d.multiline_text((10,62),ascii_frame(k),font=mf,fill=(248,248,248),spacing=-2);im.save(F/f'f-{i:04d}.png')
 subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(F/'f-%04d.png'),'-c:v','libx264','-preset','medium','-crf','39','-pix_fmt','yuv420p','-movflags','+faststart',str(V)],check=True);v=V.read_bytes();h=hashlib.sha256(v).hexdigest();e=m['motion_dungeon'].get('media_sha256');
 if e and h!=e:raise SystemExit(f'media hash mismatch expected={e} got={h}')
 S.write_text(spa(m,a,v));print(json.dumps({'frames':len(q),'media_sha256':h,'media_bytes':len(v),'sheet_sha256':hashlib.sha256(a.encode()).hexdigest(),'spa_sha256':hashlib.sha256(S.read_bytes()).hexdigest()},sort_keys=True))
if __name__=='__main__':main()
