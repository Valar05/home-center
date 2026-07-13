#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const DEFAULT_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const DEFAULT_TOKEN_CONFIG = path.join(os.homedir(), '.config', 'home-center', 'codex-hub.json');
const PROJECT_ID = 'command-center-workers';

function parseArgs(argv) {
  const args = {
    mode: 'heartbeat',
    mcpUrl: DEFAULT_MCP_URL,
    tokenConfig: DEFAULT_TOKEN_CONFIG,
    runId: `health-ladder-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}`,
    evidenceDir: 'tools/command_center_invokability_evidence',
    workerId: 'cloud-run-debian-codex-primary',
    timeoutMs: 12 * 60 * 1000,
    pollMs: 15000,
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mode') args.mode = argv[++i];
    else if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--token-config') args.tokenConfig = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--worker-id') args.workerId = argv[++i];
    else if (arg === '--timeout-ms') args.timeoutMs = Number(argv[++i]) || args.timeoutMs;
    else if (arg === '--poll-ms') args.pollMs = Number(argv[++i]) || args.pollMs;
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_health_ladder.mjs --mode heartbeat|executor-pulse|codex-smoke|full-acceptance [--run-id ID] [--evidence-dir DIR] [--json]');
      process.exit(0);
    }
  }
  if (!['heartbeat', 'executor-pulse', 'codex-smoke', 'full-acceptance'].includes(args.mode)) {
    throw new Error(`Unsupported --mode ${args.mode}`);
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
  return JSON.parse(JSON.stringify(value)
    .replace(/Bearer\s+[A-Za-z0-9._~+/=-]{12,}/gi, 'Bearer [REDACTED]')
    .replace(/\bccw_[A-Za-z0-9_-]{12,}(?:_[A-Za-z0-9_-]{12,})?\b/g, '[REDACTED_WORKER_TOKEN]')
    .replace(/\bya29\.[A-Za-z0-9._-]{20,}/g, '[REDACTED_GOOGLE_TOKEN]'));
}

async function accessToken(args) {
  const config = readJson(args.tokenConfig);
  if (!config.accessToken || Number(config.expiresAtMs || 0) < Date.now() + 120000) {
    if (!config.refreshToken) throw new Error(`${args.tokenConfig} has no refresh token`);
    const response = await fetch(`${config.gatewayBase || 'https://us-central1-home-center-dclar.cloudfunctions.net'}/termuxTokenRefresh`, {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify({refreshToken: config.refreshToken}),
    });
    const text = await response.text();
    const json = JSON.parse(text);
    if (!response.ok || !json.ok || !json.access_token) throw new Error(`token refresh failed: ${response.status} ${text.slice(0, 400)}`);
    config.accessToken = json.access_token;
    config.tokenType = json.token_type || config.tokenType || 'Bearer';
    config.expiresAtMs = Date.now() + Number(json.expires_in || 0) * 1000;
    config.refreshedAt = new Date().toISOString();
    fs.writeFileSync(args.tokenConfig, JSON.stringify(config, null, 2) + '\n', {mode: 0o600});
  }
  return config.accessToken;
}

function parseMcpResponse(text, label) {
  const dataLines = String(text || '').split(/\r?\n/)
    .filter((line) => line.startsWith('data:'))
    .map((line) => line.slice(5).trim());
  const payload = dataLines.length ? dataLines.join('\n') : text;
  try {
    return JSON.parse(payload);
  } catch {
    throw new Error(`${label} did not return JSON: ${String(text).slice(0, 600)}`);
  }
}

function contentJson(result, label) {
  const text = result?.result?.content?.find((item) => item.type === 'text')?.text || '';
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${label} content was not JSON: ${text.slice(0, 600)}`);
  }
}

async function callTool(args, token, id, name, toolArgs = {}) {
  const response = await fetch(args.mcpUrl, {
    method: 'POST',
    headers: {authorization: `Bearer ${token}`, 'content-type': 'application/json', accept: 'application/json, text/event-stream'},
    body: JSON.stringify({jsonrpc: '2.0', id, method: 'tools/call', params: {name, arguments: toolArgs}}),
  });
  const text = await response.text();
  const json = parseMcpResponse(text, name);
  if (!response.ok || json.error) throw new Error(`${name} failed: ${response.status} ${JSON.stringify(json.error || json).slice(0, 1200)}`);
  return contentJson(json, name);
}

async function op(args, token, id, operation, opArgs = {}) {
  return callTool(args, token, id, 'command_center_operation', {operation, args: opArgs});
}

function unwrap(value, key) {
  return value?.result?.[key] ?? value?.[key];
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function summarizeJobsList(label, result) {
  const jobs = unwrap(result, 'jobs') || [];
  return {
    label,
    ok: !result.error && Array.isArray(jobs),
    error: result.error || '',
    diagnostic: result.diagnostic || '',
    requiredIndex: result.requiredIndex || null,
    count: Array.isArray(jobs) ? jobs.length : 0,
    jobIds: Array.isArray(jobs) ? jobs.map((job) => job.jobId).filter(Boolean).slice(0, 8) : [],
  };
}

function assertListOk(summary) {
  if (!summary.ok) throw new Error(`${summary.label} failed: ${summary.error || 'unknown'} ${summary.diagnostic || ''}`.slice(0, 1400));
  if (summary.error === 'missing_firestore_index') throw new Error(`${summary.label} still reports missing_firestore_index: ${JSON.stringify(summary.requiredIndex)}`);
}

async function checkJobLists(args, token, idBase, projectId, status = 'completed') {
  const cases = [
    {label: 'namespaced_all', tool: 'command_center.jobs.list', args: {limit: 10}},
    {label: `namespaced_status_${status}`, tool: 'command_center.jobs.list', args: {status, limit: 10}},
    {label: `namespaced_project_${projectId}`, tool: 'command_center.jobs.list', args: {projectId, limit: 10}},
    {label: `namespaced_project_${projectId}_status_${status}`, tool: 'command_center.jobs.list', args: {projectId, status, limit: 10}},
    {label: 'dispatcher_all', operation: 'jobs.list', args: {limit: 10}},
    {label: `dispatcher_status_${status}`, operation: 'jobs.list', args: {status, limit: 10}},
    {label: `dispatcher_project_${projectId}`, operation: 'jobs.list', args: {projectId, limit: 10}},
    {label: `dispatcher_project_${projectId}_status_${status}`, operation: 'jobs.list', args: {projectId, status, limit: 10}},
  ];
  const results = [];
  for (let i = 0; i < cases.length; i += 1) {
    const item = cases[i];
    const result = item.tool
      ? await callTool(args, token, idBase + i, item.tool, item.args)
      : await op(args, token, idBase + i, item.operation, item.args);
    const summary = summarizeJobsList(item.label, result);
    assertListOk(summary);
    results.push(summary);
  }
  return results;
}

async function heartbeat(args, token, evidence) {
  const health = await callTool(args, token, 10, 'command_center.health', {});
  const workers = await op(args, token, 11, 'workers.list', {limit: 100});
  const workerRows = unwrap(workers, 'workers') || [];
  const worker = workerRows.find((item) => item.workerId === args.workerId) || null;
  evidence.health = health;
  evidence.worker = worker ? {
    workerId: worker.workerId,
    simulated: worker.simulated,
    routable: worker.routable,
    retired: worker.retired,
    health: worker.health,
    livenessState: worker.livenessState,
    capabilities: worker.capabilities,
  } : null;
  evidence.listChecks.push(...await checkJobLists(args, token, 20, PROJECT_ID, 'completed'));
  evidence.ok = Boolean(health.ok || health.invokable)
    && Boolean(worker)
    && worker.simulated === false
    && worker.routable === true
    && worker.retired !== true
    && evidence.listChecks.every((check) => check.ok);
}

async function createHealthJob(args, token, evidence, mode) {
  const nonce = `${mode.replace(/-/g, '_')}_${evidence.runId.replace(/[^A-Za-z0-9_.-]/g, '_')}`;
  const executionMode = mode === 'executor-pulse' ? 'executor_pulse' : 'codex_smoke';
  const requiredArtifacts = executionMode === 'executor_pulse'
    ? ['job-intake.json', 'pulse-proof.json', 'stdout-transcript.txt', 'command-log.jsonl', 'acceptance.json', 'acceptance-matrix.json', 'usage-summary.json', 'verification.json', 'final-report.md']
    : ['job-intake.json', 'stdout-transcript.txt', 'stderr-transcript.txt', 'command-log.jsonl', 'acceptance.json', 'acceptance-matrix.json', 'usage-summary.json', 'verification.json', 'final-report.md'];
  const jobCreate = await op(args, token, 100, 'jobs.create', {
    projectId: PROJECT_ID,
    title: `Command Center ${mode} ${evidence.runId}`,
    objective: executionMode === 'executor_pulse'
      ? `Run deterministic executor pulse only. nonce: ${nonce}. Do not invoke Codex.`
      : `Run repo-less Codex smoke only. nonce: ${nonce}. Create hello-world.txt containing exactly ${nonce}. Do not inspect or clone a repository.`,
    acceptanceCriteria: [
      'A real non-simulated cloud-run-debian worker is selected.',
      'Executor start, PID identity, heartbeat, stdout or stderr, and finish events are recorded in order.',
      executionMode === 'executor_pulse' ? 'pulse-proof.json contains the requested nonce.' : 'hello-world.txt contains the requested nonce in the executor workspace.',
      'acceptance-matrix.json is uploaded and every criterion has status, evidenceRefs, notes, and blockingReason.',
      'usage-summary.json is uploaded and readable.',
      executionMode === 'executor_pulse' ? 'No Codex model tokens are consumed.' : 'Codex smoke usage is bounded and does not restore a repository.',
    ],
    constraints: ['No GitHub mutation.', 'No Drive mutation.', 'No deployment mutation.', 'No worker-registration or project-registration mutation.'],
    workerRequirements: ['cloud-run-debian', 'durable-session', 'gcs-workspace-snapshot'],
    executionMode,
    requiredArtifacts,
    verificationCommands: executionMode === 'codex_smoke' ? ['cat hello-world.txt'] : [],
    mutationPolicy: {editFiles: 'workspace_only', externalProviderWrite: 'deny', destructive: 'deny'},
    idempotencyKey: `command-center-${mode}-${evidence.runId}`,
  });
  const job = unwrap(jobCreate, 'job') || {};
  if (!job.jobId) throw new Error(`jobs.create did not return jobId: ${JSON.stringify(jobCreate).slice(0, 900)}`);
  evidence.jobCreate = {jobId: job.jobId, status: job.status, selectedWorkerId: job.selectedWorkerId, simulatedWorker: job.simulatedWorker, executionMode: job.executionMode};
  evidence.jobId = job.jobId;
  evidence.nonce = nonce;
  evidence.listChecks.push(...await checkJobLists(args, token, 200, PROJECT_ID, job.status || 'leased'));
  return job.jobId;
}

function artifactByName(rows) {
  const out = {};
  for (const row of rows || []) out[row.name] = row;
  return out;
}

async function pollAndReadback(args, token, evidence, jobId) {
  const deadline = Date.now() + args.timeoutMs;
  while (Date.now() < deadline) {
    const summary = await op(args, token, 300, 'jobs.get_summary', {jobId});
    const status = summary.result?.status || summary.status || summary.result?.job?.status || '';
    const statusLists = await checkJobLists(args, token, 400, PROJECT_ID, status || 'leased');
    evidence.polls.push({at: new Date().toISOString(), status, listChecks: statusLists});
    if (['completed', 'failed', 'canceled', 'expired'].includes(status)) break;
    await sleep(args.pollMs);
  }
  const jobReadback = await op(args, token, 500, 'jobs.get', {jobId});
  const events = await op(args, token, 501, 'jobs.get_events', {jobId, limit: 100});
  const logs = await op(args, token, 502, 'jobs.get_logs', {jobId, limit: 100});
  const artifacts = await op(args, token, 503, 'jobs.get_artifacts', {jobId, limit: 100});
  const handoff = await op(args, token, 504, 'jobs.get_handoff', {jobId});
  const finalJob = unwrap(jobReadback, 'job') || {};
  const eventRows = unwrap(events, 'events') || [];
  const logRows = unwrap(logs, 'logs') || [];
  const artifactRows = unwrap(artifacts, 'artifacts') || [];
  const handoffPacket = unwrap(handoff, 'handoff') || {};
  const byName = artifactByName(artifactRows);
  const matrix = handoffPacket.review?.acceptanceMatrix || handoffPacket.checkpoint?.acceptanceCriteriaStatus || [];
  const usage = handoffPacket.usageSummary || handoffPacket.checkpoint?.usageSummary || {};
  const eventTypes = eventRows.map((event) => event.type);
  evidence.final = {
    status: finalJob.status,
    selectedWorkerId: finalJob.selectedWorkerId,
    simulatedWorker: finalJob.simulatedWorker,
    executionMode: finalJob.executionMode,
    eventTypes,
    logsCount: logRows.length,
    artifacts: artifactRows.map((artifact) => ({artifactId: artifact.artifactId, name: artifact.name, kind: artifact.kind, origin: artifact.origin, sha256: artifact.sha256, uri: artifact.uri})),
    acceptanceMatrixCount: Array.isArray(matrix) ? matrix.length : 0,
    acceptanceMatrix: matrix,
    usageSummary: usage,
  };
  evidence.listChecks.push(...await checkJobLists(args, token, 600, PROJECT_ID, 'completed'));
  const artifactNames = new Set(artifactRows.map((artifact) => artifact.name));
  const allExecutorArtifactsHaveHashes = artifactRows.filter((artifact) => artifact.origin === 'executor_workspace').every((artifact) => artifact.sha256);
  const expectedMode = evidence.mode === 'executor-pulse' ? 'executor_pulse' : 'codex_smoke';
  const expectedArtifacts = expectedMode === 'executor_pulse'
    ? ['job-intake.json', 'pulse-proof.json', 'stdout-transcript.txt', 'command-log.jsonl', 'acceptance.json', 'acceptance-matrix.json', 'usage-summary.json', 'verification.json', 'final-report.md']
    : ['job-intake.json', 'stdout-transcript.txt', 'stderr-transcript.txt', 'command-log.jsonl', 'acceptance.json', 'acceptance-matrix.json', 'usage-summary.json', 'verification.json', 'final-report.md'];
  const matrixComplete = Array.isArray(matrix)
    && matrix.length > 0
    && matrix.every((item) => item.status && Array.isArray(item.evidenceRefs) && item.notes !== undefined && item.blockingReason !== undefined);
  evidence.ok = finalJob.status === 'completed'
    && finalJob.selectedWorkerId === args.workerId
    && finalJob.simulatedWorker === false
    && finalJob.executionMode === expectedMode
    && ['executor_started', 'executor_heartbeat', 'executor_finished'].every((type) => eventTypes.includes(type))
    && (expectedMode === 'executor_pulse' || eventTypes.includes('executor_stdout') || eventTypes.includes('executor_stderr'))
    && expectedArtifacts.every((name) => artifactNames.has(name) && byName[name]?.sha256)
    && matrixComplete
    && Object.prototype.hasOwnProperty.call(usage, 'inputTokens')
    && (expectedMode !== 'executor_pulse' || Number(usage.inputTokens || 0) === 0)
    && allExecutorArtifactsHaveHashes
    && evidence.listChecks.every((check) => check.ok);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.mode === 'full-acceptance') {
    const mod = await import('./command_center_job_list_observability_gate.mjs');
    if (mod) return;
  }
  const token = await accessToken(args);
  const runSafe = args.runId.replace(/[^A-Za-z0-9_.-]/g, '-');
  const evidencePath = path.join(args.evidenceDir, `command_center_health_ladder_${args.mode}_${runSafe}.json`);
  const evidence = {ok: false, mode: args.mode, runId: runSafe, workerId: args.workerId, startedAt: new Date().toISOString(), listChecks: [], polls: []};
  if (args.mode === 'heartbeat') {
    await heartbeat(args, token, evidence);
  } else {
    const jobId = await createHealthJob(args, token, evidence, args.mode);
    await pollAndReadback(args, token, evidence, jobId);
  }
  evidence.completedAt = new Date().toISOString();
  writeJson(evidencePath, redact(evidence));
  console.log(JSON.stringify({
    ok: evidence.ok,
    mode: args.mode,
    evidencePath,
    jobId: evidence.jobId || null,
    finalStatus: evidence.final?.status || null,
    selectedWorkerId: evidence.final?.selectedWorkerId || evidence.worker?.workerId || null,
    simulatedWorker: evidence.final?.simulatedWorker ?? evidence.worker?.simulated ?? null,
    executionMode: evidence.final?.executionMode || null,
    listChecks: evidence.listChecks.length,
    acceptanceMatrixCount: evidence.final?.acceptanceMatrixCount || 0,
    usageSummary: evidence.final?.usageSummary || null,
  }, null, args.json ? 0 : 2));
  if (!evidence.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
