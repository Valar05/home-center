#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';

const relay = fs.readFileSync(new URL('../functions/phone_hands_relay.js', import.meta.url), 'utf8');
assert.ok(relay.includes(".limit(100).get()"), 'must inspect a bounded backlog larger than ten');
assert.ok(relay.includes("status:'failed', error:'expired_before_lease'"), 'expired commands must become terminal evidence');
assert.ok(relay.includes("Number(x.expiresAtMs || 0) > now"), 'fresh commands must remain lease candidates');
assert.ok(relay.includes('expired.slice(0, 80)'), 'cleanup must remain bounded');
assert.ok(!relay.includes("collection(COLLECTIONS.commands).doc(command.commandId).delete"), 'expired command evidence must not be deleted');
console.log('Phone Hands queue starvation contract tests passed');
