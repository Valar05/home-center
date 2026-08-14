#!/data/data/com.termux/files/usr/bin/python
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any

from android_phone_hands_bridge import run_rish

PACKAGE = 'com.homecenter.operatoroverlay'
SERVICE = PACKAGE + '/.OperatorOverlayService'
ACTIVITY = PACKAGE + '/.MainActivity'
RECEIVER = PACKAGE + '/.OverlayUpdateReceiver'
STATE_URI = 'content://com.homecenter.operatoroverlay.state/state'
ACTION_UPDATE = 'com.homecenter.operatoroverlay.UPDATE'
ACTION_HEARTBEAT = 'com.homecenter.operatoroverlay.HEARTBEAT'
ACTION_SCREEN_ACTIVITY = 'com.homecenter.operatoroverlay.SCREEN_ACTIVITY'
MAX_TEXT_CHARS = 8000
STATE_READ_ATTEMPTS = 3
STATE_READ_DELAY_SECONDS = 0.12
SCREEN_ACTIVITY_SETTLE_SECONDS = 0.24
BUILD_INSTALL_TIMEOUT_SECONDS = 1200
RECOVERY_SCRIPT = Path(__file__).resolve().with_name('recover_adam_overlay_phone.sh')
RECOVERY_RECEIPT = Path.home() / '.local/state/home-center/adam-overlay-recovery.json'


def _shell(command: str, timeout: float = 20) -> str:
    return str(run_rish(command, timeout=timeout)).strip()


def installed() -> bool:
    for attempt in range(STATE_READ_ATTEMPTS):
        out = _shell(
            f'dumpsys package {shlex.quote(PACKAGE)} 2>/dev/null '
            f'| grep -m1 {shlex.quote("Package{")} || true'
        )
        if PACKAGE in out:
            return True
        if attempt + 1 < STATE_READ_ATTEMPTS:
            time.sleep(STATE_READ_DELAY_SECONDS)
    return False


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
        'controlEnabled': integer('control_enabled', 0) != 0,
        'muted': integer('muted', 0) != 0,
        'lastHeartbeatMs': integer('last_heartbeat_ms', 0),
        'lastUpdateMs': integer('last_update_ms', 0),
        'latestSource': text('latest_source', ''),
        'screenActiveUntilMs': integer('screen_active_until_ms', 0),
        'screenYieldUntilMs': integer('screen_yield_until_ms', 0),
        'panelCollapsed': integer('panel_collapsed', 0) != 0,
        'overlayHidden': integer('overlay_hidden', 0) != 0,
    }


def _read_state() -> str:
    last_error = 'operator state provider returned no readable row'
    for attempt in range(STATE_READ_ATTEMPTS):
        try:
            raw = _shell(f'content query --uri {shlex.quote(STATE_URI)}', timeout=15)
            if 'control_enabled=' in raw and 'muted=' in raw:
                return raw
            last_error = 'operator state provider returned an incomplete row'
        except Exception as exc:
            last_error = str(exc)[:2000]
        if attempt + 1 < STATE_READ_ATTEMPTS:
            time.sleep(STATE_READ_DELAY_SECONDS)
    raise RuntimeError(last_error)


def status() -> dict[str, Any]:
    try:
        raw = _read_state()
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
        present = installed()
        return {
            'ok': False,
            'installed': present,
            'stateReadable': False,
            'controlEnabled': False,
            'muted': False,
            'screenActiveUntilMs': 0,
            'screenYieldUntilMs': 0,
            'panelCollapsed': False,
            'overlayHidden': True,
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


def screen_activity(lease_ms: int = 2500, yield_ms: int = 0) -> dict[str, Any]:
    lease = max(250, min(int(lease_ms), 15000))
    pulse = max(0, min(int(yield_ms), min(lease, 12000)))
    out = _shell(
        f'am start-foreground-service -a {shlex.quote(ACTION_SCREEN_ACTIVITY)} '
        f'-n {shlex.quote(SERVICE)} --ei leaseMs {lease} --ei yieldMs {pulse}',
        timeout=15,
    )
    time.sleep(SCREEN_ACTIVITY_SETTLE_SECONDS)
    return {
        'ok': True,
        'leaseMs': lease,
        'yieldMs': pulse,
        'output': out[-1200:],
    }


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


def build_install() -> dict[str, Any]:
    """Run the one fixed overlay recovery path; no caller-supplied command exists."""
    if not RECOVERY_SCRIPT.is_file():
        raise RuntimeError(f'operator overlay recovery script is missing: {RECOVERY_SCRIPT}')
    env = os.environ.copy()
    env['HC_FORCE_BUILD'] = '1'
    run = subprocess.run(
        ['bash', str(RECOVERY_SCRIPT)],
        cwd=str(RECOVERY_SCRIPT.parent.parent),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=BUILD_INSTALL_TIMEOUT_SECONDS,
        check=False,
    )
    output = run.stdout[-12000:]
    if run.returncode != 0:
        raise RuntimeError(f'operator overlay build/install failed ({run.returncode}): {output}')
    receipt: dict[str, Any] = {}
    if RECOVERY_RECEIPT.is_file():
        receipt = json.loads(RECOVERY_RECEIPT.read_text(encoding='utf-8'))
    if not receipt.get('ok'):
        raise RuntimeError('operator overlay recovery did not produce a successful receipt')
    return {
        'ok': True,
        'action': 'operator_overlay_build_install',
        'receipt': receipt,
        'output': output,
        'status': status(),
    }


def control_gate() -> dict[str, Any]:
    state = status()
    if not state.get('installed'):
        raise PermissionError('Home Center operator overlay is required; refusing remote phone control')
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
    if kind == 'operator_overlay_build_install':
        return build_install()
    raise ValueError(f'unsupported operator overlay action: {kind}')


if __name__ == '__main__':
    import json
    import sys
    payload = json.loads(sys.stdin.read() or '{}')
    print(json.dumps(execute(payload), ensure_ascii=False))
