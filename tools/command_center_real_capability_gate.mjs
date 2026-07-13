#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';
import {homedir} from 'node:os';

const DEFAULT_HOME_MCP_URL = 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp/mcp';
const DEFAULT_COMMAND_CENTER_BASE = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp';
const DEFAULT_EVIDENCE_DIR = 'tools/command_center_invokability_evidence';

function parseArgs(argv) {
  const args = {
    mcpUrl: DEFAULT_HOME_MCP_URL,
    commandCenterBase: DEFAULT_COMMAND_CENTER_BASE,
    evidenceDir: DEFAULT_EVIDENCE_DIR,
    runId: new Date().toISOString().replace(/[-:.TZ]/g, '').slice(0, 14),
    bearerToken: process.env.HOME_CENTER_MCP_BEARER_TOKEN || process.env.HOME_CENTER_COMMAND_CENTER_BEARER_TOKEN || '',
    tokenConfig: process.env.HOME_CENTER_CODEX_CONFIG || path.join(homedir(), '.config', 'home-center', 'codex-hub.json'),
    codexUrl: process.env.REAL_CODEX_CLOUD_URL || '',
    json: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === '--mcp-url') args.mcpUrl = argv[++i];
    else if (arg === '--command-center-base') args.commandCenterBase = argv[++i];
    else if (arg === '--evidence-dir') args.evidenceDir = argv[++i];
    else if (arg === '--run-id') args.runId = argv[++i];
    else if (arg === '--bearer-token') args.bearerToken = argv[++i];
    else if (arg === '--token-config') args.tokenConfig = argv[++i];
    else if (arg === '--codex-url') args.codexUrl = argv[++i];
    else if (arg === '--json') args.json = true;
    else if (arg === '--help') {
      console.log('Usage: node tools/command_center_real_capability_gate.mjs [--mcp-url URL] [--command-center-base URL] [--codex-url URL] [--run-id ID] [--json]');
      process.exit(0);
    }
  }
  return args;
}

function parseJson(text, label) {
  try { return JSON.parse(text); } catch (_) { throw new Error(`${label} did not return JSON: ${String(text || '').slice(0, 500)}`); }
}

function parseMcpResponse(text, label) {
  const dataLines = String(text || '').split(/\r?\n/).filter((line) => line.startsWith('data:')).map((line) => line.slice(5).trim());
  return parseJson(dataLines.length ? dataLines.join('\n') : text, label);
}

function toolContentJson(payload, label) {
  const text = payload?.result?.content?.find((item) => item.type === 'text')?.text || '';
  if (/^MCP error\b/.test(text)) return {mcpErrorText: text};
  return parseJson(text, label);
}

async function refreshTokenConfig(configPath) {
  if (!fs.existsSync(configPath)) return {token: '', refreshed: false, reason: 'token config missing'};
  const raw = parseJson(fs.readFileSync(configPath, 'utf8'), configPath);
  if (raw.accessToken && Number(raw.expiresAtMs || 0) > Date.now() + 60000) return {token: raw.accessToken, refreshed: false, reason: 'token still fresh'};
  if (!raw.refreshToken) return {token: raw.accessToken || raw.bearerToken || raw.token || '', refreshed: false, reason: 'refresh token missing'};
  const gatewayBase = raw.gatewayBase || 'https://us-central1-home-center-dclar.cloudfunctions.net';
  const response = await fetch(`${gatewayBase}/termuxTokenRefresh`, {
    method: 'POST',
    headers: {'content-type': 'application/json'},
    body: JSON.stringify({refreshToken: raw.refreshToken}),
  });
  const text = await response.text();
  const json = parseJson(text, 'termuxTokenRefresh');
  if (!response.ok || !json.ok || !json.access_token) return {token: raw.accessToken || raw.bearerToken || raw.token || '', refreshed: false, reason: `refresh failed status=${response.status}`};
  const next = {...raw, accessToken: json.access_token, tokenType: json.token_type || raw.tokenType || 'Bearer', expiresAtMs: Date.now() + Number(json.expires_in || 0) * 1000, refreshedAt: new Date().toISOString()};
  fs.writeFileSync(configPath, JSON.stringify(next, null, 2) + '\n', {mode: 0o600});
  try { fs.chmodSync(configPath, 0o600); } catch (_) {}
  return {token: next.accessToken, refreshed: true, reason: 'refreshed'};
}

async function loadToken(args) {
  if (args.bearerToken) return {token: args.bearerToken, source: 'env_or_arg', refreshed: false, reason: 'explicit bearer token'};
  const refreshed = await refreshTokenConfig(args.tokenConfig);
  return {token: refreshed.token || 'home-center-command-center-bridge-protocol-token', source: args.tokenConfig, refreshed: refreshed.refreshed, reason: refreshed.reason};
}

async function postMcp(mcpUrl, token, body) {
  const response = await fetch(mcpUrl, {
    method: 'POST',
    headers: {authorization: `Bearer ${token}`, 'content-type': 'application/json', accept: 'application/json, text/event-stream'},
    body: JSON.stringify(body),
  });
  const text = await response.text();
  return {status: response.status, headers: Object.fromEntries(response.headers.entries()), text};
}

async function callCommandCenter(mcpUrl, token, id, operation, args = {}) {
  const response = await postMcp(mcpUrl, token, {jsonrpc: '2.0', id, method: 'tools/call', params: {name: 'command_center_operation', arguments: {operation, args}}});
  const payload = parseMcpResponse(response.text, `command_center_operation ${operation}`);
  return {response, payload, content: toolContentJson(payload, `command_center_operation ${operation} content`)};
}

async function postWorker(base, workerToken, endpoint, body) {
  const response = await fetch(`${base}${endpoint}`, {
    method: 'POST',
    headers: {authorization: `Bearer ${workerToken}`, 'content-type': 'application/json'},
    body: JSON.stringify(body),
  });
  const text = await response.text();
  return {status: response.status, json: parseJson(text, endpoint), text};
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const tokenInfo = await loadToken(args);
  const evidenceDir = path.resolve(args.evidenceDir);
  fs.mkdirSync(evidenceDir, {recursive: true});
  const checks = [];
  const add = (name, ok, detail = {}) => checks.push({name, ok: !!ok, ...detail});
  const safeRun = args.runId.replace(/[^a-zA-Z0-9_-]/g, '-').slice(0, 60);
  const workerId = `codex-cloud-primary-real-${safeRun}`.slice(0, 120);
  const capabilities = ['codex-cloud', 'codex', 'home-drive-mcp', 'playwright', 'browser-worker', 'prepared-workspace'];

  const registered = await callCommandCenter(args.mcpUrl, tokenInfo.token, 101, 'workers.register_oneshot', {
    idempotencyKey: `real-worker-register-${safeRun}`,
    workerId,
    engine: 'codex',
    location: 'user-owned-codex-cloud-bridge',
    capabilities,
    baseWorkspace: {baseWorkspaceId: 'codex-cloud-bridge-profile', kind: 'persistent_user_owned_browser_profile', snapshotRef: 'worker-local://codex-cloud-profile', version: safeRun, restoreStrategy: 'persistent_profile'},
    limits: {concurrentActivations: 1},
  });
  const worker = registered.content.result?.worker || {};
  const workerToken = registered.content.result?.workerToken || '';
  add('real_worker_registered', registered.response.status === 200 && worker.workerId === workerId && worker.simulated === false && worker.routable !== false && workerToken.startsWith('ccw_'), {status: registered.response.status, worker});

  const project = await callCommandCenter(args.mcpUrl, tokenInfo.token, 102, 'projects.upsert', {
    idempotencyKey: `real-worker-project-${safeRun}`,
    projectId: 'home-drive',
    name: 'Home Drive',
    repository: 'Valar05/home-center',
    capability: 'home-drive-mcp',
    repositoryBinding: {kind: 'github_repository', repository: 'Valar05/home-center', path: 'services/home-drive'},
    availableWorkers: [workerId],
  });
  add('home_drive_bound_to_real_worker', project.response.status === 200 && project.content.result?.project?.availableWorkers?.includes(workerId), {status: project.response.status, project: project.content.result?.project});

  const agentId = `home-center-real-capability-${safeRun}`.slice(0, 120);
  const upsert = await callCommandCenter(args.mcpUrl, tokenInfo.token, 103, 'agents.upsert_repo_agent', {
    idempotencyKey: `real-agent-upsert-${safeRun}`,
    agentId,
    projectId: 'home-drive',
    name: 'Home Drive real capability proof',
    repository: 'Valar05/home-center',
    contextRefs: ['docs/COMMAND_CENTER_MCP.md'],
  });
  add('repo_agent_upserted', upsert.response.status === 200 && upsert.content.result?.agent?.agentId === agentId, {status: upsert.response.status, agent: upsert.content.result?.agent});

  const activation = await callCommandCenter(args.mcpUrl, tokenInfo.token, 104, 'agents.create_activation', {
    idempotencyKey: `real-activation-create-${safeRun}`,
    agentId,
    title: 'Real capability red-build proof',
    prompt: 'Claim this activation from a real user-owned Codex cloud bridge worker. Do not use simulated workers.',
    workerRequirements: ['codex-cloud', 'home-drive-mcp', 'playwright'],
    acceptanceCriteria: ['A non-simulated worker was selected', 'Worker token claimed activation', 'Worker recorded artifact and final handoff'],
    artifactRequirements: ['final-report.md'],
  });
  const activationResult = activation.content.result?.activation || {};
  const activationId = activationResult.activationId || '';
  add('activation_selected_real_worker', activation.response.status === 200 && activationResult.selectedWorkerId === workerId && activationResult.selectedWorker?.simulated === false, {status: activation.response.status, activation: activationResult});

  const claim = workerToken ? await postWorker(args.commandCenterBase, workerToken, '/agent/claim', {activationId}) : {status: 0, json: {}};
  add('worker_claimed_activation', claim.status === 200 && claim.json.claimed === true && claim.json.activation?.activationId === activationId && claim.json.activation?.claimedByWorkerId === workerId, {status: claim.status, claim: claim.json});

  const heartbeat = workerToken ? await postWorker(args.commandCenterBase, workerToken, '/agent/heartbeat', {activationId, currentPhase: 'real_capability_gate', summary: 'Real worker token heartbeat accepted.'}) : {status: 0, json: {}};
  add('worker_heartbeat_recorded', heartbeat.status === 200 && heartbeat.json.ok === true && heartbeat.json.workerId === workerId, {status: heartbeat.status, heartbeat: heartbeat.json});

  let codexRef = {status: 0, json: {skipped: true}};
  if (args.codexUrl) {
    codexRef = await postWorker(args.commandCenterBase, workerToken, '/agent/codex-ref', {activationId, url: args.codexUrl, title: 'Real Codex cloud task', status: 'running', summary: 'Recorded by real capability gate.'});
  }
  add('real_codex_cloud_ref_recorded', !!args.codexUrl && codexRef.status === 200 && codexRef.json.ok === true && codexRef.json.codexCloudRef?.surface === 'openai-codex-cloud', {status: codexRef.status, codexRef: codexRef.json, skippedReason: args.codexUrl ? '' : 'Set REAL_CODEX_CLOUD_URL or pass --codex-url to prove Drew quota Codex task.'});

  const artifact = workerToken ? await postWorker(args.commandCenterBase, workerToken, '/agent/artifacts', {activationId, artifact: {name: 'final-report.md', kind: 'final_report', body: `Real worker ${workerId} claimed activation ${activationId}.`, summary: 'Worker claim and heartbeat proof.', required: true}}) : {status: 0, json: {}};
  add('worker_artifact_recorded', artifact.status === 200 && artifact.json.ok === true && artifact.json.artifacts?.[0]?.name === 'final-report.md', {status: artifact.status, artifact: artifact.json});

  const completeStatus = args.codexUrl ? 'completed' : 'needs_human';
  const complete = workerToken ? await postWorker(args.commandCenterBase, workerToken, '/agent/complete', {activationId, status: completeStatus, finalSummary: args.codexUrl ? 'Real Codex cloud ref and worker artifact recorded.' : 'Real worker substrate proved. Awaiting actual Codex cloud task URL to prove Drew quota execution.', handoffSummary: 'Review real capability gate evidence.'}) : {status: 0, json: {}};
  add('activation_terminal_handoff_recorded', complete.status === 200 && complete.json.ok === true && complete.json.handoff?.packetVersion === 'command-center-codex-cloud-handoff-v1', {status: complete.status, complete: complete.json});

  const result = {
    ok: checks.every((check) => check.ok),
    mode: args.codexUrl ? 'real_codex_cloud_ref' : 'real_worker_substrate_red_until_codex_url',
    mcpUrl: args.mcpUrl,
    commandCenterBase: args.commandCenterBase,
    workerId,
    activationId,
    checks,
    tokenSource: tokenInfo.source,
    tokenRefreshed: tokenInfo.refreshed,
    generatedAt: new Date().toISOString(),
  };
  const evidencePath = path.join(evidenceDir, `command_center_real_capability_${safeRun}.json`);
  fs.writeFileSync(evidencePath, JSON.stringify(result, null, 2) + '\n');
  const summary = {ok: result.ok, mode: result.mode, evidencePath, failed: checks.filter((check) => !check.ok).map((check) => check.name), workerId, activationId};
  console.log(JSON.stringify(summary, null, args.json ? 0 : 2));
  if (!result.ok) process.exit(1);
}

main().catch((err) => {
  console.error(err.stack || err.message || String(err));
  process.exit(1);
});
