#!/data/data/com.termux/files/usr/bin/python3
import json
import shutil
import subprocess
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


def enabled_google_services(project='home-center-dclar'):
    if not shutil.which('gcloud'):
        return None
    result = subprocess.run([
        'gcloud', 'services', 'list', '--enabled', f'--project={project}',
        '--filter=NAME:(drive.googleapis.com docs.googleapis.com sheets.googleapis.com gmail.googleapis.com calendar-json.googleapis.com people.googleapis.com)',
        '--format=value(config.name)',
    ], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
    if result.returncode != 0:
        fail(f'gcloud services check failed: {result.stderr.strip()}')
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


required_google_services = {
    'drive.googleapis.com',
    'docs.googleapis.com',
    'sheets.googleapis.com',
    'gmail.googleapis.com',
    'calendar-json.googleapis.com',
    'people.googleapis.com',
}
services = enabled_google_services()
if services is not None and services != required_google_services:
    fail(f'Google API services mismatch: missing={sorted(required_google_services - services)} extra={sorted(services - required_google_services)}')

status, health = get_json('health')
expected_groups = {'drive', 'docs', 'sheets', 'lists', 'gmail', 'calendar', 'contacts', 'github', 'knowledge'}
actual_groups = set(health.get('contractGroups') or [])
if (status != 200
        or health.get('service') != 'home-center-gateway'
        or health.get('confirmationFlow') != 'short-confirm-v1'
        or health.get('toolContractVersion') != 'google-github-knowledge-delete-cru-v1'
        or actual_groups != expected_groups):
    fail(f'health bad: status={status} body={health}')

status, headers, body = post_json('tts', {'text': 'Home Center provider smoke.'}, timeout=45)
content_type = headers.get('Content-Type', '')
speech_provider = headers.get('X-Speech-Provider', '')
speech_voice = headers.get('X-Speech-Voice', '')
tts_bytes = len(body)
if status != 200 or tts_bytes < 2048 or not ('audio' in content_type or 'octet-stream' in content_type):
    fail(f'ElevenLabs tts bad: status={status} content_type={content_type!r} bytes={tts_bytes} body={body[:160]!r}')
if speech_provider != 'elevenlabs' or speech_voice.lower() != 'brian':
    fail(f'ElevenLabs tts headers bad: provider={speech_provider!r} voice={speech_voice!r}')

status, headers, body = post_json('googleDriveProbe', {'query': 'Can Home Center read Google Drive?'}, timeout=20)
if status != 401:
    fail(f'googleDriveProbe should require Firebase auth when unauthenticated: status={status} body={body[:200]!r}')

status, headers, body = post_json('agentToolTurn', {'message': 'Create a Google Doc titled Home Center Write Test with body Tool write test.'}, timeout=20)
if status != 401:
    fail(f'agentToolTurn should require Firebase auth when unauthenticated: status={status} body={body[:200]!r}')

service_note = 'googleApis=' + ','.join(sorted(required_google_services)) if services is not None else 'googleApis=not_checked_no_gcloud'
print(f'Home Center provider smoke: OK elevenlabsBytes={tts_bytes} toolContractVersion=google-github-knowledge-delete-cru-v1 contractGroups=calendar,contacts,docs,drive,github,gmail,knowledge,lists,sheets {service_note} driveProbeUnauth=401 agentToolTurnUnauth=401')
