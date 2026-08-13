#!/usr/bin/env python3
from pathlib import Path

source = Path(__file__).with_name('android_phone_home_center_relay.py').read_text(encoding='utf-8')
start = source.index('def execute_action(a):')
end = source.index('\ndef loop(', start)
body = source[start:end]

shell_exemption = "if k in TERMUX_SHELL_ACTIONS:return termux_shell_execute(a)"
gate = 'gate=overlay_control_gate()'
assert shell_exemption in body, 'phone_shell must have an explicit pre-gate execution lane'
assert body.index(shell_exemption) < body.index(gate), 'phone_shell must execute before Android UI consent is evaluated'
assert body.index("if k in OVERLAY_ACTIONS:return overlay_execute(a)") < body.index(gate)
assert body.index("if k in DIAGNOSTIC_ACTIONS:return diagnostics_execute(a)") < body.index(gate)
assert 'SCREEN_DIRECT_ACTIONS' not in body[:body.index(gate)], 'screen actions must not bypass overlay consent'
assert 'SCREEN_WINDOW_ACTIONS' not in body[:body.index(gate)], 'screen-window actions must not bypass overlay consent'
assert body.index('return dispatch(a)') > body.index(gate), 'ordinary Android actions remain behind the gate'

print('Phone relay overlay gate contract tests passed')
