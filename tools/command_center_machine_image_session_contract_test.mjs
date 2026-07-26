#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const commandCenterSource = fs.readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
const workerSource = fs.readFileSync(new URL('command_center_oneshot_worker.mjs', import.meta.url), 'utf8');
const cloudManifest = JSON.parse(fs.readFileSync(new URL('command_center_base_manifests/cloud-run-debian-codex.json', import.meta.url), 'utf8'));
const {
  COMMAND_CENTER_COLLECTIONS,
  COMMAND_CENTER_MACHINE_IMAGE_STATUSES,
  COMMAND_CENTER_CODEX_SESSION_STATUSES,
  COMMAND_CENTER_SESSION_ISOLATION_MODES,
  cleanMachineImage,
  cleanSessionPolicy,
  workerMachineImageState,
  workerImagePolicyDiagnostic,
  workerSessionPolicyDiagnostic,
  selectWorkerCandidates,
  compactWorkerCensus,
  cleanAgentSession,
  isLocalHostWorker,
  cloudProvisioningDefaults,
  assertCloudProvisioningRequest,
  cloudMachineImageRecord,
  cloudWorkerRecordFromProvisioning,
} = require('../functions/command_center_mcp');

assert.equal(COMMAND_CENTER_COLLECTIONS.machineImages, 'commandCenterMachineImages');
assert(COMMAND_CENTER_MACHINE_IMAGE_STATUSES.includes('available'));
assert(COMMAND_CENTER_CODEX_SESSION_STATUSES.includes('allocated'));
assert(COMMAND_CENTER_SESSION_ISOLATION_MODES.includes('session'));

const caller = {actor: 'drew@example.invalid', ownerKey: 'owner-test'};
const image = cleanMachineImage({
  imageId: 'cloud-debian-codex',
  imageKind: 'cloud-run-debian-codex',
  version: 'v2',
  digest: 'sha256:abc',
  capabilities: ['codex', 'node', 'python'],
  dependencyBundleRefs: ['gs://bundle'],
  warmCacheRefs: ['gs://cache'],
  hotPathInstallAllowed: false,
}, caller);
assert.equal(image.imageId, 'cloud-debian-codex');
assert.equal(image.status, 'available');
assert.equal(image.ownerKey, 'owner-test');
assert.equal(image.hotPathInstallAllowed, false);
assert.deepEqual(image.capabilities, ['codex', 'node', 'python']);

const policy = cleanSessionPolicy({machineImageId: 'cloud-debian-codex', isolationMode: 'session'});
assert.equal(policy.machineImageId, 'cloud-debian-codex');
assert.equal(policy.requireMaterializedImage, true);
assert.equal(policy.allowMaterializationDuringJob, false);

const nowMs = Date.now();
const worker = {
  workerId: 'cloud-debian-codex-primary',
  location: 'gcp-cloud-run-job',
  workerInstallationId: 'winst-test',
  workerInstanceId: 'winstproc-test',
  runnerVersion: 'command-center-runner-v2',
  protocolVersion: 'command-center-worker-v2',
  health: 'healthy',
  lastHeartbeatAtMs: nowMs,
  simulated: false,
  capabilities: ['codex', 'one-shot-worker', 'prepared-workspace'],
  runtime: {codexAuth: 'api_key', apiKeyCapabilityProbe: {status: 'ok'}},
  activation: {mode: 'cloud_run_job', verifiedAtMs: nowMs},
  cloudRunJob: {projectId: 'home-center-dclar', region: 'us-central1', jobName: 'command-center-debian-worker'},
  sessionPolicy: {durable: true, snapshotStore: 'gcs'},
  availableImageIds: ['cloud-debian-codex'],
  materializedImageIds: ['cloud-debian-codex'],
  maxConcurrentSessions: 1,
  activeSessionIds: [],
  sessionIsolationModes: ['session'],
  cacheState: {hotStartReady: true, hotPathInstallAllowed: false},
};
const state = workerMachineImageState(worker);
assert.equal(state.maxConcurrentSessions, 1);
assert.equal(state.sessionCapacityRemaining, 1);
assert.deepEqual(state.materializedImageIds, ['cloud-debian-codex']);
assert.equal(workerImagePolicyDiagnostic(worker, policy, [image]).code, 'image_materialized');
assert.equal(workerSessionPolicyDiagnostic(worker, policy).code, 'session_capacity_available');

const missing = workerImagePolicyDiagnostic(worker, {machineImageId: 'debian-blender'}, [image]);
assert.equal(missing.ok, false);
assert.equal(missing.code, 'image_not_materialized');

const hotPathInstall = workerImagePolicyDiagnostic(worker, {machineImageId: 'debian-blender', allowMaterializationDuringJob: true}, [image]);
assert.equal(hotPathInstall.ok, false);
assert.equal(hotPathInstall.code, 'hot_path_materialization_forbidden');

const fullWorker = {...worker, activeSessionIds: ['session-a']};
assert.equal(workerSessionPolicyDiagnostic(fullWorker, policy).code, 'session_capacity_exhausted');
const noIsolationWorker = {...worker, sessionIsolationModes: ['host']};
assert.equal(workerSessionPolicyDiagnostic(noIsolationWorker, policy).code, 'session_isolation_unavailable');

const candidates = selectWorkerCandidates([worker], ['codex'], {nowMs, sessionPolicy: policy, machineImages: [image]});
assert.equal(candidates[0].eligible, true);
assert.equal(candidates[0].imagePolicy.code, 'image_materialized');
const missingCandidates = selectWorkerCandidates([worker], ['codex'], {nowMs, sessionPolicy: {machineImageId: 'debian-blender'}, machineImages: [image]});
assert.equal(missingCandidates[0].eligible, false);
assert.equal(missingCandidates[0].reasonCode, 'image_not_materialized');

const census = compactWorkerCensus(worker, 0, nowMs);
assert.deepEqual(census.materializedImageIds, ['cloud-debian-codex']);
assert.equal(census.sessionCapacity.capacityRemaining, 1);
assert.equal(census.authenticationMode, 'api_key');
assert.equal(census.localHostExcludedByDefault, false);

const session = cleanAgentSession({sessionId: 'session_test_machine_image', machineImageId: 'cloud-debian-codex', hostInstallationId: 'winst-test', workerId: 'cloud-debian-codex-primary',
  location: 'gcp-cloud-run-job', workerInstanceId: 'winstproc-test', status: 'allocated', codexAuthMode: 'api_key'}, {}, caller);
assert.equal(session.status, 'allocated');
assert.equal(session.machineImageId, 'cloud-debian-codex');
assert.equal(session.hostInstallationId, 'winst-test');
assert.equal(session.codexAuthMode, 'api_key');

for (const operation of [
  'machine_images.register',
  'machine_images.list',
  'machine_images.inspect',
  'codex_sessions.create',
  'codex_sessions.list',
  'codex_sessions.inspect',
  'codex_sessions.reconcile',
  'hosts.list',
  'hosts.inspect',
  'proof.run_multi_session',
  'workers.provision',
  'provisioning.inspect',
  'provisioning.reconcile',
]) {
  assert(commandCenterSource.includes(`case '${operation}'`), `missing dispatcher case ${operation}`);
}
for (const tool of [
  'command_center.machine_images.register',
  'command_center.machine_images.list',
  'command_center.machine_images.inspect',
  'command_center.codex_sessions.create',
  'command_center.codex_sessions.list',
  'command_center.hosts.list',
  'command_center.proof.run_multi_session',
  'command_center.workers.provision',
  'command_center.provisioning.inspect',
]) {
  assert(commandCenterSource.includes(`server.registerTool('${tool}'`), `missing MCP tool ${tool}`);
}
assert(commandCenterSource.includes('image_not_materialized'));
assert(commandCenterSource.includes('hot_path_materialization_forbidden'));
assert(commandCenterSource.includes('No synthetic completion'));

assert(workerSource.includes('machineImageRuntimePayload'));
assert(workerSource.includes('materializedImageIds'));
assert(workerSource.includes('maxConcurrentSessions'));
assert(workerSource.includes('CODEX_ENV_DENYLIST'));
assert.equal(cloudManifest.materializedImageIds.includes('cloud-debian-codex'), true);
assert.equal(cloudManifest.maxConcurrentSessions, 1);
assert.equal(cloudManifest.cacheState.hotPathInstallAllowed, false);
assert.equal(cloudManifest.canMaterializeImages, false);
assert.equal(cloudManifest.runtime.codexAuth, 'api_key');
assert.equal(cloudManifest.runtime.deviceIndependent, true);
assert.equal(cloudManifest.machineImages[0].hotPathInstallAllowed, false);
const defaults = cloudProvisioningDefaults({idempotencyKey: 'machine-image-provision-test'}, caller);
assert.equal(defaults.machineImageId, 'cloud-debian-codex');
assert.equal(defaults.githubTokenSecret, 'GITHUB_TOKEN');
assert.equal(defaults.snapshotBucket, 'home-center-dclar-command-center-worker-sessions');
assert.throws(() => assertCloudProvisioningRequest({workerId: 'termux-debian-codex'}), /cloud-only/);
const provisioned = cloudWorkerRecordFromProvisioning({...defaults, apiKeyCapabilityProbe: {status: 'ok'}}, caller);
assert.equal(isLocalHostWorker(provisioned), false);
assert.equal(provisioned.materializedImageIds.includes('cloud-debian-codex'), true);

console.log('Command Center machine image/session contract test: OK');
