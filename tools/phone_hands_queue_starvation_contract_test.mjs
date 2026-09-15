import fs from 'node:fs'; import assert from 'node:assert/strict';
const s=fs.readFileSync('functions/phone_hands_relay.js','utf8');
assert.doesNotMatch(s,/where\('status','==','queued'\)\.limit\(10\)\.get\(\)/);
for (const x of ['PHONE_QUEUE_SCAN_LIMIT = 100','PHONE_QUEUE_DRAIN_ROUNDS = 20','expired_before_lease','lease_expired_before_completion']) assert.ok(s.includes(x),x);
assert.ok(s.includes('for (let round = 0; round < PHONE_QUEUE_DRAIN_ROUNDS; round += 1)'));
console.log('phone hands queue starvation contract: ok');
