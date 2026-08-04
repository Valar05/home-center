#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const registryPath = path.join(root, 'ops', 'worker_profiles.v1.json');
const outputPath = path.join(root, 'functions', 'venice_worker_profile.generated.js');
const registry = JSON.parse(fs.readFileSync(registryPath, 'utf8'));
const assignment = registry.assignments?.['venice-discord-interactions'];

assert.ok(assignment, 'venice-discord-interactions assignment is missing');
assert.equal(assignment.profile, 'discord-interaction-control');
assert.equal(assignment.state, 'bound');

const profile = registry.profiles?.[assignment.profile];
assert.ok(profile, `worker profile ${assignment.profile} is missing`);
assert.equal(profile.runtime, 'cloud-run-service');
assert.match(assignment.serviceAccount || '', /^venice-discord-runtime@home-center-dclar\.iam\.gserviceaccount\.com$/);

function firebaseMemory(value) {
  const match = String(value).match(/^(\d+)(Mi|Gi)$/);
  assert.ok(match, `unsupported Firebase memory value: ${value}`);
  return `${match[1]}${match[2]}B`;
}

const rendered = `// Generated from ops/worker_profiles.v1.json by
// tools/generate_venice_worker_profile.mjs. Do not edit by hand.
module.exports = Object.freeze({
  cpu: ${profile.cpu},
  memory: '${firebaseMemory(profile.memory)}',
  concurrency: ${profile.concurrency},
  minInstances: ${profile.minInstances},
  maxInstances: ${profile.maxInstances},
  timeoutSeconds: ${profile.timeoutSeconds},
  serviceAccount: '${assignment.serviceAccount}',
});
`;

if (process.argv.includes('--check')) {
  assert.equal(fs.readFileSync(outputPath, 'utf8'), rendered, 'generated Venice worker profile is stale');
  process.stdout.write(JSON.stringify({ok: true, assignment: 'venice-discord-interactions', profile: assignment.profile}) + '\n');
} else {
  fs.writeFileSync(outputPath, rendered);
  process.stdout.write(`${path.relative(root, outputPath)}\n`);
}
