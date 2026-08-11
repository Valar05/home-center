'use strict';

const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const assert = require('node:assert/strict');
const { sha256 } = require('../src/contracts');
const { adapterInterfaces } = require('../src/adapters');
const { createProbe, validateProbeResult, resultDigestPayload } = require('../src/probes');
const { hash } = require('./helpers');

function probe(adapter = 'qwen') {
  return createProbe({ adapter, operation: 'health', probeId: 'probe-1', nonceHash: hash('1'), commissionId: 'c1', commissionHash: hash('2'), queueDocumentId: 'doc', queueFolderId: 'folder', queueRevision: 'r1', stateOwner: 'Adam', laneId: 'lane-1', laneOwner: 'worker-1', workerId: 'worker-1', workerIdentityHash: hash('3'), issuedAt: '2026-08-11T10:00:00Z', expiresAt: '2026-08-11T10:05:00Z', accountId: 'account-1', conversationId: 'conversation-1', cdpTargetId: 'target-1' });
}

function result(expected) {
  const value = { schemaVersion: expected.schemaVersion, kind: 'LOCAL_BROKER_PROBE_RESULT', mode: 'read_only', probeId: expected.probeId, nonceHash: expected.nonceHash, adapter: expected.adapter, operation: expected.operation, commission: expected.commission, queue: expected.queue, lane: expected.lane, worker: expected.worker, observedAt: '2026-08-11T10:01:00Z', resultId: 'result-1', healthy: true };
  if (expected.browserIdentity) value.browserIdentity = expected.browserIdentity;
  value.resultHash = sha256(resultDigestPayload(value));
  return value;
}

test('every adapter descriptor remains read-only and fully identity bound', () => {
  assert.deepEqual(Object.keys(adapterInterfaces), ['computer_hands', 'browser_nerve', 'venice_nerve', 'codex', 'continue', 'qwen', 'piper', 'local_assembler', 'local_playback', 'voice_aperture']);
  for (const descriptor of Object.values(adapterInterfaces)) {
    assert.deepEqual(descriptor.operations, ['health', 'identity']);
    assert.equal(descriptor.requiredIdentityFields.includes('queueRevision'), true);
    assert.equal(descriptor.requiredIdentityFields.includes('laneId'), true);
  }
});

test('probe result binds schema, kind, SHA, RFC3339, commission, queue, lane, worker, freshness, and replay', () => {
  const expected = probe();
  const observed = result(expected);
  const options = { now: '2026-08-11T10:01:30Z', maxAgeMs: 60_000, seenProbeIds: [], seenResultIds: [] };
  assert.equal(validateProbeResult(expected, observed, options).ok, true);
  for (const changed of [
    { schemaVersion: '2.0.0' }, { kind: 'other' }, { resultHash: hash('f') }, { observedAt: 'not-time' },
    { commission: { ...observed.commission, commissionId: 'other' } }, { queue: { ...observed.queue, revision: 'other' } },
    { lane: { ...observed.lane, laneId: 'other' } }, { worker: { ...observed.worker, workerId: 'other' } }
  ]) assert.equal(validateProbeResult(expected, { ...observed, ...changed }, options).ok, false);
  assert.equal(validateProbeResult(expected, observed, { ...options, now: '2026-08-11T10:03:00Z' }).ok, false);
  assert.equal(validateProbeResult(expected, observed, { ...options, seenProbeIds: ['probe-1'] }).ok, false);
  assert.equal(validateProbeResult(expected, observed, { ...options, seenResultIds: new Set(['result-1']) }).ok, false);
});

test('Browser Nerve probe binds account, conversation, and CDP target', () => {
  const expected = probe('browser_nerve');
  const observed = result(expected);
  const options = { now: '2026-08-11T10:01:30Z', maxAgeMs: 60_000, seenProbeIds: [], seenResultIds: [] };
  assert.equal(validateProbeResult(expected, observed, options).ok, true);
  for (const key of ['accountId', 'conversationId', 'cdpTargetId']) {
    const changed = { ...observed, browserIdentity: { ...observed.browserIdentity, [key]: 'other' } };
    changed.resultHash = sha256(resultDigestPayload(changed));
    assert.equal(validateProbeResult(expected, changed, options).ok, false);
  }
});

test('source contains no runtime, network, file mutation, synthesis, or playback implementation', () => {
  const sourceDir = path.join(__dirname, '..', 'src');
  const source = fs.readdirSync(sourceDir).sort().map(file => fs.readFileSync(path.join(sourceDir, file), 'utf8')).join('\n');
  for (const forbidden of ['child_process', 'writeFile', 'appendFile', 'unlink', 'rmSync', 'fetch(', 'http.request', 'https.request', 'browser_sessions.act', 'phone_hands.enqueue', 'AudioContext', 'speechSynthesis', 'piper --', 'ffplay', 'aplay']) assert.equal(source.includes(forbidden), false, forbidden);
});
