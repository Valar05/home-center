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
const COMMAND_CENTER_MCP_SERVER_VERSION = '0.2.0';
const HOME_CENTER_AUTHORIZATION_SERVER_BASE = process.env.HOME_CENTER_MCP_PUBLIC_BASE || 'https://us-central1-home-center-dclar.cloudfunctions.net/homeCenterMcp';
const COMMAND_CENTER_COLLECTIONS = Object.freeze({
  projects: 'commandCenterProjects',
  events: 'commandCenterEvents',
  bucketObjects: 'commandCenterBucketObjects',
  appControlProfiles: APP_CONTROL_COLLECTIONS.profiles,
  appControlRuns: APP_CONTROL_COLLECTIONS.runs,
  browserSessions: 'browserSessions',
  browserEpisodes: 'browserEpisodes',
  browserDiscoveries: 'browserDiscoveries',
  browserPlaybooks: 'browserPlaybooks',
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
    'memory/current-condensed': {kind: 'memory.current_condensed', role: 'latest compact resumable state per project'},
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

function cleanProjectId(value, repository = '') {
  const projectId = slug(safeText(value, 120) || repository, 'project');
  if (!/^[a-z0-9][a-z0-9-]{1,118}[a-z0-9]$/.test(projectId)) {
    const err = new Error('A valid projectId is required.');
    err.status = 400;
    throw err;
  }
  return projectId;
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

function cleanProjectPacket(args = {}) {
  const repository = safeText(args.repository, 240);
  const projectId = cleanProjectId(args.projectId, repository || args.name || 'project');
  return {
    projectId,
    name: safeText(args.name, 200) || repository || projectId,
    repository,
    capability: safeText(args.capability, 200),
    repositoryBinding: safeObject(args.repositoryBinding),
    currentBranch: safeText(args.currentBranch, 120),
    projectPacketRefs: safeList(args.projectPacketRefs, 80, 800),
    recentRelevantOutcomes: Array.isArray(args.recentRelevantOutcomes) ? args.recentRelevantOutcomes.slice(0, 50).map((outcome) => safeObject(outcome)) : [],
    durable: args.durable !== false,
    updatedAtMs: Date.now(),
    createdAtMs: Number(args.createdAtMs || 0) || Date.now(),
  };
}

async function appendEvent(admin, event) {
  const eventId = `evt_${Date.now()}_${randomUUID().slice(0, 8)}`;
  const payload = {
    eventId,
    type: safeText(event.type, 120),
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
    await appendEvent(admin, {type: 'bucket_object_written', projectId: object.projectId, actor: caller.actor, summary: object.title, evidenceRefs: [`bucket://${object.bucketId}/${object.path}`], data: {objectId: object.objectId, kind: object.kind, path: object.path}});
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
    await appendEvent(admin, {type: 'browser_action_' + status, projectId: 'home-center', actor: caller.actor, summary: `${action}: ${status}`, data: payload});
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
      currentBranch: '',
      projectPacketRefs: [],
      recentRelevantOutcomes: [],
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

function normalizeCommandCenterOperationName(value) {
  return safeText(value, 180).replace(/^command_center\./, '');
}

const RETIRED_RENDER_OPERATIONS = new Set(['render.blender_glb', 'render.blender_build', 'render.status', 'render.reconcile']);
function assertNotRetiredOperation(operation) {
  if (!RETIRED_RENDER_OPERATIONS.has(operation)) return;
  const error = new Error('This rendering capability is retired. Use Home Center drive_operation with blender.workspace.create, blender.workspace.mutate, blender.workspace.render, or blender.workspace.export.');
  error.status = 410;
  error.code = 'capability_retired.use_blender_workspace';
  throw error;
}

async function runCommandCenterOperation(admin, extra, operation, args = {}) {
  const op = normalizeCommandCenterOperationName(operation);
  assertNotRetiredOperation(op);
  if (['agents.', 'workers.', 'hosts.', 'jobs.', 'machine_images.', 'provisioning.', 'codex_sessions.', 'routing.', 'proof.'].some((prefix) => op.startsWith(prefix))) { const error = new Error('Command Center Codex workers are retired.'); error.status = 410; error.code = 'capability_retired.command_center_codex'; throw error; }
  const caller = async () => callerFromExtra(admin, extra);
  switch (op) {
    case 'health':
    case 'system.health':
      return commandCenterHealthPayload();
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

function commandCenterHealthPayload() {
  return {ok: true, service: 'command-center-mcp', version: COMMAND_CENTER_MCP_SERVER_VERSION, hasFrontend: false};
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
    diagnosticsOperation: 'system.health',
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
    description: 'Create or update a durable Command Center project binding with repository, capability.',
    inputSchema: {idempotencyKey: z.string(), projectId: z.string(), name: z.string().optional(), repository: z.string().optional(), capability: z.string().optional(), repositoryBinding: z.record(z.string(), z.any()).optional(), currentBranch: z.string().optional(), projectPacketRefs: z.array(z.string()).optional(), recentRelevantOutcomes: z.array(z.record(z.string(), z.any())).optional(), durable: z.boolean().optional()},
  }, async (args, extra) => textResult(await upsertProject(admin, await callerFromExtra(admin, extra), args || {})));

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
    inputSchema: {bucketId: z.string().optional(), kind: z.enum(COMMAND_CENTER_BUCKET_KINDS).optional(), projectId: z.string().optional(), repository: z.string().optional(), tag: z.string().optional(), limit: z.number().optional()},
  }, async (args, extra) => textResult(await listBucketObjects(admin, args || {}, await callerFromExtra(admin, extra))));

  server.registerTool('command_center.bucket.promote_skill', {
    title: 'Promote Command Center scratch skill',
    description: 'Promote a scratch skill bucket object into the promoted skill lane while preserving provenance and supersession links.',
    inputSchema: {idempotencyKey: z.string(), objectId: z.string(), path: z.string().optional(), title: z.string().optional(), summary: z.string().optional(), body: z.string().optional(), evidenceRefs: z.array(z.string()).optional()},
  }, async (args, extra) => textResult(await promoteBucketSkill(admin, await callerFromExtra(admin, extra), args || {})));


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
    inputSchema: {idempotencyKey: z.string(), sessionId: z.string(), actionId: z.string().optional(), action: z.string(), target: z.record(z.string(), z.any()).optional(), value: z.string().optional(), reason: z.string().optional()},
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

  const retiredCodexExecution = (_req, res) => res.status(410).json({ok: false, code: 'capability_retired.command_center_codex', message: 'Command Center Codex agents, jobs, sessions, and workers are permanently retired.'});
  app.all('/agent/:operation', retiredCodexExecution);
  app.all('/worker/:operation', retiredCodexExecution);

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
  commandCenterHealthPayload,
  commandCenterReadinessPayload,
  commandCenterCapabilitiesPayload,
  COMMAND_CENTER_ALLOWED_EMAILS,
  requireCommandCenterAllowedEmail,
  COMMAND_CENTER_COLLECTIONS,
  COMMAND_CENTER_DEFAULT_PROJECTS,
  COMMAND_CENTER_DEFAULT_BUCKET_ID,
  COMMAND_CENTER_BUCKET_KINDS,
  COMMAND_CENTER_BUCKET_LAYOUT,
  cleanAppControlProfile,
  cleanBrowserEpisode,
  cleanBrowserPlaybook,
  cleanProjectPacket,
  lookupBrowserPlaybook,
  createCommandCenterMcpApp,
  createCommandCenterMcpServer,
  cleanBucketObject,
  ownerKeyFromActor,
  ownerKeyFromCaller,
  attachOwnerKey,
  assertOwnerAccess,
};
