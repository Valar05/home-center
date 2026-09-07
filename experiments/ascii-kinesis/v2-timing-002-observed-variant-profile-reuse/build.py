#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / 'motion.json'
SLUG = 'observed-variant-profile-reuse'
MP4 = HERE / f'{SLUG}.mp4'
HTML = HERE / f'{SLUG}.motion.html'
MANIFEST = HERE / 'manifest.json'
RECEIPT = HERE / 'receipt.json'
W, H = 57, 20
HOLD = {'ONES': 1, 'TWOS': 2, 'FOURS': 4}
LINKS = [
    ('root','spine'),('spine','head'),('spine','left_hand'),('spine','right_hand'),
    ('root','left_knee'),('left_knee','left_foot'),('root','right_knee'),('right_knee','right_foot')
]


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bres(a, b):
    x0,y0=a; x1,y1=b; dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy; out=[]
    while True:
        out.append((x0,y0))
        if (x0,y0)==(x1,y1): break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy
    return out


def glyph(a, b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx)>abs(dy)*2: return '-'
    if abs(dy)>abs(dx)*2: return '|'
    return '\\' if dx*dy>0 else '/'


def orient(joints, variant):
    j={name:list(pt) for name,pt in joints.items()}
    if variant == 'LEFT':
        # Mirror generic rig around root-local vertical axis. This is a render/config transform,
        # not a second decisive key set.
        cx=j['root'][0]
        for name,(x,y) in list(j.items()): j[name]=[2*cx-x,y]
    return j


def ascii_frame(key, variant):
    j=orient(key['pose_rig']['joints'], variant)
    grid=[[' ']*W for _ in range(H)]
    def put(x,y,ch):
        if 0<=x<W and 0<=y<H: grid[y][x]=ch
    for a,b in LINKS:
        for x,y in bres(j[a],j[b])[1:-1]:
            if 0<=y<H and 0<=x<W and grid[y][x]==' ': put(x,y,glyph(j[a],j[b]))
    chars={'root':'@','spine':'+','head':'O','left_hand':'l','right_hand':'r','left_knee':'o','right_knee':'o','left_foot':'L','right_foot':'R'}
    for name,(x,y) in j.items(): put(x,y,chars.get(name,'o'))
    # Ground is abstract support reference, not source art.
    for x in range(10,47): put(x,17,'=')
    put(5,3,'<' if variant=='LEFT' else '>')
    return '\n'.join(''.join(row).rstrip() for row in grid)


def ascii_sheet(data):
    out=[
        'ASCII KINESIS V2 TIMING 002 — OBSERVED VARIANT PROFILE REUSE',
        'SOURCE ART: NOT EMBEDDED. ABSTRACT RIG ONLY.',
        'VARIANT PASSES: LEFT / RIGHT reuse the same decisive temporal keys.',
        'OBSERVED TSR PREVIEW RELATION: RUN_LEFT = RUN_RIGHT = 8 frames x 60 ms.',
        'AUTHORED 24fps CLASS COMPILATION: INFERRED; 60 ms is not silently relabeled ONES/TWOS/FOURS.',
        ''
    ]
    for key in data['keys']:
        out.extend([
            f"[{key['key_id']}] {key['name']} | pose/rig={key['pose_rig']['rig_id']} | support/contact={key['support_contact']}",
            f"root/motion-arc: {key['motion_arc_root_note']}",
            f"timing: {key['timing_class']} | timing provenance: {key['timing_provenance']}",
            f"causal role: {key['causal_role']}",
            f"clock state: GAIT={key['clock_state']['GAIT_CLOCK']} | ORIENTATION={key['clock_state']['ORIENTATION_VARIANT']}",
            ascii_frame(key, 'RIGHT'),
            ''
        ])
    out.extend([
        'VARIANT AXIS (NON-TEMPORAL KEY MULTIPLIER)',
        'LEFT  = mirror/config render of the same keys',
        'RIGHT = base/config render of the same keys',
        'No turn chronology is implied by switching presentation passes.'
    ])
    return '\n'.join(out)


def render_png(text, path, label):
    im=Image.new('RGB',(640,360),'black')
    draw=ImageDraw.Draw(im)
    try:
        font=ImageFont.truetype('DejaVuSansMono.ttf',14)
    except Exception:
        font=ImageFont.load_default()
    draw.text((12,8),label,fill='white',font=font)
    draw.multiline_text((12,34),text,fill='white',font=font,spacing=1)
    im.save(path)


def compile_video(data):
    semantic=[]
    for variant in data['compile']['variant_passes']:
        for key in data['keys']:
            frame=ascii_frame(key, variant)
            for _ in range(HOLD[key['timing_class']]):
                semantic.append((variant,key['key_id'],frame,'AUTHORED_HOLD'))
    frames=semantic*int(data['compile']['loop_repetitions'])
    with tempfile.TemporaryDirectory(prefix='akv2-timing-002-') as td:
        td=Path(td)
        for i,(variant,kid,text,kind) in enumerate(frames):
            render_png(text,td/f'frame-{i:04d}.png',f'{variant} VARIANT PASS | {kid} | {kind} | NOT A TURN TIMELINE')
        subprocess.run([
            'ffmpeg','-hide_banner','-loglevel','error','-y',
            '-framerate',str(data['compile']['fps']),'-i',str(td/'frame-%04d.png'),
            '-map_metadata','-1','-c:v','libx264','-preset','veryslow','-crf','38',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(MP4)
        ],check=True)
    return len(semantic), len(frames)


def esc(text):
    return text.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')


def make_page(data, sheet, media_b64):
    payload_obj={
        'schema':data['schema'],
        'experiment_id':data['experiment_id'],
        'rig':data['rig'],
        'keys':data['keys'],
        'clock_channels':data['clock_channels'],
        'timing_classes':data['timing_doctrine'],
        'timing_provenance':{
            'decisive_key_classes':'INFERRED',
            'source_preview_measurements':'OBSERVED_TSR_PREVIEW',
            'original_runtime_authenticity_claim':False,
        },
        'source_rights':{
            'site':data['source']['site'],
            'asset_id':data['source']['asset_id'],
            'name':data['source']['name'],
            'game':data['source']['game'],
            'platform':data['source']['platform'],
            'page_url':data['source']['page_url'],
            'sheet':data['source']['sheet'],
            'preview_timing_observations':data['source']['preview_timing_observations'],
            'timing_scope_note':data['source']['timing_scope_note'],
            'rights_note':data['source']['rights_note'],
        },
        'compatibility':data['compatibility'],
        'manifest':data['manifest'],
        'media_sha256':data['compile']['media_sha256'],
        'media_bytes':data['compile']['media_bytes'],
    }
    payload=json.dumps(payload_obj,separators=(',',':'),sort_keys=True)
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Timing 002 — Observed Variant Profile Reuse</title><style>:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}body{{margin:0;padding:1rem;max-width:1180px}}nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}button[data-view]{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}video{{max-width:100%;height:auto;border:1px solid #555}}.note{{max-width:82ch;line-height:1.45}}</style></head><body><h1>Observed Variant Profile Reuse</h1><p class="note">The copyrighted sheet is evidence only and is not embedded. The measured TSR run-left and run-right preview schedules are equal, but the shipped ONES/TWOS/FOURS schedule is an independent INFERRED compilation over an abstract biped rig. LEFT/RIGHT are presentation variants over one temporal key list.</p><nav role="tablist" aria-label="Primary views"><button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button><button type="button" role="tab" data-view="json" aria-selected="false">JSON</button><button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button></nav><section id="ascii" role="tabpanel"><pre>{esc(sheet)}</pre></section><section id="json" role="tabpanel" hidden><pre>{esc(payload)}</pre></section><section id="video" role="tabpanel" hidden><video controls loop playsinline preload="metadata"><source src="data:video/mp4;base64,{media_b64}" type="video/mp4"></video><p class="note">Real embedded MP4 compiled solely from the abstract ASCII rig, explicit ONES/TWOS/FOURS holds, and a fail-closed zero-connector policy. Variant switching is labeled as presentation rather than turn chronology.</p></section><script>const tabs=[...document.querySelectorAll('button[data-view]')],panels=[...document.querySelectorAll('section[role=tabpanel]')];for(const tab of tabs)tab.addEventListener('click',()=>{{for(const b of tabs)b.setAttribute('aria-selected',b===tab?'true':'false');for(const p of panels)p.hidden=p.id!==tab.dataset.view;}});</script></body></html>'''


def main():
    data=json.loads(MOTION.read_text(encoding='utf-8'))
    semantic_per_cycle,total_frames=compile_video(data)
    media=MP4.read_bytes(); media_hash=sha(media)
    sheet=ascii_sheet(data); sheet_hash=sha(sheet.encode('utf-8'))
    per_variant=sum(HOLD[k['timing_class']] for k in data['keys'])
    data['ascii_sheet_sha256']=sheet_hash
    data['compile'].update(
        media_sha256=media_hash,
        media_bytes=len(media),
        authored_hold_frames_per_variant=per_variant,
        semantic_frames_per_two_variant_cycle=semantic_per_cycle,
        connective_frames_per_cycle=0,
        video_frames_total=total_frames
    )
    data['manifest']={
        'schema':'ascii-kinesis.swarm-manifest.v2',
        'format_version':2,
        'status':'BUILT',
        'media_sha256':media_hash,
        'media_bytes':len(media),
        'primary_tabs':['ASCII','JSON','VIDEO'],
        'video_source':'abstract_ascii_rig_only'
    }
    MOTION.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    HTML.write_text(make_page(data,sheet,base64.b64encode(media).decode('ascii')),encoding='utf-8')
    manifest={
        'schema':'ascii-kinesis.swarm-manifest.v2','format_version':2,'experiment_id':data['experiment_id'],'lane':'timing',
        'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'ascii_surface':'real preformatted DOM text',
        'ligatures_disabled':True,'whitespace_preserved':True,'video_required':True,'video_source':'abstract_ascii_rig_only',
        'video_packaging':f'embedded MP4 data URI in {SLUG}.motion.html','media_sha256':media_hash,'media_bytes':len(media),
        'source_art_embedded':False,'backward_compatible':True,
        'motion_dungeon':{
            'authored_ascii_keys':len(data['keys']),'explicit_holds':True,'deterministic_connective_motion':True,
            'connector_semantics_fail_closed':True,'connective_frames_per_cycle':0,'ascii_only_frame_render':True,
            'fps':data['compile']['fps'],'authored_hold_frames_per_variant':per_variant,
            'semantic_frames_per_two_variant_cycle':semantic_per_cycle,'loop_repetitions':data['compile']['loop_repetitions'],
            'video_frames_total':total_frames
        },
        'source':{
            'site':data['source']['site'],'asset_id':data['source']['asset_id'],'page_url':data['source']['page_url'],
            'raw_sha256':data['source']['sheet']['raw_sha256'],'whole_sheet_inspected':True,
            'source_timing_available':True,'source_timing_scope':'measured TSR preview GIF timing; original game runtime not claimed'
        },
        'files':['build.py','manifest.json','motion.json','receipt.json',f'{SLUG}.motion.html'],
        'reconstruction':'python3 build.py','contract_test':'python3 tools/test_ascii_kinesis_swarm_contract_v2.py',
        'correction_hooks':data['correction_hooks']
    }
    MANIFEST.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    receipt={
        'schema':'ascii-kinesis.v2-receipt','experiment_id':data['experiment_id'],'status':'RENDERED_AWAITING_REPO_VERIFICATION',
        'repo_path':f"experiments/ascii-kinesis/{data['experiment_id']}/",
        'source':data['source'],'rights_note':data['source']['rights_note'],
        'observation_inference_split':{
            'OBSERVED':data['source']['observed'],
            'INFERRED':'All decisive ASCII rig geometry, semantic compression, ONES/TWOS/FOURS classes, 24 fps holds, variant presentation compilation, and causal roles.',
            'UNKNOWN':data['source']['unknown']
        },
        'key_timings':[{'key_id':k['key_id'],'name':k['name'],'timing_class':k['timing_class'],'timing_provenance':k['timing_provenance']} for k in data['keys']],
        'observed_preview_timing':data['source']['preview_timing_observations'],
        'media_sha256':media_hash,'media_bytes':len(media),'ascii_sheet_sha256':sheet_hash,
        'skill_mutation':{'performed':False,'reason':'No new reusable rule earned. Specimen concretely exercises existing PoseLab v1.3 temporal-equivalence and v1.8 orientation-space separation, with v1.1 provenance discipline.'},
        'reconstruction':'python3 build.py','contract_test':'PENDING_EXTERNAL_RUN','repo_readback':'PENDING',
        'correction_hooks':data['correction_hooks']
    }
    RECEIPT.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'media_sha256':media_hash,'media_bytes':len(media),'ascii_sheet_sha256':sheet_hash,'semantic_frames_per_two_variant_cycle':semantic_per_cycle,'video_frames_total':total_frames},sort_keys=True))

if __name__ == '__main__': main()
