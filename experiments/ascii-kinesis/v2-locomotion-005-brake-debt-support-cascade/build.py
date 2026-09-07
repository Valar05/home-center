#!/usr/bin/env python3
from __future__ import annotations
import base64
import hashlib
import gzip
import html
import json
import subprocess
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
MOTION = HERE / "motion.json"
SPA = HERE / "brake-debt-support-cascade.motion.html"
MANIFEST = HERE / "manifest.json"
RECEIPT = HERE / "receipt.json"
REBUILD = HERE / ".rebuild"
VIDEO = REBUILD / "brake-debt-support-cascade.mp4"
HOLD = {"ONES": 1, "TWOS": 2, "FOURS": 4}


def contact_sheet(motion: dict) -> str:
    blocks = []
    for key in motion["keys"]:
        blocks.append(
            f"[{key['key_id']}] {key['name']} | {key['timing_class']} | {key['timing_provenance']}\n"
            f"SUPPORT={key['support_contact']} | ROOT_OWNER={key['root_owner']} | ROOT_X={key['root_travel_units']:.1f}\n"
            f"ROLE={key['causal_role']}\n"
            f"ROOT={key['motion_arc_root_note']}\n"
            f"{key['pose_rig']}"
        )
    return "\n\n".join(blocks)


def semantic_frames(motion: dict) -> list[tuple[str, str]]:
    frames: list[tuple[str, str]] = []
    for key in motion["keys"]:
        timing = key["timing_class"]
        provenance = key["timing_provenance"]
        if timing not in HOLD:
            raise SystemExit(f"unsupported timing class: {timing}")
        if provenance not in {"OBSERVED", "INFERRED"}:
            raise SystemExit(f"unsupported timing provenance: {provenance}")
        pose = key.get("pose_rig")
        if not isinstance(pose, str) or not pose.strip():
            raise SystemExit(f"missing literal pose_rig: {key.get('key_id')}")
        frames.extend([(key["key_id"], pose)] * HOLD[timing])
    return frames


def render_mp4(motion: dict) -> bytes:
    REBUILD.mkdir(exist_ok=True)
    frames = semantic_frames(motion)
    sequence = frames * int(motion["compile"]["loop_repetitions"])
    with tempfile.TemporaryDirectory() as td_name:
        td = Path(td_name)
        font = ImageFont.load_default()
        for index, (label, pose) in enumerate(sequence):
            image = Image.new("RGB", (320, 180), "black")
            draw = ImageDraw.Draw(image)
            draw.text((6, 4), label, fill="white", font=font)
            draw.multiline_text((6, 18), pose, fill="white", font=font, spacing=0)
            image.save(td / f"{index:04d}.png", optimize=False)
        subprocess.run(
            [
                "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-framerate", str(motion["compile"]["fps"]),
                "-i", str(td / "%04d.png"),
                "-c:v", "libx264", "-preset", "veryslow", "-crf", "42",
                "-pix_fmt", "yuv420p", "-threads", "1",
                "-fflags", "+bitexact", "-flags:v", "+bitexact",
                "-metadata", "creation_time=1970-01-01T00:00:00Z",
                "-movflags", "+faststart", str(VIDEO),
            ],
            check=True,
        )
    return VIDEO.read_bytes()


def main() -> None:
    motion = json.loads(MOTION.read_text(encoding="utf-8"))
    media = render_mp4(motion)
    media_sha = hashlib.sha256(media).hexdigest()
    sheet = contact_sheet(motion)
    ascii_sha = hashlib.sha256(sheet.encode("utf-8")).hexdigest()
    per_loop = len(semantic_frames(motion))
    total = per_loop * int(motion["compile"]["loop_repetitions"])

    motion["compile"].update(
        media_sha256=media_sha,
        media_bytes=len(media),
        semantic_frames_per_loop=per_loop,
        video_frames_total=total,
    )
    motion["ascii_sheet_sha256"] = ascii_sha
    motion["receipt"].update(
        status="RENDERED_CONSTRUCTION_CHECKED_AWAITING_REPO_READBACK",
        media_sha256=media_sha,
        media_bytes=len(media),
    )
    MOTION.write_text(json.dumps(motion, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    manifest = {
        "schema": "ascii-kinesis.swarm-manifest.v2",
        "format_version": 2,
        "id": motion["id"],
        "lane": "locomotion",
        "primary_tabs": ["ASCII", "JSON", "VIDEO"],
        "ascii_literal_text": True,
        "ligatures_disabled": True,
        "whitespace_preserved": True,
        "video_required": True,
        "video_source": "abstract_ascii_rig_only",
        "source_art_embedded": False,
        "backward_compatible": True,
        "motion_json": "motion.json",
        "builder": "build.py",
        "spa": "brake-debt-support-cascade.motion.html",
        "embedded_media_authoritative": True,
        "standalone_media_tracked": False,
        "media_sha256": media_sha,
        "media_bytes": len(media),
        "source_asset_id": motion["source"]["asset_id"],
    }
    receipt = {
        "schema": "ascii-kinesis.swarm-receipt.v2",
        "experiment_id": motion["id"],
        "status": "RENDERED_CONSTRUCTION_CHECKED_AWAITING_REPO_READBACK",
        "repo_path": motion["receipt"]["repo_path"],
        "source": {"identity": motion["source"]["identity"], "url": motion["source"]["url"]},
        "rights_note": motion["source"]["rights_boundary"],
        "timing_split": {"OBSERVED": 0, "INFERRED": len(motion["keys"])},
        "per_key_timing": [
            {
                "key_id": key["key_id"],
                "timing_class": key["timing_class"],
                "timing_provenance": key["timing_provenance"],
            }
            for key in motion["keys"]
        ],
        "media_sha256": media_sha,
        "media_bytes": len(media),
        "test_boundary": "Builder and equivalent isolated structural checks may run in construction space; only exact remote repository persistence/readback can satisfy the completion gate. No full-repository runtime-suite pass is claimed by this file.",
        "correction_hooks": motion["correction_hooks"],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    audit = {"motion": motion, "manifest": manifest, "receipt": receipt}
    audit_json = json.dumps(audit, indent=2, ensure_ascii=False)
    packed_json = base64.b64encode(gzip.compress(audit_json.encode("utf-8"), 9)).decode("ascii")
    media_b64 = base64.b64encode(media).decode("ascii")
    page = f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(motion['title'])}</title><style>:root{{color-scheme:dark}}body{{margin:0;background:#101114;color:#f3f3f3;font:15px system-ui,sans-serif}}header,nav,main{{max-width:1040px;margin:auto;padding:12px}}header h1{{font-size:1.05rem;margin:.2rem 0}}nav{{display:flex;gap:8px;position:sticky;top:0;background:#101114}}button{{font:inherit;padding:.55rem .9rem}}section[hidden]{{display:none}}pre{{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;font-variant-ligatures:none;white-space:pre;overflow:auto;tab-size:2;line-height:1.05;background:#090a0c;padding:12px;border-radius:8px}}video{{display:block;max-width:100%;width:720px;background:#000;margin:auto}}.note{{opacity:.78}}</style></head><body><header><h1>{html.escape(motion['title'])}</h1><div class="note">Abstract ASCII rig only · source art not embedded · Motion Dungeon compile · embedded MP4 SHA-256 {media_sha}</div></header><nav aria-label="Primary views"><button data-view="ascii">ASCII</button><button data-view="json">JSON</button><button data-view="video">VIDEO</button></nav><main><section id="ascii"><pre id="asciiSurface">{html.escape(sheet)}</pre></section><section id="json" hidden><pre id="jsonSurface">loading…</pre></section><section id="video" hidden><video controls loop muted playsinline preload="metadata"><source src="data:video/mp4;base64,{media_b64}" type="video/mp4"></video></section></main><script>const packed='{packed_json}';async function loadJson(){{const a=Uint8Array.from(atob(packed),c=>c.charCodeAt(0));const ds=new DecompressionStream('gzip');const t=await new Response(new Blob([a]).stream().pipeThrough(ds)).text();document.getElementById('jsonSurface').textContent=t}}loadJson();for(const b of document.querySelectorAll('[data-view]'))b.addEventListener('click',()=>{{for(const s of document.querySelectorAll('main>section'))s.hidden=s.id!==b.dataset.view}});</script></body></html>'''
    SPA.write_text(page, encoding="utf-8")
    print(json.dumps({
        "ascii_sha256": ascii_sha,
        "media_sha256": media_sha,
        "media_bytes": len(media),
        "spa_bytes": len(page.encode("utf-8")),
        "semantic_frames_per_loop": per_loop,
        "video_frames_total": total,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
