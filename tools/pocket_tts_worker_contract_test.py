#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'tools' / 'pocket_tts_home_center_worker.py'


rejected_env = dict(os.environ)
rejected_env['HOME_CENTER_POCKET_TTS_BACKEND'] = 'cauldron'
rejected = subprocess.run(
    [sys.executable, str(WORKER), 'doctor'],
    cwd=ROOT,
    env=rejected_env,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)
assert rejected.returncode != 0, 'worker accepted the removed Cauldron backend'
assert 'local-only' in rejected.stderr, rejected.stderr


def load_worker_module():
    spec = importlib.util.spec_from_file_location('pocket_tts_home_center_worker', WORKER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


with tempfile.TemporaryDirectory(prefix='home-center-pocket-tts-publish-') as temp:
    base = Path(temp)
    source = base / 'source.wav'
    target = base / 'android-owned.wav'
    receipt = base / 'android-owned.json'
    source.write_bytes(b'new wav bytes')
    target.write_bytes(b'placeholder')
    receipt.write_text('{}', encoding='utf-8')
    target_inode = target.stat().st_ino
    receipt_inode = receipt.stat().st_ino
    worker = load_worker_module()
    for contract, profile in [("pocket-tts-render-v2", worker.VOICE_PROFILE_ID), (worker.CONTRACT_VERSION, "wrong-profile")]:
        args = type("Request", (), {"contract_version": contract, "voice_profile_id": profile})()
        try:
            worker.render_section(args)
            raise AssertionError("stale request identity accepted")
        except ValueError: pass
    worker.overwrite_file_in_place(source, target)
    worker.overwrite_json_in_place(receipt, {'status': 'accepted', 'requestId': 'test'})
    assert target.stat().st_ino == target_inode, 'WAV publication replaced the Android-owned inode'
    assert receipt.stat().st_ino == receipt_inode, 'receipt publication replaced the Android-owned inode'
    assert target.read_bytes() == b'new wav bytes'
    assert json.loads(receipt.read_text(encoding='utf-8'))['status'] == 'accepted'

with tempfile.TemporaryDirectory(prefix='home-center-pocket-tts-worker-') as temp:
    base = Path(temp)
    requests = base / 'requests'
    output = base / 'output'
    env = dict(os.environ)
    env['HOME_CENTER_POCKET_TTS_REQUESTS'] = str(requests)
    env['HOME_CENTER_POCKET_TTS_OUTPUT'] = str(output)
    process = subprocess.Popen(
        [sys.executable, str(WORKER), 'serve', '--request-dir', str(requests)],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    heartbeat = output / 'worker-heartbeat.json'
    try:
        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline and not heartbeat.exists():
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise AssertionError(f'worker exited early: {process.returncode}\n{stdout}\n{stderr}')
            time.sleep(0.1)
        assert heartbeat.exists(), 'worker did not publish heartbeat'
        first = json.loads(heartbeat.read_text(encoding='utf-8'))
        first_mtime = heartbeat.stat().st_mtime_ns
        assert first['status'] == 'running'
        assert first['pid'] == process.pid
        assert first['configuredBackend'] == 'local'
        assert first['contractVersion'] == worker.CONTRACT_VERSION
        assert first['voiceProfileId'] == worker.VOICE_PROFILE_ID
        assert first['voice'] == worker.BUILTIN_VOICE == 'vera'
        assert first['audioFilter'] == worker.VENICE_AUDIO_FILTER
        assert 'activeBackend' in first and 'lastBackendError' in first
        time.sleep(2.5)
        second = json.loads(heartbeat.read_text(encoding='utf-8'))
        assert second['updatedAtMs'] >= first['updatedAtMs']
        assert heartbeat.stat().st_mtime_ns > first_mtime, 'heartbeat did not advance while idle'
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

print('Pocket TTS worker heartbeat contract: OK')
