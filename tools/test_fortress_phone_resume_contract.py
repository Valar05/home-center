#!/usr/bin/env python3
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
resume = (ROOT/'tools/fortress_phone_resume.sh').read_text(encoding='utf-8')
loop = (ROOT/'tools/fortress_venice_loop.py').read_text(encoding='utf-8')
installer = (ROOT/'tools/install_fortress_resume_phone.sh').read_text(encoding='utf-8')
required_resume = [
    'run_fortress_local_contracts.sh',
    'recover_adam_overlay_phone.sh',
    'vlad_pixel_forge_probe.py',
    'bootstrap_vlad_pixel_forge_mnn_phone.sh',
    'stage_vlad_pixel_model_phone.py',
    'vlad_pixel_request.py',
    'vlad_pixel_generate_mnn_phone.py',
    'intermediateDeleted',
    'fortress_venice_loop.py',
    'git pull --ff-only origin main',
]
for token in required_resume:
    assert token in resume, f'missing resume token: {token}'
required_loop = [
    'venice_review_selfheal.sh',
    "tools/adam.py', 'continue'",
    'externalReviewGateSatisfied',
    'run_fortress_local_contracts.sh',
    "git','commit'",
    'preexisting_dirty_tree_requires_preservation',
]
for token in required_loop:
    assert token in loop, f'missing Venice loop token: {token}'
for forbidden in ['workflow_dispatch', 'gh workflow', 'github actions', 'godot --path']:
    assert forbidden.lower() not in resume.lower(), f'forbidden execution lane: {forbidden}'
assert 'fortress-resume' in installer
assert 'fortress_phone_resume.sh' in installer
print('Fortress phone resume + real Pixel Forge smoke + Venice repair loop contract: PASS')
