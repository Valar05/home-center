#!/usr/bin/env node
import fs from 'node:fs';

const agent = fs.readFileSync('tools/android_phone_home_center_relay.py', 'utf8');
const shellDispatch = "if k in TERMUX_SHELL_ACTIONS:return termux_shell_execute(a)";
const gate = 'gate=overlay_control_gate()';

const executeStart = agent.indexOf('def execute_action(a):');
if (executeStart < 0) throw new Error('execute_action missing');
const executeEnd = agent.indexOf('def loop(', executeStart);
const executeBody = agent.slice(executeStart, executeEnd < 0 ? undefined : executeEnd);

const shellIndex = executeBody.indexOf(shellDispatch);
const gateIndex = executeBody.indexOf(gate);
if (shellIndex < 0) throw new Error('phone_shell direct Termux dispatch missing from execute_action');
if (gateIndex < 0) throw new Error('interactive overlay gate missing from execute_action');
if (shellIndex > gateIndex) throw new Error('phone_shell must bypass the screen-control overlay gate');
if (!executeBody.includes('if k in DIAGNOSTIC_ACTIONS:return diagnostics_execute(a)')) throw new Error('readonly diagnostics bypass regressed');
if (!executeBody.includes('if k in OVERLAY_ACTIONS:return overlay_execute(a)')) throw new Error('overlay maintenance bypass regressed');

console.log('phone_shell is a background Termux lane and bypasses the interactive overlay gate: PASS');
