'use strict';

const {createHash, randomBytes} = require('node:crypto');

const API_VERSION = 'home-center.browser-nerve-api.v1';
const CONTRACT_VERSION = 'home-center.browser-nerve-contract.v1';
const PUBLIC_ORIGIN = process.env.HOME_CENTER_BROWSER_NERVE_ORIGIN || 'https://us-central1-home-center-dclar.cloudfunctions.net/browserNerve';
const COLLECTIONS = Object.freeze({
  workers: 'browserNerveWorkers',
  bootstrap: 'browserNerveBootstrapCodes',
  tokens: 'browserNerveWorkerTokens',
  tickets: 'browserNerveTickets',
  sessions: 'browserSessions',
  episodes: 'browserEpisodes',
});
const BOOTSTRAP_TTL_MS = 10 * 60 * 1000;
const TOKEN_TTL_MS = 90 * 24 * 60 * 60 * 1000;
const LEASE_TTL_MS = 3 * 60 * 1000;
const MAX_RESULT_BYTES = 500 * 1024;
const SUPPORTED_ACTIONS = Object.freeze(['navigate', 'observe', 'find', 'read', 'click', 'type', 'select', 'submit', 'scroll', 'wait_for']);

function safeText(value, max = 2000) {
  const text = value == null ? '' : String(value).trim();
  return text.length > max ? text.slice(0, max) : text;
}
function safeObject(value) { return value && typeof value === 'object' && !Array.isArray(value) ? value : {}; }
function hash(value) { return createHash('sha256').update(String(value || '')).digest('hex'); }
function safeId(value, label = 'id') {
  const text = safeText(value, 180);
  if (!/^[A-Za-z0-9_.:-]{6,180}$/.test(text)) throw Object.assign(new Error(`${label} must be 6-180 safe identifier characters.`), {status: 400, failureKind: 'browser_nerve_invalid_id'});
  return text;
}
function safeEmail(value) {
  const text = safeText(value, 320).toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) throw Object.assign(new Error('Authenticated owner email is required.'), {status: 401, failureKind: 'browser_nerve_owner_required'});
  return text;
}
function ownerKey(email) { return `owner_${hash(safeEmail(email)).slice(0, 32)}`; }
function workerDocId(owner, workerId) { return hash(`${owner}\n${safeId(workerId, 'workerId')}`); }
function ticketDocId(owner, ticketId) { return hash(`${owner}\n${safeId(ticketId, 'ticketId')}`); }
function bodyObject(req) { return req && req.body && typeof req.body === 'object' && !Buffer.isBuffer(req.body) ? req.body : {}; }
function routePath(req) {
  const raw = safeText(req && (req.path || req.url), 1000).split('?')[0];
  const marker = '/browser-nerve/v1/';
  const index = raw.indexOf(marker);
  return index >= 0 ? raw.slice(index + marker.length) : raw.replace(/^\/+/, '');
}
function send(res, status, body) { res.status(status).json(body); }
function bearer(req) {
  const match = String(req && typeof req.get === 'function' ? req.get('Authorization') || '' : '').match(/^Bearer\s+(.+)$/i);
  if (!match) throw Object.assign(new Error('Browser Nerve worker bearer token is required.'), {status: 401, failureKind: 'browser_nerve_worker_auth_required'});
  return match[1];
}
function actionName(value) {
  const action = safeText(value, 80).toLowerCase();
  if (!SUPPORTED_ACTIONS.includes(action)) throw Object.assign(new Error(`Unsupported Browser Nerve action: ${action}`), {status: 400, failureKind: 'browser_nerve_action_unsupported'});
  return action;
}
function safeOrigin(url) {
  try { return new URL(url).origin; } catch { return ''; }
}

async function registerWorkerOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId');
  const email = safeEmail(user && user.email);
  const owner = ownerKey(email);
  const workerId = safeId(args.workerId || 'windows-browser-nerve-01', 'workerId');
  const code = randomBytes(24).toString('base64url');
  const digest = hash(code);
  const expiresAtMs = nowMs + BOOTSTRAP_TTL_MS;
  const workerRef = admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId));
  const bootstrapRef = admin.firestore().collection(COLLECTIONS.bootstrap).doc(digest);
  await admin.firestore().runTransaction(async (tx) => {
    tx.set(workerRef, {
      apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, workerId, ownerKey: owner, ownerEmail: email,
      capabilities: SUPPORTED_ACTIONS, selectorPolicy: 'aria_role_name_then_testid_id_css_then_text',
      state: 'bootstrap_pending', requestId, createdAtMs: nowMs, updatedAtMs: nowMs, lastSeenAtMs: 0,
    }, {merge: true});
    tx.set(bootstrapRef, {digest, workerRef: workerRef.path, workerId, ownerKey: owner, ownerEmail: email, expiresAtMs, usedAtMs: 0, createdAtMs: nowMs}, {merge: false});
  });
  return {status: 'bootstrap_ready', workerId, contractVersion: CONTRACT_VERSION, origin: PUBLIC_ORIGIN, bootstrapCode: code, bootstrapExpiresAtMs: expiresAtMs, capabilities: SUPPORTED_ACTIONS};
}

async function exchangeBootstrap({admin, args = {}, nowMs = Date.now()}) {
  const code = safeText(args.bootstrapCode, 300);
  const workerId = safeId(args.workerId, 'workerId');
  if (!code) throw Object.assign(new Error('bootstrapCode is required.'), {status: 400});
  const ref = admin.firestore().collection(COLLECTIONS.bootstrap).doc(hash(code));
  const token = randomBytes(32).toString('base64url');
  const tokenDigest = hash(token);
  let record;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (!snap.exists) throw Object.assign(new Error('Bootstrap code was not found.'), {status: 404});
    record = snap.data() || {};
    if (record.workerId !== workerId) throw Object.assign(new Error('Bootstrap worker mismatch.'), {status: 403});
    if (record.usedAtMs) throw Object.assign(new Error('Bootstrap code was already used.'), {status: 409});
    if (Number(record.expiresAtMs || 0) <= nowMs) throw Object.assign(new Error('Bootstrap code expired.'), {status: 410});
    tx.set(admin.firestore().collection(COLLECTIONS.tokens).doc(tokenDigest), {
      tokenDigest, workerId, ownerKey: record.ownerKey, ownerEmail: record.ownerEmail, capabilities: SUPPORTED_ACTIONS,
      createdAtMs: nowMs, expiresAtMs: nowMs + TOKEN_TTL_MS, revokedAtMs: 0,
    }, {merge: false});
    tx.update(ref, {usedAtMs: nowMs, tokenDigest});
    tx.set(admin.firestore().doc(record.workerRef), {state: 'registered', tokenDigest, updatedAtMs: nowMs, lastSeenAtMs: nowMs}, {merge: true});
  });
  return {status: 'registered', workerId, token, origin: PUBLIC_ORIGIN, contractVersion: CONTRACT_VERSION, expiresAtMs: nowMs + TOKEN_TTL_MS};
}

async function authenticateWorker(admin, req, nowMs = Date.now()) {
  const snap = await admin.firestore().collection(COLLECTIONS.tokens).doc(hash(bearer(req))).get();
  if (!snap.exists) throw Object.assign(new Error('Worker token is invalid.'), {status: 401});
  const worker = snap.data() || {};
  if (worker.revokedAtMs || Number(worker.expiresAtMs || 0) <= nowMs) throw Object.assign(new Error('Worker token is inactive.'), {status: 401});
  const headerWorker = safeId(req.get('X-Home-Center-Worker') || worker.workerId, 'workerId');
  if (headerWorker !== worker.workerId) throw Object.assign(new Error('Worker identity mismatch.'), {status: 403});
  return worker;
}

async function workerStatusOperation({admin, user, args = {}}) {
  const owner = ownerKey(safeEmail(user && user.email));
  const workerId = safeId(args.workerId || 'windows-browser-nerve-01', 'workerId');
  const snap = await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId)).get();
  if (!snap.exists) return {workerId, status: 'not_registered', online: false, capabilities: SUPPORTED_ACTIONS, queueDepth: 0};
  const row = snap.data() || {};
  const lastSeenAtMs = Number(row.lastSeenAtMs || 0);
  const updatedAtMs = Number(row.updatedAtMs || 0);
  const state = safeText(row.state, 80) || 'unknown';
  const freshnessMs = ['running', 'leased'].includes(state) ? LEASE_TTL_MS + 15000 : 30000;
  const heartbeatAtMs = Math.max(lastSeenAtMs, ['running', 'leased'].includes(state) ? updatedAtMs : 0);
  const online = heartbeatAtMs > 0 && Date.now() - heartbeatAtMs < freshnessMs;
  const pending = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', owner).limit(100).get();
  const rows = pending.docs.map((doc) => doc.data() || {}).filter((item) => item.workerId === workerId && ['queued', 'leased', 'running'].includes(item.status));
  return {
    workerId, status: state, online, lastSeenAtMs, updatedAtMs, onlineFreshnessMs: freshnessMs,
    workerVersion: safeText(row.workerVersion, 120), machine: row.machine || null,
    browser: row.browser || null, capabilities: row.capabilities || SUPPORTED_ACTIONS,
    selectorPolicy: row.selectorPolicy || 'aria_role_name_then_testid_id_css_then_text', queueDepth: rows.length,
  };
}

async function enqueueBrowserNerveTicket({admin, caller = {}, args = {}, nowMs = Date.now()}) {
  const owner = safeText(caller.ownerKey, 80);
  const ownerEmail = safeEmail(caller.actor || caller.email);
  if (!owner || !owner.startsWith('owner_')) throw Object.assign(new Error('Browser Nerve ownerKey is required.'), {status: 401});
  const sessionId = safeId(args.sessionId, 'sessionId');
  const actionId = safeId(args.actionId, 'actionId');
  const action = actionName(args.action);
  const ticketId = safeId(`nerve-${actionId}`, 'ticketId');
  const workerId = safeId(args.workerId || 'windows-browser-nerve-01', 'workerId');
  const target = safeObject(args.target);
  const value = args.value == null ? '' : String(args.value).slice(0, 12000);
  const reason = safeText(args.reason, 2000);
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId));
  let idempotent = false;
  await admin.firestore().runTransaction(async (tx) => {
    const existing = await tx.get(ref);
    if (existing.exists) {
      const old = existing.data() || {};
      if (old.actionId !== actionId || old.sessionId !== sessionId || old.action !== action) throw Object.assign(new Error('Browser Nerve ticket idempotency conflict.'), {status: 409});
      idempotent = true;
      return;
    }
    tx.create(ref, {
      apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, ticketId, actionId, sessionId, ownerKey: owner, ownerEmail,
      workerId, action, target, value, reason, status: 'queued', cancelRequested: false,
      progress: {phase: 'queued', message: action, updatedAtMs: nowMs}, lease: null, result: null,
      createdAtMs: nowMs, updatedAtMs: nowMs,
    });
  });
  return {ticketId, actionId, sessionId, workerId, status: (await ref.get()).data()?.status || 'queued', idempotent};
}

async function leaseRequest({admin, worker, nowMs = Date.now()}) {
  const query = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', worker.ownerKey).limit(100).get();
  const eligible = query.docs.map((doc) => ({ref: doc.ref, row: doc.data() || {}})).filter((item) => {
    if (item.row.workerId !== worker.workerId || item.row.cancelRequested === true) return false;
    if (item.row.status === 'queued') return true;
    if (!['leased', 'running'].includes(item.row.status)) return false;
    return !item.row.lease || Number(item.row.lease.expiresAtMs || 0) <= nowMs;
  }).sort((a, b) => Number(a.row.createdAtMs || 0) - Number(b.row.createdAtMs || 0));
  for (const item of eligible) {
    let leased = null;
    await admin.firestore().runTransaction(async (tx) => {
      const snap = await tx.get(item.ref);
      if (!snap.exists) return;
      const row = snap.data() || {};
      const active = row.lease && Number(row.lease.expiresAtMs || 0) > nowMs;
      if (row.cancelRequested === true || row.status === 'cancelled' || active) return;
      leased = {...row, status: 'leased', lease: {workerId: worker.workerId, leasedAtMs: nowMs, expiresAtMs: nowMs + LEASE_TTL_MS}, progress: {...(row.progress || {}), phase: 'leased', updatedAtMs: nowMs}, updatedAtMs: nowMs};
      tx.set(item.ref, leased, {merge: false});
    });
    if (leased) {
      await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'leased', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
      return {ticket: leased, pollAfterSeconds: 1};
    }
  }
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {ticket: null, pollAfterSeconds: 2};
}

async function ticketForWorker(admin, worker, ticketId) {
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(worker.ownerKey, ticketId));
  const snap = await ref.get();
  if (!snap.exists) throw Object.assign(new Error('Browser Nerve ticket was not found.'), {status: 404});
  const row = snap.data() || {};
  if (row.workerId !== worker.workerId) throw Object.assign(new Error('Browser Nerve worker mismatch.'), {status: 403});
  return {ref, row};
}

async function heartbeat({admin, worker, ticketId, args = {}, nowMs = Date.now()}) {
  const found = await ticketForWorker(admin, worker, ticketId);
  if (found.row.cancelRequested === true || found.row.status === 'cancelled') return {ticketId, status: 'cancelled', cancelRequested: true};
  if (!found.row.lease || found.row.lease.workerId !== worker.workerId) throw Object.assign(new Error('Worker does not own this lease.'), {status: 409});
  const progress = {phase: safeText(args.phase, 80) || 'running', message: safeText(args.message, 400), updatedAtMs: nowMs};
  await found.ref.set({status: 'running', progress, lease: {...found.row.lease, expiresAtMs: nowMs + LEASE_TTL_MS}, updatedAtMs: nowMs}, {merge: true});
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'running', lastSeenAtMs: nowMs, updatedAtMs: nowMs, machine: safeText(args.machine, 160) || undefined, browser: safeText(args.browser, 160) || undefined, workerVersion: safeText(args.workerVersion, 120) || undefined}, {merge: true});
  return {ticketId, status: 'running', cancelRequested: false};
}

async function completeRequest({admin, worker, ticketId, args = {}, nowMs = Date.now()}) {
  const found = await ticketForWorker(admin, worker, ticketId);
  if (!found.row.lease || found.row.lease.workerId !== worker.workerId) throw Object.assign(new Error('Worker does not own this lease.'), {status: 409});
  const result = safeObject(args.result);
  const bytes = Buffer.byteLength(JSON.stringify(result), 'utf8');
  if (bytes > MAX_RESULT_BYTES) throw Object.assign(new Error('Browser Nerve evidence envelope is too large.'), {status: 413});
  const ok = result.ok !== false;
  const status = ok ? 'completed' : 'failed';
  const episodeId = safeId(`browser_episode_${found.row.actionId}`, 'episodeId');
  const url = safeText(result.url, 1000);
  const episode = {
    episodeId,
    sessionId: found.row.sessionId,
    intent: safeText(found.row.reason, 2000),
    origin: safeOrigin(url),
    url,
    title: safeText(result.title, 500),
    surface: {runtime: 'puppeteer', browser: safeText(result.browser, 80) || 'chrome', mode: 'desktop', userAgentMode: 'desktop', workerId: worker.workerId},
    outcome: ok ? 'completed' : 'failed',
    accessibilitySummary: safeText(result.accessibilitySummary, 12000),
    visibleTextSummary: safeText(result.visibleTextSummary, 12000),
    focusedElement: safeObject(result.focusedElement),
    actions: [{actionId: found.row.actionId, action: found.row.action, target: found.row.target, locatorUsed: safeText(result.locatorUsed, 2000), postcondition: safeObject(result.postcondition), status}],
    blockers: ok ? [] : [safeText(result.error || 'browser_nerve_action_failed', 1000)],
    redactionReport: {secretsPersisted: false, screenshotPersisted: false, inputValueReturned: false},
    discoveryCandidates: [], evidenceRefs: [`browser-nerve://${worker.workerId}/${ticketId}`],
    createdBy: found.row.ownerEmail, createdAtMs: nowMs,
  };
  await admin.firestore().collection(COLLECTIONS.episodes).doc(episodeId).set(episode, {merge: true});
  await admin.firestore().collection(COLLECTIONS.sessions).doc(found.row.sessionId).set({
    status: ok ? 'ready' : 'action_failed', lastEpisodeId: episodeId, lastUrl: url, lastTitle: episode.title, updatedAtMs: nowMs,
  }, {merge: true});
  await found.ref.set({status, lease: null, result: {...result, value: undefined}, completedAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {ticketId, actionId: found.row.actionId, sessionId: found.row.sessionId, status, episodeId, resultBytes: bytes};
}

function browserNerveOperationEntries() {
  return {
    'browser_nerve.worker.register': {summary: 'Mint a ten-minute bootstrap code for the dedicated outbound Windows Browser Nerve selector worker.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'optional windows-browser-nerve-01'}},
    'browser_nerve.worker.status': {summary: 'Read Browser Nerve worker heartbeat, selector capability, and queued browser work.', write: false, requiresRequestId: false, requiredScopes: [], input: {workerId: 'optional windows-browser-nerve-01'}},
  };
}
async function browserNerveOperationRunOperation({admin, user, operation, args = {}}) {
  if (operation === 'browser_nerve.worker.register') return registerWorkerOperation({admin, user, args});
  if (operation === 'browser_nerve.worker.status') return workerStatusOperation({admin, user, args});
  throw Object.assign(new Error('Unsupported Browser Nerve operation.'), {status: 400});
}

function createBrowserNerveHandler({admin}) {
  return async (req, res) => {
    try {
      const path = routePath(req);
      if (req.method === 'GET' && path === 'health') return send(res, 200, {ok: true, service: 'browser-nerve', apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, capabilities: SUPPORTED_ACTIONS, selectorPolicy: 'aria_role_name_then_testid_id_css_then_text'});
      if (req.method === 'POST' && path === 'bootstrap') return send(res, 200, await exchangeBootstrap({admin, args: bodyObject(req)}));
      const worker = await authenticateWorker(admin, req);
      if (req.method === 'POST' && path === 'lease') return send(res, 200, await leaseRequest({admin, worker}));
      const match = path.match(/^tickets\/([^/]+)\/(heartbeat|complete)$/);
      if (req.method === 'POST' && match && match[2] === 'heartbeat') return send(res, 200, await heartbeat({admin, worker, ticketId: match[1], args: bodyObject(req)}));
      if (req.method === 'POST' && match && match[2] === 'complete') return send(res, 200, await completeRequest({admin, worker, ticketId: match[1], args: bodyObject(req)}));
      return send(res, 404, {ok: false, error: 'browser_nerve_route_not_found'});
    } catch (error) {
      return send(res, Number(error.status) || 500, {ok: false, error: error.failureKind || error.code || 'browser_nerve_failed', detail: safeText(error.message || String(error), 500)});
    }
  };
}

module.exports = {
  API_VERSION, CONTRACT_VERSION, PUBLIC_ORIGIN, COLLECTIONS, SUPPORTED_ACTIONS,
  ownerKey, actionName, registerWorkerOperation, workerStatusOperation, enqueueBrowserNerveTicket,
  browserNerveOperationEntries, browserNerveOperationRunOperation, createBrowserNerveHandler,
};
