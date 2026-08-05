'use strict';

const {createHash, randomBytes, timingSafeEqual} = require('node:crypto');
const contract = require('./venus_cauldron_contract');

const API_VERSION = 'home-center.venus-cauldron-relay-api.v1';
const PUBLIC_ORIGIN = process.env.HOME_CENTER_VENUS_CAULDRON_ORIGIN || 'https://us-central1-home-center-dclar.cloudfunctions.net/venusCauldronRelay';
const COLLECTIONS = Object.freeze({workers: 'venusCauldronWorkers', bootstrap: 'venusCauldronBootstrapCodes', tokens: 'venusCauldronWorkerTokens', tickets: 'venusCauldronTickets'});
const BOOTSTRAP_TTL_MS = 10 * 60 * 1000;
const WORKER_TOKEN_TTL_MS = 90 * 24 * 60 * 60 * 1000;

function text(value, max = 1000) {
  const result = value === undefined || value === null ? '' : String(value).trim();
  return result.length > max ? result.slice(0, max) : result;
}

function hash(value) {
  return createHash('sha256').update(String(value || '')).digest('hex');
}

function modelAllowlist(value = process.env.VENUS_CAULDRON_ALLOWED_MODELS || '') {
  return [...new Set(String(value).split(',').map((item) => item.trim()).filter((item) => /^[A-Za-z0-9_.:-]{2,120}$/.test(item)))];
}

function bearer(req, kind = 'authorization') {
  const header = req && typeof req.get === 'function' ? req.get('Authorization') || '' : '';
  const match = String(header).match(/^Bearer\s+(.+)$/i);
  if (!match) throw Object.assign(new Error(`${kind} bearer token is required.`), {status: 401, failureKind: `venus_relay_${kind}_required`});
  return match[1];
}

function constantTimeEqual(left, right) {
  const a = Buffer.from(String(left || ''));
  const b = Buffer.from(String(right || ''));
  return a.length > 0 && a.length === b.length && timingSafeEqual(a, b);
}

function authenticateClient(req, configuredKey) {
  const supplied = bearer(req, 'client_auth');
  if (!configuredKey || !constantTimeEqual(supplied, configuredKey)) throw Object.assign(new Error('Client bearer token is invalid.'), {status: 401, failureKind: 'venus_relay_client_auth_invalid'});
}

function routePath(req) {
  const raw = text(req && (req.path || req.url), 1000).split('?')[0];
  const marker = '/venus-cauldron-relay/';
  const index = raw.indexOf(marker);
  return index >= 0 ? raw.slice(index + marker.length) : raw.replace(/^\/+/, '');
}

function ownerEmail(user) {
  const email = text(user && user.email, 320).toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) throw Object.assign(new Error('Authenticated owner email is required.'), {status: 401, failureKind: 'venus_relay_owner_required'});
  return email;
}

function ownerKey(email) {
  return 'owner_' + hash(email).slice(0, 32);
}

function workerDocId(owner, workerId) {
  return hash(owner + '\n' + contract.safeId(workerId, 'workerId'));
}

function ticketDocId(requestId) {
  return hash('venusos\n' + contract.safeId(requestId, 'requestId'));
}

function send(res, status, body) {
  return res.status(status).json(body);
}

async function registerWorkerOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const email = ownerEmail(user);
  const owner = ownerKey(email);
  const requestId = contract.safeId(args.requestId, 'requestId');
  const workerId = contract.safeId(args.workerId || 'cauldron-llm-01', 'workerId');
  const models = modelAllowlist(Array.isArray(args.models) ? args.models.join(',') : args.models);
  if (!models.length) throw Object.assign(new Error('At least one explicit Ollama model is required.'), {status: 400, failureKind: 'venus_relay_models_required'});
  const code = randomBytes(24).toString('base64url');
  const digest = hash(code);
  const expiresAtMs = nowMs + BOOTSTRAP_TTL_MS;
  const workerRef = admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId));
  const bootstrapRef = admin.firestore().collection(COLLECTIONS.bootstrap).doc(digest);
  await admin.firestore().runTransaction(async (tx) => {
    tx.set(workerRef, {apiVersion: API_VERSION, contractVersion: contract.CONTRACT_VERSION, workerId, ownerKey: owner, ownerEmail: email, models, state: 'bootstrap_pending', requestId, createdAtMs: nowMs, updatedAtMs: nowMs, revokedAtMs: 0}, {merge: true});
    tx.create(bootstrapRef, {digest, workerRef: workerRef.path, workerId, ownerKey: owner, ownerEmail: email, models, expiresAtMs, usedAtMs: 0, createdAtMs: nowMs});
  });
  return {status: 'bootstrap_ready', workerId, models, origin: PUBLIC_ORIGIN, bootstrapCode: code, bootstrapExpiresAtMs: expiresAtMs, secretHandling: 'The code is single-use. The exchanged worker token is returned only to THECAULDRON.', network: 'outbound_https_only', ollama: '127.0.0.1 only'};
}

async function workerStatusOperation({admin, user, args = {}}) {
  const email = ownerEmail(user);
  const owner = ownerKey(email);
  const workerId = contract.safeId(args.workerId || 'cauldron-llm-01', 'workerId');
  const snap = await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId)).get();
  if (!snap.exists) return {status: 'not_registered', workerId};
  const record = snap.data() || {};
  return {status: record.revokedAtMs ? 'revoked' : record.state, workerId, models: record.models || [], lastSeenAtMs: record.lastSeenAtMs || 0, updatedAtMs: record.updatedAtMs || 0, network: 'outbound_https_only'};
}

async function revokeWorkerOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const email = ownerEmail(user);
  const owner = ownerKey(email);
  const workerId = contract.safeId(args.workerId || 'cauldron-llm-01', 'workerId');
  const workerRef = admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId));
  const snap = await workerRef.get();
  if (!snap.exists) return {status: 'not_registered', workerId};
  const record = snap.data() || {};
  if (record.tokenDigest) await admin.firestore().collection(COLLECTIONS.tokens).doc(record.tokenDigest).set({revokedAtMs: nowMs}, {merge: true});
  await workerRef.set({state: 'revoked', revokedAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {status: 'revoked', workerId, revokedAtMs: nowMs};
}

async function exchangeBootstrap({admin, args = {}, nowMs = Date.now()}) {
  const code = text(args.bootstrapCode, 300);
  const workerId = contract.safeId(args.workerId, 'workerId');
  if (!code) throw Object.assign(new Error('bootstrapCode is required.'), {status: 400, failureKind: 'venus_relay_bootstrap_required'});
  const bootstrapRef = admin.firestore().collection(COLLECTIONS.bootstrap).doc(hash(code));
  const token = randomBytes(32).toString('base64url');
  const tokenDigest = hash(token);
  let record;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(bootstrapRef);
    if (!snap.exists) throw Object.assign(new Error('Bootstrap code was not found.'), {status: 404, failureKind: 'venus_relay_bootstrap_not_found'});
    record = snap.data() || {};
    if (record.workerId !== workerId) throw Object.assign(new Error('Bootstrap code belongs to another worker.'), {status: 403, failureKind: 'venus_relay_bootstrap_worker_mismatch'});
    if (record.usedAtMs) throw Object.assign(new Error('Bootstrap code was already used.'), {status: 409, failureKind: 'venus_relay_bootstrap_used'});
    if (record.expiresAtMs <= nowMs) throw Object.assign(new Error('Bootstrap code expired.'), {status: 410, failureKind: 'venus_relay_bootstrap_expired'});
    tx.create(admin.firestore().collection(COLLECTIONS.tokens).doc(tokenDigest), {tokenDigest, workerId, ownerKey: record.ownerKey, models: record.models, createdAtMs: nowMs, expiresAtMs: nowMs + WORKER_TOKEN_TTL_MS, revokedAtMs: 0});
    tx.update(bootstrapRef, {usedAtMs: nowMs, tokenDigest});
    tx.set(admin.firestore().doc(record.workerRef), {state: 'registered', tokenDigest, lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  });
  return {status: 'registered', workerId, models: record.models, token, origin: PUBLIC_ORIGIN, contractVersion: contract.CONTRACT_VERSION, expiresAtMs: nowMs + WORKER_TOKEN_TTL_MS};
}

async function authenticateWorker(admin, req, nowMs = Date.now()) {
  const token = bearer(req, 'worker_auth');
  const snap = await admin.firestore().collection(COLLECTIONS.tokens).doc(hash(token)).get();
  if (!snap.exists) throw Object.assign(new Error('Worker token is invalid.'), {status: 401, failureKind: 'venus_relay_worker_auth_invalid'});
  const record = snap.data() || {};
  if (record.revokedAtMs || record.expiresAtMs <= nowMs) throw Object.assign(new Error('Worker token is inactive.'), {status: 401, failureKind: 'venus_relay_worker_auth_inactive'});
  const workerId = contract.safeId(req.get('X-Home-Center-Worker') || record.workerId, 'workerId');
  if (workerId !== record.workerId) throw Object.assign(new Error('Worker identity mismatch.'), {status: 403, failureKind: 'venus_relay_worker_identity_mismatch'});
  return record;
}

async function leaseTicket({admin, worker, nowMs = Date.now()}) {
  const query = await admin.firestore().collection(COLLECTIONS.tickets).where('status', 'in', ['queued', 'leased']).limit(25).get();
  const candidates = query.docs.map((doc) => ({ref: doc.ref, ticket: doc.data()})).sort((a, b) => a.ticket.createdAtMs - b.ticket.createdAtMs);
  for (const candidate of candidates) {
    try {
      let leased;
      await admin.firestore().runTransaction(async (tx) => {
        const snap = await tx.get(candidate.ref);
        leased = contract.leaseTicket(snap.data(), worker, nowMs);
        tx.set(candidate.ref, leased, {merge: false});
      });
      await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'leased', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
      return {ticket: leased, pollAfterSeconds: 1};
    } catch (error) {
      if (!['venus_relay_ticket_already_leased', 'venus_relay_ticket_not_leasable', 'venus_relay_ticket_expired', 'venus_relay_worker_model_mismatch'].includes(error.code)) throw error;
    }
  }
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {ticket: null, pollAfterSeconds: 2};
}

async function finishTicket({admin, worker, ticketId, args = {}, failed = false, nowMs = Date.now()}) {
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(ticketId.replace(/^vcr-/, '')));
  let updated;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    if (!snap.exists) throw Object.assign(new Error('Ticket was not found.'), {status: 404, failureKind: 'venus_relay_ticket_not_found'});
    const ticket = snap.data() || {};
    if (failed) {
      if (!ticket.lease || ticket.lease.workerId !== worker.workerId || ticket.lease.expiresAtMs <= nowMs) throw new contract.VenusRelayError('venus_relay_lease_owner_mismatch', 'Worker does not own a current lease.', 409);
      updated = {...ticket, status: 'failed', updatedAtMs: nowMs, lease: null, failure: {code: text(args.code, 120) || 'ollama_failed', detail: text(args.detail, 500)}};
    } else {
      updated = contract.completeTicket(ticket, worker.workerId, args, nowMs);
    }
    tx.set(ref, updated, {merge: false});
  });
  return {status: updated.status, ticketId: updated.ticketId, receipt: updated.receipt};
}

async function chatCompletion({admin, req, allowlist, nowMs = Date.now()}) {
  const body = req.body && typeof req.body === 'object' && !Buffer.isBuffer(req.body) ? req.body : {};
  const suppliedId = text(req.get('Idempotency-Key') || req.get('X-Request-Id'), 160);
  const requestId = suppliedId && /^[A-Za-z0-9_.:-]{6,160}$/.test(suppliedId) ? suppliedId : randomBytes(12).toString('hex');
  const proposed = contract.createTicket({requestId, input: body, allowlist, nowMs});
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(requestId));
  let ticket;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    ticket = contract.reconcileTicket(snap.exists ? snap.data() : null, proposed);
    if (!snap.exists) tx.create(ref, ticket);
  });
  const deadline = Date.now() + 45000;
  while (Date.now() < deadline) {
    const snap = await ref.get();
    const current = snap.data() || {};
    if (current.status === 'completed') return current.completion;
    if (current.status === 'failed') throw Object.assign(new Error(current.failure && current.failure.detail || 'THECAULDRON inference failed.'), {status: 502, failureKind: current.failure && current.failure.code || 'venus_relay_worker_failed'});
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw Object.assign(new Error(`THECAULDRON did not complete ${ticket.ticketId} before the relay deadline.`), {status: 504, failureKind: 'venus_relay_deadline_exceeded'});
}

function operationEntries() {
  return {
    'venus_relay.worker.register': {summary: 'Mint a ten-minute single-use bootstrap code for an outbound-only THECAULDRON Ollama worker.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'cauldron-llm-01', models: 'explicit string[]'}, output: {status: 'bootstrap_ready', bootstrapCode: 'one-time secret', origin: 'HTTPS relay origin'}},
    'venus_relay.worker.status': {summary: 'Read THECAULDRON relay worker state and last outbound heartbeat.', write: false, requiresRequestId: false, requiredScopes: [], input: {workerId: 'cauldron-llm-01'}, output: {status: 'worker state', lastSeenAtMs: 'timestamp'}},
    'venus_relay.worker.revoke': {summary: 'Revoke the THECAULDRON relay token. Local uninstall remains a separate host action.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'cauldron-llm-01'}, output: {status: 'revoked'}},
  };
}

async function runOperation({admin, user, operation, args = {}}) {
  if (operation === 'venus_relay.worker.register') return registerWorkerOperation({admin, user, args});
  if (operation === 'venus_relay.worker.status') return workerStatusOperation({admin, user, args});
  if (operation === 'venus_relay.worker.revoke') return revokeWorkerOperation({admin, user, args});
  throw Object.assign(new Error('Unsupported Venus relay operation.'), {status: 400, failureKind: 'venus_relay_operation_unsupported'});
}

function createHandler({admin, clientKey = () => process.env.VENUS_CAULDRON_CLIENT_KEY || '', allowedModels = () => process.env.VENUS_CAULDRON_ALLOWED_MODELS || ''}) {
  return async (req, res) => {
    try {
      const path = routePath(req);
      if (req.method === 'GET' && path === 'health') return send(res, 200, {ok: true, service: 'venus-cauldron-relay', apiVersion: API_VERSION, contractVersion: contract.CONTRACT_VERSION, network: 'outbound_worker_only', ollamaExposure: 'loopback_only'});
      if (req.method === 'POST' && path === 'v1/chat/completions') {
        authenticateClient(req, clientKey());
        const models = modelAllowlist(allowedModels());
        if (!models.length) throw Object.assign(new Error('No THECAULDRON models are enabled.'), {status: 503, failureKind: 'venus_relay_models_unconfigured'});
        return send(res, 200, await chatCompletion({admin, req, allowlist: models}));
      }
      if (req.method === 'POST' && path === 'worker/v1/bootstrap') return send(res, 200, await exchangeBootstrap({admin, args: req.body || {}}));
      const worker = await authenticateWorker(admin, req);
      if (req.method === 'POST' && path === 'worker/v1/lease') return send(res, 200, await leaseTicket({admin, worker}));
      const match = path.match(/^worker\/v1\/tickets\/(vcr-[A-Za-z0-9_.:-]+)\/(complete|fail)$/);
      if (req.method === 'POST' && match) return send(res, 200, await finishTicket({admin, worker, ticketId: match[1], args: req.body || {}, failed: match[2] === 'fail'}));
      return send(res, 404, {ok: false, error: 'venus_relay_route_not_found'});
    } catch (error) {
      return send(res, Number(error.status) || 500, {ok: false, error: error.failureKind || error.code || 'venus_relay_failed', detail: text(error.message || String(error), 500)});
    }
  };
}

module.exports = {API_VERSION, PUBLIC_ORIGIN, COLLECTIONS, hash, modelAllowlist, authenticateClient, registerWorkerOperation, workerStatusOperation, revokeWorkerOperation, operationEntries, runOperation, createHandler};

