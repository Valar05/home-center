#!/usr/bin/env python3
"""Dedicated outbound THECAULDRON Warm v1 worker, no arbitrary shell."""
import argparse
import getpass
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(r'C:\Users\dclar\workspace\ritsu-faster-qwen3-tts')
SENDER = ROOT / 'ritsu_say.py'
PYTHON = ROOT / '.venv' / 'Scripts' / 'python.exe'
VOICE_TOKEN = ROOT / 'ritsu-api-token.txt'
PAUSE = ROOT / 'RITSU_WARM_ASMR_MAINTENANCE'
DIRECTORY = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'RitsuWarmTicketWorker'
CREDENTIALS = DIRECTORY / 'worker_token.json'
JOURNAL = DIRECTORY / 'tickets'
TIMING = DIRECTORY / 'timing'
SERVER = os.environ.get('RITSU_VOICE_TICKET_ORIGIN', 'https://us-central1-home-center-dclar.cloudfunctions.net/ritsuVoice').rstrip('/')
WORKER = 'cauldron-ritsu-warm-01'
RECEIPT = re.compile(r'^ENQUEUED_CHUNK\s+(\d+)\s+of\s+(\d+)\s+relay\s+([a-f0-9]{16,80})\b')
SAFE_ID = re.compile(r'^[A-Za-z0-9_.:-]{6,160}$')
REGISTERED_PROFILES = frozenset(('normal', 'whisper', 'amused', 'happy', 'upset', 'somber'))


def trace_ticket(ticket_id, event):
    """Best-effort same-clock trace; do not record text or credentials."""
    if not SAFE_ID.fullmatch(str(ticket_id)):
        return
    try:
        import datetime
        TIMING.mkdir(parents=True, exist_ok=True)
        stamp = {"turnId": ticket_id, "event": event, "seq": 0,
                 "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="milliseconds"),
                 "monotonic_ns": time.monotonic_ns()}
        with (TIMING / ("worker-" + ticket_id + ".jsonl")).open("a", encoding="utf-8") as out:
            out.write(json.dumps(stamp, separators=(",", ":")) + "\n")
    except OSError:
        pass


def post(route, payload, token=None):
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = 'Bearer ' + token
        headers['X-Home-Center-Worker'] = WORKER
    req = urllib.request.Request(SERVER + '/' + route, json.dumps(payload).encode(), headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        # Never echo bootstrap code, bearer token, or request body.
        try:
            body = json.loads(err.read(1024).decode('utf-8'))
            reason = str(body.get('error', 'server error'))[:160]
        except (ValueError, UnicodeError):
            reason = 'non-JSON server response'
        raise RuntimeError(f'Voice endpoint HTTP {err.code}: {reason}') from None


def read_private_code(use_clipboard=False):
    if not use_clipboard:
        return getpass.getpass('One-time private Ritsu bootstrap code: ').strip()
    # msvcrt.getwch used by getpass on Windows may not receive pasted text
    # from some terminal hosts. Read clipboard without putting the code on
    # the command line or printing it, then immediately clear clipboard.
    if os.name != 'nt':
        raise RuntimeError('Clipboard bootstrap is available on Windows only')
    capture = subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                              'Get-Clipboard -Raw'], capture_output=True, text=True,
                             timeout=15, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    try:
        if capture.returncode != 0:
            raise RuntimeError('Cannot read clipboard; copy the code and retry')
        return capture.stdout.strip()
    finally:
        subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                        "Set-Clipboard -Value ''"], capture_output=True, timeout=15,
                       creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))


def bootstrap(use_clipboard=False):
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    if CREDENTIALS.exists():
        raise RuntimeError('Worker already registered; refusing credential replacement')
    code = read_private_code(use_clipboard)
    if not re.fullmatch(r'[A-Za-z0-9_-]{32}', code):
        raise RuntimeError('Registration code must be exactly 32 base64url characters. No spaces or backticks.')
    print('CODE_FINGERPRINT:', hashlib.sha256(code.encode('utf-8')).hexdigest()[:12], flush=True)
    answer = post('bootstrap', {'bootstrapCode': code})
    if answer.get('status') != 'registered' or answer.get('workerId') != WORKER:
        raise RuntimeError('Worker registration not accepted')
    tmp = CREDENTIALS.with_suffix('.tmp')
    tmp.write_text(json.dumps(answer), encoding='utf-8')
    me = os.environ.get('USERNAME', '')
    if not me:
        tmp.unlink(missing_ok=True)
        raise RuntimeError('Missing Windows user for credential ACL')
    subprocess.run(['icacls', str(tmp), '/inheritance:r', '/grant:r', me + ':F'],
                   check=True, stdout=subprocess.DEVNULL)
    os.replace(tmp, CREDENTIALS)
    print('REGISTERED: token saved privately, not printed')


def worker_token():
    row = json.loads(CREDENTIALS.read_text(encoding='utf-8'))
    if row.get('workerId') != WORKER or int(row.get('expiresAtMs', 0)) <= int(time.time()*1000):
        raise RuntimeError('Voice token invalid or expired')
    return row['token']


def warm_ready():
    if not PYTHON.is_file() or not SENDER.is_file() or not VOICE_TOKEN.is_file():
        return False
    token = VOICE_TOKEN.read_text(encoding='utf-8').strip()
    req = urllib.request.Request('http://127.0.0.1:10205/v1/health',
                                 headers={'Authorization': 'Bearer ' + token})
    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            row = json.load(response)
        return row.get('model') == 'loaded' and not row.get('error')
    except (OSError, ValueError):
        return False


def dispatch(ticket):
    if ticket.get('voice') != 'warm-v1' or ticket.get('delivery') != 'phone':
        return {'status': 'failed', 'errorCode': 'WRONG_VOICE_OR_TRANSPORT'}
    if PAUSE.exists():
        return {'status': 'maintenance'}
    if not warm_ready():
        return {'status': 'failed', 'errorCode': 'WARM_UNAVAILABLE'}
    profile = ticket.get('profile', 'normal')
    if profile not in REGISTERED_PROFILES:
        return {'status': 'failed', 'errorCode': 'UNKNOWN_VOICE_PROFILE'}
    text = ticket.get('text', '')
    if hashlib.sha256(text.encode('utf-8')).hexdigest() != ticket.get('textSha256'):
        return {'status': 'failed', 'errorCode': 'PAYLOAD_DIGEST_MISMATCH'}
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='ritsu-', dir=DIRECTORY) as temp:
        source = Path(temp)/'dialogue.txt'
        source.write_text(text, encoding='utf-8')
        # Fixed program and fixed argument names; dialogue never interpolated into a shell.
        trace_ticket(ticket['ticketId'], 'worker_sender_start')
        # A cloud ticket is exactly one agent-authored passage, with no
        # deterministic sentence or paragraph splitting by the sender.
        # Several paragraphs require separate explicit agent-authored tickets
        # with ordered delivery, not heuristic text chopping.
        expected_chunks = ticket.get('expectedChunks')
        if expected_chunks is not None and expected_chunks != 1:
            return {'status': 'failed', 'errorCode': 'AGENT_AUTHORED_CHUNKS_REQUIRED'}
        args = [str(PYTHON), str(SENDER), '--text-file', str(source),
                '--profile', profile, '--turn-id', ticket['ticketId']]
        proc = subprocess.run(args,
                              cwd=str(ROOT), capture_output=True, text=True, timeout=1100,
                              creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        trace_ticket(ticket['ticketId'], 'worker_sender_returned')
        if proc.returncode != 0:
            return {'status': 'failed', 'errorCode': 'SENDER_FAILED'}
        ids = []
        total = None
        for line in proc.stdout.splitlines():
            match = RECEIPT.match(line)
            if match:
                number, count, relay = int(match[1]), int(match[2]), match[3]
                if number != len(ids)+1 or count > 50 or (total is not None and count != total):
                    return {'status': 'failed', 'errorCode': 'RECEIPT_ORDER_MISMATCH'}
                total = count
                ids.append(relay)
        if not ids or len(ids) != total or 'ALL_CHUNKS_ENQUEUED_NOT_HEARD' not in proc.stdout:
            return {'status': 'failed', 'errorCode': 'INCOMPLETE_ENQUEUE'}
        return {'status': 'enqueued', 'relayIds': ids}


def durable_record(name, payload):
    """Write safely before a side effect or result acknowledgment."""
    JOURNAL.mkdir(parents=True, exist_ok=True)
    target = JOURNAL / (name + '.json')
    draft = JOURNAL / (name + '.new')
    with draft.open('w', encoding='utf-8') as f:
        json.dump(payload, f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(draft, target)


def process_ticket(job):
    name = job.get('ticketId', '')
    if not SAFE_ID.fullmatch(name):
        raise RuntimeError('Rejected malformed ticket id')
    trace_ticket(name, 'worker_claim')
    digest = job.get('textSha256', '')
    record_file = JOURNAL / (name + '.json')
    if record_file.exists():
        old = json.loads(record_file.read_text(encoding='utf-8'))
        if old.get('textSha256') != digest:
            raise RuntimeError('Duplicate ticket ID with different transcript digest')
        if old.get('phase') == 'complete':
            return old['result']
        # Previous invocation may have enqueued one or more clips.
        # Fail closed rather than replay speech with unknown delivery.
        return {'status': 'failed', 'errorCode': 'AMBIGUOUS_PREVIOUS_ATTEMPT'}
    durable_record(name, {'phase': 'started', 'textSha256': digest})
    try:
        result = dispatch(job)
    except subprocess.TimeoutExpired:
        result = {'status': 'failed', 'errorCode': 'SENDER_TIMEOUT_AMBIGUOUS'}
    except Exception:
        result = {'status': 'failed', 'errorCode': 'LOCAL_EXECUTION_ERROR'}
    durable_record(name, {'phase': 'complete', 'textSha256': digest, 'result': result})
    trace_ticket(name, 'worker_local_complete')
    return result


def main():
    # Windows kernel mutex prevents accidental duplicate polling processes.
    mutex = None
    if os.name == 'nt':
        import ctypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        kernel.CreateMutexW.restype = ctypes.c_void_p
        mutex = kernel.CreateMutexW(None, 0, 'Local\\RitsuWarmTicketWorker_V1')
        if not mutex:
            raise RuntimeError('Cannot create voice worker mutex')
        if ctypes.get_last_error() == 183:
            print('ALREADY_RUNNING: refusing second ticket worker', flush=True)
            kernel.CloseHandle(mutex)
            return
    token = worker_token()
    while True:
        try:
            response = post('lease', {}, token)
            job = response.get('ticket')
            if not job:
                time.sleep(max(1, min(int(response.get('pollAfterSeconds', 3)), 30)))
                continue
            name = job.get('ticketId', '')
            result = process_ticket(job)
            post('tickets/' + name + '/complete', result, token)
            trace_ticket(name, 'worker_cloud_completion_ack')
            print('TICKET', name, result['status'], len(result.get('relayIds', [])), flush=True)
        except KeyboardInterrupt:
            break
        except Exception as err:
            print('RETRY', type(err).__name__, flush=True)
            time.sleep(10)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bootstrap', action='store_true')
    parser.add_argument('--bootstrap-clipboard', action='store_true')
    args = parser.parse_args()
    if args.bootstrap or args.bootstrap_clipboard:
        bootstrap(use_clipboard=args.bootstrap_clipboard)
    else:
        main()
