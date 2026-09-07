#!/usr/bin/env python3
from __future__ import annotations
import base64, hashlib, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / 'motion.json'
MANIFEST = HERE / 'manifest.json'
OUT_MP4 = HERE / 'root-clock-custody-fork.mp4'
OUT_HTML = HERE / 'root-clock-custody-fork.motion.html'
RECEIPT = HERE / 'receipt.md'
W, H = 52, 19
HOLD = {'ONES':1, 'TWOS':2, 'FOURS':4}
JOINT_LINKS = [
    ('head','shoulder_l'),('head','shoulder_r'),('shoulder_l','shoulder_r'),
    ('shoulder_l','hand_l'),('shoulder_r','hand_r'),('shoulder_l','pelvis'),
    ('shoulder_r','pelvis'),('pelvis','knee_l'),('pelvis','knee_r'),
    ('knee_l','foot_l'),('knee_r','foot_r')
]

def lerp(a,b,t):
    return [round(a[0]+(b[0]-a[0])*t), round(a[1]+(b[1]-a[1])*t)]

def bres(a,b):
    x0,y0=a; x1,y1=b
    dx=abs(x1-x0); sx=1 if x0<x1 else -1
    dy=-abs(y1-y0); sy=1 if y0<y1 else -1
    err=dx+dy; pts=[]
    while True:
        pts.append((x0,y0))
        if x0==x1 and y0==y1: break
        e=2*err
        if e>=dy: err+=dy; x0+=sx
        if e<=dx: err+=dx; y0+=sy
    return pts

def line_glyph(a,b):
    dx=b[0]-a[0]; dy=b[1]-a[1]
    if abs(dx) > abs(dy)*2: return '-'
    if abs(dy) > abs(dx)*2: return '|'
    return '\\' if dx*dy>0 else '/'

def render_ascii(key, actor_override=None, object_override=None):
    g=[[' ']*W for _ in range(H)]
    def put(x,y,ch):
        if 0<=x<W and 0<=y<H:
            g[y][x]=ch
    p={j:list(v) for j,v in key['A'].items()}
    if actor_override is not None:
        p=actor_override
    for a,b in JOINT_LINKS:
        glyph=line_glyph(p[a],p[b])
        for x,y in bres(p[a],p[b])[1:-1]:
            if g[y][x]==' ': put(x,y,glyph)
    for j,(x,y) in p.items():
        put(x,y, '@' if j=='pelvis' else ('A' if j=='head' else 'o'))
    foot = key.get('support_foot')
    if key.get('support_A')=='ALTERNATING' and foot in {'LEFT','RIGHT'}:
        j='foot_l' if foot=='LEFT' else 'foot_r'
        x,y=p[j]; put(x,y+1,'=')
    obj = key.get('object',{})
    pos = obj.get('position') if object_override is None else object_override
    if pos is not None and obj.get('state') not in {'NONE','EXITED'}:
        put(pos[0],pos[1],'*')
    for anchor in key.get('anchors',[]):
        x,y=anchor['at']; put(x,y,'x')
    for x in range(2,9): put(x,1,'>')
    if key.get('custody')=='FREE' and pos is not None:
        for x in range(max(0,pos[0]-3), pos[0]):
            put(x,2,'.')
    lines=[''.join(r).rstrip() for r in g]
    return '\n'.join(lines)

def topology(k):
    o=k.get('object',{})
    return (
        k.get('contact_state'),
        k.get('support_A'),
        k.get('root_owner'),
        k.get('custody'),
        o.get('state')
    )

def connector(a,b,t=0.5):
    actor={j:lerp(a['A'][j], b['A'][j], t) for j in a['A']}
    apos=a.get('object',{}).get('position')
    bpos=b.get('object',{}).get('position')
    obj = lerp(apos,bpos,t) if apos is not None and bpos is not None else None
    return render_ascii(a, actor_override=actor, object_override=obj)

def contact_sheet(data):
    chunks=[]
    for k in data['keys']:
        obj=k['object']['state']
        header=(
            f"[{k['key_id']}] {k['name']} | {k['timing_class']} {k['timing_provenance']} "
            f"| contact={k['contact_state']} | custody={k['custody']} | object={obj} "
            f"| support={k['support_A']}:{k['support_foot']} | root={k['root_owner']}"
        )
        chunks.append(header+'\n'+render_ascii(k))
    return '\n\n'.join(chunks)

def render_png(text: str, path: Path, label: str):
    im=Image.new('RGB',(720,406),'black')
    d=ImageDraw.Draw(im)
    font=ImageFont.load_default(size=18)
    d.text((18,12),label,fill='white',font=font)
    d.multiline_text((18,42),text,fill='white',font=font,spacing=1)
    im.save(path)

def build_video(data):
    semantic=[]
    keys=data['keys']
    for i,k in enumerate(keys):
        pose=render_ascii(k)
        for _ in range(HOLD[k['timing_class']]):
            semantic.append((k['key_id'],pose))
        if i+1 < len(keys) and topology(k)==topology(keys[i+1]):
            semantic.append((k['key_id']+'~'+keys[i+1]['key_id'], connector(k,keys[i+1])))
    sequence=semantic*int(data['compile']['loop_repetitions'])
    with tempfile.TemporaryDirectory(prefix='ascii-kinesis-v2-contact-002-') as td:
        td=Path(td)
        for n,(label,txt) in enumerate(sequence):
            render_png(txt, td/f'frame-{n:04d}.png', label)
        cmd=[
            'ffmpeg','-hide_banner','-loglevel','error','-y',
            '-framerate',str(data['compile']['fps']),
            '-i',str(td/'frame-%04d.png'),
            '-c:v','libx264','-preset','veryslow','-crf','36',
            '-pix_fmt','yuv420p','-movflags','+faststart',str(OUT_MP4)
        ]
        subprocess.run(cmd,check=True)
    return semantic

def html_escape(s):
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def build_html(data,sheet,media_b64):
    pretty=json.dumps(data,indent=2,sort_keys=True)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ASCII Kinesis V2 Contact 002 — Root Clock / Custody Fork</title>
<style>
:root{{color-scheme:dark;background:#101010;color:#eee;font-family:system-ui,sans-serif}}
body{{margin:0;padding:1rem;max-width:1100px}}
nav{{display:flex;gap:.5rem;position:sticky;top:0;background:#101010;padding:.5rem 0}}
button[data-view]{{font:inherit;padding:.55rem .9rem}}
section[hidden]{{display:none}}
pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;font-feature-settings:"liga" 0,"calt" 0;white-space:pre;overflow:auto;tab-size:2;line-height:1.05}}
video{{max-width:100%;height:auto;border:1px solid #555}}
.note{{max-width:76ch;line-height:1.45}}
</style></head><body>
<h1>Root Clock / Custody Fork</h1>
<p class="note">Copyright-safe abstract carrier + object rig. Source art is evidence only and is not embedded. Transferable rule: an object custody change can occur without handing authority over the carrier root/support clock to the object event.</p>
<nav role="tablist" aria-label="Primary views">
<button type="button" role="tab" data-view="ascii" aria-selected="true">ASCII</button>
<button type="button" role="tab" data-view="json" aria-selected="false">JSON</button>
<button type="button" role="tab" data-view="video" aria-selected="false">VIDEO</button>
</nav>
<section id="ascii" role="tabpanel"><pre>{html_escape(sheet)}</pre></section>
<section id="json" role="tabpanel" hidden><pre>{html_escape(pretty)}</pre></section>
<section id="video" role="tabpanel" hidden><video controls loop playsinline preload="metadata"><source src="data:video/mp4;base64,{media_b64}" type="video/mp4"></video><p class="note">MP4 compiled only from abstract rig coordinates, generated ASCII frames, explicit holds, and topology-safe connectors recorded in JSON.</p></section>
<script>
const tabs=[...document.querySelectorAll('button[data-view]')];
const panels=[...document.querySelectorAll('section[role=tabpanel]')];
for(const t of tabs)t.addEventListener('click',()=>{{for(const b of tabs)b.setAttribute('aria-selected',b===t?'true':'false');for(const p of panels)p.hidden=p.id!==t.dataset.view;}});
</script></body></html>'''

def build_manifest(data, semantic_count, media_sha, media_bytes):
    return {
      'schema':'ascii-kinesis.swarm-manifest.v2',
      'format_version':2,
      'experiment_id':data['experiment_id'],
      'lane':'contact',
      'primary_tabs':['ASCII','JSON','VIDEO'],
      'ascii_literal_text':True,
      'ascii_surface':'real preformatted DOM text',
      'ligatures_disabled':True,
      'whitespace_preserved':True,
      'video_required':True,
      'video_source':'abstract_ascii_rig_only',
      'video_packaging':'embedded MP4 data URI in root-clock-custody-fork.motion.html',
      'media_sha256':media_sha,
      'media_bytes':media_bytes,
      'source_art_embedded':False,
      'backward_compatible':True,
      'motion_dungeon':{
        'authored_ascii_keys':len(data['keys']),
        'explicit_holds':True,
        'deterministic_connective_motion':True,
        'connector_semantics_fail_closed':True,
        'ascii_only_frame_render':True,
        'fps':data['compile']['fps'],
        'semantic_frames_per_loop':semantic_count,
        'loop_repetitions':data['compile']['loop_repetitions'],
        'video_frames_total':semantic_count*data['compile']['loop_repetitions']
      },
      'source':{
        'site':'The Spriters Resource',
        'asset_id':data['source']['asset_id'],
        'page_url':data['source']['page_url'],
        'raw_dimensions':data['source']['raw_dimensions'],
        'raw_bytes':data['source']['raw_bytes'],
        'raw_sha256':data['source']['raw_sha256'],
        'whole_sheet_inspected':True,
        'source_timing_available':False
      },
      'files':['build.py','manifest.json','motion.json','receipt.md','root-clock-custody-fork.motion.html','root-clock-custody-fork.mp4'],
      'reconstruction':'python3 build.py',
      'correction_hooks':data['correction_hooks']
    }

def build_receipt(data, media_sha, media_bytes, semantic_count, ascii_sha):
    timing='\n'.join(f"- {k['key_id']} {k['name']} — {k['timing_class']} ({k['timing_provenance']})" for k in data['keys'])
    return f'''# ASCII Kinesis V2 Contact 002 — receipt

Status: BUILT; repository verification, media decode/readback, and issue receipt are external completion gates.

Source: The Spriters Resource, `Mario & Luigi`, *Super Mario Bros. 2 / The Lost Levels (JPN)* (NES), asset 52578.
Source page: {data['source']['page_url']}
Exact raw source identity observed through Home Center primary-phone: 584x468 PNG, 52,370 bytes, SHA-256 `{data['source']['raw_sha256']}`.

Rights boundary: copyrighted source art was used only as whole-sheet evidence. No source pixels, palette, costume/facial detail, exact silhouettes, sheet layout, tracing, redistribution, or close imitation enters the repo specimen or compiled video. Drew's work was not used.

Whole-sheet evidence: exact bytes were freshly fetched and every raster cell participated in a 12x12 non-background occupancy scan. The complete sheet visibly combines Mario/Luigi small/big movement families, jump/swim context, fireball-handling variants, separate fireball/effect frames, and explanatory annotation about throwing during movement states. The TSR asset page reports Animated GIFs (0), so no source-authentic exposure duration is claimed.

Minimal-maximal transferable principle: `OBJECT RELEASE IS ORTHOGONAL TO ROOT MOTION.` The hand-object custody constraint can acquire and release while the carrier root/support clock continues. Release forks object authority from carrier authority; it does not automatically pause, reverse, or re-parent the carrier root.

Observation/inference firewall:
- OBSERVED: source identity, complete-sheet family coexistence, movement + fireball relation, separate object/effect frames, static PNG / Animated GIFs (0), exact bytes/dimensions/hash, whole-sheet occupancy coverage.
- INFERRED: generic hand-object anchor, abstract rig geometry, custody state machine, projectile arc magnitude, recoil amount, all PoseLab timings, and topology-safe connective frames.
- UNKNOWN: source-authentic exposure/order/hit-stop, exact fireball velocity, force magnitude, hand-object distance, collision timing, and any shared center of mass. `shared_center` stays null.

Timing — all INFERRED under STREET_FIGHTER/CAPCOM; `1s/2s/4s` means ONES/TWOS/FOURS, not seconds:
{timing}

Motion Dungeon compile: authored abstract ASCII keys -> explicit holds -> one deterministic connector frame only where contact/support/root/custody/object-state topology is unchanged -> ASCII-only rendered frames -> H.264 MP4 -> embedded data URI in the three-tab SPA. Causal joins hard-cut rather than interpolate so transitions cannot invent contact ownership, support, root authority, object custody, or causal events.

Media: {media_bytes:,}-byte MP4, SHA-256 `{media_sha}`; {semantic_count} semantic frames/loop at {data['compile']['fps']} fps; {data['compile']['loop_repetitions']} loops; {semantic_count*data['compile']['loop_repetitions']} encoded frames total.
ASCII contact-sheet SHA-256: `{ascii_sha}`.

Correction hooks: {' / '.join(data['correction_hooks'])}.
'''

def main():
    data=json.loads(MOTION.read_text())
    semantic=build_video(data)
    media=OUT_MP4.read_bytes()
    media_sha=hashlib.sha256(media).hexdigest()
    data['compile']['media_sha256']=media_sha
    data['compile']['media_bytes']=len(media)
    data['compile']['semantic_frames_per_loop']=len(semantic)
    data['compile']['video_frames_total']=len(semantic)*int(data['compile']['loop_repetitions'])
    sheet=contact_sheet(data)
    ascii_sha=hashlib.sha256(sheet.encode()).hexdigest()
    data['ascii_sheet_sha256']=ascii_sha
    MOTION.write_text(json.dumps(data,indent=2,sort_keys=True)+'\n')
    MANIFEST.write_text(json.dumps(build_manifest(data,len(semantic),media_sha,len(media)),indent=2,sort_keys=True)+'\n')
    RECEIPT.write_text(build_receipt(data,media_sha,len(media),len(semantic),ascii_sha))
    OUT_HTML.write_text(build_html(data,sheet,base64.b64encode(media).decode('ascii')))
    print(json.dumps({
        'media_sha256':media_sha,'media_bytes':len(media),
        'semantic_frames_per_loop':len(semantic),
        'video_frames_total':data['compile']['video_frames_total'],
        'ascii_sheet_sha256':ascii_sha
    },sort_keys=True))

if __name__=='__main__':
    main()
