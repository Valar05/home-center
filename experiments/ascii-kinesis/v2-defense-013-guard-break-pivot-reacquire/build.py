#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

H=Path(__file__).resolve().parent
M=H/'motion.json'
A=H/'contact-sheet.txt'
S=H/'guard-break-pivot-reacquire.motion.html'
V=H/'guard-break-pivot-reacquire.mp4'
W,HH=68,23

def J(k,m):
    return {n:tuple(xy) for n,xy in zip(m['rig']['joint_order'],k['pose_rig']['joint_xy'])}

def line(g,a,b):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<HH and g[y0][x0]==' ':
            g[y0][x0]='|' if x0==x1 else ('-' if y0==y1 else ('\\' if (x1-x0)*(y1-y0)>0 else '/'))
        if x0==x1 and y0==y1: break
        e2=2*e
        if e2>=dy:e+=dy;x0+=sx
        if e2<=dx:e+=dx;y0+=sy

def support_names(s):
    if s in {'BOTH_FEET','BOTH_FEET_REAR_BIASED','BOTH_FEET_EXIT_BIASED'}: return {'foot_l','foot_r'}
    if s=='REAR_FOOT': return {'foot_l'}
    if s=='EXIT_FOOT': return {'foot_r'}
    return set()

def topology(k):
    return tuple(k.get(x) for x in ('support_contact','contact_state','root_state','readiness','guard_authority','facing'))

def pose(k,m,meta=False):
    j=J(k,m);fy=m['rig']['floor_y'];g=[[' ']*W for _ in range(HH)]
    for x in range(2,W-2):g[fy][x]='_'
    for a,b in m['rig']['links']: line(g,j[a],j[b])
    glyph={'head':'O','neck':'+','shoulder_l':'+','shoulder_r':'+','elbow_l':'+','elbow_r':'+',
           'hand_l':'o','hand_r':'o','pelvis':'@','knee_l':'+','knee_r':'+','foot_l':'=','foot_r':'='}
    for n,c in glyph.items():
        x,y=j[n]
        if 0<=x<W and 0<=y<HH:g[y][x]=c
    if k.get('guard_authority') in {'OWNED','CARRIED'}:
        x,y=j['hand_r']
        if x+1<W:g[y][x+1]=']'
    if k.get('contact_state')=='INCOMING_RIGHT':
        for x in range(W-10,W-3):g[11][x]='<'
    elif k.get('contact_state')=='IMPACT_RIGHT':
        for x in range(W-13,W-3):g[13][x]='<'
        x,y=j['hand_r']
        if x+2<W:g[y][x+2]='X'
    s=k.get('support_contact',''); marks=[]
    if s=='REAR_FOOT':marks=[('foot_l','R')]
    elif s=='EXIT_FOOT':marks=[('foot_r','E')]
    elif s=='BOTH_FEET_REAR_BIASED':marks=[('foot_l','R'),('foot_r','f')]
    elif s=='BOTH_FEET_EXIT_BIASED':marks=[('foot_l','t'),('foot_r','E')]
    elif s=='BOTH_FEET':marks=[('foot_l','L'),('foot_r','R')]
    for n,c in marks:
        x=j[n][0]
        if fy+1<HH and 0<=x<W:g[fy+1][x]=c
    if k.get('root_state')=='PIVOTING':
        px,py=j['pelvis']
        for dx,dy,c in [(-4,-1,'('),(-5,0,'<'),(-4,1,'(')]:
            x,y=px+dx,py+dy
            if 0<=x<W and 0<=y<HH and g[y][x]==' ':g[y][x]=c
    body='\n'.join(''.join(r).rstrip() for r in g)
    if not meta:return body
    return (f"{k['key_id']}  {k['name']}  [{k['timing_class']} | {k['timing_provenance']}]\n"
            f"{body}\n"
            f"support={s} root={k['root_state']} contact={k['contact_state']} guard={k['guard_authority']} readiness={k['readiness']} facing={k['facing']}\n"
            f"role={k['causal_role']}\narc={k['motion_arc_root_note']} debt={k['recovery_debt']:.2f}")

def interp(a,b,t,m,arc):
    if topology(a)!=topology(b): raise SystemExit(f"semantic bridge forbidden: {a['key_id']} -> {b['key_id']}")
    names=m['rig']['joint_order'];aj=J(a,m);bj=J(b,m);out={};pinned=support_names(a.get('support_contact',''))
    for n in names:
        p0,p1=aj[n],bj[n]
        lag=.12 if n=='hand_r' else (.08 if n=='head' else (.05 if n=='hand_l' else 0.0))
        tt=max(0,min(1,t-lag));e=tt*tt*(3-2*tt);q=4*tt*(1-tt)
        scale=0 if n in pinned else (1 if n in ('pelvis','neck','head') else .55)
        out[n]=[round(p0[0]+(p1[0]-p0[0])*e+arc[0]*q*scale),round(p0[1]+(p1[1]-p0[1])*e+arc[1]*q*scale)]
    k={x:y for x,y in a.items() if x!='pose_rig'}
    k['pose_rig']={'joint_xy':[out[n] for n in names]}
    k['key_id']=a['key_id']+'→'+b['key_id'];k['name']='BRIDGE'
    return k

def frames(m):
    out=[];labs=[];ks=m['keys']
    for i,k in enumerate(ks):
        for _ in range(k['hold_frames']):out.append(pose(k,m));labs.append(k['key_id'])
        if i<len(ks)-1:
            n=k['bridge']['frames'];arc=k['bridge']['root_arc']
            if n and topology(k)!=topology(ks[i+1]):raise SystemExit(f"bridge crosses semantic topology: {k['key_id']} -> {ks[i+1]['key_id']}")
            for s in range(1,n+1):
                z=interp(k,ks[i+1],s/(n+1),m,arc);out.append(pose(z,m));labs.append(z['key_id'])
    return out,labs

def sheet(m):
    return (
        'ASCII KINESIS V2 DEFENSE 013 — GUARD-BREAK / PIVOT REACQUIRE\n'
        'abstract rig only — TSR M. Bison asset 5555 is evidence only; no source pixels or choreography enter output\n'
        'performance law: impact crushes guard -> rear anchor buys a pivot -> cross-body exit foot acquires root -> overshoot/counter-rotation -> late guard reopen -> displaced ready debt\n'
        'force line: RIGHT impact -> DOWN/LEFT compression -> rear-anchor pivot -> LEFT cross-body exit -> exit-foot plant -> LEFT rotational overshoot -> RIGHT counter-rotation -> guard reopen\n'
        'support legend: R=rear-foot owner, E=exit-foot owner, f/t=secondary foot, floor=_\n\n'
        + ('\n\n'+'-'*68+'\n\n').join(pose(k,m,True) for k in m['keys'])
    )

def video(m,p):
    fs,labs=frames(m);font=ImageFont.load_default(size=16);meta=ImageFont.load_default(size=14)
    with tempfile.TemporaryDirectory(prefix='d013-') as td:
        td=Path(td)
        for i,(txt,lab) in enumerate(zip(fs,labs)):
            im=Image.new('RGB',(800,450),(12,12,12));d=ImageDraw.Draw(im)
            d.text((14,8),f"{lab}   DEFENSE 013   GUARD-BREAK / PIVOT REACQUIRE",fill=(220,220,220),font=meta)
            d.multiline_text((16,42),txt,fill=(246,246,246),font=font,spacing=1)
            d.text((14,420),'RIGHT threat  |  support markers below floor  |  abstract ASCII rig only',fill=(180,180,180),font=meta)
            im.save(td/f'{i:04d}.png')
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(m['compile']['fps']),'-i',str(td/'%04d.png'),
                        '-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart','-preset','veryslow','-crf','28',str(p)],check=True)
    return len(fs)

def probe(p):
    q=json.loads(subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries',
        'stream=codec_name,width,height,r_frame_rate,nb_frames:format=duration','-of','json',str(p)],
        check=True,capture_output=True,text=True).stdout)
    s=q['streams'][0]
    return {'tool':'ffprobe','codec':s['codec_name'],'width':int(s['width']),'height':int(s['height']),
            'fps':s['r_frame_rate'],'frames':int(s['nb_frames']),'duration_seconds':float(q['format']['duration'])}

def spa(m,a,v):
    a64=base64.b64encode(gzip.compress(a.encode('utf-8'),9)).decode()
    j64=base64.b64encode(gzip.compress(M.read_bytes(),9)).decode()
    v64=base64.b64encode(v).decode()
    css='html,body{margin:0;background:#111;color:#eee;font-family:system-ui,sans-serif}header{position:sticky;top:0;background:#171717;padding:12px;border-bottom:1px solid #444}nav{display:flex;gap:8px}button{font:inherit;padding:.55rem .85rem;background:#222;color:#eee;border:1px solid #666;border-radius:6px}button[aria-selected=true]{background:#eee;color:#111}main{padding:14px}.panel{display:none}.panel.active{display:block}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;line-height:1.05}video{max-width:100%;height:auto;border:1px solid #555;background:#000}'
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Defense 013 — Guard Break Pivot Reacquire</title><style>{css}</style></head><body><header><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section class="panel active" data-panel="ascii"><pre id="a"></pre></section><section class="panel" data-panel="json"><pre id="j"></pre></section><section class="panel" data-panel="video"><video id="v" controls playsinline preload="metadata"></video></section></main><script>async function z(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([z({json.dumps(a64)}),z({json.dumps(j64)})]).then(([a,j])=>{{document.getElementById("a").textContent=a;document.getElementById("j").textContent=JSON.stringify(JSON.parse(j),null,2)}});document.getElementById("v").src="data:video/mp4;base64,"+{json.dumps(v64)};const B=[...document.querySelectorAll("button[data-view]")],P=[...document.querySelectorAll("[data-panel]")];B.forEach(b=>b.onclick=()=>{{B.forEach(x=>x.setAttribute("aria-selected",String(x===b)));P.forEach(p=>p.classList.toggle("active",p.dataset.panel===b.dataset.view))}});</script></body></html>'''

def manifest(m,pr,a):
    return {
      'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':m['experiment_id'],'lane':'defense',
      'principle':m['principle'],'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,
      'ascii_surface':'real preformatted DOM text','ligatures_disabled':True,'whitespace_preserved':True,
      'video_required':True,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'backward_compatible':True,
      'compatibility':m['compatibility'],'revision':m['revision'],'source':m['source'],'rights':m['rights'],
      'files':['build.py','contact-sheet.txt','guard-break-pivot-reacquire.motion.html','manifest.json','motion.json','receipt.md'],
      'reconstruction':'python3 build.py','video_packaging':'authoritative embedded MP4 data URI in SPA','tracked_media_sidecar':False,
      'media_sha256':m['media']['sha256'],'media_bytes':m['media']['bytes'],'media_decode_preflight':pr,
      'ascii_sha256':hashlib.sha256(a.encode()).hexdigest(),
      'motion_dungeon':{'authored_ascii_keys':len(m['keys']),'explicit_holds':True,'deterministic_connective_motion':True,
        'connector_semantics_fail_closed':True,'ascii_only_frame_render':True,'fps':m['compile']['fps'],'frames':pr['frames']},
      'timing_provenance_required':True,'quality_gates':m['quality_gates'],'contract_test':m['contract_test'],
      'correction_hooks':m['correction_hooks'],'receipt_status':'QUALITY_GATES_PASS / REPO_READBACK_REQUIRED / CHAT_DELIVERY_REQUIRED'
    }

def receipt(m,pr,a):
    times='\n'.join(f"- {k['key_id']} {k['name']} — {k['timing_class']} — {k['timing_provenance']}" for k in m['keys'])
    q=m['quality_gates']
    return f'''# ASCII Kinesis V2 Defense 013 — guard-break / pivot-reacquire receipt

Status: QUALITY_GATES_PASS / REPO_READBACK_REQUIRED / CHAT_DELIVERY_REQUIRED

## New-concept authority
Defense pre-reset repair debt 001..006 is exhausted by canonical repairs 007..012. This is exactly one post-reset new concept after Defense006 HEALTHY closure `5591342224`.
Canonical entry: `experiments/ascii-kinesis/v2-defense-013-guard-break-pivot-reacquire/`.
No predecessor is overwritten; `revises=null`, `negative_fixture=null`, `source_change=NOT_APPLICABLE_NEW_CONCEPT`.

## Source / rights
The Spriters Resource — M. Bison — *Super Street Fighter II: The New Challengers* — SNES — asset `5555` — {m['source']['page_url']}
Exact campaign evidence identity: 1175×1309 PNG; 175,378 bytes; SHA-256 `{m['source']['whole_source']['sha256']}`; single raster.
Evidence custody comes from the commissioned Home Center campaign Defense Pass 009, which records exact Home Center→primary-phone fetch and whole-sheet inspection.
Commercial source art is evidence only. No source pixels, palette, contours, layout, tracing, source choreography, redistribution, or close imitation enter output. Drew's work is not used.

## Observation / inference firewall
OBSERVED: campaign whole-sheet evidence records the labeled Blocking family, compact grounded defense contrasted with larger consequence/grounded silhouettes, and dominant-axis/support/negative-space readability.
INFERRED: the entire guard-break→rear-anchor pivot→cross-body exit→plant→overshoot→counter-rotation→late guard-reopen performance and all compile timing.
UNKNOWN: source chronology/exposure, hit-stop duration, anatomical support sequence, root/COM path, hitbox/contact rules, cancel windows, and source-authentic pivot behavior.

## Timing
Every decisive compile timing is INFERRED / STREET_FIGHTER-CAPCOM. `1s/2s/4s` means ONES/TWOS/FOURS, never seconds.
{times}

## Motion Dungeon
Authored ASCII keys -> explicit holds/timing -> topology-safe deterministic connective motion -> ASCII-only frame render -> H.264 MP4 -> exact three-tab self-contained SPA.
MP4 SHA-256 `{m['media']['sha256']}`; {m['media']['bytes']} bytes; H.264 {pr['width']}×{pr['height']} at {pr['fps']}; {pr['frames']} frames; {pr['duration_seconds']:.6f}s.
ASCII SHA-256 `{hashlib.sha256(a.encode()).hexdigest()}`.

## Current-worker quality gates
Tango iteration 1: REVISE_REQUIRED — {q['tango_iteration_1']['highest_value_visible_defect']}
Correction: {q['tango_iteration_1']['correction']}
Tango iteration 2: PASS on the actual rerender. {q['tango_iteration_2']['judgment']}
Noodle Queen: PASS only after Tango PASS on that same actual final render + full specimen. TASTE: {q['noodle_queen']['taste']} FUNCTION: {q['noodle_queen']['function']} CONTEMPT: {q['noodle_queen']['contempt']}

## Contract
Official V2 script: `tools/test_ascii_kinesis_swarm_contract_v2.py`, blob `{m['contract_test']['script_blob']}`.
Candidate-isolated exact-script run: {m['contract_test'].get('status','PENDING')}.
Repo-global full-checkout shell is not claimed by this Standard Chat construction environment.

## Pending durable acceptance legs
Exact GitHub post-write readback and issue #343 closure receipt are required after persistence.
Required reporting-chat delivery remains PART 1 complete ASCII -> PART 2 actual JSON -> PART 3 visible media.

## Correction hooks
{' / '.join(m['correction_hooks'])}
'''

def main():
    m=json.loads(M.read_text(encoding='utf-8'))
    a=sheet(m); A.write_text(a,encoding='utf-8')
    n=video(m,V);pr=probe(V)
    got=hashlib.sha256(V.read_bytes()).hexdigest()
    if got!=m['media']['sha256']:raise SystemExit(f"media hash mismatch: {got} != {m['media']['sha256']}")
    if V.stat().st_size!=m['media']['bytes']:raise SystemExit('media byte count mismatch')
    if n!=m['media']['frames']:raise SystemExit('frame count mismatch')
    S.write_text(spa(m,a,V.read_bytes()),encoding='utf-8')
    (H/'manifest.json').write_text(json.dumps(manifest(m,pr,a),ensure_ascii=False,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    (H/'receipt.md').write_text(receipt(m,pr,a),encoding='utf-8')
    print(json.dumps({'experiment_id':m['experiment_id'],'media_sha256':got,'media_bytes':V.stat().st_size,'frames':n,'ascii_sha256':hashlib.sha256(a.encode()).hexdigest()},sort_keys=True))

if __name__=='__main__':main()
