#!/usr/bin/env python3
from __future__ import annotations
import argparse,base64,gzip,hashlib,html,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
D=Path(__file__).resolve().parent; M=D/'motion.json'; C=D/'contact-sheet.txt'; V=D/'scoped-freeze-release-repair.motion.mp4'; H=D/'scoped-freeze-release-repair.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}; GW,GH=39,21
LINKS=[('root','chest'),('chest','neck'),('neck','head'),('chest','left_shoulder'),('left_shoulder','left_elbow'),('left_elbow','left_hand'),('chest','right_shoulder'),('right_shoulder','right_elbow'),('right_elbow','right_hand'),('root','left_hip'),('left_hip','left_knee'),('left_knee','left_foot'),('root','right_hip'),('right_hip','right_knee'),('right_knee','right_foot')]
MARK={'root':'@','chest':'+','neck':':','head':'O','left_shoulder':'o','left_elbow':'o','left_hand':'A','right_shoulder':'o','right_elbow':'o','right_hand':'B','left_hip':'o','left_knee':'o','left_foot':'L','right_hip':'o','right_knee':'o','right_foot':'R'}
def sh(b):return hashlib.sha256(b).hexdigest()
def line(a,b):
 x,y=a;X,Y=b;dx=abs(X-x);sx=1 if x<X else -1;dy=-abs(Y-y);sy=1 if y<Y else -1;e=dx+dy;o=[]
 while 1:
  o.append((x,y))
  if (x,y)==(X,Y):return o
  q=2*e
  if q>=dy:e+=dy;x+=sx
  if q<=dx:e+=dx;y+=sy
def glyph(a,b):
 dx=b[0]-a[0];dy=b[1]-a[1]
 return '-' if abs(dx)>2*abs(dy) else '|' if abs(dy)>2*abs(dx) else ('\\' if dx*dy>0 else '/')
def art(joints,gate='OPEN'):
 j={n:tuple(v) for n,v in joints.items()};g=[[' ']*GW for _ in range(GH)]
 def p(x,y,c):
  if 0<=x<GW and 0<=y<GH:g[y][x]=c
 for a,b in LINKS:
  for x,y in line(j[a],j[b])[1:-1]:
   if g[y][x]==' ':p(x,y,glyph(j[a],j[b]))
 for n,(x,y) in j.items():p(x,y,MARK[n])
 for x in range(8,31):p(x,19,'=')
 p(12,19,'^');p(26,19,'^');p(j['head'][0],1,{'OPEN':'g','FREEZE_B':'F','RELEASE_B':'R'}[gate]);bx,by=j['right_hand']
 if gate=='FREEZE_B':p(bx-1,by,'[');p(bx+1,by,']')
 if gate=='RELEASE_B':p(bx-1,by,'<');p(bx+1,by,'>')
 return '\n'.join(''.join(r).rstrip() for r in g)
def ease(t,k):return t*t if k=='EASE_IN' else 1-(1-t)**2 if k=='EASE_OUT' else t*t*(3-2*t) if k=='SMOOTHSTEP' else t
def interp(a,b,t,bias):
 o={}
 for n,p in a.items():
  if 'foot' in n:o[n]=p;continue
  q=b[n];m=1.5 if 'hand' in n else 1 if 'elbow' in n else .45;cx=(p[0]+q[0])/2+bias[0]*m;cy=(p[1]+q[1])/2+bias[1]*m;u=1-t;o[n]=[round(u*u*p[0]+2*u*t*cx+t*t*q[0]),round(u*u*p[1]+2*u*t*cy+t*t*q[1])]
 return o
def frames(m):
 out=[];ks=m['keys']
 for i,k in enumerate(ks):
  a=art(k['pose_rig']['joints'],k['pose_rig']['gate_state']);out += [a]*HOLD[k['timing_class']];n=ks[(i+1)%len(ks)];s=k['bridge_to_next'];q=int(s.get('frames',0))
  ok=not n.get('event') and not(k.get('event') and k['pose_rig']['gate_state']!=n['pose_rig']['gate_state'])
  if q and ok:
   for z in range(1,q+1):out.append(art(interp(k['pose_rig']['joints'],n['pose_rig']['joints'],ease(z/(q+1),s['easing']),s['arc_bias']),k['pose_rig']['gate_state']))
 return out
def sheet(m):
 o=['ASCII KINESIS V2 TIMING 006 — SCOPED FREEZE / RELEASE REPAIR',f"revises: {m['revises']}",f"negative_fixture: {m['negative_fixture']}",'SOURCE ART: NONE | SOURCE TIMING OBSERVED: NONE | AUTHORED TIMING: INFERRED','POLICY: STREET_FIGHTER/CAPCOM | ONES=1 display frame | TWOS=2 | FOURS=4 | 1s/2s/4s are classes, never seconds','']
 for k in m['keys']:o += [f"[{k['key_id']}] {k['name']}",f"pose/rig={k['pose_rig']['rig_id']} | support/contact={k['support_contact']}",f"root/motion-arc={k['motion_arc_root_note']}",f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']}",f"causal_role={k['causal_role']}",f"clocks BASE={k['clock_state']['BASE']} | A={k['clock_state']['SIGNAL_A']} | B={k['clock_state']['SIGNAL_B']} | GATE={k['clock_state']['GATE']}",art(k['pose_rig']['joints'],k['pose_rig']['gate_state']),'']
 return '\n'.join(o).rstrip()+'\n'
def png(txt,p):
 f=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',7);im=Image.new('RGB',(240,150),'black');d=ImageDraw.Draw(im);d.text((5,3),'SCOPED FREEZE / RELEASE',font=f,fill='white');d.multiline_text((5,16),txt,font=f,fill='white',spacing=0);im.save(p)
def spa(m,s,v):
 pack=lambda x:base64.b64encode(gzip.compress(x.encode(),mtime=0)).decode(); vid=base64.b64encode(v).decode()
 page='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>:root{color-scheme:dark;background:#101010;color:#eee}body{margin:1rem;font-family:system-ui}nav{display:flex;gap:.5rem}section[hidden]{display:none}pre{font-family:ui-monospace,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto}video{max-width:100%;image-rendering:auto}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="a"></pre></section><section id="json" hidden><pre id="j"></pre></section><section id="video" hidden><video controls autoplay muted loop playsinline><source src="data:video/mp4;base64,__V__" type="video/mp4"></video></section><script>const P={a:"__A__",j:"__J__"};async function u(x){let b=Uint8Array.from(atob(x),c=>c.charCodeAt(0)),d=new DecompressionStream('gzip');return new TextDecoder().decode(await new Response(new Blob([b]).stream().pipeThrough(d)).arrayBuffer())}(async()=>{a.textContent=await u(P.a);j.textContent=await u(P.j)})();let B=[...document.querySelectorAll('button[data-view]')],S=[...document.querySelectorAll('section')];B.forEach(b=>b.onclick=()=>S.forEach(s=>s.hidden=s.id!=b.dataset.view));</script></body></html>'''
 return page.replace('__V__',vid).replace('__A__',pack(s)).replace('__J__',pack(json.dumps(m,ensure_ascii=False,separators=(',',':'),sort_keys=True)))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--bootstrap',action='store_true');a=ap.parse_args();m=json.loads(M.read_text());s=sheet(m);C.write_text(s);q=frames(m)
 if len(q)!=m['compile']['semantic_frames_per_loop']:raise SystemExit('frame-count mismatch')
 with tempfile.TemporaryDirectory() as td:
  td=Path(td)
  for i,x in enumerate(q):png(x,td/f'f{i:03d}.png')
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','24','-i',str(td/'f%03d.png'),'-c:v','libx264','-preset','veryslow','-crf','40','-pix_fmt','yuv420p','-movflags','+faststart',str(V)],check=True)
 v=V.read_bytes();mh=sh(v);ah=sh(s.encode())
 if a.bootstrap or m['compile']['media_sha256']=='PENDING':m['compile']['media_sha256']=mh;m['compile']['media_bytes']=len(v);m['ascii_sheet_sha256']=ah;M.write_text(json.dumps(m,ensure_ascii=False,separators=(',',':'),sort_keys=True))
 elif mh!=m['compile']['media_sha256'] or ah!=m['ascii_sheet_sha256']:raise SystemExit('hash mismatch')
 m=json.loads(M.read_text());p=spa(m,s,v);H.write_text(p);print(json.dumps({'ok':True,'media_sha256':mh,'media_bytes':len(v),'html_sha256':sh(p.encode()),'ascii_sha256':ah,'frames':len(q)},sort_keys=True))
if __name__=='__main__':main()
