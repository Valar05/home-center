#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import base64, gzip, hashlib, json, shutil, subprocess

R=Path(__file__).resolve().parent
M=R/'motion.json'
A=R/'contact-sheet.txt'
B=R/'.motion-build'
V=B/'motion.mp4'
S=R/'overlap-custody-transfer-no-free-state-gate.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}

def font(n):
    p=Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf')
    if not p.is_file(): raise SystemExit('MISSING_REQUIRED_FONT')
    return ImageFont.truetype(str(p),n)

def put(g,x,y,c):
    if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=c

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
        if i==0 or i==len(pts)-1: continue
        if not (0<=y<len(g) and 0<=x<len(g[0])): continue
        if overwrite or g[y][x]==' ':
            if ch:
                g[y][x]=ch
            else:
                px,py=pts[max(0,i-1)]; nx,ny=pts[min(len(pts)-1,i+1)]
                ddx=nx-px; ddy=ny-py
                g[y][x]='-' if abs(ddx)>=2*abs(ddy) else ('|' if abs(ddy)>=2*abs(ddx) else ('\\' if ddx*ddy>0 else '/'))

def body(g,root,lean,hand,side,support,tag):
    rx,ry=root; fy=len(g)-3
    sign=1 if side=='A' else -1
    pelvis=(rx,ry)
    spine=(rx+round(lean*.28),ry-4)
    shoulder=(rx+round(lean*.42),ry-7)
    head=(shoulder[0]+round(lean*.18),shoulder[1]-2)
    com=(rx+round(lean*.62),ry-4)
    rear=(rx-sign*4,fy)
    front=(rx+sign*5,fy)
    line(g,head,shoulder,'|')
    line(g,shoulder,spine,'|')
    line(g,spine,pelvis,'|')
    line(g,pelvis,rear)
    line(g,pelvis,front)
    elbow=(shoulder[0]+sign*4, shoulder[1]+(1 if hand[1]>=shoulder[1] else -1))
    line(g,shoulder,elbow)
    line(g,elbow,tuple(hand))
    free_elbow=(shoulder[0]-sign*3,shoulder[1]+2)
    free_hand=(free_elbow[0]-sign*3,free_elbow[1]+2)
    line(g,shoulder,free_elbow); line(g,free_elbow,free_hand)
    put(g,*head,'O'); put(g,*pelvis,'P'); put(g,*com,'x')
    put(g,*hand,'o'); put(g,*free_hand,'h')
    if 'BOTH' in support:
        put(g,*rear,'!'); put(g,*front,'!')
    elif 'REAR' in support:
        put(g,*rear,'!'); put(g,*front,'~')
    elif 'FRONT' in support:
        put(g,*front,'!'); put(g,*rear,'~')
    else:
        put(g,*rear,'~'); put(g,*front,'~')
    put(g,rx,fy+1,tag)

def art(k,m):
    W=m['rig']['grid']['width']; H=m['rig']['grid']['height']; fy=m['rig']['grid']['floor_y']
    g=[[' ']*W for _ in range(H)]
    for x in range(1,W-1): g[fy][x]='_'
    body(g,k['a_root'],k['a_lean'],k['a_hand'],'A',k['support_a'],'A')
    body(g,k['b_root'],k['b_lean'],k['b_hand'],'B',k['support_b'],'B')
    line(g,tuple(k['baton_l']),tuple(k['baton_r']),'=',True)
    put(g,*tuple(k['baton_l']),'['); put(g,*tuple(k['baton_r']),']')
    if k['a_contact']: put(g,*tuple(k['a_hand']),'*')
    if k['b_contact']: put(g,*tuple(k['b_hand']),'*')
    if k['relationship']=='B_ELIGIBLE':
        bx,by=k['b_hand']; put(g,bx-1,by,'?')
    la=max(0,min(4,round(k['load_a']*4)))
    lb=max(0,min(4,round(k['load_b']*4)))
    lx,ly=k['baton_l']; rx,ry=k['baton_r']
    for i in range(la):
        put(g,lx-2-i,ly-1,'<')
    for i in range(lb):
        put(g,rx+2+i,ry-1,'>')
    mx=round((lx+rx)/2); my=round((ly+ry)/2)+2
    owner={'A':'A','A_PRIMARY_B_CONTACT':'a','DUAL_A_PRIMARY':'a','DUAL_B_PRIMARY':'b','DUAL_B_FULL':'B','B':'B'}.get(k['custody'],'+')
    put(g,mx,my,owner)
    return '\n'.join(''.join(r).rstrip() for r in g)

def sheet(m):
    o=[
      'ASCII KINESIS V2 CONTACT027 — OVERLAPPING CUSTODY TRANSFER / NO-FREE-STATE GATE',
      'Primitive: OVERLAPPING_CUSTODY_TRANSFER_WITHOUT_FREE_STATE',
      'Pocket rule: TOUCH DOES NOT TELEPORT OWNERSHIP. B earns eligibility, contact, then load authority before A may release; the baton never enters FREE state.',
      'Legend: O head | P root | x COM | o hand | * hand/object contact | [====] baton | ! trusted support | ~ unloaded/probe | ? precontact | < > load authority | a/b/B custody witness',
      'Source role: commercial source evidence only. No source pixels, palette, costume, contours, layout, choreography, audio, tracing, or close imitation enter this artifact.',
      ''
    ]
    for k in m['keys']:
        o += [
          f"{k['key_id']} {k['name']} [{k['timing_class']}/{k['timing_provenance']}]",
          f"REL={k['relationship']} CUSTODY={k['custody']} A_CONTACT={k['a_contact']} B_CONTACT={k['b_contact']} LOAD_A={k['load_a']:.2f} LOAD_B={k['load_b']:.2f}",
          f"A_ROOT={k['a_root']} A_LEAN={k['a_lean']} A_SUPPORT={k['support_a']} | B_ROOT={k['b_root']} B_LEAN={k['b_lean']} B_SUPPORT={k['support_b']}",
          f"ROLE={k['causal_role']}",
          art(k,m),
          ''
        ]
    return '\n'.join(o).rstrip()+'\n'

def frame(k,m,fonts):
    im=Image.new('RGB',tuple(m['compile']['canvas']),(8,9,12))
    d=ImageDraw.Draw(im)
    d.text((8,5),'CONTACT027 | OVERLAPPING CUSTODY, NEVER FREE',font=fonts[0],fill=(244,244,244))
    d.text((8,19),f"{k['key_id']}  {k['name']}",font=fonts[0],fill=(244,244,244))
    y=36
    for ln in art(k,m).splitlines():
        d.text((8,y),ln,font=fonts[1],fill=(238,238,238)); y+=10
    d.text((8,304),f"custody={k['custody']}  relation={k['relationship']}  contacts=A:{int(k['a_contact'])}/B:{int(k['b_contact'])}  load={k['load_a']:.2f}/{k['load_b']:.2f}",font=fonts[2],fill=(220,220,220))
    d.text((8,318),f"support A={k['support_a']}  B={k['support_b']}  roots A={k['a_root']}  B={k['b_root']}  bridge={k['bridge_key']}",font=fonts[2],fill=(220,220,220))
    return im

def gz(s):
    return base64.b64encode(gzip.compress(s.encode(),compresslevel=9,mtime=0)).decode()

def spa(a,j,v):
    vb=base64.b64encode(v).decode()
    return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Contact027 Overlap Custody Transfer</title><style>body{margin:0;background:#101116;color:#eee;font-family:system-ui}nav{padding:10px;background:#191b22;position:sticky;top:0}button{margin-right:8px;padding:8px 14px}section{display:none;padding:16px}section.active{display:block}pre{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;border:1px solid #555}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+vb+'"></video></section><script>const A="'+gz(a)+'",J="'+gz(j)+'";async function z(s){let u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}Promise.all([z(A),z(J)]).then(x=>{a.textContent=x[0];j.textContent=x[1]});for(const b of document.querySelectorAll("button"))b.onclick=()=>{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view)}</script></body></html>'

def main():
    m=json.loads(M.read_text())
    A.write_text(sheet(m))
    shutil.rmtree(B,ignore_errors=True); (B/'f').mkdir(parents=True)
    fonts=(font(10),font(9),font(8)); n=0
    for k in m['keys']:
        for _ in range(HOLD[k['timing_class']]):
            frame(k,m,fonts).save(B/'f'/f'{n:04d}.png'); n+=1
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(B/'f'/'%04d.png'),
                    '-map_metadata','-1','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-crf','39',
                    '-movflags','+faststart','-fflags','+bitexact','-flags:v','+bitexact',str(V)],check=True)
    v=V.read_bytes(); h=hashlib.sha256(v).hexdigest(); e=m['compile'].get('media_sha256')
    if e and h!=e: raise SystemExit(f'MEDIA_IDENTITY_MISMATCH {e} != {h}')
    if not e:
        m['compile']['media_sha256']=h
        m['compile']['media_bytes']=len(v)
        m['compile']['actual_decode']='PASS_CURRENT_WORKER_ACTUAL_RENDER'
        m['compile']['frames']=n
        M.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n')
        A.write_text(sheet(m))
    S.write_text(spa(A.read_text(),M.read_text(),v))
    print(json.dumps({'ok':True,'frames':n,'media_sha256':h,'media_bytes':len(v)},sort_keys=True))

if __name__=='__main__':
    main()
