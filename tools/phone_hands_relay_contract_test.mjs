#!/usr/bin/env node
import fs from 'node:fs';
const relay=fs.readFileSync('functions/phone_hands_relay.js','utf8');
const patcher=fs.readFileSync('tools/apply_phone_hands_relay_wiring.mjs','utf8');
const agent=fs.readFileSync('tools/android_phone_home_center_relay.py','utf8');
const requiredRelay=['command_center.phone_hands.devices','command_center.phone_hands.enqueue','command_center.phone_hands.get','devicePull','deviceComplete','registerDevice'];
for (const s of requiredRelay) if (!relay.includes(s)) throw new Error('relay contract missing '+s);
for (const s of ["require('./phone_hands_relay')",'registerCommandCenterPhoneTools','exports.phoneHandsRelay']) if (!patcher.includes(s)) throw new Error('wiring patch missing '+s);
for (const s of ['termuxTokenRefresh','android_phone_hands_bridge','dungeon_run','local_ask','/pull','/complete']) if (!agent.includes(s)) throw new Error('phone agent contract missing '+s);
if (relay.includes('deviceToken:'+' token')) throw new Error('device token must not be returned by MCP');
console.log('phone hands relay contract: PASS');
