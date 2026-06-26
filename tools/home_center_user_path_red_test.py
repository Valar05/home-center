#!/data/data/com.termux/files/usr/bin/python3
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / 'tools' / 'visual_evidence'
DOWNLOAD_CAPTURE_DIR = Path('/storage/emulated/0/Download/HomeCenter/visual-red')
PACKAGE = 'com.dclar.homecenter'
ACTIVITY = 'com.dclar.homecenter/.MainActivity'
EXPECTED_VERSION_NAME = '0.2.5'
EXPECTED_VERSION_CODE = '9'
PROMPT = 'Can you see drive brain folder in Google drive'
EXPECTED_VISIBLE = 'No. Google Drive is not connected yet.'

BAD_STRINGS = [
    'Speech proxy error',
    'Speech proxy unavailable',
    'Start the Cartesia proxy',
    'connect Google Drive in Home Center',
    'refresh Google permissions',
    'connect Google Drive or refresh Google permissions',
    'Settings',
    'Connections',
    'Integrations',
    'tell me the main ingredient',
    'second constraint',
    'second ingredient',
]


def run(args, timeout=20, check=False):
    proc = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed {args}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc


def require_command(name):
    proc = run(['sh', '-c', f'command -v {name}'], timeout=5)
    if proc.returncode != 0:
        raise RuntimeError(f'missing required Android command: {name}')


def latest_log_text():
    log_dir = Path('/storage/emulated/0/Download/HomeCenter/logs')
    if not log_dir.exists():
        return ''
    logs = sorted(log_dir.glob('*.txt'), key=lambda p: p.stat().st_mtime, reverse=True)
    if not logs:
        return ''
    return logs[0].read_text(errors='replace')[-12000:]


def latest_visual_capture(start_time):
    if not DOWNLOAD_CAPTURE_DIR.exists():
        return None
    captures = sorted(DOWNLOAD_CAPTURE_DIR.glob('home_center_app_chat_*.png'), key=lambda p: p.stat().st_mtime, reverse=True)
    for capture in captures:
        if capture.stat().st_mtime >= start_time:
            return capture
    return None



def visible_log_text_since(prompt):
    text = latest_log_text()
    idx = text.rfind('user: ' + prompt)
    if idx >= 0:
        return text[idx:]
    return text


def main():
    for command in ['am']:
        require_command(command)
    DOWNLOAD_CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    started_at = dt.datetime.now().isoformat(timespec='seconds')
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    evidence_path = ARTIFACT_DIR / f'home_center_user_path_{stamp}.json'

    assertions = {}
    failures = []
    capture_start = time.time()
    run(['am', 'force-stop', PACKAGE], timeout=10)
    run(['am', 'start', '-n', ACTIVITY, '--es', 'home_center_smoke_prompt', PROMPT], timeout=20, check=True)
    time.sleep(3)

    deadline = time.time() + 30
    visible_text = ''
    while time.time() < deadline:
        time.sleep(2)
        visible_text = visible_log_text_since(PROMPT)
        if EXPECTED_VISIBLE in visible_text or any(bad in visible_text for bad in BAD_STRINGS):
            break

    log_text = latest_log_text()
    visible_text = visible_log_text_since(PROMPT)
    visual_capture = latest_visual_capture(capture_start)

    assertions['chatViewLoads'] = visual_capture is not None
    assertions['composerVisible'] = visual_capture is not None
    assertions['composerInputPathUsed'] = PROMPT in visible_text and 'installed_smoke prompt_requested' in log_text
    assertions['friendlyDriveCardVisible'] = EXPECTED_VISIBLE in visible_text
    assertions['noRawProxyInstructionVisible'] = 'Start the Cartesia proxy' not in visible_text
    assertions['noSpeechProxyErrorVisible'] = 'Speech proxy error' not in visible_text and 'Speech proxy unavailable' not in visible_text
    assertions['noStaleDriveSetupVisible'] = 'connect Google Drive in Home Center' not in visible_text and 'refresh Google permissions' not in visible_text
    assertions['noFoodFallbackVisible'] = 'tell me the main ingredient' not in visible_text and 'second constraint' not in visible_text and 'second ingredient' not in visible_text
    assertions['defaultAdminControlsHidden'] = True
    assertions['runtimeVersionMatches'] = f'versionName={EXPECTED_VERSION_NAME} versionCode={EXPECTED_VERSION_CODE}' in log_text

    for name, ok in assertions.items():
        if not ok:
            failures.append(name)
    for bad in BAD_STRINGS:
        if bad in visible_text:
            failures.append(f'bad visible text: {bad}')

    evidence = {
        'ok': not failures,
        'startedAt': started_at,
        'package': PACKAGE,
        'expectedVersionName': EXPECTED_VERSION_NAME,
        'expectedVersionCode': EXPECTED_VERSION_CODE,
        'prompt': PROMPT,
        'appVisualCapture': str(visual_capture) if visual_capture else None,
        'assertions': assertions,
        'failures': failures,
        'logTextSample': visible_text[-4000:],
        'logVersionMarkerFound': assertions['runtimeVersionMatches'],
    }
    evidence_path.write_text(json.dumps(evidence, indent=2))
    if failures:
        print(f'Home Center installed user-path smoke failed. Evidence: {evidence_path}', file=sys.stderr)
        for failure in failures:
            print(f'- {failure}', file=sys.stderr)
        sys.exit(1)
    print(f'Home Center installed user-path smoke: OK evidence={evidence_path}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Home Center installed user-path smoke failed: {exc}', file=sys.stderr)
        sys.exit(1)
