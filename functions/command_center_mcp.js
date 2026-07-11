const {createHash, randomUUID} = require('node:crypto');
const express = require('express');
const {z} = require('zod/v4');
const {McpServer} = require('@modelcontextprotocol/sdk/server/mcp.js');
const {StreamableHTTPServerTransport} = require('@modelcontextprotocol/sdk/server/streamableHttp.js');

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
  health: 'healthy',
  capabilities: ['codex', 'github', 'node', 'python', 'firebase', 'home-drive-mcp', 'network', 'one-shot-worker', 'prepared-workspace'],
  limits: {concurrentJobs: 2},
  simulated: true,
}];

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
  return {authKind: 'home_center_mcp_oauth', tokenHash: hashText(token, 24), actor: email || `mcp:${hashText(token, 12)}`};
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

function cleanRequiredArtifacts(value) {
  const requested = safeList(value, 60, 180);
  const names = new Set([...COMMAND_CENTER_REQUIRED_ARTIFACTS, ...requested]);
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
  return {
    executionMode: 'one_shot',
    baseWorkspace: cleanBaseWorkspace(args.baseWorkspace),
    requiredArtifacts: cleanRequiredArtifacts(args.requiredArtifacts),
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
  return {
    workerId: safeText(data.workerId, 120),
    engine: safeText(data.engine, 80) || 'codex',
    location: safeText(data.location, 80) || 'cloud',
    health: safeText(data.health, 80) || 'unknown',
    capabilities: safeList(data.capabilities, 80, 120),
    baseWorkspaces: Array.isArray(data.baseWorkspaces) ? data.baseWorkspaces.slice(0, 20).map(cleanBaseWorkspace) : [],
    limits: safeObject(data.limits),
    simulated: data.simulated === true,
    oneShot: data.oneShot !== false,
  };
}

async function workerRecords(admin) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).limit(50).get();
  const byId = new Map(COMMAND_CENTER_DEFAULT_WORKERS.map((worker) => [worker.workerId, worker]));
  snap.forEach((doc) => byId.set(doc.id, cleanWorker({workerId: doc.id, ...(doc.data() || {})})));
  return Array.from(byId.values()).filter((worker) => worker.workerId);
}

function selectWorker(workers, requirements) {
  const reqs = safeList(requirements, 40, 120).map((req) => req.toLowerCase());
  const candidates = workers.filter((worker) => safeText(worker.health, 40) !== 'unhealthy');
  return candidates.find((worker) => {
    const caps = new Set((worker.capabilities || []).map((cap) => String(cap).toLowerCase()));
    return reqs.every((req) => caps.has(req));
  }) || candidates[0] || COMMAND_CENTER_DEFAULT_WORKERS[0];
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
  const idemId = `${caller.tokenHash}_${hashText(operation + ':' + idempotencyKey, 32)}`;
  const ref = collection(admin, COMMAND_CENTER_COLLECTIONS.idempotency).doc(idemId);
  const snap = await ref.get();
  if (snap.exists) return {idempotentReplay: true, ...(snap.data().response || {})};
  const response = await fn();
  await ref.set({idempotencyKey, operation, caller: caller.actor, createdAtMs: Date.now(), response});
  return response;
}

async function getLatestCheckpoint(admin, jobId) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.checkpoints).where('jobId', '==', jobId).limit(25).get();
  const checkpoints = [];
  snap.forEach((doc) => checkpoints.push(doc.data()));
  checkpoints.sort((a, b) => Number(b.createdAtMs || 0) - Number(a.createdAtMs || 0));
  return checkpoints[0] || null;
}

async function getJob(admin, jobId) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).get();
  if (!snap.exists) {
    const err = new Error('Command Center job not found.');
    err.status = 404;
    throw err;
  }
  return snap.data() || {};
}

async function resolveProject(admin, args) {
  const repository = safeText(args.repository, 240);
  const projectId = cleanProjectId(args.projectId, repository || args.name || 'project');
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.projects).doc(projectId).get();
  if (snap.exists) return {project: {projectId, ...(snap.data() || {})}, created: false};
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

async function createJob(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'jobs.create', async () => {
    const projectId = cleanProjectId(args.projectId, args.repository || 'project');
    const jobId = `job_${randomUUID()}`;
    const workers = await workerRecords(admin);
    const worker = selectWorker(workers, args.workerRequirements);
    const nowMs = Date.now();
    const job = {
      jobId,
      projectId,
      title: safeText(args.title, 300) || 'Untitled Command Center job',
      objective: safeText(args.objective, 4000),
      acceptanceCriteria: safeList(args.acceptanceCriteria, 80, 1000),
      constraints: safeList(args.constraints, 80, 1000),
      scopeExclusions: safeList(args.scopeExclusions, 80, 1000),
      workerRequirements: safeList(args.workerRequirements, 40, 120),
      budgetClass: safeText(args.budgetClass, 80) || 'small',
      mutationPolicy: cleanMutationPolicy(args.mutationPolicy),
      ...cleanOneShotExecution(args),
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
    const createdEvent = await appendEvent(admin, {type: 'job_created', jobId, projectId, actor: caller.actor, summary: job.title, data: {workerRequirements: job.workerRequirements}});
    const leasedEvent = await appendEvent(admin, {type: 'job_leased', jobId, projectId, actor: 'command_center', summary: `Leased to ${worker.workerId}.`, data: {worker}});
    await recordLog(admin, jobId, projectId, 'Command Center created and leased one-shot job from prepared workspace contract.', {workerId: worker.workerId, executionMode: job.executionMode, baseWorkspace: job.baseWorkspace.baseWorkspaceId});
    const checkpoint = await recordCheckpoint(admin, job);
    return {job, lease, events: [createdEvent, leasedEvent], checkpoint};
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
    const job = await getJob(admin, jobId);
    if (job.status === 'canceled' || job.status === 'completed') {
      const err = new Error('Cannot revise a completed or canceled Command Center job.');
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
    const job = await getJob(admin, jobId);
    const updates = {status, updatedAtMs: Date.now(), lastTransitionBy: caller.actor};
    await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set(updates, {merge: true});
    const event = await appendEvent(admin, {type: `job_${status}`, jobId, projectId: job.projectId, actor: caller.actor, summary: safeText(args.reason, 1000) || `Job ${status}.`});
    return {jobId, status, event};
  });
}

async function answerQuestion(admin, caller, args) {
  return idempotentMutation(admin, caller, requireIdempotencyKey(args.idempotencyKey), 'jobs.answer_question', async () => {
    const jobId = cleanJobId(args.jobId);
    const job = await getJob(admin, jobId);
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
    const job = await getJob(admin, jobId);
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
    const workerToken = `ccw_${randomUUID()}_${randomUUID()}`;
    const tokenHash = tokenDigest(workerToken);
    const worker = cleanWorker({
      workerId,
      engine: args.engine || 'codex',
      location: args.location || 'local',
      health: 'healthy',
      capabilities: cleanRequiredArtifacts([]).length ? safeList(args.capabilities, 80, 120) : [],
      baseWorkspaces: Array.isArray(args.baseWorkspaces) ? args.baseWorkspaces : [args.baseWorkspace || COMMAND_CENTER_DEFAULT_BASE_WORKSPACE],
      limits: safeObject(args.limits),
      simulated: false,
      oneShot: true,
    });
    if (!worker.capabilities.length) worker.capabilities = ['codex', 'one-shot-worker', 'prepared-workspace'];
    await collection(admin, COMMAND_CENTER_COLLECTIONS.workers).doc(workerId).set({...worker, registeredBy: caller.actor, updatedAtMs: nowMs, createdAtMs: nowMs}, {merge: true});
    await collection(admin, COMMAND_CENTER_COLLECTIONS.workerTokens).doc(tokenHash).set({workerId, createdBy: caller.actor, createdAtMs: nowMs, expiresAtMs: nowMs + 90 * 24 * 60 * 60 * 1000, authKind: 'command_center_worker_token'}, {merge: false});
    return {worker, workerToken, tokenType: 'Bearer', expiresIn: 90 * 24 * 60 * 60, warning: 'Store this worker token only on the worker host. Command Center stores only its hash.'};
  });
}

async function recordArtifact(admin, jobId, projectId, artifact) {
  const artifactId = safeText(artifact.artifactId, 180) || `artifact_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const payload = {
    artifactId,
    jobId,
    projectId,
    name: safeText(artifact.name, 240),
    kind: safeText(artifact.kind, 120) || 'file',
    uri: safeText(artifact.uri, 1000),
    sha256: safeText(artifact.sha256, 128),
    required: artifact.required === true,
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

async function leasedJobForWorker(admin, workerId) {
  const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).where('selectedWorkerId', '==', workerId).limit(25).get();
  const jobs = [];
  snap.forEach((doc) => {
    const job = doc.data();
    if (job && job.status === 'leased') jobs.push(job);
  });
  jobs.sort((a, b) => Number(a.createdAtMs || 0) - Number(b.createdAtMs || 0));
  return jobs[0] || null;
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

  server.registerTool('command_center.projects.resolve', {
    title: 'Resolve Command Center project',
    description: 'Resolve a project into a Command Center project packet. Command Center is not a chat UI and not the planner.',
    inputSchema: {projectId: z.string().optional(), name: z.string().optional(), repository: z.string().optional(), capability: z.string().optional()},
  }, async (args) => textResult(await resolveProject(admin, args || {})));

  server.registerTool('command_center.projects.get', {
    title: 'Get Command Center project',
    description: 'Read one durable Command Center project registry entry.',
    inputSchema: {projectId: z.string()},
  }, async (args) => {
    const projectId = cleanProjectId(args.projectId);
    const snap = await collection(admin, COMMAND_CENTER_COLLECTIONS.projects).doc(projectId).get();
    return textResult(snap.exists ? {projectId, found: true, project: {projectId, ...(snap.data() || {})}} : {projectId, found: false});
  });

  server.registerTool('command_center.jobs.create', {
    title: 'Create Command Center job',
    description: 'Create a durable execution ticket, select a compatible worker, lease it, and write initial events/checkpoint state.',
    inputSchema: {idempotencyKey: z.string(), projectId: z.string(), title: z.string(), objective: z.string(), acceptanceCriteria: z.array(z.string()).optional(), constraints: z.array(z.string()).optional(), scopeExclusions: z.array(z.string()).optional(), workerRequirements: z.array(z.string()).optional(), budgetClass: z.string().optional(), mutationPolicy: z.record(z.string(), z.string()).optional(), baseWorkspace: z.record(z.string(), z.any()).optional(), requiredArtifacts: z.array(z.string()).optional(), verificationCommands: z.array(z.string()).optional(), stopConditions: z.array(z.string()).optional()},
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
  }, async (args) => {
    let query = collection(admin, COMMAND_CENTER_COLLECTIONS.jobs);
    if (args.projectId) query = query.where('projectId', '==', cleanProjectId(args.projectId));
    if (args.status) query = query.where('status', '==', args.status);
    const snap = await query.orderBy('createdAtMs', 'desc').limit(Math.max(1, Math.min(Number(args.limit) || 20, 50))).get();
    const jobs = [];
    snap.forEach((doc) => jobs.push(doc.data()));
    return textResult({jobs});
  });

  server.registerTool('command_center.jobs.cancel', {title: 'Cancel Command Center job', description: 'Cancel a durable job and preserve the audit event.', inputSchema: {idempotencyKey: z.string(), jobId: z.string(), reason: z.string().optional()}}, async (args, extra) => textResult(await transitionJob(admin, await callerFromExtra(admin, extra), args || {}, 'canceled', 'jobs.cancel')));
  server.registerTool('command_center.jobs.resume', {title: 'Resume Command Center job', description: 'Resume a job from its latest checkpoint.', inputSchema: {idempotencyKey: z.string(), jobId: z.string(), reason: z.string().optional()}}, async (args, extra) => textResult(await transitionJob(admin, await callerFromExtra(admin, extra), args || {}, 'running', 'jobs.resume')));

  server.registerTool('command_center.jobs.revise', {
    title: 'Revise Command Center job',
    description: 'Revise a live ticket packet without reviving stale user intent.',
    inputSchema: {idempotencyKey: z.string(), jobId: z.string(), title: z.string().optional(), objective: z.string().optional(), acceptanceCriteria: z.array(z.string()).optional(), constraints: z.array(z.string()).optional(), scopeExclusions: z.array(z.string()).optional(), mutationPolicy: z.record(z.string(), z.string()).optional(), revisionSummary: z.string().optional()},
  }, async (args, extra) => textResult(await reviseJob(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.answer_question', {title: 'Answer Command Center job question', description: 'Record ChatGPT or human answer to a worker question and resume when appropriate.', inputSchema: {idempotencyKey: z.string(), jobId: z.string(), questionId: z.string().optional(), answer: z.string(), decision: z.string().optional()}}, async (args, extra) => textResult(await answerQuestion(admin, await callerFromExtra(admin, extra), args || {})));
  server.registerTool('command_center.jobs.authorize_mutation', {title: 'Authorize Command Center mutation', description: 'Approve or reject a requested worker mutation under the ticket mutation policy. Workers cannot silently elevate permissions.', inputSchema: {idempotencyKey: z.string(), jobId: z.string(), action: z.string(), approved: z.boolean(), reason: z.string().optional(), evidenceRefs: z.array(z.string()).optional()}}, async (args, extra) => textResult(await authorizeMutation(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.jobs.get_summary', {title: 'Get Command Center job summary', description: 'Read compact resumable worker-state checkpoint plus job status.', inputSchema: {jobId: z.string()}}, async (args) => {
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
    inputSchema: {idempotencyKey: z.string(), workerId: z.string(), engine: z.string().optional(), location: z.string().optional(), capabilities: z.array(z.string()).optional(), baseWorkspace: z.record(z.string(), z.any()).optional(), baseWorkspaces: z.array(z.record(z.string(), z.any())).optional(), limits: z.record(z.string(), z.any()).optional()},
  }, async (args, extra) => textResult(await registerOneShotWorker(admin, await callerFromExtra(admin, extra), args || {})));

  server.registerTool('command_center.workers.list', {title: 'List Command Center workers', description: 'List registered Codex workers and their health/capability metadata.', inputSchema: {}}, async () => textResult({workers: await workerRecords(admin)}));
  server.registerTool('command_center.workers.get_capabilities', {title: 'Get Command Center worker capabilities', description: 'Read capability metadata for one registered worker.', inputSchema: {workerId: z.string()}}, async (args) => {
    const workerId = safeText(args.workerId, 120);
    const workers = await workerRecords(admin);
    return textResult({worker: workers.find((worker) => worker.workerId === workerId) || null});
  });
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

  app.post('/worker/lease', async (req, res) => {
    try {
      const caller = await workerCallerFromRequest(admin, req);
      const job = await leasedJobForWorker(admin, caller.workerId);
      if (!job) {
        res.json({ok: true, leased: false});
        return;
      }
      await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(job.jobId).set({status: 'running', updatedAtMs: Date.now(), workerStartedAtMs: Date.now()}, {merge: true});
      await appendEvent(admin, {type: 'worker_started', jobId: job.jobId, projectId: job.projectId, actor: caller.workerId, summary: 'One-shot worker accepted lease.', data: {baseWorkspace: job.baseWorkspace}});
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
      for (const artifact of artifacts.slice(0, 80)) written.push(await recordArtifact(admin, jobId, job.projectId, artifact));
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
        objective: job.objective || '',
        acceptanceCriteriaStatus: Array.isArray(req.body.acceptanceCriteriaStatus) ? req.body.acceptanceCriteriaStatus : [],
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
      for (const artifact of artifacts.slice(0, 80)) written.push(await recordArtifact(admin, jobId, job.projectId, artifact));
      await collection(admin, COMMAND_CENTER_COLLECTIONS.jobs).doc(jobId).set({status, updatedAtMs: Date.now(), completedAtMs: Date.now(), finalReport, completionArtifactIds: written.map((artifact) => artifact.artifactId)}, {merge: true});
      const event = await appendEvent(admin, {type: `job_${status}`, jobId, projectId: job.projectId, actor: caller.workerId, summary: finalReport || `One-shot worker marked job ${status}.`, data: {artifactIds: written.map((artifact) => artifact.artifactId)}});
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
