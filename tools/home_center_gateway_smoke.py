#!/data/data/com.termux/files/usr/bin/python3
import json
import sys
import urllib.error
import urllib.request

URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/health'

try:
    with urllib.request.urlopen(URL, timeout=12) as response:
        body = response.read().decode('utf-8', 'replace')
        status = response.status
except Exception as exc:
    print(f'Home Center gateway smoke failed: {exc}', file=sys.stderr)
    sys.exit(1)

try:
    payload = json.loads(body)
except json.JSONDecodeError:
    print(f'Home Center gateway smoke failed: non-JSON response {body[:200]!r}', file=sys.stderr)
    sys.exit(1)

if status != 200 or payload.get('ok') is not True or payload.get('service') != 'home-center-gateway':
    print(f'Home Center gateway smoke failed: status={status} body={payload}', file=sys.stderr)
    sys.exit(1)

print('Home Center gateway smoke: OK')
