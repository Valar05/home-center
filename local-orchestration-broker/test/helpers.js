'use strict';

const { computeCommissionHash, evidenceRecordPayload, sha256 } = require('../src/contracts');

const hash = character => character.repeat(64);
const gitHead = character => character.repeat(40);
const capabilityStates = Object.freeze({ requested: true, implemented: true, tested: true, deployed: false, callable: false, delivered: false, accepted: false });

function commission(overrides = {}) {
  const value = { commissionId: 'commission-1', queue: { documentId: 'queue-doc', folderId: 'queue-folder', revision: 'revision-10', stateOwner: 'Adam' }, lane: { laneId: 'broker-repair', owner: 'worker-1' }, worker: { workerId: 'worker-1', identityHash: hash('a') }, mutating: false, operations: ['health', 'identity'], ...overrides };
  value.commissionHash = computeCommissionHash(value);
  return value;
}

function device() { return { deviceId: 'phone-1', appId: 'venice.mobile', buildId: 'build-7', accountId: 'account-1' }; }
function mobileSession() { return { mobileSessionId: 'mobile-session-1', conversationId: 'conversation-1', turnId: 'turn-1' }; }

function audioLease(overrides = {}) {
  const value = { leaseId: 'audio-1', holderId: 'worker-1', commissionHash: hash('c'), queueRevision: 'r1', laneId: 'audio-lane', jobId: 'job-1', sessionId: 'session-1', conversationId: 'conversation-1', channel: 'DYNAMIC_ASMR', target: { deviceId: 'phone-1', appId: 'venice.mobile', buildId:'build-7', accountId: 'account-1' }, action: 'PLAY_CUE', idempotencyNamespace: 'asmr-lane', fencingToken: 2, acquiredAt: '2026-08-11T10:00:00Z', expiresAt: '2026-08-11T10:05:00Z', state: 'ACTIVE', muteState: 'AUDIBLE_ALLOWED', unattended: false, ...overrides };
  const payload = { ...value };
  delete payload.leaseDigest;
  value.leaseDigest = sha256(payload);
  return value;
}

function leaseOptions(lease, now = '2026-08-11T10:01:00Z') { return { now, trustedLease: lease, registry: { consumedLeaseIds: [] }, activeLeases: [lease] }; }

function artifactEvidence() {
  const value = { kind: 'ARTIFACT', evidenceId: 'artifact-1', ref: 'artifact://candidate', verifierId: 'verifier-1', contentSha256: hash('d'), verifiedAt: '2026-08-11T10:00:00Z', byteSize: 42 };
  value.recordHash = sha256(evidenceRecordPayload(value));
  return value;
}

function testEvidence() {
  const value = { kind: 'TEST', evidenceId: 'test-1', ref: 'artifact://test-log', verifierId: 'verifier-1', contentSha256: hash('e'), verifiedAt: '2026-08-11T10:01:00Z', command: 'npm test', exitCode: 0, logSha256: hash('f'), head: gitHead('a') };
  value.recordHash = sha256(evidenceRecordPayload(value));
  return value;
}

module.exports = { hash, gitHead, capabilityStates, commission, device, mobileSession, audioLease, leaseOptions, artifactEvidence, testEvidence };

