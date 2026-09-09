#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, shutil, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from html import escape

ROOT=Path(__file__).resolve().parent
MOTION_PATH=ROOT/'motion.json'; CONTACT_PATH=ROOT/'contact-sheet.txt'
MP4_PATH=ROOT/'midair-recoil-vector-bend-crossstep-recovery.mp4'
SPA_PATH=ROOT/'midair-recoil-vector-bend-crossstep-recovery.motion.html'
FPS=24; CANVAS_W,CANVAS_H=800,382
FONT_PATHS=['/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf']

def lerp(a,b,t): return a+(b-a)*t
def ease(t): return t*t*(3-2*t)
def point_lerp(a,b,t): return [int(round(lerp(a[0],b[0],t))),int(round(lerp(a[1],b[1],t)))]
def bresenham(a,b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; pts=[]
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return pts

def line_char(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>=2*abs(dy): return '-'
    if abs(dy)>=2*abs(dx): return '|'
    return '\\' if dx*dy>=0 else '/'
def put(g,x,y,ch):
    if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=ch
def seg(g,a,b,ch=None):
    c=ch or line_char(a,b)
    for x,y in bresenham(a,b): put(g,x,y,c)
def smark(s,n):
    if s in ('BOTH_FEET','BOTH_FEET_NEW_SECOND_CONTACT'): return '*'
    if s=='LEFT_TOE_LAST_SUPPORT' and n=='l_foot': return '*'
    if s in ('RIGHT_FOOT_NEW_CONTACT','RIGHT_FOOT') and n=='r_foot': return '*'
    return '^'
def render_ascii_pose(state,cols=72,rows=24,ground=21):
    g=[[' ']*cols for _ in range(rows)]
    for x in range(cols): put(g,x,ground+1,'_')
    p=state['points']
    for a,b in [('head','chest'),('chest','pelvis'),('l_sh','r_sh'),('l_sh','l_hand'),('r_sh','r_hand'),('pelvis','l_knee'),('l_knee','l_foot'),('pelvis','r_knee'),('r_knee','r_foot')]: seg(g,p[a],p[b])
    put(g,*p['head'],'O'); put(g,*p['chest'],'X'); put(g,*p['pelvis'],'@')
    for n in ['l_sh','r_sh','l_hand','r_hand','l_knee','r_knee']: put(g,*p[n],'o')
    put(g,*p['l_foot'],smark(state.get('support_contact','AIR'),'l_foot')); put(g,*p['r_foot'],smark(state.get('support_contact','AIR'),'r_foot'))
    bar=state.get('bar') or {}
    if bar:
        seg(g,bar['a'],bar['b'],'='); put(g,*bar['a'],'['); put(g,*bar['b'],']')
        if bar.get('puck_visible'): put(g,*bar['puck'],'#')
    return '\n'.join(''.join(r).rstrip() for r in g).rstrip()
def interpolate(a,b,t):
    t=ease(t); out={'key_id':a['key_id']+'~'+b['key_id'],'label':a['label']+' -> '+b['label'],'support_contact':a['support_contact'],'custody':a['custody'],'points':{},'bar':{}}
    for k in a['points']: out['points'][k]=point_lerp(a['points'][k],b['points'][k],t)
    for k in ('a','b','puck'): out['bar'][k]=point_lerp(a['bar'][k],b['bar'][k],t)
    out['bar']['puck_visible']=a['bar'].get('puck_visible',False); return out
def compile_states(motion):
    keys=motion['keys']; frames=[]; meta=[]
    for _ in range(keys[0]['hold_frames']): frames.append(keys[0]); meta.append(keys[0]['key_id'])
    for i in range(1,len(keys)):
        a,b=keys[i-1],keys[i]; travel=max(1,int(b.get('travel_frames',1))); mode=b.get('transition_mode','AUTHORED_EASE')
        if mode=='CAUSAL_SNAP':
            for _ in range(max(0,travel-1)): frames.append(a); meta.append(a['key_id']+' HOLD_FOR_CAUSAL_SNAP')
        else:
            for j in range(1,travel): frames.append(interpolate(a,b,j/travel)); meta.append(f"{a['key_id']}->{b['key_id']} {j}/{travel}")
        for _ in range(int(b['hold_frames'])): frames.append(b); meta.append(b['key_id'])
    return frames,meta
def make_contact(motion):
    chunks=[]
    for k in motion['keys']:
        chunks.append(f"[{k['key_id']}] {k['label']}\n"
        f"support_contact={k['support_contact']} | custody={k['custody']}\n"
        f"root={k['root']} | timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']}\n"
        f"causal_role={k['causal_role']}\n"
        f"motion_arc_root_note={k['motion_arc_root_note']}\n"+render_ascii_pose(k,motion['rig']['stage_cols'],motion['rig']['stage_rows'],motion['rig']['ground_row']))
    return ('ASCII KINESIS V2 · AIRBORNE029\nMID-AIR REACTION PULSE / ROOT-VECTOR BEND / CROSSED SUPPORT RECOVERY\nIndependent abstract ASCII rig. Source art pixels never enter this artifact.\nLegend: O head | X chest | @ pelvis/root | o joint | ^ free foot | * authored support | = abstract reaction bar | # released calibration puck\nAll decisive timing is INFERRED / STREET_FIGHTER-CAPCOM. Source-authentic timing is UNKNOWN.\n\n'+'\n\n'.join(chunks)+'\n')
def fontpath():
    for p in FONT_PATHS:
        if Path(p).is_file(): return p
    raise RuntimeError('monospace font unavailable')
def render_pngs(motion,out):
    out.mkdir(parents=True,exist_ok=True); frames,meta=compile_states(motion); font=ImageFont.truetype(fontpath(),12); hud=ImageFont.truetype(fontpath(),11)
    for i,state in enumerate(frames):
        img=Image.new('RGB',(CANVAS_W,CANVAS_H),(8,8,10)); d=ImageDraw.Draw(img)
        txt=render_ascii_pose(state,motion['rig']['stage_cols'],motion['rig']['stage_rows'],motion['rig']['ground_row'])
        d.text((18,12),txt,font=font,fill=(238,238,238),spacing=0)
        d.text((18,CANVAS_H-34),f"{i+1:03d}/{len(frames):03d}  {meta[i]}",font=hud,fill=(185,185,185))
        d.text((CANVAS_W-290,CANVAS_H-34),'AIRBORNE029 · ASCII ONLY',font=hud,fill=(185,185,185))
        img.save(out/f'{i:04d}.png',compress_level=9)
    return frames,meta
def encode(out,mp4):
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(out/'%04d.png'),'-an','-c:v','libx264','-preset','medium','-crf','27','-pix_fmt','yuv420p','-threads','1','-map_metadata','-1','-metadata','encoder=','-fflags','+bitexact','-flags:v','+bitexact',str(mp4)],check=True)
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def make_spa(motion,contact,mp4):
    mtxt=json.dumps(motion,separators=(',',':'),ensure_ascii=False); b64=base64.b64encode(mp4).decode('ascii'); a=escape(contact); j=escape(mtxt)
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis · Airborne029</title><style>body{{margin:0;background:#0b0b0d;color:#eee;font-family:system-ui,sans-serif}}nav{{position:sticky;top:0;background:#151519;padding:10px;border-bottom:1px solid #555}}button{{font:inherit;margin-right:8px;padding:8px 14px}}section{{display:none;padding:16px}}section.active{{display:block}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555;background:#000}}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre>{a}</pre></section><section id="json"><pre>{j}</pre></section><section id="video"><video controls loop autoplay muted playsinline src="data:video/mp4;base64,{b64}"></video></section><script>for(const b of document.querySelectorAll("[data-view]")) b.onclick=()=>{{document.querySelectorAll("section").forEach(s=>s.classList.remove("active"));document.getElementById(b.dataset.view).classList.add("active")}};</script></body></html>'''
def main():
    motion=json.loads(MOTION_PATH.read_text()); motion.pop('media',None); out=ROOT/'_frames';
    if out.exists(): shutil.rmtree(out)
    frames,_=render_pngs(motion,out); encode(out,MP4_PATH); mp4=MP4_PATH.read_bytes()
    media={'sha256':sha_bytes(mp4),'bytes':len(mp4),'fps':FPS,'frames':len(frames),'width':CANVAS_W,'height':CANVAS_H,'codec':'H.264','pixel_format':'yuv420p'}
    motion['media']=media; MOTION_PATH.write_text(json.dumps(motion,separators=(',',':'),ensure_ascii=False)+'\n')
    contact=make_contact(motion); CONTACT_PATH.write_text(contact)
    SPA_PATH.write_text(make_spa(motion,contact,mp4)); shutil.rmtree(out); print(json.dumps(media,sort_keys=True))
if __name__=='__main__': main()
