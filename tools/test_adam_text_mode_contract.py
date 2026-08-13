#!/usr/bin/env python3
import contextlib
import importlib.util
import io
import json
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class FakeError(RuntimeError):
    pass

class FakeMcp:
    calls = []
    def __init__(self, timeout=45):
        self.timeout = timeout
    def drive_operation(self, operation, args):
        self.calls.append((operation, dict(args)))
        if operation == 'sms_calendar.inbox':
            return {
                'state': 'all',
                'count': 1,
                'messages': [{
                    'sourceMessageReference': 'sms_' + 'a' * 32,
                    'sender': 'phone_ending_1234',
                    'state': 'classified',
                    'receivedAtMs': 123456,
                    'classification': {'sourceExcerpt': 'bounded excerpt'},
                }],
            }
        if operation == 'sms_calendar.get':
            return {
                'sourceMessageReference': args['messageId'],
                'sender': 'phone_ending_1234',
                'state': 'classified',
                'classification': {'sourceExcerpt': 'one bounded excerpt'},
            }
        raise AssertionError(operation)

fake = types.ModuleType('home_center_mcp_client')
fake.HomeCenterError = FakeError
fake.HomeCenterMcp = FakeMcp
sys.modules['home_center_mcp_client'] = fake

spec = importlib.util.spec_from_file_location('adam_text_contract_target', ROOT / 'tools' / 'adam.py')
adam = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adam)

def invoke(text):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = adam.run_text(text, str(ROOT), 30)
    return rc, json.loads(buf.getvalue())

rc, recent = invoke('recent 3')
assert rc == 0 and recent['ok'] is True
assert FakeMcp.calls[-1] == ('sms_calendar.inbox', {'limit': 3})
assert recent['readOnly'] is True
assert recent['rawMessageBodyExposed'] is False
assert recent['authoritativeUnreadState'] is False
assert recent['authoritativeProviderThreadId'] is False
assert recent['outboundAuthority'] is False
assert 'bounded excerpt' in recent['response']

message_id = 'sms_' + 'b' * 32
rc, one = invoke('get ' + message_id)
assert rc == 0 and one['ok'] is True
assert FakeMcp.calls[-1] == ('sms_calendar.get', {'messageId': message_id})
assert 'one bounded excerpt' in one['response']

rc, invalid = invoke('get nope')
assert rc == 1 and invalid['error'] == 'invalid_message_id'
assert FakeMcp.calls[-1] == ('sms_calendar.get', {'messageId': message_id}), 'invalid ids must not call Home Center'

rc, unsupported = invoke('send hello')
assert rc == 1 and unsupported['error'] == 'unsupported_text_command'
assert unsupported['usage'].startswith('TEXT: recent')

# Vlad is a read-only alias over the exact same Home Center text gate.
sys.modules['adam'] = adam
vlad_spec = importlib.util.spec_from_file_location('vlad_text_contract_target', ROOT / 'tools' / 'vlad_text.py')
vlad = importlib.util.module_from_spec(vlad_spec)
vlad_spec.loader.exec_module(vlad)
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    rc = vlad.main(['recent', '2'])
vlad_recent = json.loads(buf.getvalue())
assert rc == 0 and vlad_recent['ok'] is True
assert FakeMcp.calls[-1] == ('sms_calendar.inbox', {'limit': 2})
assert vlad_recent['readOnly'] is True
assert vlad_recent['outboundAuthority'] is False

router = (ROOT / 'tools' / 'adam.py').read_text(encoding='utf-8')
assert 'ONE_SHOT_MODES = ("terminal", "text", "chat", "continue", "vlad", "radio")' in router
assert 'drive_operation("sms_calendar.inbox"' in router
assert 'drive_operation("sms_calendar.get"' in router
assert 'sms_calendar.approve' not in router
assert 'sms_calendar.create_event' not in router
assert 'send' not in router.split('def run_text(', 1)[1].split('def worker_commission(', 1)[0].lower()
print('ADAM_TEXT_READONLY_CONTRACT=passed')
