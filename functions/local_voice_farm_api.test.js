'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const api = require('./local_voice_farm_api');

test('owner keys are deterministic and redact email identity', () => {
  const first = api.ownerKey('dclarke1005@gmail.com');
  assert.equal(first, api.ownerKey('DCLARKE1005@gmail.com'));
  assert.match(first, /^owner_[a-f0-9]{32}$/);
  assert.equal(first.includes('dclarke'), false);
});

test('artifact names fail closed outside immutable WAV checkpoints', () => {
  assert.equal(api.safeArtifactName('segment-0000.wav'), 'segment-0000.wav');
  assert.equal(api.safeArtifactName('final.wav'), 'final.wav');
  assert.throws(() => api.safeArtifactName('../final.wav'), {failureKind: 'local_voice_artifact_name_invalid'});
  assert.throws(() => api.safeArtifactName('voice.mp3'), {failureKind: 'local_voice_artifact_name_invalid'});
});

test('stable dispatcher exposes only registration, ticket creation, and status', () => {
  const entries = api.localVoiceOperationEntries();
  assert.deepEqual(Object.keys(entries).sort(), [
    'local_voice.ticket.create',
    'local_voice.ticket.status',
    'local_voice.worker.register',
  ]);
  assert.equal(entries['local_voice.worker.register'].write, true);
  assert.equal(entries['local_voice.ticket.status'].write, false);
});

test('public worker origin is HTTPS and cloning is absent from the API', () => {
  assert.match(api.PUBLIC_ORIGIN, /^https:\/\//);
  const text = JSON.stringify(api.localVoiceOperationEntries());
  assert.equal(text.includes('Venice identity claims are forbidden'), true);
});
