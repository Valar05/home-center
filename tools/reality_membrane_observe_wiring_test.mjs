#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';

const patcher = fs.readFileSync(new URL('./install_reality_membrane_observe_patch.mjs', import.meta.url),'utf8');
for (const operation of ['reality.observe','reality.history','reality.events']) {
  assert.ok(patcher.includes(`'${operation}'`),`patcher must register ${operation}`);
}
assert.ok(patcher.includes("operation.startsWith('reality.')"));
assert.ok(patcher.includes('realityRuntime.runRealityOperation'));
assert.ok(patcher.includes('write: false'));
assert.ok(patcher.includes("payload.battery_pct==null?undefined"));
assert.ok(patcher.includes("payload.temperature_f==null?undefined"));
assert.ok(!patcher.includes('new sidecar'));
assert.ok(!patcher.includes('OPENAI_API_KEY'));
console.log('Reality Membrane observe wiring tests passed');
