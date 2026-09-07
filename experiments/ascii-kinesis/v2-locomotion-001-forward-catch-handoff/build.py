#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, html, json, os, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MOTION=HERE/'motion.json'
VIDEO=HERE/'motion.mp4'
SPA=HERE/'v2-locomotion-001-forward-catch-handoff.motion.html'
MANIFEST=HERE/'manifest.json'
RECEIPT=HERE/'receipt.json'
FPS=24


def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
    return h.hexdigest()

def font_path()->str:
    for p in (os.path.join(os.environ.get('PREFIX',''), 'share/fonts/TTF/DejaVuSansMono.ttf'),'/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf','/usr/share/fonts/dejavu/DejaVuSansMono.ttf','/system/fonts/DroidSansMono.ttf'):
        if Path(p).is_file(): return p
    raise SystemExit('BUILD_FAIL: DejaVuSansMono.ttf is required for deterministic ASCII rasterization')

def validate(m:dict)->None:
    if m.get('schema')!='ascii-kinesis.motion.v2': raise SystemExit('BUILD_FAIL: wrong schema')
    if not m.get('keys'): raise SystemExit('BUILD_FAIL: no keys')
    allowed={'ONES','TWOS','FOURS'}
    for k in m['keys']:
        if k.get('timing_class') not in allowed: raise SystemExit(f"BUILD_FAIL: {k.get('key_id')} timing")
        if k.get('timing_provenance') not in {'OBSERVED','INFERRED'}: raise SystemExit(f"BUILD_FAIL: {k.get('key_id')} provenance")
        if not isinstance(k.get('ascii_pose'),str) or not k['ascii_pose'].strip(): raise SystemExit(f"BUILD_FAIL: {k.get('key_id')} ASCII")
    md=m.get('motion_dungeon') or {}
    if md.get('semantic_authority')!='authored ascii_pose strings in decisive keys': raise SystemExit('BUILD_FAIL: ASCII is not semantic authority')
    if md.get('connective_motion')!='NONE_BETWEEN_CAUSAL_KEYS': raise SystemExit('BUILD_FAIL: unsupported connective semantics')
    if md.get('video_source')!='abstract_ascii_rig_only' or md.get('source_art_embedded') is not False: raise SystemExit('BUILD_FAIL: source firewall')

def contact_sheet(m:dict)->str:
    chunks=[]
    for k in m['keys']:
        chunks += [
            f"=== {k['key_id']} {k['name']} | {k['timing_class']} | {k['timing_provenance']} ===",
            f"SUPPORT: {k['support_contact']}",
            f"ROOT: {k['motion_arc_root_note']}",
            f"ROLE: {k['causal_role']}",
            k['ascii_pose'],
            ''
        ]
    chunks += [
        'LEGEND: O=head  +=pelvis/root  o=joint  *=free extremity  !=trusted support  ?=probe contact  -=ground',
        'MOTION DUNGEON: authored ASCII keys -> explicit holds -> no invented causal tween states -> ASCII-only render -> MP4'
    ]
    return '\n'.join(chunks)

def render_video(m:dict)->tuple[int,float]:
    hold={'ONES':1,'TWOS':2,'FOURS':4}
    repeats=int(m['motion_dungeon'].get('cycle_repeats',1))
    key_frames=[]
    for k in m['keys']:
        key_frames.extend([k]*hold[k['timing_class']])
    sequence=key_frames*repeats
    fp=font_path(); font=ImageFont.truetype(fp,14); meta_font=ImageFont.truetype(fp,16)
    with tempfile.TemporaryDirectory(prefix='ascii-kinesis-') as td:
        td=Path(td)
        for i,k in enumerate(sequence):
            im=Image.new('RGB',(896,432),(12,12,14)); d=ImageDraw.Draw(im)
            header=f"{m['id']}   {k['key_id']} {k['name']}   {k['timing_class']} / {k['timing_provenance']}   {k['support_contact']}"
            d.text((18,16),header,font=meta_font,fill=(238,238,238))
            d.multiline_text((18,52),k['ascii_pose'],font=font,fill=(232,232,232),spacing=1)
            d.text((18,402),"ASCII RIG ONLY · SOURCE ART NOT EMBEDDED",font=font,fill=(190,190,190))
            im.save(td/f'frame_{i:05d}.png',compress_level=9)
        cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-framerate',str(FPS),'-start_number','0','-i',str(td/'frame_%05d.png'),'-c:v','libx264','-preset','veryslow','-crf','18','-pix_fmt','yuv420p','-map_metadata','-1','-fflags','+bitexact','-flags:v','+bitexact','-movflags','+faststart',str(VIDEO)]
        subprocess.run(cmd,check=True)
    return len(sequence),len(sequence)/FPS

def write_spa(m:dict, sheet:str)->None:
    j=json.dumps(m,indent=2,ensure_ascii=False)
    b64=base64.b64encode(VIDEO.read_bytes()).decode('ascii')
    page='''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Locomotion 001 — Forward Catch Handoff</title>
<style>
:root{color-scheme:dark;background:#0c0c0e;color:#eee;font-family:system-ui,sans-serif}body{margin:0;padding:18px;max-width:1200px}h1{font-size:1.2rem;margin:.2rem 0 1rem}.tabs{display:flex;gap:8px;position:sticky;top:0;background:#0c0c0e;padding:8px 0}.tabs button{font:inherit;padding:9px 16px;border:1px solid #666;background:#18181c;color:#eee;border-radius:6px}.tabs button[aria-selected="true"]{background:#eee;color:#111}.panel{display:none}.panel.active{display:block}pre{font-family:"DejaVu Sans Mono","Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2;line-height:1.08;border:1px solid #38383d;padding:14px;border-radius:8px;background:#111114}video{width:min(100%,896px);border:1px solid #38383d;border-radius:8px;background:#000}.note{max-width:80ch;color:#bbb}
</style></head><body>
<h1>ASCII Kinesis V2 Locomotion 001 — Forward Catch Handoff</h1>
<div class="tabs" role="tablist" aria-label="Primary views">
<button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json" aria-selected="false">JSON</button><button data-view="video" aria-selected="false">VIDEO</button>
</div>
<section id="ascii" class="panel active"><p class="note">Literal authored contact sheet. Select, copy, diff, or rebuild it.</p><pre id="asciiSurface">__ASCII__</pre></section>
<section id="json" class="panel"><p class="note">Rig, decisive keys, timing provenance, rights boundary, compile facts, compatibility, and receipt inputs.</p><pre id="jsonSurface">__JSON__</pre></section>
<section id="video" class="panel"><p class="note">Compiled solely from the authored ASCII rig and structured holds. No source sprite pixels are present.</p><video controls loop muted playsinline preload="metadata"><source src="data:video/mp4;base64,__VIDEO__" type="video/mp4"></video></section>
<script>
const buttons=[...document.querySelectorAll('.tabs button')];const panels=[...document.querySelectorAll('.panel')];
for(const b of buttons)b.addEventListener('click',()=>{for(const x of buttons)x.setAttribute('aria-selected',String(x===b));for(const p of panels)p.classList.toggle('active',p.id===b.dataset.view);});
</script></body></html>'''
    page=page.replace('__ASCII__',html.escape(sheet)).replace('__JSON__',html.escape(j)).replace('__VIDEO__',b64)
    SPA.write_text(page,encoding='utf-8')

def main()->None:
    m=json.loads(MOTION.read_text(encoding='utf-8')); validate(m)
    frames,duration=render_video(m)
    per_cycle=sum({'ONES':1,'TWOS':2,'FOURS':4}[k['timing_class']] for k in m['keys'])
    m['compile_facts']={
        'status':'RENDERED','media_path':'motion.mp4','media_sha256':sha256(VIDEO),'media_bytes':VIDEO.stat().st_size,
        'frames_per_cycle':per_cycle,'cycle_repeats':int(m['motion_dungeon']['cycle_repeats']),'total_frames':frames,'nominal_fps':FPS,
        'duration_seconds':round(duration,6),'codec':'h264','pixel_format':'yuv420p','frame_source':'authored ascii_pose strings only',
        'connective_motion':'NONE_BETWEEN_CAUSAL_KEYS','source_art_embedded':False
    }
    MOTION.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    sheet=contact_sheet(m); write_spa(m,sheet)
    manifest={
        'format_version':2,'id':m['id'],'lane':'locomotion','primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,
        'video_required':True,'video_source':'abstract_ascii_rig_only','source_art_embedded':False,'backward_compatible':True,
        'motion_file':'motion.json','video_file':'motion.mp4','spa_file':SPA.name,'builder_file':'build.py','author_file':'author.py','receipt_file':'receipt.json',
        'motion_sha256':sha256(MOTION),'video_sha256':sha256(VIDEO),'spa_sha256':sha256(SPA),'source_asset_sha256':m['source']['evidence_identity']['sha256']
    }
    MANIFEST.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    receipt={
        'schema':'ascii-kinesis.v2-build-receipt','id':m['id'],'status':'RENDERED','product':'one new backward-compatible repository specimen',
        'source':{'provider':'The Spriters Resource','asset_id':32,'url':m['source']['url'],'sha256':m['source']['evidence_identity']['sha256'],'rights_note':m['source']['rights_note']},
        'timing':[{x:k[x] for x in ('key_id','name','timing_class','timing_provenance')} for k in m['keys']],
        'motion_dungeon':{'semantic_authority':'authored ASCII keys','connective_motion':'fail-closed/no invented causal states','video_source':'abstract_ascii_rig_only'},
        'media':{'path':'motion.mp4','sha256':manifest['video_sha256'],'bytes':VIDEO.stat().st_size,'frames':frames,'fps':FPS,'duration_seconds':round(duration,6)},
        'hashes':{'motion.json':manifest['motion_sha256'],SPA.name:manifest['spa_sha256'],'manifest.json':sha256(MANIFEST),'build.py':sha256(Path(__file__)),'author.py':sha256(HERE/'author.py')},
        'contract_test':{'tool':'tools/test_ascii_kinesis_swarm_contract_v2.py','status':'PENDING_REPOSITORY_EXECUTION'},
        'correction_hooks':m['correction_hooks']
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'id':m['id'],'video_sha256':manifest['video_sha256'],'frames':frames,'duration_seconds':round(duration,6),'spa_bytes':SPA.stat().st_size},sort_keys=True))

if __name__=='__main__': main()
