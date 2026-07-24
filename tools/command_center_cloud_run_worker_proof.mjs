#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const TOKEN_CONFIG = path.join(os.homedir(), '.config', 'home-center', 'codex-hub.json');

function parseArgs(argv) {
  const args = {
    runId: `cloud-run-worker-proof-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}`,
    workerId: 'cloud-run-debian-codex-primary',
    evidenceDir: 'tools/command_center_invokability_evidence',
    timeoutMs: 12 * 60 * 1000,
    pollMs: 15000,
    json: false,
    failureProbe: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--worker-id') args.workerId = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--timeout-ms') args.timeoutMs = Number(argv[++i]) || args.timeoutMs;
    else if (arg === '--poll-ms') args.pollMs = Number(argv[++i]) || args.pollMs;
    else if (arg === '--json') args.json = true;
    else if (arg === '--failure-probe') args.failureProbe = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_cloud_run_worker_proof.mjs --worker-id cloud-run-debian-codex-primary [--failure-probe] [--json]');
      process.exit(0);
    }
  }
  return args;
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, JSON.stringify(value, null, 2) + '\n');
}

function redact(value) {
  return JSON.parse(JSON.stringify(value).replace(/Bearer\s+[A-Za-z0-9._~+/=-]{12,}/gi, 'Bearer [REDACTED]').replace(/\bccw_[A-Za-z0-9_-]{12,}(?:_[A-Za-z0-9_-]{12,})?\b/g, '[REDACTED_WORKER_TOKEN]').replace(/\bya29\.[A-Za-z0-9._-]{20,}/g, '[REDACTED_GOOGLE_TOKEN]'));
}

async function token() {
  const config = readJson(TOKEN_CONFIG);
  if (!config.accessToken || Number(config.expiresAtMs || 0) < Date.now() + 120000) {
    if (!config.refreshToken) throw new Error(`${TOKEN_CONFIG} has no usable accessToken or refreshToken`);
    const response = await fetch(`${config.gatewayBase || 'https://us-central1-home-center-dclar.cloudfunctions.net'}/termuxTokenRefresh`, {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify({refreshToken: config.refreshToken}),
    });
    const text = await response.text();
    let json = {};
    try { json = JSON.parse(text); } catch (_) {}
    if (!response.ok || !json.ok || !json.access_token) throw new Error(`token refresh failed: ${response.status} ${text.slice(0, 300)}`);
    config.accessToken = json.access_token;
    config.tokenType = json.token_type || config.tokenType || 'Bearer';
    config.expiresAtMs = Date.now() + Number(json.expires_in || 0) * 1000;
    config.allowedGroups = json.allowedGroups || config.allowedGroups || [];
    config.refreshedAt = new Date().toISOString();
    fs.writeFileSync(TOKEN_CONFIG, JSON.stringify(config, null, 2) + '\n', {mode: 0o600});
  }
  return config.accessToken;
}

function parseMcpResponse(text, label) {
  const dataLines = String(text || '').split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
  const payload = dataLines.length ? dataLines.join('\n') : text;
  try { return JSON.parse(payload); } catch (_) { throw new Error(`${label} did not return JSON: ${String(text).slice(0, 500)}`); }
}

function toolContentJson(result, label) {
  const text = result?.result?.content?.find((item) => item.type === 'text')?.text || '';
  try { return JSON.parse(text); } catch (_) { throw new Error(`${label} content was not JSON: ${text.slice(0, 500)}`); }
}

async function callTool(accessToken, id, name, args = {}) {
  const response = await fetch(MCP_URL, {
    method: 'POST',
    headers: {authorization: `Bearer ${accessToken}`, 'content-type': 'application/json', accept: 'application/json, text/event-stream'},
    body: JSON.stringify({jsonrpc: '2.0', id, method: 'tools/call', params: {name, arguments: args}}),
  });
  const text = await response.text();
  const json = parseMcpResponse(text, name);
  if (!response.ok || json.error) throw new Error(`${name} failed: ${response.status} ${JSON.stringify(json.error || json).slice(0, 900)}`);
  return toolContentJson(json, name);
}

async function op(accessToken, id, operation, args = {}) {
  return callTool(accessToken, id, 'command_center_operation', {operation, args});
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function findWorker(workers, workerId) {
  return (workers || []).find((worker) => worker.workerId === workerId) || null;
}

async function waitForWorker(accessToken, workerId, deadline, pollMs, evidence) {
  while (Date.now() < deadline) {
    const listed = await op(accessToken, 10, 'workers.list', {});
    const worker = findWorker(listed.result?.workers || listed.workers || [], workerId);
    evidence.steps.push({name: 'poll_worker', worker: worker ? {workerId: worker.workerId, health: worker.health, livenessState: worker.livenessState, activatable: worker.activatable, heartbeatFresh: worker.heartbeatFresh, heartbeatAgeMs: worker.heartbeatAgeMs, routable: worker.routable} : null});
    if (worker && worker.routable === true && (worker.health === 'healthy' || worker.health === 'activatable' || worker.activatable === true || worker.livenessState === 'activatable')) return worker;
    await sleep(pollMs);
  }
  return null;
}

async function waitForJob(accessToken, jobId, deadline, pollMs, evidence) {
  while (Date.now() < deadline) {
    const summary = await op(accessToken, 20, 'jobs.get_summary', {jobId});
    const status = summary.result?.status || summary.status || summary.result?.job?.status || '';
    evidence.steps.push({name: 'poll_job', jobId, status, counters: summary.result?.counters || summary.counters || {}});
    if (['completed', 'failed', 'canceled', 'expired'].includes(status)) return summary;
    await sleep(pollMs);
  }
  return null;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const accessToken = await token();
  const runSafe = args.runId.replace(/[^A-Za-z0-9_.-]/g, '-');
  const evidencePath = path.join(args.evidenceDir, `cloud_run_worker_proof_${runSafe}.json`);
  const evidence = {ok: false, runId: runSafe, mode: args.failureProbe ? 'deliberate_failure' : 'success', workerId: args.workerId, startedAt: new Date().toISOString(), steps: []};
  const deadline = Date.now() + args.timeoutMs;

  const wake = await op(accessToken, 1, 'workers.wake', {
    workerId: args.workerId,
    projectId: 'command-center-workers',
    reason: `Cloud Run worker proof ${runSafe}`,
    runLabel: runSafe,
    idempotencyKey: `wake-${runSafe}-${args.workerId}`,
  });
  evidence.steps.push({name: 'wake', result: wake.result || wake});

  const liveWorker = await waitForWorker(accessToken, args.workerId, deadline, args.pollMs, evidence);
  if (!liveWorker) throw new Error(`worker did not become routable/activatable before timeout: ${args.workerId}`);
  evidence.liveWorker = liveWorker;

  const reconcileDry = await op(accessToken, 2, 'jobs.reconcile_stale', {dryRun: true, statuses: ['leased', 'executing', 'running', 'activating'], olderThanMs: 30 * 60 * 1000, limit: 100});
  evidence.steps.push({name: 'reconcile_dry_run', result: reconcileDry.result || reconcileDry});
  const reconcileApply = await op(accessToken, 3, 'jobs.reconcile_stale', {dryRun: false, statuses: ['leased', 'executing', 'running', 'activating'], olderThanMs: 30 * 60 * 1000, limit: 100, idempotencyKey: `reconcile-${runSafe}`});
  evidence.steps.push({name: 'reconcile_apply', result: reconcileApply.result || reconcileApply});

  const verificationCommands = args.failureProbe
    ? ['sh -c "echo deliberate failure evidence; exit 42"']
    : ['node --version', 'python3 --version', 'date -u'];
  const jobCreate = await op(accessToken, 4, 'jobs.create', {
    projectId: 'command-center-workers',
    title: `${args.failureProbe ? 'Cloud Run worker deliberate failure proof' : 'Cloud Run worker repository-free proof'} ${runSafe}`,
    objective: args.failureProbe
      ? 'Run a bounded deliberate command failure through the real Cloud Run Debian worker and prove executor_failed terminal reconciliation plus lease release.'
      : 'Run bounded harmless repository-free commands through the real Cloud Run Debian worker and produce executor, command, artifact, checkpoint, and completion evidence.',
    acceptanceCriteria: args.failureProbe
      ? ['Worker emits executor_started.', 'Worker emits executor_failed.', 'Durable job becomes terminal failed.', 'Active lease is released.']
      : ['Worker emits executor_started.', 'Worker emits executor_heartbeat.', 'Worker emits command output evidence.', 'Worker records executor workspace artifacts.', 'Worker writes a checkpoint.', 'Worker completes the job.'],
    constraints: ['No repository mutation.', 'No external provider writes beyond Command Center job state and artifacts.'],
    workerRequirements: ['cloud-run-debian', 'durable-session'],
    baseWorkspace: {snapshotRef: 'worker-local://prepared-workspaces/command-center-empty'},
    requiredArtifacts: ['job-intake.json', 'command-log.jsonl', 'verification.json', 'final-report.md'],
    verificationCommands,
    mutationPolicy: {editFiles: 'deny', externalProviderWrite: 'deny', destructive: 'deny'},
    idempotencyKey: `${args.failureProbe ? 'failure' : 'repo-free'}-job-${runSafe}`,
  });
  const job = jobCreate.result?.job || jobCreate.job;
  const jobId = job?.jobId || '';
  if (!jobId) throw new Error(`jobs.create did not return jobId: ${JSON.stringify(jobCreate).slice(0, 500)}`);
  evidence.jobId = jobId;
  evidence.steps.push({name: 'jobs_create', jobId, selectedWorkerId: job.selectedWorkerId, activation: jobCreate.result?.activation || jobCreate.activation});

  const finalSummary = await waitForJob(accessToken, jobId, deadline, args.pollMs, evidence);
  if (!finalSummary) throw new Error(`job did not reach terminal status before timeout: ${jobId}`);
  const events = await op(accessToken, 5, 'jobs.get_events', {jobId, limit: 100});
  const logs = await op(accessToken, 6, 'jobs.get_logs', {jobId, limit: 100});
  const artifacts = await op(accessToken, 7, 'jobs.get_artifacts', {jobId, limit: 100});
  const handoff = await op(accessToken, 8, 'jobs.get_handoff', {jobId});
  const eventRows = events.result?.events || events.events || [];
  const logRows = logs.result?.logs || logs.logs || [];
  const artifactRows = artifacts.result?.artifacts || artifacts.artifacts || [];
  const finalStatus = finalSummary.result?.status || finalSummary.status || '';
  evidence.finalStatus = finalStatus;
  evidence.events = eventRows.map((event) => ({type: event.type, actor: event.actor, summary: event.summary, createdAtMs: event.createdAtMs, data: event.data || {}}));
  evidence.logsCount = logRows.length;
  evidence.artifacts = artifactRows.map((artifact) => ({name: artifact.name, kind: artifact.kind, origin: artifact.origin, workspacePath: artifact.workspacePath}));
  evidence.handoffCounters = handoff.result?.handoff?.counters || handoff.handoff?.counters || {};
  const eventTypes = new Set(eventRows.map((event) => event.type));
  const artifactNames = new Set(artifactRows.map((artifact) => artifact.name));
  const jobFailedEvents = eventRows.filter((event) => event.type === 'job_failed');
  const releasedLeaseCount = jobFailedEvents.reduce((sum, event) => sum + Number(event.data?.releasedLeases || event.data?.expiredLeases || 0), 0);
  evidence.releasedLeaseCount = releasedLeaseCount;
  evidence.ok = args.failureProbe
    ? finalStatus === 'failed'
      && eventTypes.has('executor_started')
      && eventTypes.has('executor_failed')
      && eventTypes.has('job_failed')
      && releasedLeaseCount > 0
    : finalStatus === 'completed'
      && eventTypes.has('executor_started')
      && eventTypes.has('executor_heartbeat')
      && eventTypes.has('executor_stdout')
      && eventTypes.has('executor_finished')
      && artifactNames.has('job-intake.json')
      && artifactNames.has('command-log.jsonl')
      && artifactNames.has('verification.json')
      && artifactNames.has('final-report.md')
      && logRows.length > 0;
  evidence.completedAt = new Date().toISOString();
  writeJson(evidencePath, redact(evidence));
  console.log(JSON.stringify({ok: evidence.ok, evidencePath, mode: evidence.mode, workerId: args.workerId, jobId, finalStatus, releasedLeaseCount, eventTypes: Array.from(eventTypes).sort(), artifactNames: Array.from(artifactNames).sort(), logsCount: logRows.length}, null, args.json ? 0 : 2));
  if (!evidence.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
