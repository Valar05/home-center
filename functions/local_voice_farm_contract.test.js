'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const farm = require('./local_voice_farm_contract');

const base = {requestId: 'ferravine-canary-001', owner: 'drew', text: 'Fortress interface ready. The road remains first.', provider: 'local_cauldron'};

test('split plan preserves every submitted character in order', () => {
  const text = `${'A sentence with breathing room. '.repeat(30)}Cut the cam.`;
  const segments = farm.splitTextLossless(text, 140);
  assert.equal(segments.map((segment) => segment.text).join(''), text);
  assert.ok(segments.length > 1);
});

test('identical request IDs reuse immutable input and conflicts fail', () => {
  const first = farm.createTicket(base);
  const same = farm.createTicket(base);
  assert.equal(farm.reconcileTicket(first, same), first);
  assert.throws(() => farm.reconcileTicket(first, farm.createTicket({...base, text: 'Different.'})), {code: 'local_voice_idempotency_conflict'});
});

test('unknown and unconsented clone profiles fail before a ticket exists', () => {
  assert.throws(() => farm.createTicket({...base, voiceProfileId: 'venice'}), {code: 'local_voice_profile_unknown'});
  assert.throws(() => farm.createTicket({...base, voiceProfileId: 'venice'}, {profileId: 'venice', kind: 'clone'}), {code: 'local_voice_profile_unconsented'});
});

test('a consented clone remains a candidate and never inherits acceptance', () => {
  const profile = {profileId: 'candidate:venice', kind: 'clone', consent: true, owner: 'Drew Clarke', referenceSha256: 'a'.repeat(64), permittedUses: ['tts']};
  const ticket = farm.createTicket({...base, voiceProfileId: profile.profileId}, profile);
  assert.equal(ticket.request.voice.acceptedIdentityClaim, false);
  assert.equal(ticket.receipt.humanAcceptance, 'unreviewed');
});

test('leases require engine capability and current ownership', () => {
  const ticket = farm.createTicket(base);
  assert.throws(() => farm.leaseTicket(ticket, {workerId: 'cauldron-01', capabilities: []}, 1000), {code: 'local_voice_worker_capability_mismatch'});
  const leased = farm.leaseTicket(ticket, {workerId: 'cauldron-01', capabilities: ['kokoro-onnx']}, 1000);
  const running = farm.heartbeatTicket(leased, 'cauldron-01', 2000);
  assert.equal(running.status, 'running');
  assert.throws(() => farm.heartbeatTicket(running, 'other-worker', 3000), {code: 'local_voice_lease_owner_mismatch'});
});

test('completion refuses provider laundering and requires readback equality', () => {
  const ticket = farm.createTicket(base);
  assert.throws(() => farm.validateArtifactReceipt(ticket, {provider: 'cartesia', engine: 'kokoro-onnx', sha256: 'b'.repeat(64), byteCount: 100, inputSha256: ticket.request.inputSha256}), {code: 'local_voice_artifact_identity_mismatch'});
  const receipt = farm.validateArtifactReceipt(ticket, {provider: 'local_cauldron', engine: 'kokoro-onnx', sha256: 'b'.repeat(64), byteCount: 100, readbackSha256: 'b'.repeat(64), readbackByteCount: 100, inputSha256: ticket.request.inputSha256, cloudSpeechSynthesisUsed: false});
  assert.equal(receipt.verified, true);
  assert.equal(receipt.humanAcceptance, 'unreviewed');
});
