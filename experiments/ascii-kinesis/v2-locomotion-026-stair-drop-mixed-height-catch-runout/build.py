#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,json,math,subprocess
from pathlib import Path
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent; M=json.loads((HERE/'motion.json').read_text(encoding='utf-8')); W,H=M['rig']['viewport']; FPS=M['timing']['fps']
F=HERE/'_frames'; MP4=HERE/'_authoritative.mp4'; ASCII=HERE/'contact-sheet.txt'; SPA=HERE/'stair-drop-mixed-height-catch-runout.motion.html'
def body(k):
 rx,ry=k['root']; a=math.radians(k['torso_lean_deg']); vx,vy=math.sin(a),-math.cos(a); chest=(rx+vx*43,ry+vy*43); head=(chest[0]+vx*25,chest[1]+vy*25); lag=math.radians(k['arm_lag_deg']); sh=(chest[0],chest[1]+4); lead=(sh[0]+math.cos(lag)*31,sh[1]+math.sin(lag)*31); trail=(sh[0]-math.cos(lag)*26,sh[1]-math.sin(lag)*26); return {'root':(rx,ry),'com':tuple(k['com']),'chest':chest,'head':head,'lf':tuple(k['left_foot']),'rf':tuple(k['right_foot']),'lead':lead,'trail':trail}
def sup(s): return s.startswith('PLANTED') or s.startswith('UNLOADING')
def draw(k,path):
 im=Image.new('RGB',(W,H),(14,16,20)); d=ImageDraw.Draw(im); t=M['rig']['terrain_model']; ex,uy,ly=t['edge_x'],t['upper_y'],t['lower_y']; d.line((22,uy,ex,uy),fill=(90,97,107),width=4); d.line((ex,uy,ex,ly),fill=(90,97,107),width=4); d.line((ex,ly,W-20,ly),fill=(90,97,107),width=4); pts=[tuple(q['root']) for q in M['keys']]; d.line(pts,fill=(55,61,70),width=3); p=body(k); root=p['root']; com=p['com']
 for nm,side in [('lf','left'),('rf','right')]:
  foot=p[nm]; knee=((foot[0]+root[0])/2+(8 if side=='left' else -8),(foot[1]+root[1])/2-6); d.line((*root,*knee,*foot),fill=(180,190,204),width=4); state=k['support'][side]
  if sup(state): d.ellipse((foot[0]-8,foot[1]-5,foot[0]+8,foot[1]+5),fill=(101,204,147)); d.line((*foot,*com),fill=(101,204,147),width=2)
  elif state=='PROBE': d.ellipse((foot[0]-8,foot[1]-5,foot[0]+8,foot[1]+5),outline=(241,180,92),width=3)
  else: d.ellipse((foot[0]-7,foot[1]-4,foot[0]+7,foot[1]+4),outline=(235,239,244),width=2)
 d.line((*p['root'],*p['chest']),fill=(236,239,244),width=6); d.line((*p['chest'],*p['lead']),fill=(180,190,204),width=4); d.line((*p['chest'],*p['trail']),fill=(180,190,204),width=4); hx,hy=p['head']; d.ellipse((hx-9,hy-9,hx+9,hy+9),outline=(236,239,244),width=4); rx,ry=root; d.polygon([(rx,ry-7),(rx+7,ry),(rx,ry+7),(rx-7,ry)],outline=(246,204,88),width=3); cx,cy=com; d.ellipse((cx-5,cy-5,cx+5,cy+5),fill=(225,126,150)); d.text((12,10),f"{k['key_id']} {k['name']}",fill=(150,160,174)); d.text((12,28),f"owner {k['support']['owner']} | {k['phase']} | rootΔ {k['root_spacing_px']} | {k['timing_class']}",fill=(114,126,141)); d.text((12,46),'upper tread → step down → lower tread',fill=(114,126,141)); im.save(path)
def gridline(g,a,b,ch):
 x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy
 while True:
  if 0<=y0<len(g) and 0<=x0<len(g[0]):g[y0][x0]=ch
  if x0==x1 and y0==y1:break
  e=2*err
  if e>=dy:err+=dy;x0+=sx
  if e<=dx:err+=dx;y0+=sy
def tg(pt): x,y=pt; return int(round((x-35)/(W-70)*83)),int(round((y-105)/(H-115)*23))
def pose(k):
 g=[[' ']*84 for _ in range(24)];t=M['rig']['terrain_model']; ex,uy,ly=t['edge_x'],t['upper_y'],t['lower_y']; gridline(g,tg((40,uy)),tg((ex,uy)),'_');gridline(g,tg((ex,uy)),tg((ex,ly)),'|');gridline(g,tg((ex,ly)),tg((W-25,ly)),'_'); p=body(k)
 for nm in ('lf','rf'):gridline(g,tg(p[nm]),tg(p['root']),'/')
 gridline(g,tg(p['root']),tg(p['chest']),'|');gridline(g,tg(p['chest']),tg(p['lead']),'-');gridline(g,tg(p['chest']),tg(p['trail']),'-')
 for nm,ch in [('head','O'),('chest','T'),('root','@'),('com','c')]: x,y=tg(p[nm]); g[y][x]=ch
 for nm,side in [('lf','left'),('rf','right')]: x,y=tg(p[nm]);s=k['support'][side];g[y][x]='*' if sup(s) else ('?' if s=='PROBE' else '~')
 return '\n'.join(''.join(r).rstrip() for r in g)
def contact():
 out=['ASCII KINESIS V2 · LOCOMOTION 026 · STAIR DROP / MIXED-HEIGHT CATCH / RUNOUT','legend: @ root · c COM · * trusted support · ? probe · ~ free foot · upper/lower tread explicitly drawn','source evidence: Bullwinkle / The Adventures of Rocky and Bullwinkle and Friends / NES / TSR 81106 / Home Center 1zQGdJx7uIqTnvJlHp2NfydUu_EDDNvt01tCAlQvlYQ8','OBSERVED: whole static sheet exposes Charge, Idle, Using Stairs, Walking; Using Stairs is distinct from level Walking; Animated GIFs (0).','UNKNOWN: source-authentic stair direction, chronology, exposures, root displacement, tread height, contact frame, timing.','INFERRED / STREET_FIGHTER-CAPCOM: all decisive geometry, support authority, spacing and timing. Evidence-only rights firewall; no source pixels/audio/tracing/close imitation.','collision authority: canonical first creation 5e2e42f8298e6c96d7ea0501bc18622a28000602; later ladder-dismount 026 is preserved NON_AUTHORITATIVE_SUCCESSOR_CHURN.','thesis: lower contact must earn authority before root height drops; horizontal momentum survives the height transaction into an overlong first bottom catch and shorter debt-paying corrections.','']
 for k in M['keys']:
  out += [f"{k['key_id']} {k['name']} · {k['timing_class']}/{k['hold_frames']}f · {k['timing_provenance']} · support={k['support']['owner']} · phase={k['phase']} · rootΔ={k['root_spacing_px']}px · lean={k['torso_lean_deg']:+}° · armLag={k['arm_lag_deg']:+}°",pose(k),f"causal: {k['causal_role']}",'']
 return '\n'.join(out).rstrip()+'\n'
def spa(a,j,v):
 A=base64.b64encode(gzip.compress(a.encode(),mtime=0)).decode();J=base64.b64encode(gzip.compress(j.encode(),mtime=0)).decode();V=base64.b64encode(v).decode();
 return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Locomotion 026</title><style>:root{{color-scheme:dark}}body{{margin:0;background:#0f1114;color:#edf0f3;font-family:system-ui}}header,main{{padding:14px 18px}}nav{{display:flex;gap:8px}}button{{padding:7px 12px;background:#1a1e24;color:inherit;border:1px solid #4a515d}}pre{{font-family:ui-monospace,monospace;white-space:pre;overflow:auto;line-height:1.05;border:1px solid #343943;padding:12px;max-height:78vh}}video{{width:min(100%,960px);background:#000}}section[hidden]{{display:none}}</style></head><body><header><h1>Locomotion 026 · Stair Drop / Mixed-Height Catch / Runout</h1><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav></header><main><section id="ascii"><pre id="ap"></pre></section><section id="json" hidden><pre id="jp"></pre></section><section id="video" hidden><video id="vp" controls loop muted playsinline></video></section></main><script>const A={json.dumps(A)},J={json.dumps(J)},V={json.dumps(V)};async function z(s){{let b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream('gzip'))).text()}}Promise.all([z(A),z(J)]).then(x=>{{ap.textContent=x[0];jp.textContent=x[1]}});vp.src='data:video/mp4;base64,'+V;let bs=[...document.querySelectorAll('button[data-view]')];for(let b of bs)b.onclick=()=>{{for(let s of document.querySelectorAll('main section'))s.hidden=s.id!==b.dataset.view}};</script></body></html>"""
def main():
 F.mkdir(exist_ok=True); [p.unlink() for p in F.glob('*.png')];i=0
 for k in M['keys']:
  for _ in range(k['hold_frames']):draw(k,F/f'frame-{i:04d}.png');i+=1
 assert i==M['timing']['total_frames']; subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(F/'frame-%04d.png'),'-vf','scale=480:270:flags=neighbor','-c:v','libx264','-preset','veryslow','-crf','40','-pix_fmt','yuv420p','-movflags','+faststart','-metadata','creation_time=1970-01-01T00:00:00Z',str(MP4)],check=True);a=contact();ASCII.write_text(a);j=(HERE/'motion.json').read_text();SPA.write_text(spa(a,j,MP4.read_bytes()))
if __name__=='__main__':main()
