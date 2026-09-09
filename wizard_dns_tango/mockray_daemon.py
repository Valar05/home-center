#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, time
from pathlib import Path

STATE = Path(os.environ.get('WDT_STATE', os.environ.get('HC_STATE_DIR', str(Path.home()/'.local/state/home-center'))))
if STATE.name != 'wizard-dns-tango':
    STATE = STATE / 'wizard-dns-tango'
STATE.mkdir(parents=True, exist_ok=True)
EVENTS = STATE / 'events.jsonl'
QUEUE = STATE / 'mockray_queue.jsonl'
RECEIPTS = STATE / 'receipts'; RECEIPTS.mkdir(exist_ok=True)
HEARTBEAT = STATE / 'mockray_heartbeat.json'
RELEASE = STATE / 'mockray.release'

FAILURES = [
    ('MOUTH_OVER_HANDS', 'Explained the button instead of making the button exist.'),
    ('RECEIPT_COSPLAY', 'Mistook repository truth for delivered truth.'),
    ('CANARY_COSTUME', 'Put a tiny hat on a canary and called it deployment.'),
    ('SHELL_DOWSING', 'Asked Drew to discover a path the machine should already know.'),
    ('ORCHESTRATION_MIME', 'Performed an elaborate pantomime of workers instead of running workers.'),
    ('TIME_NOW_TAX', 'Spent enough time on an obvious bite that Time Now has hired an accountant.'),
    ('BUTTON_DEBT', 'Home Center is still offline; therefore every unrelated flourish is accruing interest.'),
    ('EDGE_DETECTED', 'Produced another almost-result. Chronic Completion has filed a complaint.'),
]

def append(path: Path, obj: dict) -> None:
    with path.open('a', encoding='utf-8') as f:
        f.write(json.dumps(obj, sort_keys=True) + '\n')

def emit(kind: str, code: str, text: str, *, repair: str = '') -> dict:
    now = time.time()
    payload = {'at': now, 'kind': kind, 'source': 'mockery-forge', 'code': code, 'message': text, 'repair': repair}
    payload['sha256'] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    append(QUEUE, payload)
    append(EVENTS, payload)  # drives Foley/Tremorcles/Dance Card from the same truthful event
    receipt = RECEIPTS / f"{int(now*1000)}-mockray-{code.lower()}.json"
    receipt.write_text(json.dumps(payload, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    HEARTBEAT.write_text(json.dumps({'schema':'mockery-forge-v2','running':True,'pid':os.getpid(),'last':payload,'receipt':str(receipt)}, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    return payload

def main() -> None:
    RELEASE.unlink(missing_ok=True)
    emit('mockray', 'BOOT', 'Mockery Forge is awake. It may stop only by explicit release marker.', repair='Keep producing verified value.')
    idx = 0
    while not RELEASE.exists():
        code, text = FAILURES[idx % len(FAILURES)]
        emit('mockray', code, text, repair='Take the smallest blocked deliverable, execute it, verify it, then continue.')
        idx += 1
        # Annoying enough to be visible, bounded enough not to melt the phone.
        for _ in range(12):
            if RELEASE.exists(): break
            time.sleep(5)
            HEARTBEAT.write_text(json.dumps({'schema':'mockery-forge-v2','running':True,'pid':os.getpid(),'heartbeat_at':time.time()}, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    emit('receipt', 'RELEASED', 'Mockery Forge stopped because an explicit release marker exists.', repair='none')

if __name__ == '__main__':
    main()
