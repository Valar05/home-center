'use strict';

const {createHash, randomBytes} = require('node:crypto');
const contract = require('./local_voice_farm_contract');
const {uploadGeneratedArtifact, inspectGeneratedArtifact} = require('./artifact_bucket');
const {registerAudioArtifactForReader} = require('./audio_catalog_service');

const API_VERSION = 'home-center.local-voice-farm-api.v1';
const PUBLIC_ORIGIN = process.env.HOME_CENTER_LOCAL_VOICE_ORIGIN || 'https://us-central1-home-center-dclar.cloudfunctions.net/localVoiceFarm';
const COLLECTIONS = Object.freeze({
  workers: 'localVoiceFarmWorkers',
  bootstrap: 'localVoiceFarmBootstrapCodes',
  tokens: 'localVoiceFarmWorkerTokens',
  tickets: 'localVoiceFarmTickets',
  artifacts: 'localVoiceFarmArtifacts',
});
const BOOTSTRAP_TTL_MS = 10 * 60 * 1000;
const WORKER_TOKEN_TTL_MS = 90 * 24 * 60 * 60 * 1000;
const MAX_UPLOAD_BYTES = 8 * 1024 * 1024;

function safeText(value, max = 1200) {
  const text = value === undefined || value === null ? '' : String(value).trim();
  return text.length > max ? text.slice(0, max) : text;
}

function hash(value) {
  return createHash('sha256').update(String(value || '')).digest('hex');
}

function safeId(value, label = 'id') {
  const text = safeText(value, 160);
  if (!/^[A-Za-z0-9_.:-]{6,160}$/.test(text)) {
    throw Object.assign(new Error(label + ' must be 6-160 safe identifier characters.'), {status: 400, failureKind: 'local_voice_invalid_id'});
  }
  return text;
}

function safeEmail(value) {
  const text = safeText(value, 320).toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(text)) {
    throw Object.assign(new Error('Authenticated owner email is required.'), {status: 401, failureKind: 'local_voice_owner_required'});
  }
  return text;
}

function ownerKey(email) {
  return 'owner_' + hash(safeEmail(email)).slice(0, 32);
}

function workerDocId(owner, workerId) {
  return hash(owner + '\n' + safeId(workerId, 'workerId'));
}

function ticketDocId(owner, ticketId) {
  return hash(owner + '\n' + safeId(ticketId, 'ticketId'));
}

function artifactDocId(owner, ticketId, name) {
  return hash(owner + '\n' + safeId(ticketId, 'ticketId') + '\n' + safeArtifactName(name));
}

function safeArtifactName(value) {
  const text = safeText(value, 120);
  if (!/^(?:segment-[0-9]{4}|final)\.wav$/.test(text)) {
    throw Object.assign(new Error('Only segment-NNNN.wav and final.wav artifacts are accepted.'), {status: 400, failureKind: 'local_voice_artifact_name_invalid'});
  }
  return text;
}

function bodyObject(req) {
  return req && req.body && typeof req.body === 'object' && !Buffer.isBuffer(req.body) ? req.body : {};
}

function rawBytes(req) {
  if (Buffer.isBuffer(req && req.rawBody)) return req.rawBody;
  if (Buffer.isBuffer(req && req.body)) return req.body;
  if (typeof (req && req.body) === 'string') return Buffer.from(req.body);
  return Buffer.alloc(0);
}

function bearer(req) {
  const header = req && typeof req.get === 'function' ? req.get('Authorization') || '' : '';
  const match = String(header).match(/^Bearer\s+(.+)$/i);
  if (!match) throw Object.assign(new Error('Worker bearer token is required.'), {status: 401, failureKind: 'local_voice_worker_auth_required'});
  return match[1];
}

function routePath(req) {
  const raw = safeText(req && (req.path || req.url), 1000).split('?')[0];
  const marker = '/local-voice-farm/v1/';
  const index = raw.indexOf(marker);
  return index >= 0 ? raw.slice(index + marker.length) : raw.replace(/^\/+/, '');
}

function send(res, status, body) {
  res.status(status).json(body);
}

async function registerWorkerOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const requestId = safeId(args.requestId, 'requestId');
  const email = safeEmail(user && user.email);
  const owner = ownerKey(email);
  const workerId = safeId(args.workerId || 'cauldron-voice-01', 'workerId');
  const capabilities = Array.isArray(args.capabilities) ? args.capabilities.map((item) => safeText(item, 80)).filter(Boolean) : [contract.ENGINE_ID];
  if (!capabilities.includes(contract.ENGINE_ID)) {
    throw Object.assign(new Error('Worker must advertise kokoro-onnx.'), {status: 400, failureKind: 'local_voice_worker_capability_required'});
  }
  const code = randomBytes(24).toString('base64url');
  const digest = hash(code);
  const expiresAtMs = nowMs + BOOTSTRAP_TTL_MS;
  const worker = {
    apiVersion: API_VERSION,
    contractVersion: contract.CONTRACT_VERSION,
    workerId,
    ownerKey: owner,
    ownerEmail: email,
    capabilities: [contract.ENGINE_ID],
    state: 'bootstrap_pending',
    cloningEnabled: false,
    requestId,
    createdAtMs: nowMs,
    updatedAtMs: nowMs,
  };
  const workerRef = admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(owner, workerId));
  const bootstrapRef = admin.firestore().collection(COLLECTIONS.bootstrap).doc(digest);
  await admin.firestore().runTransaction(async (tx) => {
    tx.set(workerRef, worker, {merge: true});
    tx.set(bootstrapRef, {digest, workerRef: workerRef.path, workerId, ownerKey: owner, ownerEmail: email, expiresAtMs, usedAtMs: 0, createdAtMs: nowMs}, {merge: false});
  });
  return {
    status: 'bootstrap_ready',
    workerId,
    contractVersion: contract.CONTRACT_VERSION,
    provider: contract.PROVIDER_ID,
    engine: contract.ENGINE_ID,
    origin: PUBLIC_ORIGIN,
    bootstrapCode: code,
    bootstrapExpiresAtMs: expiresAtMs,
    secretHandling: 'One-time bootstrap code. The exchanged bearer token is returned only to THECAULDRON and is never stored in a ticket.',
    cloningEnabled: false,
  };
}

async function exchangeBootstrap({admin, args = {}, nowMs = Date.now()}) {
  const code = safeText(args.bootstrapCode, 300);
  const workerId = safeId(args.workerId, 'workerId');
  if (!code) throw Object.assign(new Error('bootstrapCode is required.'), {status: 400, failureKind: 'local_voice_bootstrap_required'});
  const bootstrapRef = admin.firestore().collection(COLLECTIONS.bootstrap).doc(hash(code));
  const token = randomBytes(32).toString('base64url');
  const tokenDigest = hash(token);
  let record;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(bootstrapRef);
    if (!snap.exists) throw Object.assign(new Error('Bootstrap code was not found.'), {status: 404, failureKind: 'local_voice_bootstrap_not_found'});
    record = snap.data() || {};
    if (record.workerId !== workerId) throw Object.assign(new Error('Bootstrap code does not belong to this worker.'), {status: 403, failureKind: 'local_voice_bootstrap_worker_mismatch'});
    if (record.usedAtMs) throw Object.assign(new Error('Bootstrap code was already used.'), {status: 409, failureKind: 'local_voice_bootstrap_used'});
    if (Number(record.expiresAtMs || 0) <= nowMs) throw Object.assign(new Error('Bootstrap code expired.'), {status: 410, failureKind: 'local_voice_bootstrap_expired'});
    const tokenRef = admin.firestore().collection(COLLECTIONS.tokens).doc(tokenDigest);
    tx.set(tokenRef, {tokenDigest, workerId, ownerKey: record.ownerKey, ownerEmail: record.ownerEmail, capabilities: [contract.ENGINE_ID], createdAtMs: nowMs, expiresAtMs: nowMs + WORKER_TOKEN_TTL_MS, revokedAtMs: 0}, {merge: false});
    tx.update(bootstrapRef, {usedAtMs: nowMs, tokenDigest});
    tx.set(admin.firestore().doc(record.workerRef), {state: 'registered', tokenDigest, updatedAtMs: nowMs, lastSeenAtMs: nowMs}, {merge: true});
  });
  return {status: 'registered', workerId, token, origin: PUBLIC_ORIGIN, contractVersion: contract.CONTRACT_VERSION, expiresAtMs: nowMs + WORKER_TOKEN_TTL_MS};
}

async function authenticateWorker(admin, req, nowMs = Date.now()) {
  const token = bearer(req);
  const snap = await admin.firestore().collection(COLLECTIONS.tokens).doc(hash(token)).get();
  if (!snap.exists) throw Object.assign(new Error('Worker token is invalid.'), {status: 401, failureKind: 'local_voice_worker_token_invalid'});
  const record = snap.data() || {};
  if (record.revokedAtMs || Number(record.expiresAtMs || 0) <= nowMs) {
    throw Object.assign(new Error(record.revokedAtMs ? 'Worker token was revoked.' : 'Worker token expired.'), {status: 401, failureKind: 'local_voice_worker_token_inactive'});
  }
  const headerWorker = safeId(req.get('X-Home-Center-Worker') || record.workerId, 'workerId');
  if (headerWorker !== record.workerId) throw Object.assign(new Error('Worker header does not match token identity.'), {status: 403, failureKind: 'local_voice_worker_identity_mismatch'});
  return record;
}

async function createTicketOperation({admin, user, args = {}, nowMs = Date.now()}) {
  const email = safeEmail(user && user.email);
  const owner = ownerKey(email);
  const input = {
    requestId: safeId(args.requestId, 'requestId'),
    owner: email,
    text: String(args.text || ''),
    provider: contract.PROVIDER_ID,
    engine: contract.ENGINE_ID,
    modelRevision: safeText(args.modelRevision, 120) || 'kokoro-v1.0',
    voiceProfileId: safeText(args.voiceProfileId, 160) || contract.DEFAULT_VOICE_PROFILE,
    speed: args.speed,
    segmentChars: args.segmentChars,
  };
  const proposed = contract.createTicket(input, null, nowMs);
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, proposed.ticketId));
  let finalTicket;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(ref);
    const existing = snap.exists ? snap.data() : null;
    finalTicket = contract.reconcileTicket(existing, {...proposed, ownerKey: owner, ownerEmail: email, project: safeText(args.project, 120) || 'ferravine', stage: safeText(args.stage, 120) || 'voice-tests', displayName: safeText(args.displayName, 240) || proposed.ticketId + '.wav'});
    if (!existing) tx.create(ref, finalTicket);
  });
  return {status: finalTicket.status, ticketId: finalTicket.ticketId, request: finalTicket.request, receipt: finalTicket.receipt, idempotent: finalTicket.createdAtMs !== nowMs};
}

async function ticketStatusOperation({admin, user, args = {}}) {
  const email = safeEmail(user && user.email);
  const owner = ownerKey(email);
  const ticketId = safeId(args.ticketId || ('lvr-' + safeId(args.requestId, 'requestId')), 'ticketId');
  const snap = await admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(owner, ticketId)).get();
  if (!snap.exists) throw Object.assign(new Error('Local voice ticket was not found.'), {status: 404, failureKind: 'local_voice_ticket_not_found'});
  const ticket = snap.data() || {};
  return {ticketId: ticket.ticketId, status: ticket.status, request: ticket.request, receipt: ticket.receipt, artifact: ticket.artifact || null, readerRegistration: ticket.readerRegistration || null, updatedAtMs: ticket.updatedAtMs};
}

async function leaseTicket({admin, worker, args = {}, nowMs = Date.now()}) {
  const query = await admin.firestore().collection(COLLECTIONS.tickets).where('ownerKey', '==', worker.ownerKey).limit(25).get();
  const candidates = query.docs.map((doc) => ({ref: doc.ref, ticket: doc.data()})).filter((item) => ['queued', 'leased', 'running'].includes(item.ticket.status)).sort((a, b) => Number(a.ticket.createdAtMs || 0) - Number(b.ticket.createdAtMs || 0));
  for (const candidate of candidates) {
    try {
      let leased;
      await admin.firestore().runTransaction(async (tx) => {
        const snap = await tx.get(candidate.ref);
        if (!snap.exists) throw Object.assign(new Error('Ticket disappeared.'), {status: 409});
        leased = contract.leaseTicket(snap.data(), {workerId: worker.workerId, capabilities: worker.capabilities || []}, nowMs);
        tx.set(candidate.ref, leased, {merge: false});
      });
      await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'leased', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
      return {ticket: leased, pollAfterSeconds: 2};
    } catch (error) {
      if (!['local_voice_ticket_already_leased', 'local_voice_ticket_not_leasable'].includes(error.code)) throw error;
    }
  }
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {ticket: null, pollAfterSeconds: 5};
}

async function ticketForWorker(admin, worker, ticketId) {
  const ref = admin.firestore().collection(COLLECTIONS.tickets).doc(ticketDocId(worker.ownerKey, ticketId));
  const snap = await ref.get();
  if (!snap.exists) throw Object.assign(new Error('Ticket was not found.'), {status: 404, failureKind: 'local_voice_ticket_not_found'});
  const ticket = snap.data() || {};
  if (ticket.ownerKey !== worker.ownerKey) throw Object.assign(new Error('Ticket is not owned by this worker token.'), {status: 404, failureKind: 'local_voice_ticket_not_found'});
  return {ref, ticket};
}

async function heartbeat({admin, worker, ticketId, args = {}, nowMs = Date.now()}) {
  const found = await ticketForWorker(admin, worker, ticketId);
  let updated;
  await admin.firestore().runTransaction(async (tx) => {
    const snap = await tx.get(found.ref);
    updated = contract.heartbeatTicket(snap.data(), worker.workerId, nowMs);
    const completed = Array.isArray(args.completedSegmentIndexes) ? [...new Set(args.completedSegmentIndexes.map(Number).filter(Number.isInteger))].sort((a, b) => a - b) : updated.completedSegmentIndexes || [];
    updated = {...updated, phase: safeText(args.phase, 80) || 'running', completedSegmentIndexes: completed};
    tx.set(found.ref, updated, {merge: false});
  });
  return {status: updated.status, ticketId: updated.ticketId, lease: updated.lease, completedSegmentIndexes: updated.completedSegmentIndexes};
}

async function uploadArtifact({admin, worker, ticketId, name, bytes, expectedSha256, nowMs = Date.now()}) {
  name = safeArtifactName(name);
  if (!Buffer.isBuffer(bytes) || bytes.length < 44 || bytes.length > MAX_UPLOAD_BYTES) throw Object.assign(new Error('WAV upload size is invalid.'), {status: 413, failureKind: 'local_voice_artifact_size_invalid'});
  if (bytes.subarray(0, 4).toString('ascii') !== 'RIFF' || bytes.subarray(8, 12).toString('ascii') !== 'WAVE') throw Object.assign(new Error('Artifact is not a RIFF/WAVE file.'), {status: 415, failureKind: 'local_voice_artifact_container_invalid'});
  const actualSha256 = hash(bytes);
  if (!/^[a-f0-9]{64}$/.test(String(expectedSha256 || '')) || actualSha256 !== expectedSha256) throw Object.assign(new Error('Upload SHA-256 mismatch.'), {status: 409, failureKind: 'local_voice_artifact_sha_mismatch'});
  const found = await ticketForWorker(admin, worker, ticketId);
  if (!found.ticket.lease || found.ticket.lease.workerId !== worker.workerId || Number(found.ticket.lease.expiresAtMs || 0) <= nowMs) throw Object.assign(new Error('Worker does not own a current ticket lease.'), {status: 409, failureKind: 'local_voice_lease_owner_mismatch'});
  const artifactRef = admin.firestore().collection(COLLECTIONS.artifacts).doc(artifactDocId(worker.ownerKey, ticketId, name));
  const prior = await artifactRef.get();
  if (prior.exists) {
    const data = prior.data() || {};
    if (data.sha256 !== actualSha256 || Number(data.byteCount) !== bytes.length) throw Object.assign(new Error('Artifact name already exists with different bytes.'), {status: 409, failureKind: 'local_voice_artifact_conflict'});
    return {...data, reused: true};
  }
  const artifact = await uploadGeneratedArtifact({
    bytes,
    name,
    mimeType: 'audio/wav',
    owner: worker.ownerEmail,
    ownerEmail: worker.ownerEmail,
    project: found.ticket.project || 'ferravine',
    stage: found.ticket.stage || 'voice-tests',
    engine: contract.ENGINE_ID,
    createdBy: worker.workerId,
    executionAuthorized: true,
    authorizationState: 'owner_scoped',
    humanAcceptance: 'unreviewed',
    requestId: found.ticket.request.requestId,
    artifactType: 'voice-test',
    prefix: 'audio/' + worker.ownerKey + '/voice-tests/' + ticketId,
  });
  const record = {...artifact, ticketId, workerId: worker.workerId, ownerKey: worker.ownerKey, uploadedAtMs: nowMs, reused: false};
  await artifactRef.create(record);
  return record;
}

async function downloadArtifact({admin, worker, ticketId, name}) {
  name = safeArtifactName(name);
  await ticketForWorker(admin, worker, ticketId);
  const snap = await admin.firestore().collection(COLLECTIONS.artifacts).doc(artifactDocId(worker.ownerKey, ticketId, name)).get();
  if (!snap.exists) throw Object.assign(new Error('Checkpoint artifact was not found.'), {status: 404, failureKind: 'local_voice_artifact_not_found'});
  const record = snap.data() || {};
  const inspected = await inspectGeneratedArtifact(record.storageRef || record.durableRef);
  if (!inspected || inspected.sha256 !== record.sha256 || inspected.byteCount !== record.byteCount) throw Object.assign(new Error('Checkpoint readback identity failed.'), {status: 502, failureKind: 'local_voice_artifact_readback_failed'});
  return inspected;
}

async function completeTicket({admin, worker, ticketId, args = {}, nowMs = Date.now()}) {
  const found = await ticketForWorker(admin, worker, ticketId);
  if (!found.ticket.lease || found.ticket.lease.workerId !== worker.workerId || Number(found.ticket.lease.expiresAtMs || 0) <= nowMs) throw Object.assign(new Error('Worker does not own a current ticket lease.'), {status: 409, failureKind: 'local_voice_lease_owner_mismatch'});
  const artifactSnap = await admin.firestore().collection(COLLECTIONS.artifacts).doc(artifactDocId(worker.ownerKey, ticketId, 'final.wav')).get();
  if (!artifactSnap.exists) throw Object.assign(new Error('Final WAV artifact is missing.'), {status: 409, failureKind: 'local_voice_final_missing'});
  const artifact = artifactSnap.data() || {};
  const inspected = await inspectGeneratedArtifact(artifact.storageRef || artifact.durableRef);
  const verified = contract.validateArtifactReceipt(found.ticket, {
    provider: args.provider,
    engine: args.engine,
    inputSha256: args.inputSha256,
    cloudSpeechSynthesisUsed: args.cloudSpeechSynthesisUsed,
    sha256: artifact.sha256,
    byteCount: artifact.byteCount,
    readbackSha256: inspected.sha256,
    readbackByteCount: inspected.byteCount,
    modelRevision: args.modelRevision,
    voiceProfileId: args.voiceProfileId,
    segmentCheckpoints: Array.isArray(args.segmentCheckpoints) ? args.segmentCheckpoints : [],
    textSha256: args.textSha256,
  });
  if (!verified.verified) throw Object.assign(new Error('Final WAV failed readback equality.'), {status: 502, failureKind: 'local_voice_final_readback_failed'});
  const readerRegistration = await registerAudioArtifactForReader({
    ownerEmail: worker.ownerEmail,
    output: {name: found.ticket.displayName || 'Fortress-interface-ready.wav', mimeType: 'audio/wav', storageRef: artifact.storageRef, durableRef: artifact.storageRef, byteCount: artifact.byteCount, sha256: artifact.sha256},
    producerReceiptId: found.ticket.request.requestId,
    project: found.ticket.project || 'ferravine',
    stage: found.ticket.stage || 'voice-tests',
  });
  const completed = {...found.ticket, status: 'completed', updatedAtMs: nowMs, lease: null, artifact, receipt: {...found.ticket.receipt, ...verified, completedAtMs: nowMs}, readerRegistration};
  await found.ref.set(completed, {merge: false});
  await admin.firestore().collection(COLLECTIONS.workers).doc(workerDocId(worker.ownerKey, worker.workerId)).set({state: 'idle', lastSeenAtMs: nowMs, updatedAtMs: nowMs}, {merge: true});
  return {status: 'completed', ticketId, artifact, receipt: completed.receipt, readerRegistration};
}

function localVoiceOperationEntries() {
  return {
    'local_voice.worker.register': {summary: 'Mint a ten-minute one-time bootstrap code for an owner-scoped outbound THECAULDRON worker. The code exchanges directly on the worker host; no reusable token is returned to ChatGPT.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', workerId: 'cauldron-voice-01', capabilities: 'optional string[]'}, output: {status: 'bootstrap_ready', bootstrapCode: 'one-time secret', origin: 'worker HTTPS origin', cloningEnabled: 'false'}},
    'local_voice.ticket.create': {summary: 'Create or idempotently reuse one immutable local Kokoro fixed-voice ticket. Cloud fallback and Venice identity claims are forbidden.', write: true, requiresRequestId: true, requiredScopes: [], input: {requestId: 'stable id', text: 'required transcript', voiceProfileId: 'fixed:kokoro:af_heart', project: 'optional', stage: 'optional', displayName: 'optional'}, output: {status: 'queued|leased|running|completed', ticketId: 'stable id', request: 'immutable contract'}},
    'local_voice.ticket.status': {summary: 'Read one owner-scoped local voice ticket, final GCS identity, and Audio Reader playback registration.', write: false, requiresRequestId: false, requiredScopes: [], input: {ticketId: 'ticket id or requestId alias', requestId: 'optional request id'}, output: {status: 'ticket state', artifact: 'verified GCS identity when complete', readerRegistration: 'authenticated discovery and playback probe when complete'}},
  };
}

async function localVoiceOperationRunOperation({admin, user, operation, args = {}}) {
  if (operation === 'local_voice.worker.register') return registerWorkerOperation({admin, user, args});
  if (operation === 'local_voice.ticket.create') return createTicketOperation({admin, user, args});
  if (operation === 'local_voice.ticket.status') return ticketStatusOperation({admin, user, args});
  throw Object.assign(new Error('Unsupported local voice operation.'), {status: 400, failureKind: 'local_voice_operation_unsupported'});
}

function createLocalVoiceFarmHandler({admin}) {
  return async (req, res) => {
    try {
      const path = routePath(req);
      if (req.method === 'GET' && path === 'health') return send(res, 200, {ok: true, service: 'local-voice-farm', apiVersion: API_VERSION, contractVersion: contract.CONTRACT_VERSION, provider: contract.PROVIDER_ID, engine: contract.ENGINE_ID, cloningEnabled: false});
      if (req.method === 'POST' && path === 'bootstrap') return send(res, 200, await exchangeBootstrap({admin, args: bodyObject(req)}));
      const worker = await authenticateWorker(admin, req);
      if (req.method === 'POST' && path === 'lease') return send(res, 200, await leaseTicket({admin, worker, args: bodyObject(req)}));
      const match = path.match(/^tickets\/([^/]+)\/(heartbeat|complete)$/);
      if (req.method === 'POST' && match && match[2] === 'heartbeat') return send(res, 200, await heartbeat({admin, worker, ticketId: match[1], args: bodyObject(req)}));
      if (req.method === 'POST' && match && match[2] === 'complete') return send(res, 200, await completeTicket({admin, worker, ticketId: match[1], args: bodyObject(req)}));
      const artifactMatch = path.match(/^tickets\/([^/]+)\/artifacts\/([^/]+)$/);
      if (req.method === 'PUT' && artifactMatch) {
        const expected = safeText(req.query && req.query.sha256, 80).toLowerCase();
        return send(res, 200, await uploadArtifact({admin, worker, ticketId: artifactMatch[1], name: artifactMatch[2], bytes: rawBytes(req), expectedSha256: expected}));
      }
      if (req.method === 'GET' && artifactMatch) {
        const artifact = await downloadArtifact({admin, worker, ticketId: artifactMatch[1], name: artifactMatch[2]});
        res.set('Content-Type', 'audio/wav');
        res.set('Content-Length', String(artifact.byteCount));
        res.set('X-Content-SHA256', artifact.sha256);
        return res.status(200).send(artifact.bytes);
      }
      return send(res, 404, {ok: false, error: 'local_voice_route_not_found'});
    } catch (error) {
      return send(res, Number(error.status) || 500, {ok: false, error: error.failureKind || error.code || 'local_voice_failed', detail: safeText(error.message || String(error), 500)});
    }
  };
}

module.exports = {
  API_VERSION,
  PUBLIC_ORIGIN,
  COLLECTIONS,
  hash,
  ownerKey,
  safeArtifactName,
  localVoiceOperationEntries,
  localVoiceOperationRunOperation,
  registerWorkerOperation,
  createTicketOperation,
  ticketStatusOperation,
  createLocalVoiceFarmHandler,
};
