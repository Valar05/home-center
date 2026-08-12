#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
resume = (ROOT/'tools/fortress_phone_resume.sh').read_text(encoding='utf-8')
installer = (ROOT/'tools/install_fortress_resume_phone.sh').read_text(encoding='utf-8')
required = [
    'recover_adam_overlay_phone.sh',
    'vlad_pixel_forge_probe.py',
    'bootstrap_vlad_pixel_forge_mnn_phone.sh',
    'venice_review.py',
    'externalReviewGateSatisfied',
    'git pull --ff-only origin main',
]
for token in required:
    assert token in resume, f'missing resume token: {token}'
for forbidden in ['workflow_dispatch', 'gh workflow', 'github actions', 'godot --path']:
    assert forbidden.lower() not in resume.lower(), f'forbidden execution lane: {forbidden}'
assert 'fortress-resume' in installer
assert 'fortress_phone_resume.sh' in installer
print('Fortress phone resume contract: PASS')
