#!/usr/bin/env python3
"""Deterministic Motion Dungeon builder for ASCII Kinesis V2 Video Motion 004.

Reads only motion.json, which contains abstract authored rig/timing data.
Never reads source video, source frames, or source audio.
Builds literal ASCII contact sheet, H.264 MP4, manifest, receipt, and a
self-contained three-tab ASCII | JSON | VIDEO SPA.
"""
from __future__ import annotations
import base64, hashlib, json, math, subprocess, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOTION = ROOT / "motion.json"
W, H = 56, 22
FPS = 24
CELL_W, CELL_H = 8, 10
VIDEO_W, VIDEO_H = W * CELL_W, H * CELL_H
SPA_NAME = "cat-door-delayed-force-handoff.motion.html"
FONT = {
    'O':["01110","10001","10011","10101","11001","10001","01110"],
    '@':["01110","10001","10111","10101","10111","10000","01111"],
    'H':["10001","10001","10001","11111","10001","10001","10001"],
    'D':["11110","10001","10001","10001","10001","10001","11110"],
    '|':["00100","00100","00100","00100","00100","00100","00100"],
    '-':["00000","00000","00000","11111","00000","00000","00000"],
    '_':["00000","00000","00000","00000","00000","00000","11111"],
    '/':["00001","00010","00100","01000","10000","00000","00000"],
    '\\':["10000","01000","00100","00010","00001","00000","00000"],
    '~':["00000","01001","10110","00000","00000","00000","00000"],
    '+':["00000","00100","00100","11111","00100","00100","00000"],
    '.':["00000","00000","00000","00000","00000","00110","00110"],
    '?':["01110","10001","00010","00100","00100","00000","00100"],
    ' ':["00000"]*7,
}

def sha256_bytes(data: bytes) -> str: return hashlib.sha256(data).hexdigest()

def line(grid, a, b, glyph=None):
    x0,y0=a; x1,y1=b; tx1,ty1=x1,y1
    dx=abs(x1-x0); dy=-abs(y1-y0); sx=1 if x0<x1 else -1; sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        if 0<=x0<W and 0<=y0<H and grid[y0][x0]==' ':
            if glyph: ch=glyph
            elif x0==tx1: ch='|'
            elif y0==ty1: ch='-'
            else: ch='\\' if (tx1-x0)*(ty1-y0)>0 else '/'
            grid[y0][x0]=ch
        if x0==tx1 and y0==ty1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def pose_grid(key):
    g=[[' ']*W for _ in range(H)]
    for x in range(W): g[20][x]='_'
    j=key['joints']; head=tuple(j['head']); shoulder=tuple(j['shoulder']); root=tuple(j['root']); fp=tuple(j['front_paw']); rp=tuple(j['rear_paw']); tail=tuple(j['tail_tip'])
    line(g, head, shoulder); line(g, shoulder, root); line(g, shoulder, fp); line(g, root, rp); line(g, root, tail, '~')
    for p,ch in ((head,'O'),(root,'@'),(fp,'+'),(rp,'+')):
        x,y=p
        if 0<=x<W and 0<=y<H: g[y][x]=ch
    # Door hinge and free edge are an authored environment rig, not source pixels.
    door=key['door']; hinge=door['hinge_x']; edge=door['edge_x']; hy=door['handle_y']; htip=tuple(j['handle_tip'])
    for y in range(2,20):
        x=int(round(hinge+(edge-hinge)*(y-2)/17))
        if 0<=x<W and g[y][x]==' ': g[y][x]='|'
    if 0<=edge<W: g[2][edge]='D'
    hp=(hinge,hy)
    if 0<=hp[0]<W and 0<=hp[1]<H: g[hp[1]][hp[0]]='H'
    line(g,hp,htip,'-')
    return [''.join(r) for r in g]

def combine_contact(keys):
    panels=[]
    for key in keys:
        label=f"{key['key_id']} t={key['source_time_s']:.1f}s OBS | {key['compile_timing_class']}/{key['compile_timing_provenance']}"
        body=pose_grid(key)
        panels.append([label[:W].ljust(W)]+body+[
            f"ROLE:{key['causal_role']}"[:W].ljust(W),
            f"SUP:{key['support_state']}"[:W].ljust(W),
            f"CONTACT:{key['contact_state']}"[:W].ljust(W),
            f"FORCE:{key['force_owner']}"[:W].ljust(W),
        ])
    rows=[]
    for block in range(0,len(panels),2):
        pair=panels[block:block+2]
        while len(pair)<2: pair.append([' '*W]*len(panels[0]))
        for i in range(len(pair[0])): rows.append(pair[0][i]+'   '+pair[1][i])
        rows.append('')
    return '\n'.join(rows).rstrip()+'\n'

def interpolate(a,b,t):
    out=json.loads(json.dumps(a))
    if a.get('semantic_group') != b.get('semantic_group'): return out
    for name,pt in a['joints'].items():
        q=b['joints'][name]
        out['joints'][name]=[int(round(pt[0]+(q[0]-pt[0])*t)),int(round(pt[1]+(q[1]-pt[1])*t))]
    for field in ('hinge_x','edge_x','handle_y','handle_dx'):
        av=a['door'][field]; bv=b['door'][field]; out['door'][field]=int(round(av+(bv-av)*t))
    return out

def compile_frames(keys):
    last=max(k['compile_frame']+k['compile_hold_frames'] for k in keys); frames=[]
    for f in range(last):
        prev=max((k for k in keys if k['compile_frame']<=f),key=lambda k:k['compile_frame'])
        future=[k for k in keys if k['compile_frame']>prev['compile_frame']]
        nxt=min(future,key=lambda k:k['compile_frame']) if future else None
        if nxt and f>=prev['compile_frame']+prev['compile_hold_frames']:
            span=max(1,nxt['compile_frame']-(prev['compile_frame']+prev['compile_hold_frames']))
            t=min(1.0,max(0.0,(f-(prev['compile_frame']+prev['compile_hold_frames'])+1)/span))
            pose=interpolate(prev,nxt,t)
        else: pose=prev
        frames.append(pose_grid(pose))
    return frames

def ppm_bytes(lines):
    width,height=VIDEO_W,VIDEO_H; pix=bytearray([246,246,246])*(width*height)
    def setpx(x,y,v=18):
        if 0<=x<width and 0<=y<height:
            i=(y*width+x)*3; pix[i:i+3]=bytes((v,v,v))
    for gy,row in enumerate(lines):
        for gx,ch in enumerate(row):
            glyph=FONT.get(ch,FONT['?']); ox=gx*CELL_W+1; oy=gy*CELL_H+1
            for yy,bits in enumerate(glyph):
                for xx,bit in enumerate(bits):
                    if bit=='1': setpx(ox+xx,oy+yy)
    return f'P6\n{width} {height}\n255\n'.encode()+bytes(pix)

def render_mp4(frames,out):
    with tempfile.TemporaryDirectory() as td:
        td=Path(td)
        for i,fr in enumerate(frames): (td/f'{i:04d}.ppm').write_bytes(ppm_bytes(fr))
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',str(FPS),'-i',str(td/'%04d.ppm'),'-an','-c:v','libx264','-pix_fmt','yuv420p','-profile:v','baseline','-level','3.0','-movflags','+faststart','-map_metadata','-1',str(out)],check=True)

def esc(s): return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;')

def make_html(contact,motion,mp4):
    payload=base64.b64encode(mp4).decode('ascii'); mt=json.dumps(motion,indent=2,sort_keys=True); title=motion['title']
    return f'''<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">\n<title>{esc(title)}</title><style>\n:root{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;background:#f4f4f1;color:#151515}}body{{margin:0;min-height:100vh}}header{{padding:1rem;border-bottom:1px solid #bbb}}h1{{font-size:1rem;margin:.1rem 0}}nav{{display:flex;gap:.4rem;padding:.6rem 1rem;border-bottom:1px solid #bbb;position:sticky;top:0;background:#f4f4f1}}button{{font:inherit;padding:.45rem .8rem}}main{{padding:1rem}}section[hidden]{{display:none}}pre{{font:12px/1.1 ui-monospace,SFMono-Regular,Menlo,Consolas,"Liberation Mono",monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2}}video{{display:block;max-width:100%;height:auto;border:1px solid #999;background:#fff}}.note{{max-width:78ch;line-height:1.4}}\n</style></head><body><header><h1>{esc(title)}</h1><div class="note">ASCII Kinesis V2 · Video Motion 004 · source pixels excluded · observed timestamps + inferred compile timing</div></header>\n<nav aria-label="Primary views"><button data-view="ascii" aria-selected="true">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav>\n<main><section id="ascii"><pre>{esc(contact)}</pre></section><section id="json" hidden><pre>{esc(mt)}</pre></section><section id="video" hidden><video controls loop playsinline preload="metadata" src="data:video/mp4;base64,{payload}"></video><p class="note">Motion Dungeon compile: authored abstract ASCII rig + explicit timing only. No source frames, pixels, audio, or artwork are embedded.</p></section></main>\n<script>const buttons=[...document.querySelectorAll('[data-view]')];const sections=[...document.querySelectorAll('main>section')];buttons.forEach(b=>b.addEventListener('click',()=>{{buttons.forEach(x=>x.setAttribute('aria-selected',String(x===b)));sections.forEach(s=>s.hidden=s.id!==b.dataset.view)}}));</script></body></html>'''

def write_manifest(motion, media, contact_sha, spa_sha):
    manifest={
      'schema':'ascii-kinesis.v2.manifest','format_version':2,'experiment_id':motion['experiment_id'],'lane':'video-motion',
      'repo_path':'experiments/ascii-kinesis/v2-video-motion-004-cat-door-delayed-force-handoff/',
      'primary_tabs':['ASCII','JSON','VIDEO'],'ascii_literal_text':True,'video_required':True,'video_source':'abstract_ascii_rig_only',
      'source_art_embedded':False,'backward_compatible':True,'motion':'motion.json','contact_sheet':'contact_sheet.txt','builder':'build_motion.py',
      'video':'motion.mp4','spa':SPA_NAME,'receipt':'receipt.json','media':media,
      'source':{'title':motion['source']['title'],'author':motion['source']['author'],'license':motion['source']['license_id'],'page_url':motion['source']['page_url'],'source_sha1':motion['source']['source_sha1'],'source_sha256':motion['source']['source_sha256'],'source_pixels_embedded':False},
      'hashes':{'contact_sheet_sha256':contact_sha,'spa_sha256':spa_sha},
      'validation':{'contract_test':'tools/test_ascii_kinesis_swarm_contract_v2.py','candidate_result':'PENDING_RUN','repo_readback_result':'PENDING_ISSUE_343_RECEIPT','video_decode':'PENDING_FFPROBE'},
      'status':'BUILT_CANDIDATE'
    }
    (ROOT/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')

def write_receipt(motion, media):
    receipt={
      'schema':'ascii-kinesis.v2.receipt','experiment_id':motion['experiment_id'],'lane':'video-motion',
      'source_identity':{'title':motion['source']['title'],'author':motion['source']['author'],'license':motion['source']['license_id'],'page_url':motion['source']['page_url'],'source_sha1':motion['source']['source_sha1'],'source_sha256':motion['source']['source_sha256']},
      'evidence_split':{'observed':'source identity/hash/decode; full selected-segment ordered luma/motion-mask inspection; measured 2 fps change timing','inferred':'all exact paw/handle/support/door-angle anatomy plus PoseLab compile exposure classes','unknown':motion['evidence_boundary']['unknown']},
      'per_key_timing':[{'key_id':k['key_id'],'source_time_s':k['source_time_s'],'timing_class':k['timing_class'],'timing_provenance':k['timing_provenance'],'compile_frame':k['compile_frame'],'compile_timing_class':k['compile_timing_class'],'compile_timing_provenance':k['compile_timing_provenance']} for k in motion['keys']],
      'media':media,'repo_path':'experiments/ascii-kinesis/v2-video-motion-004-cat-door-delayed-force-handoff/','repo_commit_authority':'issue_343_receipt_after_exact_readback',
      'status':'BUILT_CANDIDATE_AWAITING_REPO_READBACK','correction_hooks':motion['correction_hooks']
    }
    (ROOT/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')

def main():
    motion=json.loads(MOTION.read_text()); keys=motion['keys']; contact=combine_contact(keys); (ROOT/'contact_sheet.txt').write_text(contact)
    frames=compile_frames(keys); render_mp4(frames,ROOT/'motion.mp4'); media_bytes=(ROOT/'motion.mp4').read_bytes(); media={'path':'motion.mp4','sha256':sha256_bytes(media_bytes),'bytes':len(media_bytes),'codec':'H.264','pixel_format':'yuv420p','width':VIDEO_W,'height':VIDEO_H,'fps':FPS,'frame_count':len(frames),'duration_s':round(len(frames)/FPS,6),'source':'abstract_ascii_rig_only','embedded_in_spa':True}
    motion['media']=media; MOTION.write_text(json.dumps(motion,indent=2,sort_keys=True)+'\n')
    html=make_html(contact,motion,media_bytes); (ROOT/SPA_NAME).write_text(html)
    write_manifest(motion,media,sha256_bytes(contact.encode()),sha256_bytes(html.encode())); write_receipt(motion,media)
    print(json.dumps({'media_sha256':media['sha256'],'media_bytes':media['bytes'],'frames':len(frames),'duration_s':media['duration_s'],'spa_sha256':sha256_bytes(html.encode()),'spa_bytes':len(html.encode()),'contact_sha256':sha256_bytes(contact.encode()),'contact_bytes':len(contact.encode())},sort_keys=True))
if __name__=='__main__': main()
