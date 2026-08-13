#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';
const require = createRequire(import.meta.url);

const patcher = fs.readFileSync(new URL('./install_reality_membrane_runtime_patch.mjs', import.meta.url), 'utf8');
const serviceSource = fs.readFileSync(new URL('../functions/reality_membrane_service.js', import.meta.url), 'utf8');
const service = require('../functions/reality_membrane_service');

for (const operation of ['reality.status', 'reality.observe', 'reality.history', 'reality.sources', 'reality.capabilities']) {
  assert.ok(service.operationEntries()[operation], `service must register ${operation}`);
  assert.ok(service.CALLABLE_OPERATIONS.includes(operation), `service must mark ${operation} callable`);
}
assert.ok(patcher.includes("require('./reality_membrane_service')"));
assert.ok(patcher.includes('...realityMembraneService.operationEntries()'));
assert.ok(patcher.includes('realityMembraneService.runOperation'));
assert.ok(patcher.includes("callCommandCenter: async (commandCenterOperation, commandCenterArgs)"));
assert.ok(patcher.includes("args: {operation: commandCenterOperation, args: commandCenterArgs}"));
assert.ok(!patcher.includes("callable:true"));
assert.ok(!patcher.includes('OPENAI_API_KEY'));
assert.ok(!patcher.includes('realityMembrane.realityCapabilities'));

for (const source of [patcher, serviceSource]) {
  assert.ok(!source.includes('temporary promotional credits'));
  assert.ok(!source.includes('CARTESIA_API_KEY'));
  assert.ok(!source.includes('OPENAI_API_KEY'));
}
assert.ok(serviceSource.includes('api.open-meteo.com'));
assert.ok(serviceSource.includes('api.weather.gov'));
assert.ok(serviceSource.includes("paid_service_activated: false"));
assert.ok(serviceSource.includes("fiction_generated: false"));
assert.ok(serviceSource.includes("coordinates_returned: false"));
assert.ok(serviceSource.includes("telemetry_policy: 'transition_events_only'"));
assert.ok(serviceSource.includes("location.scope"));
assert.ok(!serviceSource.includes('message bodies'));

console.log('Reality Membrane runtime patch contract tests passed');
