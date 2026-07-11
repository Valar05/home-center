#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const commandCenterSource = fs.readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
const {
  COMMAND_CENTER_COLLECTIONS,
  COMMAND_CENTER_DEFAULT_WORKERS,
  COMMAND_CENTER_REQUIRED_ARTIFACTS,
  COMMAND_CENTER_DEFAULT_BASE_WORKSPACE,
  COMMAND_CENTER_DEFAULT_BUCKET_ID,
  COMMAND_CENTER_BUCKET_KINDS,
  COMMAND_CENTER_BUCKET_LAYOUT,
  cleanBaseWorkspace,
  cleanMutationPolicy,
  cleanOneShotExecution,
  cleanBucketObject,
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
  'bucketObjects',
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

assert.equal(COMMAND_CENTER_DEFAULT_BUCKET_ID, 'command-center');
for (const kind of ['memory.past_log', 'memory.current_condensed', 'skill.scratch', 'skill.promoted', 'note.cross_repo']) {
  assert(COMMAND_CENTER_BUCKET_KINDS.includes(kind));
}
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['memory/past-logs'].kind, 'memory.past_log');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['memory/current-condensed'].kind, 'memory.current_condensed');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['skills/scratch'].kind, 'skill.scratch');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['skills/promoted'].kind, 'skill.promoted');
assert.equal(COMMAND_CENTER_BUCKET_LAYOUT.lanes['notes/cross-repo'].kind, 'note.cross_repo');
assert.match(COMMAND_CENTER_BUCKET_LAYOUT.storagePolicy.secretPolicy, /No bearer tokens/);

const bucketObject = cleanBucketObject({
  idempotencyKey: 'bucket-test-001',
  kind: 'skill.scratch',
  title: 'Long running executor observation',
  body: 'Capture stdout batches and heartbeat evidence before promoting.',
  projectId: 'home-center',
  repository: 'Valar05/home-center',
  jobId: 'job_12345678',
  tags: ['worker', 'streaming'],
}, {actor: 'tester@example.com'});
assert.equal(bucketObject.bucketId, 'command-center');
assert.equal(bucketObject.kind, 'skill.scratch');
assert.equal(bucketObject.lane, 'skills/scratch');
assert.match(bucketObject.path, /^skills\/scratch\//);
assert.equal(bucketObject.projectId, 'home-center');
assert.equal(bucketObject.jobId, 'job_12345678');
assert.equal(bucketObject.provenance.noSecrets, true);
assert.throws(() => cleanBucketObject({
  kind: 'note.cross_repo',
  title: 'bad',
  body: 'Authorization: ' + 'Bearer ' + 'abcdefghijklmnopqrstuvwxyz',
}, {actor: 'tester@example.com'}), /must not contain reusable secrets/);

assert(commandCenterSource.includes("server.registerTool('command_center.jobs.get_handoff'"));
assert(commandCenterSource.includes("server.registerTool('command_center.jobs.create_followup'"));
assert(commandCenterSource.includes('synthesizeJobHandoff'));
assert(commandCenterSource.includes('createFollowupJob'));

console.log('Command Center MCP contract test: OK');
