#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations
import json, os, shutil, subprocess, time
from pathlib import Path

from android_phone_factory_tools import ARMORY, WORKSPACE, resolve_path, file_info

ROOT = Path(__file__).resolve().parent.parent
BLENDER_SCRIPT = ROOT / 'tools/fleshpunk_armory_blender.py'


def blender_path() -> str:
    explicit = os.getenv('HC_PHONE_BLENDER', '').strip()
    if explicit:
        p = Path(os.path.expanduser(explicit))
        if p.exists():
            return str(p)
    found = shutil.which('blender')
    return found or ''


def doctor() -> dict:
    blender = blender_path()
    version = ''
    if blender:
        try:
            p = subprocess.run([blender, '--version'], text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=30)
            version = (p.stdout or '').splitlines()[0][:300]
        except Exception as exc:
            version = f'ERROR: {exc}'
    return {
        'ok': bool(blender and BLENDER_SCRIPT.exists()),
        'blender': blender,
        'blenderVersion': version,
        'workerScript': str(BLENDER_SCRIPT),
        'workerScriptExists': BLENDER_SCRIPT.exists(),
        'workspace': str(WORKSPACE),
        'armoryRoot': str(ARMORY),
    }


def slice_specimen(action: dict) -> dict:
    blender = blender_path()
    if not blender:
        raise RuntimeError('Blender executable not found on phone')
    if not BLENDER_SCRIPT.exists():
        raise RuntimeError(f'Armory Blender worker missing: {BLENDER_SCRIPT}')
    source = resolve_path(action.get('source'), must_exist=True)
    specimen = ''.join(c for c in str(action.get('specimen') or '') if c.isalnum() or c in '-_').strip('-_')
    if not specimen:
        raise ValueError('specimen is required')
    out = (ARMORY / specimen / 'slice').resolve()
    out.mkdir(parents=True, exist_ok=True)
    resolution = max(128, min(int(action.get('resolution', 512)), 1024))
    views = str(action.get('views') or 'front,rear,left,right,top,bottom')
    timeout = max(120, min(int(action.get('timeoutSeconds', 1800)), 3600))
    cmd = [
        blender, '--background', '--python', str(BLENDER_SCRIPT), '--',
        '--source', str(source), '--out', str(out), '--specimen', specimen,
        '--views', views, '--resolution', str(resolution),
    ]
    started = int(time.time() * 1000)
    proc = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
    output = proc.stdout or ''
    receipt = out / 'slice_receipt.json'
    if proc.returncode != 0:
        raise RuntimeError(f'Blender Armory slice failed exit={proc.returncode}: {output[-5000:]}')
    if not receipt.exists():
        raise RuntimeError('Blender Armory slice exited 0 without slice_receipt.json')
    data = json.loads(receipt.read_text())
    return {
        'ok': True,
        'exit': proc.returncode,
        'startedAtMs': started,
        'completedAtMs': int(time.time() * 1000),
        'source': file_info(source),
        'outputRoot': str(out),
        'receiptPath': str(receipt),
        'receipt': data,
        'blenderOutputTail': output[-5000:],
    }


def execute(action: dict) -> dict:
    kind = str(action.get('action') or '')
    if kind == 'armory_doctor':
        return doctor()
    if kind == 'armory_slice':
        return slice_specimen(action)
    raise ValueError(f'unsupported armory driver action: {kind}')


if __name__ == '__main__':
    import sys
    print(json.dumps(execute(json.loads(sys.stdin.read() or '{}')), ensure_ascii=False))
