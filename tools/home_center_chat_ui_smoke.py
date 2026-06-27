#!/data/data/com.termux/files/usr/bin/python3
import datetime as dt
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / 'tools' / 'visual_evidence'
DUMP_PATH = Path('/storage/emulated/0/Download/HomeCenter/home_center_chat_ui_dump.xml')
PACKAGE = 'com.dclar.homecenter'
ACTIVITY = 'com.dclar.homecenter/.MainActivity'


def run(args, timeout=20, check=False):
    proc = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
    if check and proc.returncode != 0:
        raise RuntimeError(f"command failed {args}: {proc.stderr.strip() or proc.stdout.strip()}")
    return proc


def require_command(name):
    proc = run(['sh', '-c', f'command -v {name}'], timeout=5)
    if proc.returncode != 0:
        raise RuntimeError(f'missing required Android command: {name}')


def fail_if(condition, failures, name):
    if condition:
        failures.append(name)


def main():
    require_command('am')
    require_command('uiautomator')
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    DUMP_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime('%Y%m%d_%H%M%S')
    evidence_path = ARTIFACT_DIR / f'home_center_chat_ui_smoke_{stamp}.json'

    run(['am', 'force-stop', PACKAGE], timeout=10)
    time.sleep(0.5)
    run(['am', 'start', '-n', ACTIVITY], timeout=20, check=True)
    time.sleep(2.0)
    dump = run(['uiautomator', 'dump', str(DUMP_PATH)], timeout=20, check=True)
    xml = DUMP_PATH.read_text(errors='replace')

    visible_home_center_titles = len(re.findall(r'text="Home Center"', xml))
    checks = {
        'chatViewLoads': PACKAGE in dump.stdout or DUMP_PATH.exists(),
        'composerVisible': 'content-desc="Message Home Center"' in xml,
        'sendVisible': 'text="Send"' in xml,
        'micButtonAbsent': 'text="Mic"' not in xml and 'content-desc="Talk to Home Center"' not in xml,
        'stopHiddenWhenIdle': 'text="Stop speech"' not in xml and 'text="Stop"' not in xml,
        'searchTagAccountControlsAbsent': all(text not in xml for text in ['Conversation search', 'Tag editor', 'Sign out', 'Refresh']),
        'debugStatusSpamAbsent': all(text not in xml for text in ['Home Center sync:', 'Type or use Talk', 'Restored previous chat history', 'Google tools connected']),
        'rawJsonAbsent': '{&quot;' not in xml and '{"' not in xml and 'raw tool' not in xml.lower(),
        'singleHomeCenterTitle': visible_home_center_titles <= 1,
    }
    failures = [name for name, ok in checks.items() if not ok]
    evidence = {
        'startedAt': stamp,
        'dumpPath': str(DUMP_PATH),
        'visibleHomeCenterTitles': visible_home_center_titles,
        'checks': checks,
        'failures': failures,
        'xmlSample': xml[:4000],
    }
    evidence_path.write_text(json.dumps(evidence, indent=2))
    if failures:
        print(f'Home Center chat UI smoke failed: {failures}. Evidence: {evidence_path}', file=sys.stderr)
        sys.exit(1)
    print(f'Home Center chat UI smoke: OK evidence={evidence_path}')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'Home Center chat UI smoke failed: {exc}', file=sys.stderr)
        sys.exit(1)
