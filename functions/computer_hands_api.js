'use strict';

const {createHash, randomBytes} = require('node:crypto');

const API_VERSION = 'home-center.computer-hands-api.v1';
const CONTRACT_VERSION = 'home-center.computer-hands-contract.v1';
const PUBLIC_ORIGIN = process.env.HOME_CENTER_COMPUTER_HANDS_ORIGIN || 'https://us-central1-home-center-dclar.cloudfunctions.net/computerHands';
const COLLECTIONS = Object.freeze({workers: 'computerHandsWorkers', bootstrap: 'computerHandsBootstrapCodes', tokens: 'computerHandsWorkerTokens', tickets: 'computerHandsTickets'});
const BOOTSTRAP_TTL_MS = 10 * 60 * 1000;
const TOKEN_TTL_MS = 90 * 24 * 60 * 60 * 1000;
const LEASE_TTL_MS = 2 * 60 * 1000;
const MAX_RESULT_BYTES = 850 * 1024;
const READ_ACTIONS = new Set(['system.status', 'screen.capture', 'window.list', 'process.list', 'clipboard.get']);
const WRITE_ACTIONS = new Set(['window.focus', 'input.type', 'input.key', 'input.mouse', 'process.start', 'process.stop', 'shell.exec', 'clipboard.set']);
const HIGH_RISK_ACTIONS = new Set(['process.stop', 'shell.exec']);
const SUPPORTED_ACTIONS = Object.freeze([...READ_ACTIONS, ...WRITE_ACTIONS]);

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
function permissionClass(action) { return READ_ACTIONS.has(action) ? 'read' : (HIGH_RISK_ACTIONS.has(action) ? 'high_risk_write' : 'write'); }
function requireApproval(action, args) { if (!WRITE_ACTIONS.has(action)) return; if (args.approved !== true) throw Object.assign(new Error(`${action} requires approved=true.`), {status: 409, failureKind: 'computer_hands_confirmation_required'}); if (HIGH_RISK_ACTIONS.has(action) && args.highRiskApproved !== true) throw Object.assign(new Error(`${action} requires highRiskApproved=true.`), {status: 409, failureKind: 'computer_hands_high_risk_confirmation_required'}); }

function sanitizeActionArgs(action, value) {
  const input = value && typeof value === 'object' && !Array.isArray(value) ? value : {};
  const out = {};
  const text = (name, max) => { const v = safeText(input[name], max); if (v) out[name] = v; };
  const integer = (name, min, max) => { if (input[name] == null || input[name] === '') return; const v = Math.floor(Number(input[name])); if (!Number.isFinite(v) || v < min || v > max) throw Object.assign(new Error(`${name} is out of range.`), {status: 400, failureKind: 'computer_hands_invalid_argument'}); out[name] = v; };
  if (action === 'screen.capture') { integer('maxWidth', 320, 2560); integer('quality', 20, 90); }
  if (action === 'window.focus') { integer('pid', 1, 2147483647); text('title', 300); if (!out.pid && !out.title) throw Object.assign(new Error('window.focus requires pid or title.'), {status: 400}); }
  if (action === 'input.type') { text('text', 12000); if (!out.text) throw Object.assign(new Error('input.type requires text.'), {status: 400}); }
  if (action === 'input.key') { text('key', 80); if (!out.key) throw Object.assign(new Error('input.key requires key.'), {status: 400}); }
  if (action === 'input.mouse') { integer('x', -32768, 32767); integer('y', -32768, 32767); text('button', 20); text('event', 20); if (out.x == null || out.y == null) throw Object.assign(new Error('input.mouse requires x and y.'), {status: 400}); }
  if (action === 'process.start') { text('command', 2000); text('arguments', 8000); text('workingDirectory', 1000); if (!out.command) throw Object.assign(new Error('process.start requires command.'), {status: 400}); }
  if (action === 'process.stop') { integer('pid', 1, 2147483647); if (!out.pid) throw Object.assign(new Error('process.stop requires pid.'), {status: 400}); }
  if (action === 'shell.exec') { text('command', 16000); text('workingDirectory', 1000); if (!out.command) throw Object.assign(new Error('shell.exec requires command.'), {status: 400}); }
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
  const owner = ownerKey(safeEmail(user && user.email)); const workerId = safeId(args.workerId || 'windows-hands-01', 'workerId'); const snap = await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId)).get(); if (!snap.exists) return {workerId, status: 'not_registered', online: false, fileLayer: 'drive_sync', capabilities: SUPPORTED_ACTIONS}; const row = snap.data() || {}; const lastSeenAtMs = Number(row.lastSeenAtMs || 0); return {workerId, status: safeText(row.state, 80) || 'unknown', online: lastSeenAtMs > 0 && Date.now() - lastSeenAtMs < 30000, lastSeenAtMs, workerVersion: safeText(row.workerVersion, 120), machine: row.machine || null, capabilities: row.capabilities || SUPPORTED_ACTIONS, fileLayer: 'drive_sync'};
}

async function createRequestOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId'); const owner = ownerKey(safeEmail(user && user.email)); const action = actionName(args.action); requireApproval(action, args); const actionArgs = sanitizeActionArgs(action, args.arguments || args.actionArgs || {}); const workerId = safeId(args.workerId || 'windows-hands-01', 'workerId'); const ticketId = safeId(args.ticketId || `hands-${requestId}`, 'ticketId'); const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId)); let idempotent = false;
  await admin.firestore().runTransaction(async (tx) => { const snap = await tx.get(ref); if (snap.exists) { const old = snap.data() || {}; if (old.requestId !== requestId || old.action !== action || hash(JSON.stringify(old.arguments || {})) !== hash(JSON.stringify(actionArgs))) throw Object.assign(new Error('Computer Hands idempotency conflict.'), {status: 409}); idempotent = true; return; } tx.create(ref, {apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, ticketId, requestId, ownerKey: owner, workerId, action, permissionClass: permissionClass(action), arguments: actionArgs, fileLayer: 'drive_sync', status: 'queued', createdAtMs: nowMs, updatedAtMs: nowMs, lease: null, result: null}); });
  const row = (await ref.get()).data() || {}; return {ticketId, requestId, action, permissionClass: row.permissionClass, status: row.status, workerId, idempotent, fileLayer: 'drive_sync'};
}

async function requestStatusOperation({admin, user, args = {}}) {
  const owner = ownerKey(safeEmail(user && user.email)); const ticketId = safeId(args.ticketId || `hands-${safeId(args.requestId, 'requestId')}`, 'ticketId'); const snap = await admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId)).get(); if (!snap.exists) throw Object.assign(new Error('Computer Hands request was not found.'), {status: 404}); const row = snap.data() || {}; return {ticketId, requestId: row.requestId, action: row.action, permissionClass: row.permissionClass, status: row.status, result: row.result || null, workerId: row.workerId, updatedAtMs: row.updatedAtMs, fileLayer: 'drive_sync'};
}

async function leaseRequest({admin, worker, nowMs = Date.now()}) {
  const query = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', worker.ownerKey).limit(30).get(); const candidates = query.docs.map((doc) => ({ref: doc.ref, row: doc.data() || {}})).filter((x) => x.row.workerId === worker.workerId && ['queued', 'leased', 'running'].includes(x.row.status)).sort((a, b) => Number(a.row.createdAtMs || 0) - Number(b.row.createdAtMs || 0));
  for (const item of candidates) { let leased = null; await admin.firestore().runTransaction(async (tx) => { const snap = await tx.get(item.ref); if (!snap.exists) return; const row = snap.data() || {}; const active = row.lease && Number(row.lease.expiresAtMs || 0) > nowMs; if (row.status === 'queued' || !active || row.lease.workerId === worker.workerId) { leased = {...row, status: 'leased', lease: {workerId: worker.workerId, leasedAtMs: nowMs, expiresAtMs: nowMs + LEASE_TTL_MS}, updatedAtMs: nowMs}; tx.set(item.ref, leased, {merge: false}); } }); if (leased) { await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'leased', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true}); return {ticket: leased, pollAfterSeconds: 1}; } }
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true}); return {ticket: null, pollAfterSeconds: 3};
}

async function ticketForWorker(admin, worker, ticketId) { const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(worker.ownerKey, ticketId)); const snap = await ref.get(); if (!snap.exists) throw Object.assign(new Error('Computer Hands request was not found.'), {status: 404}); const row = snap.data() || {}; if (row.workerId !== worker.workerId) throw Object.assign(new Error('Computer Hands worker mismatch.'), {status: 403}); return {ref, row}; }
async function heartbeat({admin, worker, ticketId, args = {}, nowMs = Date.now()}) { const found = await ticketForWorker(admin, worker, ticketId); const lease = found.row.lease || {}; if (lease.workerId !== worker.workerId) throw Object.assign(new Error('Worker does not own this lease.'), {status: 409}); await found.ref.set({status: 'running', phase: safeText(args.phase, 80) || 'running', lease: {...lease, expiresAtMs: nowMs + LEASE_TTL_MS}, updatedAtMs: nowMs}, {merge: true}); await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'running', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true}); return {ticketId, status: 'running'}; }
async function completeRequest({admin, worker, ticketId, args = {}, nowMs = Date.now()}) { const found = await ticketForWorker(admin, worker, ticketId); if (!found.row.lease || found.row.lease.workerId !== worker.workerId) throw Object.assign(new Error('Worker does not own this lease.'), {status: 409}); const result = args.result && typeof args.result === 'object' && !Array.isArray(args.result) ? args.result : {ok: false, error: 'worker_result_missing'}; const bytes = Buffer.byteLength(JSON.stringify(result), 'utf8'); if (bytes > MAX_RESULT_BYTES) throw Object.assign(new Error('Computer Hands evidence envelope is too large.'), {status: 413}); const status = result.ok === false ? 'failed' : 'completed'; await found.ref.set({status, lease: null, result, completedAtMs: nowMs, updatedAtMs: nowMs}, {merge: true}); await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true}); return {ticketId, status, resultBytes: bytes}; }

function computerHandsOperationEntries() { return {
  'computer_hands.worker.register': {summary: 'Mint a ten-minute bootstrap code for the owner-scoped outbound Windows Computer Hands worker. Drive sync remains the file layer.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'optional windows-hands-01'}},
  'computer_hands.worker.status': {summary: 'Read owner-scoped Computer Hands worker heartbeat and capability evidence.', write: false, requiresRequestId: false, requiredScopes: [], input: {workerId: 'optional windows-hands-01'}},
  'computer_hands.request.create': {summary: 'Queue a computer action. Reads need no approval. UI/process/clipboard writes require approved=true; shell.exec and process.stop also require highRiskApproved=true. No file-transfer API: Drive sync owns files.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'optional', action: SUPPORTED_ACTIONS.join('|'), arguments: 'action-specific object', approved: 'boolean for writes', highRiskApproved: 'boolean for high-risk writes'}},
  'computer_hands.request.status': {summary: 'Read a Computer Hands request and bounded worker-returned evidence.', write: false, requiresRequestId: false, requiredScopes: [], input: {ticketId: 'ticket id', requestId: 'request id alias'}},
}; }
async function computerHandsOperationRunOperation({admin, user, operation, args = {}}) { if (operation === 'computer_hands.worker.register') return registerWorkerOperation({admin, user, args}); if (operation === 'computer_hands.worker.status') return workerStatusOperation({admin, user, args}); if (operation === 'computer_hands.request.create') return createRequestOperation({admin, user, args}); if (operation === 'computer_hands.request.status') return requestStatusOperation({admin, user, args}); throw Object.assign(new Error('Unsupported Computer Hands operation.'), {status: 400}); }

function createComputerHandsHandler({admin}) { return async (req, res) => { try { const path = routePath(req); if (req.method === 'GET' && path === 'health') return send(res, 200, {ok: true, service: 'computer-hands', apiVersion: API_VERSION, contractVersion: CONTRACT_VERSION, fileLayer: 'drive_sync', capabilities: SUPPORTED_ACTIONS}); if (req.method === 'POST' && path === 'bootstrap') return send(res, 200, await exchangeBootstrap({admin, args: bodyObject(req)})); const worker = await authenticateWorker(admin, req); if (req.method === 'POST' && path === 'lease') return send(res, 200, await leaseRequest({admin, worker})); const match = path.match(/^tickets\/([^/]+)\/(heartbeat|complete)$/); if (req.method === 'POST' && match && match[2] === 'heartbeat') return send(res, 200, await heartbeat({admin, worker, ticketId: match[1], args: bodyObject(req)})); if (req.method === 'POST' && match && match[2] === 'complete') return send(res, 200, await completeRequest({admin, worker, ticketId: match[1], args: bodyObject(req)})); return send(res, 404, {ok: false, error: 'computer_hands_route_not_found'}); } catch (error) { return send(res, Number(error.status) || 500, {ok: false, error: error.failureKind || error.code || 'computer_hands_failed', detail: safeText(error.message || String(error), 500)}); } }; }

module.exports = {API_VERSION, CONTRACT_VERSION, PUBLIC_ORIGIN, COLLECTIONS, SUPPORTED_ACTIONS, READ_ACTIONS, WRITE_ACTIONS, HIGH_RISK_ACTIONS, hash, ownerKey, actionName, sanitizeActionArgs, permissionClass, computerHandsOperationEntries, computerHandsOperationRunOperation, registerWorkerOperation, workerStatusOperation, createRequestOperation, requestStatusOperation, createComputerHandsHandler};
