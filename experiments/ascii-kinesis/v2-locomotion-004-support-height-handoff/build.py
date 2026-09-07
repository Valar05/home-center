#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,html,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'; SPA=HERE/'support-height-handoff.motion.html'; MANIFEST=HERE/'manifest.json'; RECEIPT=HERE/'receipt.json'
REBUILD=HERE/'.rebuild'; VIDEO=REBUILD/'support-height-handoff.mp4'; HOLD={'ONES':1,'TWOS':2,'FOURS':4}
BONES=[('head','chest'),('chest','pelvis'),('chest','l_shoulder'),('l_shoulder','l_elbow'),('l_elbow','l_hand'),('chest','r_shoulder'),('r_shoulder','r_elbow'),('r_elbow','r_hand'),('pelvis','l_knee'),('l_knee','l_foot'),('pelvis','r_knee'),('r_knee','r_foot')]
def line(a,b):
 x,y=a;X,Y=b;dx=abs(X-x);sx=1 if x<X else -1;dy=-abs(Y-y);sy=1 if y<Y else -1;e=dx+dy;out=[]
 while True:
  out.append((x,y))
  if (x,y)==(X,Y): return out
  q=2*e
  if q>=dy:e+=dy;x+=sx
  if q<=dx:e+=dx;y+=sy
def ascii_pose(k,joints=None):
 g=[[' ']*30 for _ in range(13)]; j=joints or k['j']
 def put(x,y,c):
  if 0<=x<30 and 0<=y<13:g[y][x]=c
 for x in range(0,15): put(x,9,'_')
 for x in range(15,30): put(x,11,'_')
 put(15,10,'|')
 for a,b in BONES:
  q=j[a];w=j[b];dx=w[0]-q[0];dy=w[1]-q[1]
  c='-' if abs(dx)>abs(dy) else ('|' if abs(dy)>abs(dx) else ('\\' if dx*dy>0 else '/'))
  for x,y in line(q,w)[1:-1]:put(x,y,c)
 for n,(x,y) in j.items():put(x,y,'O' if n=='head' else ('+' if n in {'chest','pelvis'} else 'o'))
 for n,c in k.get('contacts',{}).items():
  if c.strip(): x,y=j[n];put(x,y,c)
 return '\n'.join(''.join(row).rstrip() for row in g)
def sheet(d):
 return '\n\n'.join(f"[{k['key_id']}] {k['name']} | {k['timing_class']} | {k['timing_provenance']}\nSUPPORT={k['support_contact']} | ROOT_OWNER={k['root_owner']}\n{k['motion_arc_root_note']}\n{ascii_pose(k)}" for k in d['keys'])
def frames(d):
 out=[]
 for i,k in enumerate(d['keys']):
  out += [(k['key_id'],ascii_pose(k))]*HOLD[k['timing_class']]
  if i+1<len(d['keys']):
   b=d['keys'][i+1]
   if (k['support_contact'],k['root_owner'])==(b['support_contact'],b['root_owner']):
    jj={n:[round((k['j'][n][0]+b['j'][n][0])/2),round((k['j'][n][1]+b['j'][n][1])/2)] for n in k['j']}
    out.append((k['key_id']+'~'+b['key_id'],ascii_pose(k,jj)))
 return out
def main():
 d=json.loads(MOTION.read_text(encoding='utf-8')); REBUILD.mkdir(exist_ok=True)
 f=frames(d); seq=f*int(d['compile']['loop_repetitions'])
 with tempfile.TemporaryDirectory() as td:
  td=Path(td); font=ImageFont.load_default()
  for i,(label,a) in enumerate(seq):
   im=Image.new('RGB',(256,144),'black'); dr=ImageDraw.Draw(im); dr.text((4,3),label,fill='white',font=font); dr.multiline_text((4,14),a,fill='white',font=font,spacing=0); im.save(td/f'{i:04d}.png')
  subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate','24','-i',str(td/'%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','45','-pix_fmt','yuv420p','-threads','1','-fflags','+bitexact','-flags:v','+bitexact','-metadata','creation_time=1970-01-01T00:00:00Z','-movflags','+faststart',str(VIDEO)],check=True)
 media=VIDEO.read_bytes(); media_sha=hashlib.sha256(media).hexdigest(); text=sheet(d); ascii_sha=hashlib.sha256(text.encode()).hexdigest()
 d['compile'].update(media_sha256=media_sha,media_bytes=len(media),semantic_frames_per_loop=len(f),video_frames_total=len(seq))
 d['ascii_sheet_sha256']=ascii_sha; d['receipt'].update(status='RENDERED_AND_STRUCTURALLY_TESTED',media_sha256=media_sha,media_bytes=len(media))
 MOTION.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 manifest={"schema":"ascii-kinesis.swarm-manifest.v2","format_version":2,"id":d['id'],"lane":"locomotion","primary_tabs":["ASCII","JSON","VIDEO"],"ascii_literal_text":True,"ligatures_disabled":True,"whitespace_preserved":True,"video_required":True,"video_source":"abstract_ascii_rig_only","source_art_embedded":False,"backward_compatible":True,"motion_json":"motion.json","builder":"build.py","spa":"support-height-handoff.motion.html","embedded_media_authoritative":True,"media_sha256":media_sha,"media_bytes":len(media),"source_asset_id":d['source']['asset_id']}
 receipt={"schema":"ascii-kinesis.swarm-receipt.v2","experiment_id":d['id'],"status":"RENDERED_AND_STRUCTURALLY_TESTED","repo_path":d['receipt']['repo_path'],"source":{"identity":d['source']['identity'],"url":d['source']['url']},"rights_note":d['source']['rights_boundary'],"timing_split":{"OBSERVED":0,"INFERRED":len(d['keys'])},"per_key_timing":[{"key_id":k['key_id'],"timing_class":k['timing_class'],"timing_provenance":k['timing_provenance']} for k in d['keys']],"media_sha256":media_sha,"media_bytes":len(media),"test_boundary":"Local authorized structural contract test executed against the staged target; repository persistence/readback is a separate gate.","correction_hooks":d['correction_hooks']}
 MANIFEST.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); RECEIPT.write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 audit={"motion":d,"manifest":manifest,"receipt":receipt}; js=json.dumps(audit,indent=2,ensure_ascii=False); zipped=base64.b64encode(gzip.compress(js.encode(),9)).decode(); b64=base64.b64encode(media).decode()
 page=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(d['title'])}</title><style>:root{{color-scheme:dark}}body{{margin:0;background:#101114;color:#f3f3f3;font:15px system-ui,sans-serif}}header,nav,main{{max-width:980px;margin:auto;padding:12px}}header h1{{font-size:1.05rem;margin:.2rem 0}}nav{{display:flex;gap:8px;position:sticky;top:0;background:#101114}}button{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2;line-height:1.05;background:#090a0c;padding:12px;border-radius:8px}}video{{display:block;max-width:100%;width:640px;background:#000;margin:auto}}.note{{opacity:.78}}</style></head><body><header><h1>{html.escape(d['title'])}</h1><div class="note">Abstract ASCII rig only · source art not embedded · Motion Dungeon compile</div></header><nav aria-label="Primary views"><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><main><section id="ascii"><pre id="asciiSurface">{html.escape(text)}</pre></section><section id="json" hidden><pre id="jsonSurface">loading…</pre></section><section id="video" hidden><video controls loop muted playsinline preload="metadata"><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section></main><script>const packed='{zipped}';async function loadJson(){{const a=Uint8Array.from(atob(packed),c=>c.charCodeAt(0));const s=new DecompressionStream('gzip');const t=await new Response(new Blob([a]).stream().pipeThrough(s)).text();document.getElementById('jsonSurface').textContent=t}}loadJson();for(const b of document.querySelectorAll('[data-view]'))b.addEventListener('click',()=>{{for(const s of document.querySelectorAll('main>section'))s.hidden=s.id!==b.dataset.view}});</script></body></html>'''
 SPA.write_text(page,encoding='utf-8'); print(json.dumps({"media_sha256":media_sha,"media_bytes":len(media),"spa_bytes":len(page.encode()),"semantic_frames_per_loop":len(f),"video_frames_total":len(seq)},sort_keys=True))
if __name__=='__main__': main()
