import {getQuickJS} from 'quickjs-emscripten';

export const FOUNDRY_SCRIPT_VERSION = 'foundry-js.v1';
export const FOUNDRY_SCRIPT_MAX_BYTES = 256 * 1024;
export const FOUNDRY_SCRIPT_MEMORY_BYTES = 64 * 1024 * 1024;
export const FOUNDRY_SCRIPT_TIMEOUT_MS = 5000;
export const FOUNDRY_SCRIPT_MAX_OPERATIONS = 4096;
export const FOUNDRY_SCRIPT_MAX_NOTES = 100;

const API = Object.freeze({
  asset: ['inspect'],
  scene: ['createGroup', 'createBox', 'createCylinder', 'createProfileExtrusion', 'createSectionLoft', 'transform', 'rename', 'reparent', 'remove', 'instance', 'array', 'mirror', 'separate'],
  mesh: ['recalculateNormals', 'weld', 'boolean'],
  material: ['create', 'assign'],
  rig: ['addBone', 'renameBone', 'orientBone', 'reparentBone', 'attachRigid'],
  animation: ['trim', 'retime', 'setKey', 'deleteKey', 'loop', 'rootMotion'],
  review: ['fixedViews'],
  validation: ['assert', 'productionBudget'],
});

function fail(code, message, details = {}) {
  const error = new Error(message);
  error.code = code;
  error.status = 400;
  error.details = details;
  return error;
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === 'object') return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  return value;
}

function prelude(parameters, seed) {
  const api = JSON.stringify(API);
  return `
"use strict";
const __ops = [];
const __notes = [];
const __api = ${api};
const parameters = Object.freeze(${JSON.stringify(stable(parameters || {}))});
let __seed = ${Number(seed) >>> 0};
const __random = () => { __seed = ((__seed * 1664525) + 1013904223) >>> 0; return __seed / 4294967296; };
Math.random = __random;
const __push = (namespace, operation, args) => {
  if (__ops.length >= 4096) throw new Error("foundry.limit.operations");
  __ops.push({namespace, operation, args: Array.from(args)});
};
const foundry = {};
for (const [namespace, methods] of Object.entries(__api)) {
  const target = {};
  for (const operation of methods) target[operation] = (...args) => __push(namespace, operation, args);
  foundry[namespace] = Object.freeze(target);
}
foundry.note = (message, details = null) => {
  if (__notes.length >= 100) throw new Error("foundry.limit.notes");
  __notes.push({message: String(message).slice(0, 500), details});
};
Object.freeze(foundry);
globalThis.fetch = undefined;
globalThis.XMLHttpRequest = undefined;
globalThis.WebSocket = undefined;
globalThis.Worker = undefined;
globalThis.process = undefined;
globalThis.require = undefined;
globalThis.module = undefined;
globalThis.Date = undefined;
globalThis.eval = undefined;
globalThis.Function = undefined;
`;
}

export async function executeFoundryScript({version, text, parameters = {}, seed = 1, timeoutMs = FOUNDRY_SCRIPT_TIMEOUT_MS, memoryBytes = FOUNDRY_SCRIPT_MEMORY_BYTES}) {
  if (version !== FOUNDRY_SCRIPT_VERSION) throw fail('foundry.script.unsupported_version', `Unsupported Foundry script version: ${version || 'missing'}`, {supported: [FOUNDRY_SCRIPT_VERSION]});
  if (typeof text !== 'string' || !text.trim()) throw fail('foundry.script.required', 'A non-empty Foundry script is required.');
  const byteLength = Buffer.byteLength(text, 'utf8');
  if (byteLength > FOUNDRY_SCRIPT_MAX_BYTES) throw fail('foundry.limit.script', 'Foundry script exceeds 256 KiB.', {byteLength, max: FOUNDRY_SCRIPT_MAX_BYTES});

  const QuickJS = await getQuickJS();
  const runtime = QuickJS.newRuntime();
  runtime.setMemoryLimit(Math.max(8 * 1024 * 1024, Math.min(Number(memoryBytes) || FOUNDRY_SCRIPT_MEMORY_BYTES, FOUNDRY_SCRIPT_MEMORY_BYTES)));
  runtime.setMaxStackSize(2 * 1024 * 1024);
  const deadline = Date.now() + Math.max(50, Math.min(Number(timeoutMs) || FOUNDRY_SCRIPT_TIMEOUT_MS, FOUNDRY_SCRIPT_TIMEOUT_MS));
  runtime.setInterruptHandler(() => Date.now() > deadline);
  const context = runtime.newContext();
  try {
    const wrapped = `(() => { ${prelude(parameters, seed)}; const __user = () => {\n${text}\n}; __user(); return JSON.stringify({operations: __ops, notes: __notes}); })()`;
    const evaluated = context.evalCode(wrapped, 'foundry-script.js');
    if (evaluated.error) {
      const dumped = context.dump(evaluated.error);
      evaluated.error.dispose();
      const message = String(dumped && (dumped.message || dumped) || 'Foundry script failed.');
      if (/interrupted/i.test(message)) throw fail('foundry.script.timeout', 'Foundry script exceeded its bounded planning time.');
      if (/out of memory/i.test(message)) throw fail('foundry.script.memory_limit', 'Foundry script exceeded its bounded memory.');
      if (/foundry\.limit\.operations/.test(message)) throw fail('foundry.limit.operations', 'Foundry script emitted too many operations.');
      throw fail('foundry.script.failed', message.slice(0, 1200));
    }
    const json = context.dump(evaluated.value);
    evaluated.value.dispose();
    const parsed = JSON.parse(json);
    if (!parsed || !Array.isArray(parsed.operations) || !Array.isArray(parsed.notes)) throw fail('foundry.script.invalid_result', 'Foundry script did not produce a bounded operation plan.');
    return {scriptVersion: FOUNDRY_SCRIPT_VERSION, operationCount: parsed.operations.length, operations: parsed.operations, notes: parsed.notes};
  } finally {
    context.dispose();
    runtime.dispose();
  }
}

export function foundryScriptApi() {
  return API;
}
