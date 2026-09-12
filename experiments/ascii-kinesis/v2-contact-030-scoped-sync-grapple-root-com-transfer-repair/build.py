#!/usr/bin/env python3
from pathlib import Path
import base64, hashlib, json, shutil, subprocess, tempfile, html
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parent
MOTION=ROOT/'motion.json'; SHEET=ROOT/'contact-sheet.txt'; SPA=ROOT/'scoped-sync-grapple-root-com-transfer-repair.motion.html'
W,H,FLOOR=100,28,25
TIMING={'ONES':1,'TWOS':2,'FOURS':4}

def lerp(a,b,t): return [a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t]
def smooth(t): return t*t*(3-2*t)
def state_sig(k): return (k['contact_state'],k['custody'],k['root_owner'])
def interp_body(a,b,t):
    s=smooth(t); return {j:lerp(a[j],b[j],s) for j in a}
def interp_state(a,b,t):
    s=smooth(t); st=json.loads(json.dumps(a)); st['A']=interp_body(a['A'],b['A'],t); st['B']=interp_body(a['B'],b['B'],t)
    if a.get('relationship_center') is not None and b.get('relationship_center') is not None: st['relationship_center']=lerp(a['relationship_center'],b['relationship_center'],s)
    if a.get('force_axis') and b.get('force_axis'): st['force_axis']=[lerp(a['force_axis'][0],b['force_axis'][0],s),lerp(a['force_axis'][1],b['force_axis'][1],s)]
    anchors=[]
    for x in a.get('anchors',[]):
        aa=x['a'].split('.'); bb=x['b'].split('.')
        pa=st[aa[0]][aa[1]]; pb=st[bb[0]][bb[1]]
        anchors.append({'a':x['a'],'b':x['b'],'at':[(pa[0]+pb[0])/2,(pa[1]+pb[1])/2]})
    st['anchors']=anchors; st['key_id']=a['key_id']+'~'+b['key_id']; st['name']='AUTHORED_CONNECTIVE'; return st

def seq(data):
    out=[]; ks=data['keys']; scale=data['compile']['preview_time_scale']
    for i,k in enumerate(ks):
        out += [k]*(TIMING[k['timing_class']]*scale)
        if i<len(ks)-1:
            n=int(k.get('bridge_frames',0))
            if n and state_sig(k)==state_sig(ks[i+1]):
                for q in range(1,n+1): out.append(interp_state(k,ks[i+1],q/(n+1)))
    return out

def put(g,p,ch):
    if p is None:return
    x,y=map(lambda v:int(round(v)),p)
    if 0<=x<W and 0<=y<H:g[y][x]=ch

def line(g,a,b,ch=None):
    x0,y0=map(lambda v:int(round(v)),a); x1,y1=map(lambda v:int(round(v)),b)
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    if ch is None:
        if abs(x1-x0)>abs(y1-y0)*1.7: ch='-'
        elif abs(y1-y0)>abs(x1-x0)*1.7: ch='|'
        else: ch='\\' if (x1-x0)*(y1-y0)>0 else '/'
    while True:
        if 0<=x0<W and 0<=y0<H and g[y0][x0]==' ':g[y0][x0]=ch
        if x0==x1 and y0==y1:break
        e2=2*err
        if e2>=dy:err+=dy;x0+=sx
        if e2<=dx:err+=dx;y0+=sy

def draw_body(g,p,label):
    for a,b in [('shoulder_l','shoulder_r'),('shoulder_l','pelvis'),('shoulder_r','pelvis'),('shoulder_l','hand_l'),('shoulder_r','hand_r'),('pelvis','foot_l'),('pelvis','foot_r')]: line(g,p[a],p[b])
    neck=[(p['shoulder_l'][0]+p['shoulder_r'][0])/2,(p['shoulder_l'][1]+p['shoulder_r'][1])/2]; line(g,neck,p['head'],'|')
    put(g,p['head'],label); put(g,p['pelvis'],label.lower())
    for j in ('hand_l','hand_r','shoulder_l','shoulder_r'): put(g,p[j],'+')
    put(g,p['foot_l'],'L'); put(g,p['foot_r'],'R')

def support(g,p,s):
    if 'LEFT_TRUSTED' in s or s.startswith('LEFT_'): put(g,[p['foot_l'][0],FLOOR-1],'^')
    if 'RIGHT_TRUSTED' in s or 'RIGHT_BRAKE' in s or s.startswith('RIGHT_'): put(g,[p['foot_r'][0],FLOOR-1],'^')
    if 'RELEAS' in s or 'LIGHT' in s:
        if 'LEFT_RELEAS' in s or 'LEFT_LIGHT' in s: put(g,[p['foot_l'][0],FLOOR-1],'.')
        if 'RIGHT_RELEAS' in s or 'RIGHT_LIGHT' in s: put(g,[p['foot_r'][0],FLOOR-1],'.')

def ascii_frame(st,compact=False):
    g=[[' ']*W for _ in range(H)]
    if compact:
        xs=[st['A']['foot_l'][0],st['A']['foot_r'][0],st['B']['foot_l'][0],st['B']['foot_r'][0]]
        lo=max(0,int(min(xs))-4); hi=min(W,int(max(xs))+5)
        for x in range(lo,hi):g[FLOOR][x]='_'
    else:
        for x in range(W):g[FLOOR][x]='_'
    draw_body(g,st['A'],'A'); draw_body(g,st['B'],'B'); support(g,st['A'],st['support_A']);support(g,st['B'],st['support_B'])
    if st.get('force_axis'): line(g,st['force_axis'][0],st['force_axis'][1],':')
    if st.get('relationship_center') is not None: put(g,st['relationship_center'],'X')
    for an in st.get('anchors',[]): put(g,an.get('at'),'*')
    text='\n'.join(''.join(r).rstrip() for r in g)
    if compact:
        rows=[r for r in text.splitlines() if r.strip()]
        if rows:
            indent=min(len(r)-len(r.lstrip()) for r in rows if r.strip())
            rows=[r[indent:].rstrip() for r in rows]
        return '\n'.join(rows)
    return text

def contact_sheet(data):
    s=data['source']; rev=data['revision']; out=[data['experiment_id'],data['primitive'],f"REVISION: revises={rev['revises']} | negative_fixture={rev['negative_fixture']} | reset={rev['reset_issue_comment']}",f"SOURCE: TSR asset {s['asset_id']} | {s['name']} | {s['game']} | {s['platform']} | raw_sha256={s['raw_sha256']}",f"SOURCE EVIDENCE: Home Center {s['evidence_document_id']} | whole_sheet_inspected=true | source_timing=UNKNOWN | timing_authority=false",'RIGHTS: evidence only; independent abstract ASCII rig; no source pixels/palette/costume/exact silhouette/choreography/tracing/redistribution.','LEGEND: A/B heads, a/b pelvis roots, +=joint, L/R=feet, ^=trusted/braking support, .=light/releasing support, *=inter-body anchor, X=relationship center, :=force axis.','VISIBLE CAUSAL SENTENCE: separation -> root-led close -> precontact coil -> first anchor -> second-anchor lock -> shared-center load -> counterload -> authored root-owner swap -> transfer while contact lives -> hard release -> partner lag/carrier recoil -> overshoot/brake -> displaced settle.']
    for k in data['keys']:
        out += ['='*W,f"{k['key_id']} {k['name']} | {k['timing_class']} / {k['timing_provenance']}",f"CONTACT={k['contact_state']} | CUSTODY={k['custody']} | ROOT_OWNER={k['root_owner']} | SUPPORT_A={k['support_A']} | SUPPORT_B={k['support_B']}",f"ROLE: {k['causal_role']}",f"ARC: {k['motion_arc_root_note']}",ascii_frame(k,True)]
    return '\n'.join(out)+'\n'

SEG={'A':[((0,1),(0.5,0)),((0.5,0),(1,1)),((.22,.58),(.78,.58))],'B':[((0,0),(0,1)),((0,0),(.65,0)),((.65,0),(1,.25)),((1,.25),(.65,.5)),((0,.5),(.65,.5)),((.65,.5),(1,.75)),((1,.75),(.65,1)),((.65,1),(0,1))],'a':[((.2,.45),(.5,.2)),((.5,.2),(.8,.45)),((.8,.45),(.5,.72)),((.5,.72),(.2,.45))],'b':[((.15,0),(.15,1)),((.15,.45),(.65,.3)),((.65,.3),(.9,.55)),((.9,.55),(.65,.82)),((.65,.82),(.15,.7))],'L':[((.1,0),(.1,1)),((.1,1),(.9,1))],'R':[((.1,0),(.1,1)),((.1,0),(.7,0)),((.7,0),(.9,.25)),((.9,.25),(.7,.5)),((.7,.5),(.1,.5)),((.5,.5),(.95,1))]}
def glyph(d,c,x,y,cw,ch):
    p=lambda u,v:(x+2+u*(cw-4),y+2+v*(ch-4)); white=(245,245,245); w=2
    if c==' ':return
    if c=='_': d.line((*p(0,1),*p(1,1)),fill=white,width=w)
    elif c=='-': d.line((*p(0,.5),*p(1,.5)),fill=white,width=w)
    elif c=='|': d.line((*p(.5,0),*p(.5,1)),fill=white,width=w)
    elif c=='/': d.line((*p(0,1),*p(1,0)),fill=white,width=w)
    elif c=='\\': d.line((*p(0,0),*p(1,1)),fill=white,width=w)
    elif c==':': d.ellipse((x+cw//2-1,y+3,x+cw//2+1,y+5),fill=white); d.ellipse((x+cw//2-1,y+ch-5,x+cw//2+1,y+ch-3),fill=white)
    elif c=='.': d.ellipse((x+cw//2-1,y+ch-4,x+cw//2+1,y+ch-2),fill=white)
    elif c=='+': d.line((*p(0,.5),*p(1,.5)),fill=white,width=w);d.line((*p(.5,0),*p(.5,1)),fill=white,width=w)
    elif c in '*X': d.line((*p(0,0),*p(1,1)),fill=white,width=w);d.line((*p(0,1),*p(1,0)),fill=white,width=w); d.line((*p(.5,0),*p(.5,1)),fill=white,width=1) if c=='*' else None
    elif c=='^': d.line((*p(0,1),*p(.5,0)),fill=white,width=w);d.line((*p(.5,0),*p(1,1)),fill=white,width=w)
    elif c in SEG:
        for aa,bb in SEG[c]:d.line((*p(*aa),*p(*bb)),fill=white,width=w)

def raster(text,path,width,height):
    im=Image.new('RGB',(width,height),(8,8,8));d=ImageDraw.Draw(im);cw=width//W;ch=height//H
    for r,line_ in enumerate(text.splitlines()[:H]):
      for col,c in enumerate(line_[:W]): glyph(d,c,col*cw,r*ch,cw,ch)
    im.save(path)

def build_video(data,tmp):
    frames=seq(data); fd=tmp/'frames';fd.mkdir(); w=data['compile']['width'];h=data['compile']['height']
    for i,st in enumerate(frames): raster(ascii_frame(st),fd/f'{i:04d}.png',w,h)
    mp4=tmp/'motion.mp4'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(data['compile']['fps']),'-i',str(fd/'%04d.png'),'-c:v','libx264','-preset','veryslow','-crf',str(data['compile']['crf']),'-pix_fmt','yuv420p','-movflags','+faststart','-metadata','encoder=ascii-kinesis-v2',str(mp4)],check=True)
    return frames,mp4

def page(data,sheet,raw):
    import gzip
    payload=json.dumps(data,indent=2,sort_keys=True); enc=lambda text: base64.b64encode(gzip.compress(text.encode(),compresslevel=9,mtime=0)).decode(); A=enc(sheet); J=enc(payload); V=base64.b64encode(raw).decode()
    return f"""<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><title>{data['experiment_id']}</title><style>*{{box-sizing:border-box}}body{{margin:0;background:#090909;color:#eee;font-family:system-ui}}nav{{position:sticky;top:0;background:#111;padding:10px;display:flex;gap:8px}}button{{padding:8px 14px}}section{{display:none;padding:12px}}section.active{{display:block}}pre{{white-space:pre;overflow:auto;font-family:ui-monospace,SFMono-Regular,Consolas,\"Liberation Mono\",monospace;font-variant-ligatures:none;line-height:1.1}}video{{display:block;width:min(100%,800px);height:auto;background:#000}}</style></head><body><nav><button data-view=\"ascii\">ASCII</button><button data-view=\"json\">JSON</button><button data-view=\"video\">VIDEO</button></nav><section id=\"ascii\" class=\"active\"><pre id=\"a\"></pre></section><section id=\"json\"><pre id=\"j\"></pre></section><section id=\"video\"><video id=\"v\" controls autoplay muted loop playsinline></video></section><script>const A='{A}',J='{J}',V='{V}';async function d(s){{const u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new TextDecoder().decode(await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer())}};(async()=>{{document.getElementById('a').textContent=await d(A);document.getElementById('j').textContent=await d(J);document.getElementById('v').src='data:video/mp4;base64,'+V}})();for(const b of document.querySelectorAll('button[data-view]'))b.onclick=()=>{{for(const s of document.querySelectorAll('section'))s.classList.toggle('active',s.id===b.dataset.view)}};</script></body></html>"""

def main():
    data=json.loads(MOTION.read_text()); sheet=contact_sheet(data);SHEET.write_text(sheet)
    with tempfile.TemporaryDirectory() as td:
        frames,mp4=build_video(data,Path(td)); raw=mp4.read_bytes(); (ROOT/'.motion.mp4').write_bytes(raw)
    SPA.write_text(page(data,sheet,raw)); print(json.dumps({'frames':len(frames),'media_bytes':len(raw),'media_sha256':hashlib.sha256(raw).hexdigest(),'sheet_sha256':hashlib.sha256(sheet.encode()).hexdigest(),'spa_sha256':hashlib.sha256(SPA.read_bytes()).hexdigest()},sort_keys=True))
if __name__=='__main__':main()
