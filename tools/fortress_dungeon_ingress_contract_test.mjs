#!/usr/bin/env node
import fs from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const contract = require('../functions/dungeon_run_contract');
const relayModule = require('../functions/phone_hands_relay');
const relay = fs.readFileSync('functions/phone_hands_relay.js', 'utf8');
const operation = fs.readFileSync('functions/dungeon_run_operation.js', 'utf8');
const mcp = fs.readFileSync('functions/home_center_mcp.js', 'utf8');
const phone = fs.readFileSync('tools/android_phone_home_center_relay.py', 'utf8');
const runner = fs.readFileSync('tools/mobile_coding_dungeon_v2.py', 'utf8');

for (const needle of [
  'cleanDungeonRun', 'cleanDungeonStatus', 'coding_dungeon_v2', 'requestHash',
  'priorityRank', 'leaseId', 'recoverStaleDungeonLeases', 'exact live admission lease',
]) if (!relay.includes(needle)) throw new Error(`typed relay boundary missing ${needle}`);

for (const needle of [
  'dungeon_run', 'dungeon_status', 'dungeon_command_status', 'enqueuePhoneCommand',
  'callerFromHomeCenterUser', 'checkpoint-only',
]) if (!operation.includes(needle)) throw new Error(`direct dungeon operation missing ${needle}`);

for (const needle of [
  "require('./dungeon_run_operation')", '...dungeonOperationEntries()',
  "operation === 'dungeon_run'", "operation === 'dungeon_status'",
  "operation === 'dungeon_command_status'", '2026-08-13.fortress-dungeon-v2',
]) if (!mcp.includes(needle)) throw new Error(`stable drive_operation ingress missing ${needle}`);

for (const needle of [
  'mobile_coding_dungeon_v2', 'DUNGEON_ACTIONS', 'coding_dungeon_v2',
  "if k in DUNGEON_ACTIONS:return dispatch(a)", "'leaseId':cmd.get('leaseId','')",
]) if (!phone.includes(needle)) throw new Error(`phone relay v2 integration missing ${needle}`);
if (phone.includes("p.get('manifest')") || phone.includes("dungeon_run requires manifest")) {
  throw new Error('legacy caller-selected manifest path remains reachable');
}
if (phone.indexOf("if k in DUNGEON_ACTIONS:return dispatch(a)") > phone.indexOf('gate=overlay_control_gate()')) {
  throw new Error('screenless dungeon ingress must bypass the overlay/Shizuku gate');
}

for (const needle of [
  'shell=False', 'codex-local-low-deterministic-v1', 'workspace-write',
  'ask-for-approval', 'checkpoint-only', 'prepare_worktree', 'launch_tmux',
  'QUARANTINED', 'phone-state://coding-dungeon-v2',
]) if (!runner.includes(needle)) throw new Error(`phone-local coordinator missing ${needle}`);
for (const forbidden of ["shell=True", "subprocess.run(cmd", "get('manifest')", "get(\"manifest\")"] ) {
  if (runner.includes(forbidden)) throw new Error(`v2 coordinator contains forbidden execution surface: ${forbidden}`);
}

const critical = contract.cleanDungeonRun({
  requestId:'critical-campaign-0001', campaignId:'fortress-online', workspaceId:'home-center',
  objective:'Repair one exact first-class execution aperture.', acceptance:['Typed ingress passes.'],
  lane:'critical', criticalReason:'The owner designated this as the recovery-critical lane.',
});
const standard = contract.cleanDungeonRun({
  requestId:'standard-campaign-0001', campaignId:'fortress-online', workspaceId:'home-center',
  objective:'Perform one ordinary bounded maintenance task.', acceptance:['Verification passes.'],
});
const status = contract.cleanDungeonStatus({requestId:'status-campaign-0001',jobId:'dng_0123456789abcdef01234567'});
const now = Date.now();
const chosen = relayModule.selectQueuedCommand([
  {commandId:'ordinary', action:standard, createdAtMs:now-1000, expiresAtMs:now+10000},
  {commandId:'critical', action:critical, createdAtMs:now, expiresAtMs:now+10000},
  {commandId:'status', action:status, createdAtMs:now+1000, expiresAtMs:now+10000},
], now);
if (chosen.commandId !== 'status') throw new Error('status/critical deterministic queue ordering failed');
const criticalChosen = relayModule.selectQueuedCommand([
  {commandId:'ordinary', action:standard, createdAtMs:now-1000, expiresAtMs:now+10000},
  {commandId:'critical', action:critical, createdAtMs:now, expiresAtMs:now+10000},
], now);
if (criticalChosen.commandId !== 'critical') throw new Error('critical lane did not outrank ordinary work');

console.log('Fortress typed dungeon ingress / critical lane / fixed decay contract: PASS');
