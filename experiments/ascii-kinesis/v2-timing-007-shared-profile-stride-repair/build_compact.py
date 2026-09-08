#!/usr/bin/env python3
from __future__ import annotations
import base64, gzip, json
from PIL import Image, ImageDraw
import build as B

def compact_render_png(txt, path):
    font = B.get_font(5)
    im = Image.new('RGB', (320, 180), 'black')
    ImageDraw.Draw(im).multiline_text((4, 3), txt, font=font, fill='white', spacing=0)
    im.save(path)

def audit_payload(m):
    return {
        'schema': m['schema'],
        'format_version': m['format_version'],
        'experiment_id': m['experiment_id'],
        'lane': m['lane'],
        'revision': {
            'revises': m['revises'],
            'negative_fixture': m['negative_fixture'],
            'negative_fixture_status': m['negative_fixture_status'],
        },
        'timing': {
            'policy': m['timing_policy'],
            'classes': {'ONES': 1, 'TWOS': 2, 'FOURS': 4},
            'shorthand': '1s/2s/4s are timing classes, never seconds',
            'provenance': 'OBSERVED only when established; every decisive successor key is INFERRED',
        },
        'axis_partition': m['axis_partition'],
        'clock_channels': m['clock_channels'],
        'source': {
            'site': m['source']['site'],
            'asset_id': m['source']['asset_id'],
            'name': m['source']['name'],
            'game': m['source']['game'],
            'platform': m['source']['platform'],
            'page_url': m['source']['page_url'],
            'sheet': m['source']['sheet'],
            'preview_timing_observations': m['source']['preview_timing_observations'],
            'evidence_reused_from_negative_fixture': m['source']['evidence_reused_from_negative_fixture'],
            'fresh_source_selected': m['source']['fresh_source_selected'],
            'rights_note': m['source']['rights_note'],
        },
        'compatibility': m['compatibility'],
        'rig_schema': m['rig_schema'],
        'keys': m['keys'],
        'compile': m['compile'],
        'correction_hooks': m['correction_hooks'],
    }

def compact_spa(m, s, v):
    pack = lambda x: base64.b64encode(gzip.compress(x.encode('utf-8'), mtime=0)).decode('ascii')
    page = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ASCII Kinesis V2 Timing 007 Repair</title><style>:root{color-scheme:dark;background:#101010;color:#eee}body{margin:1rem;font-family:system-ui}nav{display:flex;gap:.5rem}section[hidden]{display:none}pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto}video{max-width:100%;height:auto}</style></head><body><nav><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><section id="ascii"><pre id="a"></pre></section><section id="json" hidden><pre id="j"></pre></section><section id="video" hidden><video controls autoplay muted playsinline><source src="data:video/mp4;base64,__V__" type="video/mp4"></video></section><script>const P={a:"__A__",j:"__J__"};async function u(x){const b=Uint8Array.from(atob(x),c=>c.charCodeAt(0)),d=new DecompressionStream("gzip");return new TextDecoder().decode(await new Response(new Blob([b]).stream().pipeThrough(d)).arrayBuffer())}(async()=>{a.textContent=await u(P.a);j.textContent=await u(P.j)})();const B=[...document.querySelectorAll("button[data-view]")],S=[...document.querySelectorAll("section")];B.forEach(b=>b.onclick=()=>S.forEach(s=>s.hidden=s.id!==b.dataset.view));</script></body></html>'''
    return page.replace('__V__', base64.b64encode(v).decode('ascii')).replace('__A__', pack(s)).replace('__J__', pack(json.dumps(audit_payload(m), separators=(',', ':'), ensure_ascii=False)))

B.render_png = compact_render_png
B.spa = compact_spa

if __name__ == '__main__':
    B.main()
