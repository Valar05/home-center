'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { authorizeReadOnly, BrokerGateError } = require('../src/guards');

const hash = 'b'.repeat(64);
const commission = { commissionId: 'c1', commissionHash: hash, queue: { documentId: 'doc', folderId: 'folder', revision: 'r10', stateOwner: 'Adam' }, lane: { laneId: 'l1', owner: 'w1' }, worker: { workerId: 'w1', identityHash: hash }, mutating: false, operations: ['health', 'identity'] };
const trusted = { queueRevision: 'r10', stateOwner: 'Adam', laneOwner: 'w1', workerId: 'w1', workerIdentityHash: hash, commissionHash: hash };

test('matching trusted state authorizes only read-only probes', () => assert.equal(authorizeReadOnly(commission, trusted).authorized, true));

for (const [name, changed, code] of [
  ['stale revision', { queueRevision: 'r9' }, 'STALE_REVISION'],
  ['wrong state owner', { stateOwner: 'other' }, 'OWNER_MISMATCH'],
  ['wrong lane owner', { laneOwner: 'other' }, 'OWNER_MISMATCH'],
  ['wrong worker', { workerId: 'other' }, 'IDENTITY_MISMATCH'],
  ['wrong identity digest', { workerIdentityHash: 'c'.repeat(64) }, 'IDENTITY_MISMATCH'],
  ['wrong commission digest', { commissionHash: 'c'.repeat(64) }, 'COMMISSION_MISMATCH']
]) test(`fails closed on ${name}`, () => assert.throws(() => authorizeReadOnly(commission, { ...trusted, ...changed }), error => error instanceof BrokerGateError && error.code === code));

test('fails closed on mutating and unknown operations', () => {
  assert.throws(() => authorizeReadOnly({ ...commission, mutating: true }, trusted), error => error.code === 'INVALID_COMMISSION');
  assert.throws(() => authorizeReadOnly({ ...commission, operations: ['execute'] }, trusted), error => error.code === 'INVALID_COMMISSION');
});
