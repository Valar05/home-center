#!/data/data/com.termux/files/usr/bin/python3
import json
import sys
import urllib.error
import urllib.request

BASE = 'https://us-central1-home-center-dclar.cloudfunctions.net'


def post_json(path, payload, token=None, timeout=30):
    data = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    if token:
        headers['Authorization'] = f'Bearer {token}'
    req = urllib.request.Request(f'{BASE}/{path}', data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as err:
        return err.code, err.headers, err.read()


def get_json(path, timeout=15):
    with urllib.request.urlopen(f'{BASE}/{path}', timeout=timeout) as response:
        return response.status, json.loads(response.read().decode('utf-8', 'replace'))


def fail(message):
    print(f'Home Center provider smoke failed: {message}', file=sys.stderr)
    sys.exit(1)

status, health = get_json('health')
if status != 200 or health.get('service') != 'home-center-gateway':
    fail(f'health bad: status={status} body={health}')

status, headers, body = post_json('tts', {'text': 'Home Center provider smoke.'}, timeout=45)
content_type = headers.get('Content-Type', '')
tts_bytes = len(body)
if status != 200 or tts_bytes < 2048 or not ('audio' in content_type or 'octet-stream' in content_type):
    fail(f'Cartesia tts bad: status={status} content_type={content_type!r} bytes={tts_bytes} body={body[:160]!r}')

status, headers, body = post_json('googleDriveProbe', {'query': 'Can Home Center read Google Drive?'}, timeout=20)
if status != 401:
    fail(f'googleDriveProbe should require Firebase auth when unauthenticated: status={status} body={body[:200]!r}')

print(f'Home Center provider smoke: OK cartesiaBytes={tts_bytes} driveProbeUnauth=401')
