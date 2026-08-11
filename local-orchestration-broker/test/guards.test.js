'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const { sha256 } = require('../src/contracts');
const { authorizeReadOnly, BrokerGateError, leaseDigestPayload, validateQueueLease, authorizeCompactionFence, approvalDigestPayload, validateApproval, authorizeApproval, validateConsumptionCas } = require('../src/guards');
const { hash, commission } = require('./helpers');
const current = commission();
const trusted = { commissionId: current.commissionId, commissionHash: current.commissionHash, queueDocumentId: current.queue.documentId, queueFolderId: current.queue.folderId, queueRevision: current.queue.revision, stateOwner: current.queue.stateOwner, laneId: current.lane.laneId, laneOwner: current.lane.owner, workerId: current.worker.workerId, workerIdentityHash: current.worker.identityHash, mutating: current.mutating, operations: current.operations };
test('trusted read-only commission is exact', () => {
  assert.equal(authorizeReadOnly(current, trusted).authorized, true);
  for (const changed of [{ queueRevision: 'stale' }, { workerId: 'other' }, { mutating: true }, { operations: ['health'] }]) assert.throws(() => authorizeReadOnly(current, { ...trusted, ...changed }), BrokerGateError);
});
function lease() { const v = { leaseId: 'lease-1', documentId: 'doc', folderId: 'folder', revision: 'r1', stateOwner: 'Adam', holderId: 'worker', fencingToken: 7, acquiredAt: '2026-08-11T10:00:00Z', expiresAt: '2026-08-11T10:05:00Z' }; v.leaseDigest = sha256(leaseDigestPayload(v)); return v; }
test('queue lease identity is persistent, fenced, CAS-consumed, and replay rejected', () => {
  const value = lease(); const registry = { registryId: 'leases', revision: 4, leaseRecord: value, records:{[value.leaseId]:value}, consumedLeaseIds: [], consumedIdempotencyKeys:[] };
  assert.equal(validateQueueLease(value).ok, true);
  const out = authorizeCompactionFence(value, registry, '2026-08-11T10:01:00Z');
  assert.equal(out.authorized, true);
  assert.equal(validateConsumptionCas(out.cas, { registryId: 'leases', revision: 4, records: { [value.leaseId]: value }, consumedIdempotencyKeys: [] }).ok, true);
  for (const changed of [{ leaseId: 'forged' }, { fencingToken: 8 }, { acquiredAt: '2026-08-11T10:00:01Z' }]) assert.throws(() => authorizeCompactionFence({ ...value, ...changed }, registry, '2026-08-11T10:01:00Z'), BrokerGateError);
  assert.throws(() => authorizeCompactionFence(value, { ...registry, consumedLeaseIds: ['lease-1'] }, '2026-08-11T10:01:00Z'), error => error.code === 'LEASE_REPLAY');
  assert.throws(() => authorizeCompactionFence(value, { leaseRecord:value,consumedLeaseIds:[] }, '2026-08-11T10:01:00Z'), error => error.code === 'TRUST_STATE_MISSING');
});
function approval() { const v = { approvalId: 'a1', actor: 'Drew', action: 'playback', target: 'speakers-1', artifactDigest: hash('a'), environment: 'desktop', commissionHash: hash('b'), issuedAt: '2026-08-11T10:00:00Z', expiresAt: '2026-08-11T10:05:00Z', maxUses: 1, useCount: 0, state: 'GRANTED_SCOPED' }; v.approvalDigest = sha256(approvalDigestPayload(v)); return v; }
test('approval is full-record trusted, digest-bound, expiring, scoped, and single-use', () => {
  const value = approval(); const request = { actor: 'Drew', action: 'playback', target: 'speakers-1', artifactDigest: hash('a'), environment: 'desktop', commissionHash: hash('b'), idempotencyKey: 'play-once' };
  const registry = { registryId: 'approvals', revision: 2, records: { a1: value }, consumedIdempotencyKeys: [] };
  const out = authorizeApproval(value, request, '2026-08-11T10:01:00Z', registry);
  assert.equal(validateApproval(out.consumed).ok, true); assert.equal(validateConsumptionCas(out.cas, registry).ok, true);
  assert.throws(() => authorizeApproval(value, request, '2026-08-11T10:01:00Z', { ...registry, consumedIdempotencyKeys: ['play-once'] }), error => error.code === 'APPROVAL_REPLAY');
  assert.throws(() => authorizeApproval(value, { ...request, target: 'other' }, '2026-08-11T10:01:00Z', registry), error => error.code === 'APPROVAL_SCOPE_MISMATCH');
  assert.throws(() => authorizeApproval(value, request, '2026-08-11T10:01:00Z', { ...registry, records: { a1: { ...value, target: 'other' } } }), error => error.code === 'APPROVAL_IDENTITY_MISMATCH');
});
