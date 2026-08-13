#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';

const patch = fs.readFileSync(new URL('./install_phone_hands_queue_starvation_fix.mjs', import.meta.url), 'utf8');
assert.ok(patch.includes('fileURLToPath(import.meta.url)'), 'patcher must resolve file URLs correctly on Windows');
assert.ok(patch.includes("rawSource.replace(/\\r\\n/g, '\\n')"), 'patcher must normalize CRLF before matching');
assert.ok(patch.includes("source.replace(/\\n/g, eol)"), 'patcher must restore the original line ending');
assert.ok(patch.includes(".limit(100).get()"), 'must inspect a bounded backlog larger than ten');
assert.ok(patch.includes("status:'failed', error:'expired_before_lease'"), 'expired commands must become terminal');
assert.ok(patch.includes("Number(x.expiresAtMs || 0) > now"), 'fresh commands must remain lease candidates');
assert.ok(patch.includes('expired.slice(0, 80)'), 'cleanup must stay bounded');
assert.ok(!patch.includes('delete('), 'cleanup must not permanently delete command evidence');
console.log('Phone Hands queue starvation contract tests passed');
