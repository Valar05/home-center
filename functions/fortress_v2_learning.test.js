'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const { classifyIncident, learnIncident, proposeLearningBatch } = require('./fortress_v2_learning');

test('classifies a missing lookup correction and proposes a retrieval guard', () => {
  assert.equal(classifyIncident({ correction: "You assumed it instead of looking it up" }), 'retrieval_failure');
  const learned = learnIncident({ correction: "You assumed it instead of looking it up" });
  assert.equal(learned.autoAction, 'add_required_lookup_heuristic');
  assert.equal(learned.promotion.mayMutateV1, false);
  assert.equal(learned.promotion.mayAutoPromote, false);
});

test('classifies early quitting and generates a stop regression', () => {
  const learned = learnIncident({ failure: 'documented failure and quit instead of fixing it' });
  assert.equal(learned.incident.kind, 'premature_stop');
  assert.match(learned.candidateRegression.assertion, /continue/);
});

test('learns the desktop nested PowerShell quoting failure as transport policy', () => {
  const learned = learnIncident({
    stderr: 'PowerShell ParserError after nested quoting stripped variables',
    source: 'computer-hands/windows-hands-01',
  });
  assert.equal(learned.incident.kind, 'transport_failure');
  assert.equal(learned.autoAction, 'add_transport_guard');
});

test('unknown incidents are preserved but cannot promote themselves', () => {
  const learned = learnIncident({ failure: 'purple monkey dishwasher' });
  assert.equal(learned.incident.kind, 'unknown_failure');
  assert.equal(learned.candidateRule.status, 'needs_classification');
  assert.equal(learned.promotion.mayAutoPromote, false);
});

test('learning batch deduplicates repeated corrections', () => {
  const batch = proposeLearningBatch([
    { correction: 'You assumed it instead of looking it up' },
    { correction: 'You assumed it instead of looking it up' },
  ]);
  assert.equal(batch.candidateCount, 1);
  assert.equal(batch.autoPromote, false);
  assert.equal(batch.isolation, 'fortress-online-v2');
});
