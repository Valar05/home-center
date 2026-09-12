#!/usr/bin/env python3
from pathlib import Path
import base64,gzip,hashlib,html,json,subprocess,tempfile
from PIL import Image,ImageDraw
R=Path(__file__).resolve().parent;M=R/'motion.json';S=R/'contact-sheet.txt';P=R/'scoped-sync-grapple-root-com-transfer-repair.motion.html';V=R/'.motion.mp4'
W,H,F=80,24,21

def put(g,p,c):
 if p is None:return
 x,y=map(lambda z:int(round(z)),p)
 if 0<=x<W and 0<=y<H:g[y][x]=c

def line(g,a,b,c=None):
 x0,y0=map(lambda z:int(round(z)),a);x1,y1=map(lambda z:int(round(z)),b);dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
 if c is None:c='-' if abs(x1-x0)>abs(y1-y0)*1.7 else ('|' if abs(y1-y0)>abs(x1-x0)*1.7 else ('\\' if (x1-x0)*(y1-y0)>0 else '/'))
 while 1:
  if 0<=x0<W and 0<=y0<H and g[y0][x0]==' ':g[y0][x0]=c
  if x0==x1 and y0==y1:break
  q=2*e
  if q>=dy:e+=dy;x0+=sx
  if q<=dx:e+=dx;y0+=sy

def body(g,p,l):
 for a,b in [('shoulder_l','shoulder_r'),('shoulder_l','pelvis'),('shoulder_r','pelvis'),('shoulder_l','hand_l'),('shoulder_r','hand_r'),('pelvis','foot_l'),('pelvis','foot_r')]:line(g,p[a],p[b])
 n=[(p['shoulder_l'][0]+p['shoulder_r'][0])/2,(p['shoulder_l'][1]+p['shoulder_r'][1])/2];line(g,n,p['head'],'|');put(g,p['head'],l);put(g,p['pelvis'],l.lower())
 for j in ('hand_l','hand_r','shoulder_l','shoulder_r'):put(g,p[j],'+')
 put(g,p['foot_l'],'L');put(g,p['foot_r'],'R')

def support(g,p,s):
 put(g,[p['foot_l'][0],F-1],'^' if 'L!' in s else ('.' if 'L.' in s else ' '))
 put(g,[p['foot_r'][0],F-1],'^' if 'R!' in s else ('.' if 'R.' in s else ' '))

def frame(k):
 g=[[' ']*W for _ in range(H)]
 for x in range(W):g[F][x]='_'
 body(g,k['A'],'A');body(g,k['B'],'B');support(g,k['A'],k['support_A']);support(g,k['B'],k['support_B'])
 if k.get('force_axis'):line(g,k['force_axis'][0],k['force_axis'][1],':')
 if k.get('relationship_center') is not None:put(g,k['relationship_center'],'X')
 for a in k.get('anchors',[]):put(g,a,'*')
 for a in k.get('arrows',[]):line(g,a['from'],a['to'],a.get('ch',':'));put(g,a['to'],a.get('tip','>'))
 return '\n'.join(''.join(r).rstrip() for r in g)

def crop(t):
 rs=t.splitlines();ys=[i for i,r in enumerate(rs) if r.strip()]
 if not ys:return ''
 lo,hi=min(ys),max(ys);block=rs[lo:hi+1]
 bodyrows=[r for r in block if r.strip() and set(r.strip())!={'_'}]
 xs=[]
 for r in bodyrows:
  for i,c in enumerate(r):
   if c!=' ':xs.append(i)
 x0=max(0,min(xs)-2);x1=min(W,max(xs)+3)
 return '\n'.join(r[x0:x1].rstrip() for r in block)

def sheet(m):
 s=m['source'];r=m['revision'];o=[m['experiment_id'],m['primitive'],f"RESET={m['reset_issue_comment']} | CHRONOLOGY={m['chronology_bind_issue_comment']} | CHURN_REBIND={m['successor_churn_rebind_issue_comment']}",f"REVISES={r['revises']} | NEGATIVE_FIXTURE={r['negative_fixture']} | SOURCE_CHANGE=false",f"QUARANTINED_LATER_CHURN={r['later_churn_quarantined']}",f"SOURCE=TSR asset {s['asset_id']} | {s['name']} | {s['game']} | {s['platform']}",f"EVIDENCE=Home Center {s['evidence_document_id']} | raw_sha256={s['raw_sha256']}",'SOURCE_TIMING=UNKNOWN | timing_authority=false | roles=POSE_REFERENCE + CONTACT_TOPOLOGY_REFERENCE','RIGHTS=evidence only; no source pixels/palette/costume/exact silhouette/choreography/tracing/redistribution.','LEGEND=A/B heads, a/b roots, +=joint, L/R feet, ^=trusted/braking, .=light/released, *=anchor, X=relationship center, :=force/arc.','CAUSAL='+m['direction']['sentence'],'']
 for k in m['keys']:o+=['='*72,f"{k['key_id']} {k['name']} | {k['timing_class']} | hold={k['hold_frames']} | {k['timing_provenance']}",f"CONTACT={k['contact_state']} | CUSTODY={k['custody']} | ROOT_OWNER={k['root_owner']}",f"SUPPORT_A={k['support_A']} | SUPPORT_B={k['support_B']}",f"ROLE={k['causal_role']}",f"ARC={k['motion_arc_root_note']}",crop(frame(k)),'']
 return '\n'.join(o).rstrip()+'\n'

SEG={'A':[((0,1),(.5,0)),((.5,0),(1,1)),((.22,.58),(.78,.58))],'B':[((0,0),(0,1)),((0,0),(.65,0)),((.65,0),(1,.25)),((1,.25),(.65,.5)),((0,.5),(.65,.5)),((.65,.5),(1,.75)),((1,.75),(.65,1)),((.65,1),(0,1))],'a':[((.2,.45),(.5,.2)),((.5,.2),(.8,.45)),((.8,.45),(.5,.72)),((.5,.72),(.2,.45))],'b':[((.15,0),(.15,1)),((.15,.45),(.65,.3)),((.65,.3),(.9,.55)),((.9,.55),(.65,.82)),((.65,.82),(.15,.7))],'L':[((.1,0),(.1,1)),((.1,1),(.9,1))],'R':[((.1,0),(.1,1)),((.1,0),(.7,0)),((.7,0),(.9,.25)),((.9,.25),(.7,.5)),((.7,.5),(.1,.5)),((.5,.5),(.95,1))]}
def glyph(d,c,x,y,cw,ch):
 p=lambda u,v:(x+2+u*(cw-4),y+2+v*(ch-4));q=(245,245,245);w=2
 if c==' ':return
 if c=='_':d.line((*p(0,1),*p(1,1)),fill=q,width=w)
 elif c=='-':d.line((*p(0,.5),*p(1,.5)),fill=q,width=w)
 elif c=='|':d.line((*p(.5,0),*p(.5,1)),fill=q,width=w)
 elif c=='/':d.line((*p(0,1),*p(1,0)),fill=q,width=w)
 elif c=='\\':d.line((*p(0,0),*p(1,1)),fill=q,width=w)
 elif c==':':d.ellipse((x+cw//2-1,y+ch//3-1,x+cw//2+1,y+ch//3+1),fill=q);d.ellipse((x+cw//2-1,y+2*ch//3-1,x+cw//2+1,y+2*ch//3+1),fill=q)
 elif c=='.':d.ellipse((x+cw//2-1,y+ch-4,x+cw//2+1,y+ch-2),fill=q)
 elif c=='+':d.line((*p(0,.5),*p(1,.5)),fill=q,width=w);d.line((*p(.5,0),*p(.5,1)),fill=q,width=w)
 elif c in '*X':d.line((*p(0,0),*p(1,1)),fill=q,width=w);d.line((*p(0,1),*p(1,0)),fill=q,width=w)
 elif c=='^':d.line((*p(0,1),*p(.5,0)),fill=q,width=w);d.line((*p(.5,0),*p(1,1)),fill=q,width=w)
 elif c=='>':d.line((*p(0,0),*p(1,.5)),fill=q,width=w);d.line((*p(1,.5),*p(0,1)),fill=q,width=w)
 elif c=='<':d.line((*p(1,0),*p(0,.5)),fill=q,width=w);d.line((*p(0,.5),*p(1,1)),fill=q,width=w)
 elif c=='v':d.line((*p(0,0),*p(.5,1)),fill=q,width=w);d.line((*p(.5,1),*p(1,0)),fill=q,width=w)
 elif c in SEG:
  for a,b in SEG[c]:d.line((*p(*a),*p(*b)),fill=q,width=w)

def raster(t,w,h):
 im=Image.new('RGB',(w,h),(7,7,7));d=ImageDraw.Draw(im);cw=w//W;ch=h//H
 for y,r in enumerate(t.splitlines()[:H]):
  for x,c in enumerate(r[:W]):glyph(d,c,x*cw,y*ch,cw,ch)
 return im

def video(m,tmp):
 fd=tmp/'frames';fd.mkdir();i=0;c=m['compile']
 for k in m['keys']:
  im=raster(frame(k),c['width'],c['height'])
  for _ in range(k['hold_frames']):im.save(fd/f'{i:04d}.png');i+=1
 p=tmp/'motion.mp4';subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(c['fps']),'-i',str(fd/'%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','30','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','encoder=ascii-kinesis-v2',str(p)],check=True);return i,p

def spa(j,a,v,e):
 z=lambda s:base64.b64encode(gzip.compress(s.encode(),9,mtime=0)).decode();b=base64.b64encode(v).decode()
 return '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(e)+'</title><style>body{background:#090909;color:#eee;font-family:system-ui;margin:0}nav{padding:10px;position:sticky;top:0;background:#111}button{margin-right:8px}section{display:none;padding:12px}section.on{display:block}pre{white-space:pre;overflow:auto;font-family:ui-monospace,Consolas,monospace;font-variant-ligatures:none}video{width:min(100%,800px)}</style><nav><button data-v="a">ASCII</button><button data-v="j">JSON</button><button data-v="v">VIDEO</button></nav><section id="a" class="on"><pre></pre></section><section id="j"><pre></pre></section><section id="v"><video controls autoplay muted loop playsinline src="data:video/mp4;base64,'+b+'"></video></section><script>const A="'+z(a)+'",J="'+z(j)+'";async function d(s){let u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new TextDecoder().decode(await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).arrayBuffer())}(async()=>{a.querySelector("pre").textContent=await d(A);j.querySelector("pre").textContent=await d(J)})();document.querySelectorAll("button").forEach(b=>b.onclick=()=>document.querySelectorAll("section").forEach(s=>s.classList.toggle("on",s.id===b.dataset.v)))</script>'

def sh(b):return hashlib.sha256(b).hexdigest()
def main():
 m=json.loads(M.read_text());j=json.dumps(m,separators=(',',':'),sort_keys=True)+'\n';a=sheet(m)
 with tempfile.TemporaryDirectory() as td:n,p=video(m,Path(td));v=p.read_bytes()
 c=m['compile'];assert n==c['frames_total'] and len(v)==c['media_bytes'] and sh(v)==c['media_sha256']
 S.write_text(a);V.write_bytes(v);P.write_text(spa(j,a,v,m['experiment_id']))
 print(json.dumps({'frames':n,'media_sha256':sh(v),'media_bytes':len(v),'motion_sha256':sh(j.encode()),'sheet_sha256':sh(a.encode()),'spa_sha256':sh(P.read_bytes())},sort_keys=True))
if __name__=='__main__':main()
