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
  baseWorkspaces: 'commandCenterBaseWorkspaces',
  workerTokens: 'commandCenterWorkerTokens',
  idempotency: 'commandCenterIdempotency',
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
  return payload;
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
    const job = await getJob(admin, jobId);
    return textResult({jobId, status: job.status, checkpoint: await getLatestCheckpoint(admin, jobId), job});
  });
  server.registerTool('command_center.jobs.get_events', {title: 'Get Command Center job events', description: 'Read structured job events generated from Command Center state, not another chat agent.', inputSchema: {jobId: z.string(), limit: z.number().optional()}}, async (args) => textResult({events: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.events, cleanJobId(args.jobId), Math.max(1, Math.min(Number(args.limit) || 50, 100)))}));
  server.registerTool('command_center.jobs.get_logs', {title: 'Get Command Center job logs', description: 'Read append-only log metadata for a job.', inputSchema: {jobId: z.string(), limit: z.number().optional()}}, async (args) => textResult({logs: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.logs, cleanJobId(args.jobId), Math.max(1, Math.min(Number(args.limit) || 50, 100)))}));
  server.registerTool('command_center.jobs.get_artifacts', {title: 'Get Command Center job artifacts', description: 'Read artifact metadata and object references for a job.', inputSchema: {jobId: z.string(), limit: z.number().optional()}}, async (args) => textResult({artifacts: await listByJob(admin, COMMAND_CENTER_COLLECTIONS.artifacts, cleanJobId(args.jobId), Math.max(1, Math.min(Number(args.limit) || 50, 100)))}));
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
      const event = await appendEvent(admin, {type: req.body.type || 'worker_event', jobId, projectId: job.projectId, actor: caller.workerId, summary: req.body.summary || '', evidenceRefs: req.body.evidenceRefs || [], requiresHumanDecision: req.body.requiresHumanDecision === true, recommendedAction: req.body.recommendedAction || '', data: safeObject(req.body.data)});
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
      res.json({ok: true, checkpoint});
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

module.exports = {COMMAND_CENTER_COLLECTIONS, COMMAND_CENTER_DEFAULT_WORKERS, COMMAND_CENTER_REQUIRED_ARTIFACTS, COMMAND_CENTER_DEFAULT_BASE_WORKSPACE, createCommandCenterMcpApp, createCommandCenterMcpServer, cleanBaseWorkspace, cleanMutationPolicy, cleanOneShotExecution, selectWorker};
