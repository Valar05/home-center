#!/usr/bin/env node
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {createRequire} from 'node:module';

const require = createRequire(import.meta.url);
const {
  COMMAND_CENTER_COLLECTIONS,
  COMMAND_CENTER_ALLOWED_STATUSES,
  COMMAND_CENTER_JOB_ACTIVATION_STATUSES,
  COMMAND_CENTER_COMPLETION_EVENT_LOOKBACK_LIMIT,
  COMMAND_CENTER_DURABLE_SESSION_RESTORE_STRATEGIES,
  isWorkerLeaseEligible,
  selectWorker,
  workerApiKeyProbeAllowsCodex,
  normalizeActivationChannel,
  buildJobActivation,
  activationStateFromResult,
  shouldAcceptWorkerCompletion,
} = require('../functions/command_center_mcp');

assert.equal(COMMAND_CENTER_COLLECTIONS.jobActivations, 'commandCenterJobActivations');
assert(COMMAND_CENTER_ALLOWED_STATUSES.includes('activating'));
assert(COMMAND_CENTER_ALLOWED_STATUSES.includes('executing'));
assert.deepEqual(COMMAND_CENTER_JOB_ACTIVATION_STATUSES, ['requested', 'accepted', 'rejected', 'timed_out', 'completed', 'failed']);
const requiredLifecycleEvents = ['activation_requested', 'activation_accepted', 'activation_rejected', 'executor_started', 'executor_heartbeat', 'executor_finished', 'executor_failed'];
assert(requiredLifecycleEvents.includes('activation_requested'));
assert(requiredLifecycleEvents.includes('executor_finished'));
assert.equal(COMMAND_CENTER_COMPLETION_EVENT_LOOKBACK_LIMIT >= 1000, true);
assert(COMMAND_CENTER_DURABLE_SESSION_RESTORE_STRATEGIES.includes('gcs_snapshot'));

const nowMs = Date.now();
const v2Identity = {workerInstallationId: 'install-cloud-real', workerInstanceId: 'instance-cloud-real', runnerVersion: 'command-center-runner-v2', protocolVersion: 'command-center-worker-v2'};
const liveCloudWorker = {
  ...v2Identity,
  workerId: 'codex-cloud-real',
  health: 'healthy',
  simulated: false,
  routable: true,
  capabilities: ['codex-cloud', 'codex', 'one-shot-worker'],
  activation: {mode: 'push', endpoint: 'https://worker.example.invalid/activate', verifiedAtMs: nowMs - 1000},
  lastHeartbeatAtMs: nowMs - 1000,
};
assert.equal(isWorkerLeaseEligible(liveCloudWorker, ['codex-cloud'], {nowMs}).eligible, true);
assert.equal(selectWorker([liveCloudWorker], ['codex-cloud'], {nowMs}).workerId, 'codex-cloud-real');

const noActivatorWorker = {
  ...v2Identity,
  workerInstallationId: 'install-no-activator',
  workerInstanceId: 'instance-no-activator',
  workerId: 'codex-cloud-no-activator',
  health: 'healthy',
  simulated: false,
  routable: true,
  capabilities: ['codex-cloud'],
};
assert.equal(isWorkerLeaseEligible(noActivatorWorker, ['codex-cloud'], {nowMs}).eligible, false);
assert.match(isWorkerLeaseEligible(noActivatorWorker, ['codex-cloud'], {nowMs}).reason, /heartbeat missing|activation channel/);
assert.throws(
  () => selectWorker([noActivatorWorker], ['codex-cloud'], {nowMs}),
  /No live real Command Center worker satisfies requirements: codex-cloud/
);

const staleWorker = {...liveCloudWorker, workerId: 'stale-cloud', lastHeartbeatAtMs: nowMs - 10 * 60 * 1000, activation: {...liveCloudWorker.activation, verifiedAtMs: nowMs - 60 * 60 * 1000}};
assert.equal(isWorkerLeaseEligible(staleWorker, ['codex-cloud'], {nowMs}).eligible, false);
assert.match(isWorkerLeaseEligible(staleWorker, ['codex-cloud'], {nowMs}).reason, /stale/);

const livePollWorker = {...liveCloudWorker, workerId: 'poll-cloud', activation: {mode: 'poll', verifiedAtMs: nowMs - 1000}, lastHeartbeatAtMs: nowMs - 1000};
assert.equal(isWorkerLeaseEligible(livePollWorker, ['codex-cloud'], {nowMs}).eligible, false);
assert.match(isWorkerLeaseEligible(livePollWorker, ['codex-cloud'], {nowMs}).reason, /local\/phone workers are excluded/);

const cloudRunSessionWorker = {
  ...v2Identity,
  workerInstallationId: 'install-cloud-run',
  workerInstanceId: 'instance-cloud-run',
  workerId: 'cloud-run-debian-primary',
  health: 'healthy',
  simulated: false,
  routable: true,
  capabilities: ['codex', 'cloud-run-debian', 'durable-session', 'prepared-workspace'],
  activation: {mode: 'cloud_run_job', verifiedAtMs: nowMs - 1000},
  lastHeartbeatAtMs: nowMs - 1000,
  cloudRunJob: {projectId: 'home-center-dclar', region: 'us-central1', jobName: 'command-center-debian-worker'},
  sessionPolicy: {durable: true, snapshotStore: 'gcs'},
};
assert.equal(isWorkerLeaseEligible(cloudRunSessionWorker, ['cloud-run-debian', 'durable-session'], {nowMs}).eligible, true);
assert.equal(selectWorker([liveCloudWorker, cloudRunSessionWorker], ['cloud-run-debian', 'durable-session'], {nowMs}).workerId, 'cloud-run-debian-primary');
const heartbeatProvenCloudRunWorker = {...cloudRunSessionWorker, activation: {mode: 'cloud_run_job', verifiedAtMs: nowMs - 60 * 60 * 1000}, lastHeartbeatAtMs: nowMs - 1000};
assert.equal(isWorkerLeaseEligible(heartbeatProvenCloudRunWorker, ['cloud-run-debian', 'durable-session'], {nowMs}).eligible, true);
const cloudRunWithoutApiProbe = {...cloudRunSessionWorker, runtime: {kind: 'debian-container', codexAuth: 'api_key', apiKeyCapabilityProbe: {status: 'failed', failureKind: 'worker_openai_quota_exceeded'}}};
assert.equal(workerApiKeyProbeAllowsCodex(cloudRunWithoutApiProbe).ok, false);
assert.equal(isWorkerLeaseEligible(cloudRunWithoutApiProbe, ['cloud-run-debian', 'durable-session'], {nowMs}).eligible, false);
assert.match(isWorkerLeaseEligible(cloudRunWithoutApiProbe, ['cloud-run-debian', 'durable-session'], {nowMs}).reason, /worker_openai_quota_exceeded|api-key capability unavailable/);
const coldActivatableCloudRunWorker = {...cloudRunSessionWorker, activation: {mode: 'cloud_run_job', verifiedAtMs: nowMs - 60 * 60 * 1000}, lastHeartbeatAtMs: 0};
assert.equal(isWorkerLeaseEligible(coldActivatableCloudRunWorker, ['cloud-run-debian', 'durable-session'], {nowMs}).eligible, true);
assert.equal(selectWorker([coldActivatableCloudRunWorker], ['cloud-run-debian', 'durable-session'], {nowMs}).workerId, 'cloud-run-debian-primary');
assert.equal(isWorkerLeaseEligible({...cloudRunSessionWorker, sessionPolicy: {durable: true, snapshotStore: 'local'}}, ['cloud-run-debian', 'durable-session'], {nowMs}).eligible, false);
assert.match(isWorkerLeaseEligible({...cloudRunSessionWorker, activation: {mode: 'poll', verifiedAtMs: nowMs}}, ['cloud-run-debian', 'durable-session'], {nowMs}).reason, /local\/phone workers are excluded/);

const simulatedWorker = {...liveCloudWorker, workerId: 'simulated', simulated: true};
assert.equal(isWorkerLeaseEligible(simulatedWorker, ['codex-cloud'], {nowMs}).eligible, false);
assert.match(isWorkerLeaseEligible(simulatedWorker, ['codex-cloud'], {nowMs}).reason, /simulated/);

assert.deepEqual(normalizeActivationChannel({mode: 'push', endpoint: ' https://bridge.example/activate ', verifiedAtMs: nowMs}), {
  mode: 'push',
  endpoint: 'https://bridge.example/activate',
  authRef: '',
  verifiedAtMs: nowMs,
});
assert.equal(normalizeActivationChannel({mode: 'poll'}).mode, 'poll');

const job = {jobId: 'job_real_cloud_contract', projectId: 'home-center'};
const lease = {leaseId: 'lease_real_cloud_contract'};
const activation = buildJobActivation(job, lease, liveCloudWorker, {attempt: 2, nowMs});
assert.equal(activation.activationId, 'job_activation_job_real_cloud_contract_2');
assert.equal(activation.jobId, job.jobId);
assert.equal(activation.leaseId, lease.leaseId);
assert.equal(activation.workerId, liveCloudWorker.workerId);
assert.equal(activation.status, 'requested');
assert.equal(activation.idempotencyKey, `${job.jobId}:${lease.leaseId}:${liveCloudWorker.workerId}:2`);

assert.deepEqual(activationStateFromResult({ok: true, accepted: true, executorId: 'exec-1'}), {
  status: 'accepted',
  accepted: true,
  diagnostic: '',
  executorId: 'exec-1',
});
assert.equal(activationStateFromResult({ok: false, error: 'no route'}).status, 'rejected');
assert.equal(activationStateFromResult(null).status, 'rejected');

assert.equal(shouldAcceptWorkerCompletion({
  requestedStatus: 'completed',
  events: [{type: 'executor_started'}, {type: 'executor_finished'}],
  artifacts: [
    {name: 'job-intake.json', origin: 'executor_workspace'},
    {name: 'orientation.md', origin: 'executor_workspace'},
    {name: 'reasoning-summary.md', origin: 'executor_workspace'},
    {name: 'command-log.jsonl', origin: 'executor_workspace'},
    {name: 'acceptance.json', origin: 'executor_workspace'},
    {name: 'acceptance-matrix.json', origin: 'executor_workspace'},
    {name: 'implementation.patch', origin: 'executor_workspace'},
    {name: 'changed-files.json', origin: 'executor_workspace'},
    {name: 'verification.json', origin: 'executor_workspace'},
    {name: 'final-report.md', origin: 'executor_workspace'},
    {name: 'mutation-requests.jsonl', origin: 'executor_workspace'},
  ],
}).ok, true);

assert.equal(shouldAcceptWorkerCompletion({
  requestedStatus: 'completed',
  events: [{type: 'executor_started'}, {type: 'executor_stdout'}, {type: 'executor_finished'}],
  artifacts: [
    {name: 'job-intake.json', origin: 'executor_workspace'},
    {name: 'orientation.md', origin: 'executor_workspace'},
    {name: 'reasoning-summary.md', origin: 'executor_workspace'},
    {name: 'command-log.jsonl', origin: 'executor_workspace'},
    {name: 'acceptance.json', origin: 'executor_workspace'},
    {name: 'acceptance-matrix.json', origin: 'executor_workspace'},
    {name: 'implementation.patch', origin: 'executor_workspace'},
    {name: 'changed-files.json', origin: 'executor_workspace'},
    {name: 'verification.json', origin: 'executor_workspace'},
    {name: 'final-report.md', origin: 'executor_workspace'},
    {name: 'mutation-requests.jsonl', origin: 'executor_workspace'},
  ],
  job: {repository: '', baseWorkspace: {snapshotRef: 'worker-local://'}, workerRequirements: ['cloud-run-debian']},
}).ok, true);
assert.equal(shouldAcceptWorkerCompletion({
  requestedStatus: 'completed',
  events: [{type: 'executor_started'}],
  artifacts: [{name: 'job-intake.json', origin: 'executor_workspace'}],
}).ok, false);
assert.match(shouldAcceptWorkerCompletion({
  requestedStatus: 'completed',
  events: [{type: 'executor_started'}, {type: 'executor_finished'}],
  artifacts: [{name: 'job-intake.json', origin: 'command_center'}],
}).reason, /executor workspace/);
assert.match(shouldAcceptWorkerCompletion({
  requestedStatus: 'completed',
  events: [{type: 'executor_started'}, {type: 'executor_finished'}],
  artifacts: [{name: 'noop-proof.txt', origin: 'executor_workspace'}],
}).reason, /noop-proof/);
assert.match(shouldAcceptWorkerCompletion({
  requestedStatus: 'completed',
  events: [{type: 'executor_started'}, {type: 'executor_finished'}],
  artifacts: [
    {name: 'job-intake.json', origin: 'executor_workspace'},
    {name: 'orientation.md', origin: 'executor_workspace'},
    {name: 'reasoning-summary.md', origin: 'executor_workspace'},
    {name: 'command-log.jsonl', origin: 'executor_workspace'},
    {name: 'acceptance.json', origin: 'executor_workspace'},
    {name: 'implementation.patch', origin: 'executor_workspace'},
    {name: 'changed-files.json', origin: 'executor_workspace'},
    {name: 'verification.json', origin: 'executor_workspace'},
    {name: 'final-report.md', origin: 'executor_workspace'},
    {name: 'mutation-requests.jsonl', origin: 'executor_workspace'},
  ],
}).reason, /acceptance-matrix\.json/);
assert.equal(shouldAcceptWorkerCompletion({requestedStatus: 'failed', events: [], artifacts: []}).ok, true);


const cloudWorkerSource = fs.readFileSync(new URL('../cloud-worker/src/cloud_run_worker.mjs', import.meta.url), 'utf8');

assert(cloudWorkerSource.includes('COMMAND_CENTER_OPENAI_AUTH_MODE'));
assert(cloudWorkerSource.includes('chatgpt_subscription'));
assert(cloudWorkerSource.includes('COMMAND_CENTER_CODEX_HOME_BUNDLE'));
assert(cloudWorkerSource.includes('prepareCodexAuth'));
assert(cloudWorkerSource.includes('Codex run did not emit turn.completed'));
assert(cloudWorkerSource.includes('quota exceeded'));
assert(cloudWorkerSource.includes('codex-auth-evidence.json'));
assert(cloudWorkerSource.includes('async function runOneShotJob()'));
assert(cloudWorkerSource.includes("post('/worker/lease', {jobId, executorId})"));
assert(cloudWorkerSource.includes("executor_started"));
assert(cloudWorkerSource.includes("executor_heartbeat"));
assert(cloudWorkerSource.includes("executor_finished"));
assert(cloudWorkerSource.includes("executor_stdout"));
assert(cloudWorkerSource.includes("executor_stderr"));
assert(!cloudWorkerSource.includes("noop-proof.txt"));
assert(cloudWorkerSource.includes("restoreJobWorkspace(job)"));
assert(cloudWorkerSource.includes('function repositoryFromGithubRef'));
assert(cloudWorkerSource.includes('function mutationPolicyForbidsRepositoryMutation'));
assert(cloudWorkerSource.includes('if (mutationPolicyForbidsRepositoryMutation(job)) return false;'));
assert(cloudWorkerSource.includes('runRepositoryFreeJob'));
assert(cloudWorkerSource.includes('worker_local_empty_workspace'));
assert(cloudWorkerSource.includes('Repository-free command evidence'));
assert(cloudWorkerSource.includes("type: 'executor_failed'"));
assert(!cloudWorkerSource.includes('repositoryFromText'));
assert(cloudWorkerSource.includes('parts.length < 2'));
assert(!cloudWorkerSource.includes("replace(/^github:\\\\/\\\\//, '').replace(/\\\\/.*$/, '')"));
assert(cloudWorkerSource.includes("runCodexPromptStreaming"));
assert(cloudWorkerSource.includes("implementation.patch"));
assert(cloudWorkerSource.includes("changed-files.json"));
assert(cloudWorkerSource.includes("verification.json"));
assert(cloudWorkerSource.includes("acceptance.json"));
assert(cloudWorkerSource.includes("acceptance-matrix.json"));
assert(cloudWorkerSource.includes("usage-summary.json"));
assert(cloudWorkerSource.includes("acceptanceCriteriaStatus: acceptance.acceptanceMatrix"));
assert(cloudWorkerSource.includes("usageSummary: acceptance.usageSummary"));
assert(cloudWorkerSource.includes("command-center-git-askpass.sh"));
assert(cloudWorkerSource.includes("GIT_ASKPASS"));
assert(cloudWorkerSource.includes(").trim()"));
assert(cloudWorkerSource.includes("process.env.GH_TOKEN = token"));
assert(cloudWorkerSource.includes("git ls-remote"));
assert(cloudWorkerSource.includes("GitHub auth preflight failed"));
assert(cloudWorkerSource.includes("Mutation ticket produced no uncommitted diff"));
assert(cloudWorkerSource.includes("Ticket required push/PR evidence"));
assert(cloudWorkerSource.includes("stdout-transcript.txt"));
assert(cloudWorkerSource.includes("stderr-transcript.txt"));
assert(cloudWorkerSource.includes("origin: 'executor_workspace'"));
assert(cloudWorkerSource.includes('function codexApiKeyProbe()'));
assert(cloudWorkerSource.includes('apiKeyCapabilityProbe: probe'));
assert(cloudWorkerSource.includes("post('/agent/heartbeat'"));
assert(cloudWorkerSource.includes("post('/worker/heartbeat'"));
assert(cloudWorkerSource.includes("['login', '--with-api-key']"));
assert(cloudWorkerSource.includes("['login', '--with-access-token']"));
assert(cloudWorkerSource.includes('CODEX_ACCESS_TOKEN'));
assert(cloudWorkerSource.includes("missingFailureKind: 'secret_missing'"));
assert(cloudWorkerSource.includes("missingFailureKind: 'access_token_missing'"));
assert(cloudWorkerSource.includes('worker_openai_quota_exceeded'));

const commandCenterSource = fs.readFileSync(new URL('../functions/command_center_mcp.js', import.meta.url), 'utf8');
assert(commandCenterSource.includes("githubTokenSecret: safeText(args.githubTokenSecret || 'GITHUB_TOKEN'"));
assert(commandCenterSource.includes("codexAccessTokenSecret: safeText(args.codexAccessTokenSecret || 'CODEX_ACCESS_TOKEN'"));
assert(commandCenterSource.includes("{name: 'CODEX_ACCESS_TOKEN'"));
assert(commandCenterSource.includes('grantSecretAccessor'));
assert(commandCenterSource.includes('secret_iam_binding_failed'));
assert(commandCenterSource.includes('secret_iam_binding_unverified'));
assert(commandCenterSource.includes('cloud_run_job_not_ready'));
assert(commandCenterSource.includes('ensureWorkerSecretAccess'));
assert(commandCenterSource.includes('waitForCloudRunJobReady'));
assert(commandCenterSource.includes('deleteCloudRunJob'));
assert(commandCenterSource.includes('waitForCloudRunJobDeleted'));
assert(commandCenterSource.includes('recreate fallback failed'));
assert(commandCenterSource.includes('api-key capability unavailable'));
assert(commandCenterSource.includes('async function claimActivationForWorker'));
assert(commandCenterSource.includes('agentContextSnapshots').valueOf());
assert(!commandCenterSource.includes("args.githubTokenSecret || 'GH_TOKEN'"));

console.log('Command Center cloud activation contract test: OK');
