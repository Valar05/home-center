#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const target = path.join(root, 'functions', 'home_center_mcp.js');
let source = fs.readFileSync(target, 'utf8');

const requireLine = "const realityMembrane = require('./reality_membrane');\n";
if (!source.includes(requireLine.trim())) {
  const anchor = "const voiceTierPolicy = require('./voice_tier_policy');\n";
  if (!source.includes(anchor)) throw new Error('reality require anchor not found');
  source = source.replace(anchor, anchor + requireLine);
}

const registryFn = source.indexOf('function driveOperationRegistry()');
if (registryFn < 0) throw new Error('driveOperationRegistry() not found');
const operationsAnchor = source.indexOf('    operations: {\n', registryFn);
if (operationsAnchor < 0) throw new Error('drive operation registry operations block not found');
const nextRegistryFn = source.indexOf('\nfunction ', operationsAnchor + 1);
const registryEnd = nextRegistryFn >= 0 ? nextRegistryFn : source.length;
const registrySlice = source.slice(registryFn, registryEnd);

const entries = [
  "      'reality.capabilities': {summary: 'Return the Reality Membrane contract, privacy classes, and zero-dollar policy.', write: false, requiredScopes: [], input: {}},\n",
  "      'reality.status': {summary: 'Return bounded Reality Membrane source/capability status without inventing unavailable observations.', write: false, requiredScopes: [], input: {}},\n",
  "      'reality.sources': {summary: 'List Reality Membrane source classes and their privacy/network policy.', write: false, requiredScopes: [], input: {}},\n",
];
let insertAt = operationsAnchor + '    operations: {\n'.length;
for (const entry of entries) {
  const name = entry.match(/'([^']+)'/)?.[1];
  if (name && !registrySlice.includes(`'${name}':`)) {
    source = source.slice(0, insertAt) + entry + source.slice(insertAt);
    insertAt += entry.length;
  }
}

const runAnchor = "  const registry = driveOperationRegistry();\n  if (!registry.operations[operation]) throw Object.assign(new Error('Unsupported drive_operation operation: ' + operation), {status: 400});\n";
const runAt = source.indexOf(runAnchor);
if (runAt < 0) throw new Error('drive operation execution anchor not found');
const branches = [
  "  if (operation === 'reality.capabilities') {\n    return {operation, registryVersion: registry.version, completed: true, result: realityMembrane.realityCapabilities()};\n  }\n",
  "  if (operation === 'reality.sources') {\n    return {operation, registryVersion: registry.version, completed: true, result: {contract:'home-center.reality.v1', sources:[{id:'home_center.runtime_clock',privacy:'PUBLIC',network:'none',cost:'zero',state:'available'},{id:'phone_hands',privacy:'DEVICE',network:'home_center_relay',cost:'zero',state:'adapter_pending'},{id:'weather.public_free',privacy:'PUBLIC',network:'required',cost:'zero_only',state:'adapter_pending'},{id:'sunrise_sunset',privacy:'PUBLIC',network:'optional',cost:'zero_only',state:'adapter_pending'}]}};\n  }\n",
  "  if (operation === 'reality.status') {\n    return {operation, registryVersion: registry.version, completed: true, result: {contract:'home-center.reality.v1', callable:true, accepted:false, observationPolicy:'unknown-remains-unknown', defaultPrivacy:['PUBLIC','DEVICE'], sources:{time:'available',phone:'adapter_pending',weather:'adapter_pending',daylight:'adapter_pending'}, note:'Status is capability truth only; it is not an observation packet.'}};\n  }\n",
];
let runInsertAt = runAt + runAnchor.length;
for (const branch of branches) {
  const name = branch.match(/operation === '([^']+)'/)?.[1];
  const tail = source.slice(runAt, runAt + runAnchor.length + 5000);
  if (name && !tail.includes(`operation === '${name}'`)) {
    source = source.slice(0, runInsertAt) + branch + source.slice(runInsertAt);
    runInsertAt += branch.length;
  }
}

fs.writeFileSync(target, source);
console.log('Reality Membrane registry/status/capabilities/sources patch applied');
