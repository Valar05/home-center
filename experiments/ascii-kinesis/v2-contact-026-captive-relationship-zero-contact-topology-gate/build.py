#!/usr/bin/env python3
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import base64,gzip,hashlib,json,shutil,subprocess

R=Path(__file__).resolve().parent
M=R/'motion.json'; A=R/'contact-sheet.txt'; B=R/'.motion-build'; V=B/'motion.mp4'
S=R/'captive-relationship-zero-contact-topology-gate.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}

def font(n):
    p=Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
    if not p.is_file(): raise SystemExit('MISSING_REQUIRED_FONT')
    return ImageFont.truetype(str(p),n)

def line(g,a,b,ch=None,overwrite=False):
    x0,y0=a; x1,y1=b
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    e=dx+dy; pts=[]
    while True:
        pts.append((x0,y0))
        if (x0,y0)==(x1,y1): break
        e2=2*e
        if e2>=dy: e+=dy; x0+=sx
        if e2<=dx: e+=dx; y0+=sy
    for i,(x,y) in enumerate(pts):
        if not (0<=y<len(g) and 0<=x<len(g[0])): continue
        if i==0 or i==len(pts)-1: continue
        if overwrite or g[y][x]==' ':
            if ch: g[y][x]=ch
            else:
                px,py=pts[max(0,i-1)]; nx,ny=pts[min(len(pts)-1,i+1)]
                ddx=nx-px; ddy=ny-py
                g[y][x]='-' if abs(ddx)>=2*abs(ddy) else ('|' if abs(ddy)>=2*abs(ddx) else ('\\' if ddx*ddy>0 else '/'))

def put(g,x,y,c):
    if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=c

def eyelet(g,m):
    cx,cy=m['rig']['grid']['eyelet_center']
    # Open negative-space aperture. The rod may pass through the hole; the eyelet itself remains visibly fixed.
    for x in range(cx-3,cx+4):
        put(g,x,cy-4,'=')
        put(g,x,cy+4,'=')
    for y in range(cy-3,cy+4):
        put(g,cx-3,y,'(')
        put(g,cx+3,y,')')
    put(g,cx-3,cy-4,'/')
    put(g,cx+3,cy-4,'\\')
    put(g,cx-3,cy+4,'\\')
    put(g,cx+3,cy+4,'/')
    put(g,cx,cy-4,'^')
    put(g,cx,cy+4,'v')

def art(k,m):
    W=m['rig']['grid']['width']; H=m['rig']['grid']['height']; fy=m['rig']['grid']['floor_y']
    g=[[' ']*W for _ in range(H)]
    for x in range(1,W-1): g[fy][x]='_'
    eyelet(g,m)

    rx,ry=k['root']; lean=k['lean']; compact=k['compact']
    pelvis=(rx,ry); spine=(rx+round(lean*.35),ry-(3-compact))
    sh=(rx+round(lean*.55),ry-(6-compact))
    head=(sh[0]+round(lean*.25),sh[1]-2)
    rear_foot=(rx-5,fy); front_foot=(rx+5,fy)
    com=(rx+round(lean*.7),ry-3)

    line(g,head,sh,'|')
    line(g,sh,spine,'|')
    line(g,spine,pelvis,'|')
    line(g,pelvis,rear_foot)
    line(g,pelvis,front_foot)

    h1=tuple(k['hand']); h2=tuple(k['rear_hand'])
    # Front and rear arm chains converge on independently authored hands.
    el1=(sh[0]+5,sh[1]+(1 if h1[1]>=sh[1] else -1))
    el2=(sh[0]+2,sh[1]+3)
    line(g,sh,el1); line(g,el1,h1)
    line(g,sh,el2); line(g,el2,h2)

    # The rigid tool is always explicit. It is drawn after the body but before semantic contact marker.
    line(g,h2,tuple(k['tip']),'=' , True)
    put(g,*h2,'o'); put(g,*h1,'o'); put(g,*tuple(k['tip']),'>')
    put(g,*pelvis,'P'); put(g,*head,'O'); put(g,*com,'x')

    # Contact marker is geometric, not merely a label.
    cx,cy=m['rig']['grid']['eyelet_center']
    if k['contact_state']=='UPPER_RIM':
        put(g,cx,cy-4,'@')
        # normal reaction points back/down along the loaded side
        n=max(1,min(5,round(k['normal_load']*5)))
        for i in range(1,n+1): put(g,cx-i,cy-5-i//3,'<')
    elif k['contact_state']=='LOWER_RIM':
        put(g,cx,cy+4,'@')
        n=max(1,min(5,round(k['normal_load']*5)))
        for i in range(1,n+1): put(g,cx-i,cy+5+i//3,'<')

    sc=k['support_contact']
    if 'REAR' in sc or 'BOTH' in sc: put(g,*rear_foot,'!')
    if 'FRONT' in sc or 'BOTH' in sc: put(g,*front_foot,'!')
    if sc=='FRONT_CATCH': put(g,*front_foot,'!')
    if sc=='FRONT_PROBE': put(g,*front_foot,'?')

    # Relationship bead. This remains even when instantaneous contact is GAP.
    if k['relationship_state']=='CAPTIVE':
        put(g,cx+5,cy,'C')
    elif k['relationship_state']=='ELIGIBLE':
        put(g,cx+5,cy,'?')

    return '\n'.join(''.join(r).rstrip() for r in g)

def sheet(m):
    o=[
        'ASCII KINESIS V2 CONTACT026 — CAPTIVE RELATIONSHIP / ZERO-CONTACT TOPOLOGY GATE',
        'Primitive: CAPTIVE_RELATIONSHIP_PERSISTS_THROUGH_ZERO_CONTACT',
        'Pocket rule: NO CONTACT DOES NOT MEAN FREE. The threaded endpoint can float inside the eyelet at zero contact/zero force while the captive relationship remains.',
        'Legend: O head | P root | x COM | o hand | > tool endpoint | @ geometric rim contact | C captive relationship | ! support | ? eligibility/probe',
        'Eyelet is an authored abstract constraint. Source art/pixels/palette/choreography never enter the output.',
        ''
    ]
    for k in m['keys']:
        full=[r.ljust(m['rig']['grid']['width']) for r in art(k,m).splitlines()]
        crop=[]
        for y in range(5,26):
            r=full[y] if y<len(full) else ' '*m['rig']['grid']['width']
            crop.append(r[10:76])
        o += [
            f"{k['key_id']} {k['name']} [{k['timing_class']}/{k['timing_provenance']}]",
            f"REL={k['relationship_state']} CAPTURE={k['capture']} CONTACT={k['contact_state']} FORCE={k['force_owner']} N={k['normal_load']:.2f}",
            f"ROOT={k['root']} COM_CONSEQUENCE=lean:{k['lean']} SUPPORT={k['support_contact']} CUSTODY={k['custody']} ROLE={k['causal_role']}",
            *crop,''
        ]
    return '\n'.join(o).rstrip()+'\n'

def frame(k,m,fonts):
    im=Image.new('RGB',tuple(m['compile']['canvas']),(8,9,12))
    d=ImageDraw.Draw(im)
    d.text((8,5),'CONTACT026 | ZERO CONTACT != FREE',font=fonts[0],fill=(242,242,242))
    d.text((8,20),f"{k['key_id']}  {k['name']}",font=fonts[0],fill=(242,242,242))
    y=38
    for ln in art(k,m).splitlines():
        d.text((8,y),ln,font=fonts[1],fill=(238,238,238)); y+=10
    d.text((8,306),f"relationship={k['relationship_state']}  capture={k['capture']}  contact={k['contact_state']}  force={k['force_owner']}  load={k['normal_load']:.2f}",font=fonts[2],fill=(220,220,220))
    d.text((8,321),f"support={k['support_contact']}  custody={k['custody']}  root={k['root']}  lean={k['lean']}",font=fonts[2],fill=(220,220,220))
    d.text((8,336),'thread -> upper load -> zero-contact captive gap -> lower load -> zero-contact unload -> endpoint escape -> free arc -> displaced settle',font=fonts[2],fill=(220,220,220))
    return im

def gz(s):
    return base64.b64encode(gzip.compress(s.encode(),compresslevel=9,mtime=0)).decode()

def spa(a,j,v):
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Contact026 Captive Relationship Zero-Contact Gate</title><style>body{margin:0;background:#101116;color:#eee;font-family:system-ui}nav{padding:10px;background:#191b22;position:sticky;top:0}button{margin-right:8px;padding:8px 14px}section{display:none;padding:16px}section.active{display:block}pre{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;border:1px solid #555}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+base64.b64encode(v).decode()+'"></video></section><script>const A="'+gz(a)+'",J="'+gz(j)+'";async function z(s){let u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}Promise.all([z(A),z(J)]).then(x=>{a.textContent=x[0];j.textContent=x[1]});for(const b of document.querySelectorAll("button"))b.onclick=()=>{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view)}</script></body></html>'

def main():
    m=json.loads(M.read_text())
    A.write_text(sheet(m))
    shutil.rmtree(B,ignore_errors=True); (B/'f').mkdir(parents=True)
    fonts=(font(10),font(10),font(8)); n=0
    for k in m['keys']:
        for _ in range(HOLD[k['timing_class']]):
            frame(k,m,fonts).save(B/'f'/f'{n:04d}.png'); n+=1
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(B/'f'/'%04d.png'),'-map_metadata','-1','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-crf','40','-movflags','+faststart','-fflags','+bitexact','-flags:v','+bitexact',str(V)],check=True)
    v=V.read_bytes(); h=hashlib.sha256(v).hexdigest(); e=m['compile'].get('media_sha256')
    if e and h!=e: raise SystemExit(f'MEDIA_IDENTITY_MISMATCH {e} != {h}')
    if not e:
        m['compile']['media_sha256']=h; m['compile']['media_bytes']=len(v); m['compile']['actual_decode']='PASS_CURRENT_WORKER_ACTUAL_RENDER'; m['compile']['frames']=n
        M.write_text(json.dumps(m,separators=(',',':'),ensure_ascii=False)+'\n')
        A.write_text(sheet(m))
    S.write_text(spa(A.read_text(),M.read_text(),v))
    print(json.dumps({'ok':True,'frames':n,'media_sha256':h,'media_bytes':len(v)},sort_keys=True))

if __name__=='__main__': main()
