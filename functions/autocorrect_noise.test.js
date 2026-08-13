'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const api = require('./autocorrect_noise');

function candidate(intended, observations, contexts, extra = {}) {
  return {intended, intendedNormalized: api.normalizeLexeme(intended), observations, contexts: Array.from({length: contexts}, (_, i) => 'ctx-' + i), explicitConfirmations: 0, rejections: 0, ...extra};
}

function pattern(noisy, candidates, extra = {}) {
  return api.refreshPattern({noisy, noisyNormalized: api.normalizeLexeme(noisy), candidates, protected: false, protectedOverride: false, intrinsicSystemRisk: false, ...extra});
}

test('recurrence separates candidate, good, and gold', () => {
  assert.equal(api.tierForCandidate(candidate('the', 1, 1), 1), 'candidate');
  assert.equal(api.tierForCandidate(candidate('the', 2, 1), 2), 'good');
  assert.equal(api.tierForCandidate(candidate('the', 3, 2), 3), 'gold');
});

test('confirmation promotes and rejection blocks', () => {
  assert.equal(api.tierForCandidate(candidate('jars', 1, 1, {explicitConfirmations: 1}), 1), 'gold');
  assert.equal(api.tierForCandidate(candidate('jars', 3, 2, {rejections: 1}), 3), 'rejected');
});

test('conflicts preserve the source', () => {
  const record = pattern('noise', {a: candidate('voice', 2, 2), b: candidate('choice', 2, 2)});
  const result = api.planResolution('noise', {noise: record}, true);
  assert.equal(record.ambiguous, true);
  assert.equal(result.goldAppliedText, 'noise');
  assert.equal(result.decisions[0].blockedReason, 'conflicting_patterns');
});

test('good stays advisory and gold requires applyGold', () => {
  const records = {
    teh: pattern('teh', {a: candidate('the', 2, 2)}),
    recieve: pattern('recieve', {a: candidate('receive', 3, 2)}),
  };
  const preview = api.planResolution('Teh package will recieve it.', records, false);
  assert.equal(preview.goldAppliedText, preview.originalText);
  assert.equal(preview.reviewText, 'The package will receive it.');
  const applied = api.planResolution('Teh package will recieve it.', records, true);
  assert.equal(applied.goldAppliedText, 'Teh package will receive it.');
});

test('longest phrase wins', () => {
  const result = api.planResolution('home center dame', {
    'home center dame': pattern('home center dame', {a: candidate('Home Center Drive', 3, 2)}),
    dame: pattern('dame', {a: candidate('name', 3, 2)}),
  }, true);
  assert.equal(result.goldAppliedText, 'Home Center Drive');
});

test('system-shaped and adjacent identifier tokens fail closed', () => {
  assert.equal(api.systemShapedToken('time.now'), true);
  const result = api.planResolution('time.now', {time: pattern('time', {a: candidate('dime', 3, 2)})}, true);
  assert.equal(result.goldAppliedText, 'time.now');
  assert.equal(result.decisions[0].blockedReason, 'system_shaped_token');
});

test('authenticated identity creates isolated stable scopes', () => {
  const a = api.authenticatedUserScope({uid: 'user-a', email: 'same@example.com'});
  const b = api.authenticatedUserScope({uid: 'user-b', email: 'same@example.com'});
  assert.notEqual(a, b);
  assert.equal(a, api.authenticatedUserScope({uid: 'user-a'}));
  assert.throws(() => api.authenticatedUserScope({}), /authenticated Home Center user/);
});

test('span generation is bounded to four words', () => {
  const text = 'One two three four five';
  const spans = api.candidateSpans(text, api.segmentText(text));
  assert.equal(spans.some((item) => item.normalized === 'one two three four'), true);
  assert.equal(spans.some((item) => item.normalized === 'one two three four five'), false);
  assert.ok(spans.length <= 96);
});
