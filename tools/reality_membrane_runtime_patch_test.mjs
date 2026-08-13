#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';

const patcher=fs.readFileSync(new URL('./install_reality_membrane_runtime_patch.mjs',import.meta.url),'utf8');
const membrane=fs.readFileSync(new URL('../functions/reality_membrane.js',import.meta.url),'utf8');
const runtime=fs.readFileSync(new URL('../functions/reality_membrane_runtime.js',import.meta.url),'utf8');
const service=fs.readFileSync(new URL('../functions/reality_membrane_service.js',import.meta.url),'utf8');

for (const operation of ['reality.status','reality.sources','reality.capabilities','reality.observe','reality.history']) {
  assert.ok(patcher.includes(`'${operation}'`),`patcher must register ${operation}`);
  assert.ok(patcher.includes(`operation === '${operation}'`),`patcher must execute ${operation}`);
}
assert.ok(patcher.includes("require('./reality_membrane')"));
assert.ok(patcher.includes("require('./reality_membrane_runtime')"));
assert.ok(patcher.includes("require('./reality_membrane_service')"));
assert.ok(patcher.includes('REALITY_MEMBRANE_RUNTIME_START'));
assert.ok(patcher.includes('REALITY_MEMBRANE_PHONE_RUNNER_START'));
assert.ok(patcher.includes("operation:'phone_hands.enqueue'"));
assert.ok(patcher.includes("operation:'phone_hands.get'"));
assert.ok(patcher.includes("action:{action:'phone_shell'"));
assert.ok(patcher.includes("deviceId:'primary-phone'"));
assert.ok(patcher.includes("record.status === 'completed' || record.status === 'failed'"));
assert.ok(patcher.includes('write: false'));
assert.ok(!patcher.includes('OPENAI_API_KEY'));
assert.ok(!patcher.includes('cartesia'));
assert.ok(!patcher.includes('microphone'));
assert.ok(!patcher.includes('precise_location'));
assert.ok(membrane.includes("cost_policy:'zero-dollar-default'"));
assert.ok(membrane.includes("unknown_policy:'unknown-remains-unknown'"));
assert.ok(membrane.includes("fiction_policy:'observations_only_no_narrative_generation'"));
assert.ok(runtime.includes('open-meteo.com'));
assert.ok(runtime.includes('api.weather.gov'));
assert.ok(service.includes("default:['PUBLIC','DEVICE']"));
assert.ok(service.includes('fiction_generated:false'));
assert.ok(service.includes('HISTORY_RETENTION_MS = 72'));
assert.ok(service.includes('phone_command:phoneParsed.command'));

console.log('Reality Membrane runtime patch contract tests passed');
