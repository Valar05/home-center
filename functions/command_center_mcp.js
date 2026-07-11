const {createHash, randomUUID} = require('node:crypto');
const express = require('express');
const {z} = require('zod/v4');
const {McpServer} = require('@modelcontextprotocol/sdk/server/mcp.js');
const {StreamableHTTPServerTransport} = require('@modelcontextprotocol/sdk/server/streamableHttp.js');
const {APP_CONTROL_COLLECTIONS, APP_CONTROL_DEFAULT_SEEDS, appControlProfileObjectId, appControlProfilePath} = require('./app_control_cloud');

const DEFAULT_COMMAND_CENTER_PUBLIC_BASE = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp';
const COMMAND_CENTER_PUBLIC_BASE = process.env.COMMAND_CENTER_MCP_PUBLIC_BASE || DEFAULT_COMMAND_CENTER_PUBLIC_BASE;
const COMMAND_CENTER_RESOURCE = `${COMMAND_CENTER_PUBLIC_BASE}/mcp`;
const COMMAND_CENTER_RESOURCE_METADATA = `${COMMAND_CENTER_PUBLIC_BASE}/.well-known/oauth-protected-resource`;
const HOME_CENTER_AUTHORIZATION_SERVER_BASE = process.env.HOME_CENTER_MCP_PUBLIC_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp';
const COMMAND_CENTER_COLLECTIONS = Object.freeze({
  projects: 'commandCenterProjects',
  jobs: 'commandCenterJobs',
  workers: 'commandCenterWorkers',
  leases: 'commandCenterLeases',
  events: 'commandCenterEvents',
  questions: 'commandCenterQuestions',
  mutationAuthorizations: 'commandCenterMutationAuthorizations',
  artifacts: 'commandCenterArtifacts',
  logs: 'commandCenterLogs',
  checkpoints: 'commandCenterCheckpoints',
  bucketObjects: 'commandCenterBucketObjects',
  baseWorkspaces: 'commandCenterBaseWorkspaces',
  repoAgents: 'commandCenterRepoAgents',
  agentSessions: 'commandCenterAgentSessions',
  agentActivations: 'commandCenterAgentActivations',
  agentArtifacts: 'commandCenterAgentArtifacts',
  codexCloudRefs: 'commandCenterCodexCloudRefs',
  agentContextSnapshots: 'commandCenterAgentContextSnapshots',
  jobActivations: 'commandCenterJobActivations',
  workerTokens: 'commandCenterWorkerTokens',
  idempotency: 'commandCenterIdempotency',
});
const COMMAND_CENTER_DEFAULT_BUCKET_ID = 'command-center';
const COMMAND_CENTER_BUCKET_KINDS = Object.freeze([
  'memory.past_log',
  'memory.current_condensed',
  'skill.scratch',
  'skill.promoted',
  'note.cross_repo',
]);
const COMMAND_CENTER_BUCKET_LAYOUT = Object.freeze({
  bucketId: COMMAND_CENTER_DEFAULT_BUCKET_ID,
  purpose: 'Command Center managed knowledge bucket for durable execution memory, skills, and cross-repository notes.',
  storagePolicy: {
    metadataStore: COMMAND_CENTER_COLLECTIONS.bucketObjects,
    largeObjectRefs: 'Use objectUri for Cloud Storage, Drive, GitHub, or local artifact refs; do not inline secrets.',
    inlineBodyMaxChars: 64000,
    secretPolicy: 'No bearer tokens, worker tokens, OAuth secrets, private keys, passwords, or reusable credentials.',
  },
  lanes: {
    'memory/past-logs': {kind: 'memory.past_log', role: 'append-only historical execution logs and evidence summaries'},
    'memory/current-condensed': {kind: 'memory.current_condensed', role: 'latest compact resumable state per job or project'},
    'skills/scratch': {kind: 'skill.scratch', role: 'unpromoted candidate procedures captured from runs'},
    'skills/promoted': {kind: 'skill.promoted', role: 'reviewed reusable procedures with acceptance evidence'},
    'notes/cross-repo': {kind: 'note.cross_repo', role: 'project-spanning engineering notes and links'},
  },
});
const COMMAND_CENTER_ALLOWED_STATUSES = ['queued', 'leased', 'running', 'question', 'awaiting_mutation_authorization', 'completed', 'failed', 'canceled'];
const COMMAND_CENTER_EXECUTION_MODES = ['one_shot'];
const COMMAND_CENTER_REQUIRED_ARTIFACTS = Object.freeze([
  'job-intake.json',
  'orientation.md',
  'reasoning-summary.md',
  'command-log.jsonl',
  'implementation.patch',
  'changed-files.json',
  'verification.json',
  'final-report.md',
  'mutation-requests.jsonl',
]);
const COMMAND_CENTER_EXECUTOR_PULSE_ARTIFACTS = Object.freeze([
  'job-intake.json',
  'pulse-proof.json',
  'stdout-transcript.txt',
  'command-log.jsonl',
  'acceptance.json',
  'acceptance-matrix.json',
  'usage-summary.json',
  'verification.json',
  'final-report.md',
]);
const COMMAND_CENTER_CODEX_SMOKE_ARTIFACTS = Object.freeze([
  'job-intake.json',
  'stdout-transcript.txt',
  'stderr-transcript.txt',
  'command-log.jsonl',
  'acceptance.json',
  'acceptance-matrix.json',
  'usage-summary.json',
  'verification.json',
  'final-report.md',
]);
const COMMAND_CENTER_DEFAULT_BASE_WORKSPACE = Object.freeze({
  baseWorkspaceId: 'base-default-oneshot',
  kind: 'prepared_workspace_snapshot',
  snapshotRef: 'worker-local://prepared-workspaces/default',
  version: 'unversioned',
  restoreStrategy: 'copy_overlay',
  immutable: true,
  toolchains: [],
});
const COMMAND_CENTER_DEFAULT_WORKERS = [{
  workerId: 'cloud-codex-primary',
  engine: 'codex',
  location: 'cloud',
  health: 'placeholder',
  capabilities: [],
  advertisedCapabilities: ['codex', 'github', 'node', 'python', 'firebase', 'network', 'one-shot-worker', 'prepared-workspace', 'browser-worker', 'playwright', 'chrome-desktop', 'web-hands'],
  limits: {concurrentJobs: 0},
  simulated: true,
  routable: false,
  stalePremise: 'Non-routable placeholder only; not a real OpenAI Codex cloud worker. Register or activate a real worker before leasing compute.',
}];
const COMMAND_CENTER_DEFAULT_PROJECTS = Object.freeze({
  'home-drive': Object.freeze({
    projectId: 'home-drive',
    name: 'Home Drive',
    repository: 'Valar05/home-center',
    capability: 'home-drive-mcp',
    repositoryBinding: {kind: 'github_repository', repository: 'Valar05/home-center', path: 'services/home-drive'},
    currentBranch: 'main',
    projectPacketRefs: ['docs/COMMAND_CENTER_MCP.md', 'docs/APP_CONTROL_BUCKET.md'],
    recentRelevantOutcomes: [],
    availableWorkers: ['home-drive-primary'],
    durable: true,
  }),
});

function safeText(value, max = 12000) {
  const text = typeof value === 'string' ? value.trim() : '';
  return text.length > max ? text.slice(0, max) : text;
}

function safeList(value, maxItems = 50, maxText = 500) {
  return Array.isArray(value) ? value.slice(0, maxItems).map((item) => safeText(item, maxText)).filter(Boolean) : [];
}

function safeObject(value) {
  return value && typeof value === 'object' && !Array.isArray(value) ? value : {};
}

function safeBoolean(value, fallback = false) {
  return typeof value === 'boolean' ? value : fallback;
}

function hashText(value, length = 16) {
  return createHash('sha256').update(String(value || '')).digest('hex').slice(0, length);
}

function fullHash(value) {
  return createHash('sha256').update(String(value || '')).digest('hex');
}

function tokenDigest(value) {
  return createHash('sha256').update(String(value || '')).digest('hex');
}

function slug(value, fallback = 'project') {
  const text = safeText(value, 120).toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '');
  return text || fallback;
}

function headerValue(headers, name) {
  if (!headers) return '';
  if (typeof headers.get === 'function') return headers.get(name) || headers.get(name.toLowerCase()) || '';
  return headers[name] || headers[name.toLowerCase()] || '';
}

function bearerFromExtra(extra) {
  const header = headerValue(extra && extra.requestInfo && extra.requestInfo.headers, 'authorization');
  const match = String(header || '').match(/^Bearer\s+(.+)$/i);
  if (!match) {
    const err = new Error('Missing Command Center bearer token. Connect this MCP app before using dispatch tools.');
    err.status = 401;
    throw err;
  }
  return match[1];
}

async function callerFromExtra(admin, extra) {
  const token = bearerFromExtra(extra);
  const snap = await collection(admin, 'mcpOAuthAccessTokens').doc(tokenDigest(token)).get();
  if (!snap.exists) {
    const err = new Error('Command Center bearer token is not a valid Home Center MCP OAuth token.');
    err.status = 401;
    throw err;
  }
  const data = snap.data() || {};
  if (data.revokedAtMs || Number(data.expiresAtMs || 0) <= Date.now()) {
    const err = new Error(data.revokedAtMs ? 'Command Center bearer token was revoked.' : 'Command Center bearer token expired.');
    err.status = 401;
    throw err;
  }
  const email = safeText(data.email, 320).toLowerCase();
  const actor = email || `mcp:${hashText(token, 12)}`;
  return {authKind: 'home_center_mcp_oauth', tokenHash: hashText(token, 24), actor, ownerKey: ownerKeyFromActor(actor)};
}

function ownerKeyFromActor(actor) {
  return `owner_${hashText(safeText(actor, 320).toLowerCase() || 'anonymous', 32)}`;
}

function ownerKeyFromCaller(caller = {}) {
  return safeText(caller.ownerKey, 80) || ownerKeyFromActor(caller.actor || caller.tokenHash || 'command_center');
}

function attachOwnerKey(payload, caller = {}) {
  return {...payload, ownerKey: ownerKeyFromCaller(caller)};
}

function assertOwnerAccess(record = {}, caller = {}, noun = 'Command Center record') {
  const recordOwner = safeText(record.ownerKey, 80);
  if (!recordOwner) return;
  if (recordOwner === ownerKeyFromCaller(caller)) return;
  const err = new Error(`${noun} not found for this Command Center owner.`);
  err.status = 404;
  throw err;
}
function hasBearerAuthorization(req) {
  const header = req && typeof req.get === 'function' ? req.get('Authorization') : '';
  return /^Bearer\s+.+/i.test(String(header || ''));
}

function oauthChallenge() {
  return `Bearer resource_metadata="${COMMAND_CENTER_RESOURCE_METADATA}"`;
}

function rejectMissingTransportAuth(req, res) {
  if (hasBearerAuthorization(req)) return false;
  res.set('WWW-Authenticate', oauthChallenge());
  res.status(401).json({
    error: 'authorization_required',
    error_description: 'Connect Command Center MCP before using dispatch tools.',
    resource_metadata: COMMAND_CENTER_RESOURCE_METADATA,
  });
  return true;
}

function textResult(value) {
  return {content: [{type: 'text', text: JSON.stringify(value, null, 2)}]};
}

function collection(admin, name) {
  return admin.firestore().collection(name);
}

function requireIdempotencyKey(value) {
  const key = safeText(value, 180);
  if (!key) {
    const err = new Error('idempotencyKey is required for Command Center mutations.');
    err.status = 400;
    throw err;
  }
  return key;
}

function cleanMutationPolicy(policy) {
  const src = safeObject(policy);
  return {
    editFiles: safeText(src.editFiles, 40) || 'allowed',
    runTests: safeText(src.runTests, 40) || 'allowed',
    commit: safeText(src.commit, 40) || 'allowed',
    createIssue: safeText(src.createIssue, 40) || 'allowed',
    createPullRequest: safeText(src.createPullRequest, 40) || 'allowed',
    push: safeText(src.push, 40) || 'confirm',
    merge: safeText(src.merge, 40) || 'confirm',
    deployPreview: safeText(src.deployPreview, 40) || 'confirm',
    deployProduction: safeText(src.deployProduction, 40) || 'confirm',
    externalProviderWrite: safeText(src.externalProviderWrite, 40) || 'confirm',
    destructive: safeText(src.destructive, 40) || 'deny',
  };
}

function requiredArtifactsForExecutionMode(mode) {
  if (mode === 'executor_pulse') return COMMAND_CENTER_EXECUTOR_PULSE_ARTIFACTS;
  if (mode === 'codex_smoke') return COMMAND_CENTER_CODEX_SMOKE_ARTIFACTS;
  return COMMAND_CENTER_REQUIRED_ARTIFACTS;
}

function cleanExecutionMode(value) {
  const mode = safeText(value, 80) || 'one_shot';
  if (COMMAND_CENTER_EXECUTION_MODES.includes(mode)) return mode;
  const err = new Error(`Unsupported executionMode: ${mode}.`);
  err.status = 400;
  throw err;
}

function cleanRequiredArtifacts(value, mode = 'one_shot') {
  const requested = safeList(value, 60, 180);
  const names = new Set([...requiredArtifactsForExecutionMode(mode), ...requested]);
  return Array.from(names);
}

function cleanBaseWorkspace(value) {
  const src = safeObject(value);
  return {
    baseWorkspaceId: safeText(src.baseWorkspaceId, 140) || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE.baseWorkspaceId,
    kind: safeText(src.kind, 80) || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE.kind,
    snapshotRef: safeText(src.snapshotRef, 600) || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE.snapshotRef,
    version: safeText(src.version, 120) || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE.version,
    restoreStrategy: safeText(src.restoreStrategy, 80) || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE.restoreStrategy,
    immutable: safeBoolean(src.immutable, true),
    toolchains: safeList(src.toolchains, 60, 160),
  };
}

function cleanOneShotExecution(args = {}) {
  const executionMode = cleanExecutionMode(args.executionMode);
  return {
    executionMode,
    baseWorkspace: cleanBaseWorkspace(args.baseWorkspace),
    requiredArtifacts: cleanRequiredArtifacts(args.requiredArtifacts, executionMode),
    stopConditions: safeList(args.stopConditions, 40, 500),
    verificationCommands: safeList(args.verificationCommands, 40, 500),
    promptPacketVersion: 'command-center-one-shot-v1',
  };
}

function cleanProjectId(value, repository = '') {
  const projectId = slug(safeText(value, 120) || repository, 'project');
  if (!/^[a-z0-9][a-z0-9-]{1,118}[a-z0-9]$/.test(projectId)) {
    const err = new Error('A valid projectId is required.');
    err.status = 400;
    throw err;
  }
  return projectId;
}

function cleanAgentId(value, projectId = '', repository = '') {
  const base = safeText(value, 160) || [projectId, repository, 'repo-agent'].filter(Boolean).join('-');
  const agentId = slug(base, 'repo-agent');
  if (!/^[a-z0-9][a-z0-9-]{1,158}[a-z0-9]$/.test(agentId)) {
    const err = new Error('A valid agentId is required.');
    err.status = 400;
    throw err;
  }
  return agentId;
}

function cleanSessionId(value) {
  const sessionId = safeText(value, 180);
  if (sessionId && /^[A-Za-z0-9_.:-]{3,180}$/.test(sessionId)) return sessionId;
  if (!sessionId) return `session_${randomUUID()}`;
  const err = new Error('A valid sessionId is required.');
  err.status = 400;
  throw err;
}

function cleanActivationId(value) {
  const activationId = safeText(value, 180);
  if (activationId && /^activation_[A-Za-z0-9_-]{8,160}$/.test(activationId)) return activationId;
  if (!activationId) return `activation_${randomUUID()}`;
  const err = new Error('A valid activationId is required.');
  err.status = 400;
  throw err;
}

function cleanRepoAgent(args = {}, caller = {}) {
  const repository = safeText(args.repository, 240);
  const projectId = cleanProjectId(args.projectId, repository || args.name || 'project');
  const agentId = cleanAgentId(args.agentId, projectId, repository);
  const nowMs = Date.now();
  return {
    agentId,
    agentType: 'repo_agent',
    projectId,
    name: safeText(args.name, 240) || repository || projectId,
    repository,
    domain: safeText(args.domain, 200),
    purpose: safeText(args.purpose, 2000) || 'Durable Command Center context owner for real OpenAI Codex cloud activations.',
    status: safeText(args.status, 80) || 'active',
    codexCloudSurface: COMMAND_CENTER_CODEX_CLOUD_SURFACE,
    contextRefs: safeList(args.contextRefs, 80, 800),
    preferredTools: safeList(args.preferredTools, 80, 160),
    validationRules: safeList(args.validationRules, 80, 500),
    openQuestions: safeList(args.openQuestions, 80, 500),
    createdBy: safeText(args.createdBy, 160) || caller.actor || 'command_center',
    updatedBy: caller.actor || safeText(args.updatedBy, 160),
    ownerKey: ownerKeyFromCaller(caller),
    createdAtMs: Number(args.createdAtMs || 0) || nowMs,
    updatedAtMs: nowMs,
  };
}

function cleanAgentSession(args = {}, agent = {}, caller = {}) {
  const sessionId = cleanSessionId(args.sessionId);
  const nowMs = Date.now();
  const repository = safeText(args.repository || agent.repository, 240);
  const projectId = cleanProjectId(args.projectId || agent.projectId || args.name || agent.name || 'general-worker-session', repository);
  const agentId = cleanAgentId(args.agentId || agent.agentId || `${projectId}-worker-session`, projectId, repository);
  const restoreStrategy = safeText(args.restoreStrategy || safeObject(args.workspaceSnapshot).restoreStrategy, 80) || 'gcs_snapshot';
  return {
    sessionId,
    sessionKind: safeText(args.sessionKind, 80) || 'durable_worker_session',
    agentId,
    projectId,
    repository,
    repositoryOptional: true,
    repoRequired: args.repoRequired === true,
    workerFamily: safeText(args.workerFamily, 120) || 'cloud-run-debian-codex',
    runtime: safeText(args.runtime, 120) || 'cloud-run-debian',
    title: safeText(args.title, 300) || 'Durable Codex worker session',
    purpose: safeText(args.purpose, 2000) || 'Resumable Codex worker session with durable workspace and context.',
    status: safeText(args.status, 80) || 'active',
    latestActivationId: safeText(args.latestActivationId, 180),
    latestCodexCloudRefId: safeText(args.latestCodexCloudRefId, 180),
    currentWorkspaceSnapshotRef: safeText(args.currentWorkspaceSnapshotRef || safeObject(args.workspaceSnapshot).snapshotRef, 1200),
    currentWorkspaceSnapshotDigest: safeText(args.currentWorkspaceSnapshotDigest || safeObject(args.workspaceSnapshot).sha256, 160),
    restoreStrategy: COMMAND_CENTER_DURABLE_SESSION_RESTORE_STRATEGIES.includes(restoreStrategy) ? restoreStrategy : 'gcs_snapshot',
    workspaceState: safeObject(args.workspaceState),
    mutationState: safeObject(args.mutationState),
    currentSummary: safeText(args.currentSummary, 8000),
    contextRefs: safeList(args.contextRefs, 80, 800),
    artifactRefs: safeList(args.artifactRefs, 120, 800),
    openQuestions: safeList(args.openQuestions, 80, 1000),
    preferredWorkerIds: safeList(args.preferredWorkerIds, 80, 160),
    createdBy: safeText(args.createdBy, 160) || caller.actor || 'command_center',
    updatedBy: caller.actor || safeText(args.updatedBy, 160),
    ownerKey: ownerKeyFromCaller(caller),
    createdAtMs: Number(args.createdAtMs || 0) || nowMs,
    updatedAtMs: nowMs,
  };
}

function cleanActivationTask(args = {}) {
  const task = safeObject(args.task);
  return {
    taskType: safeText(args.taskType || task.taskType, 80) || 'codex_cloud',
    title: safeText(args.title || task.title, 300) || 'Codex cloud activation',
    prompt: safeText(args.prompt || task.prompt, 12000),
    trigger: safeText(args.trigger || task.trigger, 120) || 'chatgpt',
    inputs: safeObject(args.inputs || task.inputs),
    acceptanceCriteria: safeList(args.acceptanceCriteria || task.acceptanceCriteria, 80, 1000),
    constraints: safeList(args.constraints || task.constraints, 80, 1000),
    artifactRequirements: safeList(args.artifactRequirements || task.artifactRequirements, 80, 240),
    executionPolicy: safeObject(args.executionPolicy || task.executionPolicy),
  };
}

function cleanCodexCloudRef(args = {}) {
  const url = safeText(args.url || args.codexCloudUrl, 1200);
  const title = safeText(args.title, 300) || 'Codex cloud task';
  const surface = safeText(args.surface, 120) || COMMAND_CENTER_CODEX_CLOUD_SURFACE.surfaceId;
  const textForSecretScan = [url, title, args.summary, args.resumeHandle, ...(Array.isArray(args.evidenceRefs) ? args.evidenceRefs : [])].join('\n');
  if (containsForbiddenSecret(textForSecretScan)) {
    const err = new Error('Codex cloud refs must not contain reusable credentials, bearer tokens, cookies, or session material.');
    err.status = 400;
    throw err;
  }
  if (url && !/^https:\/\/(chatgpt\.com|chat\.openai\.com)\/codex\/?/i.test(url)) {
    const err = new Error('Codex cloud refs must point to the real ChatGPT/OpenAI Codex cloud surface.');
    err.status = 400;
    throw err;
  }
  return {
    codexCloudRefId: safeText(args.codexCloudRefId, 180) || `codex_ref_${hashText(`${url}:${Date.now()}:${randomUUID()}`, 32)}`,
    surface,
    url,
    title,
    status: safeText(args.status, 80) || 'recorded',
    resumeHandle: safeText(args.resumeHandle, 500),
    summary: safeText(args.summary, 4000),
    evidenceRefs: safeList(args.evidenceRefs, 80, 800),
    credentialBoundary: COMMAND_CENTER_CODEX_CLOUD_SURFACE.credentialPolicy,
  };
}

function cleanJobId(value) {
  const jobId = safeText(value, 140);
  if (!/^job_[A-Za-z0-9_-]{8,120}$/.test(jobId)) {
    const err = new Error('A valid jobId is required.');
    err.status = 400;
    throw err;
  }
  return jobId;
}

function cleanBucketId(value) {
  const bucketId = slug(safeText(value, 120) || COMMAND_CENTER_DEFAULT_BUCKET_ID, COMMAND_CENTER_DEFAULT_BUCKET_ID);
  if (!/^[a-z0-9][a-z0-9-]{1,118}[a-z0-9]$/.test(bucketId)) {
    const err = new Error('A valid bucketId is required.');
    err.status = 400;
    throw err;
  }
  return bucketId;
}

function cleanBucketKind(value) {
  const kind = safeText(value, 80);
  if (!COMMAND_CENTER_BUCKET_KINDS.includes(kind)) {
    const err = new Error(`bucket kind must be one of: ${COMMAND_CENTER_BUCKET_KINDS.join(', ')}`);
    err.status = 400;
    throw err;
  }
  return kind;
}

function bucketLaneForKind(kind) {
  for (const [lane, spec] of Object.entries(COMMAND_CENTER_BUCKET_LAYOUT.lanes)) {
    if (spec.kind === kind) return lane;
  }
  return 'notes/cross-repo';
}

function cleanBucketPath(value, kind, fallbackTitle = '') {
  const lane = bucketLaneForKind(kind);
  const requested = safeText(value, 500).replace(/\\/g, '/').replace(/^\/+/, '');
  const suffix = slug(fallbackTitle || kind, 'entry');
  const candidate = requested || `${lane}/${suffix}.md`;
  const parts = candidate.split('/').map((part) => slug(part.replace(/\.[a-z0-9]+$/i, ''), 'entry')).filter(Boolean);
  const extension = /\.(json|jsonl|md|txt)$/i.test(candidate) ? candidate.match(/\.(json|jsonl|md|txt)$/i)[0].toLowerCase() : '.md';
  const clean = parts.join('/');
  return clean.startsWith(lane + '/') ? clean + extension : `${lane}/${clean}${extension}`;
}

function containsForbiddenSecret(text) {
  const value = String(text || '');
  return /Bearer\s+[A-Za-z0-9._~+/=-]{12,}/i.test(value)
    || /\bccw_[A-Za-z0-9_-]{12,}(?:_[A-Za-z0-9_-]{12,})?\b/.test(value)
    || /\bgh[pousr]_[A-Za-z0-9_]{20,}\b/.test(value)
    || /\bya29\.[A-Za-z0-9._-]{20,}\b/.test(value)
    || /\bAIza[A-Za-z0-9_-]{20,}\b/.test(value)
    || /\b[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b/.test(value)
    || /(?:TOKEN|SECRET|PASSWORD|CREDENTIAL)\s*[=:]\s*["']?[^"'\s]{12,}/i.test(value);
}

function cleanBucketObject(args = {}, caller = {}) {
  const kind = cleanBucketKind(args.kind);
  const bucketId = cleanBucketId(args.bucketId);
  const title = safeText(args.title, 300) || kind;
  const body = safeText(args.body, COMMAND_CENTER_BUCKET_LAYOUT.storagePolicy.inlineBodyMaxChars);
  const objectUri = safeText(args.objectUri, 1000);
  if (containsForbiddenSecret([title, args.summary, body, objectUri, ...(Array.isArray(args.sourceRefs) ? args.sourceRefs : []), ...(Array.isArray(args.evidenceRefs) ? args.evidenceRefs : [])].join('\n'))) {
    const err = new Error('Command Center bucket objects must not contain reusable secrets or bearer credentials.');
    err.status = 400;
    throw err;
  }
  const objectPath = cleanBucketPath(args.path, kind, title);
  const nowMs = Date.now();
  const projectId = args.projectId ? cleanProjectId(args.projectId) : '';
  const jobId = args.jobId ? cleanJobId(args.jobId) : '';
  const contentHash = body ? fullHash(body) : safeText(args.contentHash, 128);
  const objectId = safeText(args.objectId, 180) || `bucket_${hashText(`${bucketId}:${objectPath}:${contentHash || nowMs}`, 32)}`;
  return {
    objectId,
    bucketId,
    kind,
    lane: bucketLaneForKind(kind),
    path: objectPath,
    title,
    summary: safeText(args.summary, 2000),
    body,
    objectUri,
    contentHash,
    projectId,
    repository: safeText(args.repository, 240),
    jobId,
    sourceRefs: safeList(args.sourceRefs, 80, 800),
    evidenceRefs: safeList(args.evidenceRefs, 80, 800),
    tags: safeList(args.tags, 80, 120),
    promotionState: kind === 'skill.promoted' ? 'promoted' : safeText(args.promotionState, 80) || (kind === 'skill.scratch' ? 'scratch' : 'active'),
    supersedes: safeList(args.supersedes, 40, 180),
    createdBy: safeText(args.createdBy, 160) || caller.actor || 'command_center',
    updatedBy: caller.actor || safeText(args.updatedBy, 160),
    createdAtMs: nowMs,
    updatedAtMs: nowMs,
    provenance: {
      actor: caller.actor || safeText(args.actor, 160),
      source: safeText(args.source, 200) || 'command_center.bucket.put_object',
      idempotencyKey: safeText(args.idempotencyKey, 180),
      noSecrets: true,
    },
  };
}

function cleanWorker(worker) {
  const data = safeObject(worker);
  const liveness = deriveWorkerLiveness(data);
  const retired = data.retiredAtMs || data.retired === true || safeText(data.status, 80) === 'retired';
  return {
    workerId: safeText(data.workerId, 120),
    engine: safeText(data.engine, 80) || 'codex',
    location: safeText(data.location, 80) || 'cloud',
    registryHealth: liveness.registryHealth,
    health: liveness.health,
    livenessState: liveness.livenessState,
    livenessReason: liveness.livenessReason,
    heartbeatAgeMs: liveness.heartbeatAgeMs,
    heartbeatFresh: liveness.heartbeatFresh,
    activationAgeMs: liveness.activationAgeMs,
    activationFresh: liveness.activationFresh,
    activatable: liveness.activatable,
    capabilities: safeList(data.capabilities, 80, 120),
    baseWorkspaces: Array.isArray(data.baseWorkspaces) ? data.baseWorkspaces.slice(0, 20).map(cleanBaseWorkspace) : [],
    limits: safeObject(data.limits),
    activation: normalizeActivationChannel(data.activation),
    runtime: safeObject(data.runtime),
    cloudRunJob: safeObject(data.cloudRunJob),
    sessionPolicy: safeObject(data.sessionPolicy),
    repositoryAffinity: safeList(data.repositoryAffinity, 80, 240),
    simulated: data.simulated === true,
    registryRoutable: retired ? false : liveness.registryRoutable,
    routable: retired ? false : liveness.routable,
    lastHeartbeatAtMs: liveness.lastHeartbeatAtMs,
    status: retired ? 'retired' : (safeText(data.status, 80) || 'active'),
    retiredAtMs: Number(data.retiredAtMs || 0) || 0,
    retiredBy: safeText(data.retiredBy, 160),
    retireReason: safeText(data.retireReason, 1000),
    ownerKey: safeText(data.ownerKey, 80),
    oneShot: data.oneShot !== false,
  };
}

function cleanProjectPacket(args = {}) {
  const repository = safeText(args.repository, 240);
  const projectId = cleanProjectId(args.projectId, repository || args.name || 'project');
  return {
    projectId,
    name: safeText(args.name, 200) || repository || projectId,
    repository,
    capability: safeText(args.capability, 200),
    repositoryBinding: safeObject(args.repositoryBinding),
    activeTickets: Array.isArray(args.activeTickets) ? args.activeTickets.slice(0, 50).map((ticket) => safeObject(ticket)) : [],
    currentBranch: safeText(args.currentBranch, 120),
    projectPacketRefs: safeList(args.projectPacketRefs, 80, 800),
    recentRelevantOutcomes: Array.isArray(args.recentRelevantOutcomes) ? args.recentRelevantOutcomes.slice(0, 50).map((outcome) => safeObject(outcome)) : [],
    availableWorkers: safeList(args.availableWorkers, 80, 160),
    durable: args.durable !== false,
    updatedAtMs: Date.now(),
    createdAtMs: Number(args.createdAtMs || 0) || Date.now(),
  };
}

async function workerRecords(admin) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).limit(50).get();
  const byId = new Map(COMMAND_CENTER_DEFAULT_WORKERS.map((worker) => [worker.workerId, worker]));
  snap.forEach((doc) => byId.set(doc.id, cleanWorker({workerId: doc.id, ...(doc.data() || {})})));
  return Array.from(byId.values()).filter((worker) => worker.workerId);
}

function recordsVisibleToCaller(records, caller = null) {
  if (!caller) return records;
  const ownerKey = ownerKeyFromCaller(caller);
  return records.filter((record) => !safeText(record.ownerKey, 80) || record.ownerKey === ownerKey);
}

function queryOwnedCollection(admin, collectionName, caller) {
  return collection(admin, collectionName).where('ownerKey', '==', ownerKeyFromCaller(caller));
}

function commandCenterJobsListRequiredIndex(args = {}) {
  const fields = ['ownerKey ASC'];
  if (args.projectId) fields.push('projectId ASC');
  if (args.status) fields.push('status ASC');
  fields.push('createdAtMs DESC');
  if (args.status && !args.projectId) fields.push('__name__ DESC');
  return {collectionGroup: COMMAND_CENTER_COLLECTIONS.jobs, fields};
}

function commandCenterJobsListIndexError(args = {}, err = null) {
  return {
    jobs: [],
    error: 'missing_firestore_index',
    diagnostic: safeText(err && err.message, 2000),
    requiredIndex: commandCenterJobsListRequiredIndex(args),
  };
}

function normalizeActivationChannel(value = {}) {
  const data = safeObject(value);
  const mode = safeText(data.mode, 40) || (safeText(data.endpoint, 1000) ? 'push' : '');
  return {
    mode: ['push', 'poll', 'cloud_run_job'].includes(mode) ? mode : '',
    endpoint: safeText(data.endpoint || data.url, 1200),
    authRef: safeText(data.authRef || data.secretRef || data.tokenRef, 240),
    verifiedAtMs: Number(data.verifiedAtMs || data.lastVerifiedAtMs || 0) || 0,
  };
}

function isWorkerLeaseEligible(worker, requirements, options = {}) {
  const nowMs = Number(options.nowMs || 0) || Date.now();
  const requireActivationChannel = options.requireActivationChannel !== false;
  const reqs = safeList(requirements, 40, 120).map((req) => req.toLowerCase());
  const caps = new Set((worker.capabilities || []).map((cap) => String(cap).toLowerCase()));
  const liveness = deriveWorkerLiveness(worker, nowMs);
  if (worker.simulated === true) return {eligible: false, reason: 'worker is simulated'};
  if (worker.status === 'retired' || worker.retiredAtMs) return {eligible: false, reason: 'worker is retired'};
  if (worker.registryRoutable === false) return {eligible: false, reason: 'worker is not routable'};
  const missing = reqs.filter((req) => !caps.has(req));
  if (missing.length) return {eligible: false, reason: `missing capabilities: ${missing.join(', ')}`};
  const requiresCloudActivation = reqs.includes('codex-cloud') || caps.has('codex-cloud');
  if (requiresCloudActivation) {
    const activation = normalizeActivationChannel(worker.activation);
    const heartbeatFresh = Number(worker.lastHeartbeatAtMs || 0) > 0 && nowMs - Number(worker.lastHeartbeatAtMs || 0) <= COMMAND_CENTER_WORKER_HEARTBEAT_FRESH_MS;
    const activationFresh = activation.verifiedAtMs > 0 && nowMs - activation.verifiedAtMs <= COMMAND_CENTER_ACTIVATION_VERIFIED_FRESH_MS;
    const hasPushActivation = activation.mode === 'push' && !!activation.endpoint && activationFresh;
    const hasPollActivation = activation.mode === 'poll' && heartbeatFresh;
    const hasConfiguredChannel = (activation.mode === 'push' && !!activation.endpoint) || activation.mode === 'poll';
    if (requireActivationChannel && hasConfiguredChannel && !hasPushActivation && !hasPollActivation) return {eligible: false, reason: 'codex-cloud worker heartbeat or activation verification is stale'};
    if (requireActivationChannel && !hasPushActivation && !hasPollActivation) return {eligible: false, reason: 'codex-cloud worker has no verified push activation channel or live poll channel'};
    if (!heartbeatFresh && !activationFresh) return {eligible: false, reason: 'codex-cloud worker heartbeat or activation verification is stale'};
  }
  const requiresCloudRun = reqs.includes('cloud-run-debian') || reqs.includes('durable-session') || caps.has('cloud-run-debian');
  if (requiresCloudRun) {
    const activation = normalizeActivationChannel(worker.activation);
    const heartbeatFresh = Number(worker.lastHeartbeatAtMs || 0) > 0 && nowMs - Number(worker.lastHeartbeatAtMs || 0) <= COMMAND_CENTER_WORKER_HEARTBEAT_FRESH_MS;
    if (activation.mode !== 'cloud_run_job') return {eligible: false, reason: 'durable cloud sessions require a cloud_run_job activation channel'};
    if (!safeObject(worker.cloudRunJob).jobName || !safeObject(worker.cloudRunJob).region || !safeObject(worker.cloudRunJob).projectId) return {eligible: false, reason: 'cloud_run_job worker requires projectId, region, and jobName'};
    if (safeObject(worker.sessionPolicy).durable !== true) return {eligible: false, reason: 'cloud_run_job worker must advertise durable session policy'};
    if (safeObject(worker.sessionPolicy).snapshotStore !== 'gcs') return {eligible: false, reason: 'durable cloud sessions require gcs snapshot storage'};
    if (liveness.registryHealth !== 'healthy') return {eligible: false, reason: liveness.livenessReason};
    if (!heartbeatFresh && !liveness.activatable) return {eligible: false, reason: 'cloud_run_job worker is neither live nor activatable'};
    return {eligible: true, reason: heartbeatFresh ? 'live cloud_run_job worker' : 'activatable cloud_run_job worker'};
  }
  if (liveness.health !== 'healthy') return {eligible: false, reason: liveness.livenessReason};
  return {eligible: true, reason: 'eligible'};
}

function selectWorker(workers, requirements, options = {}) {
  const reqs = safeList(requirements, 40, 120).map((req) => req.toLowerCase());
  const compatible = workers.filter((worker) => isWorkerLeaseEligible(worker, reqs, options).eligible);
  const selected = compatible[0] || null;
  if (selected) return selected;
  const err = new Error(reqs.length ? `No live real Command Center worker satisfies requirements: ${reqs.join(', ')}` : 'No live real Command Center worker is currently routable.');
  err.status = 409;
  err.code = 'NO_REAL_WORKER_AVAILABLE';
  err.requirements = reqs;
  throw err;
}

function workerSelectionFailure(err) {
  return err && err.code === 'NO_REAL_WORKER_AVAILABLE';
}

function activationWorkerRequirements(args = {}, task = {}) {
  const policy = safeObject(task.executionPolicy || args.executionPolicy);
  const raw = args.workerRequirements || policy.workerRequirements || task.workerRequirements || args.requiredWorkerCapabilities || policy.requiredWorkerCapabilities || task.requiredWorkerCapabilities;
  const reqs = safeList(raw, 40, 120);
  return reqs.length ? reqs : ['codex-cloud'];
}

async function appendEvent(admin, event) {
  const eventId = `evt_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const payload = {
    eventId,
    type: safeText(event.type, 120),
    jobId: safeText(event.jobId, 140),
    projectId: safeText(event.projectId, 120),
    summary: safeText(event.summary, 2000),
    requiresHumanDecision: event.requiresHumanDecision === true,
    recommendedAction: safeText(event.recommendedAction, 200),
    evidenceRefs: safeList(event.evidenceRefs, 40, 500),
    actor: safeText(event.actor, 160),
    createdAtMs: Date.now(),
    data: safeObject(event.data),
  };
  await collection(admin, COMMAND_CENTER_COLLECTIONS.events).doc(eventId).set(payload);
  return payload;
}

async function recordLog(admin, jobId, projectId, message, data = {}) {
  const logId = `log_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const payload = {logId, jobId, projectId, message: safeText(message, 4000), data: safeObject(data), createdAtMs: Date.now()};
  await collection(admin, COMMAND_CENTER_COLLECTIONS.logs).doc(logId).set(payload);
  await upsertBucketObject(admin, {
    bucketId: COMMAND_CENTER_DEFAULT_BUCKET_ID,
    kind: 'memory.past_log',
    title: `Log ${logId}`,
    path: `memory/past-logs/${projectId || 'unknown-project'}/${jobId || 'unknown-job'}/${logId}.json`,
    summary: payload.message,
    body: JSON.stringify(payload, null, 2),
    projectId,
    jobId,
    sourceRefs: [`log://${jobId}/${logId}`],
    evidenceRefs: [`log://${jobId}/${logId}`],
    tags: ['log', 'execution'],
    source: 'command_center.recordLog',
  }, {actor: 'command_center'});
  return payload;
}

async function upsertBucketObject(admin, args, caller) {
  const payload = cleanBucketObject(args, caller);
  const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.bucketObjects).doc(payload.objectId);
  const existing = await ref.get();
  const existingData = existing.exists ? existing.data() || {} : {};
  await ref.set({
    ...payload,
    createdAtMs: existingData.createdAtMs || payload.createdAtMs,
    createdBy: existingData.createdBy || payload.createdBy,
  }, {merge: true});
  return {...payload, createdAtMs: existingData.createdAtMs || payload.createdAtMs, createdBy: existingData.createdBy || payload.createdBy};
}

async function putBucketObject(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'bucket.put_object', async () => {
    const object = await upsertBucketObject(admin, args, caller);
    const eventJobId = object.jobId || '';
    if (eventJobId) {
      await appendEvent(admin, {type: 'bucket_object_written', jobId: eventJobId, projectId: object.projectId, actor: caller.actor, summary: object.title, evidenceRefs: [`bucket://${object.bucketId}/${object.path}`], data: {objectId: object.objectId, kind: object.kind, path: object.path}});
    }
    return {object, bucketLayout: COMMAND_CENTER_BUCKET_LAYOUT};
  });
}

async function getBucketObject(admin, args) {
  const objectId = safeText(args.objectId, 180);
  if (!objectId) {
    const err = new Error('objectId is required.');
    err.status = 400;
    throw err;
  }
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.bucketObjects).doc(objectId).get();
  return snap.exists ? {found: true, object: snap.data()} : {found: false, objectId};
}

async function listBucketObjects(admin, args = {}) {
  const bucketId = cleanBucketId(args.bucketId);
  const kind = args.kind ? cleanBucketKind(args.kind) : '';
  const projectId = args.projectId ? cleanProjectId(args.projectId) : '';
  const jobId = args.jobId ? cleanJobId(args.jobId) : '';
  const repository = safeText(args.repository, 240);
  const tag = safeText(args.tag, 120);
  const limit = Math.max(1, Math.min(Number(args.limit) || 50, 100));
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.bucketObjects).limit(250).get();
  const objects = [];
  snap.forEach((doc) => {
    const object = doc.data() || {};
    if (object.bucketId !== bucketId) return;
    if (kind && object.kind !== kind) return;
    if (projectId && object.projectId !== projectId) return;
    if (jobId && object.jobId !== jobId) return;
    if (repository && object.repository !== repository) return;
    if (tag && !(Array.isArray(object.tags) && object.tags.includes(tag))) return;
    objects.push(object);
  });
  objects.sort((a, b) => Number(b.updatedAtMs || 0) - Number(a.updatedAtMs || 0));
  return {bucketId, objects: objects.slice(0, limit), layout: COMMAND_CENTER_BUCKET_LAYOUT};
}

async function promoteBucketSkill(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'bucket.promote_skill', async () => {
    const source = await getBucketObject(admin, {objectId: args.objectId});
    if (!source.found || source.object.kind !== 'skill.scratch') {
      const err = new Error('Only existing skill.scratch bucket objects can be promoted.');
      err.status = 400;
      throw err;
    }
    const promoted = await upsertBucketObject(admin, {
      ...source.object,
      objectId: '',
      kind: 'skill.promoted',
      path: args.path || source.object.path.replace(/^skills\/scratch\//, 'skills/promoted/'),
      title: args.title || source.object.title,
      summary: args.summary || source.object.summary,
      body: args.body || source.object.body,
      promotionState: 'promoted',
      supersedes: [source.object.objectId, ...(source.object.supersedes || [])],
      evidenceRefs: [...(source.object.evidenceRefs || []), ...safeList(args.evidenceRefs, 40, 800)],
      tags: Array.from(new Set([...(source.object.tags || []), 'promoted'])),
      source: 'command_center.bucket.promote_skill',
      idempotencyKey: args.idempotencyKey,
    }, caller);
    await collection(admin, COMMAND_CENTER_COLLECTIONS.bucketObjects).doc(source.object.objectId).set({promotionState: 'promoted_to_superseded', promotedObjectId: promoted.objectId, updatedAtMs: Date.now(), updatedBy: caller.actor}, {merge: true});
    return {sourceObjectId: source.object.objectId, promoted};
  });
}

async function recordCurrentMemorySnapshot(admin, checkpoint) {
  const title = `Current summary ${checkpoint.jobId || checkpoint.projectId}`;
  return upsertBucketObject(admin, {
    objectId: `bucket_${hashText(`${COMMAND_CENTER_DEFAULT_BUCKET_ID}:current:${checkpoint.jobId || checkpoint.projectId}`, 32)}`,
    bucketId: COMMAND_CENTER_DEFAULT_BUCKET_ID,
    kind: 'memory.current_condensed',
    title,
    path: `memory/current-condensed/${checkpoint.projectId || 'unknown-project'}/${checkpoint.jobId || 'project'}.json`,
    summary: checkpoint.nextAction || checkpoint.currentPhase || title,
    body: JSON.stringify(checkpoint, null, 2),
    projectId: checkpoint.projectId,
    jobId: checkpoint.jobId,
    sourceRefs: [`checkpoint://${checkpoint.jobId}/${checkpoint.checkpointId}`],
    evidenceRefs: checkpoint.evidenceRefs || [],
    tags: ['checkpoint', 'current-summary'],
    source: 'command_center.recordCurrentMemorySnapshot',
  }, {actor: 'command_center'});
}

async function recordCheckpoint(admin, job) {
  const checkpointId = `chk_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const payload = {
    checkpointId,
    jobId: job.jobId,
    projectId: job.projectId,
    ownerKey: safeText(job.ownerKey, 80),
    objective: job.objective || '',
    acceptanceCriteriaStatus: (job.acceptanceCriteria || []).map((criterion) => ({criterion, status: 'pending'})),
    currentPhase: job.status || 'queued',
    repositoryCommit: '',
    workingTreeState: 'unknown',
    filesInspected: [],
    filesChanged: [],
    decisionsMade: [],
    failedApproaches: [],
    testsRun: [],
    openQuestions: [],
    nextAction: 'Lease compatible Codex worker and begin repository orientation.',
    evidenceRefs: [],
    baseWorkspace: job.baseWorkspace || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE,
    requiredArtifacts: job.requiredArtifacts || COMMAND_CENTER_REQUIRED_ARTIFACTS,
    executionMode: job.executionMode || 'one_shot',
    createdAtMs: Date.now(),
  };
  await collection(admin, COMMAND_CENTER_COLLECTIONS.checkpoints).doc(checkpointId).set(payload);
  await recordCurrentMemorySnapshot(admin, payload);
  return payload;
}

async function idempotentMutation(admin, caller, idempotencyKey, operation, fn) {
  const ownerKey = ownerKeyFromCaller(caller);
  const idemId = `${ownerKey}_${hashText(operation + ':' + idempotencyKey, 32)}`;
  const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.idempotency).doc(idemId);
  const snap = await ref.get();
  if (snap.exists) return {idempotentReplay: true, ...(snap.data().response || {})};
  const response = await fn();
  await ref.set({idempotencyKey, operation, caller: caller.actor, ownerKey, createdAtMs: Date.now(), response});
  return response;
}

async function getLatestCheckpoint(admin, jobId) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.checkpoints).where('jobId', '==', jobId).limit(25).get();
  const checkpoints = [];
  snap.forEach((doc) => checkpoints.push(doc.data()));
  checkpoints.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  return checkpoints[0] || null;
}

async function getJob(admin, jobId, caller = null) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).get();
  if (!snap.exists) {
    const err = new Error('Command Center job not found.');
    err.status = 404;
    throw err;
  }
  const job = snap.data() || {};
  if (caller) assertOwnerAccess(job, caller, 'Command Center job');
  return job;
}

function buildJobActivation(job, lease, worker, options = {}) {
  const attempt = Math.max(1, Number(options.attempt || 1));
  const nowMs = Number(options.nowMs || 0) || Date.now();
  const activationId = safeText(options.activationId, 180) || `job_activation_${job.jobId}_${attempt}`;
  return {
    activationId,
    jobId: job.jobId,
    projectId: job.projectId,
    leaseId: lease.leaseId,
    workerId: worker.workerId,
    attempt,
    status: 'requested',
    idempotencyKey: `${job.jobId}:${lease.leaseId}:${worker.workerId}:${attempt}`,
    activation: normalizeActivationChannel(worker.activation),
    requestedAtMs: nowMs,
    updatedAtMs: nowMs,
    timeoutAtMs: nowMs + COMMAND_CENTER_ACTIVATION_TIMEOUT_MS,
    diagnostic: '',
    executorId: '',
  };
}

function activationStateFromResult(result) {
  if (result && result.ok !== false && result.accepted !== false) {
    return {status: 'accepted', accepted: true, diagnostic: safeText(result.diagnostic || result.summary, 1000), executorId: safeText(result.executorId || result.activationId, 180)};
  }
  return {status: 'rejected', accepted: false, diagnostic: safeText(result && (result.error || result.diagnostic || result.message), 1000) || 'Activation endpoint rejected or did not return acceptance.', executorId: ''};
}

async function googleCloudAccessToken() {
  const response = await fetch('http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token', {headers: {'Metadata-Flavor': 'Google'}});
  const text = await response.text();
  if (!response.ok) throw new Error(`Metadata token request failed: ${response.status} ${text.slice(0, 200)}`);
  const json = JSON.parse(text);
  if (!json.access_token) throw new Error('Metadata token response did not contain access_token.');
  return json.access_token;
}

async function invokeCloudRunJobActivation(worker, activation, session = {}) {
  const cloudRunJob = safeObject(worker.cloudRunJob);
  const projectId = safeText(cloudRunJob.projectId, 120);
  const region = safeText(cloudRunJob.region, 80);
  const jobName = safeText(cloudRunJob.jobName, 160);
  if (!projectId || !region || !jobName) return {ok: false, accepted: false, error: 'cloud_run_job activation requires projectId, region, and jobName.'};
  const token = await googleCloudAccessToken();
  const response = await fetch(`https://run.googleapis.com/v2/projects/${projectId}/locations/${region}/jobs/${jobName}:run`, {
    method: 'POST',
    headers: {authorization: `Bearer ${token}`, 'content-type': 'application/json'},
    body: JSON.stringify({
      validateOnly: false,
      overrides: {
        containerOverrides: [{
          env: [
            {name: 'COMMAND_CENTER_ACTIVATION_ID', value: safeText(activation.activationId, 180)},
            {name: 'COMMAND_CENTER_JOB_ID', value: safeText(activation.jobId, 180)},
            {name: 'COMMAND_CENTER_SESSION_ID', value: safeText(activation.sessionId || session.sessionId, 180)},
            {name: 'COMMAND_CENTER_SELECTED_WORKER_ID', value: safeText(worker.workerId, 120)},
            {name: 'COMMAND_CENTER_BASE', value: COMMAND_CENTER_PUBLIC_BASE},
            {name: 'COMMAND_CENTER_RESTORE_WORKSPACE_SNAPSHOT_REF', value: safeText(activation.restoreWorkspaceSnapshotRef || session.currentWorkspaceSnapshotRef, 1200)},
            {name: 'COMMAND_CENTER_PROJECT_ID', value: safeText(activation.projectId || session.projectId, 120)},
            {name: 'COMMAND_CENTER_REPOSITORY', value: safeText(activation.repository || session.repository, 240)},
            {name: 'COMMAND_CENTER_WAKE_ONLY', value: activation.wakeOnly === true || safeObject(safeObject(activation.task).executionPolicy).wakeOnly === true ? '1' : ''},
            {name: 'COMMAND_CENTER_CODEX_EXECUTOR_DRY_RUN', value: activation.wakeOnly === true || safeObject(safeObject(activation.task).executionPolicy).dryRun === true ? '1' : ''},
          ],
        }],
      },
    }),
  });
  const text = await response.text();
  let payload = {};
  try { payload = text ? JSON.parse(text) : {}; } catch (_err) { payload = {summary: text.slice(0, 1000)}; }
  if (!response.ok) return {ok: false, accepted: false, error: payload.error || payload.message || `Cloud Run Job activation failed: HTTP ${response.status}`};
  return {ok: true, accepted: true, executorId: safeText(payload.name, 300), diagnostic: `Cloud Run Job ${jobName} invoked.`, response: payload};
}

async function invokeJobActivator(jobActivation, job, lease, worker) {
  const channel = normalizeActivationChannel(worker.activation);
  if (channel.mode === 'cloud_run_job') return invokeCloudRunJobActivation(worker, {...jobActivation, jobId: job.jobId, projectId: job.projectId, repository: job.repository || ''}, {});
  if (channel.mode !== 'push' || !channel.endpoint) return {ok: false, accepted: false, error: 'Worker has no push activation endpoint.'};
  const headers = {'content-type': 'application/json'};
  if (channel.authRef && process.env[channel.authRef]) headers.authorization = `Bearer ${process.env[channel.authRef]}`;
  const body = JSON.stringify({
    activationId: jobActivation.activationId,
    jobId: job.jobId,
    leaseId: lease.leaseId,
    workerId: worker.workerId,
    commandCenterBase: COMMAND_CENTER_PUBLIC_BASE,
    packetVersion: 'command-center-job-activation-v1',
  });
  try {
    const response = await fetch(channel.endpoint, {method: 'POST', headers, body});
    const text = await response.text();
    let payload = {};
    try {
      payload = text ? JSON.parse(text) : {};
    } catch (_err) {
      payload = {summary: text.slice(0, 1000)};
    }
    if (!response.ok) return {ok: false, accepted: false, error: payload.error || payload.message || `Activation endpoint returned HTTP ${response.status}`};
    return {...payload, ok: payload.ok !== false, accepted: payload.accepted !== false};
  } catch (err) {
    return {ok: false, accepted: false, error: safeText(err && err.message, 1000) || 'Activation request failed.'};
  }
}


async function wakeWorker(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'workers.wake', async () => {
    const workerId = safeText(args.workerId, 120);
    if (!workerId) {
      const err = new Error('workerId is required.');
      err.status = 400;
      throw err;
    }
    const worker = (await workerRecords(admin)).find((candidate) => candidate.workerId === workerId) || null;
    if (!worker) {
      const err = new Error(`Command Center worker not found: ${workerId}`);
      err.status = 404;
      throw err;
    }
    if (worker.simulated === true) {
      const err = new Error('Cannot wake a simulated Command Center worker.');
      err.status = 409;
      throw err;
    }
    const channel = normalizeActivationChannel(worker.activation);
    if (channel.mode !== 'cloud_run_job') {
      const err = new Error('workers.wake currently supports cloud_run_job workers only.');
      err.status = 409;
      throw err;
    }
    const cloudRunJob = safeObject(worker.cloudRunJob);
    if (!cloudRunJob.projectId || !cloudRunJob.region || !cloudRunJob.jobName) {
      const err = new Error('cloud_run_job worker requires projectId, region, and jobName before wake.');
      err.status = 409;
      throw err;
    }
    if (safeObject(worker.sessionPolicy).durable !== true || safeObject(worker.sessionPolicy).snapshotStore !== 'gcs') {
      const err = new Error('cloud_run_job wake requires durable gcs sessionPolicy.');
      err.status = 409;
      throw err;
    }
    const nowMs = Date.now();
    const runLabel = slug(args.runLabel || args.reason || `wake-${workerId}-${nowMs}`, 'wake');
    const projectId = cleanProjectId(args.projectId || 'command-center-workers');
    const agent = cleanRepoAgent({
      agentId: args.agentId || `${projectId}-wake-agent`,
      projectId,
      name: args.name || 'Command Center worker wake agent',
      purpose: 'Owns bounded wake-only Cloud Run worker liveness activations.',
      contextRefs: ['docs/COMMAND_CENTER_MCP.md', 'cloud-worker/src/cloud_run_worker.mjs'],
    }, caller);
    const session = cleanAgentSession({
      sessionId: args.sessionId || `session_${runLabel}_${hashText(workerId, 10)}`,
      agentId: agent.agentId,
      projectId: agent.projectId,
      title: `Worker wake ${workerId}`,
      purpose: `Wake ${workerId} and prove live heartbeat without granting registry health by assertion.`,
      workerFamily: safeText(worker.workerFamily, 120) || 'cloud-run-debian-codex',
      runtime: 'cloud-run-debian',
      preferredWorkerIds: [workerId],
      currentWorkspaceSnapshotRef: safeText(args.currentWorkspaceSnapshotRef, 1200),
      restoreStrategy: 'gcs_snapshot',
    }, agent, caller);
    const activationId = cleanActivationId(args.activationId || `activation_wake_${hashText(`${workerId}:${runLabel}:${nowMs}`, 24)}`);
    const task = cleanActivationTask({
      title: `Wake ${workerId}`,
      prompt: safeText(args.prompt, 12000) || 'Wake-only Command Center worker liveness check. Restore minimal workspace, emit heartbeat, record final report, and exit.',
      trigger: 'workers.wake',
      acceptanceCriteria: ['Real Cloud Run worker claims this activation.', 'Worker emits a fresh heartbeat.', 'Worker records a wake final report artifact.'],
      artifactRequirements: ['final-report.md'],
      executionPolicy: {wakeOnly: true, dryRun: true},
    });
    const activation = {
      activationId,
      agentId: agent.agentId,
      sessionId: session.sessionId,
      projectId: agent.projectId,
      repository: '',
      sessionKind: session.sessionKind || 'durable_worker_session',
      workerFamily: session.workerFamily || 'cloud-run-debian-codex',
      runtime: session.runtime || 'cloud-run-debian',
      status: 'queued',
      executionSurface: COMMAND_CENTER_CODEX_CLOUD_SURFACE.surfaceId,
      realWorkerRequired: true,
      workerRequirements: ['cloud-run-debian', 'durable-session', 'gcs-workspace-snapshot'],
      restoreWorkspaceSnapshotRef: session.currentWorkspaceSnapshotRef || '',
      restoreWorkspaceSnapshotDigest: session.currentWorkspaceSnapshotDigest || '',
      nextWorkspaceSnapshotRequired: true,
      wakeOnly: true,
      selectedWorkerId: worker.workerId,
      selectedWorker: {workerId: worker.workerId, engine: worker.engine, location: worker.location, capabilities: worker.capabilities || [], simulated: worker.simulated === true, routable: worker.routable !== false, runtime: worker.runtime || {}, cloudRunJob: worker.cloudRunJob || {}, sessionPolicy: worker.sessionPolicy || {}},
      task,
      createdBy: caller.actor,
      createdAtMs: nowMs,
      updatedAtMs: nowMs,
      codexCloudRefIds: [],
      artifactRefs: [],
      bucketObjectIds: [],
      handoffSummary: '',
    };
    await collection(admin, COMMAND_CENTER_COLLECTIONS.repoAgents).doc(agent.agentId).set(agent, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(session.sessionId).set({...session, latestActivationId: activationId}, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).doc(activationId).set(activation, {merge: true});
    await recordAgentContextSnapshot(admin, agent, session, activation, caller);
    const result = await invokeCloudRunJobActivation(worker, {...activation, wakeOnly: true}, session);
    const state = activationStateFromResult(result);
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).doc(activationId).set({
      status: state.accepted ? 'queued' : 'failed',
      cloudRunOperationName: state.executorId,
      activationDiagnostic: state.diagnostic,
      updatedAtMs: Date.now(),
    }, {merge: true});
    if (!state.accepted) {
      const err = new Error(`Cloud Run worker wake failed: ${state.diagnostic}`);
      err.status = 502;
      throw err;
    }
    return {ok: true, workerId, activationId, sessionId: session.sessionId, cloudRunOperationName: state.executorId, diagnostic: state.diagnostic, livenessBeforeWake: deriveWorkerLiveness(worker, nowMs)};
  });
}

async function requestJobActivation(admin, job, lease, worker) {
  const channel = normalizeActivationChannel(worker.activation);
  const activation = buildJobActivation(job, lease, worker);
  await collection(admin, COMMAND_CENTER_COLLECTIONS.jobActivations).doc(activation.activationId).set(activation, {merge: true});
  const requestedEvent = await appendEvent(admin, {
    type: 'activation_requested',
    jobId: job.jobId,
    projectId: job.projectId,
    actor: 'command_center',
    summary: channel.mode === 'poll' ? `Queued poll activation for ${worker.workerId}.` : `Requested push activation from ${worker.workerId}.`,
    data: {activationId: activation.activationId, leaseId: lease.leaseId, workerId: worker.workerId, endpoint: channel.endpoint},
  });
  if (channel.mode === 'poll') return {activation, events: [requestedEvent], accepted: true};
  if (!['push', 'cloud_run_job'].includes(channel.mode)) return {activation, events: [requestedEvent], accepted: false};
  const result = await invokeJobActivator(activation, job, lease, worker);
  const state = activationStateFromResult(result);
  const update = {
    status: state.status,
    acceptedAtMs: state.accepted ? Date.now() : 0,
    rejectedAtMs: state.accepted ? 0 : Date.now(),
    updatedAtMs: Date.now(),
    diagnostic: state.diagnostic,
    executorId: state.executorId,
  };
  await collection(admin, COMMAND_CENTER_COLLECTIONS.jobActivations).doc(activation.activationId).set(update, {merge: true});
  const resultEvent = await appendEvent(admin, {
    type: state.accepted ? 'activation_accepted' : 'activation_rejected',
    jobId: job.jobId,
    projectId: job.projectId,
    actor: worker.workerId,
    summary: state.accepted ? `Activation accepted by ${worker.workerId}.` : `Activation rejected by ${worker.workerId}: ${state.diagnostic}`,
    data: {activationId: activation.activationId, leaseId: lease.leaseId, executorId: state.executorId, diagnostic: state.diagnostic},
  });
  if (!state.accepted) {
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(job.jobId).set({status: 'failed', updatedAtMs: Date.now(), failedAtMs: Date.now(), failureReason: state.diagnostic}, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).doc(lease.leaseId).set({status: 'failed', updatedAtMs: Date.now(), failureReason: state.diagnostic}, {merge: true});
  }
  return {activation: {...activation, ...update}, events: [requestedEvent, resultEvent], accepted: state.accepted};
}

function shouldAcceptWorkerCompletion({requestedStatus, events = [], artifacts = [], job = {}}) {
  if (requestedStatus === 'failed') return {ok: true, reason: 'failed completions are diagnostic terminal states'};
  const types = new Set(events.map((event) => event.type));
  if (!types.has('executor_started')) return {ok: false, reason: 'completed jobs require executor_started evidence'};
  if (!types.has('executor_finished')) return {ok: false, reason: 'completed jobs require executor_finished evidence'};
  if (!types.has('executor_heartbeat')) return {ok: false, reason: 'completed jobs require executor_heartbeat evidence'};
  const workspaceArtifact = artifacts.some((artifact) => artifact.origin === 'executor_workspace' || safeObject(artifact.metadata).origin === 'executor_workspace');
  if (!workspaceArtifact) return {ok: false, reason: 'completed jobs require at least one artifact from the executor workspace'};
  const artifactNames = new Set(artifacts.map((artifact) => safeText(artifact.name, 240)).filter(Boolean));
  const mode = cleanExecutionMode(job.executionMode);
  if (mode === 'executor_pulse') {
    const missing = COMMAND_CENTER_EXECUTOR_PULSE_ARTIFACTS.filter((name) => !artifactNames.has(name));
    if (missing.length) return {ok: false, reason: `completed executor pulse jobs require artifacts: ${missing.join(', ')}`};
    return {ok: true, reason: 'executor pulse completion has deterministic executor evidence'};
  }
  if (mode === 'codex_smoke') {
    if (!types.has('executor_stdout') && !types.has('executor_stderr')) return {ok: false, reason: 'completed Codex smoke jobs require streamed stdout or stderr evidence'};
    const missing = COMMAND_CENTER_CODEX_SMOKE_ARTIFACTS.filter((name) => !artifactNames.has(name));
    if (missing.length) return {ok: false, reason: `completed Codex smoke jobs require artifacts: ${missing.join(', ')}`};
    return {ok: true, reason: 'Codex smoke completion has executor and usage evidence'};
  }
  if (artifactNames.has('noop-proof.txt')) return {ok: false, reason: 'completed repository jobs cannot be proven by noop-proof.txt'};
  const requiredExecutionArtifacts = ['job-intake.json', 'orientation.md', 'reasoning-summary.md', 'command-log.jsonl', 'acceptance.json', 'acceptance-matrix.json', 'implementation.patch', 'changed-files.json', 'verification.json', 'final-report.md', 'mutation-requests.jsonl'];
  const missing = requiredExecutionArtifacts.filter((name) => !artifactNames.has(name));
  if (missing.length) return {ok: false, reason: `completed repository jobs require execution artifacts: ${missing.join(', ')}`};
  if (safeList(job.requiredArtifacts, 80, 180).some((name) => /red|patch|verification|pr|commit|build|readback/i.test(name)) && !artifactNames.has('implementation.patch')) {
    return {ok: false, reason: 'completed mutation tickets require implementation.patch evidence'};
  }
  return {ok: true, reason: 'completion has executor evidence'};
}

async function resolveProject(admin, args) {
  const repository = safeText(args.repository, 240);
  const projectId = cleanProjectId(args.projectId, repository || args.name || 'project');
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.projects).doc(projectId).get();
  if (snap.exists) return {project: {projectId, ...(snap.data() || {})}, created: false};
  if (COMMAND_CENTER_DEFAULT_PROJECTS[projectId]) return {project: COMMAND_CENTER_DEFAULT_PROJECTS[projectId], created: false, defaultProject: true};
  return {
    project: {
      projectId,
      name: safeText(args.name, 200) || repository || projectId,
      repository,
      capability: safeText(args.capability, 200),
      repositoryBinding: repository ? {kind: 'repository_hint', repository} : {},
      activeTickets: [],
      currentBranch: '',
      projectPacketRefs: [],
      recentRelevantOutcomes: [],
      availableWorkers: COMMAND_CENTER_DEFAULT_WORKERS.map((worker) => worker.workerId),
      durable: false,
    },
    created: false,
  };
}

async function upsertProject(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'projects.upsert', async () => {
    const packet = cleanProjectPacket(args);
    const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.projects).doc(packet.projectId);
    const existing = await ref.get();
    const existingData = existing.exists ? existing.data() || {} : {};
    if (existing.exists) assertOwnerAccess(existingData, caller, 'Command Center project');
    const project = {
      ...packet,
      createdAtMs: existingData.createdAtMs || packet.createdAtMs,
      createdBy: existingData.createdBy || caller.actor,
      updatedBy: caller.actor,
      ownerKey: existingData.ownerKey || ownerKeyFromCaller(caller),
    };
    await ref.set(project, {merge: true});
    return {project, created: !existing.exists};
  });
}

async function createJob(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'jobs.create', async () => {
    const projectId = cleanProjectId(args.projectId, args.repository || 'project');
    const jobId = `job_${randomUUID()}`;
    const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
    let worker = null;
    let selectionFailure = null;
    try {
      worker = selectWorker(workers, args.workerRequirements);
    } catch (err) {
      if (!workerSelectionFailure(err)) throw err;
      selectionFailure = err;
    }
    const nowMs = Date.now();
    const job = {
      jobId,
      projectId,
      repository: safeText(args.repository, 240),
      title: safeText(args.title, 300) || 'Untitled Command Center job',
      objective: safeText(args.objective, 4000),
      acceptanceCriteria: safeList(args.acceptanceCriteria, 80, 1000),
      constraints: safeList(args.constraints, 80, 1000),
      scopeExclusions: safeList(args.scopeExclusions, 80, 1000),
      workerRequirements: safeList(args.workerRequirements, 40, 120),
      budgetClass: safeText(args.budgetClass, 80) || 'small',
      mutationPolicy: cleanMutationPolicy(args.mutationPolicy),
      ...cleanOneShotExecution(args),
      status: worker ? 'leased' : 'queued',
      selectedWorkerId: worker ? worker.workerId : '',
      createdBy: caller.actor,
      ownerKey: ownerKeyFromCaller(caller),
      createdAtMs: nowMs,
      updatedAtMs: nowMs,
      simulatedWorker: worker ? worker.simulated === true : false,
      routingDiagnostic: selectionFailure ? selectionFailure.message : '',
    };
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set(job);
    const createdEvent = await appendEvent(admin, {type: 'job_created', jobId, projectId, actor: caller.actor, summary: job.title, data: {workerRequirements: job.workerRequirements}});
    if (!worker) {
      const queuedEvent = await appendEvent(admin, {type: 'job_queued_no_worker', jobId, projectId, actor: 'command_center', summary: selectionFailure.message, data: {requirements: selectionFailure.requirements || job.workerRequirements}});
      await recordLog(admin, jobId, projectId, 'Command Center queued job because no real worker was currently eligible.', {workerRequirements: job.workerRequirements, diagnostic: selectionFailure.message});
      const checkpoint = await recordCheckpoint(admin, job);
      return {job, lease: null, activation: null, events: [createdEvent, queuedEvent], checkpoint};
    }
    const lease = {leaseId: `lease_${randomUUID()}`, jobId, projectId, workerId: worker.workerId, status: 'active', acquiredAtMs: nowMs, expiresAtMs: nowMs + 30 * 60 * 1000, heartbeatAtMs: nowMs};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).doc(lease.leaseId).set(lease);
    const leasedEvent = await appendEvent(admin, {type: 'job_leased', jobId, projectId, actor: 'command_center', summary: `Leased to ${worker.workerId}.`, data: {worker}});
    const activationResult = await requestJobActivation(admin, job, lease, worker);
    if (activationResult.activation && activationResult.accepted === false) job.status = 'failed';
    await recordLog(admin, jobId, projectId, 'Command Center created and leased one-shot job from prepared workspace contract.', {workerId: worker.workerId, executionMode: job.executionMode, baseWorkspace: job.baseWorkspace.baseWorkspaceId});
    const checkpoint = await recordCheckpoint(admin, job);
    return {job, lease, activation: activationResult.activation, events: [createdEvent, leasedEvent, ...activationResult.events], checkpoint};
  });
}

async function synthesizeJobHandoff(admin, jobId) {
  const job = await getJob(admin, jobId);
  const [checkpoint, events, logs, artifacts, bucketRows] = await Promise.all([
    getLatestCheckpoint(admin, jobId),
    listByJob(admin, COMMAND_CENTER_COLLECTIONS.events, jobId, 100),
    listByJob(admin, COMMAND_CENTER_COLLECTIONS.logs, jobId, 100),
    listByJob(admin, COMMAND_CENTER_COLLECTIONS.artifacts, jobId, 100),
    listBucketObjects(admin, {bucketId: COMMAND_CENTER_DEFAULT_BUCKET_ID, jobId, limit: 50}),
  ]);
  const newestEvent = events[0] || null;
  const artifactNames = new Set(artifacts.map((artifact) => artifact.name).filter(Boolean));
  const missingRequiredArtifacts = (job.requiredArtifacts || COMMAND_CENTER_REQUIRED_ARTIFACTS).filter((name) => !artifactNames.has(name));
  const nowMs = Date.now();
  const acceptanceCriteria = Array.isArray(job.acceptanceCriteria) ? job.acceptanceCriteria : [];
  const checkpointCriteria = Array.isArray(checkpoint && checkpoint.acceptanceCriteriaStatus) ? checkpoint.acceptanceCriteriaStatus : [];
  const checkpointByCriterion = new Map(checkpointCriteria.map((item) => [safeText(item.criterion, 1000), item]));
  const acceptanceMatrix = acceptanceCriteria.map((criterion) => {
    const existing = checkpointByCriterion.get(criterion) || {};
    return {
      criterion,
      status: safeText(existing.status, 80) || 'not_evaluated',
      evidenceRefs: safeList(existing.evidenceRefs, 40, 800),
      notes: safeText(existing.notes, 1000) || 'No explicit criterion-level worker verdict recorded.',
      blockingReason: safeText(existing.blockingReason, 1000),
    };
  });
  const executorEvents = events.filter((event) => /^executor_/.test(event.type || ''));
  const heartbeatEvent = events.find((event) => event.type === 'executor_heartbeat') || null;
  const mutationRequests = artifacts.filter((artifact) => artifact.name === 'mutation-requests.jsonl');
  return {
    packetVersion: 'command-center-handoff-v1',
    generatedAtMs: nowMs,
    job: {
      jobId,
      projectId: job.projectId,
      title: job.title || '',
      objective: job.objective || '',
      status: job.status,
      selectedWorkerId: job.selectedWorkerId || '',
      workerRequirements: safeList(job.workerRequirements, 40, 120),
      requiredArtifacts: safeList(job.requiredArtifacts || COMMAND_CENTER_REQUIRED_ARTIFACTS, 80, 120),
      sourceJobId: job.sourceJobId || '',
      followupOf: job.followupOf || null,
      mutationPolicy: cleanMutationPolicy(job.mutationPolicy),
      baseWorkspace: job.baseWorkspace || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE,
    },
    review: {
      recommendedNextAction: job.status === 'completed' ? 'Review completion evidence and authorize only policy-approved consequential mutations.' : 'Create a linked follow-up invocation after reviewing the failure evidence.',
      correctability: {
        preferredOperation: 'command_center.jobs.create_followup',
        sourceJobId: jobId,
        carryForwardEvidenceRefs: artifacts.map((artifact) => artifact.uri).filter(Boolean).slice(0, 40),
      },
      residualRisks: missingRequiredArtifacts.length ? ['Some required artifacts are missing.'] : ['Acceptance criteria still require reviewer judgment; artifact presence is not acceptance.'],
    },
    counters: {
      eventCount: events.length,
      logCount: logs.length,
      artifactCount: artifacts.length,
      bucketObjectCount: bucketRows.objects.length,
      executorEventCount: executorEvents.length,
      lastEventType: newestEvent ? newestEvent.type : '',
      lastHeartbeatAgeMs: heartbeatEvent ? nowMs - Number(heartbeatEvent.createdAtMs || nowMs) : null,
      terminal: ['completed', 'failed', 'canceled'].includes(job.status),
      missingRequiredArtifacts,
    },
    checkpoint,
    acceptanceMatrix,
    artifacts: artifacts.map((artifact) => ({artifactId: artifact.artifactId, name: artifact.name, kind: artifact.kind, uri: artifact.uri, sha256: artifact.sha256, required: artifact.required === true})),
    events: events.slice(0, 20).map((event) => ({eventId: event.eventId, type: event.type, summary: event.summary, createdAtMs: event.createdAtMs, actor: event.actor, evidenceRefs: event.evidenceRefs || []})),
    logs: logs.slice(0, 20).map((log) => ({logId: log.logId, message: log.message, createdAtMs: log.createdAtMs})),
    bucketObjects: bucketRows.objects.map((object) => ({objectId: object.objectId, kind: object.kind, path: object.path, title: object.title, summary: object.summary, updatedAtMs: object.updatedAtMs})),
    mutationRequests,
  };
}

async function createFollowupJob(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'jobs.create_followup', async () => {
    const sourceJobId = cleanJobId(args.sourceJobId);
    const sourceHandoff = await synthesizeJobHandoff(admin, sourceJobId);
    const sourceJob = sourceHandoff.job;
    const projectId = args.projectId ? cleanProjectId(args.projectId) : cleanProjectId(sourceJob.projectId);
    const workers = await workerRecords(admin);
    const workerRequirements = safeList(args.workerRequirements, 40, 120);
    const inheritedWorkerRequirements = safeList(sourceJob.workerRequirements, 40, 120);
    const worker = selectWorker(workers, workerRequirements.length ? workerRequirements : inheritedWorkerRequirements);
    const execution = cleanOneShotExecution({
      ...args,
      baseWorkspace: args.baseWorkspace || sourceJob.baseWorkspace,
      requiredArtifacts: args.requiredArtifacts || sourceJob.requiredArtifacts,
    });
    const nowMs = Date.now();
    const jobId = `job_${randomUUID()}`;
    const job = {
      jobId,
      projectId,
      title: safeText(args.title, 300) || `Follow up: ${sourceJob.title || sourceJobId}`,
      objective: safeText(args.objective, 4000) || `Follow up on ${sourceJobId}.`,
      acceptanceCriteria: safeList(args.acceptanceCriteria, 80, 1000),
      constraints: safeList(args.constraints, 80, 1000),
      scopeExclusions: safeList(args.scopeExclusions, 80, 1000),
      workerRequirements: workerRequirements.length ? workerRequirements : inheritedWorkerRequirements,
      budgetClass: safeText(args.budgetClass, 80) || 'small',
      mutationPolicy: cleanMutationPolicy(args.mutationPolicy || sourceJob.mutationPolicy),
      ...execution,
      sourceJobId,
      followupOf: {
        jobId: sourceJobId,
        status: sourceJob.status,
        title: sourceJob.title || '',
        handoffRef: `handoff://${sourceJobId}`,
      },
      sourceEvidenceRefs: sourceHandoff.review.correctability.carryForwardEvidenceRefs,
      status: 'leased',
      selectedWorkerId: worker.workerId,
      createdBy: caller.actor,
      createdAtMs: nowMs,
      updatedAtMs: nowMs,
      simulatedWorker: worker.simulated === true,
    };
    const lease = {leaseId: `lease_${randomUUID()}`, jobId, projectId, workerId: worker.workerId, status: 'active', acquiredAtMs: nowMs, expiresAtMs: nowMs + 30 * 60 * 1000, heartbeatAtMs: nowMs};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set(job);
    await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).doc(lease.leaseId).set(lease);
    const createdEvent = await appendEvent(admin, {type: 'job_created', jobId, projectId, actor: caller.actor, summary: job.title, data: {workerRequirements: job.workerRequirements, sourceJobId}});
    const followupEvent = await appendEvent(admin, {type: 'job_followup_created', jobId, projectId, actor: caller.actor, summary: `Linked follow-up for ${sourceJobId}.`, evidenceRefs: [`handoff://${sourceJobId}`], data: {sourceJobId, sourceStatus: sourceJob.status}});
    const leasedEvent = await appendEvent(admin, {type: 'job_leased', jobId, projectId, actor: 'command_center', summary: `Leased to ${worker.workerId}.`, data: {worker}});
    await recordLog(admin, jobId, projectId, 'Command Center created linked follow-up job from source handoff.', {sourceJobId, workerId: worker.workerId, sourceStatus: sourceJob.status});
    const checkpoint = await recordCheckpoint(admin, job);
    return {job, lease, events: [createdEvent, followupEvent, leasedEvent], checkpoint, sourceHandoff};
  });
}

async function reviseJob(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'jobs.revise', async () => {
    const jobId = cleanJobId(args.jobId);
    const job = await getJob(admin, jobId, caller);
    if (isTerminalJobStatus(job.status)) {
      const err = new Error('Cannot revise a terminal Command Center job.');
      err.status = 409;
      throw err;
    }
    const updates = {updatedAtMs: Date.now(), revisedBy: caller.actor};
    if (args.title !== undefined) updates.title = safeText(args.title, 300) || job.title;
    if (args.objective !== undefined) updates.objective = safeText(args.objective, 4000) || job.objective;
    if (args.acceptanceCriteria !== undefined) updates.acceptanceCriteria = safeList(args.acceptanceCriteria, 80, 1000);
    if (args.constraints !== undefined) updates.constraints = safeList(args.constraints, 80, 1000);
    if (args.scopeExclusions !== undefined) updates.scopeExclusions = safeList(args.scopeExclusions, 80, 1000);
    if (args.mutationPolicy !== undefined) updates.mutationPolicy = cleanMutationPolicy(args.mutationPolicy);
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set(updates, {merge: true});
    const event = await appendEvent(admin, {type: 'job_revised', jobId, projectId: job.projectId, actor: caller.actor, summary: safeText(args.revisionSummary, 1000) || 'Job revised.'});
    return {jobId, updates, event};
  });
}

async function transitionJob(admin, caller, args, status, operation) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), operation, async () => {
    const jobId = cleanJobId(args.jobId);
    const job = await getJob(admin, jobId, caller);
    const updates = {status, updatedAtMs: Date.now(), lastTransitionBy: caller.actor};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set(updates, {merge: true});
    const event = await appendEvent(admin, {type: `job_${status}`, jobId, projectId: job.projectId, actor: caller.actor, summary: safeText(args.reason, 1000) || `Job ${status}.`});
    return {jobId, status, event};
  });
}

async function answerQuestion(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'jobs.answer_question', async () => {
    const jobId = cleanJobId(args.jobId);
    const job = await getJob(admin, jobId, caller);
    const questionId = safeText(args.questionId, 140) || `question_${randomUUID()}`;
    const answer = {questionId, jobId, projectId: job.projectId, answer: safeText(args.answer, 4000), answeredBy: caller.actor, createdAtMs: Date.now(), decision: safeText(args.decision, 200)};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.questions).doc(questionId).set(answer, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set({status: 'running', updatedAtMs: Date.now()}, {merge: true});
    const event = await appendEvent(admin, {type: 'question_answered', jobId, projectId: job.projectId, actor: caller.actor, summary: safeText(args.answer, 1000), data: {questionId, decision: answer.decision}});
    return {answer, event, resumed: true};
  });
}

async function authorizeMutation(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'jobs.authorize_mutation', async () => {
    const jobId = cleanJobId(args.jobId);
    const job = await getJob(admin, jobId, caller);
    const action = safeText(args.action, 200);
    const decision = args.approved === true ? 'approved' : 'rejected';
    const authId = `mut_${randomUUID()}`;
    const payload = {authorizationId: authId, jobId, projectId: job.projectId, action, decision, reason: safeText(args.reason, 1000), evidenceRefs: safeList(args.evidenceRefs, 40, 500), authorizedBy: caller.actor, createdAtMs: Date.now(), mutationPolicySnapshot: cleanMutationPolicy(job.mutationPolicy)};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.mutationAuthorizations).doc(authId).set(payload);
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set({status: args.approved === true ? 'running' : 'awaiting_mutation_authorization', updatedAtMs: Date.now()}, {merge: true});
    const event = await appendEvent(admin, {type: 'mutation_authorization', jobId, projectId: job.projectId, actor: caller.actor, summary: `${decision}: ${action}`, evidenceRefs: payload.evidenceRefs, data: {authorizationId: authId, decision}});
    return {authorization: payload, event};
  });
}

async function registerOneShotWorker(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'workers.register_oneshot', async () => {
    const workerId = safeText(args.workerId, 120);
    if (!/^[A-Za-z0-9_.-]{3,120}$/.test(workerId)) {
      const err = new Error('A valid workerId is required.');
      err.status = 400;
      throw err;
    }
    const nowMs = Date.now();
    const existing = await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(workerId).get();
    if (existing.exists) assertOwnerAccess(existing.data() || {}, caller, 'Command Center worker');
    const workerToken = `ccw_${randomUUID()}_${randomUUID()}`;
    const tokenHash = tokenDigest(workerToken);
    const requestedActivation = normalizeActivationChannel(args.activation);
    const worker = cleanWorker({
      workerId,
      engine: args.engine || 'codex',
      location: args.location || 'local',
      health: 'healthy',
      capabilities: safeList(args.capabilities, 80, 120),
	      baseWorkspaces: Array.isArray(args.baseWorkspaces) ? args.baseWorkspaces : [args.baseWorkspace || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE],
	      limits: safeObject(args.limits),
	      activation: requestedActivation.mode ? {...requestedActivation, verifiedAtMs: requestedActivation.verifiedAtMs || nowMs} : {mode: 'poll', verifiedAtMs: nowMs},
	      runtime: safeObject(args.runtime),
	      cloudRunJob: safeObject(args.cloudRunJob),
	      sessionPolicy: safeObject(args.sessionPolicy),
	      repositoryAffinity: safeList(args.repositoryAffinity, 80, 240),
	      lastHeartbeatAtMs: nowMs,
      ownerKey: ownerKeyFromCaller(caller),
      simulated: false,
      oneShot: true,
    });
    if (!worker.capabilities.length) worker.capabilities = ['codex', 'one-shot-worker', 'prepared-workspace'];
    await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(workerId).set({...worker, registeredBy: caller.actor, updatedAtMs: nowMs, createdAtMs: nowMs}, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.workerTokens).doc(tokenHash).set({workerId, ownerKey: ownerKeyFromCaller(caller), createdBy: caller.actor, createdAtMs: nowMs, expiresAtMs: nowMs + 90 * 24 * 60 * 60 * 1000, authKind: 'command_center_worker_token'}, {merge: false});
    return {worker, workerToken, tokenType: 'Bearer', expiresIn: 90 * 24 * 60 * 60, warning: 'Store this worker token only on the worker host. Command Center stores only its hash.'};
  });
}

async function retireWorker(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'workers.retire', async () => {
    const workerId = safeText(args.workerId, 120);
    if (!workerId) {
      const err = new Error('workerId is required.');
      err.status = 400;
      throw err;
    }
    const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(workerId);
    const snap = await ref.get();
    if (!snap.exists) {
      const err = new Error('Command Center worker not found.');
      err.status = 404;
      throw err;
    }
    const existing = cleanWorker({workerId, ...(snap.data() || {})});
    assertOwnerAccess(existing, caller, 'Command Center worker');
    const nowMs = Date.now();
    const update = {status: 'retired', retiredAtMs: nowMs, retiredBy: caller.actor, retireReason: safeText(args.reason, 1000) || 'Retired stale Command Center worker registration.', routable: false, registryRoutable: false, updatedAtMs: nowMs};
    await ref.set(update, {merge: true});
    const worker = cleanWorker({...existing, ...update});
    return {worker, retired: true};
  });
}

function normalizeCommandCenterOperationName(value) {
  return safeText(value, 180).replace(/^command_center\./, '');
}

async function runCommandCenterOperation(admin, extra, operation, args = {}) {
  const op = normalizeCommandCenterOperationName(operation);
  const caller = async () => callerFromExtra(admin, extra);
  switch (op) {
    case 'health': {
      const workers = await workerRecords(admin);
      const liveWorkers = workers.filter((worker) => worker.livenessState === 'live' && worker.routable === true);
      const activatableWorkers = workers.filter((worker) => worker.livenessState === 'activatable' && worker.routable === true);
      const staleWorkers = workers.filter((worker) => worker.registryHealth === 'healthy' && worker.health !== 'healthy');
      const jobSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).orderBy('createdAtMs', 'desc').limit(250).get();
      const nowMs = Date.now();
      const nonterminalStatuses = ['queued', 'activating', 'leased', 'executing', 'running', 'question', 'awaiting_mutation_authorization'];
      const jobsByStatus = {};
      let nonterminal = 0;
      let stale = 0;
      let oldestNonterminalAgeMs = null;
      jobSnap.forEach((doc) => {
        const job = doc.data() || {};
        const status = safeText(job.status, 80) || 'unknown';
        jobsByStatus[status] = (jobsByStatus[status] || 0) + 1;
        if (!nonterminalStatuses.includes(status)) return;
        nonterminal += 1;
        const ageMs = nowMs - (Number(job.createdAtMs || 0) || nowMs);
        oldestNonterminalAgeMs = oldestNonterminalAgeMs === null ? ageMs : Math.max(oldestNonterminalAgeMs, ageMs);
        if (staleJobCandidate(job, nowMs, COMMAND_CENTER_RECONCILE_DEFAULT_OLDER_THAN_MS, ['leased', 'executing', 'running', 'activating'])) stale += 1;
      });
      return {ok: true, service: 'command-center-mcp', invokable: true, hasFrontend: false, commandCenterMcpUrl: COMMAND_CENTER_RESOURCE, authorizationServer: HOME_CENTER_AUTHORIZATION_SERVER_BASE, workerLiveness: {total: workers.length, live: liveWorkers.length, activatable: activatableWorkers.length, stale: staleWorkers.length, liveWorkerIds: liveWorkers.map((worker) => worker.workerId), activatableWorkerIds: activatableWorkers.map((worker) => worker.workerId), staleWorkerIds: staleWorkers.map((worker) => worker.workerId)}, queue: {sampled: jobSnap.size, byStatus: jobsByStatus, nonterminal, stale, oldestNonterminalAgeMs}};
    }
    case 'projects.resolve':
      return resolveProject(admin, args || {});
    case 'projects.get': {
      const c = await caller();
      const projectId = cleanProjectId(args.projectId);
      const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.projects).doc(projectId).get();
      if (snap.exists) {
        const project = {projectId, ...(snap.data() || {})};
        assertOwnerAccess(project, c, 'Command Center project');
        return {projectId, found: true, project};
      }
      if (COMMAND_CENTER_DEFAULT_PROJECTS[projectId]) return {projectId, found: true, defaultProject: true, project: COMMAND_CENTER_DEFAULT_PROJECTS[projectId]};
      return {projectId, found: false};
    }
    case 'projects.upsert':
      return upsertProject(admin, await caller(), args || {});
    case 'jobs.create':
      return createJob(admin, await caller(), args || {});
    case 'jobs.create_followup':
      return createFollowupJob(admin, await caller(), args || {});
    case 'jobs.get':
      return {job: await getJob(admin, cleanJobId(args.jobId), await caller())};
    case 'jobs.list': {
      try {
        let query = queryOwnedCollection(admin, COMMAND_CENTER_COLLECTIONS.jobs, await caller());
        if (args.projectId) query = query.where('projectId', '==', cleanProjectId(args.projectId));
        if (args.status) query = query.where('status', '==', args.status);
        query = query.orderBy('createdAtMs', 'desc');
        if (args.status && !args.projectId) query = query.orderBy(admin.firestore.FieldPath.documentId(), 'desc');
        const snap = await query.limit(Math.max(1, Math.min(Number(args.limit) || 20, 50))).get();
        const jobs = [];
        snap.forEach((doc) => jobs.push(doc.data()));
        return {jobs};
      } catch (err) {
        const message = safeText(err && err.message, 2000);
        if (/index|FAILED_PRECONDITION|requires an index/i.test(message)) {
          return commandCenterJobsListIndexError(args, err);
        }
        throw err;
      }
    }
    case 'jobs.reconcile_stale':
      return reconcileStaleJobs(admin, await caller(), args || {});
    case 'jobs.cancel':
      return transitionJob(admin, await caller(), args || {}, 'canceled', 'jobs.cancel');
    case 'jobs.resume':
      return transitionJob(admin, await caller(), args || {}, 'running', 'jobs.resume');
    case 'jobs.revise':
      return reviseJob(admin, await caller(), args || {});
    case 'jobs.answer_question':
      return answerQuestion(admin, await caller(), args || {});
    case 'jobs.authorize_mutation':
      return authorizeMutation(admin, await caller(), args || {});
    case 'jobs.get_summary': {
      const jobId = cleanJobId(args.jobId);
      const c = await caller();
      const handoff = await synthesizeJobHandoff(admin, jobId, c);
      return {jobId, status: handoff.job.status, checkpoint: handoff.checkpoint, counters: handoff.counters, recommendedNextAction: handoff.review.recommendedNextAction, job: await getJob(admin, jobId, c)};
    }
    case 'jobs.get_handoff':
      return {handoff: await synthesizeJobHandoff(admin, cleanJobId(args.jobId), await caller())};
    case 'jobs.get_events': {
      const jobId = cleanJobId(args.jobId);
      await getJob(admin, jobId, await caller());
      return {events: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.events, jobId, Math.max(1, Math.min(Number(args.limit) || 50, 100)))};
    }
    case 'jobs.get_logs': {
      const jobId = cleanJobId(args.jobId);
      await getJob(admin, jobId, await caller());
      return {logs: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.logs, jobId, Math.max(1, Math.min(Number(args.limit) || 50, 100)))};
    }
    case 'jobs.get_artifacts': {
      const jobId = cleanJobId(args.jobId);
      await getJob(admin, jobId, await caller());
      return {artifacts: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.artifacts, jobId, Math.max(1, Math.min(Number(args.limit) || 50, 100)))};
    }
    case 'agents.upsert_repo_agent':
      return upsertRepoAgent(admin, await caller(), args || {});
    case 'agents.create_activation':
      return createAgentActivation(admin, await caller(), args || {});
    case 'agents.get_resume_packet':
      return getAgentResumePacket(admin, args || {});
    case 'agents.record_codex_cloud_ref':
      return recordCodexCloudRef(admin, await caller(), args || {});
    case 'agents.record_artifact':
      return recordAgentArtifact(admin, await caller(), args || {});
    case 'agents.complete_activation':
      return completeAgentActivation(admin, await caller(), args || {});
    case 'agents.get_handoff':
      return {handoff: await synthesizeAgentHandoff(admin, cleanActivationId(args.activationId))};
    case 'bucket.get_layout':
      return {layout: COMMAND_CENTER_BUCKET_LAYOUT, kinds: COMMAND_CENTER_BUCKET_KINDS};
    case 'bucket.put_object':
      return putBucketObject(admin, await caller(), args || {});
    case 'bucket.get_object':
      return getBucketObject(admin, args || {}, await caller());
    case 'bucket.list_objects':
      return listBucketObjects(admin, args || {}, await caller());
    case 'bucket.promote_skill':
      return promoteBucketSkill(admin, await caller(), args || {});
    case 'workers.register_oneshot':
      return registerOneShotWorker(admin, await caller(), args || {});
    case 'workers.wake':
      return wakeWorker(admin, await caller(), args || {});
    case 'workers.retire':
      return retireWorker(admin, await caller(), args || {});
    case 'workers.list':
      return {workers: recordsVisibleToCaller(await workerRecords(admin), await caller())};
    case 'workers.get_capabilities': {
      const c = await caller();
      const workerId = safeText(args.workerId, 120);
      const workers = recordsVisibleToCaller(await workerRecords(admin), c);
      return {worker: workers.find((worker) => worker.workerId === workerId) || null};
    }
    case 'app_control.seed_profiles':
      return seedAppControlProfiles(admin, await caller(), args || {});
    case 'app_control.put_profile':
      return putAppControlProfile(admin, await caller(), args || {});
    case 'app_control.get_profile':
      return getAppControlProfile(admin, args || {});
    case 'app_control.list_profiles':
      return listAppControlProfiles(admin, args || {});
    case 'app_control.record_run':
      return recordAppControlRun(admin, await caller(), args || {});
    case 'browser_sessions.create':
      return createBrowserSession(admin, await caller(), args || {});
    case 'browser_sessions.observe':
      return observeBrowserSession(admin, args || {});
    case 'browser_sessions.act':
      return requestBrowserAction(admin, await caller(), args || {});
    case 'browser_sessions.record_episode':
      return recordBrowserEpisode(admin, await caller(), args || {});
    case 'browser_discoveries.list':
      return listBrowserDiscoveries(admin, args || {});
    case 'browser_discoveries.promote':
      return promoteBrowserDiscovery(admin, await caller(), args || {});
    case 'browser_playbooks.lookup':
      return lookupBrowserPlaybook(admin, args || {});
    default: {
      const err = new Error(`Unsupported command_center_operation operation: ${op}`);
      err.status = 400;
      throw err;
    }
  }
}

async function recordArtifact(admin, jobId, projectId, artifact, ownerKey = '') {
  const artifactId = safeText(artifact.artifactId, 180) || `artifact_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const payload = {
    artifactId,
    jobId,
    projectId,
    ownerKey: safeText(ownerKey, 80),
    name: safeText(artifact.name, 240),
    kind: safeText(artifact.kind, 120) || 'file',
    uri: safeText(artifact.uri, 1000),
    sha256: safeText(artifact.sha256, 128),
    required: artifact.required === true,
    origin: safeText(artifact.origin || safeObject(artifact.metadata).origin, 120) || 'executor_workspace',
    workspacePath: safeText(artifact.workspacePath || safeObject(artifact.metadata).workspacePath, 1000),
    createdAtMs: Date.now(),
    metadata: safeObject(artifact.metadata),
  };
  await collection(admin, COMMAND_CENTER_COLLECTIONS.artifacts).doc(artifactId).set(payload, {merge: true});
  return payload;
}

async function workerCallerFromRequest(admin, req) {
  const header = req.get('Authorization') || '';
  const match = String(header).match(/^Bearer\s+(.+)$/i);
  if (!match) {
    const err = new Error('Missing Command Center worker token.');
    err.status = 401;
    throw err;
  }
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.workerTokens).doc(tokenDigest(match[1])).get();
  if (!snap.exists) {
    const err = new Error('Invalid Command Center worker token.');
    err.status = 401;
    throw err;
  }
  const data = snap.data() || {};
  if (data.revokedAtMs || Number(data.expiresAtMs || 0) <= Date.now()) {
    const err = new Error(data.revokedAtMs ? 'Command Center worker token was revoked.' : 'Command Center worker token expired.');
    err.status = 401;
    throw err;
  }
  return {workerId: safeText(data.workerId, 120), tokenHash: hashText(match[1], 24)};
}

async function leasedJobForWorker(admin, workerId, requestedJobId = '') {
  const targetJobId = safeText(requestedJobId, 140);
  if (targetJobId) {
    const job = await getJob(admin, cleanJobId(targetJobId));
    if (job.selectedWorkerId !== workerId || job.status !== 'leased') return null;
    return job;
  }
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).where('selectedWorkerId', '==', workerId).limit(25).get();
  const jobs = [];
  snap.forEach((doc) => {
    const job = doc.data();
    if (job && job.status === 'leased') jobs.push(job);
  });
  jobs.sort((a, b) => Number(a.createdAtMs || 0) - Number(b.createdAtMs || 0));
  return jobs[0] || null;
}

async function claimActivationForWorker(admin, caller, args = {}) {
  const requestedActivationId = safeText(args.activationId, 180);
  const snap = requestedActivationId
    ? await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).where('selectedWorkerId', '==', caller.workerId).limit(50).get()
    : await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).where('selectedWorkerId', '==', caller.workerId).limit(50).get();
  const activations = [];
  snap.forEach((doc) => {
    const activation = doc.data() || {};
    if (requestedActivationId && activation.activationId !== requestedActivationId) return;
    if (!['queued', 'claimed'].includes(activation.status)) return;
    activations.push(activation);
  });
  activations.sort((a, b) => Number(a.createdAtMs || 0) - Number(b.createdAtMs || 0));
  const activation = activations[0] || null;
  if (!activation) return {ok: true, claimed: false};
  const [agent, session] = await Promise.all([getRepoAgent(admin, activation.agentId), getAgentSession(admin, activation.sessionId)]);
  const nowMs = Date.now();
  await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).doc(activation.activationId).set({
    status: 'claimed',
    claimedByWorkerId: caller.workerId,
    workerClaimedAtMs: nowMs,
    lastWorkerHeartbeatAtMs: nowMs,
    updatedAtMs: nowMs,
  }, {merge: true});
  await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(caller.workerId).set({lastHeartbeatAtMs: nowMs, health: 'healthy', routable: true, simulated: false}, {merge: true});
  const refreshed = {...activation, status: 'claimed', claimedByWorkerId: caller.workerId, workerClaimedAtMs: nowMs, lastWorkerHeartbeatAtMs: nowMs, updatedAtMs: nowMs};
  const snapshot = await recordAgentContextSnapshot(admin, agent, session, refreshed, {actor: caller.workerId});
  return {ok: true, claimed: true, activation: refreshed, resumePacket: buildAgentResumePacket(agent, session, refreshed, snapshot)};
}

async function requireWorkerOwnedActivation(admin, caller, activationId) {
  const activation = await getAgentActivation(admin, activationId);
  if (activation.selectedWorkerId !== caller.workerId) {
    const err = new Error('Worker cannot mutate an activation it does not own.');
    err.status = 403;
    throw err;
  }
  return activation;
}

function jobPacket(job, checkpoint = null) {
  return {
    packetVersion: 'command-center-one-shot-v1',
    job,
    checkpoint,
    promptContract: {
      mode: 'one_shot',
      noChatHistoryDependency: true,
      durableArtifactsRequired: job.requiredArtifacts || COMMAND_CENTER_REQUIRED_ARTIFACTS,
      finalStateRequired: true,
    },
  };
}

async function listByJob(admin, collectionName, jobId, limit = 50) {
  const snap = await collection(admin, collectionName).where('jobId', '==', jobId).limit(Math.max(limit, 100)).get();
  const rows = [];
  snap.forEach((doc) => rows.push(doc.data()));
  rows.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  return rows.slice(0, limit);
}

function createCommandCenterMcpServer({admin}) {
  const server = new McpServer({name: 'home-center-command-center', version: '0.1.0'});

  server.registerTool('command_center.health', {
    title: 'Command Center health',
    description: 'Cheap invokability probe for ChatGPT remote MCP attachment. Does not create jobs or mutate state.',
    inputSchema: {},
  }, async () => textResult({ok: true, service: 'command-center-mcp', invokable: true, hasFrontend: false, commandCenterMcpUrl: COMMAND_CENTER_RESOURCE, authorizationServer: HOME_CENTER_AUTHORIZATION_SERVER_BASE}));

  server.registerTool('command_center_operation', {
    title: 'Command Center operation dispatcher',
    description: 'Compatibility dispatcher matching the Home Center MCP bridge. Use this when ChatGPT sees Command Center directly or when top-level tool metadata is stale.',
    inputSchema: {operation: z.string(), args: z.record(z.string(), z.any()).optional()},
  }, async (args, extra) => textResult({operation: normalizeCommandCenterOperationName(args.operation), result: await runCommandCenterOperation(admin, extra, args.operation, args.args || {})}));

  server.registerTool('command_center.projects.resolve', {
    title: 'Resolve Command Center project',
    description: 'Resolve a project into a Command Center project packet. Command Center is not a chat UI and not the planner.',
    inputSchema: {projectId: z.string().optional(), name: z.string().optional(), repository: z.string().optional(), capability: z.string().optional()},
  }, async (args) => textResult(await resolveProject(admin, args || {})));

  server.registerTool('command_center.projects.get', {
    title: 'Get Command Center project',
    description: 'Read one durable Command Center project registry entry.',
    inputSchema: {projectId: z.string()},
  }, async (args, extra) => {
    const c = await callerFromExtra(admin, extra);
    const projectId = cleanProjectId(args.projectId);
    const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.projects).doc(projectId).get();
    if (snap.exists) {
      const project = {projectId, ...(snap.data() || {})};
      assertOwnerAccess(project, c, 'Command Center project');
      return textResult({projectId, found: true, project});
    }
    if (COMMAND_CENTER_DEFAULT_PROJECTS[projectId]) return textResult({projectId, found: true, defaultProject: true, project: COMMAND_CENTER_DEFAULT_PROJECTS[projectId]});
    return textResult({projectId, found: false});
  });

  server.registerTool('command_center.projects.upsert', {
    title: 'Upsert Command Center project',
    description: 'Create or update a durable Command Center project binding with repository, capability, and worker metadata.',
    inputSchema: {idempotencyKey: z.string(), projectId: z.string(), name: z.string().optional(), repository: z.string().optional(), capability: z.string().optional(), repositoryBinding: z.record(z.string(), z.any()).optional(), activeTickets: z.array(z.record(z.string(), z.any())).optional(), currentBranch: z.string().optional(), projectPacketRefs: z.array(z.string()).optional(), recentRelevantOutcomes: z.array(z.record(z.string(), z.any())).optional(), availableWorkers: z.array(z.string()).optional(), durable: z.boolean().optional()},
  }, async (args, extra) => textResult(await upsertProject(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.create', {
    title: 'Create Command Center job',
    description: 'Create a durable execution ticket, select a compatible worker, lease it, and write initial events/checkpoint state.',
    inputSchema: {idempotencyKey: z.string(), projectId: z.string(), title: z.string(), objective: z.string(), acceptanceCriteria: z.array(z.string()).optional(), constraints: z.array(z.string()).optional(), scopeExclusions: z.array(z.string()).optional(), workerRequirements: z.array(z.string()).optional(), budgetClass: z.string().optional(), mutationPolicy: z.record(z.string(), z.string()).optional(), executionMode: z.string().optional(), baseWorkspace: z.record(z.string(), z.any()).optional(), requiredArtifacts: z.array(z.string()).optional(), verificationCommands: z.array(z.string()).optional(), stopConditions: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await createJob(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.create_followup', {
    title: 'Create Command Center follow-up job',
    description: 'Create a new linked invocation from a source job handoff. This does not rewrite old job history.',
    inputSchema: {idempotencyKey: z.string(), sourceJobId: z.string(), projectId: z.string().optional(), title: z.string(), objective: z.string(), acceptanceCriteria: z.array(z.string()).optional(), constraints: z.array(z.string()).optional(), scopeExclusions: z.array(z.string()).optional(), workerRequirements: z.array(z.string()).optional(), budgetClass: z.string().optional(), mutationPolicy: z.record(z.string(), z.string()).optional(), baseWorkspace: z.record(z.string(), z.any()).optional(), requiredArtifacts: z.array(z.string()).optional(), verificationCommands: z.array(z.string()).optional(), stopConditions: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await createFollowupJob(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.get', {title: 'Get Command Center job', description: 'Read one Command Center job packet.', inputSchema: {jobId: z.string()}}, async (args) => textResult({job: await getJob(admin, cleanJobId(args.jobId))}));

  server.registerTool('command_center.jobs.list', {
    title: 'List Command Center jobs',
    description: 'List recent Command Center jobs, optionally filtered by project or status.',
    inputSchema: {projectId: z.string().optional(), status: z.enum(COMMAND_CENTER_ALLOWED_STATUSES).optional(), limit: z.number().optional()},
  }, async (args, extra) => {
    try {
      const c = await callerFromExtra(admin, extra);
      let query = queryOwnedCollection(admin, COMMAND_CENTER_COLLECTIONS.jobs, c);
      if (args.projectId) query = query.where('projectId', '==', cleanProjectId(args.projectId));
      if (args.status) query = query.where('status', '==', args.status);
      query = query.orderBy('createdAtMs', 'desc');
      if (args.status && !args.projectId) query = query.orderBy(admin.firestore.FieldPath.documentId(), 'desc');
      const snap = await query.limit(Math.max(1, Math.min(Number(args.limit) || 20, 50))).get();
      const jobs = [];
      snap.forEach((doc) => jobs.push(doc.data()));
      return textResult({jobs});
    } catch (err) {
      const message = safeText(err && err.message, 2000);
      if (/index|FAILED_PRECONDITION|requires an index/i.test(message)) {
        return textResult(commandCenterJobsListIndexError(args, err));
      }
      throw err;
    }
  });

  server.registerTool('command_center.jobs.reconcile_stale', {
    title: 'Reconcile stale Command Center jobs',
    description: 'Dry-run or expire stale nonterminal jobs and active leases with audit events.',
    inputSchema: {idempotencyKey: z.string().optional(), dryRun: z.boolean().optional(), olderThanMs: z.number().optional(), statuses: z.array(z.string()).optional(), limit: z.number().optional()},
  }, async (args, extra) => textResult(await reconcileStaleJobs(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.cancel', {title: 'Cancel Command Center job', description: 'Cancel a durable job and preserve the audit event.', inputSchema: {idempotencyKey: z.string(), jobId: z.string(), reason: z.string().optional()}}, async (args, extra) => textResult(await transitionJob(admin, await callerFromExtra(admin, extra), args || {}, 'canceled', 'jobs.cancel')));
  server.registerTool('command_center.jobs.resume', {title: 'Resume Command Center job', description: 'Resume a job from its latest checkpoint.', inputSchema: {idempotencyKey: z.string(), jobId: z.string(), reason: z.string().optional()}}, async (args, extra) => textResult(await transitionJob(admin, await callerFromExtra(admin, extra), args || {}, 'running', 'jobs.resume')));

  server.registerTool('command_center.jobs.revise', {
    title: 'Revise Command Center job',
    description: 'Revise a live ticket packet without reviving stale user intent.',
    inputSchema: {idempotencyKey: z.string(), jobId: z.string(), title: z.string().optional(), objective: z.string().optional(), acceptanceCriteria: z.array(z.string()).optional(), constraints: z.array(z.string()).optional(), scopeExclusions: z.array(z.string()).optional(), mutationPolicy: z.record(z.string(), z.string()).optional(), revisionSummary: z.string().optional()},
  }, async (args, extra) => textResult(await reviseJob(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.answer_question', {title: 'Answer Command Center job question', description: 'Record ChatGPT or human answer to a worker question and resume when appropriate.', inputSchema: {idempotencyKey: z.string(), jobId: z.string(), questionId: z.string().optional(), answer: z.string(), decision: z.string().optional()}}, async (args, extra) => textResult(await answerQuestion(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.jobs.authorize_mutation', {title: 'Authorize Command Center mutation', description: 'Approve or reject a requested worker mutation under the ticket mutation policy. Workers cannot silently elevate permissions.', inputSchema: {idempotencyKey: z.string(), jobId: z.string(), action: z.string(), approved: z.boolean(), reason: z.string().optional(), evidenceRefs: z.array(z.string()).optional()}}, async (args, extra) => textResult(await authorizeMutation(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.get_summary', {title: 'Get Command Center job summary', description: 'Read compact resumable worker-state checkpoint plus job status.', inputSchema: {jobId: z.string()}}, async (args, extra) => {
    const c = await callerFromExtra(admin, extra);
    const jobId = cleanJobId(args.jobId);
    const handoff = await synthesizeJobHandoff(admin, jobId);
    return textResult({jobId, status: handoff.job.status, checkpoint: handoff.checkpoint, counters: handoff.counters, recommendedNextAction: handoff.review.recommendedNextAction, job: await getJob(admin, jobId)});
  });
  server.registerTool('command_center.jobs.get_handoff', {title: 'Get Command Center job handoff', description: 'Read a compact review/correction packet synthesized from job state, events, logs, artifacts, checkpoints, and bucket objects.', inputSchema: {jobId: z.string()}}, async (args) => textResult({handoff: await synthesizeJobHandoff(admin, cleanJobId(args.jobId))}));
  server.registerTool('command_center.jobs.get_events', {title: 'Get Command Center job events', description: 'Read structured job events generated from Command Center state, not another chat agent.', inputSchema: {jobId: z.string(), limit: z.number().optional()}}, async (args) => textResult({events: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.events, cleanJobId(args.jobId), Math.max(1, Math.min(Number(args.limit) || 50, 100)))}));
  server.registerTool('command_center.jobs.get_logs', {title: 'Get Command Center job logs', description: 'Read append-only log metadata for a job.', inputSchema: {jobId: z.string(), limit: z.number().optional()}}, async (args) => textResult({logs: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.logs, cleanJobId(args.jobId), Math.max(1, Math.min(Number(args.limit) || 50, 100)))}));
  server.registerTool('command_center.jobs.get_artifacts', {title: 'Get Command Center job artifacts', description: 'Read artifact metadata and object references for a job.', inputSchema: {jobId: z.string(), limit: z.number().optional()}}, async (args) => textResult({artifacts: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.artifacts, cleanJobId(args.jobId), Math.max(1, Math.min(Number(args.limit) || 50, 100)))}));

  server.registerTool('command_center.bucket.get_layout', {
    title: 'Get Command Center bucket layout',
    description: 'Read the managed Command Center knowledge bucket lanes for durable memory, skills, and cross-repo notes.',
    inputSchema: {},
  }, async () => textResult({layout: COMMAND_CENTER_BUCKET_LAYOUT, kinds: COMMAND_CENTER_BUCKET_KINDS}));

  server.registerTool('command_center.bucket.put_object', {
    title: 'Put Command Center bucket object',
    description: 'Create or update a durable Command Center bucket object. Use this for execution memory, scratch/promoted skills, and cross-repo notes. Do not store secrets.',
    inputSchema: {
      idempotencyKey: z.string(),
      bucketId: z.string().optional(),
      objectId: z.string().optional(),
      kind: z.enum(COMMAND_CENTER_BUCKET_KINDS),
      path: z.string().optional(),
      title: z.string(),
      summary: z.string().optional(),
      body: z.string().optional(),
      objectUri: z.string().optional(),
      contentHash: z.string().optional(),
      projectId: z.string().optional(),
      repository: z.string().optional(),
      jobId: z.string().optional(),
      sourceRefs: z.array(z.string()).optional(),
      evidenceRefs: z.array(z.string()).optional(),
      tags: z.array(z.string()).optional(),
      promotionState: z.string().optional(),
      supersedes: z.array(z.string()).optional(),
    },
  }, async (args, extra) => textResult(await putBucketObject(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.bucket.get_object', {
    title: 'Get Command Center bucket object',
    description: 'Read one Command Center bucket object by id.',
    inputSchema: {objectId: z.string()},
  }, async (args) => textResult(await getBucketObject(admin, args || {})));

  server.registerTool('command_center.bucket.list_objects', {
    title: 'List Command Center bucket objects',
    description: 'List durable Command Center bucket memory, skills, and cross-repo notes with optional filters.',
    inputSchema: {bucketId: z.string().optional(), kind: z.enum(COMMAND_CENTER_BUCKET_KINDS).optional(), projectId: z.string().optional(), repository: z.string().optional(), jobId: z.string().optional(), tag: z.string().optional(), limit: z.number().optional()},
  }, async (args) => textResult(await listBucketObjects(admin, args || {})));

  server.registerTool('command_center.bucket.promote_skill', {
    title: 'Promote Command Center scratch skill',
    description: 'Promote a scratch skill bucket object into the promoted skill lane while preserving provenance and supersession links.',
    inputSchema: {idempotencyKey: z.string(), objectId: z.string(), path: z.string().optional(), title: z.string().optional(), summary: z.string().optional(), body: z.string().optional(), evidenceRefs: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await promoteBucketSkill(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.workers.register_oneshot', {
    title: 'Register one-shot Command Center worker',
    description: 'Register a user-owned one-shot Codex worker and return a worker token once. Store it only on the worker host.',
    inputSchema: {idempotencyKey: z.string(), workerId: z.string(), engine: z.string().optional(), location: z.string().optional(), capabilities: z.array(z.string()).optional(), baseWorkspace: z.record(z.string(), z.any()).optional(), baseWorkspaces: z.array(z.record(z.string(), z.any())).optional(), limits: z.record(z.string(), z.any()).optional(), activation: z.record(z.string(), z.any()).optional(), runtime: z.record(z.string(), z.any()).optional(), cloudRunJob: z.record(z.string(), z.any()).optional(), sessionPolicy: z.record(z.string(), z.any()).optional(), repositoryAffinity: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await registerOneShotWorker(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.app_control.seed_profiles', {
    title: 'Seed app-control profiles',
    description: 'Publish built-in installed-app automation seed profiles into Home Center cloud Firestore and the managed bucket. Use this to make phone-specific discoveries available to paired devices.',
    inputSchema: {idempotencyKey: z.string()},
  }, async (args, extra) => textResult(await seedAppControlProfiles(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.app_control.put_profile', {
    title: 'Put app-control profile',
    description: 'Create or update a Home Center cloud app-control profile versioned by Android package and app version.',
    inputSchema: {idempotencyKey: z.string(), profile: z.record(z.string(), z.any())},
  }, async (args, extra) => textResult(await putAppControlProfile(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.app_control.get_profile', {
    title: 'Get app-control profile',
    description: 'Read one Home Center cloud app-control profile by profileId.',
    inputSchema: {profileId: z.string()},
  }, async (args) => textResult(await getAppControlProfile(admin, args || {})));

  server.registerTool('command_center.app_control.list_profiles', {
    title: 'List app-control profiles',
    description: 'List Home Center cloud app-control profiles, optionally filtered by package, workflow, or status.',
    inputSchema: {packageName: z.string().optional(), workflow: z.string().optional(), status: z.string().optional(), limit: z.number().optional()},
  }, async (args) => textResult(await listAppControlProfiles(admin, args || {})));

  server.registerTool('command_center.app_control.record_run', {
    title: 'Record app-control run',
    description: 'Record redacted execution evidence, timings, frame-lane status, and learned fixes for a cloud app-control profile.',
    inputSchema: {idempotencyKey: z.string(), profileId: z.string(), workflow: z.string(), runId: z.string().optional(), packageName: z.string().optional(), deviceAlias: z.string().optional(), status: z.string().optional(), elapsedMs: z.number().optional(), uiActionCount: z.number().optional(), frameLane: z.record(z.string(), z.any()).optional(), summary: z.string().optional(), learnedFixes: z.array(z.string()).optional(), evidenceRefs: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await recordAppControlRun(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.browser_sessions.create', {
    title: 'Create browser-hands session',
    description: 'Create a Home Center browser-hands session. Playwright desktop Chromium is the required browser runtime for v1; Shizuku is only the Android fallback lane.',
    inputSchema: {idempotencyKey: z.string(), sessionId: z.string().optional(), intent: z.string(), startUrl: z.string().optional(), surface: z.record(z.string(), z.any()).optional(), accessibilityMode: z.string().optional(), safetyMode: z.string().optional(), learningPolicy: z.string().optional()},
  }, async (args, extra) => textResult(await createBrowserSession(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.browser_sessions.observe', {
    title: 'Observe browser-hands session',
    description: 'Read a browser-hands session and recent recorded episodes.',
    inputSchema: {sessionId: z.string(), limit: z.number().optional()},
  }, async (args) => textResult(await observeBrowserSession(admin, args || {})));

  server.registerTool('command_center.browser_sessions.act', {
    title: 'Request browser-hands action',
    description: 'Record or request a constrained browser action. Sensitive, purchase, payment, CAPTCHA, and account-security actions are blocked for human control.',
    inputSchema: {idempotencyKey: z.string(), sessionId: z.string(), actionId: z.string().optional(), action: z.string(), target: z.record(z.string(), z.any()).optional(), value: z.string().optional(), reason: z.string().optional(), jobId: z.string().optional()},
  }, async (args, extra) => textResult(await requestBrowserAction(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.browser_sessions.record_episode', {
    title: 'Record browser-hands episode',
    description: 'Record a redacted Playwright/Netrunner browser episode and extract candidate discoveries. Every invocation should call this before completion.',
    inputSchema: {idempotencyKey: z.string(), episodeId: z.string().optional(), sessionId: z.string(), intent: z.string().optional(), origin: z.string().optional(), url: z.string().optional(), title: z.string().optional(), surface: z.record(z.string(), z.any()).optional(), outcome: z.string().optional(), accessibilitySummary: z.string().optional(), visibleTextSummary: z.string().optional(), focusedElement: z.record(z.string(), z.any()).optional(), actions: z.array(z.record(z.string(), z.any())).optional(), blockers: z.array(z.string()).optional(), redactionReport: z.record(z.string(), z.any()).optional(), discoveryCandidates: z.array(z.record(z.string(), z.any())).optional(), evidenceRefs: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await recordBrowserEpisode(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.browser_discoveries.list', {
    title: 'List browser-hands discoveries',
    description: 'List candidate/tested/trusted browser discoveries by origin, task, or state.',
    inputSchema: {origin: z.string().optional(), task: z.string().optional(), state: z.string().optional(), limit: z.number().optional()},
  }, async (args) => textResult(await listBrowserDiscoveries(admin, args || {})));

  server.registerTool('command_center.browser_discoveries.promote', {
    title: 'Promote browser-hands discovery',
    description: 'Promote a validated browser discovery into a trusted playbook entry. This is the gate that shares behavior globally.',
    inputSchema: {idempotencyKey: z.string(), discoveryId: z.string(), playbookId: z.string().optional(), guidance: z.string().optional(), playbook: z.record(z.string(), z.any()).optional(), evidenceRefs: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await promoteBrowserDiscovery(admin, await callerFromExtra(admin, extra), args || {})));


  server.registerTool('command_center.browser_playbooks.lookup', {
    title: 'Lookup browser playbook',
    description: 'Find a trusted Playwright DOM/accessibility playbook by origin, task, and household replay audience.',
    inputSchema: {origin: z.string().optional(), taskKey: z.string().optional(), task: z.string().optional(), shareScope: z.string().optional(), replayAudience: z.string().optional(), limit: z.number().optional()},
  }, async (args) => textResult(await lookupBrowserPlaybook(admin, args || {})));

  server.registerTool('command_center.workers.wake', {
    title: 'Wake Command Center worker',
    description: 'Invoke a configured real Cloud Run worker so liveness can be proven by heartbeat, without marking registry health directly.',
    inputSchema: {idempotencyKey: z.string(), workerId: z.string(), activationId: z.string().optional(), sessionId: z.string().optional(), projectId: z.string().optional(), reason: z.string().optional(), runLabel: z.string().optional(), currentWorkspaceSnapshotRef: z.string().optional()},
  }, async (args, extra) => textResult(await wakeWorker(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.workers.list', {title: 'List Command Center workers', description: 'List registered Codex workers and their health/capability metadata.', inputSchema: {}}, async (_args, extra) => textResult({workers: recordsVisibleToCaller(await workerRecords(admin), await callerFromExtra(admin, extra))}));
  server.registerTool('command_center.workers.get_capabilities', {title: 'Get Command Center worker capabilities', description: 'Read capability metadata for one registered worker.', inputSchema: {workerId: z.string()}}, async (args, extra) => {
    const workerId = safeText(args.workerId, 120);
    const workers = recordsVisibleToCaller(await workerRecords(admin), await callerFromExtra(admin, extra));
    return textResult({worker: workers.find((worker) => worker.workerId === workerId) || null});
  });
  server.registerTool('command_center.workers.retire', {
    title: 'Retire Command Center worker',
    description: 'Quarantine a stale worker registration without deleting audit history.',
    inputSchema: {idempotencyKey: z.string(), workerId: z.string(), reason: z.string().optional()},
  }, async (args, extra) => textResult(await retireWorker(admin, await callerFromExtra(admin, extra), args || {})));
  return server;
}

function commandCenterProtectedResourceMetadata() {
  return {resource: COMMAND_CENTER_RESOURCE, authorization_servers: [HOME_CENTER_AUTHORIZATION_SERVER_BASE], bearer_methods_supported: ['header'], resource_documentation: 'Command Center is a cloud MCP dispatch plane. It has no frontend or independent chat UI.'};
}

function commandCenterAuthorizationServerMetadata() {
  return {
    issuer: HOME_CENTER_AUTHORIZATION_SERVER_BASE,
    authorization_endpoint: `${HOME_CENTER_AUTHORIZATION_SERVER_BASE}/oauth/authorize`,
    token_endpoint: `${HOME_CENTER_AUTHORIZATION_SERVER_BASE}/oauth/token`,
    registration_endpoint: `${HOME_CENTER_AUTHORIZATION_SERVER_BASE}/oauth/register`,
    response_types_supported: ['code'],
    grant_types_supported: ['authorization_code', 'refresh_token'],
    token_endpoint_auth_methods_supported: ['none'],
    code_challenge_methods_supported: ['plain', 'S256'],
    delegated_resource: COMMAND_CENTER_RESOURCE,
  };
}

function createCommandCenterMcpApp({admin}) {
  const app = express();
  app.use(express.json({limit: '4mb'}));
  app.use(express.urlencoded({extended: false, limit: '256kb'}));
  app.get('/', (_req, res) => res.json({ok: true, service: 'command-center-mcp', product: 'cloud MCP control plane', endpoints: ['/mcp'], hasFrontend: false}));
  app.get('/.well-known/oauth-protected-resource', (_req, res) => { res.set('Cache-Control', 'no-store'); res.json(commandCenterProtectedResourceMetadata()); });
  app.get('/.well-known/oauth-authorization-server', (_req, res) => { res.set('Cache-Control', 'no-store'); res.json(commandCenterAuthorizationServerMetadata()); });
  const sendWorkerError = (res, err) => res.status(err.status || 500).json({ok: false, error: safeText(err.message, 500) || 'Command Center worker gateway failure.'});

  app.post('/agent/claim', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      res.json(await claimActivationForWorker(admin, caller, req.body || {}));
    } catch (err) {
      sendWorkerError(res, err);
    }
  });

  app.post('/agent/heartbeat', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      const activation = await requireWorkerOwnedActivation(admin, caller, req.body && req.body.activationId);
      const nowMs = Date.now();
      const status = ['queued', 'claimed'].includes(activation.status) ? 'running' : activation.status;
      await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).doc(activation.activationId).set({
        status,
        lastWorkerHeartbeatAtMs: nowMs,
        updatedAtMs: nowMs,
        currentPhase: safeText(req.body && req.body.currentPhase, 120),
        workerStatusSummary: safeText(req.body && req.body.summary, 1000),
      }, {merge: true});
      await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(caller.workerId).set({lastHeartbeatAtMs: nowMs, health: 'healthy', routable: true, simulated: false}, {merge: true});
      res.json({ok: true, activationId: activation.activationId, status, workerId: caller.workerId});
    } catch (err) {
      sendWorkerError(res, err);
    }
  });

  app.post('/agent/codex-ref', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      const activation = await requireWorkerOwnedActivation(admin, caller, req.body && req.body.activationId);
      const result = await recordCodexCloudRef(admin, {actor: caller.workerId}, {
        ...(req.body || {}),
        activationId: activation.activationId,
        activationStatus: 'running',
        idempotencyKey: safeText(req.body && req.body.idempotencyKey, 180) || `worker-codex-ref-${activation.activationId}-${caller.workerId}`,
      });
      res.json({ok: true, ...result});
    } catch (err) {
      sendWorkerError(res, err);
    }
  });

  app.post('/agent/artifacts', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      const activation = await requireWorkerOwnedActivation(admin, caller, req.body && req.body.activationId);
      const artifacts = (Array.isArray(req.body && req.body.artifacts) ? req.body.artifacts : [req.body && req.body.artifact]).filter(Boolean);
      const written = [];
      for (const artifact of artifacts.slice(0, 80)) {
        const result = await recordAgentArtifact(admin, {actor: caller.workerId}, {
          ...artifact,
          activationId: activation.activationId,
          idempotencyKey: safeText(artifact.idempotencyKey, 180) || `worker-artifact-${activation.activationId}-${caller.workerId}-${written.length}`,
        });
        written.push(result.artifact);
      }
      res.json({ok: true, activationId: activation.activationId, artifacts: written});
    } catch (err) {
      sendWorkerError(res, err);
    }
  });

  app.post('/agent/complete', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      const activation = await requireWorkerOwnedActivation(admin, caller, req.body && req.body.activationId);
      const result = await completeAgentActivation(admin, {actor: caller.workerId}, {
        ...(req.body || {}),
        activationId: activation.activationId,
        idempotencyKey: safeText(req.body && req.body.idempotencyKey, 180) || `worker-complete-${activation.activationId}-${caller.workerId}`,
      });
      res.json({ok: true, ...result});
    } catch (err) {
      sendWorkerError(res, err);
    }
  });

  app.post('/worker/lease', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      const job = await leasedJobForWorker(admin, caller.workerId, req.body && req.body.jobId);
      if (!job) {
        res.json({ok: true, leased: false});
        return;
      }
      await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(job.jobId).set({updatedAtMs: Date.now(), workerAcceptedLeaseAtMs: Date.now()}, {merge: true});
      const activationSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobActivations).where('jobId', '==', job.jobId).limit(10).get();
      const batch = admin.firestore().batch();
      let acceptedActivations = 0;
      activationSnap.forEach((doc) => {
        const activation = doc.data() || {};
        if (activation.workerId === caller.workerId && activation.status === 'requested') {
          acceptedActivations += 1;
          batch.set(doc.ref, {status: 'accepted', acceptedAtMs: Date.now(), updatedAtMs: Date.now(), executorId: safeText(req.body && req.body.executorId, 180)}, {merge: true});
        }
      });
      if (acceptedActivations) await batch.commit();
      await appendEvent(admin, {type: 'worker_started', jobId: job.jobId, projectId: job.projectId, actor: caller.workerId, summary: 'One-shot worker accepted lease.', data: {baseWorkspace: job.baseWorkspace}});
      await appendEvent(admin, {type: 'activation_accepted', jobId: job.jobId, projectId: job.projectId, actor: caller.workerId, summary: 'Worker accepted queued activation by claiming the lease.', data: {workerId: caller.workerId}});
      res.json({ok: true, leased: true, packet: jobPacket(job, await getLatestCheckpoint(admin, job.jobId))});
    } catch (err) {
      sendWorkerError(res, err);
    }
  });

  app.post('/worker/events', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      const jobId = cleanJobId(req.body && req.body.jobId);
      const job = await getJob(admin, jobId);
      if (job.selectedWorkerId !== caller.workerId) {
        const err = new Error('Worker cannot attach events to a job it does not own.');
        err.status = 403;
        throw err;
      }
      const event = await appendEvent(admin, {type: req.body.type || 'worker_event', jobId, projectId: job.projectId, actor: caller.workerId, summary: req.body.summary || '', evidenceRefs: req.body.evidenceRefs || [], requiresHumanDecision: req.body.requiresHumanDecision === true, recommendedAction: req.body.recommendedAction || '', data: safeObject(req.body.data)});
      await recordLog(admin, jobId, job.projectId, req.body.summary || req.body.type || 'worker_event', {type: event.type, actor: caller.workerId, ...(safeObject(req.body.data))});
      if (event.type === 'executor_heartbeat') {
        await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set({updatedAtMs: Date.now(), lastWorkerHeartbeatAtMs: Date.now()}, {merge: true});
        const leaseSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).where('jobId', '==', jobId).limit(10).get();
        const batch = admin.firestore().batch();
        let leaseUpdates = 0;
        leaseSnap.forEach((doc) => {
          const lease = doc.data() || {};
          if (lease.workerId === caller.workerId && lease.status === 'active') {
            leaseUpdates += 1;
            batch.set(doc.ref, {heartbeatAtMs: Date.now()}, {merge: true});
          }
        });
        if (leaseUpdates) await batch.commit();
      }
      res.json({ok: true, event});
    } catch (err) {
      sendWorkerError(res, err);
    }
  });

  app.post('/worker/artifacts', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      const jobId = cleanJobId(req.body && req.body.jobId);
      const job = await getJob(admin, jobId);
      if (job.selectedWorkerId !== caller.workerId) {
        const err = new Error('Worker cannot attach artifacts to a job it does not own.');
        err.status = 403;
        throw err;
      }
      const artifacts = (Array.isArray(req.body.artifacts) ? req.body.artifacts : [req.body.artifact]).filter(Boolean);
      const written = [];
      for (const artifact of artifacts.slice(0, 80)) written.push(await recordArtifact(admin, jobId, job.projectId, artifact, job.ownerKey));
      await appendEvent(admin, {type: 'artifacts_recorded', jobId, projectId: job.projectId, actor: caller.workerId, summary: `Recorded ${written.length} artifact(s).`, data: {artifactIds: written.map((artifact) => artifact.artifactId)}});
      res.json({ok: true, artifacts: written});
    } catch (err) {
      sendWorkerError(res, err);
    }
  });

  app.post('/worker/checkpoint', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      const jobId = cleanJobId(req.body && req.body.jobId);
      const job = await getJob(admin, jobId);
      if (job.selectedWorkerId !== caller.workerId) {
        const err = new Error('Worker cannot checkpoint a job it does not own.');
        err.status = 403;
        throw err;
      }
      const checkpoint = {
        checkpointId: `chk_${Date.now()}_${randomUUID().slice(0, 8)}`,
        jobId,
        projectId: job.projectId,
        ownerKey: safeText(job.ownerKey, 80),
        objective: job.objective || '',
        acceptanceCriteriaStatus: Array.isArray(req.body.acceptanceCriteriaStatus) ? req.body.acceptanceCriteriaStatus : [],
        usageSummary: safeObject(req.body.usageSummary),
        currentPhase: safeText(req.body.currentPhase, 120) || job.status,
        repositoryCommit: safeText(req.body.repositoryCommit, 160),
        workingTreeState: safeText(req.body.workingTreeState, 120),
        filesInspected: safeList(req.body.filesInspected, 200, 500),
        filesChanged: safeList(req.body.filesChanged, 200, 500),
        decisionsMade: safeList(req.body.decisionsMade, 200, 1000),
        failedApproaches: safeList(req.body.failedApproaches, 200, 1000),
        testsRun: safeList(req.body.testsRun, 100, 1000),
        openQuestions: safeList(req.body.openQuestions, 100, 1000),
        nextAction: safeText(req.body.nextAction, 1000),
        evidenceRefs: safeList(req.body.evidenceRefs, 100, 1000),
        baseWorkspace: job.baseWorkspace || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE,
        requiredArtifacts: job.requiredArtifacts || COMMAND_CENTER_REQUIRED_ARTIFACTS,
        executionMode: job.executionMode || 'one_shot',
        createdAtMs: Date.now(),
      };
      await collection(admin, COMMAND_CENTER_COLLECTIONS.checkpoints).doc(checkpoint.checkpointId).set(checkpoint);
      const memoryObject = await recordCurrentMemorySnapshot(admin, checkpoint);
      res.json({ok: true, checkpoint, memoryObject});
    } catch (err) {
      sendWorkerError(res, err);
    }
  });

  app.post('/worker/complete', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      const jobId = cleanJobId(req.body && req.body.jobId);
      const job = await getJob(admin, jobId);
      if (job.selectedWorkerId !== caller.workerId) {
        const err = new Error('Worker cannot complete a job it does not own.');
        err.status = 403;
        throw err;
      }
      const status = req.body.status === 'failed' ? 'failed' : 'completed';
      const finalReport = safeText(req.body.finalReport, 8000);
      const artifacts = Array.isArray(req.body.artifacts) ? req.body.artifacts : [];
      const written = [];
      for (const artifact of artifacts.slice(0, 80)) written.push(await recordArtifact(admin, jobId, job.projectId, artifact, job.ownerKey));
      const events = await listByJob(admin, COMMAND_CENTER_COLLECTIONS.events, jobId, COMMAND_CENTER_COMPLETION_EVENT_LOOKBACK_LIMIT);
      const allArtifacts = [...(await listByJob(admin, COMMAND_CENTER_COLLECTIONS.artifacts, jobId, COMMAND_CENTER_COMPLETION_EVENT_LOOKBACK_LIMIT)), ...written];
      const completionGate = shouldAcceptWorkerCompletion({requestedStatus: status, events, artifacts: allArtifacts, job});
      if (!completionGate.ok) {
        const err = new Error(`Worker completion rejected: ${completionGate.reason}`);
        err.status = 409;
        throw err;
      }
      const completionArtifactIds = Array.from(new Set(allArtifacts.map((artifact) => artifact.artifactId).filter(Boolean)));
      await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set({status, updatedAtMs: Date.now(), completedAtMs: Date.now(), finalReport, completionArtifactIds}, {merge: true});
      const event = await appendEvent(admin, {type: `job_${status}`, jobId, projectId: job.projectId, actor: caller.workerId, summary: finalReport || `One-shot worker marked job ${status}.`, data: {artifactIds: completionArtifactIds}});
      res.json({ok: true, status, event, artifacts: written});
    } catch (err) {
      sendWorkerError(res, err);
    }
  });

  app.all('/mcp', async (req, res) => {
    if (rejectMissingTransportAuth(req, res)) return;
    if (req.method !== 'POST') {
      res.status(405).json({jsonrpc: '2.0', error: {code: -32000, message: 'Method not allowed.'}, id: null});
      return;
    }
    const server = createCommandCenterMcpServer({admin});
    const transport = new StreamableHTTPServerTransport({sessionIdGenerator: undefined});
    let closed = false;
    const closeTransport = async () => {
      if (closed) return;
      closed = true;
      await Promise.allSettled([transport.close(), server.close()]);
    };
    try {
      res.on('close', () => { closeTransport().catch(() => {}); });
      await server.connect(transport);
      await transport.handleRequest(req, res, req.body);
    } finally {
      await closeTransport();
    }
  });
  return app;
}

module.exports = {
  COMMAND_CENTER_COLLECTIONS,
  COMMAND_CENTER_DEFAULT_WORKERS,
  COMMAND_CENTER_REQUIRED_ARTIFACTS,
  COMMAND_CENTER_DEFAULT_BASE_WORKSPACE,
  COMMAND_CENTER_DEFAULT_BUCKET_ID,
  COMMAND_CENTER_BUCKET_KINDS,
  COMMAND_CENTER_BUCKET_LAYOUT,
  createCommandCenterMcpApp,
  createCommandCenterMcpServer,
  cleanBaseWorkspace,
  cleanMutationPolicy,
  cleanOneShotExecution,
  cleanBucketObject,
  selectWorker,
};
