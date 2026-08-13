#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';

const patch = fs.readFileSync(new URL('./install_phone_hands_queue_starvation_fix.mjs', import.meta.url), 'utf8');
assert.ok(patch.includes(".limit(100).get()"), 'must inspect a bounded backlog larger than ten');
assert.ok(patch.includes("expired.slice(0, 80)"), 'cleanup must stay bounded');
assert.ok(patch.includes("status:'failed', error:'expired_before_lease'"), 'expired commands must become terminal');
assert.ok(patch.includes("current.status !== 'queued'"), 'cleanup and leasing must re-read exact command state');
assert.ok(patch.includes("Number(current.expiresAtMs || 0) > now"), 'cleanup must not fail a command that was refreshed');
assert.ok(patch.includes("Number(current.expiresAtMs || 0) <= now"), 'lease CAS must reject newly expired commands');
assert.ok(patch.includes("for (const candidate of candidates)"), 'raced candidates must fall through to the next fresh command');
assert.ok(patch.match(/runTransaction/g).length >= 2, 'expiry and leasing both require transactions');
assert.ok(!patch.includes('delete('), 'cleanup must not permanently delete command evidence');
assert.ok(!patch.includes('batch.commit()'), 'non-CAS batch expiry is forbidden');
console.log('Phone Hands queue starvation patch contract tests passed');
