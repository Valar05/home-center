#!/usr/bin/env python3
"""Deterministic Motion Dungeon builder for V2 CONTACT 008 repair.
Reads only motion.json and renders host-font-independent procedural ASCII glyphs.
No source sprite pixels are read, traced, embedded, or rendered.
"""
from __future__ import annotations
import base64, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
W,H=96,25
FLOOR=23
TIMING={'ONES':1,'TWOS':2,'FOURS':4}

def qbez(a,b,bias,t):
    c=((a[0]+b[0])/2+bias[0],(a[1]+b[1])/2+bias[1]); u=1-t
    return (u*u*a[0]+2*u*t*c[0]+t*t*b[0],u*u*a[1]+2*u*t*c[1]+t*t*b[1])

def interp_pose(pa,pb,t,bias=(0,0)):
    return {j:[round(v) for v in qbez(pa[j],pb[j],bias,t)] for j in pa}

def interp_pt(pa,pb,t,bias=(0,0)):
    if pa is None or pb is None:return pa
    return [round(v) for v in qbez(pa,pb,bias,t)]

def bridge_state(k,nk,t):
    spec=k.get('bridge_to_next') or {}
    st=json.loads(json.dumps(k)); ba=tuple(spec.get('arc_bias_A',[0,0])); bo=tuple(spec.get('object_arc_bias',[0,0]))
    st['A']=interp_pose(k['A'],nk['A'],t,ba)
    if st['custody']=='A_HAND' and st['object']['state']=='ANCHORED':
        st['object']['position']=list(st['A']['hand_r'])
        for a in st.get('anchors',[]):
            if a.get('a')=='A.hand_r':a['at']=list(st['A']['hand_r'])
    elif st['object']['position'] is not None and nk['object']['position'] is not None:
        st['object']['position']=interp_pt(k['object']['position'],nk['object']['position'],t,bo)
    if k.get('shared_center') is not None and nk.get('shared_center') is not None and k.get('relationship_state')==nk.get('relationship_state'):
        st['shared_center']=interp_pt(k['shared_center'],nk['shared_center'],t)
    if k.get('force_axis') and nk.get('force_axis') and k.get('relationship_state')==nk.get('relationship_state'):
        st['force_axis']=[interp_pt(k['force_axis'][0],nk['force_axis'][0],t),interp_pt(k['force_axis'][1],nk['force_axis'][1],t)]
    return st

def bres(grid,p0,p1,ch=None):
    x0,y0=map(int,p0);x1,y1=map(int,p1);dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;err=dx+dy
    if ch is None:
        if abs(x1-x0)>abs(y1-y0)*1.7:ch='-'
        elif abs(y1-y0)>abs(x1-x0)*1.7:ch='|'
        else:ch='\\' if (x1-x0)*(y1-y0)>0 else '/'
    while True:
        if 0<=x0<W and 0<=y0<H and grid[y0][x0]==' ':grid[y0][x0]=ch
        if x0==x1 and y0==y1:break
        e2=2*err
        if e2>=dy:err+=dy;x0+=sx
        if e2<=dx:err+=dx;y0+=sy

def put(g,p,ch):
    if p is None:return
    x,y=map(int,p)
    if 0<=x<W and 0<=y<H:g[y][x]=ch

def body(g,p):
    sl,sr,pel=p['shoulder_l'],p['shoulder_r'],p['pelvis']
    for a,b in [(sl,sr),(sl,pel),(sr,pel),(sl,p['hand_l']),(sr,p['hand_r']),(pel,p['knee_l']),(pel,p['knee_r']),(p['knee_l'],p['foot_l']),(p['knee_r'],p['foot_r'])]:bres(g,a,b)
    neck=[round((sl[0]+sr[0])/2),round((sl[1]+sr[1])/2)];bres(g,neck,p['head'],'|');put(g,p['head'],'@');put(g,pel,'A')
    for j in ('shoulder_l','shoulder_r','hand_l','hand_r','knee_l','knee_r'):put(g,p[j],'+')
    put(g,p['foot_l'],'L');put(g,p['foot_r'],'R')

def support_markers(g,st):
    s=st.get('support_A','')
    if 'LEFT_TRUSTED' in s:put(g,[st['A']['foot_l'][0],FLOOR-1],'^')
    if 'RIGHT_TRUSTED' in s:put(g,[st['A']['foot_r'][0],FLOOR-1],'^')
    if 'LEFT_RELEASING' in s:put(g,[st['A']['foot_l'][0],FLOOR-1],'.')
    if 'RIGHT_RELEASING' in s:put(g,[st['A']['foot_r'][0],FLOOR-1],'.')

def ascii_frame(st,label=True):
    g=[[' ']*W for _ in range(H)]
    for x in range(W):g[FLOOR][x]='_'
    if st.get('force_axis'):bres(g,st['force_axis'][0],st['force_axis'][1],':')
    body(g,st['A']);support_markers(g,st)
    for a in st.get('anchors',[]):put(g,a.get('at'),'x')
    if st.get('shared_center') is not None:put(g,st['shared_center'],'X')
    if st.get('object',{}).get('position') is not None:put(g,st['object']['position'],'*')
    if label:
        s=f"{st['key_id']} {st['name']} | {st['timing_class']} {st['timing_provenance']} | REL={st['relationship_state']} CUSTODY={st['custody']} SUPPORT={st['support_A']}"
        for i,ch in enumerate(s[:W]):g[0][i]=ch
    return '\n'.join(''.join(r).rstrip() for r in g)

def contact_sheet(keys):
    out=[]
    for k in keys:out += ['='*W,f"{k['key_id']}  {k['name']}  | {k['timing_class']} / {k['timing_provenance']}",f"ROLE: {k['causal_role']}",f"STATE: contact={k['contact_state']} relationship={k['relationship_state']} custody={k['custody']} support={k['support_A']} root={k['root_owner']}",f"ARC: {k['motion_arc_root_note']}",ascii_frame(k,False)]
    return '\n'.join(out)+'\n'

def sequence(data):
    frames=[];keys=data['keys'];scale=int(data['compile']['preview_time_scale'])
    for i,k in enumerate(keys):
        frames += [k]*(TIMING[k['timing_class']]*scale)
        if i<len(keys)-1:
            n=int((k.get('bridge_to_next') or {}).get('frames',0))
            for j in range(1,n+1):
                st=bridge_state(k,keys[i+1],j/(n+1));st['key_id']=k['key_id']+'~'+keys[i+1]['key_id'];st['name']='AUTHORED_CONNECTIVE';frames.append(st)
    return frames

def glyph(d,c,x,y,cw,ch):
    x0,y0=x+1,y+1;x1,y1=x+cw-2,y+ch-2;xm=(x0+x1)//2;ym=(y0+y1)//2;w=2;white='white'
    if c==' ':return
    if c=='_':d.line((x0,y1,x1,y1),fill=white,width=w)
    elif c=='-':d.line((x0,ym,x1,ym),fill=white,width=w)
    elif c=='|':d.line((xm,y0,xm,y1),fill=white,width=w)
    elif c=='/':d.line((x0,y1,x1,y0),fill=white,width=w)
    elif c=='\\':d.line((x0,y0,x1,y1),fill=white,width=w)
    elif c==':':d.ellipse((xm-1,y0+2,xm+1,y0+4),fill=white);d.ellipse((xm-1,y1-4,xm+1,y1-2),fill=white)
    elif c=='.':d.ellipse((xm-1,y1-2,xm+1,y1),fill=white)
    elif c=='+':d.line((x0,ym,x1,ym),fill=white,width=w);d.line((xm,y0,xm,y1),fill=white,width=w)
    elif c in 'xX':d.line((x0,y0,x1,y1),fill=white,width=w);d.line((x0,y1,x1,y0),fill=white,width=w)
    elif c=='^':d.line((x0,y1,xm,y0),fill=white,width=w);d.line((xm,y0,x1,y1),fill=white,width=w)
    elif c=='*':d.line((xm,y0,xm,y1),fill=white,width=w);d.line((x0,ym,x1,ym),fill=white,width=w);d.line((x0,y0,x1,y1),fill=white,width=w);d.line((x0,y1,x1,y0),fill=white,width=w)
    elif c=='@':d.ellipse((x0,y0,x1,y1),outline=white,width=w);d.ellipse((xm-1,ym-1,xm+1,ym+1),fill=white)
    elif c=='A':d.line((x0,y1,xm,y0),fill=white,width=w);d.line((xm,y0,x1,y1),fill=white,width=w);d.line((x0+2,ym,x1-2,ym),fill=white,width=w)
    elif c=='L':d.line((x0,y0,x0,y1),fill=white,width=w);d.line((x0,y1,x1,y1),fill=white,width=w)
    elif c=='R':d.line((x0,y0,x0,y1),fill=white,width=w);d.line((x0,y0,x1-2,y0),fill=white,width=w);d.line((x0,ym,x1,ym),fill=white,width=w);d.line((x1,y0,x1,ym),fill=white,width=w);d.line((xm,ym,x1,y1),fill=white,width=w)

def raster(text,path):
    im=Image.new('RGB',(960,300),'black');d=ImageDraw.Draw(im);cw,ch=10,12
    for row,line in enumerate(text.splitlines()[:H]):
        for col,c in enumerate(line[:W]):glyph(d,c,col*cw,row*ch,cw,ch)
    im.save(path)

def render_mp4(data,tmp):
    frames=sequence(data);fd=tmp/'frames';fd.mkdir()
    for i,st in enumerate(frames):raster(ascii_frame(st,False),fd/f'{i:04d}.png')
    mp4=tmp/'motion.mp4';subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(data['compile']['fps']),'-i',str(fd/'%04d.png'),'-c:v','libx264','-preset','veryslow','-vf',f"scale={data['compile']['output_width']}:{data['compile']['output_height']}:flags=neighbor",'-crf',str(data['compile']['crf']),'-pix_fmt','yuv420p','-movflags','+faststart',str(mp4)],check=True)
    return mp4,len(frames)

def html_page(data,sheet,video_bytes):
    payload=json.dumps(data,separators=(',',':'),sort_keys=True,ensure_ascii=True).replace('</','<\\/')
    b64=base64.b64encode(video_bytes).decode('ascii')
    return f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{data['experiment_id']}</title><style>
*{{box-sizing:border-box}}body{{margin:0;background:#080808;color:#eee;font-family:system-ui,sans-serif}}header{{padding:12px 16px;border-bottom:1px solid #444}}nav{{display:flex;gap:8px;padding:10px 16px;position:sticky;top:0;background:#080808}}button{{font:inherit;padding:8px 14px}}section{{display:none;padding:12px 16px}}section.active{{display:block}}pre{{margin:0;overflow:auto;white-space:pre;font-family:ui-monospace,SFMono-Regular,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;tab-size:2;line-height:1.15}}video{{display:block;width:min(100%,960px);height:auto;background:#000;border:1px solid #444}}
</style></head><body><header><strong>ASCII Kinesis V2 · CONTACT 008 · running throw custody fork repair</strong></header><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="ascii-pre"></pre></section><section id="json"><pre id="json-pre"></pre></section><section id="video"><video controls autoplay muted loop playsinline src="data:video/mp4;base64,{b64}"></video></section><script>
const DATA={payload},W=96,H=25,FLOOR=23;
function put(g,p,ch){{if(!p)return;const [x,y]=p;if(x>=0&&x<W&&y>=0&&y<H)g[y][x]=ch}}
function bres(g,p0,p1,ch=null){{let [x0,y0]=p0,[x1,y1]=p1,dx=Math.abs(x1-x0),sx=x0<x1?1:-1,dy=-Math.abs(y1-y0),sy=y0<y1?1:-1,err=dx+dy;if(ch===null)ch=Math.abs(x1-x0)>Math.abs(y1-y0)*1.7?'-':Math.abs(y1-y0)>Math.abs(x1-x0)*1.7?'|':((x1-x0)*(y1-y0)>0?'\\\\':'/');while(true){{if(x0>=0&&x0<W&&y0>=0&&y0<H&&g[y0][x0]===' ')g[y0][x0]=ch;if(x0===x1&&y0===y1)break;const e2=2*err;if(e2>=dy){{err+=dy;x0+=sx}}if(e2<=dx){{err+=dx;y0+=sy}}}}}}
function pyr(n){{const f=Math.floor(n),r=n-f;return r===0.5?(f%2===0?f:f+1):Math.round(n)}}
function body(g,p){{const sl=p.shoulder_l,sr=p.shoulder_r,pel=p.pelvis;for(const [a,b] of [[sl,sr],[sl,pel],[sr,pel],[sl,p.hand_l],[sr,p.hand_r],[pel,p.knee_l],[pel,p.knee_r],[p.knee_l,p.foot_l],[p.knee_r,p.foot_r]])bres(g,a,b);const neck=[pyr((sl[0]+sr[0])/2),pyr((sl[1]+sr[1])/2)];bres(g,neck,p.head,'|');put(g,p.head,'@');put(g,pel,'A');for(const j of ['shoulder_l','shoulder_r','hand_l','hand_r','knee_l','knee_r'])put(g,p[j],'+');put(g,p.foot_l,'L');put(g,p.foot_r,'R')}}
function support(g,st){{const s=st.support_A||'';if(s.includes('LEFT_TRUSTED'))put(g,[st.A.foot_l[0],FLOOR-1],'^');if(s.includes('RIGHT_TRUSTED'))put(g,[st.A.foot_r[0],FLOOR-1],'^');if(s.includes('LEFT_RELEASING'))put(g,[st.A.foot_l[0],FLOOR-1],'.');if(s.includes('RIGHT_RELEASING'))put(g,[st.A.foot_r[0],FLOOR-1],'.')}}
function frame(st){{const g=Array.from({{length:H}},()=>Array(W).fill(' '));for(let x=0;x<W;x++)g[FLOOR][x]='_';if(st.force_axis)bres(g,st.force_axis[0],st.force_axis[1],':');body(g,st.A);support(g,st);for(const a of st.anchors||[])put(g,a.at,'x');if(st.shared_center)put(g,st.shared_center,'X');if(st.object&&st.object.position)put(g,st.object.position,'*');return g.map(r=>r.join('').replace(/\\s+$/,'')).join('\\n')}}
function sheet(keys){{const o=[];for(const k of keys)o.push('='.repeat(W),`${{k.key_id}}  ${{k.name}}  | ${{k.timing_class}} / ${{k.timing_provenance}}`,`ROLE: ${{k.causal_role}}`,`STATE: contact=${{k.contact_state}} relationship=${{k.relationship_state}} custody=${{k.custody}} support=${{k.support_A}} root=${{k.root_owner}}`,`ARC: ${{k.motion_arc_root_note}}`,frame(k));return o.join('\\n')+'\\n'}}
document.getElementById('ascii-pre').textContent=sheet(DATA.keys);document.getElementById('json-pre').textContent=JSON.stringify(DATA,null,2);const bs=[...document.querySelectorAll('button[data-view]')],ss=[...document.querySelectorAll('section')];for(const b of bs)b.onclick=()=>{{for(const s of ss)s.classList.toggle('active',s.id===b.dataset.view)}};
</script></body></html>'''

def main():
    data=json.loads(MOTION.read_text());sheet=contact_sheet(data['keys']);(HERE/'contact-sheet.txt').write_text(sheet)
    with tempfile.TemporaryDirectory() as td:mp4,n=render_mp4(data,Path(td));raw=mp4.read_bytes()
    sha=hashlib.sha256(raw).hexdigest();expected=data['compile'].get('media_sha256')
    if expected and sha!=expected:raise SystemExit(f'media hash mismatch: {sha} != {expected}')
    expected_n=data['compile'].get('video_frames_total')
    if expected_n and n!=expected_n:raise SystemExit(f'frame count mismatch: {n} != {expected_n}')
    page=html_page(data,sheet,raw);(HERE/'running-throw-custody-fork-repair.motion.html').write_text(page)
    print(json.dumps({'media_sha256':sha,'media_bytes':len(raw),'video_frames_total':n,'spa_bytes':len(page.encode()),'spa_sha256':hashlib.sha256(page.encode()).hexdigest()},sort_keys=True))
if __name__=='__main__':main()
