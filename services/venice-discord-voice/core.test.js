'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const {publicError, stateAllowsSpeech, validateSpeakRequest} = require('./core');

const guildId = '1534104765796192356';
const task = {
  guildId,
  userId: '111111111111111111',
  roomChannelId: '222222222222222222',
  interactionId: '333333333333333333',
  text: 'Venice answers once.',
  cutEpoch: 4,
  stateEpoch: 9,
};

test('validates one bounded, explicitly addressed speech task', () => {
  assert.deepEqual(validateSpeakRequest(task, guildId), task);
  assert.throws(() => validateSpeakRequest({...task, guildId: '999'}, guildId), /invalid_speak_request/);
  assert.throws(() => validateSpeakRequest({...task, text: 'x'.repeat(1801)}, guildId), /invalid_speak_request/);
});

test('speech requires the exact live consent epochs and source room', () => {
  const state = {state: 'PRESENT', epoch: 9, cutEpoch: 4, rooms: {[task.roomChannelId]: 'PRESENT'}};
  assert.equal(stateAllowsSpeech(state, task), true);
  assert.equal(stateAllowsSpeech({...state, state: 'CUT'}, task), false);
  assert.equal(stateAllowsSpeech({...state, epoch: 10}, task), false);
  assert.equal(stateAllowsSpeech({...state, cutEpoch: 5}, task), false);
  assert.equal(stateAllowsSpeech({...state, rooms: {[task.roomChannelId]: 'WITHDRAWN'}}, task), false);
});

test('unexpected runtime errors are content-free at the HTTP boundary', () => {
  assert.equal(publicError(new Error('private transcript contents')), 'voice_unavailable');
  assert.equal(publicError(new Error('user_not_in_voice')), 'user_not_in_voice');
});
