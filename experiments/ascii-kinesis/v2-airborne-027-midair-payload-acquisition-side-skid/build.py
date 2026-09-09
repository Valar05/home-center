#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, html, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
M=json.loads((ROOT/'motion.json').read_text(encoding='utf-8'))
W=int(M['rig']['grid']['width']); H=int(M['rig']['grid']['height']); GROUND=int(M['rig']['grid']['ground_y'])
FPS=int(M['compile']['fps']); SCALE=int(M['compile'].get('render_hold_scale',2))
HOLD={'ONES':1,'TWOS':2,'FOURS':4}; BR=M['compile']['bridge_plan']
BODY=['root','chest','head','l_elbow','l_hand','r_elbow','r_hand','l_knee','l_foot','r_knee','r_foot']
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'

def put(g,x,y,ch,overwrite=True):
    x=int(round(x)); y=int(round(y))
    if 0<=x<W and 0<=y<H and (overwrite or g[y][x]==' '): g[y][x]=ch

def line(g,x0,y0,x1,y1,ch,overwrite=False):
    x0,y0,x1,y1=map(lambda v:int(round(v)),(x0,y0,x1,y1))
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<H and (overwrite or g[y0][x0]==' '): g[y0][x0]=ch
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def ap(s,n):
    if n=='root': return tuple(s['root'])
    r=s['root']; q=s[n]; return (r[0]+q[0],r[1]+q[1])

def pose_grid(s):
    g=[[' ']*W for _ in range(H)]
    for x in range(1,W-1): g[GROUND][x]='_'
    p={n:ap(s,n) for n in BODY}
    for a,b,ch in ((p['root'],p['chest'],'|'),(p['chest'],p['l_elbow'],'/'),(p['l_elbow'],p['l_hand'],'-'),
                   (p['chest'],p['r_elbow'],'\\'),(p['r_elbow'],p['r_hand'],'-'),(p['root'],p['l_knee'],'/'),
                   (p['l_knee'],p['l_foot'],'/'),(p['root'],p['r_knee'],'\\'),(p['r_knee'],p['r_foot'],'\\')):
        line(g,*a,*b,ch)
    for q,ch in ((p['root'],'@'),(p['chest'],'+'),(p['head'],'O'),(p['l_elbow'],'o'),(p['l_hand'],'x'),
                 (p['r_elbow'],'o'),(p['r_hand'],'x'),(p['l_knee'],'o'),(p['l_foot'],'='),(p['r_knee'],'o'),(p['r_foot'],'=')):
        put(g,*q,ch,True)
    payload=tuple(s['payload']); put(g,payload[0]-1,payload[1],'<',True); put(g,payload[0],payload[1],'#',True); put(g,payload[0]+1,payload[1],'>',True)
    c=set(s.get('contacts',[]))
    if 'left_foot_ground' in c: put(g,p['l_foot'][0],GROUND,'!',True)
    if 'right_foot_ground' in c: put(g,p['r_foot'][0],GROUND,'!',True)
    if 'left_forearm_ground' in c: put(g,p['l_hand'][0],GROUND,'!',True)
    if 'left_knee_ground' in c: put(g,p['l_knee'][0],GROUND,'!',True)
    if 'left_hand_ground' in c: put(g,p['l_hand'][0],GROUND,'!',True)
    if 'left_hand_payload' in c: put(g,p['l_hand'][0],p['l_hand'][1],'*',True)
    if 'right_hand_payload' in c: put(g,p['r_hand'][0],p['r_hand'][1],'*',True)
    if any(x.endswith('_payload') for x in c): put(g,payload[0]-1,payload[1],'<',True); put(g,payload[0],payload[1],'#',True); put(g,payload[0]+1,payload[1],'>',True)
    return g

def pose_text(s):
    rows=[''.join(r).rstrip() for r in pose_grid(s)]
    while rows and not rows[-1]: rows.pop()
    return '\n'.join(rows)

def interp(a,b,t):
    u=t*t*(3-2*t); out={}
    for f in BODY:
        av=a[f]; bv=b[f]; out[f]=[av[0]+(bv[0]-av[0])*u,av[1]+(bv[1]-av[1])*u]
    av=a['payload']; bv=b['payload']; out['payload']=[av[0]+(bv[0]-av[0])*u,av[1]+(bv[1]-av[1])*u]
    out['contacts']=list(a.get('contacts',[])); out['payload_contacts']=list(a.get('payload_contacts',[]))
    return out

states=[dict(k['authoring']) for k in M['keys']]
parts=[]
for k,s in zip(M['keys'],states):
    sc=k['support_contact']
    parts.append(f"{k['key_id']} {k['name']}  {k['timing_class']}/{k['timing_provenance']}\n"
                 f"SUPPORT={sc['support']} CUSTODY={sc.get('payload_custody','NA')} CONTACTS={','.join(sc['contacts']) or 'NONE'}\n"
                 f"ARC={k['motion_arc_root_note']}\n{pose_text(s)}")
contact='\n\n'.join(parts)+'\n'
(ROOT/'contact-sheet.txt').write_text(contact,encoding='utf-8')

frames=[]; meta=[]
for i,(k,s) in enumerate(zip(M['keys'],states)):
    for _ in range(HOLD[k['timing_class']]*SCALE):
        frames.append(pose_text(s)); meta.append((k['key_id'],'hold'))
    if i<len(states)-1:
        for j in range(1,BR[i]+1):
            frames.append(pose_text(interp(s,states[i+1],j/(BR[i]+1)))); meta.append((f"{k['key_id']}->{M['keys'][i+1]['key_id']}",'bridge'))

fd=ROOT/'.frames'
if fd.exists(): shutil.rmtree(fd)
fd.mkdir()
font=ImageFont.truetype(FONT,10)
for i,txt in enumerate(frames):
    im=Image.new('RGB',(640,360),(8,8,8)); d=ImageDraw.Draw(im)
    d.multiline_text((8,4),txt,font=font,fill=(238,238,238),spacing=-1)
    d.text((8,338),f"{i:03d} {meta[i][0]}",font=font,fill=(180,180,180))
    im.save(fd/f'{i:04d}.png',compress_level=9)

mp4=ROOT/M['media']['filename']
subprocess.run(['ffmpeg','-y','-hide_banner','-loglevel','error','-framerate',str(FPS),'-i',str(fd/'%04d.png'),
                '-c:v','libx264','-pix_fmt','yuv420p','-preset','medium','-crf','36','-threads','1','-movflags','+faststart',str(mp4)],check=True)
subprocess.run(['ffmpeg','-v','error','-i',str(mp4),'-f','null','-'],check=True)
media=mp4.read_bytes(); sha=hashlib.sha256(media).hexdigest()
if M['media'].get('sha256') not in ('AUTO',None,'') and sha != M['media']['sha256']:
    raise SystemExit(f'MEDIA_IDENTITY_MISMATCH sha {sha}')
if int(M['media'].get('bytes') or 0) and len(media) != int(M['media']['bytes']): raise SystemExit('MEDIA_IDENTITY_MISMATCH bytes')
if int(M['media'].get('frames') or 0) and len(frames) != int(M['media']['frames']): raise SystemExit('MEDIA_IDENTITY_MISMATCH frames')

manifest={'format_version':2,'experiment_id':M['experiment_id'],'primary_tabs':['ASCII','JSON','VIDEO'],
          'ascii_literal_text':True,'video_required':True,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,
          'backward_compatible':True,'motion_json':'motion.json','contact_sheet':'contact-sheet.txt','media':dict(M['media']),
          'rights_firewall':M['source']['rights_boundary'],'source_timing':M['source']['source_authentic_timing']}
(ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')

import gzip
motion_text=(ROOT/'motion.json').read_text(encoding='utf-8'); b64=base64.b64encode(media).decode('ascii')
ab64=base64.b64encode(gzip.compress(contact.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
jb64=base64.b64encode(gzip.compress(motion_text.encode('utf-8'),compresslevel=9,mtime=0)).decode('ascii')
page='<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
page+=f'<title>{html.escape(M["experiment_id"])}</title><style>'
page+='body{font-family:system-ui,sans-serif;margin:0;background:#111;color:#eee}nav{position:sticky;top:0;background:#181818;padding:8px}'
page+='button{margin-right:8px;padding:8px 14px}section{display:none;padding:12px}section.active{display:block}'
page+='pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1.04}'
page+='video{max-width:100%;background:#000}</style></head><body>'
page+='<nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>'
page+='<section id="ascii" class="active"><pre id="ascii-pre"></pre></section><section id="json"><pre id="json-pre"></pre></section>'
page+=f'<section id="video"><video controls loop autoplay muted playsinline><source src="data:video/mp4;base64,{b64}" type="video/mp4"></video></section>'
page+=f'<script>const A="{ab64}",J="{jb64}";async function z(b,id){{let u=Uint8Array.from(atob(b),c=>c.charCodeAt(0));let r=new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip")));document.getElementById(id).textContent=await r.text()}}z(A,"ascii-pre");z(J,"json-pre");const bs=[...document.querySelectorAll("button[data-view]")];bs.forEach(b=>b.onclick=()=>{{document.querySelectorAll("section").forEach(s=>s.classList.remove("active"));document.getElementById(b.dataset.view).classList.add("active")}})</script></body></html>'
(ROOT/'midair-payload-acquisition-side-skid.motion.html').write_text(page,encoding='utf-8')
print(json.dumps({'ok':True,'frames':len(frames),'bytes':len(media),'media_sha256':sha,'contact_sheet_sha256':hashlib.sha256(contact.encode()).hexdigest()},sort_keys=True))
