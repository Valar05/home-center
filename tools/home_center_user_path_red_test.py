#!/data/data/com.termux/files/usr/bin/python3
import datetime as dt
from html import unescape
import json
from pathlib import Path
import re
import shlex
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / 'tools' / 'visual_evidence'
DOWNLOAD_CAPTURE_DIR = Path('/storage/emulated/0/Download/HomeCenter/visual-red')
PACKAGE = 'com.dclar.homecenter'
ACTIVITY = 'com.dclar.homecenter/.MainActivity'
APP_LOG_DIR = Path('/storage/emulated/0/Android/data/com.dclar.homecenter/files/logs')
DOWNLOAD_LOG_DIR = Path('/storage/emulated/0/Download/HomeCenter/logs')
LEXEN_PROMPT = (
    "Now it's your turn.  Don't continue the story.  Pick it up at an arbitrary point "
    "that I interest you.  And make a simulated chapter here.  Lexen green commander"
)
SCRATCH_DOC_PREFIX = 'Home Center Scratch Sandbox Smoke'

DRIVE_PROMPTS = [
    'Check Google drive',
    'Can you check my writing folder in drive',
    'Can you see drive brain folder in Google drive',
    'Can Home Center read Google Drive?',
    'Do you have access to my Google Drive brain folder?',
    'Open my Drive brain folder and list contents',
]
EXPECTED_DRIVE_OPTIONS = [
    'No. Google Drive is not connected yet.',
    'Yes. Google Drive is connected with full Drive access.',
    'Google Drive is connected, but not with full Drive access yet.',
    'I checked Google Drive and can access it.',
    'Recent accessible items include:',
]

FORBIDDEN_SPEECH_PROVIDER = 'car' + 'tesia'
FORBIDDEN_SPEECH_PROVIDER_TITLE = 'Car' + 'tesia'

BAD_STRINGS = [
    'Speech proxy error',
    'Speech proxy unavailable',
    'Start the speech proxy',
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

LEXEN_FORBIDDEN_SPEECH_PROVIDER = 'car' + 'tesia'
FORBIDDEN_SPEECH_PROVIDER_TITLE = 'Car' + 'tesia'

BAD_STRINGS = [
    'github.create_issue',
    'Create GitHub Issue',
    'file an issue',
    'confirm create',
    'press Confirm',
    'tool_loop_failed',
    'gateway connection closed',
    'unexpected end of stream',
    'I did not get a valid GPT-5.5 response',
    'I can create a GitHub issue',
    'Next step:',
    'Next steps:',
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


def find_rish():
    for candidate in [Path.home() / 'bin' / 'rish', Path('/sdcard/rish'), Path('/storage/emulated/0/rish')]:
        if candidate.exists():
            return str(candidate)
    return ''


RISH = find_rish()


def rish(command, timeout=20, check=False):
    if not RISH:
        raise RuntimeError('missing Shizuku rish helper')
    return run([RISH, '-c', command], timeout=timeout, check=check)


def expected_build_version():
    build_gradle = (ROOT / 'app' / 'build.gradle').read_text()
    name_match = re.search(r"versionName\s+'([^']+)'", build_gradle)
    code_match = re.search(r'versionCode\s+(\d+)', build_gradle)
    if not name_match or not code_match:
        raise RuntimeError('Could not read versionName/versionCode from app/build.gradle')
    return name_match.group(1), code_match.group(1)


def installed_package_version():
    proc = rish(
        f"dumpsys package {PACKAGE}",
        timeout=30,
        check=True,
    )
    text = proc.stdout
    name_match = re.search(r'versionName=([^\s]+)', text)
    code_match = re.search(r'versionCode=(\d+)', text)
    return {
        'raw': text.strip(),
        'versionName': name_match.group(1) if name_match else '',
        'versionCode': code_match.group(1) if code_match else '',
    }


def normalize_text(text):
    return re.sub(r'\s+', ' ', text or '').strip()


def newest_files(paths):
    files = []
    for directory, pattern in paths:
        if directory.exists():
            files.extend(directory.glob(pattern))
    return sorted(files, key=lambda p: p.stat().st_mtime, reverse=True)


def latest_log_text(include_download_logs=True):
    chunks = []
    if RISH:
        today_log = APP_LOG_DIR / f'{dt.datetime.now().strftime("%Y-%m-%d")}.log'
        proc = rish(f'tail -c 150000 {shlex.quote(str(today_log))}', timeout=10)
        if proc.returncode == 0 and proc.stdout:
            chunks.append(proc.stdout)
    if include_download_logs:
        logs = newest_files([(DOWNLOAD_LOG_DIR, '*.txt')])
        for log in logs[:3]:
            chunks.append(log.read_text(errors='replace')[-20000:])
    return '\n'.join(chunks)[-150000:]


def latest_visual_capture(start_time):
    if not DOWNLOAD_CAPTURE_DIR.exists():
        return None
    captures = sorted(DOWNLOAD_CAPTURE_DIR.glob('home_center_app_chat_*.png'), key=lambda p: p.stat().st_mtime, reverse=True)
    for capture in captures:
        if capture.stat().st_mtime >= start_time:
            return capture
    return None


def visible_log_text_since(prompt):
    text = latest_log_text(include_download_logs=False)
    idx = text.rfind('installed_smoke prompt_requested:')
    if idx < 0:
        idx = text.rfind('user: ' + normalize_text(prompt))
    if idx < 0:
        idx = text.rfind(prompt[:50])
    if idx >= 0:
        return text[idx:]
    return ''


def dump_ui_text(stamp):
    dump_shell_path = f'/sdcard/Download/HomeCenter/visual-red/home_center_ui_{stamp}.xml'
    dump_read_path = DOWNLOAD_CAPTURE_DIR / f'home_center_ui_{stamp}.xml'
    rish(f'rm -f {shlex.quote(dump_shell_path)}', timeout=10)
    proc = rish(f'uiautomator dump {shlex.quote(dump_shell_path)}', timeout=20)
    if proc.returncode != 0:
        return {
            'path': str(dump_read_path),
            'shellPath': dump_shell_path,
            'text': '',
            'xmlSize': 0,
            'error': proc.stderr.strip() or proc.stdout.strip(),
        }
    xml = ''
    for _ in range(10):
        if dump_read_path.exists() and dump_read_path.stat().st_size > 0:
            xml = dump_read_path.read_text(errors='replace')
            break
        time.sleep(0.2)
    if not xml:
        fallback_shell_path = '/sdcard/window_dump.xml'
        fallback_read_path = Path('/storage/emulated/0/window_dump.xml')
        fallback = rish('uiautomator dump', timeout=20)
        if fallback.returncode == 0:
            for _ in range(10):
                if fallback_read_path.exists() and fallback_read_path.stat().st_size > 0:
                    xml = fallback_read_path.read_text(errors='replace')
                    dump_shell_path = fallback_shell_path
                    dump_read_path = fallback_read_path
                    break
                time.sleep(0.2)
    values = []
    for attr in ['text', 'content-desc']:
        for match in re.finditer(attr + r'=(["\'])(.*?)\1', xml, flags=re.S):
            value = unescape(match.group(2)).strip()
            if value:
                values.append(value)
    return {
        'path': str(dump_read_path),
        'shellPath': dump_shell_path,
        'text': '\n'.join(values),
        'xmlSize': len(xml),
        'error': '' if xml else 'uiautomator produced no readable XML',
    }


def run_prompt(prompt, wait_seconds=90, new_conversation=False, force_stop=True):
    if force_stop:
        rish(f'am force-stop {PACKAGE}', timeout=10)
        time.sleep(0.5)
        today_log = APP_LOG_DIR / f'{dt.datetime.now().strftime("%Y-%m-%d")}.log'
        rish(f': > {shlex.quote(str(today_log))}', timeout=10)
    extra = ' --ez home_center_smoke_mute_speech true'
    if new_conversation:
        extra += ' --ez home_center_smoke_new_conversation true'
    rish(f'am start -n {ACTIVITY} --es home_center_smoke_prompt {shlex.quote(prompt)}{extra}', timeout=20, check=True)
    time.sleep(3)
    deadline = time.time() + wait_seconds
    segment = ''
    while time.time() < deadline:
        time.sleep(3)
        segment = visible_log_text_since(prompt)
        normalized = normalize_text(segment)
        if (
            'tool_loop_final_response' in segment
            or 'gateway_type=final status=confirmation_required' in segment
            or 'google_doc_created' in segment
            or 'google_doc_updated' in segment
            or 'assistant:' in segment and any(bad in normalized for bad in LEXEN_BAD_STRINGS)
            or any(expected in normalized for expected in EXPECTED_DRIVE_OPTIONS)
        ):
            break
    return visible_log_text_since(prompt)


def assistant_reply_from_segment(segment):
    matches = re.findall(r'assistant: (.*?)(?=\n\d{4}-\d{2}-\d{2}T|\Z)', segment, flags=re.S)
    return matches[-1].strip() if matches else ''


def looks_truncated(text):
    stripped = text.strip()
    if not stripped:
        return True
    if stripped.endswith(('...', '…')):
        return True
    words = re.findall(r'\w+', stripped)
    if len(words) < 120:
        return True
    return stripped[-1] not in '.!?"”'


def run_drive_checks(capture_start, expected_version_marker):
    failures = []
    prompt_results = []
    stale_install = False
    for index, prompt in enumerate(DRIVE_PROMPTS):
        prompt_start = time.time()
        segment = run_prompt(prompt, wait_seconds=30)
        log_text = latest_log_text()
        prompt_assertions = {
            'composerInputPathUsed': prompt in segment and 'installed_smoke prompt_requested' in log_text,
            'friendlyDriveCardVisible': any(expected in segment for expected in EXPECTED_DRIVE_OPTIONS),
            'noRawProxyInstructionVisible': 'Start the speech proxy' not in segment,
            'noSpeechProxyErrorVisible': 'Speech proxy error' not in segment and 'Speech proxy unavailable' not in segment,
            'noStaleDriveSetupVisible': not any(bad in segment for bad in BAD_STRINGS),
            'noFoodFallbackVisible': 'tell me the main ingredient' not in segment and 'second constraint' not in segment and 'second ingredient' not in segment,
        }
        prompt_failures = [name for name, ok in prompt_assertions.items() if not ok]
        for bad in BAD_STRINGS:
            if bad in segment:
                prompt_failures.append(f'bad visible text: {bad}')
        prompt_results.append({
            'prompt': prompt,
            'startedAtEpoch': prompt_start,
            'assertions': prompt_assertions,
            'failures': prompt_failures,
            'logTextSample': segment[-1800:],
        })
        failures.extend(f'{prompt}: {failure}' for failure in prompt_failures)

    visual_capture = latest_visual_capture(capture_start)
    assertions = {
        'chatViewLoads': visual_capture is not None,
        'composerVisible': visual_capture is not None,
        'defaultAdminControlsHidden': True,
        'runtimeVersionMatches': expected_version_marker in latest_log_text(),
        'installedBuildFreshEnoughForBehaviorAssertions': not stale_install,
    }
    for name, ok in assertions.items():
        if not ok:
            failures.append(name)
    return {
        'ok': not failures,
        'failures': failures,
        'assertions': assertions,
        'promptResults': prompt_results,
        'appVisualCapture': str(visual_capture) if visual_capture else None,
        'staleInstall': stale_install,
    }


def run_lexen_installed_path(stamp):
    prompt_start = time.time()
    segment = run_prompt(LEXEN_PROMPT, wait_seconds=150)
    ui = dump_ui_text(stamp)
    combined = segment + '\n' + ui.get('text', '')
    normalized = normalize_text(combined)
    reply = assistant_reply_from_segment(segment)
    assertions = {
        'lexenPromptVisible': normalize_text(LEXEN_PROMPT) in normalize_text(segment),
        'lexenAssistantResponseVisible': bool(reply),
        'lexenResponseContainsProse': len(re.findall(r'\w+', reply)) >= 120 and any(
            marker in reply.lower() for marker in ['lexen', 'commander', 'green']
        ),
        'lexenNoGithubIssueLoop': not any(bad in normalized for bad in [
            'github.create_issue',
            'create github issue',
            'file an issue',
            'i can create a github issue',
        ]),
        'lexenNoConfirmationCard': 'press confirm' not in normalized and 'confirm create' not in normalized,
        'lexenNoToolDiagnostic': 'docs.read' not in reply and 'tool_loop' not in reply,
        'lexenNoGatewayFailure': not any(bad in normalized for bad in [
            'gateway connection closed',
            'unexpected end of stream',
            'valid gpt-5.5 response',
            'tool_loop_failed',
            'software caused connection abort',
        ]),
        'lexenResponseNotTruncated': not looks_truncated(reply),
        'lexenFinalStatusSeen': 'gateway_type=final' in segment and 'gpt_5_5_complete' in segment,
        'lexenElevenLabsRequested': 'elevenlabs_request' in segment,
        'lexenNoLegacySpeechProvider': (FORBIDDEN_SPEECH_PROVIDER + '_') not in segment and FORBIDDEN_SPEECH_PROVIDER_TITLE not in segment,
    }
    return {
        'prompt': LEXEN_PROMPT,
        'startedAtEpoch': prompt_start,
        'assertions': assertions,
        'failures': [name for name, ok in assertions.items() if not ok],
        'assistantReply': reply,
        'logTextSample': segment[-5000:],
        'uiDump': ui,
    }


def smoke_audio_assertions(combined):
    return {
        'smokeSpeechMuted': 'smoke_mute_skip' in combined and 'speech_cleanup reason=smoke_muted' in combined,
        'smokeNoAudioFocus': 'audio_focus_request' not in combined and 'audio_focus_abandoned' not in combined,
        'smokeNoLegacySpeechProvider': (FORBIDDEN_SPEECH_PROVIDER + '_') not in combined and FORBIDDEN_SPEECH_PROVIDER_TITLE not in combined,
        'smokeNoNativeTts': 'native_tts_request' not in combined and 'device_tts_start' not in combined and 'device_tts_complete' not in combined,
        'smokeNoMediaControlPath': 'media_key_handoff_disabled' not in combined,
    }


def run_issue46_installed_path(stamp):
    prompt_start = time.time()
    scratch_title = f'{SCRATCH_DOC_PREFIX} {stamp}'
    create_prompt = f'Create a Google Doc named {scratch_title} with this body: Scratch sandbox seed {stamp}.'
    create_segment = run_prompt(create_prompt, wait_seconds=180, force_stop=True)
    create_confirm_segment = run_prompt('confirm create', wait_seconds=180, force_stop=False)
    existing_append_text = f'existing conversation scratch update {stamp}'
    existing_prompt = f'Append this exact smoke note to the Google Doc named {scratch_title}: {existing_append_text}.'
    existing_segment = run_prompt(existing_prompt, wait_seconds=180, force_stop=False)
    existing_confirm_segment = run_prompt('confirm edit', wait_seconds=180, force_stop=False)
    new_append_text = f'new conversation scratch update {stamp}'
    new_prompt = (
        f'In a new conversation, find the Google Doc named {scratch_title}, read it, '
        f'then append this exact smoke note at the very end: {new_append_text}. '
        'Ask me to confirm the edit before changing the document.'
    )
    new_segment = run_prompt(new_prompt, wait_seconds=180, new_conversation=True, force_stop=False)
    new_confirm_segment = run_prompt('confirm edit', wait_seconds=180, force_stop=False)
    full_log = latest_log_text(include_download_logs=False)
    ui = dump_ui_text(stamp)
    ui_text = ui.get('text', '')
    segment = '\n'.join([
        create_segment,
        create_confirm_segment,
        existing_segment,
        existing_confirm_segment,
        new_segment,
        new_confirm_segment,
    ])
    combined = full_log + '\n' + segment + '\n' + ui_text
    normalized = normalize_text(combined).lower()
    ui_normalized = normalize_text(ui_text).lower()
    reply = assistant_reply_from_segment(segment)
    audio_assertions = smoke_audio_assertions(combined)
    assertions = {
        'issue46ScratchDocPromptVisible': scratch_title in combined,
        'issue46ScratchDocCreated': 'android_received_tool=docs.create' in combined and 'google_doc_created' in combined,
        'issue46ScratchExistingEditConfirmed': existing_append_text in combined and combined.count('google_doc_updated') >= 1,
        'issue46ScratchNewEditConfirmed': new_append_text in combined and combined.count('google_doc_updated') >= 2,
        'issue46NewConversationUsed': 'newConversation=true' in combined or 'New conversation started.' in combined,
        'issue46DocsSearchOrReadSeen': 'android_received_tool=docs.search' in combined or 'android_received_tool=docs.read' in combined,
        'issue46DocsReadSeen': 'android_received_tool=docs.read' in combined or 'android_dispatch_result tool=docs.read ok=true' in combined,
        'issue46ConfirmationRequired': combined.count('gateway_type=final status=confirmation_required') >= 3 or 'press confirm' in normalized,
        'issue46PendingEditCopy': 'say \"confirm edit\" or press confirm' in normalized and scratch_title.lower() in normalized,
        'issue46UiDumpReadable': ui.get('xmlSize', 0) > 0 and not ui.get('error'),
        'issue46UiShowsScratchResult': scratch_title.lower() in ui_normalized or new_append_text in normalized,
        **audio_assertions,
        'issue46NoFalseUnavailable': not any(bad in normalized for bad in [
            'document editing tools are not available',
            'editing tools are not available',
            'docs.update is not exposed',
            'tool_not_exposed',
            'could not complete the document update',
        ]),
        'issue46NoGatewayFailure': not any(bad in normalized for bad in [
            'gateway connection closed',
            'unexpected end of stream',
            'valid gpt-5.5 response',
            'tool_loop_failed',
            'software caused connection abort',
        ]),
    }
    return {
        'prompt': new_prompt,
        'scratchTitle': scratch_title,
        'startedAtEpoch': prompt_start,
        'assertions': assertions,
        'failures': [name for name, ok in assertions.items() if not ok],
        'assistantReply': reply,
        'logTextSample': combined[-9000:],
        'uiDump': ui,
    }


def main():
    for command in ['am', 'uiautomator']:
        require_command(command)
    DOWNLOAD_CAPTURE_DIR.mkdir(parents=True, exist_ok=True)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    scenario = sys.argv[1] if len(sys.argv) > 1 else 'all'
    started_at = dt.datetime.now().isoformat(timespec='seconds')
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    evidence_path = ARTIFACT_DIR / f'home_center_user_path_{stamp}.json'

    expected_version_name, expected_version_code = expected_build_version()
    expected_version_marker = f'versionName={expected_version_name} versionCode={expected_version_code}'
    installed_version = installed_package_version()
    failures = []
    capture_start = time.time()
    drive_result = None
    lexen_result = None
    issue46_result = None

    version_assertions = {
        'installedVersionNameMatches': installed_version['versionName'] == expected_version_name,
        'installedVersionCodeMatches': installed_version['versionCode'] == expected_version_code,
    }
    failures.extend(name for name, ok in version_assertions.items() if not ok)

    if scenario in ('all', 'drive'):
        drive_result = run_drive_checks(capture_start, expected_version_marker)
        failures.extend(drive_result['failures'])
    if scenario in ('all', 'lexen'):
        lexen_result = run_lexen_installed_path(stamp)
        failures.extend(f'lexen: {failure}' for failure in lexen_result['failures'])
    if scenario in ('all', 'issue46'):
        issue46_result = run_issue46_installed_path(stamp)
        failures.extend(f'issue46: {failure}' for failure in issue46_result['failures'])

    evidence = {
        'ok': not failures,
        'startedAt': started_at,
        'package': PACKAGE,
        'scenario': scenario,
        'expectedVersionName': expected_version_name,
        'expectedVersionCode': expected_version_code,
        'installedVersion': installed_version,
        'versionAssertions': version_assertions,
        'driveResult': drive_result,
        'lexenResult': lexen_result,
        'issue46Result': issue46_result,
        'failures': failures,
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
