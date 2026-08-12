#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const target = path.join(root, 'functions', 'home_center_mcp.js');
let source = fs.readFileSync(target, 'utf8');

const registryEntry = "      'time.now': {summary: 'Return the current Home Center runtime time.', write: false, requiredScopes: [], input: {}},\n";
const runtimeBranch = "  if (operation === 'time.now') {\n    const now = new Date();\n    return {operation, registryVersion: registry.version, completed: true, result: {utcIso: now.toISOString(), unixMs: now.getTime()}};\n  }\n";

const registryFn = source.indexOf('function driveOperationRegistry()');
if (registryFn < 0) throw new Error('driveOperationRegistry() not found');
const operationsAnchor = source.indexOf('    operations: {\n', registryFn);
if (operationsAnchor < 0) throw new Error('drive operation registry operations block not found');
const nextRegistryFn = source.indexOf('\nfunction ', operationsAnchor + 1);
const registryEnd = nextRegistryFn >= 0 ? nextRegistryFn : source.length;
const registrySlice = source.slice(registryFn, registryEnd);
if (!registrySlice.includes("'time.now':")) {
  const insertAt = operationsAnchor + '    operations: {\n'.length;
  source = source.slice(0, insertAt) + registryEntry + source.slice(insertAt);
}

const runAnchor = "  const registry = driveOperationRegistry();\n  if (!registry.operations[operation]) throw Object.assign(new Error('Unsupported drive_operation operation: ' + operation), {status: 400});\n";
const runAt = source.indexOf(runAnchor);
if (runAt < 0) throw new Error('drive operation execution anchor not found');
const runTail = source.slice(runAt, runAt + runAnchor.length + 800);
if (!runTail.includes("operation === 'time.now'")) {
  const insertAt = runAt + runAnchor.length;
  source = source.slice(0, insertAt) + runtimeBranch + source.slice(insertAt);
}

fs.writeFileSync(target, source);
console.log('time.now is present in the Home Center drive_operation registry and runtime handler');
