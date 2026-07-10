#!/usr/bin/env node
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  COMMAND_CENTER_COLLECTIONS,
  COMMAND_CENTER_DEFAULT_WORKERS,
  COMMAND_CENTER_REQUIRED_ARTIFACTS,
  COMMAND_CENTER_DEFAULT_BASE_WORKSPACE,
  cleanBaseWorkspace,
  cleanMutationPolicy,
  cleanOneShotExecution,
  selectWorker,
} = require('../functions/command_center_mcp');

const requiredCollections = [
  'projects',
  'jobs',
  'workers',
  'leases',
  'events',
  'questions',
  'mutationAuthorizations',
  'artifacts',
  'logs',
  'checkpoints',
  'baseWorkspaces',
  'workerTokens',
  'idempotency',
];
for (const key of requiredCollections) {
  assert.match(COMMAND_CENTER_COLLECTIONS[key], /^commandCenter/);
}

const defaultWorker = COMMAND_CENTER_DEFAULT_WORKERS[0];
assert.equal(defaultWorker.workerId, 'cloud-codex-primary');
assert.equal(defaultWorker.engine, 'codex');
assert.equal(defaultWorker.simulated, true);
assert(defaultWorker.capabilities.includes('github'));
assert(defaultWorker.capabilities.includes('home-drive-mcp'));
assert(defaultWorker.capabilities.includes('one-shot-worker'));
assert(defaultWorker.capabilities.includes('prepared-workspace'));

const selected = selectWorker(COMMAND_CENTER_DEFAULT_WORKERS, ['codex', 'github']);
assert.equal(selected.workerId, 'cloud-codex-primary');

const fallback = selectWorker([{workerId: 'termux', health: 'healthy', capabilities: ['android']}], ['codex']);
assert.equal(fallback.workerId, 'termux');

const policy = cleanMutationPolicy({editFiles: 'allowed', push: 'confirm'});
assert.equal(policy.editFiles, 'allowed');
assert.equal(policy.runTests, 'allowed');
assert.equal(policy.push, 'confirm');
assert.equal(policy.destructive, 'deny');

assert(COMMAND_CENTER_REQUIRED_ARTIFACTS.includes('job-intake.json'));
assert(COMMAND_CENTER_REQUIRED_ARTIFACTS.includes('implementation.patch'));
assert(COMMAND_CENTER_REQUIRED_ARTIFACTS.includes('final-report.md'));
assert.equal(COMMAND_CENTER_DEFAULT_BASE_WORKSPACE.restoreStrategy, 'copy_overlay');
assert.equal(cleanBaseWorkspace({baseWorkspaceId: 'tank-base', snapshotRef: 'worker-local://tank'}).baseWorkspaceId, 'tank-base');
const oneShot = cleanOneShotExecution({requiredArtifacts: ['render.png'], verificationCommands: ['npm test']});
assert.equal(oneShot.executionMode, 'one_shot');
assert(oneShot.requiredArtifacts.includes('render.png'));
assert(oneShot.requiredArtifacts.includes('job-intake.json'));
assert.equal(oneShot.verificationCommands[0], 'npm test');

console.log('Command Center MCP contract test: OK');
