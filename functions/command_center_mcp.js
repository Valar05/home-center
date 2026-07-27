const {createHash, randomUUID} = require('node:crypto');
const {Storage} = require('@google-cloud/storage');
const {SecretManagerServiceClient} = require('@google-cloud/secret-manager');
const express = require('express');
const {z} = require('zod/v4');
const {McpServer} = require('@modelcontextprotocol/sdk/server/mcp.js');
const {StreamableHTTPServerTransport} = require('@modelcontextprotocol/sdk/server/streamableHttp.js');
const {APP_CONTROL_COLLECTIONS, APP_CONTROL_DEFAULT_SEEDS, appControlProfileObjectId, appControlProfilePath} = require('./app_control_cloud');

const DEFAULT_COMMAND_CENTER_PUBLIC_BASE = 'https://us-central1-home-center-dclar.cloudfunctions.net/commandCenterMcp';
const COMMAND_CENTER_PUBLIC_BASE = process.env.COMMAND_CENTER_MCP_PUBLIC_BASE || DEFAULT_COMMAND_CENTER_PUBLIC_BASE;
const COMMAND_CENTER_RESOURCE = `${COMMAND_CENTER_PUBLIC_BASE}/mcp`;
const COMMAND_CENTER_RESOURCE_METADATA = `${COMMAND_CENTER_PUBLIC_BASE}/.well-known/oauth-protected-resource`;
const COMMAND_CENTER_MCP_SERVER_VERSION = '0.3.0';
const COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED = true;
const COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE = 'command_center_codex_worker_discovery_permanently_disabled';
const COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_MESSAGE = 'Command Center Codex worker discovery was permanently disabled on 2026-07-27. This operation cannot discover, provision, route, wake, register, lease, or resume Codex workers.';
const COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATIONS = Object.freeze([
  'system.health',
  'jobs.create',
  'jobs.create_followup',
  'jobs.dispatch_queued',
  'jobs.resume',
  'jobs.answer_question',
  'agents.create_activation',
  'agents.get_resume_packet',
  'agents.record_codex_cloud_ref',
  'agents.record_artifact',
  'agents.complete_activation',
  'workers.provision',
  'provisioning.inspect',
  'provisioning.reconcile',
  'machine_images.register',
  'machine_images.list',
  'machine_images.inspect',
  'codex_sessions.create',
  'codex_sessions.list',
  'codex_sessions.inspect',
  'codex_sessions.reconcile',
  'hosts.list',
  'hosts.inspect',
  'workers.register_oneshot',
  'workers.wake',
  'workers.retire',
  'workers.list',
  'workers.inspect',
  'routing.explain',
  'workers.reconcile',
  'workers.request_restart',
  'proof.run_multi_worker',
  'proof.run_multi_session',
  'workers.get_capabilities',
]);
const COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATION_SET = new Set(COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATIONS);
const COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_TOOL_NAMES = Object.freeze(
  COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATIONS.map((operation) => `command_center.${operation}`),
);

function normalizeCodexWorkerDiscoveryOperation(value) {
  return String(value || '').trim().replace(/^command_center\./, '');
}

function isCodexWorkerDiscoveryOperationDisabled(operation) {
  return COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATION_SET.has(normalizeCodexWorkerDiscoveryOperation(operation));
}

function codexWorkerDiscoveryDisabledError(operation) {
  const normalizedOperation = normalizeCodexWorkerDiscoveryOperation(operation);
  const err = new Error(COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_MESSAGE);
  err.status = 410;
  err.code = COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE;
  err.failureKind = COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE;
  err.operation = normalizedOperation;
  return err;
}

function assertCodexWorkerDiscoveryOperationEnabled(operation) {
  if (COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED && isCodexWorkerDiscoveryOperationDisabled(operation)) {
    throw codexWorkerDiscoveryDisabledError(operation);
  }
}

function removeDisabledCodexWorkerDiscoveryTools(server) {
  if (!COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED) return server;
  for (const toolName of COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_TOOL_NAMES) {
    delete server._registeredTools[toolName];
  }
  return server;
}
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
  appControlProfiles: APP_CONTROL_COLLECTIONS.profiles,
  appControlRuns: APP_CONTROL_COLLECTIONS.runs,
  browserSessions: 'browserSessions',
  browserEpisodes: 'browserEpisodes',
  browserDiscoveries: 'browserDiscoveries',
  browserPlaybooks: 'browserPlaybooks',
  baseWorkspaces: 'commandCenterBaseWorkspaces',
  repoAgents: 'commandCenterRepoAgents',
  agentSessions: 'commandCenterAgentSessions',
  machineImages: 'commandCenterMachineImages',
  provisioningRequests: 'commandCenterProvisioningRequests',
  agentActivations: 'commandCenterAgentActivations',
  agentArtifacts: 'commandCenterAgentArtifacts',
  codexCloudRefs: 'commandCenterCodexCloudRefs',
  agentContextSnapshots: 'commandCenterAgentContextSnapshots',
  jobActivations: 'commandCenterJobActivations',
  workerTokens: 'commandCenterWorkerTokens',
  renderRequests: 'commandCenterRenderRequests',
  idempotency: 'commandCenterIdempotency',
});
const COMMAND_CENTER_DEFAULT_BUCKET_ID = 'command-center';
const COMMAND_CENTER_BUCKET_KINDS = Object.freeze([
  'memory.past_log',
  'memory.current_condensed',
  'skill.scratch',
  'skill.promoted',
  'note.cross_repo',
  'app_control.profile',
  'app_control.run',
  'app_control.frame_lane',
  'browser.session',
  'browser.episode',
  'browser.discovery',
  'browser.playbook',
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
    'app-control/profiles': {kind: 'app_control.profile', role: 'cloud-owned installed-app automation profiles versioned by app package and version'},
    'app-control/runs': {kind: 'app_control.run', role: 'redacted execution observations, timings, frame-lane status, and learned fixes'},
    'app-control/frame-lanes': {kind: 'app_control.frame_lane', role: 'bounded foreground execution contracts for cases where true background control is unavailable'},
    'browser/sessions': {kind: 'browser.session', role: 'Playwright browser-hand session intents, runtime surface, and safety state'},
    'browser/episodes': {kind: 'browser.episode', role: 'redacted browser task observations captured from every invocation'},
    'browser/discoveries': {kind: 'browser.discovery', role: 'candidate and trusted reusable claims extracted from browser episodes'},
    'browser/playbooks': {kind: 'browser.playbook', role: 'promoted site and task guidance for accessible browser hands'},
  },
});
const COMMAND_CENTER_ALLOWED_STATUSES = ['queued', 'activating', 'leased', 'executing', 'running', 'question', 'awaiting_mutation_authorization', 'completed', 'failed', 'canceled', 'expired'];
const COMMAND_CENTER_AGENT_ACTIVATION_STATUSES = ['queued', 'claimed', 'running', 'needs_human', 'completed', 'failed', 'canceled'];
const COMMAND_CENTER_JOB_ACTIVATION_STATUSES = Object.freeze(['requested', 'accepted', 'rejected', 'timed_out', 'completed', 'failed']);
const COMMAND_CENTER_WORKER_HEARTBEAT_FRESH_MS = 2 * 60 * 1000;
const COMMAND_CENTER_ACTIVATION_VERIFIED_FRESH_MS = 10 * 60 * 1000;
const COMMAND_CENTER_ACTIVATION_TIMEOUT_MS = 60 * 1000;
const COMMAND_CENTER_COLD_START_HEARTBEAT_DEADLINE_MS = 2 * 60 * 1000;
const COMMAND_CENTER_COMPLETION_EVENT_LOOKBACK_LIMIT = 1000;
const COMMAND_CENTER_TERMINAL_JOB_STATUSES = Object.freeze(['completed', 'failed', 'canceled', 'expired']);
const COMMAND_CENTER_RECONCILE_DEFAULT_OLDER_THAN_MS = 30 * 60 * 1000;
const COMMAND_CENTER_WORKER_PROTOCOL_VERSION = 'command-center-worker-v2';
const COMMAND_CENTER_MIN_RUNNER_VERSION = 'command-center-runner-v2';
const COMMAND_CENTER_MACHINE_IMAGE_STATUSES = Object.freeze(['available', 'materializing', 'missing', 'retired', 'quarantined']);
const COMMAND_CENTER_CODEX_SESSION_STATUSES = Object.freeze(['idle', 'allocated', 'running', 'recoverable', 'failed', 'quarantined', 'retired', 'active']);
const COMMAND_CENTER_SESSION_ISOLATION_MODES = Object.freeze(['session', 'host', 'image']);
const COMMAND_CENTER_LEGACY_WORKER_IDS = Object.freeze(['termux-tanks-oneshot']);
const COMMAND_CENTER_PROOF_EXCLUDED_WORKER_IDS = Object.freeze(['termux-tanks-oneshot']);
const COMMAND_CENTER_DEFAULT_CLOUD_PROJECT = process.env.GCLOUD_PROJECT || process.env.GOOGLE_CLOUD_PROJECT || 'home-center-dclar';
const COMMAND_CENTER_DEFAULT_CLOUD_REGION = process.env.COMMAND_CENTER_WORKER_REGION || 'us-central1';
const COMMAND_CENTER_DEFAULT_CLOUD_WORKER_REPOSITORY = process.env.COMMAND_CENTER_WORKER_REPOSITORY || 'command-center-workers';
const COMMAND_CENTER_DEFAULT_CLOUD_WORKER_IMAGE = process.env.COMMAND_CENTER_CLOUD_WORKER_IMAGE || `${COMMAND_CENTER_DEFAULT_CLOUD_REGION}-docker.pkg.dev/${COMMAND_CENTER_DEFAULT_CLOUD_PROJECT}/${COMMAND_CENTER_DEFAULT_CLOUD_WORKER_REPOSITORY}/debian-codex:latest`;
const COMMAND_CENTER_DEFAULT_CLOUD_MACHINE_IMAGE_ID = 'cloud-debian-codex';
const COMMAND_CENTER_PROVISIONING_STATUSES = Object.freeze(['requested', 'secrets_ready', 'job_created', 'activation_requested', 'routable', 'failed', 'blocked']);
const COMMAND_CENTER_RENDER_TOOL_VERSION = 'command-center-blender-render-v1';
const COMMAND_CENTER_RENDER_DEFAULT_SERVICE_URL = process.env.COMMAND_CENTER_RENDER_SERVICE_URL || '';
const COMMAND_CENTER_RENDER_BUCKET = process.env.COMMAND_CENTER_RENDER_BUCKET || process.env.RENDER_CACHE_BUCKET || process.env.COMMAND_CENTER_GENERATED_BUCKET || process.env.HOME_CENTER_GENERATED_BUCKET || 'home-center-generated';
const COMMAND_CENTER_RENDER_MAX_GLB_BYTES = Number(process.env.COMMAND_CENTER_RENDER_MAX_GLB_BYTES || 250 * 1024 * 1024);
const COMMAND_CENTER_RENDER_MAX_SCRIPT_BYTES = Number(process.env.COMMAND_CENTER_RENDER_MAX_SCRIPT_BYTES || 1024 * 1024);
const COMMAND_CENTER_RENDER_REQUIRED_BUNDLE_KINDS = Object.freeze([
  'rendered_frames',
  'contact_sheet',
  'native_pose_animation_data',
  'script_input_hashes',
  'blender_version_settings',
  'stdout_stderr',
  'fixed_camera_renders',
  'diagnostic_view_renders',
  'validation_manifest',
  'original_script',
]);

const COMMAND_CENTER_ALLOWED_EMAILS = Object.freeze([
  'dclarke1005@gmail.com',
  'junewren28@gmail.com',
  'timothypomeroy07@gmail.com',
]);
const COMMAND_CENTER_ALLOWED_EMAIL_SET = new Set(COMMAND_CENTER_ALLOWED_EMAILS);

function requireCommandCenterAllowedEmail(email) {
  const clean = safeText(email, 320).toLowerCase();
  if (COMMAND_CENTER_ALLOWED_EMAIL_SET.has(clean)) return clean;
  const err = new Error('command_center_forbidden: this Command Center MCP is restricted to approved Home Center accounts.');
  err.status = 403;
  err.failureKind = 'command_center_forbidden_email';
  throw err;
}

function isTerminalJobStatus(status) {
  return COMMAND_CENTER_TERMINAL_JOB_STATUSES.includes(safeText(status, 80));
}

const COMMAND_CENTER_DURABLE_SESSION_RESTORE_STRATEGIES = Object.freeze(['gcs_snapshot', 'git_clean_clone', 'empty_workspace', 'artifact_bundle']);
const COMMAND_CENTER_CODEX_CLOUD_SURFACE = Object.freeze({
  surfaceId: 'openai-codex-cloud',
  role: 'real OpenAI Codex cloud agent surface consuming Drew account quota; Command Center stores durable refs and artifacts only',
  launchUrl: 'https://chatgpt.com/codex/',
  credentialPolicy: 'Persistent login may live only in a user-owned browser profile on the bridge host. Do not copy cookies, passwords, OAuth tokens, or session blobs into Command Center.',
});
const COMMAND_CENTER_EXECUTION_MODES = ['one_shot', 'executor_pulse', 'codex_smoke'];
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

function safeNumberList(value, maxItems = 80) {
  return Array.isArray(value) ? value.slice(0, maxItems).map((item) => Number(item)).filter((item) => Number.isFinite(item)) : [];
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

function sha256Bytes(value) {
  return createHash('sha256').update(Buffer.isBuffer(value) ? value : Buffer.from(value || '')).digest('hex');
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
  const email = requireCommandCenterAllowedEmail(data.email);
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

function normalizeGithubRepositoryRef(value) {
  const text = safeText(value, 1000);
  if (!text || /^(worker-local|gs|file):\/\//i.test(text)) return '';
  let raw = text.split(/[?#]/)[0].replace(/\.git$/i, '');
  if (/^github:\/\//i.test(raw)) raw = raw.replace(/^github:\/\//i, '');
  else if (/^https:\/\/github\.com\//i.test(raw)) raw = raw.replace(/^https:\/\/github\.com\//i, '');
  else if (/^[a-z][a-z0-9+.-]*:\/\//i.test(raw)) return '';
  const parts = raw.split('/').filter(Boolean);
  if (parts.length < 2) return '';
  if (!/^[A-Za-z0-9_.-]+$/.test(parts[0]) || !/^[A-Za-z0-9_.-]+$/.test(parts[1])) return '';
  return `${parts[0]}/${parts[1]}`;
}

function repositoryFromBaseWorkspace(baseWorkspace = {}) {
  const workspace = safeObject(baseWorkspace);
  return normalizeGithubRepositoryRef(workspace.repository) || normalizeGithubRepositoryRef(workspace.snapshotRef);
}

function repositoryFromProject(project = {}) {
  const binding = safeObject(project.repositoryBinding);
  return normalizeGithubRepositoryRef(project.repository) || normalizeGithubRepositoryRef(binding.repository) || repositoryFromBaseWorkspace(project.baseWorkspace);
}

function resolveJobRepository(args = {}, project = {}, baseWorkspace = {}) {
  return normalizeGithubRepositoryRef(args.repository)
    || repositoryFromProject(project)
    || repositoryFromBaseWorkspace(args.baseWorkspace)
    || repositoryFromBaseWorkspace(baseWorkspace);
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
    status: COMMAND_CENTER_CODEX_SESSION_STATUSES.includes(safeText(args.status, 80)) ? safeText(args.status, 80) : 'idle',
    machineImageId: safeText(args.machineImageId || safeObject(args.sessionPolicy).machineImageId, 120),
    imageDigest: safeText(args.imageDigest || safeObject(args.machineImage).digest, 160),
    hostInstallationId: safeText(args.hostInstallationId || args.workerInstallationId, 180),
    workerId: safeText(args.workerId || args.selectedWorkerId, 120),
    workerInstanceId: safeText(args.workerInstanceId, 180),
    sessionSlotId: safeText(args.sessionSlotId, 180),
    isolationMode: COMMAND_CENTER_SESSION_ISOLATION_MODES.includes(safeText(args.isolationMode || safeObject(args.sessionPolicy).isolationMode, 80)) ? safeText(args.isolationMode || safeObject(args.sessionPolicy).isolationMode, 80) : 'session',
    codexAuthMode: safeText(args.codexAuthMode || safeObject(args.runtime).codexAuth || safeObject(args.runtime).authMode, 80),
    latestJobId: safeText(args.latestJobId, 180),
    lastHeartbeatAtMs: Number(args.lastHeartbeatAtMs || 0) || 0,
    hotStartMs: Number(args.hotStartMs || 0) || 0,
    cacheState: safeObject(args.cacheState),
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
    ownerKey: ownerKeyFromCaller(caller),
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

function workerStableIdentity(worker = {}) {
  const data = safeObject(worker);
  return safeText(data.workerInstallationId || data.installationId || data.stableWorkerIdentity || data.hostIdentity || data.machineId || data.workerIdentity || data.workerId, 180);
}

function workerApiKeyProbeAllowsCodex(worker = {}) {
  const data = safeObject(worker);
  const runtime = safeObject(data.runtime);
  const probe = safeObject(runtime.apiKeyCapabilityProbe || runtime.openAiApiKeyProbe || data.apiKeyCapabilityProbe);
  const authMode = safeText(runtime.codexAuth || runtime.authMode || runtime.openAiAuthMode, 80);
  const apiKeyBacked = authMode === 'api_key' || authMode === 'openai_api_key' || data.location === 'gcp-cloud-run-job' || safeText(data.location, 80).includes('cloud-run');
  if (!apiKeyBacked) return {ok: true, reason: 'not api-key-backed'};
  if (probe.ok === true || probe.status === 'ok' || runtime.openAiApiKeyProbeOk === true) return {ok: true, reason: 'api-key capability probe passed'};
  const reason = safeText(probe.failureKind || probe.code || probe.reason || runtime.apiKeyCapabilityProbeStatus, 240) || 'api-key capability probe missing';
  return {ok: false, reason};
}

function isLocalHostWorker(worker = {}) {
  const location = safeText(worker.location, 120).toLowerCase();
  const runtime = safeObject(worker.runtime);
  const activation = normalizeActivationChannel(worker.activation);
  return location.includes('termux')
    || location.includes('android')
    || location.includes('phone')
    || location.includes('local')
    || activation.mode === 'poll'
    || runtime.codexAuth === 'chatgpt_saved_login'
    || runtime.authMode === 'chatgpt_saved_login';
}

function workerRoutingPriority(worker = {}) {
  const location = safeText(worker.location, 120).toLowerCase();
  const runtime = safeObject(worker.runtime);
  const activation = normalizeActivationChannel(worker.activation);
  if (location.includes('cloud-run') || activation.mode === 'cloud_run_job') return 0;
  if (location.includes('cloud') || runtime.codexAuth === 'api_key' || runtime.authMode === 'api_key') return 10;
  if (isLocalHostWorker(worker)) return 1000;
  return 100;
}

function deriveWorkerLiveness(worker, nowMs = Date.now()) {
  const data = safeObject(worker);
  const registryHealth = safeText(data.registryHealth || data.health, 80) || 'unknown';
  const lastHeartbeatAtMs = Number(data.lastHeartbeatAtMs || 0) || 0;
  const heartbeatAgeMs = lastHeartbeatAtMs > 0 ? Math.max(0, nowMs - lastHeartbeatAtMs) : null;
  const heartbeatFresh = lastHeartbeatAtMs > 0 && heartbeatAgeMs <= COMMAND_CENTER_WORKER_HEARTBEAT_FRESH_MS;
  const activation = normalizeActivationChannel(data.activation);
  const activationAgeMs = activation.verifiedAtMs > 0 ? Math.max(0, nowMs - activation.verifiedAtMs) : null;
  const activationFresh = activation.verifiedAtMs > 0 && activationAgeMs <= COMMAND_CENTER_ACTIVATION_VERIFIED_FRESH_MS;
  const cloudRunJob = safeObject(data.cloudRunJob);
  const sessionPolicy = safeObject(data.sessionPolicy);
  const cloudRunConfigured = activation.mode === 'cloud_run_job'
    && !!cloudRunJob.projectId
    && !!cloudRunJob.region
    && !!cloudRunJob.jobName
    && sessionPolicy.durable === true
    && sessionPolicy.snapshotStore === 'gcs';
  const registryRoutable = data.registryRoutable !== false && (data.routable !== false || cloudRunConfigured);
  const activatable = data.simulated !== true && registryHealth === 'healthy' && registryRoutable && cloudRunConfigured;
  const effectiveHealth = registryHealth === 'healthy'
    ? (heartbeatFresh ? 'healthy' : (activatable ? 'activatable' : 'stale'))
    : registryHealth;
  const livenessReason = registryHealth !== 'healthy'
    ? `registry health is ${registryHealth}`
    : (heartbeatFresh
      ? 'heartbeat fresh'
      : (activatable ? 'cloud_run_job activation channel configured' : (lastHeartbeatAtMs > 0 ? 'heartbeat stale' : 'heartbeat missing')));
  return {
    registryHealth,
    registryRoutable,
    health: effectiveHealth,
    lastHeartbeatAtMs,
    heartbeatAgeMs,
    heartbeatFresh,
    activationAgeMs,
    activationFresh,
    activatable,
    livenessState: heartbeatFresh ? 'live' : (activatable ? 'activatable' : (lastHeartbeatAtMs > 0 ? 'stale' : 'registered')),
    livenessReason,
    routable: registryRoutable && (effectiveHealth === 'healthy' || effectiveHealth === 'activatable'),
  };
}


function cleanWorkerIdentity(data = {}) {
  const workerId = safeText(data.workerId, 120);
  const stableWorkerIdentity = workerStableIdentity(data) || workerId;
  const installation = safeText(data.workerInstallationId || data.installationId, 180);
  const instance = safeText(data.workerInstanceId || data.instanceId, 180);
  const runnerVersion = safeText(data.runnerVersion || safeObject(data.runtime).runnerVersion, 80);
  const protocolVersion = safeText(data.protocolVersion || safeObject(data.runtime).protocolVersion, 80);
  const legacyIdentity = !installation || !instance || !runnerVersion || !protocolVersion;
  return {
    workerInstallationId: installation || (stableWorkerIdentity ? `legacy-${hashText(stableWorkerIdentity, 24)}` : ''),
    workerId,
    workerInstanceId: instance,
    stableWorkerIdentity,
    runnerVersion,
    protocolVersion,
    ownerKey: safeText(data.ownerKey, 80),
    legacyIdentity,
    identityStatus: legacyIdentity ? 'legacy_incomplete' : 'v2_complete',
  };
}

function cleanPreparedWorkspaces(data = {}) {
  const raw = Array.isArray(data.preparedWorkspaces) ? data.preparedWorkspaces : (Array.isArray(data.baseWorkspaces) ? data.baseWorkspaces : []);
  return raw.slice(0, 40).map((item) => cleanBaseWorkspace(item));
}


function cleanMachineImage(args = {}, caller = {}) {
  const nowMs = Date.now();
  const imageKind = safeText(args.imageKind || args.kind, 120) || 'codex-worker-image';
  const version = safeText(args.version, 120) || 'unversioned';
  const imageId = slug(args.imageId || args.machineImageId || args.name || `${imageKind}-${version}`, 'machine-image');
  const status = safeText(args.status, 80) || 'available';
  return {
    imageId,
    machineImageId: imageId,
    name: safeText(args.name, 240) || imageId,
    imageKind,
    version,
    digest: safeText(args.digest || args.sha256 || args.imageDigest, 160),
    status: COMMAND_CENTER_MACHINE_IMAGE_STATUSES.includes(status) ? status : 'available',
    capabilities: safeList(args.capabilities || args.requiredCapabilities, 120, 120),
    toolchains: safeList(args.toolchains, 80, 240),
    dependencyBundleRefs: safeList(args.dependencyBundleRefs || args.bundleRefs, 80, 1000),
    warmCacheRefs: safeList(args.warmCacheRefs || args.cacheRefs, 80, 1000),
    materializationModes: safeList(args.materializationModes, 20, 120),
    hotPathInstallAllowed: args.hotPathInstallAllowed === true ? true : false,
    estimatedColdStartMs: Number(args.estimatedColdStartMs || 0) || 0,
    estimatedHotStartMs: Number(args.estimatedHotStartMs || 0) || 0,
    provenance: safeObject(args.provenance),
    ownerKey: safeText(args.ownerKey, 80) || ownerKeyFromCaller(caller),
    createdBy: safeText(args.createdBy, 160) || caller.actor || 'command_center',
    updatedBy: caller.actor || safeText(args.updatedBy, 160),
    createdAtMs: Number(args.createdAtMs || 0) || nowMs,
    updatedAtMs: nowMs,
  };
}

function cleanSessionPolicy(args = {}) {
  const raw = safeObject(args.sessionPolicy || args.executionPolicy || args);
  const allocationRaw = safeText(raw.allocation || raw.allocationMode, 40) || 'auto';
  const isolationRaw = safeText(raw.isolationMode || raw.isolation, 40) || 'session';
  return {
    allocation: ['auto', 'new', 'reuse'].includes(allocationRaw) ? allocationRaw : 'auto',
    isolationMode: COMMAND_CENTER_SESSION_ISOLATION_MODES.includes(isolationRaw) ? isolationRaw : 'session',
    machineImageId: slug(raw.machineImageId || raw.imageId || '', ''),
    imageRequirements: safeList(raw.imageRequirements || raw.requiredImageCapabilities || raw.requiredCapabilities, 40, 120).map((item) => item.toLowerCase()),
    hostRequirements: safeList(raw.hostRequirements, 40, 120).map((item) => item.toLowerCase()),
    requireMaterializedImage: raw.requireMaterializedImage !== false,
    allowMaterializationDuringJob: raw.allowMaterializationDuringJob === true,
    maxColdStartMs: Number(raw.maxColdStartMs || 0) || 0,
    preferredSessionIds: safeList(raw.preferredSessionIds, 40, 180),
  };
}

function workerMachineImageState(worker = {}) {
  const sessionCapacity = safeObject(worker.sessionCapacity);
  const rawInline = Array.isArray(worker.machineImages) ? worker.machineImages : [];
  const inlineImages = rawInline.slice(0, 40).map((item) => cleanMachineImage({...item, ownerKey: worker.ownerKey}, {ownerKey: worker.ownerKey, actor: worker.workerId || 'worker'}));
  const availableImageIds = safeList(worker.availableImageIds || sessionCapacity.availableImageIds, 80, 160).map((item) => slug(item, ''));
  const materializedImageIds = safeList(worker.materializedImageIds || sessionCapacity.materializedImageIds, 80, 160).map((item) => slug(item, ''));
  for (const image of inlineImages) {
    if (!availableImageIds.includes(image.imageId)) availableImageIds.push(image.imageId);
    if (image.status === 'available' && !materializedImageIds.includes(image.imageId)) materializedImageIds.push(image.imageId);
  }
  const maxConcurrentSessions = Math.max(1, Math.min(Number(worker.maxConcurrentSessions || sessionCapacity.maxConcurrentSessions || safeObject(worker.limits).maxConcurrentSessions || safeObject(worker.limits).concurrentSessions || 1) || 1, 100));
  const activeSessionIds = safeList(worker.activeSessionIds || sessionCapacity.activeSessionIds, 100, 180);
  return {
    availableImageIds,
    materializedImageIds,
    machineImages: inlineImages,
    cacheState: safeObject(worker.cacheState || sessionCapacity.cacheState),
    canMaterializeImages: worker.canMaterializeImages === true || sessionCapacity.canMaterializeImages === true,
    sessionIsolationModes: safeList(worker.sessionIsolationModes || sessionCapacity.sessionIsolationModes, 10, 80),
    maxConcurrentSessions,
    activeSessionIds,
    sessionCapacityRemaining: Math.max(0, maxConcurrentSessions - activeSessionIds.length),
  };
}

function machineImageMatchesRequirements(image = {}, requirements = []) {
  const caps = new Set(safeList(image.capabilities, 120, 120).map((cap) => cap.toLowerCase()));
  return requirements.every((req) => caps.has(req));
}

function workerImagePolicyDiagnostic(worker = {}, policyInput = {}, machineImages = []) {
  const policy = cleanSessionPolicy({sessionPolicy: policyInput});
  const state = workerMachineImageState(worker);
  if (!policy.machineImageId && !policy.imageRequirements.length && policy.allowMaterializationDuringJob !== true) return {ok: true, code: 'no_image_policy', reason: 'no machine image constraint requested', selectedMachineImageId: ''};
  if (policy.allowMaterializationDuringJob === true) return {ok: false, code: 'hot_path_materialization_forbidden', reason: 'normal job execution may not install or materialize machine images; prepare the image before routing', selectedMachineImageId: ''};
  if (!policy.requireMaterializedImage) return {ok: true, code: 'image_materialization_not_required', reason: 'session policy does not require a materialized image', selectedMachineImageId: policy.machineImageId};
  const materialized = new Set(state.materializedImageIds);
  if (policy.machineImageId) {
    if (materialized.has(policy.machineImageId)) return {ok: true, code: 'image_materialized', reason: `machine image ${policy.machineImageId} is materialized on host`, selectedMachineImageId: policy.machineImageId};
    return {ok: false, code: 'image_not_materialized', reason: `machine image ${policy.machineImageId} is not materialized on this host`, selectedMachineImageId: policy.machineImageId};
  }
  const allImages = [...machineImages, ...state.machineImages];
  const match = allImages.find((image) => image.status !== 'retired' && materialized.has(slug(image.imageId || image.machineImageId, '')) && machineImageMatchesRequirements(image, policy.imageRequirements));
  if (match) return {ok: true, code: 'image_requirements_materialized', reason: `materialized image ${match.imageId || match.machineImageId} satisfies requirements`, selectedMachineImageId: slug(match.imageId || match.machineImageId, '')};
  return {ok: false, code: 'image_not_materialized', reason: `no materialized machine image satisfies: ${policy.imageRequirements.join(', ')}`, selectedMachineImageId: ''};
}

function workerSessionPolicyDiagnostic(worker = {}, policyInput = {}) {
  const policy = cleanSessionPolicy({sessionPolicy: policyInput});
  const state = workerMachineImageState(worker);
  const modes = state.sessionIsolationModes.length ? state.sessionIsolationModes : ['session'];
  if (!modes.includes(policy.isolationMode)) return {ok: false, code: 'session_isolation_unavailable', reason: `host does not advertise ${policy.isolationMode} isolation`, sessionCapacity: state};
  if (state.sessionCapacityRemaining <= 0) return {ok: false, code: 'session_capacity_exhausted', reason: 'host has no free isolated Codex session slots', sessionCapacity: state};
  return {ok: true, code: 'session_capacity_available', reason: 'host has a compatible isolated Codex session slot', sessionCapacity: state};
}

function workerRoutabilityDiagnostic(worker = {}, nowMs = Date.now()) {
  const data = safeObject(worker);
  const identity = cleanWorkerIdentity(data);
  const liveness = deriveWorkerLiveness(data, nowMs);
  const caps = safeList(data.capabilities, 120, 120).map((item) => item.toLowerCase());
  const runtime = safeObject(data.runtime);
  if (data.simulated === true) return {routable: false, code: 'simulated_worker', reason: 'simulated placeholder is not executable'};
  if (data.status === 'retired' || data.retiredAtMs) return {routable: false, code: 'retired_worker', reason: 'worker registration is retired'};
  if (COMMAND_CENTER_LEGACY_WORKER_IDS.includes(identity.workerId)) return {routable: false, code: 'legacy_project_specific_worker', reason: 'project-specific one-shot worker identity is quarantined from generic routing'};
  if (identity.legacyIdentity) return {routable: false, code: 'legacy_identity_incomplete', reason: 'worker has no complete v2 installation/instance identity'};
  if (identity.protocolVersion !== COMMAND_CENTER_WORKER_PROTOCOL_VERSION) return {routable: false, code: 'protocol_version_mismatch', reason: `worker protocol ${identity.protocolVersion || 'missing'} does not match ${COMMAND_CENTER_WORKER_PROTOCOL_VERSION}`};
  if (!liveness.heartbeatFresh && !liveness.activatable) return {routable: false, code: 'stale_heartbeat', reason: liveness.livenessReason || 'heartbeat is stale or missing'};
  if (data.registryRoutable === false || data.routable === false) return {routable: false, code: 'registry_unroutable', reason: 'registry marks worker unroutable'};
  if (caps.includes('codex') && runtime.codexAuth === 'api_key') {
    const probe = workerApiKeyProbeAllowsCodex(data);
    if (!probe.ok) return {routable: false, code: 'api_key_capability_unavailable', reason: probe.reason};
  }
  return {routable: liveness.routable === true, code: liveness.routable ? 'routable' : 'not_routable', reason: liveness.routable ? 'fresh v2 worker' : liveness.livenessReason};
}

function compactWorkerCensus(worker = {}, activeLeases = 0, nowMs = Date.now()) {
  const identity = cleanWorkerIdentity(worker);
  const liveness = deriveWorkerLiveness(worker, nowMs);
  const routability = workerRoutabilityDiagnostic(worker, nowMs);
  return {
    workerId: identity.workerId,
    workerInstallationId: identity.workerInstallationId,
    workerInstanceId: identity.workerInstanceId,
    stableWorkerIdentity: identity.stableWorkerIdentity,
    location: safeText(worker.location, 80) || 'unknown',
    real: worker.simulated !== true,
    simulated: worker.simulated === true,
    status: worker.status === 'retired' || worker.retiredAtMs ? 'retired' : (liveness.heartbeatFresh ? 'active' : (liveness.activatable ? 'activatable' : 'stale')),
    routable: routability.routable,
    routabilityCode: routability.code,
    routabilityReason: routability.reason,
    heartbeatAgeMs: liveness.heartbeatAgeMs,
    heartbeatSeq: Number(worker.heartbeatSeq || 0) || 0,
    processStartAtMs: Number(worker.processStartAtMs || 0) || 0,
    lastHeartbeatAtMs: liveness.lastHeartbeatAtMs,
    lastAcceptedLeaseAtMs: Number(worker.lastAcceptedLeaseAtMs || 0) || 0,
    runnerVersion: identity.runnerVersion,
    protocolVersion: identity.protocolVersion,
    ownerKey: identity.ownerKey,
    capabilities: safeList(worker.capabilities, 120, 120),
    preparedWorkspaces: cleanPreparedWorkspaces(worker).map((workspace) => ({baseWorkspaceId: workspace.baseWorkspaceId, snapshotRef: workspace.snapshotRef, restoreStrategy: workspace.restoreStrategy, repository: repositoryFromBaseWorkspace(workspace)})),
    authenticationMode: safeText(safeObject(worker.runtime).codexAuth || safeObject(worker.runtime).authMode || safeObject(worker.runtime).openAiAuthMode, 80),
    availableImageIds: workerMachineImageState(worker).availableImageIds,
    materializedImageIds: workerMachineImageState(worker).materializedImageIds,
    cacheState: workerMachineImageState(worker).cacheState,
    maxConcurrentSessions: workerMachineImageState(worker).maxConcurrentSessions,
    activeSessionIds: workerMachineImageState(worker).activeSessionIds,
    sessionIsolationModes: workerMachineImageState(worker).sessionIsolationModes,
    canMaterializeImages: workerMachineImageState(worker).canMaterializeImages,
    sessionCapacity: {maxConcurrentSessions: workerMachineImageState(worker).maxConcurrentSessions, activeSessionCount: workerMachineImageState(worker).activeSessionIds.length, capacityRemaining: workerMachineImageState(worker).sessionCapacityRemaining},
    activeLeases,
    capacity: {activeLeases, concurrencyLimit: workerConcurrencyLimit(worker), capacityRemaining: Math.max(0, workerConcurrencyLimit(worker) - activeLeases)},
    duplicateOf: safeText(worker.duplicateOf, 120),
    supersededBy: safeText(worker.supersededBy, 120),
    legacyIdentity: identity.legacyIdentity,
    localHostExcludedByDefault: isLocalHostWorker(worker),
  };
}

function filterWorkerCensus(workers = [], args = {}, activeLeaseCounts = new Map(), nowMs = Date.now()) {
  let rows = workers.map((worker) => compactWorkerCensus(worker, activeLeaseCounts.get(worker.workerId) || 0, nowMs));
  if (args.active === true) rows = rows.filter((row) => row.status === 'active');
  if (args.stale === true) rows = rows.filter((row) => row.status === 'stale');
  if (args.retired === true) rows = rows.filter((row) => row.status === 'retired');
  if (args.routable === true) rows = rows.filter((row) => row.routable === true);
  if (args.routable === false) rows = rows.filter((row) => row.routable === false);
  const owner = safeText(args.owner || args.ownerKey, 80);
  if (owner) rows = rows.filter((row) => row.ownerKey === owner);
  const capability = safeText(args.capability, 120).toLowerCase();
  if (capability) rows = rows.filter((row) => row.capabilities.map((cap) => cap.toLowerCase()).includes(capability));
  const location = safeText(args.location, 80).toLowerCase();
  if (location) rows = rows.filter((row) => row.location.toLowerCase().includes(location));
  return rows;
}

function explainWorkerCandidate(worker = {}, requirements = [], activeLeaseCount = 0, options = {}) {
  const nowMs = Number(options.nowMs || 0) || Date.now();
  const leaseEligibility = isWorkerLeaseEligible(worker, requirements, options);
  const routability = workerRoutabilityDiagnostic(worker, nowMs);
  const capacity = workerConcurrencyLimit(worker);
  const capacityRemaining = Math.max(0, capacity - activeLeaseCount);
  const imagePolicy = workerImagePolicyDiagnostic(worker, options.sessionPolicy || options.imagePolicy || {}, options.machineImages || []);
  const sessionDiagnostic = workerSessionPolicyDiagnostic(worker, options.sessionPolicy || options.imagePolicy || {});
  const hasSessionPolicy = !!(safeText(safeObject(options.sessionPolicy || options.imagePolicy || {}).machineImageId, 120) || Array.isArray(safeObject(options.sessionPolicy || options.imagePolicy || {}).imageRequirements) || Array.isArray(safeObject(options.sessionPolicy || options.imagePolicy || {}).requiredImageCapabilities));
  let eligible = leaseEligibility.eligible === true && routability.routable === true && capacityRemaining > 0;
  let reason = eligible ? 'included' : (routability.routable ? (capacityRemaining <= 0 ? 'capacity exhausted' : leaseEligibility.reason) : routability.reason);
  let reasonCode = eligible ? 'included' : (routability.routable ? (capacityRemaining <= 0 ? 'capacity_exhausted' : (/local\/phone workers/.test(leaseEligibility.reason || '') ? 'local_host_excluded' : 'requirements_not_met')) : routability.code);
  if (eligible && !imagePolicy.ok) { eligible = false; reason = imagePolicy.reason; reasonCode = imagePolicy.code; }
  if (eligible && hasSessionPolicy && !sessionDiagnostic.ok) { eligible = false; reason = sessionDiagnostic.reason; reasonCode = sessionDiagnostic.code; }
  return {
    workerId: safeText(worker.workerId, 120),
    workerInstallationId: cleanWorkerIdentity(worker).workerInstallationId,
    workerInstanceId: cleanWorkerIdentity(worker).workerInstanceId,
    included: eligible,
    excluded: !eligible,
    reason,
    reasonCode,
    imagePolicy,
    sessionDiagnostic,
    leaseEligibility: leaseEligibility.reason,
    routability,
    activeLeases: activeLeaseCount,
    concurrencyLimit: capacity,
    capacityRemaining,
  };
}

function proofEligibleWorker(worker = {}, activeLeaseCount = 0, nowMs = Date.now()) {
  const explanation = explainWorkerCandidate(worker, ['codex', 'one-shot-worker'], activeLeaseCount, {nowMs});
  if (COMMAND_CENTER_PROOF_EXCLUDED_WORKER_IDS.includes(safeText(worker.workerId, 120))) return {...explanation, included: false, excluded: true, reason: 'excluded by proof policy', reasonCode: 'proof_excluded_worker'};
  if (worker.simulated === true) return {...explanation, included: false, excluded: true, reason: 'simulated workers excluded from proof', reasonCode: 'simulated_worker'};
  return explanation;
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
    availableImageIds: workerMachineImageState(data).availableImageIds,
    materializedImageIds: workerMachineImageState(data).materializedImageIds,
    machineImages: workerMachineImageState(data).machineImages,
    cacheState: workerMachineImageState(data).cacheState,
    maxConcurrentSessions: workerMachineImageState(data).maxConcurrentSessions,
    activeSessionIds: workerMachineImageState(data).activeSessionIds,
    sessionIsolationModes: workerMachineImageState(data).sessionIsolationModes,
    canMaterializeImages: workerMachineImageState(data).canMaterializeImages,
    sessionCapacity: {maxConcurrentSessions: workerMachineImageState(data).maxConcurrentSessions, activeSessionIds: workerMachineImageState(data).activeSessionIds, materializedImageIds: workerMachineImageState(data).materializedImageIds, availableImageIds: workerMachineImageState(data).availableImageIds, cacheState: workerMachineImageState(data).cacheState, canMaterializeImages: workerMachineImageState(data).canMaterializeImages, sessionIsolationModes: workerMachineImageState(data).sessionIsolationModes},
    repositoryAffinity: safeList(data.repositoryAffinity, 80, 240),
    preparedWorkspaces: cleanPreparedWorkspaces(data),
    workerInstallationId: cleanWorkerIdentity(data).workerInstallationId,
    workerInstanceId: cleanWorkerIdentity(data).workerInstanceId,
    stableWorkerIdentity: cleanWorkerIdentity(data).stableWorkerIdentity,
    runnerVersion: cleanWorkerIdentity(data).runnerVersion,
    protocolVersion: cleanWorkerIdentity(data).protocolVersion,
    identityStatus: cleanWorkerIdentity(data).identityStatus,
    legacyIdentity: cleanWorkerIdentity(data).legacyIdentity,
    heartbeatSeq: Number(data.heartbeatSeq || 0) || 0,
    processStartAtMs: Number(data.processStartAtMs || 0) || 0,
    lastAcceptedLeaseAtMs: Number(data.lastAcceptedLeaseAtMs || 0) || 0,
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

function dedupeWorkerRecords(workers = [], nowMs = Date.now()) {
  const byIdentity = new Map();
  for (const worker of workers.filter((item) => item && item.workerId)) {
    const identity = workerStableIdentity(worker) || worker.workerId;
    const liveness = deriveWorkerLiveness(worker, nowMs);
    const score = (worker.status === 'retired' || worker.retiredAtMs ? -100000 : 0)
      + (liveness.heartbeatFresh ? 10000 : 0)
      + (liveness.routable ? 1000 : 0)
      + (liveness.activatable ? 100 : 0)
      + Math.min(Number(worker.lastHeartbeatAtMs || 0) || 0, nowMs) / 10000000000000;
    const current = byIdentity.get(identity);
    if (!current || score > current.score) byIdentity.set(identity, {worker, score});
  }
  return Array.from(byIdentity.values()).map((entry) => entry.worker);
}

async function workerRecords(admin) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).limit(100).get();
  const byId = new Map(COMMAND_CENTER_DEFAULT_WORKERS.map((worker) => [worker.workerId, worker]));
  snap.forEach((doc) => byId.set(doc.id, cleanWorker({workerId: doc.id, ...(doc.data() || {})})));
  return dedupeWorkerRecords(Array.from(byId.values()).filter((worker) => worker.workerId));
}

function recordsVisibleToCaller(records, caller = null) {
  if (!caller) return records;
  const ownerKey = ownerKeyFromCaller(caller);
  return records.filter((record) => !safeText(record.ownerKey, 80) || record.ownerKey === ownerKey);
}

function queryOwnedCollection(admin, collectionName, caller) {
  return collection(admin, collectionName).where('ownerKey', '==', ownerKeyFromCaller(caller));
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
  if (isLocalHostWorker(worker) && options.allowLocalHost !== true) return {eligible: false, reason: 'local/phone workers are excluded from generic cloud routing'};
  if (worker.status === 'retired' || worker.retiredAtMs) return {eligible: false, reason: 'worker is retired'};
  const route = workerRoutabilityDiagnostic(worker, nowMs);
  if (!route.routable) return {eligible: false, reason: route.reason};
  if (worker.registryRoutable === false) return {eligible: false, reason: 'worker is not routable'};
  const missing = reqs.filter((req) => !caps.has(req));
  if (missing.length) return {eligible: false, reason: `missing capabilities: ${missing.join(', ')}`};
  if (reqs.includes('codex') || caps.has('codex')) {
    const probe = workerApiKeyProbeAllowsCodex(worker);
    if (!probe.ok) return {eligible: false, reason: `codex api-key capability unavailable: ${probe.reason}`};
  }
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

function workerConcurrencyLimit(worker = {}) {
  const limits = safeObject(worker.limits);
  const raw = Number(limits.concurrentJobs || limits.maxConcurrentJobs || limits.concurrentActivations || limits.maxConcurrentActivations || 1) || 1;
  return Math.max(1, Math.min(raw, 100));
}

function selectWorkerCandidates(workers, requirements, options = {}) {
  const reqs = safeList(requirements, 40, 120).map((req) => req.toLowerCase());
  return (Array.isArray(workers) ? workers : []).map((worker) => {
    const eligibility = isWorkerLeaseEligible(worker, reqs, options);
    let eligible = eligibility.eligible === true;
    let reason = eligibility.reason || '';
    let reasonCode = eligible ? 'eligible' : (/local\/phone workers/.test(reason) ? 'local_host_excluded' : 'requirements_not_met');
    const sessionPolicy = options.sessionPolicy || options.imagePolicy || {};
    const imagePolicy = workerImagePolicyDiagnostic(worker, sessionPolicy, options.machineImages || []);
    const sessionDiagnostic = workerSessionPolicyDiagnostic(worker, sessionPolicy);
    if (eligible && !imagePolicy.ok) { eligible = false; reason = imagePolicy.reason; reasonCode = imagePolicy.code; }
    if (eligible && (safeObject(sessionPolicy).machineImageId || safeObject(sessionPolicy).imageRequirements || safeObject(sessionPolicy).requiredImageCapabilities) && !sessionDiagnostic.ok) { eligible = false; reason = sessionDiagnostic.reason; reasonCode = sessionDiagnostic.code; }
    return {
      worker,
      workerId: worker && worker.workerId || '',
      eligible,
      reason,
      reasonCode,
      imagePolicy,
      sessionDiagnostic,
      concurrencyLimit: workerConcurrencyLimit(worker),
    };
  });
}

function selectWorker(workers, requirements, options = {}) {
  const reqs = safeList(requirements, 40, 120).map((req) => req.toLowerCase());
  const compatible = selectWorkerCandidates(workers, reqs, options)
    .filter((candidate) => candidate.eligible)
    .sort((a, b) => workerRoutingPriority(a.worker) - workerRoutingPriority(b.worker))
    .map((candidate) => candidate.worker);
  const selected = compatible[0] || null;
  if (selected) return selected;
  const err = new Error(reqs.length ? `No live real Command Center worker satisfies requirements: ${reqs.join(', ')}` : 'No live real Command Center worker is currently routable.');
  err.status = 409;
  err.code = 'NO_REAL_WORKER_AVAILABLE';
  err.requirements = reqs;
  err.workerDiagnostics = selectWorkerCandidates(workers, reqs, options).map((candidate) => ({workerId: candidate.workerId, eligible: candidate.eligible, reason: candidate.reason}));
  throw err;
}

async function activeLeaseCountsByWorker(admin) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).where('status', '==', 'active').limit(500).get();
  const counts = new Map();
  snap.forEach((doc) => {
    const lease = doc.data() || {};
    const workerId = safeText(lease.workerId, 120);
    if (!workerId) return;
    const expiresAtMs = Number(lease.expiresAtMs || 0) || 0;
    if (expiresAtMs > 0 && expiresAtMs <= Date.now()) return;
    counts.set(workerId, (counts.get(workerId) || 0) + 1);
  });
  return counts;
}

async function selectWorkerForJob(admin, workers, requirements, options = {}) {
  const reqs = safeList(requirements, 40, 120).map((req) => req.toLowerCase());
  const counts = await activeLeaseCountsByWorker(admin);
  const candidates = selectWorkerCandidates(workers, reqs, options).map((candidate, index) => {
    const activeLeases = counts.get(candidate.workerId) || 0;
    const capacityRemaining = candidate.concurrencyLimit - activeLeases;
    return {...candidate, index, activeLeases, capacityRemaining, loadRatio: activeLeases / Math.max(1, candidate.concurrencyLimit)};
  });
  const compatible = candidates
    .filter((candidate) => candidate.eligible && candidate.capacityRemaining > 0)
    .sort((a, b) => a.loadRatio - b.loadRatio || a.activeLeases - b.activeLeases || workerRoutingPriority(a.worker) - workerRoutingPriority(b.worker) || a.index - b.index);
  const selected = compatible[0] || null;
  if (selected) {
    return {
      worker: selected.worker,
      eligibleWorkerIds: candidates.filter((candidate) => candidate.eligible).map((candidate) => candidate.workerId),
      selectedWorkerLoad: {workerId: selected.workerId, activeLeases: selected.activeLeases, concurrencyLimit: selected.concurrencyLimit, capacityRemaining: selected.capacityRemaining},
      workerDiagnostics: candidates.map((candidate) => ({workerId: candidate.workerId, eligible: candidate.eligible, reason: candidate.reason, activeLeases: candidate.activeLeases, concurrencyLimit: candidate.concurrencyLimit, capacityRemaining: candidate.capacityRemaining})),
    };
  }
  const err = new Error(reqs.length ? `No compatible Command Center worker currently has free capacity for requirements: ${reqs.join(', ')}` : 'No live real Command Center worker currently has free capacity.');
  err.status = 409;
  err.code = 'NO_REAL_WORKER_AVAILABLE';
  err.requirements = reqs;
  err.workerDiagnostics = candidates.map((candidate) => ({workerId: candidate.workerId, eligible: candidate.eligible, reason: candidate.reason, activeLeases: candidate.activeLeases, concurrencyLimit: candidate.concurrencyLimit, capacityRemaining: candidate.capacityRemaining}));
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

function normalizeRenderRef(value, fieldName = 'ref') {
  const ref = safeText(value, 1200);
  if (!ref) {
    const err = new Error(fieldName + ' is required.');
    err.status = 400;
    err.failureKind = 'input_validation';
    throw err;
  }
  if (!/^(drive|bucket|gs):\/\//i.test(ref)) {
    const err = new Error(fieldName + ' must be a drive://, bucket://, or gs:// ref.');
    err.status = 400;
    err.failureKind = 'input_validation';
    throw err;
  }
  return ref;
}

function renderInputError(message, status = 400, failureKind = 'input_validation') {
  const err = new Error(message);
  err.status = status;
  err.failureKind = failureKind;
  return err;
}

function cleanUploadFileName(value, fallback) {
  const clean = safeText(value, 240).replace(/\\/g, '/').split('/').pop().replace(/[^A-Za-z0-9_.-]+/g, '-').replace(/^-+|-+$/g, '');
  return clean || fallback;
}

function isFileLike(value) {
  return value && typeof value === 'object' && typeof value.arrayBuffer === 'function' && typeof value.name === 'string';
}

async function bytesFromFileLike(value, role) {
  if (!isFileLike(value)) throw renderInputError(role + ' must be an uploaded MCP file, not a local path or JSON object.');
  const arrayBuffer = await value.arrayBuffer();
  return Buffer.from(arrayBuffer);
}

function validateGlbBytes(bytes, label) {
  if (!Buffer.isBuffer(bytes) || bytes.length < 12) throw renderInputError(label + ' is too small to be a GLB file.');
  if (bytes.length > COMMAND_CENTER_RENDER_MAX_GLB_BYTES) throw renderInputError(label + ' exceeds max GLB size ' + COMMAND_CENTER_RENDER_MAX_GLB_BYTES + ' bytes.', 413, 'input_validation');
  if (bytes.slice(0, 4).toString('ascii') !== 'glTF') throw renderInputError(label + ' is not a GLB: missing glTF magic.');
  const version = bytes.readUInt32LE(4);
  const declaredLength = bytes.readUInt32LE(8);
  if (version !== 2) throw renderInputError(label + ' must be GLB version 2.');
  if (declaredLength > bytes.length) throw renderInputError(label + ' declares more bytes than were uploaded.');
}

function validateScriptBytes(bytes, label) {
  if (!Buffer.isBuffer(bytes) || bytes.length === 0) throw renderInputError(label + ' is empty.');
  if (bytes.length > COMMAND_CENTER_RENDER_MAX_SCRIPT_BYTES) throw renderInputError(label + ' exceeds max script size ' + COMMAND_CENTER_RENDER_MAX_SCRIPT_BYTES + ' bytes.', 413, 'input_validation');
  if (bytes.includes(0)) throw renderInputError(label + ' must be a text Python script, not binary data.');
}

function renderStorage() {
  return new Storage();
}

async function stageRenderUpload({caller, renderId, role, fileName, bytes, contentType}) {
  if (!COMMAND_CENTER_RENDER_BUCKET) throw renderInputError('COMMAND_CENTER_RENDER_BUCKET is not configured for uploaded render files.', 503, 'transport');
  const hash = sha256Bytes(bytes);
  const safeRole = role === 'glb' ? 'glb' : 'script';
  const safeFile = cleanUploadFileName(fileName, safeRole === 'glb' ? 'input.glb' : 'render.py');
  const objectName = `temp/render-inputs/${ownerKeyFromCaller(caller)}/${safeText(renderId, 180) || 'render'}/${safeRole}-${hash}-${safeFile}`;
  await renderStorage().bucket(COMMAND_CENTER_RENDER_BUCKET).file(objectName).save(bytes, {
    resumable: false,
    metadata: {
      contentType: contentType || (safeRole === 'glb' ? 'model/gltf-binary' : 'text/x-python'),
      metadata: {sha256: hash, role: safeRole, renderer: COMMAND_CENTER_RENDER_TOOL_VERSION},
    },
  });
  return {ref: `gs://${COMMAND_CENTER_RENDER_BUCKET}/${objectName}`, sha256: hash, byteCount: bytes.length, fileName: safeFile, materializedFrom: safeRole + 'File'};
}

function hasInlineScript(args) {
  return safeText(args.scriptText || args.inlineScript || args.script, COMMAND_CENTER_RENDER_MAX_SCRIPT_BYTES + 1).length > 0;
}

function renderSourceCount(...values) {
  return values.filter(Boolean).length;
}

function normalizeRenderSettings(value = {}) {
  const src = safeObject(value);
  const settings = {
    width: Math.max(64, Math.min(Number(src.width || 1280) || 1280, 4096)),
    height: Math.max(64, Math.min(Number(src.height || 960) || 960, 4096)),
    camera: safeText(src.camera, 120) || 'front_3q',
    outputName: safeText(src.outputName, 180) || 'render.png',
    samples: Math.max(1, Math.min(Number(src.samples || src.renderSamples || 64) || 64, 128)),
    fixedCameras: safeList(src.fixedCameras || ['front_3q'], 12, 120),
    diagnosticViews: safeList(src.diagnosticViews || ['front', 'side', 'top'], 12, 120),
  };
  return {
    ...settings,
    action: safeText(src.action, 120),
    expectedAction: safeText(src.expectedAction, 120),
    authoredKeys: safeNumberList(src.authoredKeys, 160),
    evidenceFrames: safeNumberList(src.evidenceFrames, 160),
    gifFrames: safeNumberList(src.gifFrames, 160),
    gifTimingMs: safeNumberList(src.gifTimingMs, 160),
    allowRepeatedGifFrames: src.allowRepeatedGifFrames === true,
    includeBlend: src.includeBlend === false ? false : true,
    includeDiagnostics: src.includeDiagnostics === false ? false : true,
    renderOptions: safeObject(src.renderOptions),
  };
}

function stableJson(value) {
  if (Array.isArray(value)) return '[' + value.map(stableJson).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map((key) => JSON.stringify(key) + ':' + stableJson(value[key])).join(',') + '}';
  return JSON.stringify(value);
}

function renderBoolOption(value, fallback = true) {
  if (value === false || value === 'false' || value === 0 || value === '0') return false;
  if (value === true || value === 'true' || value === 1 || value === '1') return true;
  return fallback;
}

function renderBundleOptionsFrom(settings = {}, contract = {}) {
  const srcSettings = safeObject(settings);
  const srcContract = safeObject(contract);
  return {
    includeBlend: renderBoolOption(srcSettings.includeBlend ?? srcContract.includeBlend, true),
    includeDiagnostics: renderBoolOption(srcSettings.includeDiagnostics ?? srcContract.includeDiagnostics, true),
  };
}

function renderRequiredBundleKindsForOptions(options = {}) {
  const resolved = renderBundleOptionsFrom(options, options);
  const requireBundleKinds = COMMAND_CENTER_RENDER_REQUIRED_BUNDLE_KINDS.filter((kind) => resolved.includeDiagnostics || kind !== 'diagnostic_view_renders');
  if (resolved.includeBlend) requireBundleKinds.push('three_d_artifact');
  return requireBundleKinds;
}

function cleanRenderContract(value = {}) {
  const src = safeObject(value);
  const options = renderBundleOptionsFrom(src, src);
  const requireBundleKinds = renderRequiredBundleKindsForOptions(options);
  return {
    contractVersion: safeText(src.contractVersion, 80) || 'glb-script-durable-3d-artifact-v1',
    atomicOperation: 'GLB + script + execution contract -> durable 3D artifact + visual evidence',
    requireBundleKinds,
    framesAreInsufficient: true,
    preserve3dTruth: true,
    includeBlend: options.includeBlend,
    includeDiagnostics: options.includeDiagnostics,
  };
}

function renderCacheLookupKey(args = {}) {
  return fullHash(stableJson({
    toolVersion: COMMAND_CENTER_RENDER_TOOL_VERSION,
    glbRef: normalizeRenderRef(args.glbRef, 'glbRef'),
    scriptRef: normalizeRenderRef(args.scriptRef, 'scriptRef'),
    settings: normalizeRenderSettings(args.settings),
    executionContract: cleanRenderContract(args.executionContract),
  }));
}

function cleanRenderResult(serviceResult = {}, fallback = {}) {
  const result = safeObject(serviceResult);
  const bundle = safeObject(result.bundle);
  const refs = safeObject(result.refs || bundle.refs);
  const validation = safeObject(result.validation || result.validationManifest || bundle.validationManifest);
  const renderRefs = safeList(result.renderRefs || refs.renderedFrames, 60, 1200);
  const diagnosticRenderRefs = safeList(result.diagnosticRenderRefs || refs.diagnosticViewRenders, 60, 1200);
  const fixedCameraRenderRefs = safeList(result.fixedCameraRenderRefs || refs.fixedCameraRenders, 60, 1200);
  const threeDArtifactRefs = safeList(result.threeDArtifactRefs || refs.threeDArtifacts, 20, 1200);
  const nativeDataRefs = safeList(result.nativeDataRefs || refs.nativePoseAnimationData, 20, 1200);
  const artifactHashes = safeObject(result.artifactHashes || bundle.artifactHashes);
  const gifPlaybackContract = safeObject(result.gifPlaybackContract || validation.gifPlaybackContract || bundle.gifPlaybackContract);
  const timings = safeObject(result.timings || validation.timings || bundle.timings);
  const renderOptions = safeObject(result.renderOptions || validation.renderOptions || bundle.renderOptions);
  return {
    ok: result.ok === true,
    cacheHit: result.cacheHit === true,
    renderId: safeText(result.renderId || fallback.renderId, 180),
    cacheKey: safeText(result.cacheKey || fallback.cacheKey, 128),
    status: safeText(result.status, 80) || (result.ok === true ? 'completed' : 'failed'),
    renderRefs,
    contactSheetRef: safeText(result.contactSheetRef || refs.contactSheet, 1200),
    loopingGifRef: safeText(result.loopingGifRef || refs.loopingGif, 1200),
    threeDArtifactRefs,
    modifiedBlendRef: safeText(result.modifiedBlendRef || refs.modifiedBlend, 1200),
    animatedGlbRef: safeText(result.animatedGlbRef || refs.animatedGlb, 1200),
    nativeDataRefs,
    originalScriptRef: safeText(result.originalScriptRef || refs.originalScript, 1200),
    scriptInputHashesRef: safeText(result.scriptInputHashesRef || refs.scriptInputHashes, 1200),
    blenderVersionSettingsRef: safeText(result.blenderVersionSettingsRef || refs.blenderVersionSettings, 1200),
    stdoutRef: safeText(result.stdoutRef || refs.stdout, 1200),
    stderrRef: safeText(result.stderrRef || refs.stderr, 1200),
    fixedCameraRenderRefs,
    diagnosticRenderRefs,
    manifestRef: safeText(result.manifestRef || refs.validationManifest, 1200),
    validationManifestRef: safeText(result.validationManifestRef || refs.validationManifest, 1200),
    validation,
    artifactHashes,
    gifPlaybackContract,
    gifPlaybackContractRef: safeText(result.gifPlaybackContractRef || refs.gifPlaybackContract, 1200),
    timings,
    renderOptions,
    bundle,
    error: safeText(result.error || result.message, 2000),
    failureKind: safeText(result.failureKind, 80),
  };
}

async function invokeRenderService(payload) {
  const serviceUrl = COMMAND_CENTER_RENDER_DEFAULT_SERVICE_URL;
  if (!serviceUrl) {
    const err = new Error('COMMAND_CENTER_RENDER_SERVICE_URL is not configured for render.blender_glb.');
    err.status = 503;
    throw err;
  }
  const baseUrl = serviceUrl.replace(/\/+$/, '');
  const identityToken = await googleCloudIdentityToken(baseUrl);
  const response = await fetch(baseUrl + '/render/glb', {
    method: 'POST',
    headers: {authorization: `Bearer ${identityToken}`, 'content-type': 'application/json'},
    body: JSON.stringify(payload),
  });
  const text = await response.text();
  let json = {};
  try { json = text ? JSON.parse(text) : {}; } catch (_err) { json = {ok: false, error: text.slice(0, 2000)}; }
  if (!response.ok) {
    const failureKind = json.failureKind || (response.status === 401 || response.status === 403 ? 'render_service_invocation_auth_failed' : 'transport');
    const err = new Error(json.error || json.message || (failureKind + ': Blender render service failed: HTTP ' + response.status));
    err.status = response.status;
    err.failureKind = failureKind;
    err.serviceResult = {...json, failureKind};
    throw err;
  }
  return json;
}

function renderRecordId(cacheKey, caller = {}) {
  return 'render_' + hashText(ownerKeyFromCaller(caller) + ':' + cacheKey, 32);
}

function cleanRenderStagedInputs(inputs = []) {
  return (Array.isArray(inputs) ? inputs : []).slice(0, 12).map((input) => {
    const item = safeObject(input);
    return {
      ref: safeText(item.ref, 1200),
      sha256: safeText(item.sha256, 128),
      byteCount: Number(item.byteCount || 0) || 0,
      fileName: safeText(item.fileName, 240),
      materializedFrom: safeText(item.materializedFrom, 80),
      materializedBy: safeText(item.materializedBy, 120),
      sourceRef: safeText(item.sourceRef, 1200),
    };
  }).filter((item) => item.ref || item.sha256 || item.byteCount || item.fileName);
}

function cleanBucketInputObjects(objects = []) {
  return (Array.isArray(objects) ? objects : []).slice(0, 10).map((object) => ({
    objectId: safeText(object.objectId, 180),
    bucketId: safeText(object.bucketId, 120),
    kind: safeText(object.kind, 80),
    path: safeText(object.path, 500),
    body: safeText(object.body, COMMAND_CENTER_BUCKET_LAYOUT.storagePolicy.inlineBodyMaxChars),
    objectUri: safeText(object.objectUri, 1000),
    contentHash: safeText(object.contentHash, 128),
  }));
}

async function resolveRenderBucketInputs(admin, refs = [], caller = {}) {
  const objects = [];
  for (const ref of refs) {
    const text = safeText(ref, 1200);
    if (!text.toLowerCase().startsWith('bucket://')) continue;
    const raw = text.replace(/^bucket:\/\//i, '').replace(/^command-center\//i, '');
    const objectId = raw.split(/[?#]/)[0].split('/').filter(Boolean).pop() || raw;
    const found = await getBucketObject(admin, {objectId}, caller);
    if (!found.found) {
      const err = new Error('Bucket render input not found: ' + text);
      err.status = 404;
      throw err;
    }
    objects.push(found.object);
  }
  return cleanBucketInputObjects(objects);
}

async function resolveRenderSources(caller, args, renderId) {
  const glbHasFile = isFileLike(args.glbFile);
  const glbHasRef = safeText(args.glbRef, 1200).length > 0;
  if (renderSourceCount(glbHasFile, glbHasRef) !== 1) {
    throw renderInputError('Exactly one GLB source is required: provide glbFile or glbRef, but not both.');
  }

  const scriptHasFile = isFileLike(args.scriptFile);
  const scriptHasRef = safeText(args.scriptRef, 1200).length > 0;
  const scriptHasInline = hasInlineScript(args);
  if (renderSourceCount(scriptHasFile, scriptHasRef, scriptHasInline) !== 1) {
    throw renderInputError('Exactly one Blender script source is required: provide scriptFile, scriptRef, or scriptText.');
  }

  let glbRef = '';
  let scriptRef = '';
  const stagedInputs = [];
  if (glbHasFile) {
    const bytes = await bytesFromFileLike(args.glbFile, 'glbFile');
    validateGlbBytes(bytes, 'glbFile');
    const staged = await stageRenderUpload({caller, renderId, role: 'glb', fileName: args.glbFile.name, bytes, contentType: args.glbFile.type || 'model/gltf-binary'});
    glbRef = staged.ref;
    stagedInputs.push(staged);
  } else {
    glbRef = normalizeRenderRef(args.glbRef, 'glbRef');
  }

  if (scriptHasFile) {
    const bytes = await bytesFromFileLike(args.scriptFile, 'scriptFile');
    validateScriptBytes(bytes, 'scriptFile');
    const staged = await stageRenderUpload({caller, renderId, role: 'script', fileName: args.scriptFile.name, bytes, contentType: args.scriptFile.type || 'text/x-python'});
    scriptRef = staged.ref;
    stagedInputs.push(staged);
  } else if (scriptHasInline) {
    const text = safeText(args.scriptText || args.inlineScript || args.script, COMMAND_CENTER_RENDER_MAX_SCRIPT_BYTES + 1);
    const bytes = Buffer.from(text, 'utf8');
    validateScriptBytes(bytes, 'scriptText');
    const staged = await stageRenderUpload({caller, renderId, role: 'script', fileName: 'inline-render.py', bytes, contentType: 'text/x-python'});
    staged.materializedFrom = 'scriptText';
    scriptRef = staged.ref;
    stagedInputs.push(staged);
  } else {
    scriptRef = normalizeRenderRef(args.scriptRef, 'scriptRef');
  }

  return {glbRef, scriptRef, stagedInputs};
}

async function renderBlenderGlb(admin, extra, args = {}) {
  const caller = await callerFromExtra(admin, extra);
  const accessToken = bearerFromExtra(extra);
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'render.blender_glb', async () => {
    const settings = normalizeRenderSettings(args.settings);
    const executionContract = cleanRenderContract(args.executionContract);
    const requestedRenderId = safeText(args.renderId, 180) || `render_${hashText(ownerKeyFromCaller(caller) + ':' + safeText(args.idempotencyKey, 180), 32)}`;
    const resolvedSources = await resolveRenderSources(caller, args || {}, requestedRenderId);
    const glbRef = resolvedSources.glbRef;
    const scriptRef = resolvedSources.scriptRef;
    const stagedInputs = [...cleanRenderStagedInputs(args.stagedInputs), ...resolvedSources.stagedInputs];
    const requestCacheKey = renderCacheLookupKey({glbRef, scriptRef, stagedInputs, settings, executionContract});
    const renderId = safeText(args.renderId, 180) || renderRecordId(requestCacheKey, caller);
    const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.renderRequests).doc(renderId);
    const existingSnap = await ref.get();
    if (args.cache !== false && existingSnap.exists) {
      const existing = existingSnap.data() || {};
      assertOwnerAccess(existing, caller, 'Command Center render request');
      if (existing.status === 'completed' && existing.cacheKey) return {...cleanRenderResult(existing.result || {}, {renderId, cacheKey: existing.cacheKey}), cacheHit: true, persisted: true};
    }
    const bucketInputs = await resolveRenderBucketInputs(admin, [glbRef, scriptRef], caller);
    const startedAtMs = Date.now();
    await ref.set({renderId, cacheKey: requestCacheKey, requestCacheKey, status: 'running', glbRef, scriptRef, stagedInputs, settings, executionContract, toolVersion: COMMAND_CENTER_RENDER_TOOL_VERSION, ownerKey: ownerKeyFromCaller(caller), requestedBy: caller.actor, createdAtMs: existingSnap.exists ? (existingSnap.data() || {}).createdAtMs || startedAtMs : startedAtMs, updatedAtMs: startedAtMs}, {merge: true});
    try {
      const serviceResult = await invokeRenderService({renderId, requestCacheKey, glbRef, scriptRef, stagedInputs, settings, executionContract, toolVersion: COMMAND_CENTER_RENDER_TOOL_VERSION, cache: args.cache !== false, bucketInputs, googleOAuthAccessToken: accessToken});
      const result = cleanRenderResult(serviceResult, {renderId, cacheKey: serviceResult.cacheKey || requestCacheKey});
      const presentKinds = result.validation && Array.isArray(result.validation.presentBundleKinds) ? result.validation.presentBundleKinds : [];
      const effectiveRenderOptions = Object.prototype.hasOwnProperty.call(result.renderOptions || {}, 'includeBlend') || Object.prototype.hasOwnProperty.call(result.renderOptions || {}, 'includeDiagnostics') ? result.renderOptions : renderBundleOptionsFrom(settings, executionContract);
      const requiredKinds = renderRequiredBundleKindsForOptions(effectiveRenderOptions);
      const missingKinds = requiredKinds.filter((kind) => !presentKinds.includes(kind));
      const status = result.ok && missingKinds.length === 0 ? 'completed' : 'failed';
      const normalizedValidation = {...result.validation, ok: status === 'completed', missingBundleKinds: missingKinds, requiredBundleKinds: requiredKinds, renderOptions: effectiveRenderOptions};
      const finalResult = {...result, ok: status === 'completed', status, failureKind: status === 'completed' ? '' : (result.failureKind || normalizedValidation.failureKind || 'artifact_publication'), missingBundleKinds: missingKinds, validation: normalizedValidation, renderOptions: effectiveRenderOptions, stagedInputs};
      await ref.set({status, cacheKey: finalResult.cacheKey || requestCacheKey, result: finalResult, updatedAtMs: Date.now(), completedAtMs: status === 'completed' ? Date.now() : 0, failedAtMs: status === 'failed' ? Date.now() : 0}, {merge: true});
      return finalResult;
    } catch (err) {
      const failed = cleanRenderResult(err.serviceResult || {}, {renderId, cacheKey: requestCacheKey});
      const result = {...failed, ok: false, status: 'failed', failureKind: safeText(err.failureKind, 80) || 'transport', error: safeText(err.message || String(err), 2000), stagedInputs};
      await ref.set({status: 'failed', result, error: result.error, failureKind: result.failureKind, updatedAtMs: Date.now(), failedAtMs: Date.now()}, {merge: true});
      return result;
    }
  });
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

async function releaseActiveLeasesForJob(admin, jobId, workerId = '', status = 'released', reason = '') {
  const nowMs = Date.now();
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).where('jobId', '==', jobId).limit(20).get();
  const batch = admin.firestore().batch();
  let released = 0;
  snap.forEach((doc) => {
    const lease = doc.data() || {};
    if (lease.status !== 'active') return;
    if (workerId && lease.workerId !== workerId) return;
    released += 1;
    batch.set(doc.ref, {status, releasedAtMs: nowMs, updatedAtMs: nowMs, releaseReason: reason}, {merge: true});
  });
  if (released) await batch.commit();
  return released;
}

async function failJobTerminal(admin, job, actor, reason, data = {}) {
  const nowMs = Date.now();
  const jobId = cleanJobId(job.jobId);
  const projectId = cleanProjectId(job.projectId || 'project');
  const finalReport = safeText(data.finalReport, 8000) || `Command Center worker failed: ${safeText(reason, 4000)}`;
  const releasedLeases = await releaseActiveLeasesForJob(admin, jobId, job.selectedWorkerId || '', 'failed', reason);
  await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set({
    status: 'failed',
    updatedAtMs: nowMs,
    failedAtMs: nowMs,
    completedAtMs: nowMs,
    finalReport,
    failureReason: safeText(reason, 2000),
  }, {merge: true});
  const event = await appendEvent(admin, {
    type: 'job_failed',
    jobId,
    projectId,
    actor: safeText(actor, 160) || 'command_center',
    summary: finalReport,
    data: {...safeObject(data), releasedLeases},
  });
  await recordLog(admin, jobId, projectId, reason, {terminalFailure: true, releasedLeases, ...safeObject(data)});
  return {status: 'failed', event, releasedLeases};
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
  if (existing.exists) assertOwnerAccess(existingData, caller, 'Command Center bucket object');
  await ref.set({
    ...payload,
    createdAtMs: existingData.createdAtMs || payload.createdAtMs,
    createdBy: existingData.createdBy || payload.createdBy,
    ownerKey: existingData.ownerKey || payload.ownerKey,
  }, {merge: true});
  return {...payload, createdAtMs: existingData.createdAtMs || payload.createdAtMs, createdBy: existingData.createdBy || payload.createdBy, ownerKey: existingData.ownerKey || payload.ownerKey};
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

async function getBucketObject(admin, args, caller = null) {
  const objectId = safeText(args.objectId, 180);
  if (!objectId) {
    const err = new Error('objectId is required.');
    err.status = 400;
    throw err;
  }
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.bucketObjects).doc(objectId).get();
  if (!snap.exists) return {found: false, objectId};
  const object = snap.data() || {};
  if (caller) assertOwnerAccess(object, caller, 'Command Center bucket object');
  return {found: true, object};
}

async function listBucketObjects(admin, args = {}, caller = null) {
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
    if (caller && safeText(object.ownerKey, 80) && object.ownerKey !== ownerKeyFromCaller(caller)) return;
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


function cleanAppControlProfile(args = {}) {
  const profile = safeObject(args.profile && typeof args.profile === 'object' ? args.profile : args);
  const packageName = safeText(profile.packageName, 180);
  const versionName = safeText(profile.versionName, 120);
  const versionCode = safeText(profile.versionCode, 80);
  const profileId = safeText(profile.profileId, 260) || `${packageName}@${versionName}+${versionCode}`;
  if (!/^[a-zA-Z0-9_.]+$/.test(packageName)) {
    const err = new Error('app-control profile requires a valid packageName.');
    err.status = 400;
    throw err;
  }
  if (!versionName || !versionCode || !profileId.includes('@')) {
    const err = new Error('app-control profile requires versionName, versionCode, and profileId.');
    err.status = 400;
    throw err;
  }
  const workflows = safeObject(profile.workflows);
  if (!Object.keys(workflows).length) {
    const err = new Error('app-control profile requires at least one workflow.');
    err.status = 400;
    throw err;
  }
  return {
    ...profile,
    schemaVersion: Number(profile.schemaVersion || 1),
    profileId,
    packageName,
    versionName,
    versionCode,
    status: safeText(profile.status, 80) || 'candidate',
    cloudOwner: safeText(profile.cloudOwner, 120) || 'home-center-command-center',
    workflows,
    updatedAtMs: Date.now(),
  };
}

async function putAppControlProfile(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'app_control.put_profile', async () => {
    const profile = cleanAppControlProfile(args.profile || args);
    const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.appControlProfiles).doc(profile.profileId);
    const existing = await ref.get();
    const existingData = existing.exists ? existing.data() || {} : {};
    const payload = {...profile, createdAtMs: existingData.createdAtMs || Date.now(), createdBy: existingData.createdBy || caller.actor, updatedBy: caller.actor};
    await ref.set(payload, {merge: true});
    const bucketObject = await upsertBucketObject(admin, {
      objectId: appControlProfileObjectId(payload),
      bucketId: COMMAND_CENTER_DEFAULT_BUCKET_ID,
      kind: 'app_control.profile',
      path: appControlProfilePath(payload),
      title: `App control profile ${payload.profileId}`,
      summary: safeText((payload.source || {}).summary, 1200) || `Cloud app-control profile for ${payload.packageName}.`,
      body: JSON.stringify(payload, null, 2),
      projectId: 'home-center',
      repository: 'Valar05/home-center',
      sourceRefs: [`firestore://${COMMAND_CENTER_COLLECTIONS.appControlProfiles}/${payload.profileId}`],
      evidenceRefs: safeList([((payload.source || {}).evidencePath || '')], 10, 800),
      tags: ['app-control', payload.packageName, payload.status],
      source: 'command_center.app_control.put_profile',
      idempotencyKey: args.idempotencyKey,
    }, caller);
    return {profile: payload, bucketObject, collection: COMMAND_CENTER_COLLECTIONS.appControlProfiles};
  });
}

async function seedAppControlProfiles(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'app_control.seed_profiles', async () => {
    const seeded = [];
    for (const seed of APP_CONTROL_DEFAULT_SEEDS) {
      const result = await putAppControlProfile(admin, caller, {idempotencyKey: `${args.idempotencyKey}:${seed.profileId}`, profile: seed});
      seeded.push({profileId: result.profile.profileId, packageName: result.profile.packageName, versionName: result.profile.versionName, versionCode: result.profile.versionCode, bucketObjectId: result.bucketObject.objectId});
    }
    return {seeded, count: seeded.length, collection: COMMAND_CENTER_COLLECTIONS.appControlProfiles};
  });
}

async function getAppControlProfile(admin, args = {}) {
  const profileId = safeText(args.profileId, 260);
  if (!profileId) {
    const err = new Error('profileId is required.');
    err.status = 400;
    throw err;
  }
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.appControlProfiles).doc(profileId).get();
  return snap.exists ? {found: true, profile: snap.data()} : {found: false, profileId, collection: COMMAND_CENTER_COLLECTIONS.appControlProfiles};
}

async function listAppControlProfiles(admin, args = {}) {
  const packageName = safeText(args.packageName, 180);
  const workflow = safeText(args.workflow, 120);
  const status = safeText(args.status, 80);
  const limit = Math.max(1, Math.min(Number(args.limit) || 50, 100));
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.appControlProfiles).limit(250).get();
  const profiles = [];
  snap.forEach((doc) => {
    const profile = doc.data() || {};
    if (packageName && profile.packageName !== packageName) return;
    if (status && profile.status !== status) return;
    if (workflow && !(profile.workflows && profile.workflows[workflow])) return;
    profiles.push(profile);
  });
  profiles.sort((a, b) => Number(b.updatedAtMs || 0) - Number(a.updatedAtMs || 0));
  return {collection: COMMAND_CENTER_COLLECTIONS.appControlProfiles, profiles: profiles.slice(0, limit)};
}

async function recordAppControlRun(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'app_control.record_run', async () => {
    const profileId = safeText(args.profileId, 260);
    const workflow = safeText(args.workflow, 120);
    if (!profileId || !workflow) {
      const err = new Error('profileId and workflow are required for app-control run records.');
      err.status = 400;
      throw err;
    }
    const runId = safeText(args.runId, 180) || `app_run_${Date.now()}_${randomUUID().slice(0, 8)}`;
    const payload = {
      runId,
      profileId,
      workflow,
      packageName: safeText(args.packageName, 180),
      deviceAlias: safeText(args.deviceAlias, 120),
      status: safeText(args.status, 80) || 'observed',
      elapsedMs: Number(args.elapsedMs || 0),
      uiActionCount: Number(args.uiActionCount || 0),
      frameLane: safeObject(args.frameLane),
      summary: safeText(args.summary, 2000),
      learnedFixes: safeList(args.learnedFixes, 20, 1000),
      evidenceRefs: safeList(args.evidenceRefs, 40, 800),
      createdBy: caller.actor,
      createdAtMs: Date.now(),
    };
    await collection(admin, COMMAND_CENTER_COLLECTIONS.appControlRuns).doc(runId).set(payload, {merge: true});
    const bucketObject = await upsertBucketObject(admin, {
      objectId: `app_control_run_${hashText(runId, 32)}`,
      bucketId: COMMAND_CENTER_DEFAULT_BUCKET_ID,
      kind: 'app_control.run',
      path: `app-control/runs/${profileId}/${runId}.json`,
      title: `App control run ${workflow} ${profileId}`,
      summary: payload.summary || payload.status,
      body: JSON.stringify(payload, null, 2),
      projectId: 'home-center',
      repository: 'Valar05/home-center',
      sourceRefs: [`firestore://${COMMAND_CENTER_COLLECTIONS.appControlRuns}/${runId}`],
      evidenceRefs: payload.evidenceRefs,
      tags: ['app-control', 'run', payload.status, workflow],
      source: 'command_center.app_control.record_run',
      idempotencyKey: args.idempotencyKey,
    }, caller);
    return {run: payload, bucketObject, collection: COMMAND_CENTER_COLLECTIONS.appControlRuns};
  });
}


function cleanBrowserIntent(value) {
  return safeText(value, 2000);
}

function cleanBrowserSurface(value = {}) {
  const surface = safeObject(value);
  return {
    runtime: safeText(surface.runtime, 80) || 'playwright',
    browser: safeText(surface.browser, 80) || 'chromium',
    mode: safeText(surface.mode, 80) || 'desktop',
    userAgentMode: safeText(surface.userAgentMode, 80) || 'desktop',
    viewport: safeObject(surface.viewport),
    workerId: safeText(surface.workerId, 120),
    androidFallback: safeObject(surface.androidFallback),
  };
}


function cleanBrowserPlaybook(value = {}) {
  const playbook = safeObject(value);
  return {
    taskKey: safeText(playbook.taskKey || playbook.task, 160),
    origin: safeText(playbook.origin, 300),
    startUrl: safeText(playbook.startUrl, 1000),
    pageSignature: safeObject(playbook.pageSignature),
    actions: Array.isArray(playbook.actions) ? playbook.actions.slice(0, 80).map(safeObject) : [],
    successAssertions: Array.isArray(playbook.successAssertions) ? playbook.successAssertions.slice(0, 40).map(safeObject) : [],
    safetyGates: safeList(playbook.safetyGates, 40, 120),
    selectorPolicy: safeText(playbook.selectorPolicy, 180) || 'html_id_data_testid_aria_role_label_first_no_pixel_coordinates',
    learnedBy: safeText(playbook.learnedBy, 120),
    shareScope: safeText(playbook.shareScope, 80) || 'household',
    replayAudience: safeText(playbook.replayAudience, 120),
    householdLearningContract: safeText(playbook.householdLearningContract, 500) || 'First successful household use can become second-use automation for another household member after verified promotion.',
  };
}

function hasCoordinateOnlyPlaybook(playbook = {}) {
  const actions = Array.isArray(playbook.actions) ? playbook.actions : [];
  if (!actions.length) return false;
  return actions.every((action) => Array.isArray(action.coordinates) || Array.isArray(action.bounds) || action.selectorPolicy === 'pixel_coordinates');
}

function browserBucketObjectId(prefix, id) {
  return `${prefix}_${hashText(id, 32)}`;
}

async function createBrowserSession(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'browser_sessions.create', async () => {
    const sessionId = safeText(args.sessionId, 180) || `browser_session_${Date.now()}_${randomUUID().slice(0, 8)}`;
    const payload = {
      sessionId,
      status: 'created',
      intent: cleanBrowserIntent(args.intent),
      startUrl: safeText(args.startUrl, 1000) || 'https://www.google.com/',
      surface: cleanBrowserSurface(args.surface),
      accessibilityMode: safeText(args.accessibilityMode, 120) || 'web_hands',
      safetyMode: safeText(args.safetyMode, 120) || 'human_gated',
      learningPolicy: safeText(args.learningPolicy, 120) || 'record_observed_promote_later',
      createdBy: caller.actor,
      updatedBy: caller.actor,
      createdAtMs: Date.now(),
      updatedAtMs: Date.now(),
    };
    await collection(admin, COMMAND_CENTER_COLLECTIONS.browserSessions).doc(sessionId).set(payload, {merge: true});
    const bucketObject = await upsertBucketObject(admin, {
      objectId: browserBucketObjectId('browser_session', sessionId),
      bucketId: COMMAND_CENTER_DEFAULT_BUCKET_ID,
      kind: 'browser.session',
      path: `browser/sessions/${sessionId}.json`,
      title: `Browser session ${sessionId}`,
      summary: payload.intent || payload.startUrl,
      body: JSON.stringify(payload, null, 2),
      projectId: 'home-center',
      repository: 'Valar05/home-center',
      sourceRefs: [`firestore://${COMMAND_CENTER_COLLECTIONS.browserSessions}/${sessionId}`],
      tags: ['browser-hands', 'playwright', payload.surface.browser, payload.surface.mode],
      source: 'command_center.browser_sessions.create',
      idempotencyKey: args.idempotencyKey,
    }, caller);
    return {session: payload, bucketObject, collection: COMMAND_CENTER_COLLECTIONS.browserSessions};
  });
}

async function observeBrowserSession(admin, args = {}) {
  const sessionId = safeText(args.sessionId, 180);
  if (!sessionId) {
    const err = new Error('sessionId is required.');
    err.status = 400;
    throw err;
  }
  const session = await collection(admin, COMMAND_CENTER_COLLECTIONS.browserSessions).doc(sessionId).get();
  const episodeLimit = Math.max(1, Math.min(Number(args.limit) || 10, 50));
  const episodeSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.browserEpisodes).where('sessionId', '==', sessionId).limit(100).get();
  const episodes = [];
  episodeSnap.forEach((doc) => episodes.push(doc.data() || {}));
  episodes.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  return {found: session.exists, session: session.exists ? session.data() : null, episodes: episodes.slice(0, episodeLimit)};
}

async function requestBrowserAction(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'browser_sessions.act', async () => {
    const sessionId = safeText(args.sessionId, 180);
    const action = safeText(args.action, 80);
    if (!sessionId || !action) {
      const err = new Error('sessionId and action are required.');
      err.status = 400;
      throw err;
    }
    const actionId = safeText(args.actionId, 180) || `browser_action_${Date.now()}_${randomUUID().slice(0, 8)}`;
    const blockedActions = new Set(['purchase', 'submit_payment', 'place_order', 'solve_captcha', 'bypass_verification', 'change_password', 'delete_account']);
    const status = blockedActions.has(action) ? 'blocked_human_required' : 'requested';
    const payload = {
      actionId,
      sessionId,
      action,
      target: safeObject(args.target),
      valueRedacted: args.value ? '[redacted]' : '',
      status,
      reason: status === 'blocked_human_required' ? 'Sensitive or anti-bot gated browser action requires human control.' : safeText(args.reason, 1000),
      createdBy: caller.actor,
      createdAtMs: Date.now(),
    };
    await appendEvent(admin, {type: 'browser_action_' + status, jobId: safeText(args.jobId, 140), projectId: 'home-center', actor: caller.actor, summary: `${action}: ${status}`, data: payload});
    return {action: payload};
  });
}

function cleanBrowserEpisode(args = {}, caller = {}) {
  const sessionId = safeText(args.sessionId, 180);
  if (!sessionId) {
    const err = new Error('sessionId is required.');
    err.status = 400;
    throw err;
  }
  const episodeId = safeText(args.episodeId, 180) || `browser_episode_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const origin = safeText(args.origin, 300);
  return {
    episodeId,
    sessionId,
    intent: cleanBrowserIntent(args.intent),
    origin,
    url: safeText(args.url, 1000),
    title: safeText(args.title, 500),
    surface: cleanBrowserSurface(args.surface),
    outcome: safeText(args.outcome, 80) || 'observed',
    accessibilitySummary: safeText(args.accessibilitySummary, 4000),
    visibleTextSummary: safeText(args.visibleTextSummary, 4000),
    focusedElement: safeObject(args.focusedElement),
    actions: Array.isArray(args.actions) ? args.actions.slice(0, 80).map(safeObject) : [],
    blockers: safeList(args.blockers, 40, 1000),
    redactionReport: safeObject(args.redactionReport),
    discoveryCandidates: Array.isArray(args.discoveryCandidates) ? args.discoveryCandidates.slice(0, 40).map(safeObject) : [],
    evidenceRefs: safeList(args.evidenceRefs, 80, 800),
    createdBy: caller.actor || 'browser_worker',
    createdAtMs: Date.now(),
  };
}

async function recordBrowserEpisode(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'browser_sessions.record_episode', async () => {
    const episode = cleanBrowserEpisode(args, caller);
    await collection(admin, COMMAND_CENTER_COLLECTIONS.browserEpisodes).doc(episode.episodeId).set(episode, {merge: true});
    const discoveries = [];
    for (const candidate of episode.discoveryCandidates) {
      const claim = safeText(candidate.claim, 1200);
      if (!claim) continue;
      const discoveryId = safeText(candidate.discoveryId, 180) || `browser_discovery_${hashText(`${episode.origin}:${claim}`, 32)}`;
      const playbook = cleanBrowserPlaybook(candidate.playbook || {});
      const discovery = {
        discoveryId,
        state: 'candidate',
        origin: episode.origin,
        task: safeText(candidate.task || candidate.taskKey || playbook.taskKey, 160),
        taskKey: safeText(candidate.taskKey || candidate.task || playbook.taskKey, 160),
        claim,
        playbook,
        evidenceEpisodeIds: [episode.episodeId],
        safetyClass: safeText(candidate.safetyClass, 80) || 'normal',
        shareScope: playbook.shareScope || safeText(candidate.shareScope, 80) || 'household',
        learnedBy: playbook.learnedBy || safeText(candidate.learnedBy, 120),
        replayAudience: playbook.replayAudience || safeText(candidate.replayAudience, 120),
        createdBy: caller.actor,
        updatedBy: caller.actor,
        createdAtMs: Date.now(),
        updatedAtMs: Date.now(),
      };
      await collection(admin, COMMAND_CENTER_COLLECTIONS.browserDiscoveries).doc(discoveryId).set(discovery, {merge: true});
      discoveries.push(discovery);
    }
    const bucketObject = await upsertBucketObject(admin, {
      objectId: browserBucketObjectId('browser_episode', episode.episodeId),
      bucketId: COMMAND_CENTER_DEFAULT_BUCKET_ID,
      kind: 'browser.episode',
      path: `browser/episodes/${episode.origin || 'unknown-origin'}/${episode.episodeId}.json`,
      title: `Browser episode ${episode.episodeId}`,
      summary: episode.intent || episode.title || episode.url,
      body: JSON.stringify(episode, null, 2),
      projectId: 'home-center',
      repository: 'Valar05/home-center',
      sourceRefs: [`firestore://${COMMAND_CENTER_COLLECTIONS.browserEpisodes}/${episode.episodeId}`],
      evidenceRefs: episode.evidenceRefs,
      tags: ['browser-hands', 'episode', episode.outcome, episode.surface.runtime],
      source: 'command_center.browser_sessions.record_episode',
      idempotencyKey: args.idempotencyKey,
    }, caller);
    return {episode, discoveries, bucketObject, collection: COMMAND_CENTER_COLLECTIONS.browserEpisodes};
  });
}

async function listBrowserDiscoveries(admin, args = {}) {
  const origin = safeText(args.origin, 300);
  const state = safeText(args.state, 80);
  const task = safeText(args.task, 160);
  const limit = Math.max(1, Math.min(Number(args.limit) || 50, 100));
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.browserDiscoveries).limit(250).get();
  const discoveries = [];
  snap.forEach((doc) => {
    const discovery = doc.data() || {};
    if (origin && discovery.origin !== origin) return;
    if (state && discovery.state !== state) return;
    if (task && discovery.task !== task) return;
    discoveries.push(discovery);
  });
  discoveries.sort((a, b) => Number(b.updatedAtMs || 0) - Number(a.updatedAtMs || 0));
  return {collection: COMMAND_CENTER_COLLECTIONS.browserDiscoveries, discoveries: discoveries.slice(0, limit)};
}

async function promoteBrowserDiscovery(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'browser_discoveries.promote', async () => {
    const discoveryId = safeText(args.discoveryId, 180);
    if (!discoveryId) {
      const err = new Error('discoveryId is required.');
      err.status = 400;
      throw err;
    }
    const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.browserDiscoveries).doc(discoveryId);
    const snap = await ref.get();
    if (!snap.exists) {
      const err = new Error('Browser discovery not found.');
      err.status = 404;
      throw err;
    }
    const discoveryData = snap.data() || {};
    const structuredPlaybook = cleanBrowserPlaybook({...safeObject(discoveryData.playbook), ...safeObject(args.playbook || {})});
    if (hasCoordinateOnlyPlaybook(structuredPlaybook)) {
      const err = new Error('Coordinate-only browser discoveries cannot be promoted to trusted playbooks. Use Playwright DOM/accessibility selectors.');
      err.status = 400;
      throw err;
    }
    const discovery = {...discoveryData, state: 'trusted', playbook: structuredPlaybook, promotedBy: caller.actor, updatedBy: caller.actor, updatedAtMs: Date.now(), promotionEvidenceRefs: safeList(args.evidenceRefs, 40, 800)};
    await ref.set(discovery, {merge: true});
    const playbookId = safeText(args.playbookId, 180) || `browser_playbook_${hashText(`${discovery.origin}:${discovery.taskKey || discovery.task || discovery.discoveryId}`, 32)}`;
    const playbook = {
      ...structuredPlaybook,
      playbookId,
      origin: structuredPlaybook.origin || discovery.origin || '',
      task: structuredPlaybook.taskKey || discovery.taskKey || discovery.task || '',
      taskKey: structuredPlaybook.taskKey || discovery.taskKey || discovery.task || '',
      state: 'trusted',
      discoveryIds: [discoveryId],
      guidance: safeText(args.guidance, 4000) || discovery.claim,
      learnedBy: structuredPlaybook.learnedBy || discovery.learnedBy || caller.actor,
      shareScope: structuredPlaybook.shareScope || discovery.shareScope || 'household',
      replayAudience: structuredPlaybook.replayAudience || discovery.replayAudience || '',
      updatedBy: caller.actor,
      updatedAtMs: Date.now(),
    };
    await collection(admin, COMMAND_CENTER_COLLECTIONS.browserPlaybooks).doc(playbookId).set(playbook, {merge: true});
    const bucketObject = await upsertBucketObject(admin, {
      objectId: browserBucketObjectId('browser_playbook', playbookId),
      bucketId: COMMAND_CENTER_DEFAULT_BUCKET_ID,
      kind: 'browser.playbook',
      path: `browser/playbooks/${playbook.origin || 'general'}/${playbookId}.json`,
      title: `Browser playbook ${playbook.origin || playbook.task || playbookId}`,
      summary: playbook.guidance,
      body: JSON.stringify(playbook, null, 2),
      projectId: 'home-center',
      repository: 'Valar05/home-center',
      sourceRefs: [`firestore://${COMMAND_CENTER_COLLECTIONS.browserPlaybooks}/${playbookId}`, `firestore://${COMMAND_CENTER_COLLECTIONS.browserDiscoveries}/${discoveryId}`],
      evidenceRefs: playbook.discoveryIds,
      tags: ['browser-hands', 'playbook', 'trusted'],
      source: 'command_center.browser_discoveries.promote',
      idempotencyKey: args.idempotencyKey,
    }, caller);
    return {discovery, playbook, bucketObject};
  });
}


async function lookupBrowserPlaybook(admin, args = {}) {
  const origin = safeText(args.origin, 300);
  const taskKey = safeText(args.taskKey || args.task, 160);
  const shareScope = safeText(args.shareScope, 80);
  const replayAudience = safeText(args.replayAudience, 120);
  const limit = Math.max(1, Math.min(Number(args.limit) || 10, 50));
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.browserPlaybooks).limit(250).get();
  const playbooks = [];
  snap.forEach((doc) => {
    const playbook = doc.data() || {};
    if (playbook.state && playbook.state !== 'trusted') return;
    if (origin && playbook.origin !== origin) return;
    if (taskKey && (playbook.taskKey || playbook.task) !== taskKey) return;
    if (shareScope && playbook.shareScope !== shareScope) return;
    if (replayAudience && playbook.replayAudience && playbook.replayAudience !== replayAudience) return;
    playbooks.push(playbook);
  });
  playbooks.sort((a, b) => Number(b.updatedAtMs || 0) - Number(a.updatedAtMs || 0));
  return {found: playbooks.length > 0, collection: COMMAND_CENTER_COLLECTIONS.browserPlaybooks, playbook: playbooks[0] || null, playbooks: playbooks.slice(0, limit)};
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
  }, {actor: 'command_center', ownerKey: safeText(checkpoint.ownerKey, 80) || ownerKeyFromActor('command_center')});
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

async function googleCloudIdentityToken(audience) {
  const encodedAudience = encodeURIComponent(safeText(audience, 1200));
  const response = await fetch(`http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity?audience=${encodedAudience}`, {headers: {'Metadata-Flavor': 'Google'}});
  const text = await response.text();
  if (!response.ok) throw new Error(`Metadata identity token request failed: ${response.status} ${text.slice(0, 200)}`);
  if (!text) throw new Error('Metadata identity token response was empty.');
  return text;
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

function artifactNamesAndKinds(artifacts = []) {
  return {
    names: new Set(artifacts.map((artifact) => safeText(artifact.name, 240)).filter(Boolean)),
    kinds: new Set(artifacts.map((artifact) => safeText(artifact.kind, 120)).filter(Boolean)),
  };
}

function jobRequestsVisualQa(job = {}) {
  const requirements = safeList(job.workerRequirements, 80, 120).map((item) => item.toLowerCase());
  const requiredArtifacts = safeList(job.requiredArtifacts, 80, 180).map((item) => item.toLowerCase());
  const titleObjective = String((job.title || '') + ' ' + (job.objective || '')).toLowerCase();
  return requirements.some((item) => ['browser-worker', 'playwright', 'cloud-visual-truth', 'visual-qa'].includes(item))
    || requiredArtifacts.some((item) => /visual|screenshot|browser.episode|episode/.test(item))
    || /visual qa|cloud visual|screenshot|final render/.test(titleObjective);
}

function shouldAcceptVisualQaCompletion({artifacts = []}) {
  const {names, kinds} = artifactNamesAndKinds(artifacts);
  const hasManifest = names.has('visual_qa_manifest.json') || kinds.has('visual_qa_manifest');
  const hasScreenshot = names.has('screenshot.png') || kinds.has('screenshot');
  const hasEpisode = names.has('browser_episode.json') || kinds.has('browser_episode');
  const screenshot = artifacts.find((artifact) => artifact.name === 'screenshot.png' || artifact.kind === 'screenshot') || {};
  const manifest = artifacts.find((artifact) => artifact.name === 'visual_qa_manifest.json' || artifact.kind === 'visual_qa_manifest') || {};
  if (!hasManifest) return {ok: false, reason: 'completed visual QA jobs require visual_qa_manifest.json'};
  if (!hasScreenshot) return {ok: false, reason: 'completed visual QA jobs require screenshot.png'};
  if (!hasEpisode) return {ok: false, reason: 'completed visual QA jobs require browser_episode.json'};
  if (!/^[a-f0-9]{64}$/i.test(safeText(screenshot.sha256, 128))) return {ok: false, reason: 'completed visual QA jobs require screenshot.png sha256'};
  const manifestMeta = safeObject(manifest.metadata);
  const screenshotMeta = safeObject(screenshot.metadata);
  if (safeText(manifestMeta.captureKind || screenshotMeta.captureKind, 120) !== 'command-center-cloud-screenshot') {
    return {ok: false, reason: 'completed visual QA jobs require command-center-cloud-screenshot captureKind metadata'};
  }
  return {ok: true, reason: 'completion has browser-worker visual QA evidence'};
}

function shouldAcceptWorkerCompletion({requestedStatus, events = [], artifacts = [], job = {}}) {
  if (requestedStatus === 'failed') return {ok: true, reason: 'failed completions are diagnostic terminal states'};
  if (jobRequestsVisualQa(job)) return shouldAcceptVisualQaCompletion({artifacts});
  const types = new Set(events.map((event) => event.type));
  if (!types.has('executor_started')) return {ok: false, reason: 'completed jobs require executor_started evidence'};
  if (!types.has('executor_finished')) return {ok: false, reason: 'completed jobs require executor_finished evidence'};
  const workspaceArtifact = artifacts.some((artifact) => artifact.origin === 'executor_workspace' || safeObject(artifact.metadata).origin === 'executor_workspace');
  if (!workspaceArtifact) return {ok: false, reason: 'completed jobs require at least one artifact from the executor workspace'};
  const artifactNames = new Set(artifacts.map((artifact) => safeText(artifact.name, 240)).filter(Boolean));
  if (artifactNames.has('noop-proof.txt')) return {ok: false, reason: 'completed repository jobs cannot be proven by noop-proof.txt'};
  const executionMode = cleanExecutionMode(job.executionMode);
  const requiredExecutionArtifacts = executionMode === 'one_shot'
    ? [...COMMAND_CENTER_REQUIRED_ARTIFACTS, 'acceptance.json', 'acceptance-matrix.json']
    : requiredArtifactsForExecutionMode(executionMode);
  const missing = requiredExecutionArtifacts.filter((name) => !artifactNames.has(name));
  if (missing.length) return {ok: false, reason: 'completed ' + executionMode + ' jobs require execution artifacts: ' + missing.join(', ')};
  if (executionMode === 'codex_smoke' && !types.has('executor_stdout') && !types.has('executor_stderr')) {
    return {ok: false, reason: 'completed codex_smoke jobs require streamed stdout or stderr evidence'};
  }
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
    const projectResolution = await resolveProject(admin, {...args, projectId});
    const project = projectResolution.project || {};
    if (project.ownerKey) assertOwnerAccess(project, caller, 'Command Center project');
    const execution = cleanOneShotExecution({
      ...args,
      baseWorkspace: args.baseWorkspace || project.baseWorkspace,
    });
    const repository = resolveJobRepository(args, project, execution.baseWorkspace);
    const jobId = `job_${randomUUID()}`;
    const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
    const sessionPolicy = cleanSessionPolicy(args);
    const machineImages = await machineImageRecords(admin, caller);
    let worker = null;
    let selection = null;
    let selectionFailure = null;
    try {
      selection = await selectWorkerForJob(admin, workers, args.workerRequirements, {sessionPolicy, machineImages});
      worker = selection.worker;
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
      repository,
      projectRepository: repositoryFromProject(project),
      ...execution,
      sessionPolicy,
      machineImageId: sessionPolicy.machineImageId,
      status: worker ? 'leased' : 'queued',
      selectedWorkerId: worker ? worker.workerId : '',
      eligibleWorkerIds: selection ? selection.eligibleWorkerIds : [],
      workerDiagnostics: selection ? selection.workerDiagnostics : (selectionFailure && selectionFailure.workerDiagnostics || []),
      selectedWorkerLoad: selection ? selection.selectedWorkerLoad : {},
      dispatchAttemptCount: worker ? 1 : 0,
      recoverable: true,
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
      const queuedEvent = await appendEvent(admin, {type: 'job_queued_no_worker', jobId, projectId, actor: 'command_center', summary: selectionFailure.message, data: {requirements: selectionFailure.requirements || job.workerRequirements, workerDiagnostics: job.workerDiagnostics}});
      await recordLog(admin, jobId, projectId, 'Command Center queued job because no real worker was currently eligible.', {workerRequirements: job.workerRequirements, diagnostic: selectionFailure.message, workerDiagnostics: job.workerDiagnostics});
      const checkpoint = await recordCheckpoint(admin, job);
      return {job, lease: null, activation: null, events: [createdEvent, queuedEvent], checkpoint};
    }
    const lease = {leaseId: `lease_${randomUUID()}`, jobId, projectId, workerId: worker.workerId, status: 'active', acquiredAtMs: nowMs, expiresAtMs: nowMs + 30 * 60 * 1000, heartbeatAtMs: nowMs};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).doc(lease.leaseId).set(lease);
    const leasedEvent = await appendEvent(admin, {type: 'job_leased', jobId, projectId, actor: 'command_center', summary: `Leased to ${worker.workerId}.`, data: {worker, eligibleWorkerIds: job.eligibleWorkerIds, selectedWorkerLoad: job.selectedWorkerLoad}});
    const activationResult = await requestJobActivation(admin, job, lease, worker);
    if (activationResult.activation && activationResult.accepted === false) job.status = 'failed';
    await recordLog(admin, jobId, projectId, 'Command Center created and leased one-shot job from prepared workspace contract.', {workerId: worker.workerId, executionMode: job.executionMode, baseWorkspace: job.baseWorkspace.baseWorkspaceId});
    const checkpoint = await recordCheckpoint(admin, job);
    return {job, lease, activation: activationResult.activation, events: [createdEvent, leasedEvent, ...activationResult.events], checkpoint};
  });
}

async function synthesizeJobHandoff(admin, jobId, caller = null) {
  const job = await getJob(admin, jobId, caller);
  const [checkpoint, events, logs, artifacts, bucketRows] = await Promise.all([
    getLatestCheckpoint(admin, jobId),
    listByJob(admin, COMMAND_CENTER_COLLECTIONS.events, jobId, 100),
    listByJob(admin, COMMAND_CENTER_COLLECTIONS.logs, jobId, 100),
    listByJob(admin, COMMAND_CENTER_COLLECTIONS.artifacts, jobId, 100),
    listBucketObjects(admin, {bucketId: COMMAND_CENTER_DEFAULT_BUCKET_ID, jobId, limit: 50}, caller),
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
  const unevaluatedCriteria = acceptanceMatrix.filter((item) => item.status === 'not_evaluated' || item.status === 'pending');
  const failedCriteria = acceptanceMatrix.filter((item) => item.status === 'failed');
  const usageSummary = safeObject(checkpoint && checkpoint.usageSummary);
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
      repository: job.repository || '',
      baseWorkspace: job.baseWorkspace || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE,
    },
    review: {
      recommendedNextAction: job.status === 'completed' ? 'Review completion evidence and authorize only policy-approved consequential mutations.' : 'Create a linked follow-up invocation after reviewing the failure evidence.',
      correctability: {
        preferredOperation: 'command_center.jobs.create_followup',
        sourceJobId: jobId,
        carryForwardEvidenceRefs: artifacts.map((artifact) => artifact.uri).filter(Boolean).slice(0, 40),
      },
      residualRisks: [
        ...(missingRequiredArtifacts.length ? ['Some required artifacts are missing.'] : []),
        ...(unevaluatedCriteria.length ? ['Some acceptance criteria are not explicitly evaluated.'] : []),
        ...(failedCriteria.length ? ['Some acceptance criteria failed.'] : []),
        ...(usageSummary.warnings || []),
      ],
      acceptanceReviewState: failedCriteria.length ? 'failed' : (unevaluatedCriteria.length ? 'review_incomplete' : 'evaluated'),
    },
    counters: {
      eventCount: events.length,
      logCount: logs.length,
      artifactCount: artifacts.length,
      bucketObjectCount: bucketRows.objects.length,
      executorEventCount: executorEvents.length,
      lastEventType: newestEvent ? newestEvent.type : '',
      lastHeartbeatAgeMs: heartbeatEvent ? nowMs - Number(heartbeatEvent.createdAtMs || nowMs) : null,
      terminal: isTerminalJobStatus(job.status),
      missingRequiredArtifacts,
      unevaluatedAcceptanceCriteria: unevaluatedCriteria.length,
      failedAcceptanceCriteria: failedCriteria.length,
    },
    usageSummary,
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
    const sourceHandoff = await synthesizeJobHandoff(admin, sourceJobId, caller);
    const sourceJob = sourceHandoff.job;
    const projectId = args.projectId ? cleanProjectId(args.projectId) : cleanProjectId(sourceJob.projectId);
    const projectResolution = await resolveProject(admin, {...args, projectId, repository: args.repository || sourceJob.repository});
    const project = projectResolution.project || {};
    if (project.ownerKey) assertOwnerAccess(project, caller, 'Command Center project');
    const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
    const sessionPolicy = cleanSessionPolicy(args.sessionPolicy ? args : {sessionPolicy: sourceJob.sessionPolicy || {}});
    const machineImages = await machineImageRecords(admin, caller);
    const workerRequirements = safeList(args.workerRequirements, 40, 120);
    const inheritedWorkerRequirements = safeList(sourceJob.workerRequirements, 40, 120);
    let worker = null;
    let selection = null;
    let selectionFailure = null;
    const effectiveWorkerRequirements = workerRequirements.length ? workerRequirements : inheritedWorkerRequirements;
    try {
      selection = await selectWorkerForJob(admin, workers, effectiveWorkerRequirements, {sessionPolicy, machineImages});
      worker = selection.worker;
    } catch (err) {
      if (!workerSelectionFailure(err)) throw err;
      selectionFailure = err;
    }
    const execution = cleanOneShotExecution({
      ...args,
      baseWorkspace: args.baseWorkspace || sourceJob.baseWorkspace || project.baseWorkspace,
      requiredArtifacts: args.requiredArtifacts || sourceJob.requiredArtifacts,
    });
    const repository = resolveJobRepository({...args, repository: args.repository || sourceJob.repository}, project, execution.baseWorkspace);
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
      workerRequirements: effectiveWorkerRequirements,
      budgetClass: safeText(args.budgetClass, 80) || 'small',
      mutationPolicy: cleanMutationPolicy(args.mutationPolicy || sourceJob.mutationPolicy),
      repository,
      projectRepository: repositoryFromProject(project),
      ...execution,
      sessionPolicy,
      machineImageId: sessionPolicy.machineImageId,
      sourceJobId,
      followupOf: {
        jobId: sourceJobId,
        status: sourceJob.status,
        title: sourceJob.title || '',
        handoffRef: `handoff://${sourceJobId}`,
      },
      sourceEvidenceRefs: sourceHandoff.review.correctability.carryForwardEvidenceRefs,
      status: worker ? 'leased' : 'queued',
      selectedWorkerId: worker ? worker.workerId : '',
      eligibleWorkerIds: selection ? selection.eligibleWorkerIds : [],
      workerDiagnostics: selection ? selection.workerDiagnostics : (selectionFailure && selectionFailure.workerDiagnostics || []),
      selectedWorkerLoad: selection ? selection.selectedWorkerLoad : {},
      dispatchAttemptCount: worker ? 1 : 0,
      recoverable: true,
      createdBy: caller.actor,
      ownerKey: ownerKeyFromCaller(caller),
      createdAtMs: nowMs,
      updatedAtMs: nowMs,
      simulatedWorker: worker ? worker.simulated === true : false,
      routingDiagnostic: selectionFailure ? selectionFailure.message : '',
    };
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set(job);
    const createdEvent = await appendEvent(admin, {type: 'job_created', jobId, projectId, actor: caller.actor, summary: job.title, data: {workerRequirements: job.workerRequirements, sourceJobId}});
    const followupEvent = await appendEvent(admin, {type: 'job_followup_created', jobId, projectId, actor: caller.actor, summary: `Linked follow-up for ${sourceJobId}.`, evidenceRefs: [`handoff://${sourceJobId}`], data: {sourceJobId, sourceStatus: sourceJob.status}});
    if (!worker) {
      const queuedEvent = await appendEvent(admin, {type: 'job_queued_no_worker', jobId, projectId, actor: 'command_center', summary: selectionFailure.message, data: {requirements: selectionFailure.requirements || job.workerRequirements, workerDiagnostics: job.workerDiagnostics}});
      await recordLog(admin, jobId, projectId, 'Command Center queued follow-up because no real worker was currently eligible.', {sourceJobId, workerRequirements: job.workerRequirements, diagnostic: selectionFailure.message, workerDiagnostics: job.workerDiagnostics});
      const checkpoint = await recordCheckpoint(admin, job);
      return {job, lease: null, activation: null, events: [createdEvent, followupEvent, queuedEvent], checkpoint, sourceHandoff};
    }
    const lease = {leaseId: `lease_${randomUUID()}`, jobId, projectId, workerId: worker.workerId, status: 'active', acquiredAtMs: nowMs, expiresAtMs: nowMs + 30 * 60 * 1000, heartbeatAtMs: nowMs};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).doc(lease.leaseId).set(lease);
    const leasedEvent = await appendEvent(admin, {type: 'job_leased', jobId, projectId, actor: 'command_center', summary: `Leased to ${worker.workerId}.`, data: {worker, eligibleWorkerIds: job.eligibleWorkerIds, selectedWorkerLoad: job.selectedWorkerLoad}});
    const activationResult = await requestJobActivation(admin, job, lease, worker);
    if (activationResult.activation && activationResult.accepted === false) job.status = 'failed';
    await recordLog(admin, jobId, projectId, 'Command Center created linked follow-up job from source handoff.', {sourceJobId, workerId: worker.workerId, sourceStatus: sourceJob.status});
    const checkpoint = await recordCheckpoint(admin, job);
    return {job, lease, activation: activationResult.activation, events: [createdEvent, followupEvent, leasedEvent, ...activationResult.events], checkpoint, sourceHandoff};
  });
}

async function getRepoAgent(admin, agentId) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.repoAgents).doc(cleanAgentId(agentId)).get();
  if (!snap.exists) {
    const err = new Error('Command Center repo agent not found.');
    err.status = 404;
    throw err;
  }
  return snap.data() || {};
}

async function getAgentSession(admin, sessionId) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(cleanSessionId(sessionId)).get();
  if (!snap.exists) {
    const err = new Error('Command Center agent session not found.');
    err.status = 404;
    throw err;
  }
  return snap.data() || {};
}

async function getAgentActivation(admin, activationId) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).doc(cleanActivationId(activationId)).get();
  if (!snap.exists) {
    const err = new Error('Command Center agent activation not found.');
    err.status = 404;
    throw err;
  }
  return snap.data() || {};
}

function buildAgentResumePacket(agent, session, activation, snapshot = null) {
  return {
    packetVersion: 'command-center-codex-cloud-resume-v1',
    generatedAtMs: Date.now(),
    executionSurface: COMMAND_CENTER_CODEX_CLOUD_SURFACE,
    workerSessionContract: {
      durable: true,
      repositoryOptional: true,
      repoRequired: session.repoRequired === true,
      storage: 'gcs_workspace_snapshot_plus_command_center_metadata',
      restoreStrategy: session.restoreStrategy || 'gcs_snapshot',
    },
    agent: {agentId: agent.agentId, projectId: agent.projectId, repository: agent.repository || '', name: agent.name, purpose: agent.purpose, contextRefs: agent.contextRefs || []},
    session: {
      sessionId: session.sessionId,
      sessionKind: session.sessionKind || 'durable_worker_session',
      workerFamily: session.workerFamily || 'cloud-run-debian-codex',
      runtime: session.runtime || 'cloud-run-debian',
      projectId: session.projectId,
      repository: session.repository || '',
      title: session.title,
      purpose: session.purpose,
      currentSummary: session.currentSummary || '',
      contextRefs: session.contextRefs || [],
      artifactRefs: session.artifactRefs || [],
      openQuestions: session.openQuestions || [],
      mutationState: session.mutationState || {},
      currentWorkspaceSnapshotRef: session.currentWorkspaceSnapshotRef || '',
      currentWorkspaceSnapshotDigest: session.currentWorkspaceSnapshotDigest || '',
    },
    activation: {activationId: activation.activationId, status: activation.status, task: activation.task, artifactRefs: activation.artifactRefs || [], codexCloudRefIds: activation.codexCloudRefIds || [], selectedWorkerId: activation.selectedWorkerId || '', workerRequirements: activation.workerRequirements || [], realWorkerRequired: activation.realWorkerRequired === true},
    snapshotRef: snapshot ? `agent-context-snapshot://${snapshot.snapshotId}` : '',
    workspaceSnapshot: {
      restoreRef: activation.restoreWorkspaceSnapshotRef || session.currentWorkspaceSnapshotRef || '',
      restoreDigest: activation.restoreWorkspaceSnapshotDigest || session.currentWorkspaceSnapshotDigest || '',
      nextSnapshotRequired: Array.isArray(activation.workerRequirements) && activation.workerRequirements.includes('durable-session'),
    },
    bridgeInstructions: [
      'Restore the durable worker session workspace before execution; a lease without restored session state is not execution.',
      'Use the cloud worker credential boundary; do not export cookies, tokens, or session state.',
      'Record a real Codex cloud task URL/ref when one exists, but keep this resume packet usable without it.',
      'Upload final report, next workspace snapshot ref, and evidence artifacts; do not claim success from stdout alone.',
    ],
  };
}

async function recordAgentContextSnapshot(admin, agent, session, activation, caller) {
  const snapshotId = `agent_snapshot_${hashText(`${agent.agentId}:${session.sessionId}:${activation.activationId}:${Date.now()}`, 32)}`;
  const payload = {
    snapshotId,
    agentId: agent.agentId,
    sessionId: session.sessionId,
    activationId: activation.activationId,
    projectId: agent.projectId,
    repository: agent.repository,
    sessionKind: session.sessionKind || 'durable_worker_session',
    workerFamily: session.workerFamily || 'cloud-run-debian-codex',
    runtime: session.runtime || 'cloud-run-debian',
    restoreWorkspaceSnapshotRef: activation.restoreWorkspaceSnapshotRef || session.currentWorkspaceSnapshotRef || '',
    nextWorkspaceSnapshotRef: activation.nextWorkspaceSnapshotRef || '',
    currentSummary: session.currentSummary || '',
    prompt: activation.task && activation.task.prompt || '',
    contextRefs: [...safeList(agent.contextRefs, 80, 800), ...safeList(session.contextRefs, 80, 800)],
    artifactRefs: [...safeList(session.artifactRefs, 120, 800), ...safeList(activation.artifactRefs, 120, 800)],
    createdBy: caller.actor || 'command_center',
    createdAtMs: Date.now(),
  };
  await collection(admin, COMMAND_CENTER_COLLECTIONS.agentContextSnapshots).doc(snapshotId).set(payload, {merge: true});
  await upsertBucketObject(admin, {
    objectId: `bucket_${hashText(`agent-current:${agent.agentId}:${session.sessionId}`, 32)}`,
    kind: 'memory.current_condensed',
    title: `Codex cloud resume state: ${agent.name}`,
    path: `memory/current-condensed/${agent.projectId}/codex-cloud-${session.sessionId}.json`,
    summary: activation.task && activation.task.title || 'Codex cloud activation resume state',
    body: JSON.stringify(payload, null, 2),
    projectId: agent.projectId,
    repository: agent.repository,
    sourceRefs: [`repo-agent://${agent.agentId}`, `agent-session://${session.sessionId}`, `agent-activation://${activation.activationId}`],
    tags: ['codex-cloud', 'resume-packet', 'current-summary'],
    source: 'command_center.recordAgentContextSnapshot',
  }, caller);
  return payload;
}

async function upsertRepoAgent(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'agents.upsert_repo_agent', async () => {
    const agent = cleanRepoAgent(args, caller);
    const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.repoAgents).doc(agent.agentId);
    const existing = await ref.get();
    await ref.set({...agent, createdAtMs: existing.exists ? Number((existing.data() || {}).createdAtMs || agent.createdAtMs) : agent.createdAtMs}, {merge: true});
    const session = cleanAgentSession({agentId: agent.agentId, projectId: agent.projectId, sessionId: args.sessionId, title: args.sessionTitle || `${agent.name} Codex cloud session`, purpose: args.sessionPurpose, contextRefs: args.contextRefs}, agent, caller);
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(session.sessionId).set(session, {merge: true});
    const bucketObject = await upsertBucketObject(admin, {
      objectId: `bucket_${hashText(`repo-agent:${agent.agentId}`, 32)}`,
      kind: 'memory.current_condensed',
      title: `Repo agent: ${agent.name}`,
      path: `memory/current-condensed/${agent.projectId}/repo-agent-${agent.agentId}.json`,
      summary: agent.purpose,
      body: JSON.stringify({agent, session, codexCloudSurface: COMMAND_CENTER_CODEX_CLOUD_SURFACE}, null, 2),
      projectId: agent.projectId,
      repository: agent.repository,
      sourceRefs: [`repo-agent://${agent.agentId}`],
      tags: ['repo-agent', 'codex-cloud', 'current-summary'],
      source: 'command_center.agents.upsert_repo_agent',
    }, caller);
    return {agent, session, bucketObject};
  });
}

async function createAgentActivation(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'agents.create_activation', async () => {
    const projectId = cleanProjectId(args.projectId || args.name || 'general-worker-session', args.repository || '');
    const syntheticAgent = {
      agentId: cleanAgentId(args.agentId || `${projectId}-worker`, projectId, args.repository || ''),
      projectId,
      repository: safeText(args.repository, 240),
      name: safeText(args.name, 240) || projectId,
      purpose: safeText(args.purpose, 2000) || 'Durable repo-optional worker session owner.',
      contextRefs: safeList(args.contextRefs, 80, 800),
    };
    const agent = args.agentId ? await getRepoAgent(admin, args.agentId) : syntheticAgent;
    if (!args.agentId) await collection(admin, COMMAND_CENTER_COLLECTIONS.repoAgents).doc(agent.agentId).set({...agent, agentType: 'durable_worker_session_owner', repositoryOptional: true, status: 'active', createdBy: caller.actor, updatedBy: caller.actor, createdAtMs: Date.now(), updatedAtMs: Date.now()}, {merge: true});
    const session = args.sessionId ? await getAgentSession(admin, args.sessionId) : cleanAgentSession({
      agentId: agent.agentId,
      projectId: agent.projectId,
      repository: agent.repository,
      title: args.sessionTitle || `${agent.name} durable worker session`,
      purpose: args.sessionPurpose,
      workerFamily: args.workerFamily,
      runtime: args.runtime,
      currentWorkspaceSnapshotRef: args.currentWorkspaceSnapshotRef,
      currentWorkspaceSnapshotDigest: args.currentWorkspaceSnapshotDigest,
      restoreStrategy: args.restoreStrategy,
      contextRefs: args.contextRefs,
      openQuestions: args.openQuestions,
      preferredWorkerIds: args.preferredWorkerIds,
    }, agent, caller);
    if (!args.sessionId) await collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(session.sessionId).set(session, {merge: true});
    const task = cleanActivationTask(args);
    if (!task.prompt) {
      const err = new Error('A real Codex cloud activation prompt is required.');
      err.status = 400;
      throw err;
    }
	    const nowMs = Date.now();
	    const activationId = cleanActivationId(args.activationId);
	    const workerRequirements = activationWorkerRequirements(args, task);
	    const worker = selectWorker(recordsVisibleToCaller(await workerRecords(admin), caller), workerRequirements, {requireActivationChannel: false});
	    const activation = {
	      activationId,
	      agentId: agent.agentId,
	      sessionId: session.sessionId,
	      projectId: agent.projectId,
	      repository: agent.repository,
	      sessionKind: session.sessionKind || 'durable_worker_session',
	      workerFamily: session.workerFamily || 'cloud-run-debian-codex',
	      runtime: session.runtime || 'cloud-run-debian',
	      status: 'queued',
	      executionSurface: COMMAND_CENTER_CODEX_CLOUD_SURFACE.surfaceId,
	      realWorkerRequired: true,
	      workerRequirements,
	      restoreWorkspaceSnapshotRef: session.currentWorkspaceSnapshotRef || '',
	      restoreWorkspaceSnapshotDigest: session.currentWorkspaceSnapshotDigest || '',
	      nextWorkspaceSnapshotRequired: workerRequirements.includes('durable-session'),
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
	    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).doc(activationId).set(activation);
	    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(session.sessionId).set({latestActivationId: activationId, updatedAtMs: nowMs, updatedBy: caller.actor}, {merge: true});
	    const snapshot = await recordAgentContextSnapshot(admin, agent, session, activation, caller);
	    const channel = normalizeActivationChannel(worker.activation);
	    let cloudRunActivation = null;
	    if (channel.mode === 'cloud_run_job') {
	      cloudRunActivation = await invokeCloudRunJobActivation(worker, activation, session);
	      const cloudRunState = activationStateFromResult(cloudRunActivation);
	      await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).doc(activationId).set({
	        status: cloudRunState.accepted ? 'queued' : 'failed',
	        cloudRunOperationName: cloudRunActivation.executorId || '',
	        activationDiagnostic: cloudRunState.diagnostic,
	        updatedAtMs: Date.now(),
	      }, {merge: true});
	      if (!cloudRunState.accepted) {
	        const err = new Error(`Cloud Run worker activation failed: ${cloudRunState.diagnostic}`);
	        err.status = 502;
	        throw err;
	      }
	    }
	    await upsertBucketObject(admin, {
	      kind: 'memory.current_condensed',
	      title: `Real worker selected for activation ${activationId}`,
	      path: `memory/current-condensed/${agent.projectId}/activation-${activationId}-worker.json`,
	      summary: `Activation requires a real worker and selected ${worker.workerId}.`,
	      body: JSON.stringify({activationId, sessionId: session.sessionId, selectedWorkerId: worker.workerId, workerRequirements, selectedWorker: activation.selectedWorker, restoreWorkspaceSnapshotRef: activation.restoreWorkspaceSnapshotRef, cloudRunOperationName: cloudRunActivation && cloudRunActivation.executorId || ''}, null, 2),
	      projectId: agent.projectId,
	      repository: agent.repository,
	      sourceRefs: [`agent-activation://${activationId}`, `worker://${worker.workerId}`],
	      tags: ['codex-cloud', 'real-worker', 'activation'],
	      source: 'command_center.agents.create_activation',
	    }, caller);
	    return {activation, agent, session, resumePacket: buildAgentResumePacket(agent, session, activation, snapshot)};
	  });
	}

async function getAgentResumePacket(admin, args) {
  const activation = await getAgentActivation(admin, args.activationId);
  const [agent, session] = await Promise.all([getRepoAgent(admin, activation.agentId), getAgentSession(admin, activation.sessionId)]);
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.agentContextSnapshots).where('activationId', '==', activation.activationId).limit(10).get();
  const snapshots = [];
  snap.forEach((doc) => snapshots.push(doc.data()));
  snapshots.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  return {resumePacket: buildAgentResumePacket(agent, session, activation, snapshots[0] || null)};
}

async function recordCodexCloudRef(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'agents.record_codex_cloud_ref', async () => {
    const activation = await getAgentActivation(admin, args.activationId);
    const ref = {...cleanCodexCloudRef(args), activationId: activation.activationId, agentId: activation.agentId, sessionId: activation.sessionId, projectId: activation.projectId, repository: activation.repository, recordedBy: caller.actor, createdAtMs: Date.now(), updatedAtMs: Date.now()};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.codexCloudRefs).doc(ref.codexCloudRefId).set(ref, {merge: true});
    const refs = Array.from(new Set([...(activation.codexCloudRefIds || []), ref.codexCloudRefId]));
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).doc(activation.activationId).set({status: args.activationStatus || 'running', codexCloudRefIds: refs, updatedAtMs: Date.now()}, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(activation.sessionId).set({latestCodexCloudRefId: ref.codexCloudRefId, updatedAtMs: Date.now()}, {merge: true});
    return {codexCloudRef: ref, activationId: activation.activationId};
  });
}

async function recordAgentArtifact(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'agents.record_artifact', async () => {
    const activation = await getAgentActivation(admin, args.activationId);
    const name = safeText(args.name, 240) || 'codex-cloud-artifact';
    const uri = safeText(args.uri || args.objectUri, 1200);
    const body = safeText(args.body, 64000);
    if (containsForbiddenSecret([name, uri, body, args.summary].join('\n'))) {
      const err = new Error('Agent artifacts must not contain reusable secrets or bearer credentials.');
      err.status = 400;
      throw err;
    }
    const artifact = {
      artifactId: safeText(args.artifactId, 180) || `agent_artifact_${hashText(`${activation.activationId}:${name}:${Date.now()}`, 32)}`,
      activationId: activation.activationId,
      agentId: activation.agentId,
      sessionId: activation.sessionId,
      projectId: activation.projectId,
      repository: activation.repository,
      name,
      kind: safeText(args.kind, 120) || 'report',
      uri,
      body,
      summary: safeText(args.summary, 2000),
      sha256: safeText(args.sha256, 128) || (body ? fullHash(body) : ''),
      required: args.required === true,
      evidenceRefs: safeList(args.evidenceRefs, 80, 800),
      createdBy: caller.actor,
      createdAtMs: Date.now(),
    };
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentArtifacts).doc(artifact.artifactId).set(artifact, {merge: true});
    const refs = Array.from(new Set([...(activation.artifactRefs || []), `agent-artifact://${artifact.artifactId}`]));
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).doc(activation.activationId).set({artifactRefs: refs, updatedAtMs: Date.now()}, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(activation.sessionId).set({artifactRefs: refs, updatedAtMs: Date.now()}, {merge: true});
    return {artifact};
  });
}

async function synthesizeAgentHandoff(admin, activationId) {
  const activation = await getAgentActivation(admin, activationId);
  const [agent, session] = await Promise.all([getRepoAgent(admin, activation.agentId), getAgentSession(admin, activation.sessionId)]);
  const [artifactSnap, refSnap, snapshotSnap] = await Promise.all([
    collection(admin, COMMAND_CENTER_COLLECTIONS.agentArtifacts).where('activationId', '==', activation.activationId).limit(100).get(),
    collection(admin, COMMAND_CENTER_COLLECTIONS.codexCloudRefs).where('activationId', '==', activation.activationId).limit(20).get(),
    collection(admin, COMMAND_CENTER_COLLECTIONS.agentContextSnapshots).where('activationId', '==', activation.activationId).limit(20).get(),
  ]);
  const artifacts = [];
  artifactSnap.forEach((doc) => artifacts.push(doc.data()));
  artifacts.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  const codexCloudRefs = [];
  refSnap.forEach((doc) => codexCloudRefs.push(doc.data()));
  codexCloudRefs.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  const snapshots = [];
  snapshotSnap.forEach((doc) => snapshots.push(doc.data()));
  snapshots.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  return {
    packetVersion: 'command-center-codex-cloud-handoff-v1',
    generatedAtMs: Date.now(),
    agent: {agentId: agent.agentId, projectId: agent.projectId, repository: agent.repository, name: agent.name},
    session: {sessionId: session.sessionId, status: session.status, title: session.title, currentSummary: session.currentSummary || ''},
    activation: {activationId: activation.activationId, status: activation.status, task: activation.task, finalSummary: activation.finalSummary || '', handoffSummary: activation.handoffSummary || ''},
    codexCloudRefs: codexCloudRefs.map((ref) => ({codexCloudRefId: ref.codexCloudRefId, surface: ref.surface, url: ref.url, status: ref.status, title: ref.title, summary: ref.summary, evidenceRefs: ref.evidenceRefs || []})),
    artifacts: artifacts.map((artifact) => ({artifactId: artifact.artifactId, name: artifact.name, kind: artifact.kind, uri: artifact.uri, summary: artifact.summary, sha256: artifact.sha256, required: artifact.required === true})),
    latestSnapshot: snapshots[0] || null,
    review: {
      realCodexCloudRequired: true,
      credentialBoundary: COMMAND_CENTER_CODEX_CLOUD_SURFACE.credentialPolicy,
      recommendedNextAction: activation.status === 'completed' ? 'Review Codex cloud report and create a follow-up activation for implementation.' : 'Resume or repair the Codex cloud bridge using this handoff and resume packet.',
    },
  };
}

async function completeAgentActivation(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'agents.complete_activation', async () => {
    const activation = await getAgentActivation(admin, args.activationId);
    const status = COMMAND_CENTER_AGENT_ACTIVATION_STATUSES.includes(args.status) ? args.status : (args.failed === true ? 'failed' : 'completed');
    if (!['completed', 'failed', 'canceled', 'needs_human'].includes(status)) {
      const err = new Error('Activation completion status must be completed, failed, canceled, or needs_human.');
      err.status = 400;
      throw err;
    }
    const finalSummary = safeText(args.finalSummary || args.summary, 8000);
    if (containsForbiddenSecret(finalSummary)) {
      const err = new Error('Activation summaries must not contain reusable secrets or bearer credentials.');
      err.status = 400;
      throw err;
    }
    const nextWorkspaceSnapshotRef = safeText(args.nextWorkspaceSnapshotRef || args.workspaceSnapshotRef, 1200);
    const nextWorkspaceSnapshotDigest = safeText(args.nextWorkspaceSnapshotDigest || args.workspaceSnapshotDigest, 160);
    if (status === 'completed' && activation.nextWorkspaceSnapshotRequired === true && !nextWorkspaceSnapshotRef) {
      const err = new Error('Durable worker session completion requires nextWorkspaceSnapshotRef.');
      err.status = 409;
      throw err;
    }
    if (status === 'completed' && (!Array.isArray(activation.artifactRefs) || !activation.artifactRefs.length)) {
      const err = new Error('Durable Codex worker activation completion requires at least one artifact.');
      err.status = 409;
      throw err;
    }
    const updates = {status, finalSummary, handoffSummary: safeText(args.handoffSummary, 4000) || finalSummary, nextWorkspaceSnapshotRef, nextWorkspaceSnapshotDigest, updatedAtMs: Date.now(), completedAtMs: Date.now(), completedBy: caller.actor};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentActivations).doc(activation.activationId).set(updates, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(activation.sessionId).set({status: status === 'completed' ? 'active' : status, currentSummary: finalSummary, latestActivationId: activation.activationId, currentWorkspaceSnapshotRef: nextWorkspaceSnapshotRef || activation.restoreWorkspaceSnapshotRef || '', currentWorkspaceSnapshotDigest: nextWorkspaceSnapshotDigest || activation.restoreWorkspaceSnapshotDigest || '', updatedAtMs: Date.now(), updatedBy: caller.actor}, {merge: true});
    const bucketObject = await upsertBucketObject(admin, {
      kind: 'memory.past_log',
      title: `Codex cloud activation ${status}: ${activation.task && activation.task.title || activation.activationId}`,
      path: `memory/past-logs/${activation.projectId}/${activation.activationId}.md`,
      summary: finalSummary,
      body: finalSummary,
      projectId: activation.projectId,
      repository: activation.repository,
      sourceRefs: [`agent-activation://${activation.activationId}`, ...(activation.codexCloudRefIds || []).map((id) => `codex-cloud-ref://${id}`)],
      evidenceRefs: activation.artifactRefs || [],
      tags: ['codex-cloud', 'activation', status],
      source: 'command_center.agents.complete_activation',
    }, caller);
    return {activationId: activation.activationId, status, bucketObject, handoff: await synthesizeAgentHandoff(admin, activation.activationId)};
  });
}


function staleJobCutoffMs(args = {}) {
  const requested = Number(args.olderThanMs || 0) || COMMAND_CENTER_RECONCILE_DEFAULT_OLDER_THAN_MS;
  return Math.max(60 * 1000, Math.min(requested, 7 * 24 * 60 * 60 * 1000));
}

function staleJobClockMs(job) {
  return Number(job.lastWorkerHeartbeatAtMs || job.executorStartedAtMs || job.workerAcceptedLeaseAtMs || job.updatedAtMs || job.createdAtMs || 0) || 0;
}

function staleJobCandidate(job, nowMs, olderThanMs, statuses) {
  const status = safeText(job.status, 80);
  if (!statuses.includes(status)) return null;
  const clockMs = staleJobClockMs(job);
  const ageMs = clockMs > 0 ? nowMs - clockMs : Number.POSITIVE_INFINITY;
  if (ageMs < olderThanMs) return null;
  const routingDiagnostic = safeText(job.routingDiagnostic, 1000);
  const queuedWithoutWorker = status === 'queued' && !(job.selectedWorkerId || '').trim();
  const reason = queuedWithoutWorker
    ? `queued job had no eligible worker for at least ${olderThanMs}ms${routingDiagnostic ? `: ${routingDiagnostic}` : ''}`
    : `nonterminal job stale for at least ${olderThanMs}ms`;
  return {
    jobId: job.jobId,
    projectId: job.projectId,
    status,
    selectedWorkerId: job.selectedWorkerId || '',
    createdAtMs: Number(job.createdAtMs || 0) || 0,
    updatedAtMs: Number(job.updatedAtMs || 0) || 0,
    lastWorkerHeartbeatAtMs: Number(job.lastWorkerHeartbeatAtMs || 0) || 0,
    routingDiagnostic,
    staleAgeMs: Number.isFinite(ageMs) ? ageMs : null,
    reason,
  };
}

function activationStartTimeoutCandidate(job = {}, activations = [], nowMs = Date.now(), timeoutMs = COMMAND_CENTER_COLD_START_HEARTBEAT_DEADLINE_MS) {
  if (isTerminalJobStatus(job.status)) return null;
  if (!['leased', 'activating'].includes(safeText(job.status, 80))) return null;
  if (Number(job.executorStartedAtMs || 0) > 0 || Number(job.workerAcceptedLeaseAtMs || 0) > 0) return null;
  const accepted = activations
    .filter((activation) => activation.jobId === job.jobId && activation.status === 'accepted')
    .sort((a, b) => Number(b.acceptedAtMs || b.updatedAtMs || 0) - Number(a.acceptedAtMs || a.updatedAtMs || 0))[0] || null;
  if (!accepted) return null;
  const acceptedAtMs = Number(accepted.acceptedAtMs || accepted.updatedAtMs || 0) || 0;
  const ageMs = acceptedAtMs > 0 ? nowMs - acceptedAtMs : Number.POSITIVE_INFINITY;
  if (ageMs < timeoutMs) return null;
  return {
    jobId: job.jobId,
    projectId: job.projectId,
    status: job.status,
    selectedWorkerId: job.selectedWorkerId || accepted.workerId || '',
    activationId: accepted.activationId || '',
    leaseId: accepted.leaseId || '',
    acceptedAtMs,
    activationAgeMs: Number.isFinite(ageMs) ? ageMs : null,
    reason: `accepted activation did not produce executor_started within ${timeoutMs}ms`,
  };
}

async function reconcileActivationStartTimeouts(admin, actor = 'command_center', args = {}) {
  const nowMs = Date.now();
  const timeoutMs = Math.max(30 * 1000, Math.min(Number(args.timeoutMs || 0) || COMMAND_CENTER_COLD_START_HEARTBEAT_DEADLINE_MS, 30 * 60 * 1000));
  const limit = Math.max(1, Math.min(Number(args.limit) || 100, 500));
  const jobSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).orderBy('createdAtMs', 'desc').limit(limit).get();
  const activationSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobActivations).orderBy('requestedAtMs', 'desc').limit(limit * 2).get();
  const activations = [];
  activationSnap.forEach((doc) => activations.push(doc.data() || {}));
  const candidates = [];
  jobSnap.forEach((doc) => {
    const candidate = activationStartTimeoutCandidate(doc.data() || {}, activations, nowMs, timeoutMs);
    if (candidate) candidates.push(candidate);
  });
  const reconciled = [];
  for (const candidate of candidates) {
    const job = await getJob(admin, candidate.jobId);
    if (isTerminalJobStatus(job.status) || Number(job.executorStartedAtMs || 0) > 0 || Number(job.workerAcceptedLeaseAtMs || 0) > 0) continue;
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobActivations).doc(candidate.activationId).set({status: 'timed_out', timedOutAtMs: nowMs, updatedAtMs: nowMs, diagnostic: candidate.reason}, {merge: true});
    const result = await failJobTerminal(admin, job, actor, candidate.reason, {activationId: candidate.activationId, leaseId: candidate.leaseId, activationTimedOut: true});
    reconciled.push({...candidate, releasedLeases: result.releasedLeases, eventId: result.event.eventId});
  }
  return {timeoutMs, scanned: jobSnap.size, candidates, reconciled};
}

async function reconcileStaleJobs(admin, caller, args = {}) {
  const dryRun = args.dryRun !== false;
  const nowMs = Date.now();
  const staleReconcileStatuses = ['queued', 'leased', 'executing', 'running', 'activating'];
  const statuses = safeList(args.statuses, 20, 80).filter((status) => staleReconcileStatuses.includes(status));
  const targetStatuses = statuses.length ? statuses : staleReconcileStatuses;
  const olderThanMs = staleJobCutoffMs(args);
  const limit = Math.max(1, Math.min(Number(args.limit) || 50, 500));
  if (!dryRun) requireIdempotencyKey(args.idempotencyKey);
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).orderBy('createdAtMs', 'desc').limit(limit).get();
  const candidates = [];
  snap.forEach((doc) => {
    const candidate = staleJobCandidate(doc.data() || {}, nowMs, olderThanMs, targetStatuses);
    if (candidate) candidates.push(candidate);
  });
  const reconciled = [];
  if (!dryRun) {
    for (const candidate of candidates) {
      await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(candidate.jobId).set({
        status: 'expired',
        updatedAtMs: nowMs,
        expiredAtMs: nowMs,
        reconciledAtMs: nowMs,
        reconciledBy: caller.actor,
        reconcileReason: candidate.reason,
        previousStatus: candidate.status,
      }, {merge: true});
      const leaseSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).where('jobId', '==', candidate.jobId).limit(20).get();
      const batch = admin.firestore().batch();
      let expiredLeases = 0;
      leaseSnap.forEach((doc) => {
        const lease = doc.data() || {};
        if (lease.status === 'active') {
          expiredLeases += 1;
          batch.set(doc.ref, {status: 'expired', expiredAtMs: nowMs, updatedAtMs: nowMs, expirationReason: candidate.reason, releaseReason: candidate.reason}, {merge: true});
        }
      });
      if (expiredLeases) await batch.commit();
      const event = await appendEvent(admin, {type: 'job_expired', jobId: candidate.jobId, projectId: candidate.projectId, actor: caller.actor, summary: candidate.reason, data: {...candidate, status: 'expired', expiredLeases, reconciledFromStale: true}});
      await recordLog(admin, candidate.jobId, candidate.projectId, 'Command Center expired stale nonterminal job.', {...candidate, expiredLeases, previousStatus: candidate.status});
      reconciled.push({...candidate, status: 'expired', expiredLeases, eventId: event.eventId});
    }
  }
  return {dryRun, olderThanMs, statuses: targetStatuses, scanned: snap.size, candidates, reconciled};
}

async function dispatchQueuedJobsInner(admin, caller, args = {}, dryRun = true) {
  const nowMs = Date.now();
  const limit = Math.max(1, Math.min(Number(args.limit) || 25, 100));
  const maxDispatch = Math.max(1, Math.min(Number(args.maxDispatch) || 10, 50));
  const retryExpired = args.retryExpired === true;
  const targetStatuses = retryExpired ? ['queued', 'expired'] : ['queued'];
  const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
  const snap = await queryOwnedCollection(admin, COMMAND_CENTER_COLLECTIONS.jobs, caller).orderBy('createdAtMs', 'desc').limit(limit).get();
  const candidates = [];
  const dispatched = [];
  for (const doc of snap.docs) {
    const job = doc.data() || {};
    const status = safeText(job.status, 80);
    if (!targetStatuses.includes(status)) continue;
    if (isTerminalJobStatus(status) && !(retryExpired && status === 'expired')) continue;
    if (status === 'expired' && !(job.recoverable === true || job.previousStatus === 'queued')) continue;
    const activeLease = await activeLeaseForJob(admin, job.jobId, job.selectedWorkerId || '');
    if (activeLease) {
      candidates.push({jobId: job.jobId, projectId: job.projectId, status, dispatchable: false, reason: 'active lease already exists', selectedWorkerId: job.selectedWorkerId || ''});
      continue;
    }
    let selection = null;
    let selectionFailure = null;
    try {
      selection = await selectWorkerForJob(admin, workers, job.workerRequirements || []);
    } catch (err) {
      if (!workerSelectionFailure(err)) throw err;
      selectionFailure = err;
    }
    if (!selection) {
      candidates.push({jobId: job.jobId, projectId: job.projectId, status, dispatchable: false, reason: selectionFailure.message, workerDiagnostics: selectionFailure.workerDiagnostics || []});
      continue;
    }
    const candidate = {jobId: job.jobId, projectId: job.projectId, status, dispatchable: true, selectedWorkerId: selection.worker.workerId, eligibleWorkerIds: selection.eligibleWorkerIds, selectedWorkerLoad: selection.selectedWorkerLoad};
    candidates.push(candidate);
    if (dryRun || dispatched.length >= maxDispatch) continue;
    const refreshed = await getJob(admin, job.jobId, caller);
    const refreshedStatus = safeText(refreshed.status, 80);
    if (!targetStatuses.includes(refreshedStatus)) continue;
    if (refreshedStatus === 'expired' && !(retryExpired && (refreshed.recoverable === true || refreshed.previousStatus === 'queued'))) continue;
    const refreshedActiveLease = await activeLeaseForJob(admin, refreshed.jobId, refreshed.selectedWorkerId || '');
    if (refreshedActiveLease) continue;
    const refreshedSelection = await selectWorkerForJob(admin, workers, refreshed.workerRequirements || []);
    const worker = refreshedSelection.worker;
    const dispatchAttemptCount = Number(refreshed.dispatchAttemptCount || 0) + 1;
    const lease = {leaseId: `lease_${randomUUID()}`, jobId: refreshed.jobId, projectId: refreshed.projectId, workerId: worker.workerId, status: 'active', acquiredAtMs: nowMs, expiresAtMs: nowMs + 30 * 60 * 1000, heartbeatAtMs: nowMs, dispatchAttemptCount, recoveredFromStatus: refreshedStatus};
    const updates = {
      status: 'leased',
      selectedWorkerId: worker.workerId,
      eligibleWorkerIds: refreshedSelection.eligibleWorkerIds,
      workerDiagnostics: refreshedSelection.workerDiagnostics,
      selectedWorkerLoad: refreshedSelection.selectedWorkerLoad,
      dispatchAttemptCount,
      lastDispatchAtMs: nowMs,
      lastDispatchBy: caller.actor,
      previousStatus: refreshedStatus,
      routingDiagnostic: '',
      updatedAtMs: nowMs,
      recoverable: true,
    };
    await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).doc(lease.leaseId).set(lease);
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(refreshed.jobId).set(updates, {merge: true});
    const dispatchEvent = await appendEvent(admin, {type: 'job_dispatched_from_queue', jobId: refreshed.jobId, projectId: refreshed.projectId, actor: caller.actor, summary: `Dispatched recoverable job to ${worker.workerId}.`, data: {leaseId: lease.leaseId, workerId: worker.workerId, recoveredFromStatus: refreshedStatus, dispatchAttemptCount, eligibleWorkerIds: refreshedSelection.eligibleWorkerIds, selectedWorkerLoad: refreshedSelection.selectedWorkerLoad}});
    const leasedEvent = await appendEvent(admin, {type: 'job_leased', jobId: refreshed.jobId, projectId: refreshed.projectId, actor: 'command_center', summary: `Leased to ${worker.workerId}.`, data: {worker, eligibleWorkerIds: refreshedSelection.eligibleWorkerIds, selectedWorkerLoad: refreshedSelection.selectedWorkerLoad, recoveredFromStatus: refreshedStatus}});
    const activationResult = await requestJobActivation(admin, {...refreshed, ...updates}, lease, worker);
    await recordLog(admin, refreshed.jobId, refreshed.projectId, 'Command Center dispatched queued recoverable job.', {workerId: worker.workerId, leaseId: lease.leaseId, recoveredFromStatus: refreshedStatus, dispatchAttemptCount});
    const checkpoint = await recordCheckpoint(admin, {...refreshed, ...updates});
    dispatched.push({jobId: refreshed.jobId, projectId: refreshed.projectId, status: activationResult.accepted === false ? 'failed' : 'leased', workerId: worker.workerId, leaseId: lease.leaseId, dispatchAttemptCount, eventIds: [dispatchEvent.eventId, leasedEvent.eventId, ...activationResult.events.map((event) => event.eventId)], activation: activationResult.activation, checkpoint});
  }
  return {dryRun, retryExpired, statuses: targetStatuses, scanned: snap.size, candidates, dispatched};
}

async function dispatchQueuedJobs(admin, caller, args = {}) {
  const dryRun = args.dryRun !== false;
  if (dryRun) return dispatchQueuedJobsInner(admin, caller, args, true);
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'jobs.dispatch_queued', async () => dispatchQueuedJobsInner(admin, caller, args, false));
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

async function activeLeaseForJob(admin, jobId, selectedWorkerId = '') {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).where('jobId', '==', jobId).limit(20).get();
  const nowMs = Date.now();
  const leases = [];
  snap.forEach((doc) => {
    const lease = doc.data() || {};
    if (lease.status !== 'active') return;
    if (selectedWorkerId && lease.workerId !== selectedWorkerId) return;
    if (Number(lease.expiresAtMs || 0) > 0 && Number(lease.expiresAtMs || 0) <= nowMs) return;
    leases.push(lease);
  });
  leases.sort((a, b) => Number(b.heartbeatAtMs || b.acquiredAtMs || 0) - Number(a.heartbeatAtMs || a.acquiredAtMs || 0));
  return leases[0] || null;
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

async function resumeJob(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'jobs.resume', async () => {
    const jobId = cleanJobId(args.jobId);
    const job = await getJob(admin, jobId, caller);
    const lease = await activeLeaseForJob(admin, jobId, job.selectedWorkerId);
    if (!job.selectedWorkerId || !lease) {
      const event = await appendEvent(admin, {type: 'job_resume_blocked', jobId, projectId: job.projectId, actor: caller.actor, summary: 'Resume blocked: job has no active worker lease.', data: {selectedWorkerId: job.selectedWorkerId || '', currentStatus: job.status}});
      await recordLog(admin, jobId, job.projectId, 'Command Center refused to mark job running without an active lease.', {selectedWorkerId: job.selectedWorkerId || '', currentStatus: job.status});
      return {jobId, resumed: false, status: job.status, reason: 'missing_active_lease', event};
    }
    const updates = {status: 'running', updatedAtMs: Date.now(), lastTransitionBy: caller.actor, resumedAtMs: Date.now(), resumeLeaseId: lease.leaseId};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set(updates, {merge: true});
    const event = await appendEvent(admin, {type: 'job_running', jobId, projectId: job.projectId, actor: caller.actor, summary: safeText(args.reason, 1000) || 'Job resumed with active lease.', data: {leaseId: lease.leaseId, workerId: lease.workerId}});
    return {jobId, status: 'running', resumed: true, lease, event};
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
    const requestedInstallationId = safeText(args.workerInstallationId || args.installationId, 180);
    let canonicalWorkerId = workerId;
    if (requestedInstallationId) {
      const sameInstall = await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).where('workerInstallationId', '==', requestedInstallationId).limit(5).get();
      sameInstall.forEach((doc) => { if (!canonicalWorkerId || doc.id !== workerId) canonicalWorkerId = doc.id; });
    }
    const existing = await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(canonicalWorkerId).get();
    if (existing.exists) {
      assertOwnerAccess(existing.data() || {}, caller, 'Command Center worker');
      const currentInstallation = safeText((existing.data() || {}).workerInstallationId, 180);
      if (requestedInstallationId && currentInstallation && currentInstallation !== requestedInstallationId) {
        const err = new Error('workerId alias is already bound to another workerInstallationId.');
        err.status = 409;
        err.code = 'DUPLICATE_ALIAS_CONFLICT';
        throw err;
      }
    }
    const workerToken = `ccw_${randomUUID()}_${randomUUID()}`;
    const tokenHash = tokenDigest(workerToken);
    const requestedActivation = normalizeActivationChannel(args.activation);
    const worker = cleanWorker({
      workerId: canonicalWorkerId,
      engine: args.engine || 'codex',
      location: args.location || 'local',
      health: 'healthy',
      capabilities: safeList(args.capabilities, 80, 120),
	      baseWorkspaces: Array.isArray(args.baseWorkspaces) ? args.baseWorkspaces : [args.baseWorkspace || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE],
	      limits: safeObject(args.limits),
	      activation: requestedActivation.mode ? {...requestedActivation, verifiedAtMs: requestedActivation.verifiedAtMs || nowMs} : {mode: 'poll', verifiedAtMs: nowMs},
      workerInstallationId: requestedInstallationId || `legacy-${hashText(args.stableWorkerIdentity || args.hostIdentity || workerId, 24)}`,
      workerInstanceId: safeText(args.workerInstanceId || args.instanceId, 180),
      runnerVersion: safeText(args.runnerVersion, 80) || safeText(safeObject(args.runtime).runnerVersion, 80),
      protocolVersion: safeText(args.protocolVersion, 80) || safeText(safeObject(args.runtime).protocolVersion, 80),
      processStartAtMs: Number(args.processStartAtMs || 0) || 0,
      heartbeatSeq: Number(args.heartbeatSeq || 0) || 0,
      preparedWorkspaces: Array.isArray(args.preparedWorkspaces) ? args.preparedWorkspaces : (Array.isArray(args.baseWorkspaces) ? args.baseWorkspaces : [args.baseWorkspace || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE]),
      stableWorkerIdentity: safeText(args.stableWorkerIdentity || args.hostIdentity || workerId, 180),
	      runtime: {...safeObject(args.runtime), authMode: safeText(safeObject(args.runtime).authMode || safeObject(args.runtime).codexAuth, 80)},
	      cloudRunJob: safeObject(args.cloudRunJob),
	      sessionPolicy: safeObject(args.sessionPolicy),
          availableImageIds: safeList(args.availableImageIds, 80, 160),
          materializedImageIds: safeList(args.materializedImageIds, 80, 160),
          machineImages: Array.isArray(args.machineImages) ? args.machineImages.slice(0, 40) : [],
          cacheState: safeObject(args.cacheState),
          maxConcurrentSessions: Number(args.maxConcurrentSessions || safeObject(args.sessionCapacity).maxConcurrentSessions || 0) || undefined,
          activeSessionIds: safeList(args.activeSessionIds || safeObject(args.sessionCapacity).activeSessionIds, 100, 180),
          sessionIsolationModes: safeList(args.sessionIsolationModes || safeObject(args.sessionCapacity).sessionIsolationModes, 10, 80),
          canMaterializeImages: args.canMaterializeImages === true || safeObject(args.sessionCapacity).canMaterializeImages === true,
	      repositoryAffinity: safeList(args.repositoryAffinity, 80, 240),
	      lastHeartbeatAtMs: nowMs,
      ownerKey: ownerKeyFromCaller(caller),
      simulated: false,
      oneShot: true,
    });
    if (!worker.capabilities.length) worker.capabilities = ['codex', 'one-shot-worker', 'prepared-workspace'];
    await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(canonicalWorkerId).set({...worker, registeredBy: caller.actor, updatedAtMs: nowMs, createdAtMs: existing.exists ? (Number((existing.data() || {}).createdAtMs || 0) || nowMs) : nowMs}, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.workerTokens).doc(tokenHash).set({workerId: canonicalWorkerId, ownerKey: ownerKeyFromCaller(caller), createdBy: caller.actor, createdAtMs: nowMs, expiresAtMs: nowMs + 90 * 24 * 60 * 60 * 1000, authKind: 'command_center_worker_token'}, {merge: false});
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


async function systemHealth(admin, caller) {
  const activationTimeouts = await reconcileActivationStartTimeouts(admin, 'command_center_system_health', {limit: 250});
  const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
  const counts = await activeLeaseCountsByWorker(admin);
  const census = filterWorkerCensus(workers, {}, counts);
  const jobSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).orderBy('createdAtMs', 'desc').limit(250).get();
  const recentProbe = await recentEndToEndExecutionProbe(admin, jobSnap);
  const workerPool = {
    total: census.length,
    real: census.filter((row) => row.real).length,
    routable: census.filter((row) => row.routable).length,
    active: census.filter((row) => row.status === 'active').length,
    stale: census.filter((row) => row.status === 'stale').length,
    retired: census.filter((row) => row.status === 'retired').length,
    legacy: census.filter((row) => row.legacyIdentity).length,
    routableWorkerIds: census.filter((row) => row.routable).map((row) => row.workerId),
  };
  return {
    ok: true,
    controlPlane: {ok: true, service: 'command-center-mcp', invokable: true, hasFrontend: false, commandCenterMcpUrl: COMMAND_CENTER_RESOURCE},
    workerPool: {...workerPool, ok: workerPool.routable > 0, status: workerPool.routable > 0 ? 'has_routable_workers' : 'no_routable_workers'},
    recentEndToEndProbe: recentProbe,
    activationTimeoutReconciliation: {candidates: activationTimeouts.candidates.length, reconciled: activationTimeouts.reconciled.length, timeoutMs: activationTimeouts.timeoutMs},
  };
}

async function listWorkersCensus(admin, caller, args = {}) {
  const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
  const counts = await activeLeaseCountsByWorker(admin);
  const workersOut = filterWorkerCensus(workers, args, counts);
  return {workers: workersOut, summary: {total: workersOut.length, routable: workersOut.filter((row) => row.routable).length, stale: workersOut.filter((row) => row.status === 'stale').length, retired: workersOut.filter((row) => row.status === 'retired').length}};
}

async function inspectWorker(admin, caller, args = {}) {
  const workerId = safeText(args.workerId, 120);
  if (!workerId) {
    const err = new Error('workerId is required.');
    err.status = 400;
    throw err;
  }
  const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
  const worker = workers.find((item) => item.workerId === workerId) || null;
  if (!worker) return {workerId, found: false, diagnosis: {code: 'worker_not_found', localInterventionRequired: true, explanation: 'No worker record exists for this owner.'}};
  const counts = await activeLeaseCountsByWorker(admin);
  const leasesSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.leases).where('workerId', '==', workerId).limit(50).get();
  const leases = [];
  leasesSnap.forEach((doc) => leases.push(doc.data() || {}));
  leases.sort((a, b) => Number(b.acquiredAtMs || 0) - Number(a.acquiredAtMs || 0));
  const eventsSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.events).where('actor', '==', workerId).limit(50).get();
  const events = [];
  eventsSnap.forEach((doc) => events.push(doc.data() || {}));
  events.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  const census = compactWorkerCensus(worker, counts.get(workerId) || 0);
  const diagnosis = failureDiagnosisForWorker(worker);
  return {worker: census, registration: worker, recentLeases: leases.slice(0, 20), recentEvents: events.slice(0, 20), repair: diagnosis};
}

function failureDiagnosisForWorker(worker = {}) {
  const route = workerRoutabilityDiagnostic(worker);
  if (isLocalHostWorker(worker)) return {code: 'local_host_excluded', explanation: 'Local, phone, and Termux workers are excluded from generic Command Center Codex routing.', automaticallyRepairable: true, safeRecommendedOperation: 'workers.provision', localPhysicalInterventionRequired: false};
  if (route.routable) return {code: 'healthy', explanation: 'Worker is routable.', automaticallyRepairable: false, safeRecommendedOperation: '', localPhysicalInterventionRequired: false};
  const map = {
    stale_heartbeat: ['Worker heartbeat is stale or missing.', true, 'workers.reconcile', false],
    legacy_identity_incomplete: ['Worker has an old one-shot identity and must be reinstalled or re-registered with v2 identity.', false, 'install or restart persistent supervisor on host', true],
    legacy_project_specific_worker: ['Project-specific one-shot worker is quarantined from generic routing.', true, 'workers.reconcile', false],
    protocol_version_mismatch: ['Worker protocol version is incompatible.', false, 'update worker runner bundle, then restart supervisor', true],
    retired_worker: ['Worker is retired.', false, 'register a fresh worker installation', true],
    api_key_capability_unavailable: ['API-key backed Codex capability probe failed.', true, 'workers.provision or repair the cloud Codex auth probe', false],
  };
  const item = map[route.code] || [route.reason || 'Worker is not routable.', false, 'workers.inspect', false];
  return {code: route.code, explanation: item[0], evidence: {workerId: worker.workerId || '', reason: route.reason}, automaticallyRepairable: item[1], safeRecommendedOperation: item[2], localPhysicalInterventionRequired: item[3]};
}



function cloudProvisioningDefaults(args = {}, caller = {}) {
  const requested = Number(args.requestedSessions || args.sessionSlots || 1) || 1;
  const requestedSessions = Math.max(1, Math.min(requested, 20));
  const machineImageId = slug(args.machineImageId || args.imageId || COMMAND_CENTER_DEFAULT_CLOUD_MACHINE_IMAGE_ID, COMMAND_CENTER_DEFAULT_CLOUD_MACHINE_IMAGE_ID);
  const region = safeText(args.region, 80) || COMMAND_CENTER_DEFAULT_CLOUD_REGION;
  const projectId = safeText(args.cloudProjectId || args.projectId || COMMAND_CENTER_DEFAULT_CLOUD_PROJECT, 120) || COMMAND_CENTER_DEFAULT_CLOUD_PROJECT;
  const nonce = safeText(args.provisioningNonce || args.idempotencyKey || randomUUID(), 160);
  const workerId = slug(args.workerId || `cloud-debian-codex-${hashText(ownerKeyFromCaller(caller) + ':' + machineImageId + ':' + nonce, 10)}`, 'cloud-debian-codex');
  const jobName = slug(args.jobName || workerId, 'command-center-debian-worker').slice(0, 63).replace(/-+$/g, '') || 'command-center-debian-worker';
  const secretName = safeText(args.workerTokenSecret || `COMMAND_CENTER_WORKER_TOKEN_${workerId.toUpperCase().replace(/[^A-Z0-9]+/g, '_')}`, 240);
  return {
    provisioningId: slug(args.provisioningId || `prov-${hashText(ownerKeyFromCaller(caller) + ':' + workerId + ':' + nonce, 24)}`, 'prov'),
    workerId,
    workerInstallationId: safeText(args.workerInstallationId, 180) || `winst_cloud_${hashText(ownerKeyFromCaller(caller) + ':' + workerId, 24)}`,
    workerInstanceId: safeText(args.workerInstanceId, 180) || `winstproc_cloud_pending_${hashText(workerId + ':' + Date.now() + ':' + randomUUID(), 18)}`,
    machineImageId,
    projectId,
    region,
    jobName,
    image: safeText(args.image, 1200) || COMMAND_CENTER_DEFAULT_CLOUD_WORKER_IMAGE,
    requestedSessions,
    capabilities: safeList(args.capabilities, 80, 120).length ? safeList(args.capabilities, 80, 120) : ['codex', 'cloud-run-debian', 'durable-session', 'prepared-workspace', 'github', 'node', 'python', 'gcs-workspace-snapshot', 'one-shot-worker'],
    openAiApiKeySecret: safeText(args.openAiApiKeySecret || 'OPENAI_API_KEY', 240),
    codexAccessTokenSecret: safeText(args.codexAccessTokenSecret || 'CODEX_ACCESS_TOKEN', 240),
    githubTokenSecret: safeText(args.githubTokenSecret || 'GITHUB_TOKEN', 240),
    workerTokenSecret: secretName,
    snapshotBucket: safeText(args.snapshotBucket || process.env.COMMAND_CENTER_WORKSPACE_SNAPSHOT_BUCKET || `${projectId}-command-center-worker-sessions`, 240),
    serviceAccount: safeText(args.serviceAccount, 320),
  };
}

function assertCloudProvisioningRequest(request = {}) {
  const location = safeText(request.location || request.targetLocation || request.workerId, 240).toLowerCase();
  if (location.includes('termux') || location.includes('phone') || location.includes('android') || location.includes('local')) {
    const err = new Error('workers.provision is cloud-only; Termux, phone, Android, and local hosts are forbidden for generic Codex capacity.');
    err.status = 400;
    err.code = 'local_host_forbidden';
    throw err;
  }
}

function cloudMachineImageRecord(args = {}, caller = {}) {
  return cleanMachineImage({
    imageId: args.machineImageId || COMMAND_CENTER_DEFAULT_CLOUD_MACHINE_IMAGE_ID,
    name: 'Cloud Debian Codex',
    imageKind: 'cloud-run-debian-codex',
    version: safeText(args.version, 120) || 'debian-codex-latest',
    digest: safeText(args.digest || args.image, 160),
    status: 'available',
    capabilities: ['codex', 'cloud-run-debian', 'durable-session', 'prepared-workspace', 'github', 'node', 'python', 'gcs-workspace-snapshot', 'one-shot-worker'],
    toolchains: ['debian', 'codex-cli', 'node', 'python'],
    dependencyBundleRefs: [safeText(args.image, 1200) || COMMAND_CENTER_DEFAULT_CLOUD_WORKER_IMAGE],
    warmCacheRefs: safeList(args.warmCacheRefs, 20, 1000),
    materializationModes: ['cloud_run_job_image'],
    hotPathInstallAllowed: false,
    estimatedColdStartMs: Number(args.estimatedColdStartMs || 60000) || 60000,
    estimatedHotStartMs: Number(args.estimatedHotStartMs || 5000) || 5000,
    provenance: {source: 'workers.provision', noSecrets: true},
  }, caller);
}

function cloudWorkerRecordFromProvisioning(request = {}, caller = {}) {
  const nowMs = Date.now();
  const defaults = cloudProvisioningDefaults(request, caller);
  const image = cloudMachineImageRecord(defaults, caller);
  return cleanWorker({
    workerId: defaults.workerId,
    workerInstallationId: defaults.workerInstallationId,
    workerInstanceId: defaults.workerInstanceId,
    runnerVersion: COMMAND_CENTER_MIN_RUNNER_VERSION,
    protocolVersion: COMMAND_CENTER_WORKER_PROTOCOL_VERSION,
    engine: 'codex',
    location: 'gcp-cloud-run-job',
    health: 'healthy',
    registryHealth: 'healthy',
    registryRoutable: true,
    routable: true,
    simulated: false,
    capabilities: defaults.capabilities,
    limits: {concurrentJobs: Math.max(1, defaults.requestedSessions), concurrentActivations: Math.max(1, defaults.requestedSessions)},
    activation: {mode: 'cloud_run_job', verifiedAtMs: nowMs},
    runtime: {kind: 'debian-container', compute: 'cloud-run-job', deviceIndependent: true, codexAuth: 'api_key', apiKeyCapabilityProbe: safeObject(request.apiKeyCapabilityProbe || {status: 'required_before_routing', failureKind: 'probe_not_recorded'})},
    cloudRunJob: {projectId: defaults.projectId, region: defaults.region, jobName: defaults.jobName, image: defaults.image},
    sessionPolicy: {durable: true, snapshotStore: 'gcs', snapshotBucket: defaults.snapshotBucket, restoreStrategies: ['gcs_snapshot', 'git_clean_clone', 'empty_workspace', 'artifact_bundle']},
    machineImages: [image],
    availableImageIds: [defaults.machineImageId],
    materializedImageIds: [defaults.machineImageId],
    maxConcurrentSessions: defaults.requestedSessions,
    activeSessionIds: [],
    sessionIsolationModes: ['session'],
    canMaterializeImages: false,
    cacheState: {hotStartReady: true, hotPathInstallAllowed: false, machineImageId: defaults.machineImageId},
    ownerKey: ownerKeyFromCaller(caller),
    createdBy: caller.actor,
    updatedBy: caller.actor,
    createdAtMs: nowMs,
    updatedAtMs: nowMs,
  });
}

function provisioningRecommendation(args = {}, candidates = []) {
  const policy = cleanSessionPolicy(args);
  const excludedLocal = candidates.filter((candidate) => candidate.reasonCode === 'local_host_excluded').map((candidate) => candidate.workerId);
  return {
    recommendedOperation: 'workers.provision',
    cloudOnly: true,
    localHostExcludedByDefault: true,
    automaticallyRepairable: true,
    reason: 'No eligible cloud worker capacity is currently routable; provision another Cloud Run Debian Codex worker instead of using Termux or a phone.',
    suggestedArgs: {
      idempotencyKey: `provision-${hashText(JSON.stringify({policy, requirements: args.workerRequirements || args.requirements || []}), 16)}`,
      machineImageId: policy.machineImageId || COMMAND_CENTER_DEFAULT_CLOUD_MACHINE_IMAGE_ID,
      requestedSessions: 1,
    },
    excludedLocalWorkerIds: excludedLocal,
  };
}

async function createOrUpdateSecretVersion(projectId, secretId, value) {
  const client = new SecretManagerServiceClient();
  const parent = `projects/${projectId}`;
  const name = `${parent}/secrets/${secretId}`;
  try {
    await client.getSecret({name});
  } catch (err) {
    const code = Number(err && err.code || 0);
    if (code !== 5) throw err;
    await client.createSecret({parent, secretId, secret: {replication: {automatic: {}}}});
  }
  const [version] = await client.addSecretVersion({parent: name, payload: {data: Buffer.from(value, 'utf8')}});
  return safeText(version.name, 500);
}


async function googleProjectNumber(projectId) {
  const explicit = safeText(process.env.GCLOUD_PROJECT_NUMBER || process.env.GOOGLE_CLOUD_PROJECT_NUMBER, 80);
  if (explicit) return explicit;
  const token = await googleCloudAccessToken();
  const response = await fetch(`https://cloudresourcemanager.googleapis.com/v1/projects/${projectId}`, {headers: {authorization: `Bearer ${token}`}});
  const text = await response.text();
  let payload = {};
  try { payload = text ? JSON.parse(text) : {}; } catch (_err) { payload = {message: text.slice(0, 1000)}; }
  if (!response.ok || !payload.projectNumber) throw new Error(payload.error && payload.error.message || payload.message || `Project lookup failed: HTTP ${response.status}`);
  return String(payload.projectNumber);
}

async function cloudWorkerServiceAccount(request = {}) {
  const explicit = safeText(request.serviceAccount || process.env.COMMAND_CENTER_WORKER_SERVICE_ACCOUNT, 320);
  if (explicit) return explicit;
  const projectNumber = await googleProjectNumber(request.projectId || COMMAND_CENTER_DEFAULT_CLOUD_PROJECT);
  return `${projectNumber}-compute@developer.gserviceaccount.com`;
}

async function secretExists(projectId, secretId) {
  const client = new SecretManagerServiceClient();
  try {
    await client.getSecret({name: `projects/${projectId}/secrets/${secretId}`});
    return true;
  } catch (err) {
    if (Number(err && err.code || 0) === 5) return false;
    throw err;
  }
}

async function grantSecretAccessor(projectId, secretId, serviceAccount) {
  if (!await secretExists(projectId, secretId)) return {ok: false, code: 'secret_missing', secretId, serviceAccount, diagnostic: `Secret ${secretId} does not exist in ${projectId}.`};
  const client = new SecretManagerServiceClient();
  const resource = `projects/${projectId}/secrets/${secretId}`;
  let policy = {};
  try {
    [policy] = await client.getIamPolicy({resource});
  } catch (err) {
    return {ok: false, code: 'secret_iam_read_failed', secretId, serviceAccount, diagnostic: safeText(err && err.message, 1000) || 'Secret IAM read failed.'};
  }
  const member = `serviceAccount:${serviceAccount}`;
  const bindings = Array.isArray(policy.bindings) ? policy.bindings : [];
  let binding = bindings.find((item) => item.role === 'roles/secretmanager.secretAccessor');
  if (!binding) {
    binding = {role: 'roles/secretmanager.secretAccessor', members: []};
    bindings.push(binding);
  }
  binding.members = Array.from(new Set([...(Array.isArray(binding.members) ? binding.members : []), member])).sort();
  try {
    await client.setIamPolicy({resource, policy: {...policy, bindings}});
  } catch (err) {
    return {ok: false, code: 'secret_iam_binding_failed', secretId, serviceAccount, diagnostic: safeText(err && err.message, 1000) || 'Secret IAM write failed.'};
  }
  return {ok: true, code: 'secret_accessor_granted', secretId, serviceAccount};
}

async function ensureWorkerSecretAccess(request = {}) {
  const serviceAccount = await cloudWorkerServiceAccount(request);
  const secretIds = Array.from(new Set([request.workerTokenSecret, request.openAiApiKeySecret, request.codexAccessTokenSecret, request.githubTokenSecret].map((item) => safeText(item, 240)).filter(Boolean)));
  const grants = [];
  for (const secretId of secretIds) grants.push(await grantSecretAccessor(request.projectId, secretId, serviceAccount));
  const hardFailed = grants.find((grant) => grant.ok === false && grant.code !== 'secret_iam_binding_failed') || null;
  const unverified = grants.filter((grant) => grant.ok === false && grant.code === 'secret_iam_binding_failed');
  return {ok: !hardFailed, serviceAccount, grants, failed: hardFailed || unverified[0] || null, unverifiedSecretIamBindings: unverified, warningCode: unverified.length ? 'secret_iam_binding_unverified' : ''};
}

function cloudRunJobReadyDiagnostic(jobPayload = {}) {
  const conditions = Array.isArray(safeObject(jobPayload).conditions) ? jobPayload.conditions : (Array.isArray(safeObject(jobPayload.status).conditions) ? jobPayload.status.conditions : []);
  const ready = conditions.find((condition) => condition.type === 'Ready') || null;
  if (!ready) return {ready: false, code: 'cloud_run_job_ready_unknown', conditions};
  if (String(ready.status) === 'True') return {ready: true, code: 'cloud_run_job_ready', conditions};
  return {ready: false, code: safeText(ready.reason, 120) || 'cloud_run_job_not_ready', message: safeText(ready.message, 2000), conditions};
}

async function getCloudRunJob(request = {}) {
  const token = await googleCloudAccessToken();
  const parent = `projects/${request.projectId}/locations/${request.region}`;
  const jobPath = `${parent}/jobs/${request.jobName}`;
  const response = await fetch(`https://run.googleapis.com/v2/${jobPath}`, {headers: {authorization: `Bearer ${token}`}});
  const text = await response.text();
  let payload = {};
  try { payload = text ? JSON.parse(text) : {}; } catch (_err) { payload = {message: text.slice(0, 1000)}; }
  return {ok: response.ok, status: response.status, payload, jobPath};
}

async function deleteCloudRunJob(request = {}) {
  const token = await googleCloudAccessToken();
  const parent = `projects/${request.projectId}/locations/${request.region}`;
  const jobPath = `${parent}/jobs/${request.jobName}`;
  const response = await fetch(`https://run.googleapis.com/v2/${jobPath}`, {method: 'DELETE', headers: {authorization: `Bearer ${token}`}});
  const text = await response.text();
  let payload = {};
  try { payload = text ? JSON.parse(text) : {}; } catch (_err) { payload = {message: text.slice(0, 1000)}; }
  if (response.ok || response.status === 404) return {ok: true, status: response.status, payload, jobPath};
  return {ok: false, status: response.status, payload, jobPath, diagnostic: payload.error && payload.error.message || payload.message || `Cloud Run Job delete failed: HTTP ${response.status}`};
}

async function waitForCloudRunJobDeleted(request = {}, timeoutMs = 45000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() <= deadline) {
    last = await getCloudRunJob(request);
    if (last.status === 404) return {ok: true, code: 'cloud_run_job_deleted', jobPath: last.jobPath};
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
  return {ok: false, code: 'cloud_run_job_delete_timeout', jobPath: last && last.jobPath || '', diagnostic: 'Timed out waiting for Cloud Run Job deletion.'};
}

async function createCloudRunJob(request = {}, requestBody = {}) {
  const token = await googleCloudAccessToken();
  const parent = `projects/${request.projectId}/locations/${request.region}`;
  const createResponse = await fetch(`https://run.googleapis.com/v2/${parent}/jobs?jobId=${encodeURIComponent(request.jobName)}`, {
    method: 'POST',
    headers: {authorization: `Bearer ${token}`, 'content-type': 'application/json'},
    body: JSON.stringify(requestBody),
  });
  const text = await createResponse.text();
  let payload = {};
  try { payload = text ? JSON.parse(text) : {}; } catch (_err) { payload = {message: text.slice(0, 1000)}; }
  if (!createResponse.ok) return {ok: false, code: 'cloud_run_job_create_failed', diagnostic: payload.error && payload.error.message || payload.message || `Cloud Run Job create failed: HTTP ${createResponse.status}`};
  return {ok: true, operation: safeText(payload.name, 500), payload};
}

async function waitForCloudRunJobReady(request = {}, timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs;
  let last = null;
  while (Date.now() <= deadline) {
    last = await getCloudRunJob(request);
    if (!last.ok) return {ok: false, code: 'cloud_run_job_lookup_failed', diagnostic: last.payload.error && last.payload.error.message || last.payload.message || `Cloud Run Job lookup failed: HTTP ${last.status}`, jobPath: last.jobPath};
    const ready = cloudRunJobReadyDiagnostic(last.payload);
    if (ready.ready) return {ok: true, code: 'cloud_run_job_ready', jobPath: last.jobPath, readiness: ready};
    await new Promise((resolve) => setTimeout(resolve, 5000));
  }
  const ready = last && last.ok ? cloudRunJobReadyDiagnostic(last.payload) : {ready: false, code: 'cloud_run_job_ready_timeout'};
  return {ok: false, code: 'cloud_run_job_not_ready', jobPath: last && last.jobPath || '', readiness: ready, diagnostic: ready.message || ready.code};
}

async function ensureCloudRunJob(request = {}) {
  const token = await googleCloudAccessToken();
  const parent = `projects/${request.projectId}/locations/${request.region}`;
  const jobPath = `${parent}/jobs/${request.jobName}`;
  const serviceAccount = await cloudWorkerServiceAccount(request);
  const containerEnv = [
    {name: 'COMMAND_CENTER_BASE', value: COMMAND_CENTER_PUBLIC_BASE},
    {name: 'COMMAND_CENTER_WORKSPACE_SNAPSHOT_BUCKET', value: request.snapshotBucket},
    {name: 'COMMAND_CENTER_WORKER_TOKEN', valueSource: {secretKeyRef: {secret: request.workerTokenSecret, version: 'latest'}}},
    {name: 'OPENAI_API_KEY', valueSource: {secretKeyRef: {secret: request.openAiApiKeySecret, version: 'latest'}}},
    {name: 'CODEX_ACCESS_TOKEN', valueSource: {secretKeyRef: {secret: request.codexAccessTokenSecret, version: 'latest'}}},
    {name: 'GH_TOKEN', valueSource: {secretKeyRef: {secret: request.githubTokenSecret, version: 'latest'}}},
  ];
  const requestBody = {
    template: {
      template: {
        containers: [{image: request.image, env: containerEnv}],
        maxRetries: 0,
        timeout: '3600s',
        serviceAccount,
      },
    },
  };
  const access = await ensureWorkerSecretAccess({...request, serviceAccount});
  if (!access.ok) return {ok: false, code: access.failed.code, diagnostic: access.failed.diagnostic, secretAccess: access, serviceAccount};
  const existing = await getCloudRunJob(request);
  let operation = null;
  if (existing.ok) {
    const patchResponse = await fetch(`https://run.googleapis.com/v2/${jobPath}?updateMask=template.template.containers,template.template.maxRetries,template.template.timeout,template.template.serviceAccount`, {
      method: 'PATCH',
      headers: {authorization: `Bearer ${token}`, 'content-type': 'application/json'},
      body: JSON.stringify(requestBody),
    });
    const patchText = await patchResponse.text();
    let patchPayload = {};
    try { patchPayload = patchText ? JSON.parse(patchText) : {}; } catch (_err) { patchPayload = {message: patchText.slice(0, 1000)}; }
    if (patchResponse.ok) {
      operation = safeText(patchPayload.name, 500);
    } else {
      const patchDiagnostic = patchPayload.error && patchPayload.error.message || patchPayload.message || `Cloud Run Job update failed: HTTP ${patchResponse.status}`;
      const deleted = await deleteCloudRunJob(request);
      if (!deleted.ok) return {ok: false, code: 'cloud_run_job_update_failed', diagnostic: `${patchDiagnostic}; delete fallback failed: ${deleted.diagnostic}`, secretAccess: access, serviceAccount};
      const gone = await waitForCloudRunJobDeleted(request, 45000);
      if (!gone.ok) return {ok: false, code: gone.code, diagnostic: `${patchDiagnostic}; ${gone.diagnostic}`, secretAccess: access, serviceAccount};
      const created = await createCloudRunJob(request, requestBody);
      if (!created.ok) return {ok: false, code: created.code, diagnostic: `${patchDiagnostic}; recreate fallback failed: ${created.diagnostic}`, secretAccess: access, serviceAccount};
      operation = created.operation;
    }
  } else if (existing.status === 404) {
    const created = await createCloudRunJob(request, requestBody);
    if (!created.ok) return {ok: false, code: created.code, diagnostic: created.diagnostic, secretAccess: access, serviceAccount};
    operation = created.operation;
  } else {
    return {ok: false, code: 'cloud_run_job_lookup_failed', diagnostic: existing.payload.error && existing.payload.error.message || existing.payload.message || `Cloud Run Job lookup failed: HTTP ${existing.status}`, secretAccess: access, serviceAccount};
  }
  const readiness = await waitForCloudRunJobReady(request, 45000);
  if (!readiness.ok) return {ok: false, code: readiness.code, diagnostic: readiness.diagnostic, jobName: request.jobName, jobPath, operation, readiness, secretAccess: access, serviceAccount};
  return {ok: true, status: existing.ok ? 'job_updated' : 'job_created', jobName: request.jobName, jobPath, operation, readiness, secretAccess: access, serviceAccount};
}

async function provisionCloudWorker(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'workers.provision', async () => {
    assertCloudProvisioningRequest(args);
    const nowMs = Date.now();
    const dryRun = args.dryRun === true;
    const request = cloudProvisioningDefaults(args, caller);
    const workerToken = `ccw_${randomUUID()}_${hashText(request.workerId + ':' + nowMs, 18)}`;
    const tokenHash = tokenDigest(workerToken);
    const image = cloudMachineImageRecord(request, caller);
    const worker = cloudWorkerRecordFromProvisioning(request, caller);
    const provisioning = {
      ...request,
      dryRun,
      status: dryRun ? 'requested' : 'requested',
      ownerKey: ownerKeyFromCaller(caller),
      requestedBy: caller.actor,
      createdAtMs: nowMs,
      updatedAtMs: nowMs,
      workerTokenSecretRef: `secretmanager://${request.projectId}/${request.workerTokenSecret}/latest`,
      workerTokenHash: tokenHash,
      workerTokenPlaintextStored: false,
      localHostsForbidden: true,
      phoneForbidden: true,
      termuxForbidden: true,
      evidence: [],
    };
    if (dryRun) return {ok: true, dryRun: true, provisioning, worker, image, next: 'Call workers.provision with dryRun=false to create the Secret Manager token, Cloud Run Job, worker record, and image record.'};
    let secretVersion = '';
    let cloudRun = null;
    try {
      secretVersion = await createOrUpdateSecretVersion(request.projectId, request.workerTokenSecret, workerToken);
      provisioning.status = 'secrets_ready';
      provisioning.workerTokenSecretVersion = secretVersion;
    } catch (err) {
      provisioning.status = 'blocked';
      provisioning.failure = {code: 'secret_publication_failed', message: safeText(err && err.message, 1000)};
      await collection(admin, COMMAND_CENTER_COLLECTIONS.provisioningRequests).doc(provisioning.provisioningId).set(provisioning, {merge: true});
      return {ok: false, code: 'secret_publication_failed', provisioning, explanation: 'Command Center could not publish the worker token to Secret Manager. No token plaintext is returned.'};
    }
    cloudRun = await ensureCloudRunJob(request);
    if (!cloudRun.ok) {
      provisioning.status = 'blocked';
      provisioning.failure = {code: cloudRun.code, message: cloudRun.diagnostic};
      await collection(admin, COMMAND_CENTER_COLLECTIONS.provisioningRequests).doc(provisioning.provisioningId).set(provisioning, {merge: true});
      return {ok: false, code: cloudRun.code, provisioning, cloudRun, explanation: 'Command Center created the nonsecret provisioning record and worker token secret, but Cloud Run Job creation failed.'};
    }
    provisioning.status = cloudRun.status === 'job_exists' ? 'job_created' : 'job_created';
    provisioning.cloudRun = cloudRun;
    await collection(admin, COMMAND_CENTER_COLLECTIONS.machineImages).doc(image.imageId).set(image, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(worker.workerId).set(worker, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.workerTokens).doc(tokenHash).set({workerId: worker.workerId, ownerKey: ownerKeyFromCaller(caller), createdBy: caller.actor, createdAtMs: nowMs, expiresAtMs: nowMs + 90 * 24 * 60 * 60 * 1000, authKind: 'command_center_worker_token', secretRef: provisioning.workerTokenSecretRef}, {merge: false});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.provisioningRequests).doc(provisioning.provisioningId).set(provisioning, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.events).doc(`provision_${hashText(provisioning.provisioningId + ':' + nowMs, 24)}`).set({eventId: `provision_${hashText(provisioning.provisioningId + ':' + nowMs, 24)}`, type: 'cloud_worker_provisioned', actor: caller.actor, ownerKey: ownerKeyFromCaller(caller), createdAtMs: nowMs, summary: `Provisioned cloud worker ${worker.workerId}.`, data: {provisioningId: provisioning.provisioningId, workerId: worker.workerId, machineImageId: image.imageId, cloudRunJob: worker.cloudRunJob, noSecretPlaintextReturned: true}});
    return {ok: true, provisioning, worker, image, cloudRun, next: 'Run workers.wake to prove heartbeat/API-key capability before leasing Codex work.'};
  });
}

async function inspectProvisioning(admin, caller, args = {}) {
  const provisioningId = slug(args.provisioningId || '', '');
  if (provisioningId) {
    const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.provisioningRequests).doc(provisioningId).get();
    if (!snap.exists) return {found: false, provisioningId};
    const data = snap.data() || {};
    assertOwnerAccess(data, caller, 'Command Center provisioning request');
    return {found: true, provisioning: data};
  }
  const snap = await queryOwnedCollection(admin, COMMAND_CENTER_COLLECTIONS.provisioningRequests, caller).limit(Math.max(1, Math.min(Number(args.limit) || 20, 50))).get();
  const requests = [];
  snap.forEach((doc) => requests.push({provisioningId: doc.id, ...(doc.data() || {})}));
  requests.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  return {requests};
}

async function reconcileProvisioning(admin, caller, args = {}) {
  const dryRun = args.dryRun !== false;
  const inspected = await inspectProvisioning(admin, caller, {limit: Number(args.limit || 20)});
  const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
  const actions = [];
  for (const request of inspected.requests || []) {
    const worker = workers.find((item) => item.workerId === request.workerId) || null;
    const route = worker ? workerRoutabilityDiagnostic(worker) : {routable: false, code: 'worker_record_missing', reason: 'worker record missing'};
    if (!worker) {
      actions.push({type: 'mark_blocked', provisioningId: request.provisioningId, reasonCode: 'worker_record_missing'});
      continue;
    }
    if (route.routable) {
      actions.push({type: 'mark_routable', provisioningId: request.provisioningId, workerId: worker.workerId});
      continue;
    }
    const repairRequest = cloudProvisioningDefaults({...request, githubTokenSecret: request.githubTokenSecret === 'GH_TOKEN' ? 'GITHUB_TOKEN' : (request.githubTokenSecret || 'GITHUB_TOKEN'), snapshotBucket: request.snapshotBucket === `${request.projectId}-command-center-workspaces` ? `${request.projectId}-command-center-worker-sessions` : (request.snapshotBucket || `${request.projectId}-command-center-worker-sessions`)}, caller);
    actions.push({type: 'repair_cloud_run_job', provisioningId: request.provisioningId, workerId: worker.workerId, reasonCode: route.code, dryRun});
    if (!dryRun) {
      const cloudRun = await ensureCloudRunJob(repairRequest);
      const status = cloudRun.ok ? 'job_created' : 'blocked';
      await collection(admin, COMMAND_CENTER_COLLECTIONS.provisioningRequests).doc(request.provisioningId).set({status, updatedAtMs: Date.now(), githubTokenSecret: repairRequest.githubTokenSecret, snapshotBucket: repairRequest.snapshotBucket, cloudRun, failure: cloudRun.ok ? null : {code: cloudRun.code, message: cloudRun.diagnostic}}, {merge: true});
      actions[actions.length - 1].cloudRun = cloudRun;
    }
  }
  if (!dryRun) {
    const batch = admin.firestore().batch();
    for (const action of actions.slice(0, 100)) {
      if (action.type === 'mark_routable') batch.set(collection(admin, COMMAND_CENTER_COLLECTIONS.provisioningRequests).doc(action.provisioningId), {status: 'routable', updatedAtMs: Date.now()}, {merge: true});
      if (action.type === 'mark_blocked') batch.set(collection(admin, COMMAND_CENTER_COLLECTIONS.provisioningRequests).doc(action.provisioningId), {status: 'blocked', updatedAtMs: Date.now(), failure: {code: action.reasonCode}}, {merge: true});
    }
    if (actions.some((action) => action.type === 'mark_routable' || action.type === 'mark_blocked')) await batch.commit();
  }
  return {ok: true, dryRun, actions};
}

async function machineImageRecords(admin, caller) {
  const snap = await queryOwnedCollection(admin, COMMAND_CENTER_COLLECTIONS.machineImages, caller).limit(500).get();
  const images = [];
  snap.forEach((doc) => images.push(cleanMachineImage({imageId: doc.id, ...(doc.data() || {})}, caller)));
  return images;
}

async function registerMachineImage(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'machine_images.register', async () => {
    const image = cleanMachineImage(args, caller);
    const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.machineImages).doc(image.imageId);
    const existing = await ref.get();
    if (existing.exists) assertOwnerAccess(existing.data() || {}, caller, 'Command Center machine image');
    await ref.set({...image, createdAtMs: existing.exists ? (Number((existing.data() || {}).createdAtMs || 0) || image.createdAtMs) : image.createdAtMs}, {merge: true});
    return {ok: true, image, created: !existing.exists};
  });
}

async function listMachineImages(admin, caller, args = {}) {
  let images = await machineImageRecords(admin, caller);
  const status = safeText(args.status, 80);
  if (status) images = images.filter((image) => image.status === status);
  const capability = safeText(args.capability, 120).toLowerCase();
  if (capability) images = images.filter((image) => safeList(image.capabilities, 120, 120).map((cap) => cap.toLowerCase()).includes(capability));
  return {images, summary: {total: images.length, available: images.filter((image) => image.status === 'available').length}};
}

async function inspectMachineImage(admin, caller, args = {}) {
  const imageId = slug(args.imageId || args.machineImageId, '');
  if (!imageId) {
    const err = new Error('imageId is required.');
    err.status = 400;
    throw err;
  }
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.machineImages).doc(imageId).get();
  if (!snap.exists) return {imageId, found: false};
  const image = cleanMachineImage({imageId, ...(snap.data() || {})}, caller);
  assertOwnerAccess(image, caller, 'Command Center machine image');
  const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
  const hosts = workers.map((worker) => ({workerId: worker.workerId, ...workerImagePolicyDiagnostic(worker, {machineImageId: imageId}, [image])}));
  return {imageId, found: true, image, hosts};
}

async function listCodexSessions(admin, caller, args = {}) {
  const snap = await queryOwnedCollection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions, caller).limit(500).get();
  let sessions = [];
  snap.forEach((doc) => sessions.push(cleanAgentSession({sessionId: doc.id, ...(doc.data() || {})}, {}, caller)));
  const status = safeText(args.status, 80);
  if (status) sessions = sessions.filter((session) => session.status === status);
  const machineImageId = slug(args.machineImageId || '', '');
  if (machineImageId) sessions = sessions.filter((session) => session.machineImageId === machineImageId);
  const hostInstallationId = safeText(args.hostInstallationId || args.workerInstallationId, 180);
  if (hostInstallationId) sessions = sessions.filter((session) => session.hostInstallationId === hostInstallationId);
  return {sessions, summary: {total: sessions.length, idle: sessions.filter((session) => session.status === 'idle').length, running: sessions.filter((session) => session.status === 'running').length, recoverable: sessions.filter((session) => session.status === 'recoverable').length}};
}

async function inspectCodexSession(admin, caller, args = {}) {
  const sessionId = cleanSessionId(args.sessionId);
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(sessionId).get();
  if (!snap.exists) return {sessionId, found: false};
  const session = cleanAgentSession({sessionId, ...(snap.data() || {})}, {}, caller);
  assertOwnerAccess(session, caller, 'Command Center Codex session');
  const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
  const host = workers.find((worker) => worker.workerInstallationId === session.hostInstallationId || worker.workerId === session.workerId) || null;
  return {sessionId, found: true, session, host: host ? compactWorkerCensus(host, 0) : null};
}

async function createCodexSession(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'codex_sessions.create', async () => {
    const policy = cleanSessionPolicy(args);
    const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
    const images = await machineImageRecords(admin, caller);
    const requirements = safeList(args.workerRequirements || args.requiredWorkerCapabilities, 40, 120);
    const counts = await activeLeaseCountsByWorker(admin);
    const candidates = workers.map((worker) => explainWorkerCandidate(worker, requirements, counts.get(worker.workerId) || 0, {sessionPolicy: policy, machineImages: images, allowLocalHost: args.allowLocalHost === true}));
    let selected = candidates.find((candidate) => candidate.included && candidate.imagePolicy.ok && candidate.sessionDiagnostic.ok) || null;
    let provisioning = null;
    if (!selected && args.autoProvision !== false) {
      provisioning = await provisionCloudWorker(admin, caller, {...args, idempotencyKey: `${args.idempotencyKey}:auto-provision`, machineImageId: policy.machineImageId || args.machineImageId || COMMAND_CENTER_DEFAULT_CLOUD_MACHINE_IMAGE_ID, requestedSessions: 1});
      const refreshedWorkers = recordsVisibleToCaller(await workerRecords(admin), caller);
      const refreshedImages = await machineImageRecords(admin, caller);
      const refreshedCounts = await activeLeaseCountsByWorker(admin);
      const refreshedCandidates = refreshedWorkers.map((worker) => explainWorkerCandidate(worker, requirements, refreshedCounts.get(worker.workerId) || 0, {sessionPolicy: policy, machineImages: refreshedImages, allowLocalHost: args.allowLocalHost === true}));
      selected = refreshedCandidates.find((candidate) => candidate.included && candidate.imagePolicy.ok && candidate.sessionDiagnostic.ok) || null;
      if (!selected) return {ok: false, status: 'provisioning_started', code: 'cloud_capacity_not_yet_routable', policy, candidates: refreshedCandidates, provisioning, explanation: 'Command Center requested cloud capacity, but it is not yet routable. Wake/probe the provisioned Cloud Run worker before leasing Codex work.'};
    }
    if (!selected) return {ok: false, status: 'red', code: 'no_cloud_session_host', policy, candidates, provisioningRecommendation: provisioningRecommendation({...args, sessionPolicy: policy}, candidates), explanation: 'No routable cloud host has the requested materialized machine image and isolated session capacity.'};
    const worker = workers.find((item) => item.workerId === selected.workerId) || {};
    const session = cleanAgentSession({
      ...args,
      sessionId: args.sessionId || `session_${slug(selected.workerId, 'host')}_${hashText(`${selected.workerInstallationId}:${Date.now()}:${randomUUID()}`, 18)}`,
      machineImageId: policy.machineImageId || selected.imagePolicy.selectedMachineImageId,
      hostInstallationId: selected.workerInstallationId,
      workerId: selected.workerId,
      workerInstanceId: selected.workerInstanceId,
      sessionSlotId: `slot_${hashText(`${selected.workerInstallationId}:${Date.now()}:${randomUUID()}`, 18)}`,
      isolationMode: policy.isolationMode,
      codexAuthMode: safeObject(worker.runtime).codexAuth || safeObject(worker.runtime).authMode,
      status: 'allocated',
      cacheState: workerMachineImageState(worker).cacheState,
      hotStartMs: Number((images.find((image) => image.imageId === (policy.machineImageId || selected.imagePolicy.selectedMachineImageId)) || {}).estimatedHotStartMs || 0) || 0,
    }, {}, caller);
    await collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(session.sessionId).set(session, {merge: true});
    const activeSessionIds = Array.from(new Set([...workerMachineImageState(worker).activeSessionIds, session.sessionId]));
    await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(selected.workerId).set({activeSessionIds, updatedAtMs: Date.now()}, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.events).doc(`session_${hashText(session.sessionId + Date.now(), 24)}`).set({eventId: `session_${hashText(session.sessionId + Date.now(), 24)}`, type: 'codex_session_allocated', actor: caller.actor, summary: `Allocated Codex session ${session.sessionId} on ${selected.workerId}.`, ownerKey: ownerKeyFromCaller(caller), createdAtMs: Date.now(), data: {sessionId: session.sessionId, workerId: selected.workerId, workerInstallationId: selected.workerInstallationId, machineImageId: session.machineImageId}});
    return {ok: true, session, selectedHost: {...selected, reservedActiveSessionIds: activeSessionIds}, policy};
  });
}

async function reconcileCodexSessions(admin, caller, args = {}) {
  const dryRun = args.dryRun !== false;
  const olderThanMs = Number(args.olderThanMs || 0) || COMMAND_CENTER_RECONCILE_DEFAULT_OLDER_THAN_MS;
  const nowMs = Date.now();
  const list = await listCodexSessions(admin, caller, {});
  const actions = [];
  for (const session of list.sessions) {
    const heartbeat = Number(session.lastHeartbeatAtMs || 0) || 0;
    if (['allocated', 'running'].includes(session.status) && (!heartbeat || nowMs - heartbeat > olderThanMs)) actions.push({type: 'mark_recoverable', sessionId: session.sessionId, status: session.status, reasonCode: 'session_heartbeat_stale'});
  }
  if (!dryRun && actions.length) {
    const batch = admin.firestore().batch();
    for (const action of actions.slice(0, 100)) batch.set(collection(admin, COMMAND_CENTER_COLLECTIONS.agentSessions).doc(action.sessionId), {status: 'recoverable', updatedAtMs: nowMs, recoveryReason: action.reasonCode}, {merge: true});
    await batch.commit();
  }
  return {ok: true, dryRun, actions, applied: dryRun ? 0 : actions.length};
}

async function runMultiSessionProof(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'proof.run_multi_session', async () => {
    const policy = cleanSessionPolicy(args.sessionPolicy || args);
    const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
    const images = await machineImageRecords(admin, caller);
    const counts = await activeLeaseCountsByWorker(admin);
    const candidates = workers.map((worker) => explainWorkerCandidate(worker, ['codex', 'one-shot-worker'], counts.get(worker.workerId) || 0, {sessionPolicy: policy, machineImages: images, allowLocalHost: false}));
    const slots = [];
    for (const candidate of candidates.filter((item) => item.included && item.imagePolicy.ok && item.sessionDiagnostic.ok)) {
      const worker = workers.find((item) => item.workerId === candidate.workerId) || {};
      const state = workerMachineImageState(worker);
      for (let i = 0; i < state.sessionCapacityRemaining; i += 1) slots.push({...candidate, slotIndex: i});
    }
    const bySession = slots.slice(0, 2);
    const nonceA = safeText(args.nonceA, 120) || `session-proof-a-${randomUUID()}`;
    const nonceB = safeText(args.nonceB, 120) || `session-proof-b-${randomUUID()}`;
    if (bySession.length < 2) {
      const provisioning = [];
      if (args.autoProvision !== false) {
        const missing = 2 - bySession.length;
        for (let i = 0; i < missing; i += 1) provisioning.push(await provisionCloudWorker(admin, caller, {...args, idempotencyKey: `${args.idempotencyKey}:auto-provision:${i}`, machineImageId: policy.machineImageId || args.machineImageId || COMMAND_CENTER_DEFAULT_CLOUD_MACHINE_IMAGE_ID, requestedSessions: 1, provisioningNonce: `${nonceA}:${nonceB}:${i}`}));
        return {ok: false, status: 'provisioning_started', code: 'insufficient_cloud_sessions_provisioning_started', explanation: 'Two isolated real cloud Codex session slots are required. Command Center requested missing Cloud Run capacity and will not use Termux/phone or fabricate proof completion.', nonces: [nonceA, nonceB], candidates, selectedSlots: bySession, provisioning};
      }
      return {ok: false, status: 'red', code: 'insufficient_cloud_sessions', explanation: 'Two isolated real cloud Codex session slots are required. Command Center will not use Termux/phone, fabricate a second identity, or reinstall dependencies in the hot path.', nonces: [nonceA, nonceB], candidates, selectedSlots: bySession, provisioningRecommendation: provisioningRecommendation({...args, sessionPolicy: policy}, candidates)};
    }
    const sameHost = bySession[0].workerInstallationId === bySession[1].workerInstallationId;
    if (sameHost && policy.isolationMode !== 'session') return {ok: false, status: 'red', code: 'distinct_host_required', explanation: 'The selected slots share a host, but this policy does not permit session-level isolation.', nonces: [nonceA, nonceB], candidates, selectedSlots: bySession};
    return {ok: false, status: 'red', code: 'proof_execution_not_implemented', explanation: 'The registry proves two session slots, but Command Center has not yet enabled automatic concurrent nonce job execution for session proof. No synthetic completion was created.', nonces: [nonceA, nonceB], candidates, selectedSlots: bySession, jobsCreated: []};
  });
}

async function routingExplain(admin, caller, args = {}) {
  const requirements = safeList(args.workerRequirements || args.requiredWorkerCapabilities || args.requirements, 40, 120);
  const sessionPolicy = cleanSessionPolicy(args);
  const images = await machineImageRecords(admin, caller);
  const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
  const counts = await activeLeaseCountsByWorker(admin);
  const candidates = workers.map((worker) => explainWorkerCandidate(worker, requirements, counts.get(worker.workerId) || 0, {sessionPolicy, machineImages: images, allowLocalHost: args.allowLocalHost === true}));
  const imageCandidates = images.map((image) => ({imageId: image.imageId, status: image.status, capabilities: image.capabilities, materializedHostIds: candidates.filter((candidate) => candidate.imagePolicy && candidate.imagePolicy.selectedMachineImageId === image.imageId && candidate.imagePolicy.ok).map((candidate) => candidate.workerId)}));
  const eligibleWorkerIds = candidates.filter((item) => item.included).map((item) => item.workerId);
  return {requirements, sessionPolicy, cloudOnly: args.allowLocalHost !== true, localHostExcludedByDefault: args.allowLocalHost !== true, selectedWorkerId: (candidates.find((item) => item.included) || {}).workerId || '', candidates, imageCandidates, eligibleWorkerIds, provisioningRecommendation: eligibleWorkerIds.length ? null : provisioningRecommendation({...args, sessionPolicy}, candidates)};
}

async function reconcileWorkers(admin, caller, args = {}) {
  const dryRun = args.dryRun !== false;
  const nowMs = Date.now();
  const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
  const actions = [];
  for (const worker of workers) {
    const route = workerRoutabilityDiagnostic(worker, nowMs);
    if (route.code === 'legacy_project_specific_worker' || route.code === 'legacy_identity_incomplete') actions.push({type: 'retire_worker', workerId: worker.workerId, reasonCode: route.code, reason: route.reason});
    if (route.code === 'stale_heartbeat') actions.push({type: 'mark_stale_unroutable', workerId: worker.workerId, reasonCode: route.code, reason: route.reason});
  }
  const staleJobs = await reconcileStaleJobs(admin, caller, {dryRun, olderThanMs: Number(args.olderThanMs || 0) || COMMAND_CENTER_RECONCILE_DEFAULT_OLDER_THAN_MS, statuses: ['queued', 'leased', 'executing', 'running', 'activating'], limit: Number(args.limit || 0) || 50, idempotencyKey: args.idempotencyKey || `workers-reconcile-${nowMs}`});
  if (!dryRun) {
    const batch = admin.firestore().batch();
    for (const action of actions.slice(0, 100)) {
      const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(action.workerId);
      if (action.type === 'retire_worker') batch.set(ref, {status: 'retired', retiredAtMs: nowMs, retireReason: action.reason, registryRoutable: false, routable: false, updatedAtMs: nowMs}, {merge: true});
      else batch.set(ref, {registryRoutable: false, routable: false, health: 'stale', updatedAtMs: nowMs}, {merge: true});
    }
    if (actions.length) await batch.commit();
  }
  return {ok: true, dryRun, actions, staleJobReconciliation: staleJobs, applied: dryRun ? 0 : actions.length};
}

async function requestWorkerRestart(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'workers.request_restart', async () => {
    const workerId = safeText(args.workerId, 120);
    if (!workerId) {
      const err = new Error('workerId is required.');
      err.status = 400;
      throw err;
    }
    const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
    const worker = workers.find((item) => item.workerId === workerId) || null;
    if (!worker) return {ok: false, code: 'worker_not_found', workerId, restart: {requestRecorded: false}};
    const route = workerRoutabilityDiagnostic(worker);
    const requestId = `restart_${randomUUID()}`;
    const payload = {requestId, workerId, ownerKey: ownerKeyFromCaller(caller), requestedBy: caller.actor, reason: safeText(args.reason, 1000), createdAtMs: Date.now(), status: route.routable ? 'requested' : 'host_offline', desiredState: 'restart_supervisor'};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.events).doc(requestId).set({eventId: requestId, type: 'worker_restart_requested', actor: caller.actor, summary: route.routable ? `Restart requested for ${workerId}.` : `Restart request recorded but ${workerId} is offline.`, data: payload, ownerKey: ownerKeyFromCaller(caller), createdAtMs: Date.now()});
    if (!route.routable) return {ok: false, code: 'host_offline', workerId, requestId, restart: {requestRecorded: true, workerReceivedRequest: false, oldInstanceExited: false, newInstanceRegistered: false, newHeartbeatObserved: false}, explanation: 'The host is not currently heartbeating/routable, so cloud code cannot restart it.'};
    return {ok: false, code: 'restart_channel_unavailable', workerId, requestId, restart: {requestRecorded: true, workerReceivedRequest: false, oldInstanceExited: false, newInstanceRegistered: false, newHeartbeatObserved: false}, explanation: 'The worker protocol recorded a restart request, but this worker has not advertised a safe supervisor restart channel yet.'};
  });
}

async function runMultiWorkerProof(admin, caller, args = {}) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'proof.run_multi_worker', async () => {
    const nowMs = Date.now();
    const workers = recordsVisibleToCaller(await workerRecords(admin), caller);
    const counts = await activeLeaseCountsByWorker(admin);
    const candidates = workers.map((worker) => proofEligibleWorker(worker, counts.get(worker.workerId) || 0, nowMs));
    const byInstallation = new Map();
    for (const candidate of candidates.filter((item) => item.included)) {
      if (!candidate.workerInstallationId) continue;
      if (!byInstallation.has(candidate.workerInstallationId)) byInstallation.set(candidate.workerInstallationId, candidate);
    }
    const selected = Array.from(byInstallation.values()).slice(0, 2);
    const nonceA = safeText(args.nonceA, 120) || `proof-a-${randomUUID()}`;
    const nonceB = safeText(args.nonceB, 120) || `proof-b-${randomUUID()}`;
    if (selected.length < 2) {
      return {
        ok: false,
        status: 'red',
        code: 'insufficient_distinct_real_workers',
        explanation: 'Two distinct fresh real non-tanks worker installations are required. Command Center will not reuse one installation or count stale records.',
        nonces: [nonceA, nonceB],
        selectedWorkerIds: selected.map((item) => item.workerId),
        selectedInstallations: selected.map((item) => item.workerInstallationId),
        candidates,
        jobsCreated: [],
        proofPacket: {status: 'red', requiredDistinctInstallations: 2, foundDistinctInstallations: selected.length, excludedWorkerIds: COMMAND_CENTER_PROOF_EXCLUDED_WORKER_IDS},
      };
    }
    return {
      ok: false,
      status: 'red',
      code: 'proof_execution_not_implemented',
      explanation: 'The pool has enough candidates, but automatic two-job proof creation is not enabled until supervisor restart/activation acknowledgement is supported by both workers.',
      nonces: [nonceA, nonceB],
      selectedWorkerIds: selected.map((item) => item.workerId),
      selectedInstallations: selected.map((item) => item.workerInstallationId),
      candidates,
      jobsCreated: [],
    };
  });
}

async function recentEndToEndExecutionProbe(admin, jobSnap = null) {
  const nowMs = Date.now();
  const maxAgeMs = 24 * 60 * 60 * 1000;
  const snap = jobSnap || await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).orderBy('createdAtMs', 'desc').limit(250).get();
  const candidates = [];
  snap.forEach((doc) => {
    const job = doc.data() || {};
    const requirements = safeList(job.workerRequirements, 80, 120).map((item) => item.toLowerCase());
    const titleObjective = `${job.title || ''} ${job.objective || ''}`.toLowerCase();
    const ageMs = nowMs - (Number(job.completedAtMs || job.updatedAtMs || job.createdAtMs || 0) || 0);
    const repoFree = !safeText(job.repository, 240) && (requirements.includes('cloud-run-debian') || requirements.includes('durable-session'));
    const probeNamed = /no-op proof|harmless|repository-free|end-to-end|worker proof/.test(titleObjective);
    if (job.status === 'completed' && ageMs >= 0 && ageMs <= maxAgeMs && repoFree && probeNamed) candidates.push(job);
  });
  candidates.sort((a, b) => Number(b.completedAtMs || b.updatedAtMs || 0) - Number(a.completedAtMs || a.updatedAtMs || 0));
  for (const job of candidates.slice(0, 10)) {
    const [events, artifacts] = await Promise.all([
      listByJob(admin, COMMAND_CENTER_COLLECTIONS.events, job.jobId, 100),
      listByJob(admin, COMMAND_CENTER_COLLECTIONS.artifacts, job.jobId, 100),
    ]);
    const types = new Set(events.map((event) => event.type));
    const names = new Set(artifacts.map((artifact) => artifact.name));
    if (types.has('executor_started') && types.has('executor_finished') && (types.has('executor_stdout') || types.has('executor_heartbeat')) && names.has('command-log.jsonl') && names.has('final-report.md')) {
      return {ok: true, jobId: job.jobId, completedAtMs: Number(job.completedAtMs || job.updatedAtMs || 0), workerId: job.selectedWorkerId || '', eventTypes: Array.from(types).sort(), artifactNames: Array.from(names).sort().slice(0, 40)};
    }
  }
  return {ok: false, reason: 'no recent completed repository-free real-worker probe with executor_started, command evidence, executor_finished, command-log.jsonl, and final-report.md'};
}

function normalizeCommandCenterOperationName(value) {
  return safeText(value, 180).replace(/^command_center\./, '');
}

async function runCommandCenterOperation(admin, extra, operation, args = {}) {
  const op = normalizeCommandCenterOperationName(operation);
  assertCodexWorkerDiscoveryOperationEnabled(op);
  const caller = async () => callerFromExtra(admin, extra);
  switch (op) {
    case 'health':
    case 'system.health':
      return systemHealth(admin, await caller());
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
    case 'render.blender_glb':
      return renderBlenderGlb(admin, extra, args || {});
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
          return {jobs: [], error: 'missing_firestore_index', diagnostic: message, requiredIndex: {collectionGroup: COMMAND_CENTER_COLLECTIONS.jobs, fields: ['status ASC', 'createdAtMs DESC', '__name__ DESC']}};
        }
        throw err;
      }
    }
    case 'jobs.reconcile_stale':
      return reconcileStaleJobs(admin, await caller(), args || {});
    case 'jobs.dispatch_queued':
      return dispatchQueuedJobs(admin, await caller(), args || {});
    case 'jobs.cancel':
      return transitionJob(admin, await caller(), args || {}, 'canceled', 'jobs.cancel');
    case 'jobs.resume':
      return resumeJob(admin, await caller(), args || {});
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
    case 'workers.provision':
      return provisionCloudWorker(admin, await caller(), args || {});
    case 'provisioning.inspect':
      return inspectProvisioning(admin, await caller(), args || {});
    case 'provisioning.reconcile':
      return reconcileProvisioning(admin, await caller(), args || {});
    case 'machine_images.register':
      return registerMachineImage(admin, await caller(), args || {});
    case 'machine_images.list':
      return listMachineImages(admin, await caller(), args || {});
    case 'machine_images.inspect':
      return inspectMachineImage(admin, await caller(), args || {});
    case 'codex_sessions.create':
      return createCodexSession(admin, await caller(), args || {});
    case 'codex_sessions.list':
      return listCodexSessions(admin, await caller(), args || {});
    case 'codex_sessions.inspect':
      return inspectCodexSession(admin, await caller(), args || {});
    case 'codex_sessions.reconcile':
      return reconcileCodexSessions(admin, await caller(), args || {});
    case 'hosts.list':
      return listWorkersCensus(admin, await caller(), args || {});
    case 'hosts.inspect':
      return inspectWorker(admin, await caller(), args || {});
    case 'workers.register_oneshot':
      return registerOneShotWorker(admin, await caller(), args || {});
    case 'workers.wake':
      return wakeWorker(admin, await caller(), args || {});
    case 'workers.retire':
      return retireWorker(admin, await caller(), args || {});
    case 'workers.list':
      return listWorkersCensus(admin, await caller(), args || {});
    case 'workers.inspect':
      return inspectWorker(admin, await caller(), args || {});
    case 'routing.explain':
      return routingExplain(admin, await caller(), args || {});
    case 'workers.reconcile':
      return reconcileWorkers(admin, await caller(), args || {});
    case 'workers.request_restart':
      return requestWorkerRestart(admin, await caller(), args || {});
    case 'proof.run_multi_worker':
      return runMultiWorkerProof(admin, await caller(), args || {});
    case 'proof.run_multi_session':
      return runMultiSessionProof(admin, await caller(), args || {});
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
    objectUri: safeText(artifact.objectUri || artifact.objectURL || artifact.gcsUri, 1000),
    downloadUrl: safeText(artifact.downloadUrl || artifact.signedUrl || artifact.url, 1000),
    contentType: safeText(artifact.contentType, 160),
    sha256: safeText(artifact.sha256, 128),
    required: artifact.required === true,
    origin: safeText(artifact.origin || safeObject(artifact.metadata).origin, 120) || 'executor_workspace',
    workspacePath: safeText(artifact.workspacePath || safeObject(artifact.metadata).workspacePath, 1000),
    body: safeText(artifact.body, 64000),
    createdAtMs: Date.now(),
    metadata: safeObject(artifact.metadata),
  };
  await collection(admin, COMMAND_CENTER_COLLECTIONS.artifacts).doc(artifactId).set(payload, {merge: true});
  return payload;
}

async function workerHeartbeat(admin, caller, args = {}) {
  const nowMs = Date.now();
  const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(caller.workerId);
  const snap = await ref.get();
  if (!snap.exists) {
    const err = new Error('Command Center worker registration not found for heartbeat.');
    err.status = 404;
    throw err;
  }
  const existing = snap.data() || {};
  const update = {
    lastHeartbeatAtMs: nowMs,
    supervisorHeartbeatAtMs: nowMs,
    heartbeatPhase: safeText(args.phase || args.currentPhase, 120) || 'idle',
    supervisorPid: Number(args.supervisorPid || 0) || 0,
    health: 'healthy',
    routable: true,
    registryRoutable: true,
    simulated: false,
    updatedAtMs: nowMs,
    stableWorkerIdentity: safeText(args.stableWorkerIdentity || existing.stableWorkerIdentity || caller.workerId, 180),
    workerInstallationId: safeText(args.workerInstallationId || existing.workerInstallationId, 180),
    workerInstanceId: safeText(args.workerInstanceId || existing.workerInstanceId, 180),
    runnerVersion: safeText(args.runnerVersion || existing.runnerVersion || safeObject(args.runtime).runnerVersion, 80),
    protocolVersion: safeText(args.protocolVersion || existing.protocolVersion || safeObject(args.runtime).protocolVersion, 80),
    processStartAtMs: Number(args.processStartAtMs || existing.processStartAtMs || 0) || 0,
    heartbeatSeq: Math.max(Number(existing.heartbeatSeq || 0) || 0, Number(args.heartbeatSeq || 0) || 0) + 1,
  };
  if (Array.isArray(args.capabilities) && args.capabilities.length) update.capabilities = safeList(args.capabilities, 80, 120);
  if (Array.isArray(args.availableImageIds)) update.availableImageIds = safeList(args.availableImageIds, 80, 160);
  if (Array.isArray(args.materializedImageIds)) update.materializedImageIds = safeList(args.materializedImageIds, 80, 160);
  if (Array.isArray(args.machineImages)) update.machineImages = args.machineImages.slice(0, 40).map((image) => cleanMachineImage({...safeObject(image), ownerKey: existing.ownerKey || caller.ownerKey}, {ownerKey: existing.ownerKey || caller.ownerKey, actor: caller.workerId}));
  if (Object.keys(safeObject(args.cacheState)).length) update.cacheState = safeObject(args.cacheState);
  if (Number(args.maxConcurrentSessions || 0) > 0) update.maxConcurrentSessions = Math.max(1, Math.min(Number(args.maxConcurrentSessions || 1), 100));
  if (Array.isArray(args.activeSessionIds) && args.activeSessionIds.length) update.activeSessionIds = safeList(args.activeSessionIds, 100, 180);
  if (Array.isArray(args.sessionIsolationModes)) update.sessionIsolationModes = safeList(args.sessionIsolationModes, 10, 80);
  if (typeof args.canMaterializeImages === 'boolean') update.canMaterializeImages = args.canMaterializeImages;
  if (safeText(args.location, 80)) update.location = safeText(args.location, 80);
  const runtime = safeObject(args.runtime);
  if (Object.keys(runtime).length) update.runtime = {...safeObject(existing.runtime), ...runtime};
  await ref.set(update, {merge: true});
  const worker = cleanWorker({workerId: caller.workerId, ...existing, ...update});
  return {ok: true, workerId: caller.workerId, heartbeatAtMs: nowMs, routable: worker.routable, liveness: deriveWorkerLiveness(worker, nowMs)};
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
  const snapshotSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.agentContextSnapshots).where('activationId', '==', activation.activationId).limit(10).get();
  const snapshots = [];
  snapshotSnap.forEach((doc) => snapshots.push(doc.data() || {}));
  snapshots.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  return {ok: true, claimed: true, activation: refreshed, resumePacket: buildAgentResumePacket(agent, session, refreshed, snapshots[0] || null)};
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

function commandCenterHealthPayload() {
  return {
    ok: true,
    service: 'command-center-mcp',
    version: COMMAND_CENTER_MCP_SERVER_VERSION,
    codexWorkerDiscovery: {
      state: 'permanently_disabled',
      code: COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE,
      disabledAt: '2026-07-27',
    },
  };
}

function commandCenterReadinessPayload({admin}) {
  const checks = [
    {name: 'firebase_admin', required: true, ok: !!(admin && typeof admin.firestore === 'function')},
  ];
  const ready = checks.every((check) => !check.required || check.ok);
  return {
    ready,
    status: ready ? 'ready' : 'not_ready',
    service: 'command-center-mcp',
    version: COMMAND_CENTER_MCP_SERVER_VERSION,
    checks,
  };
}

function commandCenterCapabilitiesPayload(server) {
  return {
    service: 'command-center-mcp',
    version: COMMAND_CENTER_MCP_SERVER_VERSION,
    summaryKind: 'names_only',
    topLevelTools: Object.keys(server && server._registeredTools || {}).sort(),
    diagnosticsOperation: 'health',
    codexWorkerDiscovery: commandCenterHealthPayload().codexWorkerDiscovery,
  };
}

function createCommandCenterMcpServer({admin}) {
  const server = new McpServer({name: 'home-center-command-center', version: COMMAND_CENTER_MCP_SERVER_VERSION});

  server.registerTool('command_center.health', {
    title: 'Command Center health',
    description: 'Check whether the Command Center MCP process is alive.',
    inputSchema: {},
  }, async () => textResult(commandCenterHealthPayload()));

  server.registerTool('command_center.readiness', {
    title: 'Command Center readiness',
    description: 'Check whether required local configuration is present to accept Command Center work. Does not inspect workers.',
    inputSchema: {},
  }, async () => textResult(commandCenterReadinessPayload({admin})));

  server.registerTool('command_center.capabilities', {
    title: 'Command Center capabilities',
    description: 'Return a bounded, deterministic summary of callable tools for this deployed revision.',
    inputSchema: {},
  }, async () => textResult(commandCenterCapabilitiesPayload(server)));

  server.registerTool('command_center_operation', {
    title: 'Command Center operation dispatcher',
    description: 'Compatibility dispatcher matching the Home Center MCP bridge. Use this when ChatGPT sees Command Center directly or when top-level tool metadata is stale.',
    inputSchema: {operation: z.string(), args: z.record(z.string(), z.any()).optional()},
  }, async (args, extra) => textResult({operation: normalizeCommandCenterOperationName(args.operation), result: await runCommandCenterOperation(admin, extra, args.operation, args.args || {})}));

  server.registerTool('command_center.render.blender_glb', {
    title: 'Render GLB with Blender',
    description: 'Non-agent Blender execution primitive: GLB plus script plus execution contract returns a durable 3D artifact bundle and visual evidence. Does not create Command Center jobs or Codex activations.',
    inputSchema: {
      idempotencyKey: z.string(),
      renderId: z.string().optional(),
      glbFile: z.file().optional(),
      scriptFile: z.file().optional(),
      glbRef: z.string().optional(),
      scriptRef: z.string().optional(),
      scriptText: z.string().optional(),
      settings: z.record(z.string(), z.any()).optional(),
      executionContract: z.record(z.string(), z.any()).optional(),
      cache: z.boolean().optional(),
    },
  }, async (args, extra) => textResult(await renderBlenderGlb(admin, extra, args || {})));

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
    inputSchema: {idempotencyKey: z.string(), projectId: z.string(), title: z.string(), objective: z.string(), acceptanceCriteria: z.array(z.string()).optional(), constraints: z.array(z.string()).optional(), scopeExclusions: z.array(z.string()).optional(), workerRequirements: z.array(z.string()).optional(), budgetClass: z.string().optional(), mutationPolicy: z.record(z.string(), z.string()).optional(), baseWorkspace: z.record(z.string(), z.any()).optional(), requiredArtifacts: z.array(z.string()).optional(), verificationCommands: z.array(z.string()).optional(), stopConditions: z.array(z.string()).optional(), sessionPolicy: z.record(z.string(), z.any()).optional(), machineImageId: z.string().optional(), imageRequirements: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await createJob(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.create_followup', {
    title: 'Create Command Center follow-up job',
    description: 'Create a new linked invocation from a source job handoff. This does not rewrite old job history.',
    inputSchema: {idempotencyKey: z.string(), sourceJobId: z.string(), projectId: z.string().optional(), title: z.string(), objective: z.string(), acceptanceCriteria: z.array(z.string()).optional(), constraints: z.array(z.string()).optional(), scopeExclusions: z.array(z.string()).optional(), workerRequirements: z.array(z.string()).optional(), budgetClass: z.string().optional(), mutationPolicy: z.record(z.string(), z.string()).optional(), baseWorkspace: z.record(z.string(), z.any()).optional(), requiredArtifacts: z.array(z.string()).optional(), verificationCommands: z.array(z.string()).optional(), stopConditions: z.array(z.string()).optional(), sessionPolicy: z.record(z.string(), z.any()).optional(), machineImageId: z.string().optional(), imageRequirements: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await createFollowupJob(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.get', {title: 'Get Command Center job', description: 'Read one Command Center job packet.', inputSchema: {jobId: z.string()}}, async (args, extra) => textResult({job: await getJob(admin, cleanJobId(args.jobId), await callerFromExtra(admin, extra))}));

  server.registerTool('command_center.jobs.list', {
    title: 'List Command Center jobs',
    description: 'List recent Command Center jobs, optionally filtered by project or status.',
    inputSchema: {projectId: z.string().optional(), status: z.enum(COMMAND_CENTER_ALLOWED_STATUSES).optional(), limit: z.number().optional()},
  }, async (args, extra) => {
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
  });

  server.registerTool('command_center.jobs.reconcile_stale', {
    title: 'Reconcile stale Command Center jobs',
    description: 'Dry-run or expire stale nonterminal jobs and active leases with audit events.',
    inputSchema: {idempotencyKey: z.string().optional(), dryRun: z.boolean().optional(), olderThanMs: z.number().optional(), statuses: z.array(z.string()).optional(), limit: z.number().optional()},
  }, async (args, extra) => textResult(await reconcileStaleJobs(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.dispatch_queued', {
    title: 'Dispatch queued Command Center jobs',
    description: 'Dry-run or lease queued recoverable jobs to the least-loaded compatible worker; retry expired jobs only when requested.',
    inputSchema: {idempotencyKey: z.string().optional(), dryRun: z.boolean().optional(), retryExpired: z.boolean().optional(), limit: z.number().optional(), maxDispatch: z.number().optional()},
  }, async (args, extra) => textResult(await dispatchQueuedJobs(admin, await callerFromExtra(admin, extra), args || {})));

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
    const handoff = await synthesizeJobHandoff(admin, jobId, c);
    return textResult({jobId, status: handoff.job.status, checkpoint: handoff.checkpoint, counters: handoff.counters, recommendedNextAction: handoff.review.recommendedNextAction, job: await getJob(admin, jobId, c)});
  });
  server.registerTool('command_center.jobs.get_handoff', {title: 'Get Command Center job handoff', description: 'Read a compact review/correction packet synthesized from job state, events, logs, artifacts, checkpoints, and bucket objects.', inputSchema: {jobId: z.string()}}, async (args, extra) => textResult({handoff: await synthesizeJobHandoff(admin, cleanJobId(args.jobId), await callerFromExtra(admin, extra))}));
  server.registerTool('command_center.jobs.get_events', {title: 'Get Command Center job events', description: 'Read structured job events generated from Command Center state, not another chat agent.', inputSchema: {jobId: z.string(), limit: z.number().optional()}}, async (args, extra) => {
    const jobId = cleanJobId(args.jobId);
    await getJob(admin, jobId, await callerFromExtra(admin, extra));
    return textResult({events: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.events, jobId, Math.max(1, Math.min(Number(args.limit) || 50, 100)))});
  });
  server.registerTool('command_center.jobs.get_logs', {title: 'Get Command Center job logs', description: 'Read append-only log metadata for a job.', inputSchema: {jobId: z.string(), limit: z.number().optional()}}, async (args, extra) => {
    const jobId = cleanJobId(args.jobId);
    await getJob(admin, jobId, await callerFromExtra(admin, extra));
    return textResult({logs: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.logs, jobId, Math.max(1, Math.min(Number(args.limit) || 50, 100)))});
  });
  server.registerTool('command_center.jobs.get_artifacts', {title: 'Get Command Center job artifacts', description: 'Read artifact metadata and object references for a job.', inputSchema: {jobId: z.string(), limit: z.number().optional()}}, async (args, extra) => {
    const jobId = cleanJobId(args.jobId);
    await getJob(admin, jobId, await callerFromExtra(admin, extra));
    return textResult({artifacts: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.artifacts, jobId, Math.max(1, Math.min(Number(args.limit) || 50, 100)))});
  });

  server.registerTool('command_center.agents.upsert_repo_agent', {
    title: 'Upsert Command Center repo agent',
    description: 'Create or update a durable repo/project agent identity that owns Codex cloud context. This does not create a fake worker.',
    inputSchema: {idempotencyKey: z.string(), agentId: z.string().optional(), projectId: z.string(), name: z.string().optional(), repository: z.string().optional(), domain: z.string().optional(), purpose: z.string().optional(), status: z.string().optional(), contextRefs: z.array(z.string()).optional(), preferredTools: z.array(z.string()).optional(), validationRules: z.array(z.string()).optional(), openQuestions: z.array(z.string()).optional(), sessionId: z.string().optional(), sessionTitle: z.string().optional(), sessionPurpose: z.string().optional()},
  }, async (args, extra) => textResult(await upsertRepoAgent(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.agents.create_activation', {
    title: 'Create Codex cloud activation',
    description: 'Create a dormant-to-active execution packet for a durable Codex worker session. Repo binding is optional; real Codex cloud refs are attached when available.',
    inputSchema: {idempotencyKey: z.string(), activationId: z.string().optional(), agentId: z.string().optional(), projectId: z.string().optional(), name: z.string().optional(), repository: z.string().optional(), sessionId: z.string().optional(), sessionTitle: z.string().optional(), sessionPurpose: z.string().optional(), workerFamily: z.string().optional(), runtime: z.string().optional(), currentWorkspaceSnapshotRef: z.string().optional(), currentWorkspaceSnapshotDigest: z.string().optional(), restoreStrategy: z.string().optional(), openQuestions: z.array(z.string()).optional(), preferredWorkerIds: z.array(z.string()).optional(), title: z.string().optional(), prompt: z.string(), taskType: z.string().optional(), trigger: z.string().optional(), inputs: z.record(z.string(), z.any()).optional(), acceptanceCriteria: z.array(z.string()).optional(), constraints: z.array(z.string()).optional(), artifactRequirements: z.array(z.string()).optional(), workerRequirements: z.array(z.string()).optional(), executionPolicy: z.record(z.string(), z.any()).optional(), contextRefs: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await createAgentActivation(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.agents.get_resume_packet', {
    title: 'Get Codex cloud resume packet',
    description: 'Read the durable resume packet that a Codex cloud bridge should paste/use when resuming the real Codex cloud surface.',
    inputSchema: {activationId: z.string()},
  }, async (args) => textResult(await getAgentResumePacket(admin, args || {})));

  server.registerTool('command_center.agents.record_codex_cloud_ref', {
    title: 'Record real Codex cloud ref',
    description: 'Record the real ChatGPT/OpenAI Codex cloud task URL or resume handle for an activation. Never include cookies, tokens, or session material.',
    inputSchema: {idempotencyKey: z.string(), activationId: z.string(), codexCloudRefId: z.string().optional(), url: z.string().optional(), codexCloudUrl: z.string().optional(), title: z.string().optional(), surface: z.string().optional(), status: z.string().optional(), resumeHandle: z.string().optional(), summary: z.string().optional(), evidenceRefs: z.array(z.string()).optional(), activationStatus: z.string().optional()},
  }, async (args, extra) => textResult(await recordCodexCloudRef(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.agents.record_artifact', {
    title: 'Record Codex cloud activation artifact',
    description: 'Record a redacted artifact from a real Codex cloud activation, such as final report, bridge transcript, or evidence ref.',
    inputSchema: {idempotencyKey: z.string(), activationId: z.string(), artifactId: z.string().optional(), name: z.string(), kind: z.string().optional(), uri: z.string().optional(), objectUri: z.string().optional(), body: z.string().optional(), summary: z.string().optional(), sha256: z.string().optional(), required: z.boolean().optional(), evidenceRefs: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await recordAgentArtifact(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.agents.complete_activation', {
    title: 'Complete Codex cloud activation',
    description: 'Mark a durable Codex worker activation terminal and write Command Center memory. Completed durable sessions require artifact evidence and, when required, a next workspace snapshot.',
    inputSchema: {idempotencyKey: z.string(), activationId: z.string(), status: z.enum(['completed', 'failed', 'canceled', 'needs_human']).optional(), failed: z.boolean().optional(), finalSummary: z.string().optional(), summary: z.string().optional(), handoffSummary: z.string().optional(), nextWorkspaceSnapshotRef: z.string().optional(), nextWorkspaceSnapshotDigest: z.string().optional(), workspaceSnapshotRef: z.string().optional(), workspaceSnapshotDigest: z.string().optional()},
  }, async (args, extra) => textResult(await completeAgentActivation(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.agents.get_handoff', {
    title: 'Get Codex cloud activation handoff',
    description: 'Read a ChatGPT-reviewable handoff for a real Codex cloud activation.',
    inputSchema: {activationId: z.string()},
  }, async (args) => textResult({handoff: await synthesizeAgentHandoff(admin, cleanActivationId(args.activationId))}));

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
  }, async (args, extra) => textResult(await getBucketObject(admin, args || {}, await callerFromExtra(admin, extra))));

  server.registerTool('command_center.bucket.list_objects', {
    title: 'List Command Center bucket objects',
    description: 'List durable Command Center bucket memory, skills, and cross-repo notes with optional filters.',
    inputSchema: {bucketId: z.string().optional(), kind: z.enum(COMMAND_CENTER_BUCKET_KINDS).optional(), projectId: z.string().optional(), repository: z.string().optional(), jobId: z.string().optional(), tag: z.string().optional(), limit: z.number().optional()},
  }, async (args, extra) => textResult(await listBucketObjects(admin, args || {}, await callerFromExtra(admin, extra))));

  server.registerTool('command_center.bucket.promote_skill', {
    title: 'Promote Command Center scratch skill',
    description: 'Promote a scratch skill bucket object into the promoted skill lane while preserving provenance and supersession links.',
    inputSchema: {idempotencyKey: z.string(), objectId: z.string(), path: z.string().optional(), title: z.string().optional(), summary: z.string().optional(), body: z.string().optional(), evidenceRefs: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await promoteBucketSkill(admin, await callerFromExtra(admin, extra), args || {})));


  server.registerTool('command_center.machine_images.register', {
    title: 'Register Command Center machine image',
    description: 'Create or update a versioned machine image/capability profile with cache and dependency bundle refs. This records prepared capacity; it does not install dependencies during a job.',
    inputSchema: {idempotencyKey: z.string(), imageId: z.string().optional(), name: z.string().optional(), imageKind: z.string().optional(), version: z.string().optional(), digest: z.string().optional(), status: z.enum(COMMAND_CENTER_MACHINE_IMAGE_STATUSES).optional(), capabilities: z.array(z.string()).optional(), toolchains: z.array(z.string()).optional(), dependencyBundleRefs: z.array(z.string()).optional(), warmCacheRefs: z.array(z.string()).optional(), materializationModes: z.array(z.string()).optional(), estimatedColdStartMs: z.number().optional(), estimatedHotStartMs: z.number().optional(), provenance: z.record(z.string(), z.any()).optional()},
  }, async (args, extra) => textResult(await registerMachineImage(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.machine_images.list', {title: 'List Command Center machine images', description: 'List owner-scoped machine image profiles and cacheable capability bundles.', inputSchema: {status: z.string().optional(), capability: z.string().optional()}}, async (args, extra) => textResult(await listMachineImages(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.machine_images.inspect', {title: 'Inspect Command Center machine image', description: 'Inspect one machine image and which hosts have it materialized.', inputSchema: {imageId: z.string()}}, async (args, extra) => textResult(await inspectMachineImage(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.hosts.list', {title: 'List Command Center hosts', description: 'Host-centric alias for workers.list, including materialized images, cache state, and session capacity.', inputSchema: {active: z.boolean().optional(), stale: z.boolean().optional(), retired: z.boolean().optional(), routable: z.boolean().optional(), owner: z.string().optional(), ownerKey: z.string().optional(), capability: z.string().optional(), location: z.string().optional()}}, async (args, extra) => textResult(await listWorkersCensus(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.hosts.inspect', {title: 'Inspect Command Center host', description: 'Host-centric alias for workers.inspect.', inputSchema: {workerId: z.string()}}, async (args, extra) => textResult(await inspectWorker(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.workers.provision', {
    title: 'Provision Command Center cloud worker',
    description: 'Create cloud-only Debian Codex worker capacity through Secret Manager and Cloud Run Jobs. Termux, phone, Android, and local hosts are rejected.',
    inputSchema: {idempotencyKey: z.string(), dryRun: z.boolean().optional(), workerId: z.string().optional(), machineImageId: z.string().optional(), requestedSessions: z.number().optional(), cloudProjectId: z.string().optional(), projectId: z.string().optional(), region: z.string().optional(), image: z.string().optional(), jobName: z.string().optional(), workerTokenSecret: z.string().optional(), openAiApiKeySecret: z.string().optional(), githubTokenSecret: z.string().optional(), snapshotBucket: z.string().optional(), serviceAccount: z.string().optional(), capabilities: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await provisionCloudWorker(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.provisioning.inspect', {title: 'Inspect Command Center provisioning', description: 'Inspect cloud worker provisioning requests without exposing secrets.', inputSchema: {provisioningId: z.string().optional(), limit: z.number().optional()}}, async (args, extra) => textResult(await inspectProvisioning(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.provisioning.reconcile', {title: 'Reconcile Command Center provisioning', description: 'Check provisioned cloud worker records and recommend wake/probe/repair actions.', inputSchema: {idempotencyKey: z.string().optional(), dryRun: z.boolean().optional(), limit: z.number().optional()}}, async (args, extra) => textResult(await reconcileProvisioning(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.codex_sessions.create', {
    title: 'Create Command Center Codex session',
    description: 'Allocate a durable Codex session on a compatible host with a materialized machine image. Fails red when cache/session capacity is not present.',
    inputSchema: {idempotencyKey: z.string(), sessionId: z.string().optional(), projectId: z.string().optional(), repository: z.string().optional(), title: z.string().optional(), purpose: z.string().optional(), workerRequirements: z.array(z.string()).optional(), machineImageId: z.string().optional(), imageRequirements: z.array(z.string()).optional(), allocation: z.string().optional(), isolationMode: z.string().optional(), requireMaterializedImage: z.boolean().optional(), allowMaterializationDuringJob: z.boolean().optional()},
  }, async (args, extra) => textResult(await createCodexSession(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.codex_sessions.list', {title: 'List Command Center Codex sessions', description: 'List durable Codex sessions by status, image, or host installation.', inputSchema: {status: z.string().optional(), machineImageId: z.string().optional(), hostInstallationId: z.string().optional(), workerInstallationId: z.string().optional()}}, async (args, extra) => textResult(await listCodexSessions(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.codex_sessions.inspect', {title: 'Inspect Command Center Codex session', description: 'Inspect one durable Codex session and its current host/image binding.', inputSchema: {sessionId: z.string()}}, async (args, extra) => textResult(await inspectCodexSession(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.codex_sessions.reconcile', {title: 'Reconcile Command Center Codex sessions', description: 'Dry-run or mark stale allocated/running sessions recoverable.', inputSchema: {idempotencyKey: z.string().optional(), dryRun: z.boolean().optional(), olderThanMs: z.number().optional()}}, async (args, extra) => textResult(await reconcileCodexSessions(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.workers.register_oneshot', {
    title: 'Register one-shot Command Center worker',
    description: 'Register a user-owned one-shot Codex worker and return a worker token once. Store it only on the worker host.',
    inputSchema: {idempotencyKey: z.string(), workerId: z.string(), workerInstallationId: z.string().optional(), workerInstanceId: z.string().optional(), runnerVersion: z.string().optional(), protocolVersion: z.string().optional(), processStartAtMs: z.number().optional(), heartbeatSeq: z.number().optional(), engine: z.string().optional(), location: z.string().optional(), capabilities: z.array(z.string()).optional(), baseWorkspace: z.record(z.string(), z.any()).optional(), baseWorkspaces: z.array(z.record(z.string(), z.any())).optional(), preparedWorkspaces: z.array(z.record(z.string(), z.any())).optional(), limits: z.record(z.string(), z.any()).optional(), activation: z.record(z.string(), z.any()).optional(), runtime: z.record(z.string(), z.any()).optional(), cloudRunJob: z.record(z.string(), z.any()).optional(), sessionPolicy: z.record(z.string(), z.any()).optional(), repositoryAffinity: z.array(z.string()).optional()},
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

  server.registerTool('command_center.system.health', {title: 'Command Center system health', description: 'Return separate control-plane, worker-pool, and recent end-to-end probe health.', inputSchema: {}}, async (_args, extra) => textResult(await systemHealth(admin, await callerFromExtra(admin, extra))));
  server.registerTool('command_center.workers.list', {title: 'List Command Center workers', description: 'Compact worker census with identity, liveness, routability, capabilities, and active lease capacity.', inputSchema: {active: z.boolean().optional(), stale: z.boolean().optional(), retired: z.boolean().optional(), routable: z.boolean().optional(), owner: z.string().optional(), ownerKey: z.string().optional(), capability: z.string().optional(), location: z.string().optional()}}, async (args, extra) => textResult(await listWorkersCensus(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.workers.inspect', {title: 'Inspect Command Center worker', description: 'Inspect one worker registration, recent leases/events, and repair recommendation.', inputSchema: {workerId: z.string()}}, async (args, extra) => textResult(await inspectWorker(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.routing.explain', {title: 'Explain Command Center routing', description: 'Explain inclusion/exclusion reasons for worker requirements without creating a job.', inputSchema: {workerRequirements: z.array(z.string()).optional(), requiredWorkerCapabilities: z.array(z.string()).optional(), requirements: z.array(z.string()).optional(), projectId: z.string().optional(), baseWorkspace: z.record(z.string(), z.any()).optional(), sessionPolicy: z.record(z.string(), z.any()).optional(), machineImageId: z.string().optional(), imageRequirements: z.array(z.string()).optional(), allowLocalHost: z.boolean().optional()}}, async (args, extra) => textResult(await routingExplain(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.workers.reconcile', {title: 'Reconcile Command Center workers', description: 'Owner-scoped bounded repair for stale/legacy worker records and abandoned jobs/leases.', inputSchema: {idempotencyKey: z.string().optional(), dryRun: z.boolean().optional(), olderThanMs: z.number().optional(), limit: z.number().optional()}}, async (args, extra) => textResult(await reconcileWorkers(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.workers.request_restart', {title: 'Request Command Center worker restart', description: 'Record a supervisor restart request and truthfully report host_offline or missing restart channel.', inputSchema: {idempotencyKey: z.string(), workerId: z.string(), reason: z.string().optional()}}, async (args, extra) => textResult(await requestWorkerRestart(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.proof.run_multi_worker', {title: 'Run multi-worker proof', description: 'Fail-closed proof requiring two distinct real non-tanks worker installations with nonce-bearing jobs.', inputSchema: {idempotencyKey: z.string(), nonceA: z.string().optional(), nonceB: z.string().optional()}}, async (args, extra) => textResult(await runMultiWorkerProof(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.proof.run_multi_session', {title: 'Run multi-session proof', description: 'Fail-closed proof requiring two isolated real Codex session slots on materialized machine images. It never synthesizes completed execution.', inputSchema: {idempotencyKey: z.string(), nonceA: z.string().optional(), nonceB: z.string().optional(), machineImageId: z.string().optional(), imageRequirements: z.array(z.string()).optional(), sessionPolicy: z.record(z.string(), z.any()).optional(), autoProvision: z.boolean().optional()}}, async (args, extra) => textResult(await runMultiSessionProof(admin, await callerFromExtra(admin, extra), args || {})));
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
  return removeDisabledCodexWorkerDiscoveryTools(server);
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
  app.get('/', (_req, res) => {
    res.set('Cache-Control', 'no-store');
    res.json(commandCenterHealthPayload());
  });
  app.get('/ready', (_req, res) => {
    const readiness = commandCenterReadinessPayload({admin});
    res.set('Cache-Control', 'no-store');
    res.status(readiness.ready ? 200 : 503).json(readiness);
  });
  app.get('/.well-known/oauth-protected-resource', (_req, res) => { res.set('Cache-Control', 'no-store'); res.json(commandCenterProtectedResourceMetadata()); });
  app.get('/.well-known/oauth-authorization-server', (_req, res) => { res.set('Cache-Control', 'no-store'); res.json(commandCenterAuthorizationServerMetadata()); });
  const sendWorkerError = (res, err) => res.status(err.status || 500).json({ok: false, error: safeText(err.message, 500) || 'Command Center worker gateway failure.'});
  const sendCodexWorkerDiscoveryTombstone = (_req, res) => res.status(410).json({
    ok: false,
    error: {
      code: COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE,
      message: COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_MESSAGE,
      state: 'permanently_disabled',
      disabledAt: '2026-07-27',
    },
  });
  app.use(['/agent', '/worker'], sendCodexWorkerDiscoveryTombstone);

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
      const runtime = safeObject(req.body && req.body.runtime);
      const workerRef = collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(caller.workerId);
      const workerSnap = await workerRef.get();
      const existingWorker = workerSnap.exists ? safeObject(workerSnap.data()) : {};
      const workerUpdate = {lastHeartbeatAtMs: nowMs, health: 'healthy', routable: true, simulated: false};
      if (Object.keys(runtime).length) workerUpdate.runtime = {...safeObject(existingWorker.runtime), ...runtime};
      await workerRef.set(workerUpdate, {merge: true});
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

  app.post('/worker/heartbeat', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      res.json(await workerHeartbeat(admin, caller, req.body || {}));
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
      const acceptedAtMs = Date.now();
      await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(job.jobId).set({updatedAtMs: acceptedAtMs, workerAcceptedLeaseAtMs: acceptedAtMs}, {merge: true});
      await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(caller.workerId).set({lastAcceptedLeaseAtMs: acceptedAtMs, lastHeartbeatAtMs: acceptedAtMs, health: 'healthy', routable: true, registryRoutable: true}, {merge: true});
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
      if (event.type === 'executor_started') {
        await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set({
          status: 'executing',
          updatedAtMs: Date.now(),
          executorStartedAtMs: Date.now(),
          executorIdentity: safeText(req.body.executorId || safeObject(req.body.data).executorId, 180),
          executorPid: Number(req.body.pid || safeObject(req.body.data).pid || 0) || 0,
        }, {merge: true});
      }
      if (event.type === 'executor_heartbeat') {
        await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set({updatedAtMs: Date.now(), lastWorkerHeartbeatAtMs: Date.now()}, {merge: true});
        await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(caller.workerId).set({lastHeartbeatAtMs: Date.now(), health: 'healthy', routable: true, simulated: false}, {merge: true});
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
      if (event.type === 'executor_finished' || event.type === 'executor_failed') {
        const activationSnap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobActivations).where('jobId', '==', jobId).limit(10).get();
        const batch = admin.firestore().batch();
        activationSnap.forEach((doc) => {
          const activation = doc.data() || {};
          if (activation.workerId === caller.workerId && ['requested', 'accepted'].includes(activation.status)) {
            batch.set(doc.ref, {status: event.type === 'executor_finished' ? 'completed' : 'failed', updatedAtMs: Date.now(), finishedAtMs: Date.now()}, {merge: true});
          }
        });
        await batch.commit();
        if (event.type === 'executor_failed' && !isTerminalJobStatus(job.status)) {
          await failJobTerminal(admin, job, caller.workerId, event.summary || 'executor_failed', {executorEventId: event.eventId, executorEventData: event.data});
        }
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
      const releasedLeases = await releaseActiveLeasesForJob(admin, jobId, caller.workerId, status, `worker_complete_${status}`);
      await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set({status, updatedAtMs: Date.now(), completedAtMs: Date.now(), finalReport, completionArtifactIds}, {merge: true});
      const event = await appendEvent(admin, {type: `job_${status}`, jobId, projectId: job.projectId, actor: caller.workerId, summary: finalReport || `One-shot worker marked job ${status}.`, data: {artifactIds: completionArtifactIds, releasedLeases}});
      res.json({ok: true, status, event, artifacts: written, releasedLeases});
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
  COMMAND_CENTER_MCP_SERVER_VERSION,
  COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED,
  COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_CODE,
  COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_MESSAGE,
  COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_OPERATIONS,
  COMMAND_CENTER_CODEX_WORKER_DISCOVERY_DISABLED_TOOL_NAMES,
  isCodexWorkerDiscoveryOperationDisabled,
  assertCodexWorkerDiscoveryOperationEnabled,
  removeDisabledCodexWorkerDiscoveryTools,
  commandCenterHealthPayload,
  commandCenterReadinessPayload,
  commandCenterCapabilitiesPayload,
  COMMAND_CENTER_ALLOWED_EMAILS,
  requireCommandCenterAllowedEmail,
  COMMAND_CENTER_COLLECTIONS,
  COMMAND_CENTER_DEFAULT_WORKERS,
  COMMAND_CENTER_DEFAULT_PROJECTS,
  COMMAND_CENTER_REQUIRED_ARTIFACTS,
  COMMAND_CENTER_DEFAULT_BASE_WORKSPACE,
  COMMAND_CENTER_ALLOWED_STATUSES,
  COMMAND_CENTER_AGENT_ACTIVATION_STATUSES,
  COMMAND_CENTER_JOB_ACTIVATION_STATUSES,
  COMMAND_CENTER_COMPLETION_EVENT_LOOKBACK_LIMIT,
  COMMAND_CENTER_TERMINAL_JOB_STATUSES,
  COMMAND_CENTER_DURABLE_SESSION_RESTORE_STRATEGIES,
  COMMAND_CENTER_MACHINE_IMAGE_STATUSES,
  COMMAND_CENTER_CODEX_SESSION_STATUSES,
  COMMAND_CENTER_SESSION_ISOLATION_MODES,
  COMMAND_CENTER_PROVISIONING_STATUSES,
  COMMAND_CENTER_DEFAULT_CLOUD_MACHINE_IMAGE_ID,
  COMMAND_CENTER_CODEX_CLOUD_SURFACE,
  COMMAND_CENTER_DEFAULT_BUCKET_ID,
  COMMAND_CENTER_BUCKET_KINDS,
  COMMAND_CENTER_BUCKET_LAYOUT,
  cleanAppControlProfile,
  cleanBrowserEpisode,
  cleanBrowserPlaybook,
  cleanProjectPacket,
  cleanRepoAgent,
  cleanAgentSession,
  cleanMachineImage,
  cleanSessionPolicy,
  workerMachineImageState,
  workerImagePolicyDiagnostic,
  workerSessionPolicyDiagnostic,
  cleanActivationTask,
  cleanCodexCloudRef,
  buildAgentResumePacket,
  lookupBrowserPlaybook,
  renderBundleOptionsFrom,
  renderRequiredBundleKindsForOptions,
  createCommandCenterMcpApp,
  createCommandCenterMcpServer,
  cleanBaseWorkspace,
  cleanMutationPolicy,
  cleanOneShotExecution,
  cleanBucketObject,
  ownerKeyFromActor,
  ownerKeyFromCaller,
  attachOwnerKey,
  assertOwnerAccess,
  recordsVisibleToCaller,
  normalizeGithubRepositoryRef,
  repositoryFromBaseWorkspace,
  repositoryFromProject,
  resolveJobRepository,
  activeLeaseForJob,
  normalizeActivationChannel,
  deriveWorkerLiveness,
  isTerminalJobStatus,
  staleJobCandidate,
  activationStartTimeoutCandidate,
  isWorkerLeaseEligible,
  workerConcurrencyLimit,
  selectWorkerCandidates,
  selectWorkerForJob,
  dedupeWorkerRecords,
  workerStableIdentity,
  workerApiKeyProbeAllowsCodex,
  workerRoutingPriority,
  isLocalHostWorker,
  cloudProvisioningDefaults,
  assertCloudProvisioningRequest,
  cloudMachineImageRecord,
  cloudWorkerRecordFromProvisioning,
  provisioningRecommendation,
  cleanWorkerIdentity,
  workerRoutabilityDiagnostic,
  compactWorkerCensus,
  filterWorkerCensus,
  explainWorkerCandidate,
  proofEligibleWorker,
  runMultiSessionProof,
  activeLeaseCountsByWorker,
  selectWorker,
  buildJobActivation,
  activationStateFromResult,
  shouldAcceptWorkerCompletion,
  wakeWorker,
  renderBundleOptionsFrom,
  renderRequiredBundleKindsForOptions,
  renderBlenderGlb,
  resolveRenderSources,
  validateGlbBytes,
  validateScriptBytes,
};
