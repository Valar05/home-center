#!/usr/bin/env node
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

const DEFAULT_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp/mcp';
const DEFAULT_TOKEN_CONFIG = path.join(os.homedir(), '.config', 'home-center', 'codex-hub.json');

function parseArgs(argv) {
  const args = {
    mcpUrl: DEFAULT_MCP_URL,
    tokenConfig: DEFAULT_TOKEN_CONFIG,
    runId: `job-list-observability-${new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14)}`,
    evidenceDir: 'tools/command_center_invokability_evidence',
    workerId: 'cloud-run-debian-codex-primary',
    timeoutMs: 18 * 60 * 1000,
    pollMs: 15000,
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--token-config') args.tokenConfig = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--worker-id') args.workerId = argv[++i];
    else if (arg === '--timeout-ms') args.timeoutMs = Number(argv[++i]) || args.timeoutMs;
    else if (arg === '--poll-ms') args.pollMs = Number(argv[++i]) || args.pollMs;
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_job_list_observability_gate.mjs [--run-id ID] [--evidence-dir DIR] [--json]');
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

async function callTool(mcpUrl, token, id, name, args = {}) {
  const response = await fetch(mcpUrl, {
    method: 'POST',
    headers: {authorization: `Bearer ${token}`, 'content-type': 'application/json', accept: 'application/json, text/event-stream'},
    body: JSON.stringify({jsonrpc: '2.0', id, method: 'tools/call', params: {name, arguments: args}}),
  });
  const text = await response.text();
  const json = parseMcpResponse(text, name);
  if (!response.ok || json.error) throw new Error(`${name} failed: ${response.status} ${JSON.stringify(json.error || json).slice(0, 1200)}`);
  return contentJson(json, name);
}

async function op(args, token, id, operation, opArgs = {}) {
  return callTool(args.mcpUrl, token, id, 'command_center_operation', {operation, args: opArgs});
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
  if (!summary.ok) {
    throw new Error(`${summary.label} failed: ${summary.error || 'unknown'} ${summary.diagnostic || ''}`.slice(0, 1400));
  }
  if (summary.error === 'missing_firestore_index') {
    throw new Error(`${summary.label} still reports missing_firestore_index: ${JSON.stringify(summary.requiredIndex)}`);
  }
}

async function checkJobLists(args, token, idBase, projectId, status) {
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
      ? await callTool(args.mcpUrl, token, idBase + i, item.tool, item.args)
      : await op(args, token, idBase + i, item.operation, item.args);
    const summary = summarizeJobsList(item.label, result);
    assertListOk(summary);
    results.push(summary);
  }
  return results;
}

function artifactByName(rows) {
  const out = {};
  for (const row of rows || []) out[row.name] = row;
  return out;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const token = await accessToken(args);
  const runSafe = args.runId.replace(/[^A-Za-z0-9_.-]/g, '-');
  const projectId = 'command-center-workers';
  const nonce = `NONCE_${runSafe.replace(/[^A-Za-z0-9_.-]/g, '_')}`;
  const evidencePath = path.join(args.evidenceDir, `command_center_job_list_observability_${runSafe}.json`);
  const evidence = {ok: false, runId: runSafe, workerId: args.workerId, nonce, startedAt: new Date().toISOString(), listChecks: [], polls: []};
  const deadline = Date.now() + args.timeoutMs;

  evidence.listChecks.push(...await checkJobLists(args, token, 100, projectId, 'completed'));

  const jobCreate = await op(args, token, 200, 'jobs.create', {
    projectId,
    repository: 'Valar05/home-center',
    title: `Command Center job-list observability proof ${runSafe}`,
    objective: [
      `Create hello-world.txt in the current worker workspace containing exactly ${nonce}.`,
      'This is a bounded proof of real Codex execution and job-list observability only.',
      'Do not commit, push, open a PR, deploy, register workers, alter projects, touch Drive, or mutate any external provider.',
      'After creating the file, run: cat hello-world.txt',
    ].join(' '),
    acceptanceCriteria: [
      'A real non-simulated cloud-run-debian worker is selected.',
      'Executor start, stdout or stderr, heartbeat, and finish events are recorded in order.',
      'hello-world.txt contains the requested nonce in the executor workspace.',
      'acceptance-matrix.json is uploaded and every criterion has status, evidenceRefs, notes, and blockingReason.',
      'usage-summary.json is uploaded and readable.',
      'Command Center job-list queries work for owner, status, project, and project plus status filters.',
    ],
    constraints: [
      'No GitHub mutation.',
      'No Drive mutation.',
      'No deployment mutation.',
      'No worker-registration or project-registration mutation.',
      'Only write inside the ephemeral worker clone.',
    ],
    workerRequirements: ['cloud-run-debian', 'durable-session', 'gcs-workspace-snapshot'],
    requiredArtifacts: [
      'job-intake.json',
      'orientation.md',
      'reasoning-summary.md',
      'command-log.jsonl',
      'acceptance.json',
      'acceptance-matrix.json',
      'implementation.patch',
      'changed-files.json',
      'verification.json',
      'final-report.md',
      'mutation-requests.jsonl',
    ],
    verificationCommands: ['cat hello-world.txt'],
    mutationPolicy: {editFiles: 'workspace_only', externalProviderWrite: 'deny', destructive: 'deny'},
    idempotencyKey: `job-list-observability-${runSafe}`,
  });
  const job = unwrap(jobCreate, 'job') || {};
  const jobId = job.jobId || '';
  if (!jobId) throw new Error(`jobs.create did not return jobId: ${JSON.stringify(jobCreate).slice(0, 900)}`);
  evidence.jobCreate = {jobId, status: job.status, selectedWorkerId: job.selectedWorkerId, simulatedWorker: job.simulatedWorker};
  evidence.jobId = jobId;
  evidence.listChecks.push(...await checkJobLists(args, token, 300, projectId, job.status || 'leased'));

  while (Date.now() < deadline) {
    const summary = await op(args, token, 400, 'jobs.get_summary', {jobId});
    const status = summary.result?.status || summary.status || summary.result?.job?.status || '';
    const statusLists = await checkJobLists(args, token, 500, projectId, status || 'leased');
    evidence.polls.push({at: new Date().toISOString(), status, listChecks: statusLists});
    if (['completed', 'failed', 'canceled', 'expired'].includes(status)) break;
    await sleep(args.pollMs);
  }

  const jobReadback = await op(args, token, 600, 'jobs.get', {jobId});
  const events = await op(args, token, 601, 'jobs.get_events', {jobId, limit: 100});
  const logs = await op(args, token, 602, 'jobs.get_logs', {jobId, limit: 100});
  const artifacts = await op(args, token, 603, 'jobs.get_artifacts', {jobId, limit: 100});
  const handoff = await op(args, token, 604, 'jobs.get_handoff', {jobId});
  const eventRows = unwrap(events, 'events') || [];
  const logRows = unwrap(logs, 'logs') || [];
  const artifactRows = unwrap(artifacts, 'artifacts') || [];
  const handoffPacket = unwrap(handoff, 'handoff') || {};
  const byName = artifactByName(artifactRows);
  const eventTypes = eventRows.map((event) => event.type);
  const matrix = handoffPacket.review?.acceptanceMatrix || handoffPacket.checkpoint?.acceptanceCriteriaStatus || [];
  const usage = handoffPacket.usageSummary || handoffPacket.checkpoint?.usageSummary || {};
  const finalJob = unwrap(jobReadback, 'job') || {};
  evidence.final = {
    status: finalJob.status,
    selectedWorkerId: finalJob.selectedWorkerId,
    simulatedWorker: finalJob.simulatedWorker,
    eventTypes,
    logsCount: logRows.length,
    artifacts: artifactRows.map((artifact) => ({artifactId: artifact.artifactId, name: artifact.name, kind: artifact.kind, origin: artifact.origin, sha256: artifact.sha256, uri: artifact.uri})),
    acceptanceMatrixCount: Array.isArray(matrix) ? matrix.length : 0,
    acceptanceMatrixArtifact: byName['acceptance-matrix.json'] || null,
    usageSummaryArtifact: byName['usage-summary.json'] || null,
    usageSummary: usage,
  };
  evidence.listChecks.push(...await checkJobLists(args, token, 700, projectId, 'completed'));
  const allExecutorArtifactsHaveHashes = artifactRows.filter((artifact) => artifact.origin === 'executor_workspace').every((artifact) => artifact.sha256);
  evidence.ok = finalJob.status === 'completed'
    && finalJob.selectedWorkerId === args.workerId
    && finalJob.simulatedWorker === false
    && ['executor_started', 'executor_heartbeat', 'executor_stdout', 'executor_finished', 'job_completed'].every((type) => eventTypes.includes(type))
    && byName['acceptance-matrix.json']?.sha256
    && byName['usage-summary.json']?.sha256
    && Array.isArray(matrix)
    && matrix.length > 0
    && matrix.every((item) => item.status && Array.isArray(item.evidenceRefs) && item.notes !== undefined && item.blockingReason !== undefined)
    && Object.prototype.hasOwnProperty.call(usage, 'inputTokens')
    && allExecutorArtifactsHaveHashes
    && evidence.listChecks.every((check) => check.ok);
  evidence.completedAt = new Date().toISOString();
  writeJson(evidencePath, redact(evidence));
  console.log(JSON.stringify({
    ok: evidence.ok,
    evidencePath,
    jobId,
    finalStatus: finalJob.status,
    selectedWorkerId: finalJob.selectedWorkerId,
    simulatedWorker: finalJob.simulatedWorker,
    listChecks: evidence.listChecks.length,
    acceptanceMatrixCount: evidence.final.acceptanceMatrixCount,
    usageSummary: usage,
    artifactNames: artifactRows.map((artifact) => artifact.name).sort(),
  }, null, args.json ? 0 : 2));
  if (!evidence.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
