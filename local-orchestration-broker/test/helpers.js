'use strict';

const { computeCommissionHash, sha256 } = require('../src/contracts');

const hash = character => character.repeat(64);
const capabilityStates = Object.freeze({ requested: true, implemented: true, tested: true, deployed: false, callable: false, delivered: false, accepted: false });

function commission(overrides = {}) {
  const value = {
    commissionId: 'commission-1',
    queue: { documentId: 'queue-doc', folderId: 'queue-folder', revision: 'revision-10', stateOwner: 'Adam' },
    lane: { laneId: 'broker-repair', owner: 'worker-1' },
    worker: { workerId: 'worker-1', identityHash: hash('a') },
    mutating: false,
    operations: ['health', 'identity'],
    ...overrides
  };
  value.commissionHash = computeCommissionHash(value);
  return value;
}

function evidence() {
  return { evidenceId: 'e-1', kind: 'test-log', ref: 'artifact://test-log', sha256: hash('b'), observedAt: '2026-08-11T10:00:00Z' };
}

function audioLease() {
  return { leaseId: 'audio-1', holderId: 'worker-1', deviceId: 'speakers-1', fencingToken: 2, acquiredAt: '2026-08-11T10:00:00Z', expiresAt: '2026-08-11T10:05:00Z' };
}

function digestRecord(value, key) {
  const copy = { ...value };
  delete copy[key];
  return { ...value, [key]: sha256(copy) };
}

module.exports = { hash, capabilityStates, commission, evidence, audioLease, digestRecord };
