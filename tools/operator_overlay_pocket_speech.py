#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from android_operator_overlay import set_pocket_speech_state, status as overlay_status

STATE_FILE = Path(os.getenv(
    'HC_POCKET_OVERLAY_SPEECH_STATE',
    os.path.expanduser('~/.local/state/home-center/pocket-overlay-speech.json'),
))
MAX_TEXT_BYTES = 8000
FORTRESS_READ = 'fortress-read'
EXPECTED_PROVIDER = 'pocket-home-center'
EXPECTED_ENGINE = 'pocket-tts-phone'
EXPECTED_TRANSPORT = 'shizuku-rish'
EXPECTED_COMPONENT = 'com.dclar.homecenter/.PocketTtsPlaybackActivity'
TERMINAL = {'COMPLETED', 'FAILED', 'MUTED'}


def _clean(value: Any) -> str:
    text = str(value or '').strip()
    return '' if text in {'NULL', 'null', '<null>'} else text


def _load_journal() -> dict[str, Any]:
    try:
        data = json.loads(STATE_FILE.read_text(encoding='utf-8'))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _atomic_write(payload: dict[str, Any]) -> None:
    """Persist local handled/request state atomically before overlay acknowledgement."""
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_FILE.with_suffix(STATE_FILE.suffix + '.tmp')
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    os.chmod(tmp, 0o600)
    os.replace(tmp, STATE_FILE)


def _journal(request_id: str, sha256: str, state: str, *, receipt: dict[str, Any] | None = None, fault: str = '') -> dict[str, Any]:
    body: dict[str, Any] = {
        'schema': 'home-center.pocket-overlay-speech-journal.v1',
        'request_id': request_id,
        'sha256': sha256,
        'status': state,
        'handled': state in TERMINAL,
        'updated_ms': int(time.time() * 1000),
        'receipt': receipt or {},
        'fault': str(fault or '')[:2000],
    }
    _atomic_write(body)
    return body


def _decode_request(snapshot: dict[str, Any]) -> tuple[str, str, str]:
    request_id = _clean(snapshot.get('pocketSpeechRequestId'))
    encoded = _clean(snapshot.get('pocketSpeechTextB64'))
    expected_sha = _clean(snapshot.get('pocketSpeechTextSha256')).lower()
    if not request_id or len(request_id) > 120:
        raise ValueError('POCKET_REQUEST_ID_INVALID')
    if len(expected_sha) != 64 or any(ch not in '0123456789abcdef' for ch in expected_sha):
        raise ValueError('POCKET_REQUEST_SHA_INVALID')
    try:
        raw = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError('POCKET_REQUEST_BASE64_INVALID') from exc
    if not raw or len(raw) > MAX_TEXT_BYTES:
        raise ValueError('POCKET_REQUEST_SIZE_INVALID')
    actual_sha = hashlib.sha256(raw).hexdigest()
    if actual_sha != expected_sha:
        raise ValueError('POCKET_REQUEST_SHA_MISMATCH')
    try:
        text = raw.decode('utf-8', errors='strict')
    except UnicodeDecodeError as exc:
        raise ValueError('POCKET_REQUEST_UTF8_INVALID') from exc
    return request_id, expected_sha, text


def _reader() -> str:
    command = shutil.which(FORTRESS_READ)
    if command:
        return command
    candidate = Path.home() / 'bin' / FORTRESS_READ
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    raise RuntimeError('FORTRESS_READ_MISSING')


def _json_receipt(stdout: str) -> dict[str, Any]:
    clean = str(stdout or '').strip()
    if not clean:
        raise RuntimeError('FORTRESS_READ_EMPTY_RECEIPT')
    try:
        value = json.loads(clean)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    for line in reversed(clean.splitlines()):
        try:
            value = json.loads(line.strip())
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    raise RuntimeError('FORTRESS_READ_RECEIPT_NOT_JSON')


def _verify_receipt(receipt: dict[str, Any]) -> None:
    required = {
        'ok': True,
        'provider': EXPECTED_PROVIDER,
        'engine': EXPECTED_ENGINE,
        'transport': EXPECTED_TRANSPORT,
        'outputComponent': EXPECTED_COMPONENT,
        'playbackVerified': True,
        'systemFallbackUsed': False,
        'cloudFallbackUsed': False,
    }
    for key, expected in required.items():
        if receipt.get(key) != expected:
            raise RuntimeError(f'POCKET_RECEIPT_IDENTITY_MISMATCH:{key}')
    if float(receipt.get('audioSeconds') or 0.0) <= 0.0:
        raise RuntimeError('POCKET_RECEIPT_ZERO_AUDIO')
    playback = receipt.get('playbackReceipts')
    if not isinstance(playback, list) or not playback:
        raise RuntimeError('POCKET_RECEIPT_MISSING_PLAYBACK_CHAIN')
    for item in playback:
        if not isinstance(item, dict):
            raise RuntimeError('POCKET_RECEIPT_PLAYBACK_ENTRY_INVALID')
        if item.get('activityLaunchAcknowledged') is not True:
            raise RuntimeError('POCKET_RECEIPT_ACTIVITY_NOT_ACKNOWLEDGED')
        if item.get('playStartObserved') is not True:
            raise RuntimeError('POCKET_RECEIPT_PLAY_START_MISSING')
        if item.get('playCompletedObserved') is not True:
            raise RuntimeError('POCKET_RECEIPT_PLAY_COMPLETE_MISSING')
        if item.get('component') != EXPECTED_COMPONENT:
            raise RuntimeError('POCKET_RECEIPT_COMPONENT_MISMATCH')


def _publish(request_id: str, sha256: str, state: str, receipt: dict[str, Any] | None = None, fault: str = '') -> dict[str, Any]:
    exact_receipt = json.dumps(receipt or {}, ensure_ascii=False, separators=(',', ':')) if receipt else ''
    return set_pocket_speech_state(request_id, sha256, state, exact_receipt, fault)


def _terminal_reconcile(journal: dict[str, Any], request_id: str, sha256: str) -> dict[str, Any]:
    state = _clean(journal.get('status')).upper()
    receipt = journal.get('receipt') if isinstance(journal.get('receipt'), dict) else {}
    fault = _clean(journal.get('fault'))
    published = _publish(request_id, sha256, state, receipt if state == 'COMPLETED' else None, fault)
    return {
        'ok': bool(published.get('ok')),
        'handled': True,
        'reconciled': True,
        'requestId': request_id,
        'status': state,
    }


def consume_pending_pocket_speech() -> dict[str, Any]:
    """Consume at most one explicit overlay Pocket request without replaying uncertain effects."""
    snapshot = overlay_status()
    if not snapshot.get('installed') or not snapshot.get('stateReadable'):
        return {'ok': True, 'handled': False, 'reason': 'overlay_unavailable'}
    if _clean(snapshot.get('pocketSpeechStatus')).upper() != 'PENDING':
        return {'ok': True, 'handled': False, 'reason': 'no_pending_request'}

    request_id = _clean(snapshot.get('pocketSpeechRequestId'))
    sha256 = _clean(snapshot.get('pocketSpeechTextSha256')).lower()
    journal = _load_journal()
    same_journal = journal.get('request_id') == request_id and journal.get('sha256') == sha256
    prior_state = _clean(journal.get('status')).upper() if same_journal else ''

    if same_journal and prior_state in TERMINAL:
        return _terminal_reconcile(journal, request_id, sha256)
    if same_journal and prior_state == 'RUNNING':
        # A previous process may have reached the physical speaker before dying.
        # Never replay that uncertain effect. Fail closed and expose the fault.
        fault = 'POCKET_EFFECT_UNCERTAIN_AFTER_RELAY_RESTART; replay suppressed'
        terminal = _journal(request_id, sha256, 'FAILED', fault=fault)
        published = _publish(request_id, sha256, 'FAILED', fault=fault)
        return {
            'ok': bool(published.get('ok')),
            'handled': True,
            'requestId': request_id,
            'status': terminal['status'],
            'fault': fault,
        }

    try:
        request_id, sha256, text = _decode_request(snapshot)
        if snapshot.get('muted') is True:
            terminal = _journal(request_id, sha256, 'MUTED', fault='MUTED_BY_OVERLAY')
            published = _publish(request_id, sha256, 'MUTED', fault='MUTED_BY_OVERLAY')
            return {
                'ok': bool(published.get('ok')),
                'handled': True,
                'requestId': request_id,
                'status': terminal['status'],
            }

        _journal(request_id, sha256, 'RUNNING')
        running = _publish(request_id, sha256, 'RUNNING')
        if not running.get('ok'):
            raise RuntimeError('OVERLAY_RUNNING_ACK_FAILED')

        proc = subprocess.run(
            [_reader()],
            input=text + '\n',
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=300,
            check=False,
            env=os.environ.copy(),
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or f'fortress-read exit {proc.returncode}')[-1800:]
            raise RuntimeError('FORTRESS_READ_FAILED:' + detail.replace('\n', ' '))
        receipt = _json_receipt(proc.stdout)
        _verify_receipt(receipt)

        # Physical playback is already complete here. Persist the terminal
        # handled identity atomically before acknowledging it to the overlay.
        terminal = _journal(request_id, sha256, 'COMPLETED', receipt=receipt)
        published = _publish(request_id, sha256, 'COMPLETED', receipt=receipt)
        return {
            'ok': bool(published.get('ok')),
            'handled': True,
            'requestId': request_id,
            'sha256': sha256,
            'status': terminal['status'],
            'provider': EXPECTED_PROVIDER,
            'engine': EXPECTED_ENGINE,
            'outputComponent': EXPECTED_COMPONENT,
            'playbackVerified': True,
            'audioSeconds': receipt.get('audioSeconds'),
        }
    except Exception as exc:
        fault = str(exc).replace('\r', ' ').replace('\n', ' ')[:1800]
        if request_id and sha256:
            terminal = _journal(request_id, sha256, 'FAILED', fault=fault)
            try:
                _publish(request_id, sha256, 'FAILED', fault=fault)
            except Exception:
                pass
            return {
                'ok': False,
                'handled': True,
                'requestId': request_id,
                'status': terminal['status'],
                'fault': fault,
            }
        return {'ok': False, 'handled': False, 'status': 'FAILED', 'fault': fault}


if __name__ == '__main__':
    print(json.dumps(consume_pending_pocket_speech(), ensure_ascii=False, sort_keys=True))
