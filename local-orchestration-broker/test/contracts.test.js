'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { STATES, validateCommissionEnvelope, validateStateRecord, validateFindingCard, validateReceipt, canonicalJson, sha256 } = require('../src/contracts');

const hash = 'a'.repeat(64);

test('state vocabularies preserve the architecture contract', () => {
  assert.equal(validateStateRecord('queue', 'OPEN').ok, true);
  assert.equal(validateStateRecord('lane', 'TRANSITION_VERIFIED').ok, true);
  assert.equal(validateStateRecord('job', 'MATERIAL_TRANSITION').ok, true);
  assert.equal(validateStateRecord('session', 'NONRESUMABLE_PROVEN').ok, true);
  assert.equal(validateStateRecord('approval', 'CONSUMED').ok, true);
  assert.equal(validateStateRecord('compaction', 'COMPACTED_READBACK_VERIFIED').ok, true);
  assert.equal(validateStateRecord('lane', 'IDENTITY_LOST').ok, false);
  assert.equal(STATES.lane.length, 11);
});

test('commission envelopes are read-only and identity bound', () => {
  const envelope = { commissionId: 'c1', commissionHash: hash, queue: { documentId: 'doc', folderId: 'folder', revision: 'r1', stateOwner: 'Adam' }, lane: { laneId: 'lane', owner: 'worker-1' }, worker: { workerId: 'worker-1', identityHash: hash }, mutating: false, operations: ['health', 'identity'] };
  assert.deepEqual(validateCommissionEnvelope(envelope), { ok: true, errors: [] });
  assert.equal(validateCommissionEnvelope({ ...envelope, mutating: true }).ok, false);
  assert.equal(validateCommissionEnvelope({ ...envelope, operations: ['dispatch'] }).ok, false);
});

test('finding and receipt contracts require evidence shapes', () => {
  assert.equal(validateFindingCard({ findingId: 'f1', observedBySession: 's1', observedAt: 't', affectedLaneIds: ['l1'], claim: 'claim', evidenceRefs: ['r'], evidenceHashes: [hash], confidence: 'high', gateImpact: 'narrows', recommendedAction: 'inspect', scopeChange: false }).ok, true);
  assert.equal(validateReceipt({ receiptId: 'r1', commissionHash: hash, laneId: 'l1', workerId: 'w1', priorState: 'UNIMPLEMENTED', newState: 'IMPLEMENTED_AND_TESTED_CANDIDATE', artifacts: [], tests: [], evidenceRefs: [], findings: [], remainingGate: 'review', nextAction: 'review' }).ok, true);
});

test('canonical hashes are deterministic', () => {
  assert.equal(canonicalJson({ b: 2, a: 1 }), canonicalJson({ a: 1, b: 2 }));
  assert.equal(sha256({ b: 2, a: 1 }), sha256({ a: 1, b: 2 }));
});
