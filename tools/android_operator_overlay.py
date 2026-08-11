#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import re
import shlex
from typing import Any

from android_phone_hands_bridge import run_rish

PACKAGE = 'com.homecenter.operatoroverlay'
SERVICE = PACKAGE + '/.OperatorOverlayService'
ACTIVITY = PACKAGE + '/.MainActivity'
RECEIVER = PACKAGE + '/.OverlayUpdateReceiver'
STATE_URI = 'content://com.homecenter.operatoroverlay.state/state'
ACTION_UPDATE = 'com.homecenter.operatoroverlay.UPDATE'
ACTION_HEARTBEAT = 'com.homecenter.operatoroverlay.HEARTBEAT'
MAX_TEXT_CHARS = 8000


def _shell(command: str, timeout: float = 20) -> str:
    return str(run_rish(command, timeout=timeout)).strip()


def installed() -> bool:
    # `pm path` writes its successful package path to stderr under this rish build,
    # while run_rish intentionally returns stdout only on successful commands.
    # Package listing is stable stdout and therefore safe for deterministic gating.
    out = _shell(f'pm list packages {shlex.quote(PACKAGE)} 2>/dev/null || true')
    return f'package:{PACKAGE}' in {line.strip() for line in out.splitlines()}


def _start_service() -> str:
    return _shell(
        f'am start-foreground-service -n {shlex.quote(SERVICE)} >/dev/null 2>&1 '
        f'|| am startservice -n {shlex.quote(SERVICE)} >/dev/null 2>&1 || true'
    )


def _parse_state(raw: str) -> dict[str, Any]:
    def integer(name: str, default: int = 0) -> int:
        match = re.search(rf'\b{re.escape(name)}=(-?\d+)', raw)
        return int(match.group(1)) if match else default

    def text(name: str, default: str = '') -> str:
        match = re.search(rf'\b{re.escape(name)}=([^,\n]+)', raw)
        return match.group(1).strip() if match else default

    return {
        'controlEnabled': integer('control_enabled', 1) != 0,
        'muted': integer('muted', 0) != 0,
        'lastHeartbeatMs': integer('last_heartbeat_ms', 0),
        'lastUpdateMs': integer('last_update_ms', 0),
        'latestSource': text('latest_source', ''),
    }


def status() -> dict[str, Any]:
    if not installed():
        return {
            'ok': True,
            'installed': False,
            'stateReadable': False,
            'controlEnabled': True,
            'muted': False,
            'package': PACKAGE,
        }
    try:
        raw = _shell(f'content query --uri {shlex.quote(STATE_URI)}', timeout=15)
        state = _parse_state(raw)
        return {
            'ok': True,
            'installed': True,
            'stateReadable': True,
            'package': PACKAGE,
            'raw': raw[-2000:],
            **state,
        }
    except Exception as exc:
        return {
            'ok': False,
            'installed': True,
            'stateReadable': False,
            'controlEnabled': False,
            'muted': False,
            'package': PACKAGE,
            'error': str(exc)[:2000],
        }


def start() -> dict[str, Any]:
    if not installed():
        raise RuntimeError('Home Center operator overlay APK is not installed')
    launch = _shell(f'am start -n {shlex.quote(ACTIVITY)}')
    _start_service()
    return {'ok': True, 'action': 'operator_overlay_start', 'launch': launch[-1600:], 'status': status()}


def heartbeat() -> dict[str, Any]:
    if not installed():
        return {'ok': True, 'installed': False, 'sent': False}
    _start_service()
    out = _shell(
        f'am broadcast --receiver-foreground -a {shlex.quote(ACTION_HEARTBEAT)} '
        f'-n {shlex.quote(RECEIVER)}'
    )
    return {'ok': True, 'installed': True, 'sent': True, 'output': out[-1200:]}


def update(text: str, source: str = 'ChatGPT') -> dict[str, Any]:
    if not installed():
        raise RuntimeError('Home Center operator overlay APK is not installed')
    value = str(text or '').strip()
    if not value:
        raise ValueError('operator_overlay_update requires latestText')
    value = value[:MAX_TEXT_CHARS]
    source_value = (str(source or 'ChatGPT').strip() or 'ChatGPT')[:80]
    _start_service()
    out = _shell(
        f'am broadcast --receiver-foreground -a {shlex.quote(ACTION_UPDATE)} '
        f'-n {shlex.quote(RECEIVER)} '
        f'--es latestText {shlex.quote(value)} --es source {shlex.quote(source_value)}',
        timeout=25,
    )
    return {
        'ok': True,
        'action': 'operator_overlay_update',
        'chars': len(value),
        'source': source_value,
        'output': out[-1600:],
        'status': status(),
    }


def control_gate() -> dict[str, Any]:
    state = status()
    if not state.get('installed'):
        return state
    if not state.get('stateReadable'):
        raise PermissionError('operator overlay state is unreadable; refusing remote phone control')
    if not state.get('controlEnabled'):
        raise PermissionError('Home Center control is disabled from the on-screen operator overlay')
    return state


def execute(action: dict[str, Any]) -> dict[str, Any]:
    kind = str(action.get('action') or '')
    if kind == 'operator_overlay_status':
        return status()
    if kind == 'operator_overlay_start':
        return start()
    if kind == 'operator_overlay_update':
        return update(str(action.get('latestText') or action.get('text') or ''), str(action.get('source') or 'ChatGPT'))
    raise ValueError(f'unsupported operator overlay action: {kind}')


if __name__ == '__main__':
    import json
    import sys
    payload = json.loads(sys.stdin.read() or '{}')
    print(json.dumps(execute(payload), ensure_ascii=False))
