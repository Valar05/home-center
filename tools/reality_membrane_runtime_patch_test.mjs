#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';

const patcher = fs.readFileSync(new URL('./install_reality_membrane_runtime_patch.mjs', import.meta.url), 'utf8');
const membrane = fs.readFileSync(new URL('../functions/reality_membrane.js', import.meta.url), 'utf8');

assert.ok(patcher.includes('fileURLToPath(import.meta.url)'), 'patcher must resolve file URLs correctly on Windows');
assert.ok(patcher.includes("rawSource.replace(/\\r\\n/g, '\\n')"), 'patcher must normalize CRLF before matching');
assert.ok(patcher.includes("source.replace(/\\n/g, eol)"), 'patcher must restore the original line ending');
for (const operation of ['reality.status','reality.sources','reality.capabilities']) {
  assert.ok(patcher.includes(`'${operation}'`), `patcher must register ${operation}`);
  assert.ok(patcher.includes(`operation === '${operation}'`), `patcher must execute ${operation}`);
}
assert.ok(patcher.includes("require('./reality_membrane')"));
assert.ok(patcher.includes('write: false'));
assert.ok(patcher.includes("observationPolicy:'unknown-remains-unknown'"));
assert.ok(patcher.includes("defaultPrivacy:['PUBLIC','DEVICE']"));
assert.ok(!patcher.includes('OPENAI_API_KEY'));
assert.ok(!patcher.includes('paid'));
assert.ok(membrane.includes("cost_policy:'zero-dollar-default'"));
assert.ok(membrane.includes("unknown_policy:'unknown-remains-unknown'"));
console.log('Reality Membrane runtime patch contract tests passed');
