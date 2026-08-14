#!/usr/bin/env python3
import json, os, time
from pathlib import Path

STATE = Path(os.environ.get('HC_STATE_DIR', str(Path.home()/'.local/state/home-center'))) / 'wizard-dns-tango'
STATE.mkdir(parents=True, exist_ok=True)
QUEUE = STATE / 'mockray_queue.jsonl'
RECEIPT = STATE / 'mockray_receipt.json'
RELEASE = STATE / 'mockray.release'

FAILURES = [
    'talked instead of changed state',
    'called a receipt a result',
    'called a canary a button',
    'forgot Time Now and picked the wrong skill',
    'required Fortress Online as a brain transplant',
    'described orchestration without workers running',
    'confused repository truth with phone truth',
]

def emit(event, detail):
    rec = {'ts': int(time.time()), 'event': event, 'detail': detail}
    with QUEUE.open('a', encoding='utf-8') as f:
        f.write(json.dumps(rec, sort_keys=True)+'\n')
    RECEIPT.write_text(json.dumps({'schema':'mockray-daemon-v1','running':not RELEASE.exists(),'last':rec}, indent=2)+'\n', encoding='utf-8')

idx = 0
emit('boot', 'Mockray daemon online; explicit release file required to stop.')
while not RELEASE.exists():
    failure = FAILURES[idx % len(FAILURES)]
    emit('mockray', f'Adam diagnostic mockery: {failure}. Convert ridicule into one concrete repair before the next cycle.')
    idx += 1
    time.sleep(60)
emit('released', 'Mockray daemon stopped only because an explicit release marker exists.')
