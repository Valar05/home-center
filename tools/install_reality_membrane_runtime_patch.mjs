#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const target = path.join(root, 'functions', 'home_center_mcp.js');
let source = fs.readFileSync(target, 'utf8');

const legacyRequire = "const realityMembrane = require('./reality_membrane');\n";
source = source.replace(legacyRequire, '');
const requireLine = "const realityMembraneService = require('./reality_membrane_service');\n";
if (!source.includes(requireLine.trim())) {
  const anchor = "const voiceTierPolicy = require('./voice_tier_policy');\n";
  if (!source.includes(anchor)) throw new Error('Reality Membrane require anchor not found');
  source = source.replace(anchor, anchor + requireLine);
}

const legacyEntries = [
  "      'reality.capabilities': {summary: 'Return the Reality Membrane contract, privacy classes, and zero-dollar policy.', write: false, requiredScopes: [], input: {}},\n",
  "      'reality.status': {summary: 'Return bounded Reality Membrane source/capability status without inventing unavailable observations.', write: false, requiredScopes: [], input: {}},\n",
  "      'reality.sources': {summary: 'List Reality Membrane source classes and their privacy/network policy.', write: false, requiredScopes: [], input: {}},\n",
];
for (const entry of legacyEntries) source = source.replace(entry, '');

const legacyBranches = [
  "  if (operation === 'reality.capabilities') {\n    return {operation, registryVersion: registry.version, completed: true, result: realityMembrane.realityCapabilities()};\n  }\n",
  "  if (operation === 'reality.sources') {\n    return {operation, registryVersion: registry.version, completed: true, result: {contract:'home-center.reality.v1', sources:[{id:'home_center.runtime_clock',privacy:'PUBLIC',network:'none',cost:'zero',state:'available'},{id:'phone_hands',privacy:'DEVICE',network:'home_center_relay',cost:'zero',state:'adapter_pending'},{id:'weather.public_free',privacy:'PUBLIC',network:'required',cost:'zero_only',state:'adapter_pending'},{id:'sunrise_sunset',privacy:'PUBLIC',network:'optional',cost:'zero_only',state:'adapter_pending'}]}};\n  }\n",
  "  if (operation === 'reality.status') {\n    return {operation, registryVersion: registry.version, completed: true, result: {contract:'home-center.reality.v1', callable:true, accepted:false, observationPolicy:'unknown-remains-unknown', defaultPrivacy:['PUBLIC','DEVICE'], sources:{time:'available',phone:'adapter_pending',weather:'adapter_pending',daylight:'adapter_pending'}, note:'Status is capability truth only; it is not an observation packet.'}};\n  }\n",
];
for (const branch of legacyBranches) source = source.replace(branch, '');

const registryFn = source.indexOf('function driveOperationRegistry()');
if (registryFn < 0) throw new Error('driveOperationRegistry() not found');
const operationsAnchor = source.indexOf('    operations: {\n', registryFn);
if (operationsAnchor < 0) throw new Error('drive operation registry operations block not found');
const spreadLine = '      ...realityMembraneService.operationEntries(),\n';
const nextRegistryFn = source.indexOf('\nfunction ', operationsAnchor + 1);
const registryEnd = nextRegistryFn >= 0 ? nextRegistryFn : source.length;
if (!source.slice(registryFn, registryEnd).includes(spreadLine.trim())) {
  const insertAt = operationsAnchor + '    operations: {\n'.length;
  source = source.slice(0, insertAt) + spreadLine + source.slice(insertAt);
}

const argsAnchor = "  const operationArgs = args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : {...args};\n  delete operationArgs.operation;\n  delete operationArgs.type;\n  delete operationArgs.toolName;\n  delete operationArgs.args;\n";
const routeBlock = "  if (realityMembraneService.operationEntries()[operation]) {\n    const result = await realityMembraneService.runOperation({\n      operation, admin, user, args: operationArgs,\n      callCommandCenter: async (commandCenterOperation, commandCenterArgs) => {\n        const response = await commandCenterOperationRunOperation({\n          google, admin, googleClientId, googleClientSecret, extra,\n          args: {operation: commandCenterOperation, args: commandCenterArgs},\n        });\n        return response.result;\n      },\n    });\n    return {operation, registryVersion: registry.version, completed: true, result};\n  }\n";
if (!source.includes(routeBlock.trim())) {
  const at = source.indexOf(argsAnchor, source.indexOf('async function driveOperationRunOperation'));
  if (at < 0) throw new Error('drive operation argument normalization anchor not found');
  const insertAt = at + argsAnchor.length;
  source = source.slice(0, insertAt) + routeBlock + source.slice(insertAt);
}

fs.writeFileSync(target, source);
console.log('Reality Membrane service wired into canonical drive_operation registry');
