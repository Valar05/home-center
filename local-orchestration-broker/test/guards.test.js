'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { sha256 } = require('../src/contracts');
const { authorizeReadOnly, BrokerGateError, leaseDigestPayload, validateQueueLease, authorizeCompactionFence, approvalDigestPayload, validateApproval, authorizeApproval } = require('../src/guards');
const { hash, commission } = require('./helpers');

const current = commission();
const trusted = { commissionId: current.commissionId, commissionHash: current.commissionHash, queueDocumentId: current.queue.documentId, queueFolderId: current.queue.folderId, queueRevision: current.queue.revision, stateOwner: current.queue.stateOwner, laneId: current.lane.laneId, laneOwner: current.lane.owner, workerId: current.worker.workerId, workerIdentityHash: current.worker.identityHash, mutating: current.mutating, operations: current.operations };

test('matching trusted state authorizes only exact read-only probes', () => assert.equal(authorizeReadOnly(current, trusted).authorized, true));

for (const [name, changed, code] of [
  ['commission id', { commissionId: 'other' }, 'COMMISSION_MISMATCH'], ['commission hash', { commissionHash: hash('c') }, 'COMMISSION_MISMATCH'],
  ['queue document', { queueDocumentId: 'other' }, 'QUEUE_MISMATCH'], ['queue folder', { queueFolderId: 'other' }, 'QUEUE_MISMATCH'],
  ['revision', { queueRevision: 'other' }, 'STALE_REVISION'], ['state owner', { stateOwner: 'other' }, 'OWNER_MISMATCH'],
  ['lane id', { laneId: 'other' }, 'LANE_MISMATCH'], ['lane owner', { laneOwner: 'other' }, 'OWNER_MISMATCH'],
  ['worker', { workerId: 'other' }, 'IDENTITY_MISMATCH'], ['worker hash', { workerIdentityHash: hash('d') }, 'IDENTITY_MISMATCH'],
  ['mutating flag', { mutating: true }, 'MUTATION_MISMATCH'], ['operations', { operations: ['health'] }, 'OPERATION_MISMATCH']
]) test(`read-only guard rejects ${name} drift`, () => assert.throws(() => authorizeReadOnly(current, { ...trusted, ...changed }), error => error instanceof BrokerGateError && error.code === code));

test('queue compaction requires exact unexpired fenced CAS lease', () => {
  const lease = { leaseId: 'lease-1', documentId: 'doc', folderId: 'folder', revision: 'r1', stateOwner: 'Adam', holderId: 'worker', fencingToken: 7, acquiredAt: '2026-08-11T10:00:00Z', expiresAt: '2026-08-11T10:05:00Z' };
  lease.leaseDigest = sha256(leaseDigestPayload(lease));
  const fence = { documentId: 'doc', folderId: 'folder', revision: 'r1', stateOwner: 'Adam', holderId: 'worker', fencingToken: 7 };
  assert.equal(validateQueueLease(lease).ok, true);
  assert.equal(authorizeCompactionFence(lease, fence, '2026-08-11T10:01:00Z').authorized, true);
  assert.throws(() => authorizeCompactionFence(lease, { ...fence, fencingToken: 6 }, '2026-08-11T10:01:00Z'), error => error.code === 'STALE_FENCE');
  assert.throws(() => authorizeCompactionFence(lease, fence, '2026-08-11T10:05:00Z'), error => error.code === 'LEASE_EXPIRED');
});

test('approval is digest-bound, expiring, scoped, and single-use', () => {
  const approval = { approvalId: 'a1', actor: 'Drew', action: 'playback', target: 'speakers-1', artifactDigest: hash('a'), environment: 'desktop', commissionHash: hash('b'), issuedAt: '2026-08-11T10:00:00Z', expiresAt: '2026-08-11T10:05:00Z', maxUses: 1, useCount: 0, state: 'GRANTED_SCOPED' };
  approval.approvalDigest = sha256(approvalDigestPayload(approval));
  const requested = { actor: 'Drew', action: 'playback', target: 'speakers-1', artifactDigest: hash('a'), environment: 'desktop', commissionHash: hash('b') };
  assert.equal(validateApproval(approval).ok, true);
  const consumed = authorizeApproval(approval, requested, '2026-08-11T10:01:00Z');
  assert.equal(consumed.state, 'CONSUMED');
  assert.equal(validateApproval(consumed).ok, true);
  assert.throws(() => authorizeApproval({ ...approval, state: 'CONSUMED', useCount: 1 }, requested, '2026-08-11T10:01:00Z'), error => error.code === 'INVALID_APPROVAL' || error.code === 'APPROVAL_UNAVAILABLE');
  assert.throws(() => authorizeApproval(approval, { ...requested, target: 'other' }, '2026-08-11T10:01:00Z'), error => error.code === 'APPROVAL_SCOPE_MISMATCH');
});
