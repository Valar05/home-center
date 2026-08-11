'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { sha256 } = require('../src/contracts');
const { leaseDigestPayload } = require('../src/guards');
const { validateSacredSession, validateAppendOnlyEvent, eventDigestPayload, validateRollingCheckpoint, checkpointDigestPayload, validateContextRebuild } = require('../src/continuity');
const { hash } = require('./helpers');

function session() {
  return { sessionId: 'session-1', runtime: 'codex', model: 'gpt', modelVersion: '1', host: 'desktop', ticketId: 'ticket-1', jobId: 'job-1', laneId: 'lane-1', promptRef: 'artifact://prompt', promptSha256: hash('a'), identityHash: hash('b'), repository: 'Valar05/home-center', worktree: 'C:/isolated', branch: 'agent/branch', head: hash('c').slice(0, 40), evidencePointers: ['artifact://rollout'], state: 'TRANSPORT_TIMEOUT', resumeCommand: 'codex exec resume exact-session' };
}

function event(sequence, previousEventHash = null, observedAt = '2026-08-11T10:00:00Z') {
  const value = { eventId: `event-${sequence}`, kind: 'SESSION_EVENT', sequence, observedAt, payload: { sessionId: 'session-1', state: 'RUNNING' }, previousEventHash };
  value.payloadHash = sha256(value.payload);
  value.eventHash = sha256(eventDigestPayload(value));
  return value;
}

function lease() {
  const value = { leaseId: 'lease-1', documentId: 'doc', folderId: 'folder', revision: 'r10', stateOwner: 'Adam', holderId: 'worker-1', fencingToken: 3, acquiredAt: '2026-08-11T10:00:00Z', expiresAt: '2026-08-11T10:05:00Z' };
  value.leaseDigest = sha256(leaseDigestPayload(value));
  return value;
}

test('sacred session registry keeps exact resume identity through timeout', () => {
  assert.equal(validateSacredSession(session()).ok, true);
  assert.equal(validateSacredSession({ ...session(), resumeCommand: '' }).ok, false);
  assert.equal(validateSacredSession({ ...session(), identityHash: 'weak' }).ok, false);
});

test('rolling events are append-only and hash chained', () => {
  const first = event(1);
  const second = event(2, first.eventHash, '2026-08-11T10:01:00Z');
  assert.equal(validateAppendOnlyEvent(first).ok, true);
  assert.equal(validateAppendOnlyEvent(second, first).ok, true);
  assert.equal(validateAppendOnlyEvent({ ...second, sequence: 3 }, first).ok, false);
  assert.equal(validateAppendOnlyEvent({ ...second, previousEventHash: hash('f') }, first).ok, false);
});

test('checkpoint binds queue revision, watermark, leases, gates, sessions, and evidence', () => {
  const value = { checkpointId: 'cp-1', reason: 'CONTEXT_COMPACTION', createdAt: '2026-08-11T10:02:00Z', queueDocumentId: 'doc', queueFolderId: 'folder', queueRevision: 'r10', stateOwner: 'Adam', compactionWatermark: 2, eventHashAtWatermark: hash('d'), activeLeases: [lease()], unresolvedGates: [{ gateId: 'g1', laneId: 'voice', action: 'playback', reason: 'human audio acceptance', requiredAuthority: 'Drew' }], sessions: [session()], pendingReceipts: [{ receiptId: 'r1', laneId: 'voice', receiptHash: hash('e') }], evidencePointers: ['artifact://receipt'] };
  value.checkpointHash = sha256(checkpointDigestPayload(value));
  assert.equal(validateRollingCheckpoint(value).ok, true);
  assert.equal(validateRollingCheckpoint({ ...value, compactionWatermark: 1 }).ok, false);
  assert.equal(validateRollingCheckpoint({ ...value, evidencePointers: [] }).ok, false);
});

test('new Voice context rebuilds only from exact durable watermark and pending state', () => {
  const trusted = { queueDocumentId: 'doc', queueFolderId: 'folder', queueRevision: 'r10', stateOwner: 'Adam', checkpointHash: hash('a'), eventHashAtWatermark: hash('b'), compactionWatermark: 9, sessionIds: ['s1'], pendingReceipts: [{ receiptId: 'r1', laneId: 'voice', receiptHash: hash('c') }] };
  const rebuild = { ...trusted, source: 'DURABLE_QUEUE_REGISTRY_AND_PENDING_RECEIPTS' };
  assert.equal(validateContextRebuild(rebuild, trusted).ok, true);
  assert.equal(validateContextRebuild({ ...rebuild, queueRevision: 'stale' }, trusted).ok, false);
  assert.equal(validateContextRebuild({ ...rebuild, pendingReceipts: [] }, trusted).ok, false);
  assert.equal(validateContextRebuild({ ...rebuild, source: 'CHAT_SUMMARY' }, trusted).ok, false);
});
