#!/usr/bin/env python3
"""Deterministic integrity verifier for VideoMotion013.
The authoritative render is embedded in the single tracked SPA; source pixels/audio are never embedded.
"""
from __future__ import annotations
import base64, hashlib, json, re
from pathlib import Path
HERE=Path(__file__).resolve().parent
motion=json.loads((HERE/'motion.json').read_text())
spa=(HERE/'black-pirate-compression-release-repair.motion.html').read_text()
m=re.search(r'data:video/mp4;base64,([A-Za-z0-9+/=]+)',spa)
if not m: raise SystemExit('missing embedded mp4')
media=base64.b64decode(m.group(1),validate=True)
sha=hashlib.sha256(media).hexdigest()
assert sha==motion['media']['sha256'], (sha,motion['media']['sha256'])
assert len(media)==motion['media']['bytes']
assert motion['source']['timing_authority'] is False
assert motion['revision']['revises']==motion['revision']['negative_fixture']
print(json.dumps({'ok':True,'experiment_id':motion['experiment_id'],'video_sha256':sha,'bytes':len(media)},sort_keys=True))
