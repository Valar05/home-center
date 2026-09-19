#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const read = (rel) => fs.readFileSync(path.join(root, rel), 'utf8');
const failures = [];
const assert = (ok, message) => { if (!ok) failures.push(message); };

const watchdog = read('tools/phone_hands_watchdog.sh');
const installer = read('tools/install_phone_hands_watchdog.sh');
const statusMenu = read('tools/home_center_status_menu.sh');
const overlayRecovery = read('tools/recover_adam_overlay_phone.sh');
const decommission = read('tools/decommission_termux_legacy.sh');

for (const forbidden of [
  'termux-wake-lock',
  'termux-notification ',
  'android.settings',
  'SYSTEM_ALERT_WINDOW',
  'operator_overlay',
  'functions/phone_hands_relay.js',
]) {
  assert(!watchdog.includes(forbidden), `canonical Phone Hands watchdog must not contain legacy/visible side effect: ${forbidden}`);
}

for (const required of [
  'home_center_phone_relay_recover.sh',
  'phone-relay-heartbeat.json',
  'phone-hands-watchdog.run.lock',
  'BUSY_PROTECTED',
  'relay_absent',
  'idle_heartbeat_stale',
  'heartbeat_pid_mismatch',
  'source_hash_mismatch',
]) {
  assert(watchdog.includes(required), `canonical watchdog missing deterministic liveness/recovery marker: ${required}`);
}

// Clean-slate permits multiple launch triggers only when they invoke one canonical
// watchdog implementation behind the same lock and recovery primitive.
for (const required of [
  '20-phone-hands-watchdog',
  'termux-job-scheduler',
  '--job-id',
  '900000',
  'PHONE_HANDS_WATCHDOG_ACTIVE',
]) {
  assert(installer.includes(required), `watchdog installer missing durable trigger: ${required}`);
}
assert(!installer.includes('HC_ENABLE_LEGACY_PHONE_HANDS_WATCHDOG'), 'canonical watchdog must not require legacy opt-in');
assert(!installer.includes('exec "$DECOMMISSION"'), 'watchdog installation must never decommission itself');
assert(!installer.includes('termux-wake-lock'), 'watchdog installer must not take a global wake lock');
assert(!installer.includes('termux-notification'), 'watchdog installer must not create persistent notifications');

assert(statusMenu.includes('HC_ENABLE_LEGACY_STATUS_MENU'), 'persistent Home Center status menu remains explicit opt-in');
assert(overlayRecovery.includes('HC_ENABLE_LEGACY_OPERATOR_OVERLAY'), 'operator overlay resurrection remains explicit opt-in');

// Explicit decommissioning remains reversible and preserves the independent SSH
// break-glass lane. It is a user-requested cleanup path, not the default runtime.
for (const needle of [
  'Fortress-Graveyard/Termux/legacy-decommission-',
  '20-phone-hands-watchdog',
  '--cancel --job-id 6405',
  'termux-wake-unlock',
  'fortress-sshd-guardian',
  'sshd',
]) {
  assert(decommission.includes(needle), `decommission campaign missing required policy marker: ${needle}`);
}
assert(decommission.includes('*fortress-sshd-guardian*|*sshd*) continue'), 'decommission campaign must explicitly exempt sshd and guardian');

if (failures.length) {
  console.error('TERMUX_CLEAN_SLATE_POLICY=FAIL');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('TERMUX_CLEAN_SLATE_POLICY=PASS');
