#!/usr/bin/env node
import fs from 'node:fs';

const relay = fs.readFileSync('tools/android_phone_home_center_relay.py', 'utf8');
const start = relay.indexOf('def execute_action(a):');
const end = relay.indexOf('def loop(', start);
if (start < 0 || end < 0) throw new Error('execute_action boundary missing');
const body = relay.slice(start, end);

const background = body.indexOf('if k in BACKGROUND_ACTIONS:');
const gate = body.indexOf('overlay_control_gate()');
if (background < 0) throw new Error('explicit background classification missing');
if (gate < 0) throw new Error('interactive screen gate missing');
if (background > gate) throw new Error('background work is incorrectly behind the screen gate');

for (const token of [
  'BACKGROUND_ACTIONS=FACTORY_ACTIONS|ARMORY_ACTIONS|STATUS_TTS_ACTIONS|TERMUX_SHELL_ACTIONS|VENICE_ACTIONS',
  "|{'dungeon_run'}",
  'if k in DIAGNOSTIC_ACTIONS:return diagnostics_execute(a)',
  'if k in OVERLAY_ACTIONS:return overlay_execute(a)',
  "if k=='status_say':",
  'state=overlay_status()',
  "if state.get('muted')",
]) {
  if (!relay.includes(token)) throw new Error(`backend authority contract missing ${token}`);
}

if (!body.includes('overlay_control_gate()\n return dispatch(a)')) {
  throw new Error('interactive and unknown actions must remain fail-closed');
}
if (body.includes('gate=overlay_control_gate()')) {
  throw new Error('screen control must not be treated as a universal backend gate');
}
if (!relay.includes('status as overlay_status')) {
  throw new Error('background status speech must read mute independently of control');
}

console.log('backend actions bypass screen authority while interactive and unknown actions remain gated: PASS');
