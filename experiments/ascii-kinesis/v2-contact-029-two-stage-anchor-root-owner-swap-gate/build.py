#!/usr/bin/env python3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import base64,gzip,hashlib,json,shutil,subprocess
R=Path(__file__).resolve().parent
M=R/'motion.json'; A=R/'contact-sheet.txt'; B=R/'.motion-build'; V=B/'motion.mp4'; S=R/'two-stage-anchor-root-owner-swap-gate.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
def font(n):
    for p in [Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'),Path('/usr/share/fonts/truetype/liberation2/LiberationMono-Regular.ttf')]:
        if p.is_file(): return ImageFont.truetype(str(p),n)
    return ImageFont.load_default()
def put(g,x,y,c):
    if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=c
def line(g,a,b,ch=None,overwrite=False):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; e=dx+dy; pts=[]
    while True:
        pts.append((x0,y0))
        if (x0,y0)==(x1,y1): break
        e2=2*e
        if e2>=dy: e+=dy; x0+=sx
        if e2<=dx: e+=dx; y0+=sy
    for i,(x,y) in enumerate(pts):
        if i in (0,len(pts)-1) or not (0<=y<len(g) and 0<=x<len(g[0])): continue
        if overwrite or g[y][x]==' ':
            if ch: g[y][x]=ch
            else:
                px,py=pts[max(0,i-1)]; nx,ny=pts[min(len(pts)-1,i+1)]; ddx=nx-px; ddy=ny-py
                g[y][x]='-' if abs(ddx)>=2*abs(ddy) else ('|' if abs(ddy)>=2*abs(ddx) else ('\\' if ddx*ddy>0 else '/'))
def body(g,k):
    rx,ry=k['a_root']; lean=k['a_lean']; pelvis=(rx,ry); spine=(rx+round(lean*.28),ry-4); shoulder=(rx+round(lean*.48),ry-7); head=(shoulder[0]+round(lean*.18),shoulder[1]-2); com=(rx+round(lean*.40),ry-4)
    line(g,head,shoulder,'|'); line(g,shoulder,spine,'|'); line(g,spine,pelvis,'|'); line(g,pelvis,tuple(k['a_rear_foot'])); line(g,pelvis,tuple(k['a_front_foot']))
    for idx,hand in enumerate([tuple(k['a_hand_1']),tuple(k['a_hand_2'])]):
        dy=-1 if idx==0 else 2; elbow=(shoulder[0]+max(3,(hand[0]-shoulder[0])//2), shoulder[1]+dy); line(g,shoulder,elbow); line(g,elbow,hand)
    put(g,*head,'O'); put(g,*pelvis,'P'); put(g,*com,'x'); put(g,*tuple(k['a_hand_1']),'o'); put(g,*tuple(k['a_hand_2']),'o')
    rear=tuple(k['a_rear_foot']); front=tuple(k['a_front_foot']); sup=k['support_contact']
    if 'FRONT' in sup and ('DOMINANT' in sup or 'BRAKE' in sup or 'TAKING' in sup): put(g,*rear,'~'); put(g,*front,'!')
    elif 'REAR' in sup and ('DOMINANT' in sup or 'LOADED' in sup or 'DRIVE' in sup): put(g,*rear,'!'); put(g,*front,'~' if 'LIGHT' in sup else '!')
    else: put(g,*rear,'!'); put(g,*front,'!')
def partner(g,k):
    bx,by=k['b_center']
    for x in range(bx-3,bx+4): put(g,x,by-2,'#'); put(g,x,by+2,'#')
    for y in range(by-1,by+2): put(g,bx-3,y,'#'); put(g,bx+3,y,'#')
    put(g,bx,by,'B'); put(g,bx+2,by-1,'>')
    if k['contact_count']>=1:
        h1=tuple(k['a_hand_1']); a1=(bx-3,by); line(g,h1,a1,'=',True); put(g,*h1,'*'); put(g,*a1,'*')
    if k['contact_count']>=2:
        h2=tuple(k['a_hand_2']); a2=(bx-3,by+1); line(g,h2,a2,'=',True); put(g,*h2,'*'); put(g,*a2,'*')
def art(k,m):
    W=m['rig']['grid']['width']; H=m['rig']['grid']['height']; fy=m['rig']['grid']['floor_y']; g=[[' ']*W for _ in range(H)]
    for x in range(1,W-1): g[fy][x]='_'
    body(g,k); partner(g,k); bx,by=k['b_center']; n=max(0,min(4,round(k['load']*4)))
    for i in range(n): put(g,min(W-2,bx+5+i),max(1,by-4),'>')
    if k['load']>=0.45:
        support=tuple(k['a_rear_foot']) if 'REAR_' in k['support_contact'] and 'FRONT_' not in k['support_contact'] else tuple(k['a_front_foot'])
        com=(k['a_root'][0]+round(k['a_lean']*.40),k['a_root'][1]-4); line(g,com,support,'.',False)
    return '\n'.join(''.join(r).rstrip() for r in g)
def sheet(m):
    out=['ASCII KINESIS V2 CONTACT029 — TWO-STAGE ANCHOR / ROOT-OWNER SWAP GATE','Primitive: TWO_STAGE_ANCHOR_ROOT_OWNER_SWAP_RELEASE_GATE','Pocket rule: root ownership may not become SHARED until TWO_ANCHORS is visibly established; final freedom is illegal until the two-anchor relationship has stepped back through ONE_ANCHOR and the actor is already braking.','Legend: O head | P root | x COM | o free hand | * contact | # partner mass | B center | = active constraint | ! trusted/load foot | ~ light/probe foot | > load/direction witness | . COM-support load path','Source: Zangief / Super Street Fighter II: The New Challengers / Sega Genesis / TSR asset 232259 / Home Center evidence 198sAnIYicWJ9Kw7vFA25m-WhtNrybj9DUAXNTC3PGMc','Rights firewall: evidence only. No source pixels/audio/palette/contours/layout/choreography; partner proxy and compiled movement are independent worker-authored abstractions.','Timing authority: source-authentic timing UNKNOWN. Every ONES/TWOS/FOURS exposure below is INFERRED.','']
    for k in m['keys']:
        out += [f"{k['key_id']} {k['name']} [{k['timing_class']}/{k['timing_provenance']}] bridge={str(k['bridge_key']).lower()}",f"REL={k['relationship']} CONTACTS={k['contact_count']} ROOT_OWNER={k['root_owner']} LOAD={k['load']:.2f} SUPPORT={k['support_contact']}",f"A_ROOT={k['a_root']} B_CENTER={k['b_center']} ROLE={k['causal_role']}",art(k,m),'']
    return '\n'.join(out).rstrip()+'\n'
def frame(k,m,fonts):
    im=Image.new('RGB',tuple(m['compile']['canvas']),(8,9,12)); d=ImageDraw.Draw(im)
    d.text((8,5),'CONTACT029 | 1 ANCHOR -> 2 ANCHORS -> OWNER SWAP -> 1 -> FREE',font=fonts[0],fill=(244,244,244)); d.text((8,22),f"{k['key_id']}  {k['name']}",font=fonts[0],fill=(244,244,244)); y=43
    for ln in art(k,m).splitlines(): d.text((8,y),ln,font=fonts[1],fill=(238,238,238)); y+=12
    d.text((8,356),f"rel={k['relationship']} contacts={k['contact_count']} owner={k['root_owner']} load={k['load']:.2f} support={k['support_contact']}",font=fonts[2],fill=(220,220,220)); d.text((8,375),f"A={k['a_root']} B={k['b_center']} bridge={k['bridge_key']} timing={k['timing_class']}",font=fonts[2],fill=(220,220,220)); return im
def gz(s): return base64.b64encode(gzip.compress(s.encode(),compresslevel=9,mtime=0)).decode()
def spa(a,j,v):
    vb=base64.b64encode(v).decode(); return '<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Contact029 Two-Stage Anchor Root-Owner Swap</title><style>body{margin:0;background:#101116;color:#eee;font-family:system-ui}nav{padding:10px;background:#191b22;position:sticky;top:0}button{margin-right:8px;padding:8px 14px}section{display:none;padding:16px}section.active{display:block}pre{font-family:"DejaVu Sans Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;border:1px solid #555}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre id="a"></pre></section><section id="json"><pre id="j"></pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,'+vb+'"></video></section><script>const A="'+gz(a)+'",J="'+gz(j)+'";async function z(s){let u=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return await new Response(new Blob([u]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}Promise.all([z(A),z(J)]).then(x=>{a.textContent=x[0];j.textContent=x[1]});for(const b of document.querySelectorAll("button"))b.onclick=()=>{for(const s of document.querySelectorAll("section"))s.classList.toggle("active",s.id===b.dataset.view)}</script></body></html>'
def main():
    m=json.loads(M.read_text()); A.write_text(sheet(m)); shutil.rmtree(B,ignore_errors=True); (B/'f').mkdir(parents=True); fonts=(font(13),font(11),font(10)); n=0
    for k in m['keys']:
        for _ in range(HOLD[k['timing_class']]): frame(k,m,fonts).save(B/'f'/f'{n:04d}.png'); n+=1
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','24','-i',str(B/'f'/'%04d.png'),'-map_metadata','-1','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-crf','35','-movflags','+faststart','-fflags','+bitexact','-flags:v','+bitexact',str(V)],check=True)
    v=V.read_bytes(); h=hashlib.sha256(v).hexdigest(); m['compile'].update({'media_sha256':h,'media_bytes':len(v),'frames':n,'actual_decode':'PASS_CURRENT_WORKER_ACTUAL_RENDER'}); M.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n'); A.write_text(sheet(m)); S.write_text(spa(A.read_text(),M.read_text(),v)); print(json.dumps({'ok':True,'frames':n,'media_sha256':h,'media_bytes':len(v)},sort_keys=True))
if __name__=='__main__': main()
