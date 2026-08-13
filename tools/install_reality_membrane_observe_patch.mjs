#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const mcpTarget = path.join(root, 'functions', 'home_center_mcp.js');
const coreTarget = path.join(root, 'functions', 'reality_membrane.js');
let source = fs.readFileSync(mcpTarget, 'utf8');
let core = fs.readFileSync(coreTarget, 'utf8');

const runtimeRequire = "const realityRuntime = require('./reality_membrane_runtime');\n";
if (!source.includes(runtimeRequire.trim())) {
  const anchors = ["const realityMembrane = require('./reality_membrane');\n", "const voiceTierPolicy = require('./voice_tier_policy');\n"];
  const anchor = anchors.find((candidate) => source.includes(candidate));
  if (!anchor) throw new Error('Reality runtime require anchor not found');
  source = source.replace(anchor, anchor + runtimeRequire);
}

const registryFn = source.indexOf('function driveOperationRegistry()');
if (registryFn < 0) throw new Error('driveOperationRegistry() not found');
const operationsAnchor = source.indexOf('    operations: {\n', registryFn);
if (operationsAnchor < 0) throw new Error('drive operation registry operations block not found');
const nextRegistryFn = source.indexOf('\nfunction ', operationsAnchor + 1);
const registryEnd = nextRegistryFn >= 0 ? nextRegistryFn : source.length;
let registrySlice = source.slice(registryFn, registryEnd);
const entries = [
  "      'reality.observe': {summary: 'Return a bounded provenance-bearing Inner Fortress reality packet using actual clock, free public weather/daylight, and authorized Phone Hands observations.', write: false, requiredScopes: [], input: {include: 'optional string[]', requestId: 'optional stable id', phoneTimeoutMs: 'optional number', persist: 'optional boolean', timePolicy: 'optional string', sceneTime: 'optional string', lastSceneCheckpoint: 'optional string', elapsedWorldTimeMs: 'optional number'}},\n",
  "      'reality.history': {summary: 'Return bounded Reality Membrane transition history and optional recent snapshots.', write: false, requiredScopes: [], input: {since: 'optional timestamp', sinceMs: 'optional number', limit: 'optional number', includeSnapshots: 'optional boolean'}},\n",
  "      'reality.events': {summary: 'Return bounded Reality Membrane transition events without narrative transformation.', write: false, requiredScopes: [], input: {since: 'optional timestamp', sinceMs: 'optional number', limit: 'optional number'}},\n",
];
let insertAt = operationsAnchor + '    operations: {\n'.length;
for (const entry of entries) {
  const name = entry.match(/'([^']+)'/)?.[1];
  registrySlice = source.slice(registryFn, source.indexOf('\nfunction ', operationsAnchor + 1) >= 0 ? source.indexOf('\nfunction ', operationsAnchor + 1) : source.length);
  if (name && !registrySlice.includes(`'${name}':`)) {
    source = source.slice(0, insertAt) + entry + source.slice(insertAt);
    insertAt += entry.length;
  }
}

const staticBranches = [
  "  if (operation === 'reality.capabilities') {\n    return {operation, registryVersion: registry.version, completed: true, result: realityMembrane.realityCapabilities()};\n  }\n",
  "  if (operation === 'reality.sources') {\n    return {operation, registryVersion: registry.version, completed: true, result: {contract:'home-center.reality.v1', sources:[{id:'home_center.runtime_clock',privacy:'PUBLIC',network:'none',cost:'zero',state:'available'},{id:'phone_hands',privacy:'DEVICE',network:'home_center_relay',cost:'zero',state:'adapter_pending'},{id:'weather.public_free',privacy:'PUBLIC',network:'required',cost:'zero_only',state:'adapter_pending'},{id:'sunrise_sunset',privacy:'PUBLIC',network:'optional',cost:'zero_only',state:'adapter_pending'}]}};\n  }\n",
  "  if (operation === 'reality.status') {\n    return {operation, registryVersion: registry.version, completed: true, result: {contract:'home-center.reality.v1', callable:true, accepted:false, observationPolicy:'unknown-remains-unknown', defaultPrivacy:['PUBLIC','DEVICE'], sources:{time:'available',phone:'adapter_pending',weather:'adapter_pending',daylight:'adapter_pending'}, note:'Status is capability truth only; it is not an observation packet.'}};\n  }\n",
];
for (const branch of staticBranches) source = source.replace(branch, '');

const runAnchor = "  const registry = driveOperationRegistry();\n  if (!registry.operations[operation]) throw Object.assign(new Error('Unsupported drive_operation operation: ' + operation), {status: 400});\n";
const runAt = source.indexOf(runAnchor);
if (runAt < 0) throw new Error('drive operation execution anchor not found');
const runtimeBranch = "  if (operation.startsWith('reality.')) {\n    const realityArgs = args && args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? {...args.args} : {...(args || {})};\n    delete realityArgs.operation; delete realityArgs.type; delete realityArgs.toolName; delete realityArgs.args;\n    return {operation, registryVersion: registry.version, completed: true, result: await realityRuntime.runRealityOperation({operation, admin, user, args: realityArgs})};\n  }\n";
const runTail = source.slice(runAt, runAt + runAnchor.length + 8000);
if (!runTail.includes("operation.startsWith('reality.')")) {
  const runtimeInsertAt = runAt + runAnchor.length;
  source = source.slice(0, runtimeInsertAt) + runtimeBranch + source.slice(runtimeInsertAt);
}

const replacements = [
  ["temperature_f:make('weather.temperature_f',finite(payload.temperature_f),'F')", "temperature_f:make('weather.temperature_f',payload.temperature_f==null?undefined:finite(payload.temperature_f),'F')"],
  ["feels_like_f:make('weather.feels_like_f',finite(payload.feels_like_f),'F')", "feels_like_f:make('weather.feels_like_f',payload.feels_like_f==null?undefined:finite(payload.feels_like_f),'F')"],
  ["precipitation:make('weather.precipitation',payload.precipitation??null,null)", "precipitation:make('weather.precipitation',payload.precipitation===undefined?undefined:payload.precipitation,null)"],
  ["precipitation_probability_pct:make('weather.precipitation_probability_pct',finite(payload.precipitation_probability_pct),'%')", "precipitation_probability_pct:make('weather.precipitation_probability_pct',payload.precipitation_probability_pct==null?undefined:finite(payload.precipitation_probability_pct),'%')"],
  ["humidity_pct:make('weather.humidity_pct',finite(payload.humidity_pct),'%')", "humidity_pct:make('weather.humidity_pct',payload.humidity_pct==null?undefined:finite(payload.humidity_pct),'%')"],
  ["wind_mph:make('weather.wind_mph',finite(payload.wind_mph),'mph')", "wind_mph:make('weather.wind_mph',payload.wind_mph==null?undefined:finite(payload.wind_mph),'mph')"],
  ["alert:make('weather.alert',payload.alert??null,null)", "alert:make('weather.alert',payload.alert===undefined?undefined:payload.alert,null)"],
  ["battery_pct:make('phone.battery_pct',finite(payload.battery_pct),'%')", "battery_pct:make('phone.battery_pct',payload.battery_pct==null?undefined:finite(payload.battery_pct),'%')"],
];
for (const [before, after] of replacements) {
  if (core.includes(before)) core = core.replace(before, after);
}

fs.writeFileSync(mcpTarget, source);
fs.writeFileSync(coreTarget, core);
console.log('Reality Membrane observe/history/events runtime patch applied');
