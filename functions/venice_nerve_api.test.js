'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {
  CAPABILITIES,
  hashBytes,
  normalizeActions,
  veniceNerveOperationEntries,
} = require('./venice_nerve_api');

test('exact UTF-8 speech hashing is stable', () => {
  assert.equal(hashBytes('Venice'), '4e99f11596c8a05f929879e8e6ec02fe344449577489bd5dd27b75a9dd86c357');
  assert.match(hashBytes('You made the room too quiet.'), /^[a-f0-9]{64}$/);
});

test('actions remain structured and bounded', () => {
  const actions = normalizeActions([{actionId: 'media-action-01', verb: 'media.create', args: {kind: 'audio'}}]);
  assert.equal(actions.length, 1);
  assert.equal(actions[0].verb, 'media.create');
  assert.deepEqual(actions[0].args, {kind: 'audio'});
  assert.throws(() => normalizeActions('media.play'), /actions must be an array/);
});

test('public operation surface is the dedicated mouth vocabulary', () => {
  const entries = veniceNerveOperationEntries();
  assert.deepEqual(Object.keys(entries).sort(), [
    'venice_nerve.turn.cancel',
    'venice_nerve.turn.create',
    'venice_nerve.turn.status',
    'venice_nerve.worker.register',
    'venice_nerve.worker.status',
  ]);
  assert.deepEqual(CAPABILITIES, ['venice.turn']);
});

test('nerve implementation does not import or invoke Computer Hands', () => {
  const source = fs.readFileSync(path.join(__dirname, 'venice_nerve_api.js'), 'utf8');
  assert.doesNotMatch(source, /computer_hands_api|computerHandsOperation|windows-hands-01/);
  assert.match(source, /source: 'local-venice'/);
  assert.match(source, /transformedByOrchestrator: false/);
  assert.match(source, /speech SHA-256 did not match exact UTF-8 speech bytes/);
});

test('Windows worker binds to proven Drive-synced aperture and not body controls', () => {
  const worker = fs.readFileSync(path.resolve(__dirname, '..', 'venice-nerve', 'windows', 'home-center-venice-nerve.ps1'), 'utf8');
  assert.match(worker, /venice-aperture\.ps1/);
  assert.match(worker, /-MessageBase64/);
  assert.doesNotMatch(worker, /input\.type|input\.mouse|window\.focus|screen\.capture/);
  assert.match(worker, /bodyWorkerShared = \$false|bodyWorkerShared/);
});
