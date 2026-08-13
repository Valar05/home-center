#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root=path.resolve(path.dirname(new URL(import.meta.url).pathname),'..');
const target=path.join(root,'functions','home_center_mcp.js');
let source=fs.readFileSync(target,'utf8');

const requireAnchor="const voiceTierPolicy = require('./voice_tier_policy');\n";
if (!source.includes(requireAnchor)) throw new Error('Reality Membrane require anchor not found');
for (const line of [
  "const realityMembrane = require('./reality_membrane');\n",
  "const realityMembraneRuntime = require('./reality_membrane_runtime');\n",
  "const realityMembraneService = require('./reality_membrane_service');\n",
]) {
  if (!source.includes(line.trim())) source=source.replace(requireAnchor,requireAnchor+line);
}

const driveRunIndex=source.indexOf('async function driveOperationRunOperation(');
if (driveRunIndex < 0) throw new Error('driveOperationRunOperation() not found');
const driveRunBodyStart=source.indexOf(') {',driveRunIndex);
if (driveRunBodyStart < 0) throw new Error('driveOperationRunOperation() signature terminator not found');
const driveRunHeader=source.slice(driveRunIndex,driveRunBodyStart+3);
for (const required of ['google','admin','googleClientId','googleClientSecret','extra','args']) {
  if (!new RegExp(`\\b${required}\\b`).test(driveRunHeader)) throw new Error(`driveOperationRunOperation() does not expose required context: ${required}`);
}

const helperStart='// REALITY_MEMBRANE_PHONE_RUNNER_START\n';
const helperEnd='// REALITY_MEMBRANE_PHONE_RUNNER_END\n';
const helperBlock=`${helperStart}async function homeCenterRealityPhoneCommandRunner({google,admin,googleClientId,googleClientSecret,extra,commandId,command,ttlMs=45000}) {\n  const enqueued=await commandCenterOperationRunOperation({google,admin,googleClientId,googleClientSecret,extra,args:{operation:'phone_hands.enqueue',args:{idempotencyKey:commandId,commandId,deviceId:'primary-phone',ttlMs,action:{action:'phone_shell',command}}}});\n  const queued=enqueued && enqueued.result || {};\n  const actualCommandId=safeText(queued.commandId,180) || commandId;\n  const deadline=Date.now()+Math.max(5000,Math.min(Number(ttlMs)||45000,60000));\n  while (Date.now() < deadline) {\n    await new Promise((resolve)=>setTimeout(resolve,750));\n    const checked=await commandCenterOperationRunOperation({google,admin,googleClientId,googleClientSecret,extra,args:{operation:'phone_hands.get',args:{commandId:actualCommandId}}});\n    const record=checked && checked.result || {};\n    if (record.status === 'completed' || record.status === 'failed') return record;\n  }\n  return {commandId:actualCommandId,deviceId:'primary-phone',status:'timeout',error:'phone_observation_timeout',result:null};\n}\n${helperEnd}`;
const existingHelperStart=source.indexOf(helperStart);
if (existingHelperStart >= 0) {
  const existingHelperEnd=source.indexOf(helperEnd,existingHelperStart);
  if (existingHelperEnd < 0) throw new Error('Reality Membrane helper sentinel is incomplete');
  source=source.slice(0,existingHelperStart)+helperBlock+source.slice(existingHelperEnd+helperEnd.length);
} else {
  const registryAnchor='function driveOperationRegistry()';
  const registryAt=source.indexOf(registryAnchor);
  if (registryAt < 0) throw new Error('driveOperationRegistry() not found');
  source=source.slice(0,registryAt)+helperBlock+'\n'+source.slice(registryAt);
}

const registryFn=source.indexOf('function driveOperationRegistry()');
const operationsAnchor=source.indexOf('    operations: {\n',registryFn);
if (registryFn < 0 || operationsAnchor < 0) throw new Error('drive operation registry block not found');
const nextRegistryFn=source.indexOf('\nfunction ',operationsAnchor+1);
const registryEnd=nextRegistryFn >= 0 ? nextRegistryFn : source.length;
let registrySlice=source.slice(registryFn,registryEnd);
const entries=[
  "      'reality.capabilities': {summary: 'Return the Reality Membrane contract, privacy classes, time policies, and zero-dollar law.', write: false, requiredScopes: [], input: {}},\n",
  "      'reality.status': {summary: 'Return owner-scoped Reality Membrane capability and last-observation status without fabricating values.', write: false, requiredScopes: [], input: {}},\n",
  "      'reality.sources': {summary: 'List Reality Membrane sources, privacy classes, network dependence, and excluded invasive data.', write: false, requiredScopes: [], input: {}},\n",
  "      'reality.observe': {summary: 'Return one compact owner-scoped current reality packet with provenance, staleness, accessibility summary, and no fiction.', write: false, requiredScopes: [], input: {includePhone: 'optional boolean default true', timeZone: 'optional IANA timezone'}},\n",
  "      'reality.history': {summary: 'Return bounded owner-scoped Reality Membrane transition history; default and maximum retention is 72 hours.', write: false, requiredScopes: [], input: {limit: 'optional number maximum 100', windowHours: 'optional number maximum 72'}},\n",
];
let insertAt=operationsAnchor+'    operations: {\n'.length;
for (const entry of entries) {
  const name=entry.match(/'([^']+)'/)?.[1];
  if (name && !registrySlice.includes(`'${name}':`)) {
    source=source.slice(0,insertAt)+entry+source.slice(insertAt);
    insertAt+=entry.length;
    registrySlice+=entry;
  }
}

const oldBranches=[
  "  if (operation === 'reality.capabilities') {\n    return {operation, registryVersion: registry.version, completed: true, result: realityMembrane.realityCapabilities()};\n  }\n",
  "  if (operation === 'reality.sources') {\n    return {operation, registryVersion: registry.version, completed: true, result: {contract:'home-center.reality.v1', sources:[{id:'home_center.runtime_clock',privacy:'PUBLIC',network:'none',cost:'zero',state:'available'},{id:'phone_hands',privacy:'DEVICE',network:'home_center_relay',cost:'zero',state:'adapter_pending'},{id:'weather.public_free',privacy:'PUBLIC',network:'required',cost:'zero_only',state:'adapter_pending'},{id:'sunrise_sunset',privacy:'PUBLIC',network:'optional',cost:'zero_only',state:'adapter_pending'}]}};\n  }\n",
  "  if (operation === 'reality.status') {\n    return {operation, registryVersion: registry.version, completed: true, result: {contract:'home-center.reality.v1', callable:true, accepted:false, observationPolicy:'unknown-remains-unknown', defaultPrivacy:['PUBLIC','DEVICE'], sources:{time:'available',phone:'adapter_pending',weather:'adapter_pending',daylight:'adapter_pending'}, note:'Status is capability truth only; it is not an observation packet.'}};\n  }\n",
];
for (const block of oldBranches) source=source.replace(block,'');

const runAnchor="  const registry = driveOperationRegistry();\n  if (!registry.operations[operation]) throw Object.assign(new Error('Unsupported drive_operation operation: ' + operation), {status: 400});\n";
const runAt=source.indexOf(runAnchor);
if (runAt < 0) throw new Error('drive operation execution anchor not found');
const runtimeStart='  // REALITY_MEMBRANE_RUNTIME_START\n';
const runtimeEnd='  // REALITY_MEMBRANE_RUNTIME_END\n';
const runtimeBlock=`${runtimeStart}  if (operation === 'reality.capabilities') {\n    return {operation,registryVersion:registry.version,completed:true,result:realityMembrane.realityCapabilities()};\n  }\n  if (operation === 'reality.sources') {\n    return {operation,registryVersion:registry.version,completed:true,result:realityMembraneService.sources()};\n  }\n  if (operation === 'reality.status') {\n    const realityContext=await requireCreditGatedContext({google,admin,googleClientId,googleClientSecret,extra,surface:'reality.status'});\n    return {operation,registryVersion:registry.version,completed:true,result:await realityMembraneService.status({admin,user:realityContext.user})};\n  }\n  if (operation === 'reality.history') {\n    const realityContext=await requireCreditGatedContext({google,admin,googleClientId,googleClientSecret,extra,surface:'reality.history'});\n    const realityArgs=args && args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : args;\n    return {operation,registryVersion:registry.version,completed:true,result:await realityMembraneService.history({admin,user:realityContext.user,args:realityArgs})};\n  }\n  if (operation === 'reality.observe') {\n    const realityContext=await requireCreditGatedContext({google,admin,googleClientId,googleClientSecret,extra,surface:'reality.observe'});\n    const realityArgs=args && args.args && typeof args.args === 'object' && !Array.isArray(args.args) ? args.args : args;\n    const result=await realityMembraneService.observe({admin,user:realityContext.user,args:realityArgs,phoneCommandRunner:realityArgs.includePhone === false ? null : (request)=>homeCenterRealityPhoneCommandRunner({google,admin,googleClientId,googleClientSecret,extra,...request})});\n    return {operation,registryVersion:registry.version,completed:true,result};\n  }\n${runtimeEnd}`;
const existingRuntimeStart=source.indexOf(runtimeStart);
if (existingRuntimeStart >= 0) {
  const existingRuntimeEnd=source.indexOf(runtimeEnd,existingRuntimeStart);
  if (existingRuntimeEnd < 0) throw new Error('Reality Membrane runtime sentinel is incomplete');
  source=source.slice(0,existingRuntimeStart)+runtimeBlock+source.slice(existingRuntimeEnd+runtimeEnd.length);
} else {
  const at=source.indexOf(runAnchor)+runAnchor.length;
  source=source.slice(0,at)+runtimeBlock+source.slice(at);
}

fs.writeFileSync(target,source);
console.log('Reality Membrane status/sources/capabilities/observe/history wired into canonical drive_operation');
