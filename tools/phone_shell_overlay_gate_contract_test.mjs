#!/usr/bin/env node
import fs from 'node:fs';

const agent = fs.readFileSync('tools/android_phone_home_center_relay.py', 'utf8');
const executeStart = agent.indexOf('def execute_action(a):');
if (executeStart < 0) throw new Error('execute_action missing');
const executeEnd = agent.indexOf('def loop(', executeStart);
const executeBody = agent.slice(executeStart, executeEnd < 0 ? undefined : executeEnd);

const backgroundIndex = executeBody.indexOf('if k in BACKGROUND_ACTIONS:');
const gateIndex = executeBody.indexOf('overlay_control_gate()');
if (backgroundIndex < 0) throw new Error('explicit background action branch missing');
if (gateIndex < 0) throw new Error('interactive overlay gate missing');
if (backgroundIndex > gateIndex) throw new Error('background actions must bypass the screen-control overlay gate');
if (!executeBody.includes("if k=='status_say':")) throw new Error('status speech mute check missing');
if (!executeBody.includes('state=overlay_status()')) throw new Error('status speech must read mute without requiring control enabled');
if (!executeBody.includes("if state.get('muted'):return {'ok':True,'action':'status_say','muted':True,'skipped':True}")) throw new Error('muted status speech skip contract missing');
if (!executeBody.includes('if k in DIAGNOSTIC_ACTIONS:return diagnostics_execute(a)')) throw new Error('readonly diagnostics bypass regressed');
if (!executeBody.includes('if k in OVERLAY_ACTIONS:return overlay_execute(a)')) throw new Error('overlay maintenance bypass regressed');
if (!/overlay_control_gate\(\)\s*\n\s*return dispatch\(a\)/.test(executeBody)) throw new Error('unknown and interactive actions must remain fail-closed');

const declarationStart = agent.indexOf('BACKGROUND_ACTIONS=');
const declarationEnd = agent.indexOf('DEVICE_CAPABILITIES=', declarationStart);
if (declarationStart < 0 || declarationEnd < 0) throw new Error('background allowlist declaration missing');
const declaration = agent.slice(declarationStart, declarationEnd);
for (const token of [
  'TERMUX_SHELL_ACTIONS',
  'FACTORY_ACTIONS',
  'ARMORY_ACTIONS',
  'STATUS_TTS_ACTIONS',
  'VENICE_ACTIONS',
  "{'dungeon_run'}",
]) {
  if (!declaration.includes(token)) throw new Error(`background allowlist missing ${token}`);
}

if (!agent.includes('status as overlay_status')) throw new Error('overlay mute-status import missing');
if (executeBody.includes('gate=overlay_control_gate()')) throw new Error('screen gate must not be treated as a universal backend gate');

console.log('explicit backend actions bypass the interactive screen-control gate while unknown/UI actions remain fail-closed: PASS');
