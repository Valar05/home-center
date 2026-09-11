#!/usr/bin/env python3
import json, math, base64, hashlib, subprocess, tempfile, html
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
CONTACT=HERE/'contact-sheet.txt'
SPA=HERE/'internal-mass-deploy-com-conservation-landing-debt.motion.html'
MP4=HERE/'_authoritative.mp4'
DELIVERY=HERE/'_delivery.mp4'
W,H,FPS=960,448,24
FONT_PATH='/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
FONT=ImageFont.truetype(FONT_PATH,21)
SMALL=ImageFont.truetype(FONT_PATH,14)
TINY=ImageFont.truetype(FONT_PATH,11)
GROUND_Y=374

def world_to_px(root):
    return 70+float(root[0])*8.55, 90+float(root[1])*7.2

def segment_char(dx,dy):
    if abs(dx)<2: return '|'
    if abs(dy)<2: return '-'
    return '\\' if dx*dy>0 else '/'

def draw_char_segment(d,a,b,font=FONT,fill='black',steps=None):
    ax,ay=a; bx,by=b
    dist=math.hypot(bx-ax,by-ay)
    n=steps or max(2,int(dist/13))
    ch=segment_char(bx-ax,by-ay)
    for i in range(1,n):
        t=i/n
        x=ax+(bx-ax)*t; y=ay+(by-ay)*t
        d.text((x-6,y-11),ch,font=font,fill=fill)

def lerp(a,b,t): return a+(b-a)*t

def pose_geometry(root,key):
    cx,cy=world_to_px(root)
    body_x=cx+float(key.get('body_offset_x',0))*5.4
    lean=float(key.get('lean',0))*3.3
    px,py=body_x,cy
    pose=key['pose']
    head=(px+lean,py-43); neck=(px+lean*0.7,py-26); pelvis=(px,py)
    shoulderL=(neck[0]-13,neck[1]+5); shoulderR=(neck[0]+13,neck[1]+5)
    kneeL=(px-14,py+19); kneeR=(px+15,py+17)
    footL=(px-26,py+42); footR=(px+29,py+42)
    handL=(px-33+lean,py-5); handR=(px+34+lean,py-2)
    if pose=='load_stowed':
        handL=(px-37,py-2); handR=(px+27,py-11); kneeL=(px-19,py+19); kneeR=(px+12,py+20); footL=(px-37,GROUND_Y); footR=(px+31,GROUND_Y)
    elif pose=='launch':
        handL=(px-30,py-19); handR=(px+34,py-22); kneeL=(px-8,py+20); kneeR=(px+19,py+16)
    elif pose=='unlock':
        handL=(px-35,py-24); handR=(px+36,py-10); kneeL=(px-18,py+15); kneeR=(px+14,py+22)
    elif pose=='deploy_mid':
        handL=(px-40,py-21); handR=(px+38,py-13); kneeL=(px-17,py+19); kneeR=(px+16,py+20)
    elif pose=='deploy_apex':
        handL=(px-43,py-18); handR=(px+39,py-14); kneeL=(px-14,py+23); kneeR=(px+13,py+21)
    elif pose=='full_deploy':
        handL=(px-45,py-10); handR=(px+40,py-14); kneeL=(px-20,py+19); kneeR=(px+12,py+23)
    elif pose=='counterbalance':
        handL=(px-46,py-5); handR=(px+39,py-13); kneeL=(px-21,py+18); kneeR=(px+13,py+24)
    elif pose=='landing_prep':
        handL=(px-42,py+1); handR=(px+37,py-10); kneeL=(px-20,py+23); kneeR=(px+16,py+22)
    elif pose=='left_precontact':
        handL=(px-39,py+6); handR=(px+35,py-7); kneeL=(px-20,py+19); kneeR=(px+18,py+20); footL=(px-31,GROUND_Y-4); footR=(px+30,GROUND_Y-13)
    elif pose=='left_catch':
        handL=(px-36,py+8); handR=(px+34,py-4); kneeL=(px-19,py+8); kneeR=(px+18,py+15); footL=(px-32,GROUND_Y); footR=(px+31,GROUND_Y-11)
    elif pose=='left_crush':
        head=(px+lean,py-35); neck=(px+lean*0.7,py-19); shoulderL=(neck[0]-13,neck[1]+5); shoulderR=(neck[0]+13,neck[1]+5); handL=(px-32,py+10); handR=(px+38,py+6); kneeL=(px-16,py+6); kneeR=(px+17,py+11); footL=(px-32,GROUND_Y); footR=(px+31,GROUND_Y-8)
    elif pose=='both_catch':
        handL=(px-28,py+5); handR=(px+35,py+4); kneeL=(px-17,py+8); kneeR=(px+15,py+8); footL=(px-32,GROUND_Y); footR=(px+31,GROUND_Y)
    elif pose=='rebound':
        head=(px+lean,py-47); neck=(px+lean*0.7,py-29); shoulderL=(neck[0]-13,neck[1]+5); shoulderR=(neck[0]+13,neck[1]+5); handL=(px-35,py-13); handR=(px+22,py-23); kneeL=(px-17,py+15); kneeR=(px+15,py+14); footL=(px-34,GROUND_Y); footR=(px+31,GROUND_Y)
    elif pose=='counterswing':
        handL=(px-20,py-20); handR=(px+38,py-5); kneeL=(px-18,py+13); kneeR=(px+16,py+14); footL=(px-34,GROUND_Y); footR=(px+31,GROUND_Y)
    elif pose=='settle':
        handL=(px-24,py-5); handR=(px+30,py-8); kneeL=(px-18,py+12); kneeR=(px+15,py+13); footL=(px-34,GROUND_Y); footR=(px+31,GROUND_Y)
    elif pose=='final_displaced':
        handL=(px-24,py-8); handR=(px+25,py-8); kneeL=(px-17,py+12); kneeR=(px+16,py+12); footL=(px-34,GROUND_Y); footR=(px+32,GROUND_Y)
    return dict(com=(cx,cy),px=px,py=py,head=head,neck=neck,pelvis=pelvis,shoulderL=shoulderL,shoulderR=shoulderR,handL=handL,handR=handR,kneeL=kneeL,kneeR=kneeR,footL=footL,footR=footR)

def boom_geometry(g,key):
    a=key['assembly']; ext=float(a['extension']); angle=math.radians(float(a['boom_deg']))
    pivot=g['handR']; length=28+ext*118
    tip=(pivot[0]+math.cos(angle)*length,pivot[1]+math.sin(angle)*length)
    mass=(pivot[0]+math.cos(angle)*length*0.83,pivot[1]+math.sin(angle)*length*0.83)
    return pivot,mass,tip

def render_frame(root,key):
    im=Image.new('RGB',(W,H),'white'); d=ImageDraw.Draw(im)
    d.line((28,GROUND_Y,W-28,GROUND_Y),fill='black',width=2)
    for x in range(34,W-30,34): d.text((x,GROUND_Y+3),'_',font=TINY,fill='black')
    g=pose_geometry(root,key)
    cx,cy=g['com']; d.ellipse((cx-7,cy-7,cx+7,cy+7),outline='black',width=2); d.text((cx-5,cy-11),'C',font=TINY,fill='black')
    d.text((g['head'][0]-6,g['head'][1]-12),'o',font=FONT,fill='black'); d.text((g['neck'][0]-6,g['neck'][1]-12),'|',font=FONT,fill='black'); d.text((g['pelvis'][0]-6,g['pelvis'][1]-12),'+',font=FONT,fill='black')
    for a,b in [(g['shoulderL'],g['handL']),(g['shoulderR'],g['handR']),(g['neck'],g['pelvis']),(g['pelvis'],g['kneeL']),(g['kneeL'],g['footL']),(g['pelvis'],g['kneeR']),(g['kneeR'],g['footR'])]: draw_char_segment(d,a,b)
    for pt,ch in [(g['handL'],'x'),(g['handR'],'x'),(g['footL'],'_'),(g['footR'],'_')]: d.text((pt[0]-6,pt[1]-12),ch,font=FONT,fill='black')
    pivot,mass,tip=boom_geometry(g,key); draw_char_segment(d,pivot,tip); d.text((mass[0]-6,mass[1]-12),'#',font=FONT,fill='black'); d.text((tip[0]-6,tip[1]-12),'@',font=FONT,fill='black')
    sc=key['support_contact']
    if sc=='BOTH_FEET_GROUND': d.text((g['footL'][0]-8,GROUND_Y-18),'*',font=FONT,fill='black'); d.text((g['footR'][0]-8,GROUND_Y-18),'*',font=FONT,fill='black')
    elif 'LEFT' in sc: d.text((g['footL'][0]-8,GROUND_Y-18),'*',font=FONT,fill='black')
    d.text((20,14),'AIRBORNE041 :: INTERNAL MASS DEPLOY -> COM CONSERVATION -> LANDING DEBT',font=SMALL,fill='black')
    d.text((20,35),f"{key['key_id']}  {key['label']}",font=SMALL,fill='black')
    d.text((20,H-54),f"support={sc}   assembly={key['assembly']['state']} ext={key['assembly']['extension']:.2f}",font=TINY,fill='black')
    d.text((20,H-39),f"system_COM=({root[0]:.1f},{root[1]:.1f}) body_offset_x={key.get('body_offset_x',0):.1f} force={key['force']}",font=TINY,fill='black')
    d.text((20,H-24),f"timing={key['timing_class']} / {key['timing_provenance']} clock={key['assembly']['clock']}",font=TINY,fill='black')
    return im

def quad(p0,p1,pc,t):
    u=1-t; return (u*u*p0[0]+2*u*t*pc[0]+t*t*p1[0],u*u*p0[1]+2*u*t*pc[1]+t*t*p1[1])

def interp_key(k,nxt,s):
    out=json.loads(json.dumps(k)); out['lean']=lerp(float(k.get('lean',0)),float(nxt.get('lean',0)),s); out['body_offset_x']=lerp(float(k.get('body_offset_x',0)),float(nxt.get('body_offset_x',0)),s); out['assembly']['extension']=lerp(float(k['assembly']['extension']),float(nxt['assembly']['extension']),s); out['assembly']['boom_deg']=lerp(float(k['assembly']['boom_deg']),float(nxt['assembly']['boom_deg']),s)
    if s>=0.58: out['pose']=nxt['pose']
    return out

def compile_frames(m):
    frames=[]; ks=m['keys']
    for i,k in enumerate(ks):
        for _ in range(k['hold_frames']): frames.append(render_frame(k['root'],k))
        if i+1<len(ks):
            n=k['bridge_frames']; nxt=ks[i+1]
            for j in range(1,n+1):
                t=j/(n+1); s=t*t*(3-2*t); frames.append(render_frame(quad(k['root'],nxt['root'],k['bridge_control'],s),interp_key(k,nxt,s)))
    return frames

def put(g,x,y,ch):
    if 0<=y<len(g) and 0<=x<len(g[0]): g[y][x]=ch

def grid_segment(g,a,b):
    ax,ay=a; bx,by=b; n=max(2,int(max(abs(bx-ax),abs(by-ay))*1.5)); ch=segment_char(bx-ax,by-ay)
    for i in range(1,n): t=i/n; put(g,round(ax+(bx-ax)*t),round(ay+(by-ay)*t),ch)

def ascii_frame(k,w=58,h=15):
    g=[[' ']*w for _ in range(h)]; gy=13
    for x in range(w): g[gy][x]='_'
    rx=max(9,min(w-15,8+round(float(k['root'][0])*0.38))); ry=max(4,min(8,4+round((float(k['root'][1])-11.5)*0.18)))
    body=rx+round(float(k.get('body_offset_x',0))*0.35); head=(body+round(float(k.get('lean',0))*0.18),ry-3); neck=(body,ry-2); pelvis=(body,ry)
    handL=(body-4,ry-1); handR=(body+4,ry-1); kneeL=(body-2,ry+2); kneeR=(body+2,ry+2); footL=(body-4,ry+4); footR=(body+4,ry+4)
    pose=k['pose']
    if pose in ('load_stowed','settle','final_displaced','both_catch','rebound','counterswing'): footL=(body-4,gy-1); footR=(body+4,gy-1)
    elif pose=='left_precontact': footL=(body-4,gy-2); footR=(body+4,gy-4)
    elif pose in ('left_catch','left_crush'): footL=(body-4,gy-1); footR=(body+4,gy-3)
    if pose in ('deploy_mid','deploy_apex','full_deploy','counterbalance'): handL=(body-5,ry-1); handR=(body+5,ry-1)
    put(g,rx,ry,'C'); put(g,*head,'o'); put(g,*neck,'|'); put(g,*pelvis,'+')
    for a,b in [(neck,pelvis),((body-1,ry-2),handL),((body+1,ry-2),handR),(pelvis,kneeL),(kneeL,footL),(pelvis,kneeR),(kneeR,footR)]: grid_segment(g,a,b)
    put(g,*handL,'x'); put(g,*handR,'x'); put(g,*footL,'_'); put(g,*footR,'_')
    ext=float(k['assembly']['extension']); angle=math.radians(float(k['assembly']['boom_deg'])); ln=3+round(ext*9); tip=(round(handR[0]+math.cos(angle)*ln),round(handR[1]+math.sin(angle)*ln*0.25)); mass=(round(handR[0]+math.cos(angle)*ln*0.82),round(handR[1]+math.sin(angle)*ln*0.25*0.82)); grid_segment(g,handR,tip); put(g,*mass,'#'); put(g,*tip,'@')
    sc=k['support_contact']
    if sc=='BOTH_FEET_GROUND': put(g,footL[0],gy-1,'*'); put(g,footR[0],gy-1,'*')
    elif 'LEFT' in sc: put(g,footL[0],gy-1,'*')
    return '\n'.join(''.join(r).rstrip() for r in g)

def make_contact(m):
    s=m['source']; parts=['ASCII KINESIS V2 - AIRBORNE041','AIRBORNE_INTERNAL_MASS_DEPLOY_COM_CONSERVATION_LANDING_DEBT',f"SOURCE EVIDENCE: TSR asset {s['asset_id']} - {s['character']} - {s['game']} - {s['platform']} - commissioned evidence {s['evidence_artifact_id']}",'SOURCE TIMING: UNKNOWN. ALL DECISIVE COMPILE TIMING: INFERRED / STREET_FIGHTER-CAPCOM.','RIGHTS: source evidence only; no source pixels/palette/costume/contours/layout/tracing/choreography/audio/close imitation.','AIRBORNE LAW: deployment is INTERNAL redistribution. Whole-system COM marker C keeps one unsupported ballistic arc. Body/pelvis + countershifts opposite the deployed # mass; deployment never invents external root redirection.','LANDING LAW: outboard mass debt survives into descent -> separated LEFT precontact -> LEFT first support -> impact mass overshoot -> delayed RIGHT support -> retract/rebound -> counterswing -> displaced rest.','LEGEND: C=whole-system COM/root, +=pelvis/body root, x=hands, #=deployed internal mass, @=assembly tip, *=earned support.','']
    for k in m['keys']:
        parts += ['='*110,f"{k['key_id']} :: {k['label']}",f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']} | causal_role={k['causal_role']}",f"support_contact={k['support_contact']} | eligibility={k['contact_eligibility']}",f"system_com_root={k['root']} | body_offset_x={k.get('body_offset_x',0)} | force={k['force']}",f"assembly={k['assembly']}",f"clock_ownership={k['clock_ownership']}",ascii_frame(k),'']
    return '\n'.join(parts).rstrip()+'\n'

def encode_mp4(frames,out,w=W,h=H,crf=28):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,im in enumerate(frames):
            if im.size!=(w,h): im=im.resize((w,h),Image.Resampling.LANCZOS)
            im.save(td/f'f{i:04d}.png',compress_level=9)
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-i',str(td/'f%04d.png'),'-c:v','libx264','-preset','veryslow','-crf',str(crf),'-pix_fmt','yuv420p','-movflags','+faststart','-metadata','encoder=ASCII-Kinesis-V2',str(out)],check=True)

def make_spa(contact,m,delivery_bytes):
    b64=base64.b64encode(delivery_bytes).decode('ascii'); mtxt=json.dumps(m,indent=2,ensure_ascii=False)+'\n'; css="body{font-family:system-ui;margin:0;background:#fff;color:#111}nav{position:sticky;top:0;background:#fff;border-bottom:1px solid #999;padding:10px}button{font:inherit;margin-right:8px;padding:7px 14px}section{display:none;padding:14px}section.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;font-feature-settings:'liga' 0,'calt' 0;white-space:pre;overflow:auto;line-height:1.08;border:1px solid #999;padding:12px}video{max-width:100%;width:720px;background:#000}"; js="document.querySelectorAll('button[data-view]').forEach(b=>b.onclick=()=>{document.querySelectorAll('section').forEach(s=>s.classList.remove('active'));document.getElementById(b.dataset.view).classList.add('active')})"; return f'<!doctype html><html><head><meta charset="utf-8"><title>Airborne041</title><style>{css}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii" class="active"><pre>{html.escape(contact)}</pre></section><section id="json"><pre>{html.escape(mtxt)}</pre></section><section id="video"><video controls autoplay loop muted playsinline src="data:video/mp4;base64,{b64}"></video></section><script>{js}</script></body></html>'

def main():
    m=json.loads(MOTION.read_text(encoding='utf-8')); contact=make_contact(m); CONTACT.write_text(contact,encoding='utf-8'); frames=compile_frames(m); encode_mp4(frames,MP4,W,H,28); delivery_frames=[im.resize((480,224),Image.Resampling.LANCZOS) for im in frames]; encode_mp4(delivery_frames,DELIVERY,480,224,36); media=MP4.read_bytes(); delivery=DELIVERY.read_bytes(); SPA.write_text(make_spa(contact,m,delivery),encoding='utf-8'); print(json.dumps({'frames':len(frames),'authoritative_bytes':len(media),'authoritative_sha256':hashlib.sha256(media).hexdigest(),'delivery_bytes':len(delivery),'delivery_sha256':hashlib.sha256(delivery).hexdigest(),'contact_bytes':len(CONTACT.read_bytes()),'spa_bytes':len(SPA.read_bytes())},indent=2))
if __name__=='__main__': main()
