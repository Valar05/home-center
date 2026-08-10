'use strict';

const {createHash, randomBytes} = require('node:crypto');

const API_VERSION = 'home-center.venice-nerve-api.v1';
const CONTRACT_VERSION = 'venice-nerve-silk.transport.v1';
const PUBLIC_ORIGIN = process.env.HOME_CENTER_VENICE_NERVE_ORIGIN || 'https://us-central1-home-center-dclar.cloudfunctions.net/veniceNerve';
const COLLECTIONS = Object.freeze({
  workers: 'veniceNerveWorkers',
  bootstrap: 'veniceNerveBootstrapCodes',
  tokens: 'veniceNerveWorkerTokens',
  turns: 'veniceNerveTurns',
});
const BOOTSTRAP_TTL_MS = 10 * 60 * 1000;
const TOKEN_TTL_MS = 90 * 24 * 60 * 60 * 1000;
const LEASE_TTL_MS = 3 * 60 * 1000;
const MAX_PROMPT_BYTES = 64 * 1024;
const MAX_RESULT_BYTES = 850 * 1024;
const MAX_ACTIONS = 32;
const CAPABILITIES = Object.freeze(['venice.turn']);

function safeText(value, max = 1200) {
  const text = value == null ? '' : String(value);
  return text.length > max ? text.slice(0, max) : text;
}
function trimmed(value, max = 1200) { return safeText(value, max).trim(); }
function hashBytes(value) { return createHash('sha256').update(Buffer.from(String(value ?? ''), 'utf8')).digest('hex'); }
function safeId(value, label = 'id') {
  const text = trimmed(value, 160);
  if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(text)) throw Object.assign(new Error(`${label} must be 6-160 safe identifier characters.`), {status: 400, failureKind: 'venice_nerve_invalid_id'});
  return text;
}
function safeEmail(value) {
  const text = trimmed(value, 320).toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) throw Object.assign(new Error('Authenticated owner email is required.'), {status: 401, failureKind: 'venice_nerve_owner_required'});
  return text;
}
function ownerKey(email) { return `owner_${hashBytes(safeEmail(email)).slice(0, 32)}`; }
function workerDocId(owner, workerId) { return hashBytes(`${owner}\n${safeId(workerId, 'workerId')}`); }
function turnDocId(owner, turnId) { return hashBytes(`${owner}\n${safeId(turnId, 'turnId')}`); }
function bodyObject(req) { return req && req.body && typeof req.body === 'object' && !Buffer.isBuffer(req.body) ? req.body : {}; }
function routePath(req) {
  const raw = trimmed(req && (req.path || req.url), 1000).split('?')[0];
  const marker = '/venice-nerve/v1/';
  const index = raw.indexOf(marker);
  return index >= 0 ? raw.slice(index + marker.length) : raw.replace(/^\/+/, '');
}
function send(res, status, body) { res.status(status).json(body); }
function bearer(req) {
  const match = String(req && typeof req.get === 'function' ? req.get('Authorization') || '' : '').match(/^Bearer\s+(.+)$/i);
  if (!match) throw Object.assign(new Error('Venice Nerve worker bearer token is required.'), {status: 401, failureKind: 'venice_nerve_worker_auth_required'});
  return match[1];
}
function normalizeActions(value) {
  if (value == null) return [];
  if (!Array.isArray(value)) throw Object.assign(new Error('actions must be an array.'), {status: 400, failureKind: 'venice_nerve_invalid_actions'});
  if (value.length > MAX_ACTIONS) throw Object.assign(new Error(`actions exceeds ${MAX_ACTIONS} items.`), {status: 413, failureKind: 'venice_nerve_actions_too_large'});
  return value.map((item, index) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) throw Object.assign(new Error(`actions[${index}] must be an object.`), {status: 400, failureKind: 'venice_nerve_invalid_actions'});
    const actionId = safeId(item.actionId || `action-${index + 1}-${hashBytes(JSON.stringify(item)).slice(0, 12)}`, `actions[${index}].actionId`);
    const verb = trimmed(item.verb, 120);
    if (!/^[a-z][a-z0-9_.:-]{1,119}$/i.test(verb)) throw Object.assign(new Error(`actions[${index}].verb is invalid.`), {status: 400, failureKind: 'venice_nerve_invalid_actions'});
    const args = item.args && typeof item.args === 'object' && !Array.isArray(item.args) ? item.args : {};
    return {actionId, verb, args};
  });
}
function safeDiagnostics(value) {
  const input = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const out = {};
  for (const key of ['workstationThreadId', 'workstationJobId', 'durableTurnRecord', 'apertureScriptSha256', 'workstationVersion']) {
    const text = trimmed(input[key], key === 'durableTurnRecord' ? 1600 : 300);
    if (text) out[key] = text;
  }
  if (Number.isFinite(Number(input.elapsedMs))) out.elapsedMs = Math.max(0, Math.floor(Number(input.elapsedMs)));
  return out;
}

async function registerWorkerOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId');
  const email = safeEmail(user && user.email);
  const owner = ownerKey(email);
  const workerId = safeId(args.workerId || 'windows-venice-nerve-01', 'workerId');
  const code = randomBytes(24).toString('base64url');
  const digest = hashBytes(code);
  const expiresAtMs = nowMs + BOOTSTRAP_TTL_MS;
  const workerRef = admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId));
  const bootstrapRef = admin.firestore().collection(COLLECTIONS.bootstrap).doc(digest);
  await admin.firestore().runTransaction(async (tx) => {
    tx.set(workerRef, {apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, workerId, ownerKey: owner, ownerEmail: email, capabilities: CAPABILITIES, fileLayer: 'drive_sync', state: 'bootstrap_pending', requestId, createdAtMs: nowMs, updatedAtMs: nowMs, lastSeenAtMs: 0}, {merge: true});
    tx.set(bootstrapRef, {digest, workerRef: workerRef.path, workerId, ownerKey: owner, ownerEmail: email, expiresAtMs, usedAtMs: 0, createdAtMs: nowMs}, {merge: false});
  });
  return {status: 'bootstrap_ready', workerId, contractVersion: CONTRACT_VERSION, origin: PUBLIC_ORIGIN, bootstrapCode: code, bootstrapExpiresAtMs: expiresAtMs, capabilities: CAPABILITIES, fileLayer: 'drive_sync'};
}

async function exchangeBootstrap({admin, args = {}, nowMs = Date.now()}) {
  const code = trimmed(args.bootstrapCode, 300);
  const workerId = safeId(args.workerId, 'workerId');
  if (!code) throw Object.assign(new Error('bootstrapCode is required.'), {status: 400});
  const ref = admin.firestore().collection(COLLECTIONS.bootstrap).doc(hashBytes(code));
  const token = randomBytes(32).toString('base64url');
  const tokenDigest = hashBytes(token);
  let record;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (!snap.exists) throw Object.assign(new Error('Bootstrap code was not found.'), {status: 404});
    record = snap.data() || {};
    if (record.workerId !== workerId) throw Object.assign(new Error('Bootstrap worker mismatch.'), {status: 403});
    if (record.usedAtMs) throw Object.assign(new Error('Bootstrap code was already used.'), {status: 409});
    if (Number(record.expiresAtMs || 0) <= nowMs) throw Object.assign(new Error('Bootstrap code expired.'), {status: 410});
    tx.set(admin.firestore().collection(COLLECTIONS.tokens).doc(tokenDigest), {tokenDigest, workerId, ownerKey: record.ownerKey, ownerEmail: record.ownerEmail, capabilities: CAPABILITIES, createdAtMs: nowMs, expiresAtMs: nowMs + TOKEN_TTL_MS, revokedAtMs: 0}, {merge: false});
    tx.update(ref, {usedAtMs: nowMs, tokenDigest});
    tx.set(admin.firestore().doc(record.workerRef), {state: 'registered', tokenDigest, updatedAtMs: nowMs, lastSeenAtMs: nowMs}, {merge: true});
  });
  return {status: 'registered', workerId, token, origin: PUBLIC_ORIGIN, contractVersion: CONTRACT_VERSION, expiresAtMs: nowMs + TOKEN_TTL_MS};
}

async function authenticateWorker(admin, req, nowMs = Date.now()) {
  const snap = await admin.firestore().collection(COLLECTIONS.tokens).doc(hashBytes(bearer(req))).get();
  if (!snap.exists) throw Object.assign(new Error('Worker token is invalid.'), {status: 401});
  const worker = snap.data() || {};
  if (worker.revokedAtMs || Number(worker.expiresAtMs || 0) <= nowMs) throw Object.assign(new Error('Worker token is inactive.'), {status: 401});
  const headerWorker = safeId(req.get('X-Home-Center-Worker') || worker.workerId, 'workerId');
  if (headerWorker !== worker.workerId) throw Object.assign(new Error('Worker identity mismatch.'), {status: 403});
  return worker;
}

async function workerStatusOperation({admin, user, args = {}}) {
  const owner = ownerKey(safeEmail(user && user.email));
  const workerId = safeId(args.workerId || 'windows-venice-nerve-01', 'workerId');
  const snap = await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId)).get();
  if (!snap.exists) return {workerId, status: 'not_registered', online: false, capabilities: CAPABILITIES, fileLayer: 'drive_sync', queueDepth: 0};
  const row = snap.data() || {};
  const lastSeenAtMs = Number(row.lastSeenAtMs || 0);
  const updatedAtMs = Number(row.updatedAtMs || 0);
  const state = trimmed(row.state, 80) || 'unknown';
  const onlineFreshnessMs = ['running', 'leased'].includes(state) ? LEASE_TTL_MS + 15000 : 30000;
  const heartbeatAtMs = Math.max(lastSeenAtMs, ['running', 'leased'].includes(state) ? updatedAtMs : 0);
  const online = heartbeatAtMs > 0 && Date.now() - heartbeatAtMs < onlineFreshnessMs;
  const pending = await admin.firestore().collection(COLLECTIONS.turns).where('ownerKey', '==', owner).limit(100).get();
  const queueDepth = pending.docs.map((doc) => doc.data() || {}).filter((item) => item.workerId === workerId && ['queued', 'leased', 'running'].includes(item.status)).length;
  return {workerId, status: state, online, lastSeenAtMs, updatedAtMs, onlineFreshnessMs, workerVersion: trimmed(row.workerVersion, 120), machine: row.machine || null, capabilities: CAPABILITIES, fileLayer: 'drive_sync', queueDepth};
}

async function createTurnOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId');
  const owner = ownerKey(safeEmail(user && user.email));
  const workerId = safeId(args.workerId || 'windows-venice-nerve-01', 'workerId');
  const prompt = safeText(args.prompt, 70000);
  if (!prompt || Buffer.byteLength(prompt, 'utf8') > MAX_PROMPT_BYTES) throw Object.assign(new Error(`prompt is required and must be <= ${MAX_PROMPT_BYTES} UTF-8 bytes.`), {status: 400, failureKind: 'venice_nerve_invalid_prompt'});
  const threadTitle = trimmed(args.threadTitle || 'ChatGPT Aperture', 200) || 'ChatGPT Aperture';
  const timeoutSeconds = Math.max(5, Math.min(110, Math.floor(Number(args.timeoutSeconds || 95))));
  const turnId = safeId(args.turnId || `venice-${requestId}`, 'turnId');
  const ref = admin.firestore().collection(COLLECTIONS.turns).doc(turnDocId(owner, turnId));
  let idempotent = false;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (snap.exists) {
      const old = snap.data() || {};
      if (old.requestId !== requestId || old.workerId !== workerId || old.promptSha256 !== hashBytes(prompt) || old.threadTitle !== threadTitle) throw Object.assign(new Error('Venice Nerve idempotency conflict.'), {status: 409});
      idempotent = true;
      return;
    }
    tx.create(ref, {
      apiVersion: API_VERSION,
      contractVersion: CONTRACT_VERSION,
      turnId,
      requestId,
      ownerKey: owner,
      workerId,
      prompt,
      promptSha256: hashBytes(prompt),
      threadTitle,
      timeoutSeconds,
      status: 'queued',
      cancelRequested: false,
      createdAtMs: nowMs,
      updatedAtMs: nowMs,
      lease: null,
      result: null,
    });
  });
  const row = (await ref.get()).data() || {};
  return {turnId, requestId, workerId, status: row.status, idempotent, promptSha256: row.promptSha256, fileLayer: 'drive_sync'};
}

async function turnStatusOperation({admin, user, args = {}}) {
  const owner = ownerKey(safeEmail(user && user.email));
  const turnId = safeId(args.turnId || `venice-${safeId(args.requestId, 'requestId')}`, 'turnId');
  const snap = await admin.firestore().collection(COLLECTIONS.turns).doc(turnDocId(owner, turnId)).get();
  if (!snap.exists) throw Object.assign(new Error('Venice Nerve turn was not found.'), {status: 404});
  const row = snap.data() || {};
  return {turnId, requestId: row.requestId, workerId: row.workerId, status: row.status, promptSha256: row.promptSha256, result: row.result || null, cancelRequested: row.cancelRequested === true, updatedAtMs: row.updatedAtMs, fileLayer: 'drive_sync'};
}

async function cancelTurnOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const owner = ownerKey(safeEmail(user && user.email));
  const turnId = safeId(args.turnId || `venice-${safeId(args.targetRequestId || args.requestId, 'requestId')}`, 'turnId');
  const ref = admin.firestore().collection(COLLECTIONS.turns).doc(turnDocId(owner, turnId));
  let result;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (!snap.exists) throw Object.assign(new Error('Venice Nerve turn was not found.'), {status: 404});
    const row = snap.data() || {};
    if (['completed', 'failed', 'cancelled'].includes(row.status)) { result = {turnId, status: row.status, idempotent: true}; return; }
    tx.set(ref, {status: 'cancelled', cancelRequested: true, cancelReason: trimmed(args.reason, 300), updatedAtMs: nowMs}, {merge: true});
    result = {turnId, status: 'cancelled', idempotent: false};
  });
  return result;
}

async function leaseTurn({admin, worker, nowMs = Date.now()}) {
  const workerRef = admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId));
  const query = await admin.firestore().collection(COLLECTIONS.turns).where('ownerKey', '==', worker.ownerKey).limit(100).get();
  const eligible = query.docs.map((doc) => ({ref: doc.ref, row: doc.data() || {}})).filter((item) => {
    if (item.row.workerId !== worker.workerId || item.row.cancelRequested === true || item.row.status === 'cancelled') return false;
    if (item.row.status === 'queued') return true;
    return ['leased', 'running'].includes(item.row.status) && (!item.row.lease || Number(item.row.lease.expiresAtMs || 0) <= nowMs);
  }).sort((a, b) => Number(a.row.createdAtMs || 0) - Number(b.row.createdAtMs || 0));
  for (const item of eligible) {
    let leased = null;
    await admin.firestore().runTransaction(async (tx) => {
      const snap = await tx.get(item.ref);
      if (!snap.exists) return;
      const row = snap.data() || {};
      const active = row.lease && Number(row.lease.expiresAtMs || 0) > nowMs;
      if (row.cancelRequested === true || row.status === 'cancelled' || active) return;
      leased = {...row, status: 'leased', lease: {workerId: worker.workerId, leasedAtMs: nowMs, expiresAtMs: nowMs + LEASE_TTL_MS}, updatedAtMs: nowMs};
      tx.set(item.ref, leased, {merge: false});
    });
    if (leased) {
      await workerRef.set({state: 'leased', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
      return {turn: {turnId: leased.turnId, requestId: leased.requestId, prompt: leased.prompt, promptSha256: leased.promptSha256, threadTitle: leased.threadTitle, timeoutSeconds: leased.timeoutSeconds}, pollAfterSeconds: 1};
    }
  }
  await workerRef.set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {turn: null, pollAfterSeconds: 2};
}

async function turnForWorker(admin, worker, turnId) {
  const ref = admin.firestore().collection(COLLECTIONS.turns).doc(turnDocId(worker.ownerKey, turnId));
  const snap = await ref.get();
  if (!snap.exists) throw Object.assign(new Error('Venice Nerve turn was not found.'), {status: 404});
  const row = snap.data() || {};
  if (row.workerId !== worker.workerId) throw Object.assign(new Error('Venice Nerve worker mismatch.'), {status: 403});
  return {ref, row};
}
async function heartbeat({admin, worker, turnId, args = {}, nowMs = Date.now()}) {
  const found = await turnForWorker(admin, worker, turnId);
  if (found.row.cancelRequested === true || found.row.status === 'cancelled') return {turnId, status: 'cancelled', cancelRequested: true};
  const lease = found.row.lease || {};
  if (lease.workerId !== worker.workerId) throw Object.assign(new Error('Worker does not own this lease.'), {status: 409});
  await found.ref.set({status: 'running', phase: trimmed(args.phase, 80) || 'running', lease: {...lease, expiresAtMs: nowMs + LEASE_TTL_MS}, updatedAtMs: nowMs}, {merge: true});
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'running', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {turnId, status: 'running', cancelRequested: false};
}

async function completeTurn({admin, worker, turnId, args = {}, nowMs = Date.now()}) {
  const found = await turnForWorker(admin, worker, turnId);
  if (found.row.cancelRequested === true || found.row.status === 'cancelled') return {turnId, status: 'cancelled', discarded: true};
  if (!found.row.lease || found.row.lease.workerId !== worker.workerId) throw Object.assign(new Error('Worker does not own this lease.'), {status: 409});
  const workerResult = args.result && typeof args.result === 'object' && !Array.isArray(args.result) ? args.result : {};
  const ok = workerResult.ok === true;
  let result;
  if (ok) {
    const speechText = safeText(workerResult.speech && workerResult.speech.text, 64000);
    if (!speechText) throw Object.assign(new Error('Successful Venice Nerve result requires exact speech.text.'), {status: 400, failureKind: 'venice_nerve_speech_missing'});
    const computedSha = hashBytes(speechText);
    const suppliedSha = trimmed(workerResult.speech && workerResult.speech.sha256, 64).toLowerCase();
    if (suppliedSha && suppliedSha !== computedSha) throw Object.assign(new Error('Worker speech SHA-256 did not match exact UTF-8 speech bytes.'), {status: 409, failureKind: 'venice_nerve_speech_hash_mismatch'});
    result = {
      schema: 'venice.body-turn.v1',
      turnId,
      speech: {text: speechText, source: 'local-venice', transformedByOrchestrator: false, sha256: computedSha},
      actions: normalizeActions(workerResult.actions),
      observations: Array.isArray(workerResult.observations) ? workerResult.observations.slice(0, 64) : [],
      diagnostics: {workerId: worker.workerId, ...safeDiagnostics(workerResult.diagnostics)},
    };
  } else {
    result = {ok: false, error: trimmed(workerResult.error, 160) || 'venice_nerve_worker_failed', detail: safeText(workerResult.detail, 2000)};
  }
  const bytes = Buffer.byteLength(JSON.stringify(result), 'utf8');
  if (bytes > MAX_RESULT_BYTES) throw Object.assign(new Error('Venice Nerve result envelope is too large.'), {status: 413});
  const status = ok ? 'completed' : 'failed';
  await found.ref.set({status, lease: null, result, completedAtMs: nowMs, updatedAtMs: nowMs, prompt: null}, {merge: true});
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {turnId, status, resultBytes: bytes};
}

function veniceNerveOperationEntries() {
  return {
    'venice_nerve.worker.register': {summary: 'Mint a ten-minute bootstrap for the dedicated outbound local Venice Nerve worker. This worker carries speech only; Computer Hands remains the body.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'optional windows-venice-nerve-01'}},
    'venice_nerve.worker.status': {summary: 'Read dedicated Venice Nerve worker heartbeat and queue evidence.', write: false, requiresRequestId: false, requiredScopes: [], input: {workerId: 'optional windows-venice-nerve-01'}},
    'venice_nerve.turn.create': {summary: 'Queue one prompt for local Venice. Exact local speech is returned unchanged in turn.status after completion; actions remain structured data.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'optional', prompt: 'exact prompt', threadTitle: 'optional', timeoutSeconds: '5-110'}},
    'venice_nerve.turn.status': {summary: 'Read one Venice Nerve turn including exact local speech SHA-256 and separate structured actions.', write: false, requiresRequestId: false, requiredScopes: [], input: {turnId: 'turn id', requestId: 'request id alias'}},
    'venice_nerve.turn.cancel': {summary: 'Cancel one queued or running Venice Nerve turn.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'audit id', turnId: 'target turn', targetRequestId: 'target request alias', reason: 'optional'}},
  };
}
async function veniceNerveOperationRunOperation({admin, user, operation, args = {}}) {
  if (operation === 'venice_nerve.worker.register') return registerWorkerOperation({admin, user, args});
  if (operation === 'venice_nerve.worker.status') return workerStatusOperation({admin, user, args});
  if (operation === 'venice_nerve.turn.create') return createTurnOperation({admin, user, args});
  if (operation === 'venice_nerve.turn.status') return turnStatusOperation({admin, user, args});
  if (operation === 'venice_nerve.turn.cancel') return cancelTurnOperation({admin, user, args});
  throw Object.assign(new Error('Unsupported Venice Nerve operation.'), {status: 400});
}

function createVeniceNerveHandler({admin}) {
  return async (req, res) => {
    try {
      const path = routePath(req);
      if (req.method === 'GET' && path === 'health') return send(res, 200, {ok: true, service: 'venice-nerve', apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, fileLayer: 'drive_sync', capabilities: CAPABILITIES});
      if (req.method === 'POST' && path === 'bootstrap') return send(res, 200, await exchangeBootstrap({admin, args: bodyObject(req)}));
      const worker = await authenticateWorker(admin, req);
      if (req.method === 'POST' && path === 'lease') return send(res, 200, await leaseTurn({admin, worker}));
      const match = path.match(/^turns\/([^/]+)\/(heartbeat|complete)$/);
      if (req.method === 'POST' && match && match[2] === 'heartbeat') return send(res, 200, await heartbeat({admin, worker, turnId: match[1], args: bodyObject(req)}));
      if (req.method === 'POST' && match && match[2] === 'complete') return send(res, 200, await completeTurn({admin, worker, turnId: match[1], args: bodyObject(req)}));
      return send(res, 404, {ok: false, error: 'venice_nerve_route_not_found'});
    } catch (error) {
      return send(res, Number(error.status) || 500, {ok: false, error: error.failureKind || error.code || 'venice_nerve_failed', detail: safeText(error.message || String(error), 500)});
    }
  };
}

module.exports = {
  API_VERSION,
  CONTRACT_VERSION,
  PUBLIC_ORIGIN,
  COLLECTIONS,
  CAPABILITIES,
  hashBytes,
  ownerKey,
  normalizeActions,
  veniceNerveOperationEntries,
  veniceNerveOperationRunOperation,
  registerWorkerOperation,
  workerStatusOperation,
  createTurnOperation,
  turnStatusOperation,
  createVeniceNerveHandler,
};
