#!/usr/bin/env python3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
boot=(ROOT/'tools/bootstrap_vlad_pixel_forge_mnn_phone.sh').read_text(encoding='utf-8')
gen=(ROOT/'tools/vlad_pixel_generate_mnn_phone.py').read_text(encoding='utf-8')
resume=(ROOT/'tools/fortress_phone_resume.sh').read_text(encoding='utf-8')
collector=(ROOT/'tools/fortress_collect_phone_evidence.py').read_text(encoding='utf-8')
loop=(ROOT/'tools/fortress_venice_loop.py').read_text(encoding='utf-8')

for token in [
    'MNN_REF="${HC_MNN_REF:-3.4.1}"',
    '-DMNN_BUILD_DIFFUSION=ON',
    '-DMNN_BUILD_OPENCV=ON',
    '-DMNN_IMGCODECS=ON',
    '-DMNN_SUPPORT_TRANSFORMER_FUSE=ON',
    "status --porcelain",
    'Pillow is required',
]: assert token in boot, f'MNN bootstrap missing {token}'
for token in [
    "for backend in (3,0)",
    "MODEL_DIR),'0','0',str(backend)",
    'supports exactly 512x512',
    "float(req.get('cfg',1.0)) != 1.0",
    'intermediateDeleted',
    'vlad.pixel.generate.v3',
]: assert token in gen, f'MNN generator missing {token}'
for token in [
    'fortress_collect_phone_evidence.py',
    '--evidence-file "$EVIDENCE"',
    'stage_vlad_pixel_model_phone.py',
    'vlad_pixel_generate_mnn_phone.py',
    'git push origin HEAD:main',
]: assert token in resume, f'Fortress resume missing {token}'
for token in ['fortress.phone-evidence.v1','intermediateDeleted','mnnRef','canonicalBytes']:
    assert token in collector, f'evidence collector missing {token}'
for token in ['--evidence-file','RUNTIME EVIDENCE','repairPush','git\',\'push\',\'origin\',\'HEAD:main']:
    assert token in loop, f'Venice loop missing {token}'
for text in (boot,gen,resume,collector,loop):
    low=text.lower()
    assert 'workflow_dispatch' not in low
    assert 'gh workflow' not in low
print('Vlad Pixel Forge MNN + runtime evidence contract: PASS')
