#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const source = fs.readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
const workerSource = fs.readFileSync(new URL('command_center_oneshot_worker.mjs', import.meta.url), 'utf8');
const executorSource = fs.readFileSync(new URL('command_center_codex_executor.sh', import.meta.url), 'utf8');
const {
  cleanWorkerIdentity,
  workerRoutabilityDiagnostic,
  explainWorkerCandidate,
  proofEligibleWorker,
  selectWorkerCandidates,
  dedupeWorkerRecords,
  workerApiKeyProbeAllowsCodex,
  isLocalHostWorker,
} = require('../functions/command_center_mcp');

const nowMs = Date.now();
const base = {
  engine: 'codex',
  location: 'gcp-cloud-run-job',
  health: 'healthy',
  lastHeartbeatAtMs: nowMs,
  simulated: false,
  routable: true,
  registryRoutable: true,
  capabilities: ['codex', 'cloud-run-debian', 'durable-session', 'one-shot-worker', 'prepared-workspace'],
  activation: {mode: 'cloud_run_job', verifiedAtMs: nowMs},
  runtime: {codexAuth: 'api_key', apiKeyCapabilityProbe: {status: 'ok'}},
  cloudRunJob: {projectId: 'home-center-dclar', region: 'us-central1', jobName: 'codex-worker'},
  sessionPolicy: {durable: true, snapshotStore: 'gcs'},
  limits: {concurrentJobs: 1},
  runnerVersion: 'command-center-runner-v2',
  protocolVersion: 'command-center-worker-v2',
};
const a1 = {...base, workerId: 'cloud-generic-a', workerInstallationId: 'install-a', workerInstanceId: 'instance-a-1'};
const a2 = {...a1, workerId: 'cloud-generic-a-reconnect', workerInstanceId: 'instance-a-2', lastHeartbeatAtMs: nowMs + 1};
const b1 = {...base, workerId: 'cloud-generic-b', workerInstallationId: 'install-b', workerInstanceId: 'instance-b-1'};
const localTermux = {engine: 'codex', location: 'termux', health: 'healthy', lastHeartbeatAtMs: nowMs, simulated: false, routable: true, registryRoutable: true, capabilities: ['codex', 'one-shot-worker', 'prepared-workspace'], activation: {mode: 'poll', verifiedAtMs: nowMs}, runtime: {codexAuth: 'chatgpt_saved_login', authMode: 'chatgpt_saved_login'}, limits: {concurrentJobs: 1}, runnerVersion: 'command-center-runner-v2', protocolVersion: 'command-center-worker-v2', workerId: 'termux-generic-a', workerInstallationId: 'install-local-a', workerInstanceId: 'instance-local-a'};

assert.equal(cleanWorkerIdentity(a1).identityStatus, 'v2_complete');
assert.equal(workerRoutabilityDiagnostic(a1, nowMs).routable, true);
assert.equal(workerRoutabilityDiagnostic({...a1, protocolVersion: 'old'}, nowMs).code, 'protocol_version_mismatch');
assert.equal(workerRoutabilityDiagnostic({...localTermux, workerId: 'termux-tanks-oneshot'}, nowMs).code, 'legacy_project_specific_worker');
assert.equal(workerRoutabilityDiagnostic({workerId: 'legacy', health: 'healthy', lastHeartbeatAtMs: nowMs, simulated: false, capabilities: ['codex']}, nowMs).code, 'legacy_identity_incomplete');
assert.equal(workerRoutabilityDiagnostic({...localTermux, activation: {mode: 'push', endpoint: 'https://worker.example.invalid/activate', verifiedAtMs: nowMs - 600000}, lastHeartbeatAtMs: nowMs - 600000}, nowMs).code, 'stale_heartbeat');
assert.equal(workerRoutabilityDiagnostic({...a1, status: 'retired'}, nowMs).code, 'retired_worker');
assert.equal(workerRoutabilityDiagnostic({...a1, simulated: true}, nowMs).code, 'simulated_worker');

assert.equal(selectWorkerCandidates([a1], ['codex'], {nowMs})[0].eligible, true);
assert.equal(isLocalHostWorker(localTermux), true);
assert.equal(selectWorkerCandidates([localTermux], ['codex'], {nowMs})[0].reasonCode, 'local_host_excluded');
assert.equal(selectWorkerCandidates([a1], ['blender'], {nowMs})[0].eligible, false);
assert.equal(explainWorkerCandidate(a1, ['codex'], 1, {nowMs}).reasonCode, 'capacity_exhausted');
assert.equal(explainWorkerCandidate({...a1, capabilities: ['codex'], baseWorkspaces: [{snapshotRef: 'worker-local://prepared/default'}]}, ['codex'], 0, {nowMs}).included, true);
assert.equal(explainWorkerCandidate({...a1, capabilities: ['codex'], baseWorkspaces: [{snapshotRef: 'github://Valar05/home-center'}]}, ['codex'], 0, {nowMs}).included, true);
assert.equal(explainWorkerCandidate({...a1, capabilities: ['codex'], baseWorkspaces: [{snapshotRef: 'gs://snapshots/home-center.tgz'}]}, ['codex'], 0, {nowMs}).included, true);

const apiQuotaFail = {...base, workerId: 'cloud-api-key-worker', workerInstallationId: 'install-cloud', workerInstanceId: 'instance-cloud', location: 'gcp-cloud-run-job', activation: {mode: 'cloud_run_job', verifiedAtMs: nowMs}, runtime: {codexAuth: 'api_key', apiKeyCapabilityProbe: {status: 'failed', failureKind: 'insufficient_quota'}}, cloudRunJob: {projectId: 'home-center-dclar', region: 'us-central1', jobName: 'codex-worker'}, sessionPolicy: {durable: true, snapshotStore: 'gcs'}};
assert.equal(workerApiKeyProbeAllowsCodex(apiQuotaFail).ok, false);
assert.match(workerApiKeyProbeAllowsCodex(apiQuotaFail).reason, /insufficient_quota/);
assert.equal(selectWorkerCandidates([apiQuotaFail], ['codex'], {nowMs})[0].eligible, false);

assert.equal(dedupeWorkerRecords([{...a1, lastHeartbeatAtMs: nowMs - 1000}, a2, b1], nowMs).length, 2);
assert.equal(proofEligibleWorker(a1, 0, nowMs).included, true);
assert.equal(proofEligibleWorker(b1, 0, nowMs).included, true);
assert.equal(proofEligibleWorker({...localTermux, workerId: 'termux-tanks-oneshot'}, 0, nowMs).reasonCode, 'proof_excluded_worker');
assert.notEqual(a1.workerInstallationId, b1.workerInstallationId);
assert.notEqual(a1.workerInstanceId, b1.workerInstanceId);

assert(source.includes("case 'workers.request_restart'"));
assert(source.includes("code: 'host_offline'"));
assert(source.includes("proof.run_multi_worker"));
assert(source.includes('insufficient_distinct_real_workers'));
assert(source.includes('jobsCreated: []'));
assert(source.includes('requestRecorded: true'));
assert(source.includes('workerReceivedRequest: false'));
assert(source.includes('workerInstallationId'));
assert(source.includes('workerInstanceId'));
assert(source.includes('lastAcceptedLeaseAtMs'));
assert(source.includes('COMMAND_CENTER_PROOF_EXCLUDED_WORKER_IDS'));
assert(source.includes('termux-tanks-oneshot'));
assert(workerSource.includes('readOrCreateInstallationIdentity'));
assert(workerSource.includes('workerInstallationId'));
assert(workerSource.includes("const CODEX_ENV_DENYLIST = new Set(['OPENAI_API_KEY', 'CODEX_API_KEY'])"));
assert(executorSource.includes('unset OPENAI_API_KEY CODEX_API_KEY'));
assert(source.includes('workers.provision'));
assert(source.includes('local/phone workers are excluded from generic cloud routing'));

console.log('Command Center worker lifecycle contract test: OK');
