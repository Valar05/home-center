'use strict';

const {createHash, randomBytes} = require('node:crypto');

const API_VERSION = 'home-center.computer-hands-api.v1';
const CONTRACT_VERSION = 'home-center.computer-hands-contract.v1';
const PUBLIC_ORIGIN = process.env.HOME_CENTER_COMPUTER_HANDS_ORIGIN || 'https://us-central1-home-center-dclar.cloudfunctions.net/computerHands';
const COLLECTIONS = Object.freeze({workers: 'computerHandsWorkers', bootstrap: 'computerHandsBootstrapCodes', tokens: 'computerHandsWorkerTokens', tickets: 'computerHandsTickets'});
const BOOTSTRAP_TTL_MS = 10 * 60 * 1000;
const TOKEN_TTL_MS = 90 * 24 * 60 * 60 * 1000;
const LEASE_TTL_MS = 3 * 60 * 1000;
const MAX_RESULT_BYTES = 850 * 1024;
const MAX_PACKET_STEPS = 32;
const MAX_PACKET_ARGUMENT_BYTES = 96 * 1024;
const PACKET_ACTION = 'packet.execute';
const READ_ACTIONS = new Set(['system.status', 'screen.capture', 'window.list', 'process.list', 'clipboard.get']);
const WRITE_ACTIONS = new Set(['window.focus', 'input.type', 'input.key', 'input.mouse', 'process.start', 'process.stop', 'shell.exec', 'clipboard.set']);
const HIGH_RISK_ACTIONS = new Set(['process.stop', 'shell.exec']);
const SUPPORTED_ACTIONS = Object.freeze([...READ_ACTIONS, ...WRITE_ACTIONS, PACKET_ACTION]);

function safeText(value, max = 1200) { const text = value == null ? '' : String(value).trim(); return text.length > max ? text.slice(0, max) : text; }
function hash(value) { return createHash('sha256').update(String(value || '')).digest('hex'); }
function safeId(value, label = 'id') { const text = safeText(value, 160); if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(text)) throw Object.assign(new Error(`${label} must be 6-160 safe identifier characters.`), {status: 400, failureKind: 'computer_hands_invalid_id'}); return text; }
function safeEmail(value) { const text = safeText(value, 320).toLowerCase(); if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) throw Object.assign(new Error('Authenticated owner email is required.'), {status: 401, failureKind: 'computer_hands_owner_required'}); return text; }
function ownerKey(email) { return `owner_${hash(safeEmail(email)).slice(0, 32)}`; }
function workerDocId(owner, workerId) { return hash(`${owner}\n${safeId(workerId, 'workerId')}`); }
function ticketDocId(owner, ticketId) { return hash(`${owner}\n${safeId(ticketId, 'ticketId')}`); }
function bodyObject(req) { return req && req.body && typeof req.body === 'object' && !Buffer.isBuffer(req.body) ? req.body : {}; }
function routePath(req) { const raw = safeText(req && (req.path || req.url), 1000).split('?')[0]; const marker = '/computer-hands/v1/'; const index = raw.indexOf(marker); return index >= 0 ? raw.slice(index + marker.length) : raw.replace(/^\/+/, ''); }
function send(res, status, body) { res.status(status).json(body); }
function bearer(req) { const match = String(req && typeof req.get === 'function' ? req.get('Authorization') || '' : '').match(/^Bearer\s+(.+)$/i); if (!match) throw Object.assign(new Error('Computer Hands worker bearer token is required.'), {status: 401, failureKind: 'computer_hands_worker_auth_required'}); return match[1]; }
function actionName(value) { const action = safeText(value, 80).toLowerCase(); if (!SUPPORTED_ACTIONS.includes(action)) throw Object.assign(new Error(`Unsupported Computer Hands action: ${action}`), {status: 400, failureKind: 'computer_hands_action_unsupported'}); return action; }
function safeLaneId(value) { const text = safeText(value || 'lane-default', 160); return /^[A-Za-z0-9_.:-]{1,160}$/.test(text) ? text : `lane-${hash(text).slice(0, 24)}`; }
function permissionClass(action, actionArgs = {}) {
  if (action === PACKET_ACTION) {
    let level = 'read';
    for (const step of Array.isArray(actionArgs.steps) ? actionArgs.steps : []) {
      const stepClass = permissionClass(step.action, step.arguments || {});
      if (stepClass === 'high_risk_write') return 'high_risk_write';
      if (stepClass === 'write') level = 'write';
    }
    return level;
  }
  return READ_ACTIONS.has(action) ? 'read' : (HIGH_RISK_ACTIONS.has(action) ? 'high_risk_write' : 'write');
}
function requireApproval(action, args, actionArgs = {}) {
  const cls = permissionClass(action, actionArgs);
  if (cls === 'read') return;
  if (args.approved !== true) throw Object.assign(new Error(`${action} requires approved=true.`), {status: 409, failureKind: 'computer_hands_confirmation_required'});
  if (cls === 'high_risk_write' && args.highRiskApproved !== true) throw Object.assign(new Error(`${action} requires highRiskApproved=true.`), {status: 409, failureKind: 'computer_hands_high_risk_confirmation_required'});
}
function sanitizeProgress(value) {
  const input = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const completedSteps = Math.max(0, Math.min(MAX_PACKET_STEPS, Math.floor(Number(input.completedSteps || 0))));
  const totalSteps = Math.max(0, Math.min(MAX_PACKET_STEPS, Math.floor(Number(input.totalSteps || 0))));
  return {phase: safeText(input.phase, 80) || 'running', completedSteps, totalSteps, currentStepId: safeText(input.currentStepId, 160), currentAction: safeText(input.currentAction, 80), message: safeText(input.message, 400), updatedAtMs: Date.now()};
}

function sanitizeActionArgs(action, value) {
  const input = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const out = {};
  const text = (name, max) => { const v = safeText(input[name], max); if (v) out[name] = v; };
  const integer = (name, min, max) => { if (input[name] == null || input[name] === '') return; const v = Math.floor(Number(input[name])); if (!Number.isFinite(v) || v < min || v > max) throw Object.assign(new Error(`${name} is out of range.`), {status: 400, failureKind: 'computer_hands_invalid_argument'}); out[name] = v; };
  if (action === PACKET_ACTION) {
    const rawSteps = Array.isArray(input.steps) ? input.steps : [];
    if (!rawSteps.length || rawSteps.length > MAX_PACKET_STEPS) throw Object.assign(new Error(`packet.execute requires 1-${MAX_PACKET_STEPS} steps.`), {status: 400, failureKind: 'computer_hands_invalid_packet'});
    out.stopOnError = input.stopOnError !== false;
    const label = safeText(input.label, 120); if (label) out.label = label;
    out.steps = rawSteps.map((step, index) => {
      if (!step || typeof step !== 'object' || Array.isArray(step)) throw Object.assign(new Error(`packet step ${index + 1} must be an object.`), {status: 400, failureKind: 'computer_hands_invalid_packet'});
      const stepAction = actionName(step.action);
      if (stepAction === PACKET_ACTION) throw Object.assign(new Error('Nested packet.execute is not supported.'), {status: 400, failureKind: 'computer_hands_invalid_packet'});
      const stepId = safeText(step.id || `step-${String(index + 1).padStart(2, '0')}`, 160);
      if (!/^[A-Za-z0-9_.:-]{1,160}$/.test(stepId)) throw Object.assign(new Error(`packet step ${index + 1} id is invalid.`), {status: 400, failureKind: 'computer_hands_invalid_packet'});
      return {id: stepId, action: stepAction, arguments: sanitizeActionArgs(stepAction, step.arguments || {})};
    });
    if (Buffer.byteLength(JSON.stringify(out), 'utf8') > MAX_PACKET_ARGUMENT_BYTES) throw Object.assign(new Error('packet.execute arguments are too large.'), {status: 413, failureKind: 'computer_hands_packet_too_large'});
    return out;
  }
  if (action === 'screen.capture') { integer('maxWidth', 320, 2560); integer('quality', 20, 90); }
  if (action === 'window.focus') { integer('pid', 1, 2147483647); text('title', 300); if (!out.pid && !out.title) throw Object.assign(new Error('window.focus requires pid or title.'), {status: 400}); }
  if (action === 'input.type') { text('text', 48000); if (!out.text) throw Object.assign(new Error('input.type requires text.'), {status: 400}); }
  if (action === 'input.key') { text('key', 80); if (!out.key) throw Object.assign(new Error('input.key requires key.'), {status: 400}); }
  if (action === 'input.mouse') { integer('x', -32768, 32767); integer('y', -32768, 32767); text('button', 20); text('event', 20); if (out.x == null || out.y == null) throw Object.assign(new Error('input.mouse requires x and y.'), {status: 400}); }
  if (action === 'process.start') { text('command', 4000); text('arguments', 32000); text('workingDirectory', 1000); if (!out.command) throw Object.assign(new Error('process.start requires command.'), {status: 400}); }
  if (action === 'process.stop') { integer('pid', 1, 2147483647); if (!out.pid) throw Object.assign(new Error('process.stop requires pid.'), {status: 400}); }
  if (action === 'shell.exec') { text('command', 64000); text('workingDirectory', 1000); if (!out.command) throw Object.assign(new Error('shell.exec requires command.'), {status: 400}); }
  if (action === 'clipboard.set') text('text', 12000);
  return out;
}

async function registerWorkerOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId'); const email = safeEmail(user && user.email); const owner = ownerKey(email); const workerId = safeId(args.workerId || 'windows-hands-01', 'workerId');
  const code = randomBytes(24).toString('base64url'); const digest = hash(code); const expiresAtMs = nowMs + BOOTSTRAP_TTL_MS;
  const workerRef = admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId)); const bootstrapRef = admin.firestore().collection(COLLECTIONS.bootstrap).doc(digest);
  await admin.firestore().runTransaction(async (tx) => { tx.set(workerRef, {apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, workerId, ownerKey: owner, ownerEmail: email, capabilities: SUPPORTED_ACTIONS, fileLayer: 'drive_sync', state: 'bootstrap_pending', requestId, createdAtMs: nowMs, updatedAtMs: nowMs, lastSeenAtMs: 0}, {merge: true}); tx.set(bootstrapRef, {digest, workerRef: workerRef.path, workerId, ownerKey: owner, ownerEmail: email, expiresAtMs, usedAtMs: 0, createdAtMs: nowMs}, {merge: false}); });
  return {status: 'bootstrap_ready', workerId, contractVersion: CONTRACT_VERSION, origin: PUBLIC_ORIGIN, bootstrapCode: code, bootstrapExpiresAtMs: expiresAtMs, capabilities: SUPPORTED_ACTIONS, fileLayer: 'drive_sync'};
}

async function exchangeBootstrap({admin, args = {}, nowMs = Date.now()}) {
  const code = safeText(args.bootstrapCode, 300); const workerId = safeId(args.workerId, 'workerId'); if (!code) throw Object.assign(new Error('bootstrapCode is required.'), {status: 400});
  const ref = admin.firestore().collection(COLLECTIONS.bootstrap).doc(hash(code)); const token = randomBytes(32).toString('base64url'); const tokenDigest = hash(token); let record;
  await admin.firestore().runTransaction(async (tx) => { const snap = await tx.get(ref); if (!snap.exists) throw Object.assign(new Error('Bootstrap code was not found.'), {status: 404}); record = snap.data() || {}; if (record.workerId !== workerId) throw Object.assign(new Error('Bootstrap worker mismatch.'), {status: 403}); if (record.usedAtMs) throw Object.assign(new Error('Bootstrap code was already used.'), {status: 409}); if (Number(record.expiresAtMs || 0) <= nowMs) throw Object.assign(new Error('Bootstrap code expired.'), {status: 410}); tx.set(admin.firestore().collection(COLLECTIONS.tokens).doc(tokenDigest), {tokenDigest, workerId, ownerKey: record.ownerKey, ownerEmail: record.ownerEmail, capabilities: SUPPORTED_ACTIONS, createdAtMs: nowMs, expiresAtMs: nowMs + TOKEN_TTL_MS, revokedAtMs: 0}, {merge: false}); tx.update(ref, {usedAtMs: nowMs, tokenDigest}); tx.set(admin.firestore().doc(record.workerRef), {state: 'registered', tokenDigest, updatedAtMs: nowMs, lastSeenAtMs: nowMs}, {merge: true}); });
  return {status: 'registered', workerId, token, origin: PUBLIC_ORIGIN, contractVersion: CONTRACT_VERSION, expiresAtMs: nowMs + TOKEN_TTL_MS};
}

async function authenticateWorker(admin, req, nowMs = Date.now()) {
  const snap = await admin.firestore().collection(COLLECTIONS.tokens).doc(hash(bearer(req))).get(); if (!snap.exists) throw Object.assign(new Error('Worker token is invalid.'), {status: 401}); const worker = snap.data() || {}; if (worker.revokedAtMs || Number(worker.expiresAtMs || 0) <= nowMs) throw Object.assign(new Error('Worker token is inactive.'), {status: 401}); const headerWorker = safeId(req.get('X-Home-Center-Worker') || worker.workerId, 'workerId'); if (headerWorker !== worker.workerId) throw Object.assign(new Error('Worker identity mismatch.'), {status: 403}); return worker;
}

async function workerStatusOperation({admin, user, args = {}}) {
  const owner = ownerKey(safeEmail(user && user.email));
  const workerId = safeId(args.workerId || 'windows-hands-01', 'workerId');
  const snap = await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId)).get();
  if (!snap.exists) return {workerId, status: 'not_registered', online: false, fileLayer: 'drive_sync', capabilities: SUPPORTED_ACTIONS, queueDepth: 0, activeLanes: []};
  const row = snap.data() || {};
  const lastSeenAtMs = Number(row.lastSeenAtMs || 0);
  const updatedAtMs = Number(row.updatedAtMs || 0);
  const state = safeText(row.state, 80) || 'unknown';
  const onlineFreshnessMs = ['running', 'leased'].includes(state) ? LEASE_TTL_MS + 15000 : 30000;
  const heartbeatAtMs = Math.max(lastSeenAtMs, ['running', 'leased'].includes(state) ? updatedAtMs : 0);
  const online = heartbeatAtMs > 0 && Date.now() - heartbeatAtMs < onlineFreshnessMs;
  const pending = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', owner).limit(100).get();
  const rows = pending.docs.map((doc) => doc.data() || {}).filter((item) => item.workerId === workerId && ['queued', 'leased', 'running'].includes(item.status));
  const activeLanes = [...new Set(rows.map((item) => safeLaneId(item.laneId || 'lane-default')))];
  return {workerId, status: state, online, lastSeenAtMs, updatedAtMs, onlineFreshnessMs, workerVersion: safeText(row.workerVersion, 120), machine: row.machine || null, capabilities: row.capabilities || SUPPORTED_ACTIONS, fileLayer: 'drive_sync', queueDepth: rows.length, activeLanes, lastServedLaneId: safeText(row.lastServedLaneId, 160)};
}

async function createRequestOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId');
  const owner = ownerKey(safeEmail(user && user.email));
  const action = actionName(args.action);
  const actionArgs = sanitizeActionArgs(action, args.arguments || args.actionArgs || {});
  requireApproval(action, args, actionArgs);
  const workerId = safeId(args.workerId || 'windows-hands-01', 'workerId');
  const laneId = safeLaneId(args.laneId || args.threadId || 'lane-default');
  const ticketId = safeId(args.ticketId || `hands-${requestId}`, 'ticketId');
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId));
  const totalSteps = action === PACKET_ACTION ? actionArgs.steps.length : 1;
  let idempotent = false;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (snap.exists) {
      const old = snap.data() || {};
      if (old.requestId !== requestId || old.action !== action || old.laneId !== laneId || hash(JSON.stringify(old.arguments || {})) !== hash(JSON.stringify(actionArgs))) throw Object.assign(new Error('Computer Hands idempotency conflict.'), {status: 409});
      idempotent = true;
      return;
    }
    tx.create(ref, {apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, ticketId, requestId, ownerKey: owner, workerId, laneId, action, permissionClass: permissionClass(action, actionArgs), arguments: actionArgs, fileLayer: 'drive_sync', status: 'queued', progress: {phase: 'queued', completedSteps: 0, totalSteps, currentStepId: '', currentAction: '', message: safeText(actionArgs.label, 120), updatedAtMs: nowMs}, cancelRequested: false, createdAtMs: nowMs, updatedAtMs: nowMs, lease: null, result: null});
  });
  const row = (await ref.get()).data() || {};
  return {ticketId, requestId, laneId, action, permissionClass: row.permissionClass, status: row.status, workerId, idempotent, totalSteps, fileLayer: 'drive_sync'};
}

async function requestStatusOperation({admin, user, args = {}}) {
  const owner = ownerKey(safeEmail(user && user.email));
  const ticketId = safeId(args.ticketId || `hands-${safeId(args.requestId, 'requestId')}`, 'ticketId');
  const snap = await admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId)).get();
  if (!snap.exists) throw Object.assign(new Error('Computer Hands request was not found.'), {status: 404});
  const row = snap.data() || {};
  return {ticketId, requestId: row.requestId, laneId: safeLaneId(row.laneId || 'lane-default'), action: row.action, permissionClass: row.permissionClass, status: row.status, progress: row.progress || null, result: row.result || null, workerId: row.workerId, cancelRequested: row.cancelRequested === true, updatedAtMs: row.updatedAtMs, fileLayer: 'drive_sync'};
}

async function cancelRequestOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const owner = ownerKey(safeEmail(user && user.email));
  const ticketId = safeId(args.ticketId || `hands-${safeId(args.targetRequestId || args.requestId, 'requestId')}`, 'ticketId');
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId));
  let result;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (!snap.exists) throw Object.assign(new Error('Computer Hands request was not found.'), {status: 404});
    const row = snap.data() || {};
    if (['completed', 'failed', 'cancelled'].includes(row.status)) { result = {ticketId, status: row.status, idempotent: true}; return; }
    tx.set(ref, {status: 'cancelled', cancelRequested: true, progress: {...(row.progress || {}), phase: 'cancelled', message: safeText(args.reason, 300) || 'Cancelled by owner.', updatedAtMs: nowMs}, updatedAtMs: nowMs}, {merge: true});
    result = {ticketId, status: 'cancelled', idempotent: false};
  });
  return result;
}

async function leaseRequest({admin, worker, nowMs = Date.now()}) {
  const workerRef = admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId));
  const workerSnap = await workerRef.get();
  const lastServedLaneId = safeLaneId((workerSnap.exists && workerSnap.data()?.lastServedLaneId) || 'lane-default');
  const query = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', worker.ownerKey).limit(100).get();
  const eligible = query.docs.map((doc) => ({ref: doc.ref, row: doc.data() || {}})).filter((item) => {
    if (item.row.workerId !== worker.workerId || item.row.cancelRequested === true || item.row.status === 'cancelled') return false;
    if (item.row.status === 'queued') return true;
    if (!['leased', 'running'].includes(item.row.status)) return false;
    return !item.row.lease || Number(item.row.lease.expiresAtMs || 0) <= nowMs;
  }).sort((a, b) => Number(a.row.createdAtMs || 0) - Number(b.row.createdAtMs || 0));

  const laneHeads = [];
  const seenLanes = new Set();
  for (const item of eligible) {
    const laneId = safeLaneId(item.row.laneId || 'lane-default');
    if (seenLanes.has(laneId)) continue;
    seenLanes.add(laneId);
    laneHeads.push({...item, laneId});
  }
  const ordered = laneHeads.length > 1
    ? [...laneHeads.filter((item) => item.laneId !== lastServedLaneId), ...laneHeads.filter((item) => item.laneId === lastServedLaneId)]
    : laneHeads;

  for (const item of ordered) {
    let leased = null;
    await admin.firestore().runTransaction(async (tx) => {
      const snap = await tx.get(item.ref);
      if (!snap.exists) return;
      const row = snap.data() || {};
      const active = row.lease && Number(row.lease.expiresAtMs || 0) > nowMs;
      if (row.cancelRequested === true || row.status === 'cancelled' || active) return;
      if (row.status === 'queued' || ['leased', 'running'].includes(row.status)) {
        leased = {...row, laneId: safeLaneId(row.laneId || 'lane-default'), status: 'leased', lease: {workerId: worker.workerId, leasedAtMs: nowMs, expiresAtMs: nowMs + LEASE_TTL_MS}, progress: {...(row.progress || {}), phase: 'leased', updatedAtMs: nowMs}, updatedAtMs: nowMs};
        tx.set(item.ref, leased, {merge: false});
      }
    });
    if (leased) {
      await workerRef.set({state: 'leased', lastSeenAtMs: nowMs, updatedAtMs: nowMs, lastServedLaneId: leased.laneId}, {merge: true});
      return {ticket: leased, pollAfterSeconds: 1};
    }
  }
  await workerRef.set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {ticket: null, pollAfterSeconds: 2};
}

async function ticketForWorker(admin, worker, ticketId) { const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(worker.ownerKey, ticketId)); const snap = await ref.get(); if (!snap.exists) throw Object.assign(new Error('Computer Hands request was not found.'), {status: 404}); const row = snap.data() || {}; if (row.workerId !== worker.workerId) throw Object.assign(new Error('Computer Hands worker mismatch.'), {status: 403}); return {ref, row}; }
async function heartbeat({admin, worker, ticketId, args = {}, nowMs = Date.now()}) {
  const found = await ticketForWorker(admin, worker, ticketId);
  if (found.row.cancelRequested === true || found.row.status === 'cancelled') return {ticketId, status: 'cancelled', cancelRequested: true};
  const lease = found.row.lease || {};
  if (lease.workerId !== worker.workerId) throw Object.assign(new Error('Worker does not own this lease.'), {status: 409});
  const progress = args.progress ? sanitizeProgress(args.progress) : {...(found.row.progress || {}), phase: safeText(args.phase, 80) || 'running', updatedAtMs: nowMs};
  await found.ref.set({status: 'running', phase: safeText(args.phase, 80) || 'running', progress, lease: {...lease, expiresAtMs: nowMs + LEASE_TTL_MS}, updatedAtMs: nowMs}, {merge: true});
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'running', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {ticketId, status: 'running', cancelRequested: false};
}

async function completeRequest({admin, worker, ticketId, args = {}, nowMs = Date.now()}) {
  const found = await ticketForWorker(admin, worker, ticketId);
  if (found.row.cancelRequested === true || found.row.status === 'cancelled') return {ticketId, status: 'cancelled', resultBytes: 0, discarded: true};
  if (!found.row.lease || found.row.lease.workerId !== worker.workerId) throw Object.assign(new Error('Worker does not own this lease.'), {status: 409});
  const result = args.result && typeof args.result === 'object' && !Array.isArray(args.result) ? args.result : {ok: false, error: 'worker_result_missing'};
  const bytes = Buffer.byteLength(JSON.stringify(result), 'utf8');
  if (bytes > MAX_RESULT_BYTES) throw Object.assign(new Error('Computer Hands evidence envelope is too large.'), {status: 413});
  const status = result.ok === false ? 'failed' : 'completed';
  const totalSteps = Number(found.row.progress?.totalSteps || (found.row.action === PACKET_ACTION ? found.row.arguments?.steps?.length : 1) || 1);
  await found.ref.set({status, lease: null, result, progress: {...(found.row.progress || {}), phase: status, completedSteps: status === 'completed' ? totalSteps : Number(found.row.progress?.completedSteps || 0), totalSteps, updatedAtMs: nowMs}, completedAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {ticketId, status, resultBytes: bytes};
}


function computerHandsOperationEntries() { return {
  'computer_hands.worker.register': {summary: 'Mint a ten-minute bootstrap code for the owner-scoped outbound Windows Computer Hands worker. Drive sync remains the file layer.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'optional windows-hands-01'}},
  'computer_hands.worker.status': {summary: 'Read owner-scoped Computer Hands worker heartbeat and capability evidence.', write: false, requiresRequestId: false, requiredScopes: [], input: {workerId: 'optional windows-hands-01'}},
  'computer_hands.request.create': {summary: 'Queue one computer action or a bounded packet.execute sequence. Multiple ChatGPT threads should provide distinct laneId values; one physical desktop remains serialized with fair lane scheduling. Reads need no approval. Writes require approved=true; high-risk writes also require highRiskApproved=true. Drive sync owns files.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'optional', laneId: 'stable thread/lane id', action: SUPPORTED_ACTIONS.join('|'), arguments: 'action-specific object; packet.execute accepts up to 32 steps', approved: 'boolean for writes', highRiskApproved: 'boolean for high-risk writes'}},
  'computer_hands.request.cancel': {summary: 'Cancel a queued/running Computer Hands request. Packet workers observe cancellation between steps.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'audit id', ticketId: 'target ticket id', targetRequestId: 'target request id alias', reason: 'optional'}},
  'computer_hands.request.status': {summary: 'Read a Computer Hands request and bounded worker-returned evidence.', write: false, requiresRequestId: false, requiredScopes: [], input: {ticketId: 'ticket id', requestId: 'request id alias'}},
}; }
async function computerHandsOperationRunOperation({admin, user, operation, args = {}}) { if (operation === 'computer_hands.worker.register') return registerWorkerOperation({admin, user, args}); if (operation === 'computer_hands.worker.status') return workerStatusOperation({admin, user, args}); if (operation === 'computer_hands.request.create') return createRequestOperation({admin, user, args}); if (operation === 'computer_hands.request.cancel') return cancelRequestOperation({admin, user, args}); if (operation === 'computer_hands.request.status') return requestStatusOperation({admin, user, args}); throw Object.assign(new Error('Unsupported Computer Hands operation.'), {status: 400}); }

function createComputerHandsHandler({admin}) { return async (req, res) => { try { const path = routePath(req); if (req.method === 'GET' && path === 'health') return send(res, 200, {ok: true, service: 'computer-hands', apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, fileLayer: 'drive_sync', capabilities: SUPPORTED_ACTIONS}); if (req.method === 'POST' && path === 'bootstrap') return send(res, 200, await exchangeBootstrap({admin, args: bodyObject(req)})); const worker = await authenticateWorker(admin, req); if (req.method === 'POST' && path === 'lease') return send(res, 200, await leaseRequest({admin, worker})); const match = path.match(/^tickets\/([^/]+)\/(heartbeat|complete)$/); if (req.method === 'POST' && match && match[2] === 'heartbeat') return send(res, 200, await heartbeat({admin, worker, ticketId: match[1], args: bodyObject(req)})); if (req.method === 'POST' && match && match[2] === 'complete') return send(res, 200, await completeRequest({admin, worker, ticketId: match[1], args: bodyObject(req)})); return send(res, 404, {ok: false, error: 'computer_hands_route_not_found'}); } catch (error) { return send(res, Number(error.status) || 500, {ok: false, error: error.failureKind || error.code || 'computer_hands_failed', detail: safeText(error.message || String(error), 500)}); } }; }

module.exports = {API_VERSION, CONTRACT_VERSION, PUBLIC_ORIGIN, COLLECTIONS, SUPPORTED_ACTIONS, READ_ACTIONS, WRITE_ACTIONS, HIGH_RISK_ACTIONS, hash, ownerKey, actionName, sanitizeActionArgs, permissionClass, safeLaneId, computerHandsOperationEntries, computerHandsOperationRunOperation, registerWorkerOperation, workerStatusOperation, createRequestOperation, requestStatusOperation, createComputerHandsHandler};
