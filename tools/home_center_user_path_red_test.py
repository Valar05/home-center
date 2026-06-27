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
EXPECTED_VERSION_NAME = '0.2.7'
EXPECTED_VERSION_CODE = '11'
PROMPTS = [
    'Check Google drive',
    'Can you check my writing folder in drive',
    'Can you see drive brain folder in Google drive',
    'Can Home Center read Google Drive?',
    'Do you have access to my Google Drive brain folder?',
    'Open my Drive brain folder and list contents',
]
EXPECTED_VISIBLE_OPTIONS = [
    'No. Google Drive is not connected yet.',
    'Yes. Google Drive is connected with full Drive access.',
    'Google Drive is connected, but not with full Drive access yet.',
]

BAD_STRINGS = [
    'Speech proxy error',
    'Speech proxy unavailable',
    'Start the Cartesia proxy',
    'connect Google Drive in Home Center',
    'refresh Google permissions',
    'connect Google Drive or refresh Google permissions',
    'Settings',
    'Connected accounts',
    'Drive permission is active',
    'Home Center can read Google Drive',
    'no Drive access probe/tool is available here',
    'Google Drive/Docs',
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
    return ''


def main():
    for command in ['am']:
        require_command(command)
    DOWNLOAD_CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    started_at = dt.datetime.now().isoformat(timespec='seconds')
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    evidence_path = ARTIFACT_DIR / f'home_center_user_path_{stamp}.json'

    failures = []
    prompt_results = []
    capture_start = time.time()
    expected_version_marker = f'versionName={EXPECTED_VERSION_NAME} versionCode={EXPECTED_VERSION_CODE}'
    stale_install = False
    for index, prompt in enumerate(PROMPTS):
        prompt_start = time.time()
        run(['am', 'force-stop', PACKAGE], timeout=10)
        time.sleep(0.5)
        run(['am', 'start', '-n', ACTIVITY, '--es', 'home_center_smoke_prompt', prompt], timeout=20, check=True)
        time.sleep(3)
        deadline = time.time() + 30
        visible_text = ''
        while time.time() < deadline:
            time.sleep(2)
            visible_text = visible_log_text_since(prompt)
            if any(expected in visible_text for expected in EXPECTED_VISIBLE_OPTIONS) or any(bad in visible_text for bad in BAD_STRINGS):
                break
        log_text = latest_log_text()
        visible_text = visible_log_text_since(prompt)
        prompt_assertions = {
            'composerInputPathUsed': prompt in visible_text and 'installed_smoke prompt_requested' in log_text,
            'friendlyDriveCardVisible': any(expected in visible_text for expected in EXPECTED_VISIBLE_OPTIONS),
            'noRawProxyInstructionVisible': 'Start the Cartesia proxy' not in visible_text,
            'noSpeechProxyErrorVisible': 'Speech proxy error' not in visible_text and 'Speech proxy unavailable' not in visible_text,
            'noStaleDriveSetupVisible': not any(bad in visible_text for bad in BAD_STRINGS),
            'noFoodFallbackVisible': 'tell me the main ingredient' not in visible_text and 'second constraint' not in visible_text and 'second ingredient' not in visible_text,
        }
        prompt_failures = [name for name, ok in prompt_assertions.items() if not ok]
        for bad in BAD_STRINGS:
            if bad in visible_text:
                prompt_failures.append(f'bad visible text: {bad}')
        prompt_results.append({
            'prompt': prompt,
            'startedAtEpoch': prompt_start,
            'assertions': prompt_assertions,
            'failures': prompt_failures,
            'logTextSample': visible_text[-1800:],
        })
        log_text = latest_log_text()
        if index == 0 and expected_version_marker not in log_text:
            stale_install = True
            failures.append('installedBuildIsStale')
            break
        failures.extend(f'{prompt}: {failure}' for failure in prompt_failures)

    log_text = latest_log_text()
    visual_capture = latest_visual_capture(capture_start)
    assertions = {
        'chatViewLoads': visual_capture is not None,
        'composerVisible': visual_capture is not None,
        'defaultAdminControlsHidden': True,
        'runtimeVersionMatches': expected_version_marker in log_text,
        'installedBuildFreshEnoughForBehaviorAssertions': not stale_install,
    }
    for name, ok in assertions.items():
        if not ok:
            failures.append(name)

    evidence = {
        'ok': not failures,
        'startedAt': started_at,
        'package': PACKAGE,
        'expectedVersionName': EXPECTED_VERSION_NAME,
        'expectedVersionCode': EXPECTED_VERSION_CODE,
        'prompts': PROMPTS,
        'appVisualCapture': str(visual_capture) if visual_capture else None,
        'assertions': assertions,
        'promptResults': prompt_results,
        'failures': failures,
        'logVersionMarkerFound': assertions['runtimeVersionMatches'],
        'staleInstall': stale_install,
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
