#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

const root = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const target = path.join(root, 'functions', 'home_center_mcp.js');
let source = fs.readFileSync(target, 'utf8');

if (source.includes("'time.now': {summary: 'Return the current Home Center runtime time.'")) {
  console.log('time.now runtime patch already present');
  process.exit(0);
}

const registryAnchor = "    operations: {\n      drive_search: {";
if (!source.includes(registryAnchor)) throw new Error('drive operation registry anchor not found');
source = source.replace(
  registryAnchor,
  "    operations: {\n      'time.now': {summary: 'Return the current Home Center runtime time.', write: false, requiredScopes: [], input: {}},\n      drive_search: {",
);

const runAnchor = "  const registry = driveOperationRegistry();\n  if (!registry.operations[operation]) throw Object.assign(new Error('Unsupported drive_operation operation: ' + operation), {status: 400});";
if (!source.includes(runAnchor)) throw new Error('drive operation execution anchor not found');
source = source.replace(
  runAnchor,
  runAnchor + "\n  if (operation === 'time.now') {\n    const now = new Date();\n    return {operation, registryVersion: registry.version, completed: true, result: {utcIso: now.toISOString(), unixMs: now.getTime()}};\n  }",
);

fs.writeFileSync(target, source);
console.log('installed time.now into Home Center drive_operation registry and runtime handler');
