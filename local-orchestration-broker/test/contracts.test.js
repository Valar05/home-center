'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { STATES, validateCommissionEnvelope, validateStateRecord, validateFindingCard, validateReceipt, receiptDigestPayload, canonicalJson, sha256 } = require('../src/contracts');
const { hash, gitHead, capabilityStates, commission, artifactEvidence, testEvidence } = require('./helpers');

test('state vocabularies are exact and reject invented states', () => {
  for (const [kind, value] of [['queue', 'OPEN'], ['lane', 'TRANSITION_VERIFIED'], ['job', 'MATERIAL_TRANSITION'], ['session', 'NONRESUMABLE_PROVEN'], ['approval', 'CONSUMED'], ['compaction', 'COMPACTED_READBACK_VERIFIED']]) assert.equal(validateStateRecord(kind, value).ok, true);
  assert.equal(validateStateRecord('lane', 'IDENTITY_LOST').ok, false);
  assert.equal(STATES.lane.length, 11);
});

test('commission digest binds every authority-bearing field', () => {
  const valid = commission();
  assert.deepEqual(validateCommissionEnvelope(valid), { ok: true, errors: [] });
  for (const changed of [
    { commissionId: 'other' },
    { queue: { ...valid.queue, documentId: 'other' } },
    { queue: { ...valid.queue, folderId: 'other' } },
    { queue: { ...valid.queue, revision: 'other' } },
    { queue: { ...valid.queue, stateOwner: 'other' } },
    { lane: { ...valid.lane, laneId: 'other' } },
    { lane: { ...valid.lane, owner: 'other' } },
    { worker: { ...valid.worker, workerId: 'other' } },
    { worker: { ...valid.worker, identityHash: hash('c') } },
    { mutating: true },
    { operations: ['identity'] }
  ]) assert.equal(validateCommissionEnvelope({ ...valid, ...changed }).ok, false);
});

test('canonical JSON is deterministic for valid JSON data', () => {
  assert.equal(canonicalJson({ b: 2, a: [true, null, 'x'] }), canonicalJson({ a: [true, null, 'x'], b: 2 }));
  assert.equal(sha256({ b: 2, a: 1 }), sha256({ a: 1, b: 2 }));
});

for (const [name, build] of [
  ['undefined', () => ({ a: undefined })],
  ['function', () => ({ a() {} })],
  ['symbol value', () => ({ a: Symbol('x') })],
  ['symbol key', () => ({ [Symbol('x')]: 1 })],
  ['bigint', () => ({ a: 1n })],
  ['NaN', () => ({ a: Number.NaN })],
  ['infinity', () => ({ a: Infinity })],
  ['negative zero', () => ({ a: -0 })],
  ['sparse array', () => { const a = []; a[1] = 'x'; return a; }],
  ['array property', () => { const a = ['x']; a.extra = true; return a; }],
  ['date', () => ({ a: new Date() })],
  ['cycle', () => { const a = {}; a.self = a; return a; }]
]) test(`canonical JSON rejects ${name}`, () => assert.throws(() => canonicalJson(build()), TypeError));

test('finding requires evidence, routing, and acknowledgements', () => {
  const finding = { findingId: 'f1', observedBySession: 's1', observedAt: '2026-08-11T10:00:00Z', affectedLaneIds: ['l1'], claim: 'bounded', evidenceRefs: ['artifact://e'], evidenceHashes: [hash('d')], confidence: 'high', gateImpact: 'narrows', recommendedAction: 'inspect', scopeChange: false, sentTo: ['s2'], acknowledgements: [{ sessionId: 's2', at: '2026-08-11T10:01:00Z', planChanged: true, note: 'guard updated' }] };
  assert.equal(validateFindingCard(finding).ok, true);
  assert.equal(validateFindingCard({ ...finding, acknowledgements: [] }).ok, false);
  assert.equal(validateFindingCard({ ...finding, evidenceHashes: [] }).ok, false);
});

test('material transition requires strict capability states and evidence', () => {
  const artifact = artifactEvidence();
  const testReceipt = testEvidence();
  const receipt = { receiptId: 'r1', commissionId: 'c1', commissionHash: hash('e'), queueDocumentId: 'doc', queueFolderId: 'folder', queueRevision: 'r1', stateOwner: 'Adam', laneId: 'l1', workerId: 'w1', sessionId: 's1', jobId: 'j1', repository: 'Valar05/home-center', worktree: '/isolated', branch: 'agent/broker', head: gitHead('a'), observedAt: '2026-08-11T10:02:00Z', jobState: 'MATERIAL_TRANSITION', priorState: 'REVIEW_FAILED', newState: 'REVIEW_GAPS_REPAIRED_AND_TESTED_CANDIDATE', capabilityStates, artifactEvidence: [artifact], testEvidence: [testReceipt], findingEvidence: [{ findingId: 'f1', findingHash: hash('1') }], remainingGate: 'independent review', nextAction: 'review' };
  receipt.receiptHash = sha256(receiptDigestPayload(receipt));
  const evidence = new Map([[artifact.ref, artifact], [testReceipt.ref, testReceipt]]);
  const options = { resolveEvidence: ref => evidence.get(ref) };
  assert.equal(validateReceipt(receipt, options).ok, true);
  assert.equal(validateReceipt({ ...receipt, artifactEvidence: [] }, options).ok, false);
  assert.equal(validateReceipt({ ...receipt, testEvidence: [] }, options).ok, false);
  assert.equal(validateReceipt(receipt, {}).ok, false);
  assert.equal(validateReceipt(receipt, { resolveEvidence: () => ({ ...artifact, contentSha256: hash('9') }) }).ok, false);
  assert.equal(validateReceipt({ ...receipt, capabilityStates: { implemented: true } }).ok, false);
  assert.equal(validateReceipt({ ...receipt, newState: receipt.priorState }).ok, false);
  assert.equal(validateReceipt({ ...receipt, testEvidence: [{ ...testReceipt, exitCode: 1 }] }, options).ok, false);
  assert.equal(validateReceipt({ ...receipt, testEvidence: [{ ...testReceipt, head: gitHead('b') }] }, options).ok, false);
});

