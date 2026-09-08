#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, hashlib, html, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
CONTACT=HERE/'contact-sheet.txt'
MP4=HERE/'scoped-freeze-release-repair.motion.mp4'
HTML=HERE/'scoped-freeze-release-repair.motion.html'
HOLD={'ONES':1,'TWOS':2,'FOURS':4}
W,H=39,21
LINKS=[['root','chest'],['chest','neck'],['neck','head'],['chest','left_shoulder'],['left_shoulder','left_elbow'],['left_elbow','left_hand'],['chest','right_shoulder'],['right_shoulder','right_elbow'],['right_elbow','right_hand'],['root','left_hip'],['left_hip','left_knee'],['left_knee','left_foot'],['root','right_hip'],['right_hip','right_knee'],['right_knee','right_foot']]

def sha(b): return hashlib.sha256(b).hexdigest()
def bres(a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy;out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): break
        q=2*e
        if q>=dy:e+=dy;x0+=sx
        if q<=dx:e+=dx;y0+=sy
    return out
def glyph(a,b):
    dx=b[0]-a[0];dy=b[1]-a[1]
    if abs(dx)>abs(dy)*2:return '-'
    if abs(dy)>abs(dx)*2:return '|'
    return '\\' if dx*dy>0 else '/'
def render_ascii(joints,gate='OPEN'):
    j={n:tuple(v) for n,v in joints.items()};g=[[' ']*W for _ in range(H)]
    def put(x,y,ch):
        if 0<=x<W and 0<=y<H:g[y][x]=ch
    for a,b in LINKS:
        for x,y in bres(j[a],j[b])[1:-1]:
            if g[y][x]==' ':put(x,y,glyph(j[a],j[b]))
    marks={'root':'@','chest':'+','neck':':','head':'O','left_shoulder':'o','left_elbow':'o','left_hand':'A','right_shoulder':'o','right_elbow':'o','right_hand':'B','left_hip':'o','left_knee':'o','left_foot':'L','right_hip':'o','right_knee':'o','right_foot':'R'}
    for n,(x,y) in j.items():put(x,y,marks[n])
    for x in range(8,31):put(x,19,'=')
    put(12,19,'^');put(26,19,'^')
    put(j['head'][0],1,{'OPEN':'g','FREEZE_B':'F','RELEASE_B':'R'}[gate])
    bx,by=j['right_hand']
    if gate=='FREEZE_B':put(bx-1,by,'[');put(bx+1,by,']')
    if gate=='RELEASE_B':put(bx-1,by,'<');put(bx+1,by,'>')
    return '\n'.join(''.join(r).rstrip() for r in g)
def ease(t,kind):
    if kind=='EASE_IN':return t*t
    if kind=='EASE_OUT':return 1-(1-t)*(1-t)
    if kind=='SMOOTHSTEP':return t*t*(3-2*t)
    return t
def qpoint(a,b,t,bias):
    cx=(a[0]+b[0])/2+bias[0];cy=(a[1]+b[1])/2+bias[1];u=1-t
    return [round(u*u*a[0]+2*u*t*cx+t*t*b[0]),round(u*u*a[1]+2*u*t*cy+t*t*b[1])]
def interp(a,b,t,bias):
    out={}
    for n,p in a.items():
        q=b[n]
        if 'foot' in n:out[n]=list(p);continue
        mult=1.5 if 'hand' in n else 1.0 if 'elbow' in n else .45
        out[n]=qpoint(p,q,t,[bias[0]*mult,bias[1]*mult])
    return out
def bridge_allowed(k,nxt):
    # event semantics can be followed by geometry only if clock authority/gate remains identical
    if k.get('event') and k['pose_rig']['gate_state']!=nxt['pose_rig']['gate_state']:return False
    if nxt.get('event'):return False
    return True
def seq_frames(m):
    seq=[];ks=m['keys']
    for i,k in enumerate(ks):
        txt=render_ascii(k['pose_rig']['joints'],k['pose_rig']['gate_state'])
        for _ in range(HOLD[k['timing_class']]):seq.append((k['key_id'],'AUTHORED_HOLD',txt))
        nxt=ks[(i+1)%len(ks)];spec=k['bridge_to_next'];n=int(spec.get('frames',0))
        if n and bridge_allowed(k,nxt):
            for fi in range(1,n+1):
                t=ease(fi/(n+1),spec['easing']);jj=interp(k['pose_rig']['joints'],nxt['pose_rig']['joints'],t,spec['arc_bias'])
                seq.append((f"{k['key_id']}~{nxt['key_id']}:{fi}",'CONNECTIVE_ARC',render_ascii(jj,k['pose_rig']['gate_state'])))
    return seq
def contact_sheet(m):
    lines=['ASCII KINESIS V2 TIMING 006 — SCOPED FREEZE / RELEASE REPAIR',f"revises: {m['revises']}",f"negative_fixture: {m['negative_fixture']}",'SOURCE ART: NONE | SOURCE TIMING OBSERVED: NONE | AUTHORED TIMING: INFERRED','POLICY: STREET_FIGHTER/CAPCOM | ONES=1 display frame | TWOS=2 | FOURS=4 | 1s/2s/4s are classes, never seconds','']
    for k in m['keys']:
        lines += [f"[{k['key_id']}] {k['name']}",f"pose/rig={k['pose_rig']['rig_id']} | support/contact={k['support_contact']}",f"root/motion-arc={k['motion_arc_root_note']}",f"timing_class={k['timing_class']} | timing_provenance={k['timing_provenance']}",f"causal_role={k['causal_role']}",f"clocks BASE={k['clock_state']['BASE']} | A={k['clock_state']['SIGNAL_A']} | B={k['clock_state']['SIGNAL_B']} | GATE={k['clock_state']['GATE']}",render_ascii(k['pose_rig']['joints'],k['pose_rig']['gate_state']),'']
    return '\n'.join(lines).rstrip()+'\n'
def spa_projection(m):
    return {'schema':'ascii-kinesis.motion.v2-spa-view','experiment_id':m['experiment_id'],'revision':{'revises':m['revises'],'negative_fixture':m['negative_fixture'],'negative_fixture_status':m['negative_fixture_status']},'rig':m['rig_schema'],'clock_channels':m['clock_channels'],'timing_policy':m['timing_policy'],'timing_vocabulary':m['timing_vocabulary'],'keys':[{'key_id':k['key_id'],'name':k['name'],'pose_rig':{'rig_id':k['pose_rig']['rig_id'],'gate_state':k['pose_rig']['gate_state'],'ascii_authority':k['key_id']},'support_contact':k['support_contact'],'motion_arc_root_note':k['motion_arc_root_note'],'timing_class':k['timing_class'],'timing_provenance':k['timing_provenance'],'causal_role':k['causal_role'],'clock_state':k['clock_state']} for k in m['keys']],'source_rights':m['source'],'compatibility':m['compatibility'],'manifest':m['manifest'],'media':{'sha256':m['compile']['media_sha256'],'bytes':m['compile']['media_bytes'],'fps':m['compile']['fps'],'frames':m['compile']['video_frames_total'],'source':'abstract_ascii_rig_only'},'skill_mutation':m['skill_mutation'],'evaluation':m['evaluation'],'receipt_facts':m['receipt_facts']}
def frame_png(txt,path):
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',11);hdr=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',10)
    im=Image.new('RGB',(440,270),'black');dr=ImageDraw.Draw(im);dr.text((10,7),'SCOPED FREEZE / RELEASE • ABSTRACT ASCII RIG',font=hdr,fill='white');dr.multiline_text((10,26),txt,font=font,fill='white',spacing=0);im.save(path)
def make_html(m,sheet,media):
    payload=json.dumps(spa_projection(m),ensure_ascii=False,indent=2,sort_keys=True)
    tpl='''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Timing 006 — Scoped Freeze Release Repair</title><style>:root{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}body{margin:0;padding:1rem;max-width:1180px}nav{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}button[data-view]{font:inherit;padding:.55rem .9rem}section[hidden]{display:none}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}video{max-width:100%;height:auto;border:1px solid #555}.note{max-width:82ch;line-height:1.45}</style></head><body><h1>Scoped Freeze / Release — visible-performance repair</h1><p class="note">Same Robot / Nuclear Throne evidence family; abstract biped only. Deep coil, scoped B freeze, A counter-sweep, release, phase-debt whip, catch, rebound and paid restack. No source pixels.</p><nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button></nav><section id="ascii" role="tabpanel"><pre>__ASCII__</pre></section><section id="json" role="tabpanel" hidden><pre>__JSON__</pre></section><section id="video" role="tabpanel" hidden><video controls autoplay muted loop playsinline preload="metadata"><source src="data:video/mp4;base64,__VIDEO__" type="video/mp4"></video></section><script>const t=[...document.querySelectorAll('button[data-view]')],p=[...document.querySelectorAll('section[role=tabpanel]')];for(const x of t)x.addEventListener('click',()=>{for(const b of t)b.setAttribute('aria-selected',b===x?'true':'false');for(const y of p)y.hidden=y.id!==x.dataset.view;});</script></body></html>'''
    return tpl.replace('__ASCII__',html.escape(sheet)).replace('__JSON__',html.escape(payload)).replace('__VIDEO__',base64.b64encode(media).decode())
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--bootstrap',action='store_true');args=ap.parse_args();m=json.loads(MOTION.read_text())
    sheet=contact_sheet(m);CONTACT.write_text(sheet)
    seq=seq_frames(m);holds=sum(HOLD[k['timing_class']] for k in m['keys']);expected_bridges=sum(len([x for x in seq if x[1]=='CONNECTIVE_ARC']) for _ in [0])
    if holds!=m['compile']['authored_hold_frames_per_loop'] or len(seq)!=m['compile']['semantic_frames_per_loop']:
        raise SystemExit(f"frame-count mismatch holds={holds} seq={len(seq)}")
    allframes=seq*int(m['compile']['loop_repetitions'])
    if len(allframes)!=m['compile']['video_frames_total']:raise SystemExit('total frame mismatch')
    with tempfile.TemporaryDirectory(prefix='ak-t006-') as td:
        td=Path(td)
        for n,(_,_,txt) in enumerate(allframes):frame_png(txt,td/f'frame-{n:04d}.png')
        subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(m['compile']['fps']),'-i',str(td/'frame-%04d.png'),'-c:v','libx264','-preset','veryslow','-crf','29','-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)],check=True)
    media=MP4.read_bytes();mh=sha(media);ash=sha(sheet.encode());
    if args.bootstrap or m['compile']['media_sha256']=='PENDING':
        m['compile']['media_sha256']=mh;m['compile']['media_bytes']=len(media);m['ascii_sheet_sha256']=ash;MOTION.write_text(json.dumps(m,ensure_ascii=False,indent=2,sort_keys=True)+'\n');
    else:
        if mh!=m['compile']['media_sha256']:raise SystemExit(f'media hash mismatch {mh}')
        if ash!=m['ascii_sheet_sha256']:raise SystemExit(f'ascii hash mismatch {ash}')
    m=json.loads(MOTION.read_text());page=make_html(m,sheet,media);HTML.write_text(page)
    print(json.dumps({'ok':True,'media_sha256':mh,'media_bytes':len(media),'ascii_sha256':ash,'frames':len(allframes),'html_sha256':sha(page.encode()),'per_loop':len(seq),'bridges':len(seq)-holds},sort_keys=True))
if __name__=='__main__':main()
