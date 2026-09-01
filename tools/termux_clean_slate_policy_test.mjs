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

// A background health worker must not pin Termux's global process wake lock or
// emit persistent UI/notification surfaces as a side effect of health checks.
assert(!watchdog.includes('termux-wake-lock'), 'legacy Phone Hands watchdog must not acquire Termux global wake lock');
assert(!watchdog.includes('termux-notification '), 'legacy Phone Hands watchdog must not create Termux notifications');
assert(!watchdog.includes('android.settings'), 'legacy Phone Hands watchdog must not launch Android settings UI');

// Overlapping resurrection mechanisms are forbidden by default. Archaeology is
// allowed only through an explicit opt-in environment variable.
assert(installer.includes('HC_ENABLE_LEGACY_PHONE_HANDS_WATCHDOG'), 'legacy watchdog installer must remain explicit opt-in');
assert(installer.includes('decommission_termux_legacy.sh'), 'accidental legacy watchdog install must route to decommissioning');
assert(statusMenu.includes('HC_ENABLE_LEGACY_STATUS_MENU'), 'persistent Home Center status menu must remain explicit opt-in');
assert(overlayRecovery.includes('HC_ENABLE_LEGACY_OPERATOR_OVERLAY'), 'operator overlay recovery must remain explicit opt-in');

// Decommissioning is reversible and must preserve the break-glass shell while
// removing the known resurrection/UI sources.
for (const needle of [
  'Fortress-Graveyard/Termux/legacy-decommission-',
  '20-phone-hands-watchdog',
  '--cancel --job-id 6405',
  'termux-wake-unlock',
  'SYSTEM_ALERT_WINDOW deny',
  'pm disable-user --user 0',
  'fortress-sshd-guardian',
  'sshd',
]) {
  assert(decommission.includes(needle), `decommission campaign missing required policy marker: ${needle}`);
}

// The cleanup campaign must never kill the preserved SSH maintenance lane.
assert(decommission.includes('*fortress-sshd-guardian*|*sshd*) continue'), 'decommission campaign must explicitly exempt sshd and guardian');

if (failures.length) {
  console.error('TERMUX_CLEAN_SLATE_POLICY=FAIL');
  for (const failure of failures) console.error(`- ${failure}`);
  process.exit(1);
}

console.log('TERMUX_CLEAN_SLATE_POLICY=PASS');
