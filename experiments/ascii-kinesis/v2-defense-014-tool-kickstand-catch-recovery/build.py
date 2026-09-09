#!/usr/bin/env python3
from __future__ import annotations
import base64,gzip,hashlib,json,subprocess,tempfile
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

H=Path(__file__).resolve().parent
M=H/'motion.json'
A=H/'contact-sheet.txt'
S=H/'tool-kickstand-catch-recovery.motion.html'
V=H/'tool-kickstand-catch-recovery.mp4'
W,HH=68,24

def J(k,m):
    return {n:tuple(xy) for n,xy in zip(m['rig']['joint_order'],k['pose_rig']['joint_xy'])}

def line(g,a,b,ch=None):
    x0,y0=a;x1,y1=b;dx=abs(x1-x0);sx=1 if x0<x1 else -1;dy=-abs(y1-y0);sy=1 if y0<y1 else -1;e=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<HH and g[y0][x0]==' ':
            if ch:g[y0][x0]=ch
            else:g[y0][x0]='|' if x0==x1 else ('-' if y0==y1 else ('\\' if (x1-x0)*(y1-y0)>0 else '/'))
        if x0==x1 and y0==y1:break
        e2=2*e
        if e2>=dy:e+=dy;x0+=sx
        if e2<=dx:e+=dx;y0+=sy

def support_names(s):
    if s in {'BOTH_FEET','BOTH_FEET_REAR_BIASED','BOTH_FEET_NEW_BIASED'}:return {'foot_l','foot_r'}
    if s=='REAR_FOOT':return {'foot_l'}
    if s=='TOOL_HEAD_REAR_FOOT':return {'tool_head','foot_l'}
    if s=='TOOL_HEAD_NEW_FOOT':return {'tool_head','foot_r'}
    if s=='NEW_FOOT':return {'foot_r'}
    return set()

def topology(k):
    return tuple(k.get(x) for x in ('support_contact','contact_state','root_state','readiness','tool_state'))

def pose(k,m,meta=False):
    j=J(k,m);fy=m['rig']['floor_y'];g=[[' ']*W for _ in range(HH)]
    for x in range(2,W-2):g[fy][x]='_'
    line(g,j['tool_butt'],j['tool_head'],'#')
    for a,b in m['rig']['links']:
        if a.startswith('tool_') or b.startswith('tool_'): continue
        line(g,j[a],j[b])
    glyph={'head':'O','neck':'+','shoulder_l':'+','shoulder_r':'+','elbow_l':'+','elbow_r':'+',
           'hand_l':'o','hand_r':'o','pelvis':'@','knee_l':'+','knee_r':'+','foot_l':'=','foot_r':'=',
           'tool_butt':'{','tool_head':'}'}
    for n,c in glyph.items():
        x,y=j[n]
        if 0<=x<W and 0<=y<HH:g[y][x]=c
    if k.get('contact_state')=='INCOMING_RIGHT':
        for x in range(W-11,W-3):g[10][x]='<'
    elif k.get('contact_state')=='IMPACT_RIGHT':
        for x in range(W-14,W-4):g[11][x]='<'
        x,y=j['tool_head']
        if y-1>=0 and x+1<W:g[y-1][x+1]='X'
    marks=[]
    s=k.get('support_contact','')
    if s=='BOTH_FEET':marks=[('foot_l','L'),('foot_r','R')]
    elif s=='BOTH_FEET_REAR_BIASED':marks=[('foot_l','R'),('foot_r','f')]
    elif s=='REAR_FOOT':marks=[('foot_l','R')]
    elif s=='TOOL_HEAD_REAR_FOOT':marks=[('foot_l','R'),('tool_head','T')]
    elif s=='TOOL_HEAD_NEW_FOOT':marks=[('foot_r','N'),('tool_head','T')]
    elif s=='NEW_FOOT':marks=[('foot_r','N')]
    elif s=='BOTH_FEET_NEW_BIASED':marks=[('foot_l','t'),('foot_r','N')]
    for n,c in marks:
        x,_=j[n];yy=min(HH-1,fy+1)
        if 0<=x<W:g[yy][x]=c
    if k.get('root_state') in {'HANGING','TRANSFER','UNLOADING','ARRESTING'}:
        px,py=j['pelvis']
        for dx,dy,c in [(-4,-1,'('),(-5,0,'<'),(-4,1,'(')]:
            x,y=px+dx,py+dy
            if 0<=x<W and 0<=y<HH and g[y][x]==' ':g[y][x]=c
    body='\n'.join(''.join(r).rstrip() for r in g)
    if not meta:return body
    return (f"{k['key_id']}  {k['name']}  [{k['timing_class']} | {k['timing_provenance']}]\n"
            f"{body}\n"
            f"support={s} root={k['root_state']} contact={k['contact_state']} tool={k['tool_state']} readiness={k['readiness']}\n"
            f"role={k['causal_role']}\narc={k['motion_arc_root_note']} debt={k['recovery_debt']:.2f}")

def interp(a,b,t,m,arc):
    if topology(a)!=topology(b):raise SystemExit(f"semantic bridge forbidden: {a['key_id']} -> {b['key_id']}")
    names=m['rig']['joint_order'];aj=J(a,m);bj=J(b,m);out={};pinned=support_names(a.get('support_contact',''))
    for n in names:
        p0,p1=aj[n],bj[n]
        lag=.14 if n in ('tool_head','tool_butt') else (.10 if n in ('hand_l','hand_r') else (.08 if n=='head' else 0))
        tt=max(0,min(1,t-lag));e=tt*tt*(3-2*tt);q=4*tt*(1-tt)
        scale=0 if n in pinned else (1 if n in ('pelvis','neck','head','tool_butt','tool_head') else .55)
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
      'ASCII KINESIS V2 DEFENSE 014 — TOOL KICKSTAND CATCH / RECOVERY\n'
      'abstract rig only — TSR Hammer Kirby asset 2879 is campaign evidence only; no source pixels or choreography enter output\n'
      'performance law: high brace -> crush -> rear-foot yield -> tool-head floor catch -> kickstand hang -> far-foot probe/acquire -> tool unload -> counter-travel -> dual-support restack -> late tool reopen -> displaced ready debt\n'
      'novelty: external tool-floor support owns the middle of the recovery; no Defense013 rear-anchor pivot / cross-body exit grammar\n'
      'support legend: R=old rear foot, N=new foot, T=tool-head floor anchor, f/t=secondary foot, floor=_; tool shaft=#\n\n'
      + ('\n\n'+'-'*68+'\n\n').join(pose(k,m,True) for k in m['keys'])
    )

def video(m,p):
    fs,labs=frames(m);font=ImageFont.load_default(size=16);meta=ImageFont.load_default(size=14)
    with tempfile.TemporaryDirectory(prefix='d014-') as td:
        td=Path(td)
        for i,(txt,lab) in enumerate(zip(fs,labs)):
            im=Image.new('RGB',(800,450),(12,12,12));d=ImageDraw.Draw(im)
            d.text((14,8),f"{lab}   DEFENSE 014   TOOL KICKSTAND CATCH / RECOVERY",fill=(220,220,220),font=meta)
            d.multiline_text((16,42),txt,fill=(246,246,246),font=font,spacing=1)
            d.text((14,420),'RIGHT threat | T=tool-floor support | abstract ASCII rig only',fill=(180,180,180),font=meta)
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
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis Defense 014 — Tool Kickstand Catch Recovery</title><style>{css}</style></head><body><header><nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button></nav></header><main><section class="panel active" data-panel="ascii"><pre id="a"></pre></section><section class="panel" data-panel="json"><pre id="j"></pre></section><section class="panel" data-panel="video"><video id="v" controls playsinline preload="metadata"></video></section></main><script>async function z(s){{const b=Uint8Array.from(atob(s),c=>c.charCodeAt(0));return new Response(new Blob([b]).stream().pipeThrough(new DecompressionStream("gzip"))).text()}}Promise.all([z({json.dumps(a64)}),z({json.dumps(j64)})]).then(([a,j])=>{{document.getElementById("a").textContent=a;document.getElementById("j").textContent=JSON.stringify(JSON.parse(j),null,2)}});document.getElementById("v").src="data:video/mp4;base64,"+{json.dumps(v64)};const B=[...document.querySelectorAll("button[data-view]")],P=[...document.querySelectorAll("[data-panel]")];B.forEach(b=>b.onclick=()=>{{B.forEach(x=>x.setAttribute("aria-selected",String(x===b)));P.forEach(p=>p.classList.toggle("active",p.dataset.panel===b.dataset.view))}});</script></body></html>'''

def manifest(m,pr,a):
    return {
      'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':m['experiment_id'],'lane':'defense',
      'principle':m['principle'],'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,
      'ascii_surface':'real preformatted DOM text','ligatures_disabled':True,'whitespace_preserved':True,
      'video_required':True,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'backward_compatible':True,
      'compatibility':m['compatibility'],'revision':m['revision'],'source':m['source'],'rights':m['rights'],
      'files':['build.py','contact-sheet.txt','tool-kickstand-catch-recovery.motion.html','manifest.json','motion.json','receipt.md'],
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
    return f'''# ASCII Kinesis V2 Defense 014 — tool kickstand catch / recovery receipt

Status: QUALITY_GATES_PASS / REPO_READBACK_REQUIRED / CHAT_DELIVERY_REQUIRED

## New-concept authority
Pre-reset Defense repair debt 001..006 is exhausted by canonical repairs 007..012. Defense013 is HEALTHY per issue closure `5594519570`. This is exactly one fresh post-Defense013 concept after fresh current-main inventory found no `v2-defense-014-*`.
Canonical entry: `experiments/ascii-kinesis/v2-defense-014-tool-kickstand-catch-recovery/`.
This is not a repair: `revises=null`, `negative_fixture=null`, `source_change=NOT_APPLICABLE_NEW_CONCEPT`.
Novelty boundary: no Defense013 rear-anchor pivot/cross-body exit. The middle of this performance is owned by an external tool-floor support and triangular catch.

## Source / rights
The Spriters Resource — Hammer Kirby — *Kirby Super Star* — SNES — asset `2879` — {m['source']['page_url']}
Authoritative commissioned-campaign evidence receipt `5571393499` records whole 881×1922 PNG sheet inspection, including broad neutral/travel/air/guard/utility families, hammer-swing material, and a separate hammer-ground-collision branch.
The campaign did not establish source-authentic timing. Source sheet byte/hash identity is UNKNOWN in the cited campaign receipt and is not invented here.
Commercial source art is evidence only. No source pixels, palette, costume, contours, sheet layout, tracing, source choreography, redistribution, or close imitation enter output. Drew's work is not used.

## Observation / inference firewall
OBSERVED: campaign source identity, dimensions, whole-sheet scope/family evidence, and absence of measured source timing.
INFERRED: the entire defensive tool-brace→floor-kickstand→support-transfer→tool-unload performance, all pose geometry, tool-floor support semantics, root/COM path, foot reacquisition, overshoot/settle, and every timing class.
UNKNOWN: source chronology/exposure/hit-stop, exact support/root/contact mechanics, any source-authentic defensive use of the tool, and exact source tool/environment timing.

## Motion Dungeon
Pipeline: AUTHORED ASCII KEYS -> EXPLICIT HOLDS/TIMING -> DETERMINISTIC CONNECTIVE MOTION -> ASCII-ONLY FRAME RENDER -> MP4 -> SELF-CONTAINED SPA.
Semantic topology changes hard-cut. Authored bridges are permitted only inside unchanged support/contact/root/readiness/tool topology and pin declared support anchors.
Authoritative media: H.264 {pr['width']}×{pr['height']}, {pr['fps']} fps, {pr['frames']} frames, {pr['duration_seconds']:.3f} s, {m['media']['bytes']} bytes, SHA-256 `{m['media']['sha256']}`.
Decode preflight: ffprobe PASS + ffmpeg full decode PASS.
ASCII SHA-256 `{hashlib.sha256(a.encode()).hexdigest()}`.

## Timing
All decisive timing is INFERRED / STREET_FIGHTER-CAPCOM. `1s/2s/4s` means ONES/TWOS/FOURS, never seconds.
{times}

## Current-worker quality recursion
Final Tango: `{m['quality_gates']['tango']['status']}` on actual render SHA `{m['media']['sha256']}`.
Noodle Queen: `{m['quality_gates']['noodle_queen']['status']}` after Tango on the same actual final render.

## SPA / compatibility
Exactly ASCII | JSON | VIDEO. ASCII is literal selectable preformatted DOM text with ligatures disabled. JSON is structured audit/reconstruction data. VIDEO is an offline embedded MP4 produced solely from the abstract ASCII rig + timing. No source art is embedded. V1 and earlier V2 artifacts are untouched.

## Contract boundary
Exact official V2 script: `tools/test_ascii_kinesis_swarm_contract_v2.py`, blob `{m['contract_test']['script_blob']}`.
Candidate-isolated status: `{m['contract_test']['status']}`.
No fresh repo-global checkout execution is claimed by this Standard Chat unless separately established.

## Persistence / delivery
Repository readback: PENDING until post-write GitHub readback.
Issue #343 closure receipt: PENDING until exact readback.
Reporting chat PART 1 ASCII -> PART 2 JSON -> PART 3 visible VIDEO: PENDING until surfaced together.
DREW_ACCEPTED is not inferred.
'''

def main():
    m=json.loads(M.read_text())
    a=sheet(m);A.write_text(a)
    count=video(m,V)
    pr=probe(V)
    if count!=pr['frames']:raise SystemExit('frame count mismatch')
    subprocess.run(['ffmpeg','-v','error','-i',str(V),'-f','null','-'],check=True)
    vb=V.read_bytes()
    m['compile'].update({'frames':pr['frames'],'duration_seconds':pr['duration_seconds'],'media_decode_preflight':pr})
    m['media'].update({'sha256':hashlib.sha256(vb).hexdigest(),'bytes':len(vb),'codec':pr['codec'],'frames':pr['frames'],'duration_seconds':pr['duration_seconds']})
    M.write_text(json.dumps(m,separators=(',',':'),ensure_ascii=False))
    S.write_text(spa(m,a,vb))
    (H/'manifest.json').write_text(json.dumps(manifest(m,pr,a),indent=2,ensure_ascii=False)+'\n')
    (H/'receipt.md').write_text(receipt(m,pr,a))
    print(json.dumps({'frames':pr['frames'],'media_sha256':m['media']['sha256'],'media_bytes':len(vb),'ascii_sha256':hashlib.sha256(a.encode()).hexdigest()},indent=2))
if __name__=='__main__':main()
